"""CPU smoke test with fake inference and real H3 conditioning/video encoding.

Run with ComfyUI's Python from this repository. No model weights are loaded.
For a checkout outside custom_nodes, set COMFYUI_ROOT to the ComfyUI directory.
"""

from fractions import Fraction
import importlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PACKAGE = Path(__file__).resolve().parents[1]
COMFY_ROOT = Path(os.environ.get("COMFYUI_ROOT", PACKAGE.parent.parent))
sys.path.insert(0, str(COMFY_ROOT))
sys.path.insert(0, str(PACKAGE.parent))
sys.argv = [sys.argv[0], "--cpu"]

import comfy.options
comfy.options.enable_args_parsing()
import torch
import folder_paths
from comfy_api.latest import InputImpl, Types, io
from comfy_execution.utils import CurrentNodeContext
from comfy_extras.nodes_minimax_h3 import video_latent_t

long = importlib.import_module(PACKAGE.name + ".long_video")
motion = importlib.import_module(PACKAGE.name + ".nodes")
planner = importlib.import_module(PACKAGE.name + ".prompt_planner")
timing = importlib.import_module(PACKAGE.name + ".prompt_timing")
store = importlib.import_module(PACKAGE.name + ".segment_store")
REFS = {"Picture": 3, "Video": 0, "Audio": 0}


def test_progress_scope():
    updates = []
    def hook(value, total, preview, **kwargs):
        updates.append((value, total, preview))

    with patch.object(long.comfy.utils, "PROGRESS_BAR_HOOK", hook), CurrentNodeContext("smoke", "long"):
        try:
            with long._LongVideoProgress(10) as progress:
                progress.begin(6, track=True)
                inner = long.comfy.utils.ProgressBar(2)
                inner.update_absolute(1, preview="preview")
                assert updates[-1] == (3, 10, "preview")
                inner.update_absolute(2, preview="preview")
                assert updates[-1] == (6, 10, "preview")
                # A second internal bar must not move the overall bar backwards.
                long.comfy.utils.ProgressBar(4).update_absolute(1, preview="preview")
                assert updates[-1] == (6, 10, "preview")
                with CurrentNodeContext("smoke", "other"):
                    long.comfy.utils.ProgressBar(2).update_absolute(1)
                    assert updates[-1] == (1, 2, None)
                raise RuntimeError("cancelled")
        except RuntimeError as error:
            assert str(error) == "cancelled"
        else:
            raise AssertionError("Progress scope must propagate cancellation")
        assert long.comfy.utils.PROGRESS_BAR_HOOK is hook
        inner.update_absolute(1, preview="preview")
        assert updates[-1] == (1, 2, "preview")

    def cancelled_hook(*args, **kwargs):
        raise RuntimeError("cancelled before start")
    with patch.object(long.comfy.utils, "PROGRESS_BAR_HOOK", cancelled_hook), CurrentNodeContext("smoke", "long"):
        try:
            with long._LongVideoProgress(10):
                raise AssertionError("Cancelled progress must not start")
        except RuntimeError as error:
            assert str(error) == "cancelled before start"
        assert long.comfy.utils.PROGRESS_BAR_HOOK is cancelled_hook


class Clip:
    def __init__(self, events=None):
        self.calls = []
        self.texts = []
        self.events = events

    def tokenize(self, text, **kwargs):
        self.calls.append(kwargs)
        self.texts.append(text)
        return text

    def encode_from_tokens_scheduled(self, tokens):
        if self.events is not None:
            self.events.append(("encode", tokens))
        return [[torch.zeros(1, 1, 8), {}]]


class VideoVAE:
    def __init__(self, events=None):
        self.encode_calls = 0
        self.events = events
        self.encoded = []

    def encode(self, images):
        self.encode_calls += 1
        self.encoded.append(images)
        t = 1 if len(images) == 1 else video_latent_t(len(images))
        return torch.zeros(1, 24, t, images.shape[1] // 16, images.shape[2] // 16)

    def decode(self, z):
        pbar = long.comfy.utils.ProgressBar(2)
        pbar.update_absolute(1, preview="decode-preview")
        pbar.update_absolute(2, preview="decode-preview")
        if self.events is not None:
            self.events.append(("decode", int(z[0, 0, 0, 0, 0])))
        frames = motion._pixel_frames(z.shape[2])
        return torch.full((frames, z.shape[3] * 16, z.shape[4] * 16, 3), float(z[0, 0, 0, 0, 0]) / 10)

    def temporal_compression_decode(self):
        return 3.4

    def spacial_compression_decode(self):
        return 16

    def decode_tiled(self, z, **kwargs):
        return self.decode(z)


class AudioVAE:
    audio_sample_rate = 32000

    def decode(self, z):
        return torch.full((1, z.shape[-1] * 800, 2), 0.05)

    def encode(self, waveform):
        # [1, samples, channels] at 32 kHz -> [1, 32, 2, T] at 40 Hz
        return torch.zeros(1, 32, 2, max(1, waveform.shape[1] // 800))


def test_prompt_api():
    info = planner.MiniMaxH3PromptAPI.GET_NODE_INFO_V1()
    assert tuple(info["output"]) == ("H3_PROMPT_API",)
    fields = info["input"]["required"] | info["input"]["optional"]
    assert {"api_url", "api_key", "model", "json_mode"} <= fields.keys()
    assert not {"story", "prompt", "total_seconds", "segment_count", "input_mode"} & fields.keys()
    assert fields["api_key"][1]["default"] == ""
    assert fields["log_prompts"][1]["default"] is True
    assert fields["max_tokens"][1]["default"] == 65535
    for base, endpoint in [
        ("https://api.deepseek.com", "https://api.deepseek.com/chat/completions"),
        ("http://127.0.0.1:11434/v1/", "http://127.0.0.1:11434/v1/chat/completions"),
        ("http://localhost:1234/v1/chat/completions", "http://localhost:1234/v1/chat/completions"),
        ("https://example.test/proxy/v1?version=1", "https://example.test/proxy/v1/chat/completions?version=1"),
    ]:
        assert planner.chat_endpoint(base) == endpoint
    schedule = planner.segment_schedule(long.plan_segments(14, 7.5, 22))
    assert schedule[0]["pinned_global_interval"] is None
    assert schedule[1]["pinned_global_interval"] == [8 - 22 / 24, 8]
    full_prompt = "From 0-3s the man says <d>[Chinese] 你好！</d>. From 11-14s they toast."
    speech = [{"text": "<d>[Chinese] 你好！</d>", "start_seconds": 0, "end_seconds": 3}]
    timeline = {"speech": speech}
    expected = ["From 0 to 3 seconds, the man says <d>[Chinese] 你好！</d>.", "From 3.92 to 6.92 seconds, they toast."]

    def response(content, status=200, finish="stop"):
        result = MagicMock(status_code=status)
        result.__enter__.return_value = result
        result.json.return_value = {"choices": [{"finish_reason": finish, "message": {
            "role": "assistant", "content": content if isinstance(content, str) else json.dumps(content),
            "reasoning_content": "private-reasoning-placeholder",
        }}], "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
        return result

    def split(*args, **kwargs):
        # These checks repeat inputs on purpose; start each one without earlier planning results.
        planner._PLAN_CACHE.clear()
        return planner.split_prompts(*args, **kwargs)

    with patch.object(planner.requests, "post") as post:
        settings, = planner.MiniMaxH3PromptAPI.execute(api_key="smoke-test-placeholder").result
        post.assert_not_called()
        assert settings["local_llm"] is False and settings["unload_url"] == ""
        post.side_effect = [response(timeline), response({"prompts": expected})]
        assert split(full_prompt, schedule, "Ref2VA", REFS, **settings) == (schedule, expected)
        assert post.call_count == 2
        first, second = post.call_args_list
        assert first.args == ("https://api.deepseek.com/chat/completions",)
        assert first.kwargs["allow_redirects"] is False
        assert first.kwargs["headers"] == {"Authorization": "Bearer smoke-test-placeholder"}
        assert first.kwargs["json"]["thinking"] == {"type": "enabled"}
        assert first.kwargs["json"]["reasoning_effort"] == "low"
        for call in (first, second):
            payload = call.kwargs["json"]
            assert "tools" not in payload and "tool_choice" not in payload
            assert payload["response_format"] == {"type": "json_object"}
            assert [m["role"] for m in payload["messages"]] == ["system", "user"]
        request = json.loads(second.kwargs["json"]["messages"][1]["content"])
        assert request["full_h3_prompt"] == full_prompt and request["reference_counts"] == REFS
        assert request["input_mode"] == "Ref2VA" and len(request["clips"]) == 2
        assert request["continues_existing_video"] is False
        assert request["clips"][0]["speech"][0]["local_seconds"] == [0, 3]
        assert request["clips"][1]["global_time_at_local_zero"] == 7.08
        log_directory = Path(folder_paths.get_output_directory()) / "h3_prompt_logs"
        saved_path, = log_directory.glob("*.json")
        saved_text = saved_path.read_text(encoding="utf-8")
        saved = json.loads(saved_text)
        assert saved["prompts"] == expected and saved["status"] == "ok"
        assert saved["timeline"] == timeline and len(saved["responses"]) == 2
        assert [r["stage"] for r in saved["requests"]] == ["timeline", "prompts"]
        assert saved["requests"][0]["messages"] == first.kwargs["json"]["messages"]
        assert saved["requests"][1]["messages"] == second.kwargs["json"]["messages"]
        assert saved["usage"]["total_tokens"] == 60
        assert "smoke-test-placeholder" not in saved_text and "private-reasoning-placeholder" not in saved_text
        readable = saved_path.with_suffix(".txt").read_text(encoding="utf-8")
        assert "8.000-14.000s" in readable and "Time tool trace" not in readable
        assert planner.TIMELINE_PROMPT in readable and planner.SYSTEM_PROMPT in readable

        local_settings, = planner.MiniMaxH3PromptAPI.execute(api_url="http://localhost:1234/v1/chat/completions",
            model="local-model", json_mode=False, max_tokens=4096, timeout_seconds=60).result
        assert local_settings["local_llm"] is True
        post.side_effect = [response(timeline), response("```json\n" + json.dumps({"prompts": expected}) + "\n```")]
        with patch.object(planner.comfy.model_management, "unload_all_models") as unload_comfy:
            prompts = split(full_prompt, schedule, "I2VA", 0, **local_settings)[1]
            assert unload_comfy.call_count == 2
        assert prompts[0].startswith("For the target video, at 0.00 seconds")
        assert not prompts[1].startswith("For the target video")
        assert post.call_args.args == ("http://localhost:1234/v1/chat/completions",)
        assert post.call_args.kwargs["headers"] == {} and post.call_args.kwargs["timeout"] == (10, 60)
        assert "response_format" not in post.call_args.kwargs["json"]
        assert "thinking" not in post.call_args.kwargs["json"]

        for url, choice, local in [("http://127.0.0.1:8081/v1", "auto", True), ("http://[::1]:8081/v1", "auto", True),
                                   ("http://192.168.1.5:8081/v1", "auto", False), ("https://api.deepseek.com", "yes", True),
                                   ("http://127.0.0.1:8081/v1", "no", False)]:
            assert planner.MiniMaxH3PromptAPI.execute(api_url=url, local_llm=choice).result[0]["local_llm"] is local
        swap, = planner.MiniMaxH3PromptAPI.execute(api_url="http://127.0.0.1:8081/v1", model="qwen",
            unload_url="http://127.0.0.1:8081/api/models/unload", json_mode=False).result
        post.reset_mock()
        post.side_effect = [response(timeline), response({"prompts": expected}), MagicMock()]
        with patch.object(planner.comfy.model_management, "unload_all_models"):
            assert split(full_prompt, schedule, "Ref2VA", REFS, **swap)[1] == expected
        assert [c.args[0] for c in post.call_args_list] == ["http://127.0.0.1:8081/v1/chat/completions"] * 2 + ["http://127.0.0.1:8081/api/models/unload"]
        post.reset_mock()
        post.side_effect = [response(timeline), response({}, status=500), MagicMock()]
        with patch.object(planner.comfy.model_management, "unload_all_models"):
            try:
                split(full_prompt, schedule, "Ref2VA", REFS, **swap)
            except RuntimeError:
                pass
            else:
                raise AssertionError("A failed local request must propagate")
        assert post.call_args.args == ("http://127.0.0.1:8081/api/models/unload",)

        # Local servers get schema-constrained JSON; section fields are joined like the Builder does.
        structured, = planner.MiniMaxH3PromptAPI.execute(api_url="http://127.0.0.1:8081/v1", model="qwen").result
        sections = planner.SECTIONS["Ref2VA"]
        clips = [{**dict.fromkeys(sections, "N/A"), "detailed_description": text} for text in expected]
        post.reset_mock()
        post.side_effect = [response(timeline), response({"prompts": clips})]
        with patch.object(planner.comfy.model_management, "unload_all_models"):
            prompts = split(full_prompt, schedule, "Ref2VA", REFS, **structured)[1]
        assert prompts[1] == "\n\n".join(f"{name}:\n{expected[1] if name == 'detailed_description' else 'N/A'}" for name in sections)
        timeline_call, prompts_call = post.call_args_list
        assert timeline_call.kwargs["json"]["response_format"]["json_schema"]["schema"] == planner.TIMELINE_SCHEMA
        clip_schema = prompts_call.kwargs["json"]["response_format"]["json_schema"]["schema"]["properties"]["prompts"]
        assert clip_schema["minItems"] == clip_schema["maxItems"] == 2 and clip_schema["items"]["required"] == list(sections)
        assert prompts_call.kwargs["json"]["messages"][0]["content"] == planner.SYSTEM_PROMPT + planner.STRUCTURED_NOTE

        # The LLM finds timed events; each clip gets them with local times calculated by code.
        events = [{"kind": "action", "start_seconds": 11, "end_seconds": 14, "text": "they toast"},
                  {"kind": "cut", "start_seconds": 7.5, "end_seconds": 7.5, "text": "cut to the glasses"},
                  {"kind": "music", "start_seconds": 2, "end_seconds": 14, "text": "piano from 2 seconds"}]
        post.reset_mock()
        post.side_effect = [response({**timeline, "events": events}), response({"prompts": expected})]
        split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        assert json.loads(post.call_args_list[0].kwargs["json"]["messages"][1]["content"])["total_seconds"] == 14
        clips = json.loads(post.call_args.kwargs["json"]["messages"][1]["content"])["clips"]
        assert clips[0]["events"] == [{"kind": "cut", "local_time": "00:07.500", "text": "cut to the glasses"},
                                      {"kind": "music", "local_seconds": [2, 8], "text": "piano from 2 seconds"}]
        assert clips[1]["events"] == [
            {"kind": "action", "local_seconds": [3.92, 6.92], "text": "they toast"},
            {"kind": "cut", "local_time": "00:00.417", "text": "cut to the glasses"},
            {"kind": "music", "local_seconds": [0, 6.92], "text": "piano from 2 seconds", "ongoing_at_local_zero": True}]
        for bad in [{"kind": "lighting"}, {"end_seconds": 1}, {"text": " "}, "cut"]:
            post.side_effect = [response({**timeline, "events": [events[0] | bad if isinstance(bad, dict) else bad]})]
            try:
                split(full_prompt, schedule, "Ref2VA", REFS, **settings)
            except RuntimeError as error:
                assert "invalid timed event" in str(error)
            else:
                raise AssertionError("Invalid timed events must fail")
        # A line timed only by its shot reaches the clip prompts ending once spoken.
        post.side_effect = [response({"speech": [dict(speech[0], end_seconds=7.5, from_shot=True)]}), response({"prompts": expected})]
        split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        assert json.loads(post.call_args.kwargs["json"]["messages"][1]["content"])["clips"][0]["speech"][0]["local_seconds"] == [0, 1]

        post.reset_mock()
        post.side_effect = [response(timeline), response({"prompts": expected})]
        first = split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        assert planner.split_prompts(full_prompt, schedule, "Ref2VA", REFS, **settings) == first and post.call_count == 2
        post.side_effect = [response(timeline), response({"prompts": expected})]
        planner.split_prompts(full_prompt, schedule, "Ref2VA", REFS, **(settings | {"variation": 1}))
        assert post.call_count == 4

        post.side_effect = [response(timeline), response({"prompts": [expected[0].replace("the man", "<Subject 1>（S1）"), expected[1]]})]
        prompts = split(full_prompt, schedule, "Ref2VA", REFS, **settings)[1]
        assert prompts[0].startswith("From 0 to 3 seconds, <Subject 1>(S1) says") and "（" not in prompts[0]

        invalid = [
            'invalid', {"prompts": ["one"]}, {"prompts": [expected[0], ""]},
            {"prompts": [expected[0], expected[1] + " <d>[Chinese] 你好！</d>"]},
            {"prompts": ["The man smiles.", expected[1] + " <d>[Chinese] 你好！</d>"]},
        ]
        for content in invalid:
            post.side_effect = [response(timeline), response(content)]
            try:
                split(full_prompt, schedule, "Ref2VA", REFS, **settings)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Bad prompts must fail before sampling")
        post.side_effect = [response(timeline), response({}, finish="length")]
        try:
            split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        except RuntimeError as error:
            assert "truncated" in str(error)
        else:
            raise AssertionError("A truncated response must not reach video sampling")
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in log_directory.glob("*.json")]
        assert any(r["finish_reason"] == "length" and r["status"] == "invalid_response" for r in reports)

        post.reset_mock()
        untimed = ["They fly over the clouds.", "They keep flying above the clouds."]
        post.side_effect = [response({"speech": []}), response({"prompts": untimed})]
        assert split("They fly over the clouds.", schedule, "T2VA", 0, **settings) == (schedule, untimed)
        assert post.call_count == 2
        assert all(not clip["speech"] for clip in json.loads(post.call_args.kwargs["json"]["messages"][1]["content"])["clips"])
        for bad in [
            {"speech": [dict(speech[0], text="An invented line.")]},
            {"speech": [dict(speech[0], end_seconds=-1)]},
            {"speech": [dict(speech[0], start_seconds=float("nan"))]},
            {"speech": "none"},
        ]:
            post.side_effect = [response(bad)]
            try:
                split(full_prompt, schedule, "Ref2VA", REFS, **settings)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Invalid speech data must fail")
        files_before = set(log_directory.iterdir())
        post.side_effect = [response(timeline), response({"prompts": expected})]
        split(full_prompt, schedule, "Ref2VA", REFS, **(settings | {"log_prompts": False}))
        assert set(log_directory.iterdir()) == files_before
        continuous = 'From 0-14s the speaker says <d>[Chinese] 你好！</d>.'
        post.reset_mock()
        post.side_effect = [response({"speech": [dict(speech[0], end_seconds=14)]})]
        with patch.object(planner._LOG, "warning") as warning:
            final_schedule, final_prompts = split(
                continuous, planner.segment_schedule(long.plan_segments(14, 5, 22)), 'Ref2VA', 3, **settings)
        assert len(final_schedule) == 1 and final_prompts == [continuous] and post.call_count == 1
        assert warning.call_count == 1 and "so no timed line is cut" in warning.call_args.args[0]
        line = '<d>[Chinese] 你好，见到你很高兴。我们一起去山上看日出吧，好不好？</d>'

        def reply(url, **kwargs):
            request = json.loads(kwargs["json"]["messages"][1]["content"])
            if "clips" not in request:
                return response({"speech": [{"start_seconds": 0, "end_seconds": 14, "text": line}]})
            assert line not in request["full_h3_prompt"]
            return response({"prompts": [" ".join(s["text"] for s in clip["speech"]) or "They listen." for clip in request["clips"]]})
        post.side_effect = reply
        final_schedule, final_prompts = split("From 0-14s the speaker says " + line,
                                              planner.segment_schedule(long.plan_segments(14, 5, 22)), "Ref2VA", REFS, **settings)
        assert len(final_schedule) == 3 and "".join(final_prompts).count("<d>") == 4
        post.side_effect = [response({}, status=401)]
        try:
            split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        except RuntimeError as error:
            assert "401" in str(error) and "smoke-test-placeholder" not in str(error)
        else:
            raise AssertionError("HTTP errors must propagate")
        rejected = MagicMock(status_code=500)
        rejected.__enter__.return_value = rejected
        rejected.json.return_value = {"error": {"code": 500, "message": "image input is not supported - hint: provide the mmproj"}}
        post.side_effect = [rejected]
        try:
            split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        except RuntimeError as error:
            assert "HTTP 500: image input is not supported" in str(error)
        else:
            raise AssertionError("HTTP errors must propagate")
        post.side_effect = [response(timeline), response({"prompts": [expected[0], expected[1], "summary:"]})]
        try:
            split(full_prompt, schedule, "Ref2VA", REFS, **settings)
        except RuntimeError as error:
            assert "must return 2 nonempty prompts" in str(error) and "returned 3 nonempty of 3" in str(error)
        else:
            raise AssertionError("A wrong prompt count must fail")
    with patch.object(planner.requests, "post") as post:
        for url in ["file:///tmp/key", "https://name:secret@example.test/v1", ""]:
            try:
                split(full_prompt, schedule, "Ref2VA", REFS, **(settings | {"api_url": url}))
            except ValueError as error:
                assert "API URL" in str(error) and "secret" not in str(error)
            else:
                raise AssertionError("Invalid API URLs must fail before a request")
        post.assert_not_called()
    with patch.object(planner.requests, "get") as get:
        get.return_value.__enter__.return_value.json.return_value = {"object": "list", "data": [{"id": "qwen-a"}, {"id": "qwen-b"}]}
        assert planner.list_api_models("https://api.deepseek.com", " key ") == ["qwen-a", "qwen-b"]
        assert get.call_args.args == ("https://api.deepseek.com/models",)
        assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer key"} and get.call_args.kwargs["allow_redirects"] is False
        planner.list_api_models("http://127.0.0.1:8081/v1/chat/completions?x=1", "")
        assert get.call_args.args == ("http://127.0.0.1:8081/v1/models?x=1",) and get.call_args.kwargs["headers"] == {}
    return settings


def test_dialogue_boundaries():
    source = ('From 8 to 11 seconds, she says <d>[Chinese] 我们干一杯吧。</d>. '
              'From 11 to 14 seconds, he replies <d>[Chinese] 干杯！</d>.')
    passages = source.split('. ')
    events = [dict(text=p, start_seconds=a, end_seconds=b)
              for (a, b), p in zip([(8, 11), (11, 14)], passages)]
    schedule = planner.segment_schedule(long.plan_segments(14, 5, 22))
    plan = timing.protect_dialogue_boundaries(schedule, events, 24)
    # The lines follow each other directly, so the cut lands just before the first one's stated end.
    assert plan == [(124, 0, 124), (158, 22, 136), (107, 22, 76)]
    adjusted = planner.segment_schedule(plan)
    assert adjusted[1]['final_end_seconds'] == 260 / 24
    assert adjusted[2]['final_end_seconds'] == 14
    assert sum(p[2] for p in plan) == 336
    assert all(length % 17 == 5 and keep == length - overlap for length, overlap, keep in plan[:-1])
    windows = planner.prompt_windows(adjusted, events, [])
    assert [e['local_seconds'] for e in windows[1]['speech']] == [[3.75, 6.58]]
    assert [e['local_seconds'] for e in windows[2]['speech']] == [[1.08, 4.08]]
    assert schedule[1]['final_end_seconds'] == 226 / 24
    # Three back-to-back lines filling 10 s still split into two segments instead of one 10 s segment.
    touching = [dict(events[0], start_seconds=a, end_seconds=b) for a, b in [(0, 3), (3, 6), (6, 10)]]
    assert len(timing.protect_dialogue_boundaries(planner.segment_schedule(long.plan_segments(10, 5, 22)), touching, 24)) == 2

    # A line longer than a segment is split at its punctuation, each part a <d> block with proportional time.
    narration = "旁白：<d>[Chinese] 很久以前，山上住着一位剑客。他每天清晨看日出，从不下山。</d>"
    parts, split_source = timing.split_long_speech([{"start_seconds": 0, "end_seconds": 12, "text": narration}], "开场。" + narration, 5.2)
    assert [p["text"] for p in parts] == ["旁白：<d>[Chinese] 很久以前，</d>", "<d>[Chinese] 山上住着一位剑客。</d>",
                                          "<d>[Chinese] 他每天清晨看日出，</d>", "<d>[Chinese] 从不下山。</d>"]
    assert split_source == "开场。" + "".join(p["text"] for p in parts)
    assert parts[0]["start_seconds"] == 0 and parts[-1]["end_seconds"] == 12
    assert all(a["end_seconds"] == b["start_seconds"] for a, b in zip(parts, parts[1:]))
    short = {"start_seconds": 0, "end_seconds": 5, "text": narration}
    assert timing.split_long_speech([short], narration, 5.2) == ([short], narration)

    # Two speakers listed under one '40–65 秒' heading talk in turn, not at once.
    block = [{"start_seconds": 40, "end_seconds": 65, "text": "<d>[Chinese] 你是谁？</d>"},
             {"start_seconds": 40, "end_seconds": 65, "text": "<d>[Chinese] 我是守了五百年的人。</d>"},
             {"start_seconds": 65, "end_seconds": 70, "text": "<d>[Chinese] 走吧。</d>"}]
    assert [(e["start_seconds"], e["end_seconds"]) for e in timing.queue_shared_speech(block)] == [(40, 47.14), (47.14, 65), (65, 70)]

    # An untagged line the LLM wrapped in a <d> block is read back as the source has it.
    wrapped = {"speech": [{"start_seconds": 0, "end_seconds": 3, "from_shot": True, "text": "<d>[Chinese] 慢点吃，小心烫哦。</d>"}]}
    assert timing.validate_timeline(wrapped, '她说："慢点吃，小心烫哦。"')[0][0]["text"] == "慢点吃，小心烫哦。"

    # A line timed only by its shot ends once spoken instead of filling the shot, which H3 fills by repeating it.
    # Its own range, a sung line and a line without from_shot keep their range; a cap never lengthens a line.
    # A line the LLM marks from_shot is still kept when the words leading into it say it is sung.
    lines = [(15.5, 23, True, "她骄傲地宣布：", "大厨嘎嘎正在施展魔法！"), (0, 7.5, False, "他说：", "<d>[Chinese] 你好！</d>"),
             (30, 40, False, "她唱：", "<d>[Chinese] 月亮代表我的心。</d>"), (40, 48, None, "他说：", "<d>[Chinese] 走吧。</d>"),
             (50, 52, True, "旁白：", "<d>[Chinese] 很久以前，山上住着一位剑客。</d>"), (60, 70, True, "She says: ", "<d>[English] Slow down, it's hot.</d>"),
             (70, 80, True, "", "<d>[Japanese] ねえ、見て！大きな大根が抜けたよ！</d>"), (80, 90, True, "他说：", "我们去 Starbucks 买一杯 latte 吧。"),
             (90, 100, True, "Cut to a close-up as she sings: ", "<d>[English] Fly me to the moon.</d>"),
             (100, 110, True, "<Subject 1>抱着婴儿，哼唱摇篮曲：", "<d>[Chinese] 月儿明，风儿静。</d>"),
             (110, 120, True, "The singer (S1) bows. Then she says: ", "<d>[English] Thank you, good night.</d>")]
    source = "".join(lead + t for *_, lead, t in lines)
    lines = [{"start_seconds": a, "end_seconds": b, "text": t} | ({} if s is None else {"from_shot": s}) for a, b, s, _, t in lines]
    assert [(e["start_seconds"], e["end_seconds"]) for e in timing.cap_shot_speech(lines, source)] == [
        (15.5, 18.5), (0, 7.5), (30, 40), (40, 48), (50, 52), (60, 62.8), (70, 74.6), (80, 83.37), (90, 100), (100, 110),
        (110, 112.4)]
    # Two lines sharing a shot are queued first, then each ends once spoken.
    shared = [dict(line, from_shot=True) for line in block[:2]]
    queued = timing.cap_shot_speech(timing.queue_shared_speech(shared), "".join(e["text"] for e in shared))
    assert [(e["start_seconds"], e["end_seconds"]) for e in queued] == [(40, 41.25), (47.14, 49.89)]
    # 2026-10-17 run: shot-long lines pushed a segment end 0.125 s before the 23 s cut, and the next segment drew a
    # second penguin girl. Capped, that segment ends 1.54 s earlier and its line gets 3 s instead of 7.5 s.
    run = [(0, 7.5, "看！我拔到了一个大萝卜！"), (7.5, 12.5, "咕咕真棒，今晚做热腾腾的萝卜炖汤好不好？"),
           (12.5, 15.5, "好耶！还要加满满的菜叶！"), (15.5, 23, "大厨嘎嘎正在施展魔法！"), (23, 30, "慢点吃，小心烫哦。")]
    run = timing.cap_shot_speech([{"start_seconds": a, "end_seconds": b, "from_shot": True, "text": t} for a, b, t in run],
                                 "".join(t for *_, t in run))
    assert [e["end_seconds"] for e in run] == [3.3, 12.5, 15.5, 18.5, 25.55]
    capped = planner.segment_schedule(timing.protect_dialogue_boundaries(
        planner.segment_schedule(long.plan_segments(30, 10, 22)), run, 24))
    assert [s["final_end_seconds"] for s in capped] == [12.25, 515 / 24, 30]

    for context in (5, 22, 39, 56):
        initial = planner.segment_schedule(long.plan_segments(30, 5, context))
        speech = [dict(events[0], start_seconds=3.2, end_seconds=15.3)]
        planned = timing.protect_dialogue_boundaries(initial, speech, 24)
        assert sum(p[2] for p in planned) == 720
        cursor = 0
        for length, overlap, keep in planned[:-1]:
            cursor += keep
            assert length % 17 == 5 and keep == length - overlap
            assert not round(3.2 * 24) < cursor < round(15.3 * 24)
    assert timing.protect_dialogue_boundaries(schedule, [], 24) == long.plan_segments(14, 5, 22)
    # A continuation keeps its first segment's pinned context when boundaries move.
    continuing = planner.segment_schedule(long.plan_segments(14, 5, 22, continuing=True))
    moved = timing.protect_dialogue_boundaries(continuing, [dict(events[0], start_seconds=3.2, end_seconds=6)], 24)
    assert moved != long.plan_segments(14, 5, 22, continuing=True)
    assert all(overlap == 22 for _, overlap, _ in moved) and sum(p[2] for p in moved) == 336
    assert len(timing.protect_dialogue_boundaries(schedule, [dict(events[0], start_seconds=0, end_seconds=14)], 24)) == 1


def main():
    test_progress_scope()
    test_dialogue_boundaries()
    with tempfile.TemporaryDirectory() as log_root, \
            patch.object(folder_paths, "get_output_directory", return_value=log_root):
        api_settings = test_prompt_api()
    node = long.MiniMaxH3LongVideo
    assert tuple(node.GET_NODE_INFO_V1()["output"]) == ("VIDEO", "STRING", "LATENT")
    optional = node.GET_NODE_INFO_V1()["input"]["optional"]
    assert optional["save_latents"][1]["default"] is True
    assert optional["ref_image_size"][1]["default"] == "match"
    assert long.plan_segments(14, 5, 22, continuing=True) == [(124, 22, 102), (124, 22, 102), (158, 22, 132)]
    for total, segment, context in [(0.1, 5, 22), (5, 5, 22), (60.1, 5, 56), (14, 15, 22)]:
        parts = long.plan_segments(total, segment, context, continuing=True)
        assert sum(p[2] for p in parts) == max(1, round(total * 24))
        assert all(overlap == context and length % 17 == 5 for length, overlap, _ in parts)
    assert node.GET_NODE_INFO_V1()["input"]["optional"]["segment_seconds"][1]["default"] == 15.0
    assert long.plan_segments(14, 15, 22) == [(345, 0, 336)]
    assert len(long.plan_segments(30, 15, 22)) == 2
    plan = long.plan_segments(30, 5, 22)
    assert len(plan) == 7 and sum(keep for _, _, keep in plan) == 720
    # Long Video also keeps the last segment's rounding up to H3's grid, so its latent ends with the video.
    def delivered(parts):
        return parts[:-1] + [(parts[-1][0], parts[-1][1], parts[-1][0] - parts[-1][1])]
    kept = delivered(plan)
    total_frames = sum(keep for _, _, keep in kept)
    assert 720 <= total_frames < 720 + 17
    assert sum(k for *_, k in delivered(long.plan_segments(14, 5, 22))) == 345
    assert long.plan_segments(14, 5, 22) == [(124, 0, 124), (124, 22, 102), (141, 22, 110)]
    schedule = planner.segment_schedule(long.plan_segments(14, 5, 22))
    assert long.plan_segments(6, 5, 22) == [(158, 0, 144)]
    for total, segment, context in [(0.1, 5, 22), (5, 5, 22), (60.1, 5, 56), (2, 0.1, 39)]:
        parts = long.plan_segments(total, segment, context)
        assert sum(p[2] for p in parts) == max(1, round(total * 24))
        assert all(length % 17 == 5 and 0 < keep <= length - overlap for length, overlap, keep in parts)
        assert all(keep == length - overlap for length, overlap, keep in parts[:-1])

    samples = []
    events = []

    def sample(noise, guider, sampler, sigmas, latent):
        index = len(samples)
        events.append(("sample", index + 1))
        long.comfy.utils.ProgressBar(1).update_absolute(1, preview="sample-preview")
        positive = guider.conditioning[0][1]
        if index:
            keyframes = positive["minimax_keyframes"]
            video_keys = [k for k in keyframes if "latent" in k]
            audio_keys = [k for k in keyframes if "audio_latent" in k]
            assert len(video_keys) == 7 and len(audio_keys) == 1
            assert all(torch.all(k["latent"] == index) for k in video_keys)
            assert torch.all(audio_keys[0]["audio_latent"] == index)
        for z in latent["samples"].unbind():
            z.fill_(index + 1)
        samples.append((noise.seed, positive))
        return io.NodeOutput(latent, latent)

    original_temp = folder_paths.get_temp_directory()
    with tempfile.TemporaryDirectory() as temp, \
            patch.object(long.BasicScheduler, "execute", return_value=io.NodeOutput(torch.tensor([1., 0.]))), \
            patch.object(long.BasicGuider, "execute", side_effect=lambda model, conditioning: io.NodeOutput(SimpleNamespace(conditioning=conditioning))), \
            patch.object(long.SamplerCustomAdvanced, "execute", side_effect=sample), \
            patch.object(long, "split_prompts", side_effect=lambda prompt, schedule, *args, **kwargs: (schedule, [prompt] * len(schedule))):
        folder_paths.set_temp_directory(temp)
        try:
            clip = Clip(events)
            updates = []
            def hook(value, total, preview, **kwargs):
                updates.append((value / total, preview))
            with patch.object(long.comfy.utils, "PROGRESS_BAR_HOOK", hook), CurrentNodeContext("smoke", "long"):
                video, preview, last_latent = node.execute(None, clip, VideoVAE(events), AudioVAE(), "A continuous walk.",
                                      30, width=32, height=32, seed=100, tiled_decode=True, segment_seconds=5,
                                      prompt_api=api_settings).result
                assert long.comfy.utils.PROGRESS_BAR_HOOK is hook
            fractions = [value for value, _ in updates]
            assert fractions[0] == 0 and fractions[-1] == 1
            assert all(a <= b for a, b in zip(fractions, fractions[1:]))
            assert all(value < 1 for value in fractions[:-1])
            assert sum(preview == "sample-preview" for _, preview in updates) == 7
            assert video.get_frame_count() == total_frames and abs(video.get_duration() - total_frames / 24) < 1 / 24
            assert [s[0] for s in samples] == list(range(100, 107))
            video_log, = (Path(folder_paths.get_output_directory()) / "h3_prompt_logs").glob("*_video.json")
            saved = json.loads(video_log.read_text(encoding="utf-8"))
            assert saved["prompts"] == ["A continuous walk."] * 7
            assert saved["seeds"] == [s[0] for s in samples]
            assert saved["prompt_id"] == "smoke" and saved["node_id"] == "long"
            assert saved["status"] == "prepared"
            assert len(clip.calls) == 1
            assert events == [("encode", "A continuous walk.")] + [
                (stage, index) for group in ((1, 2, 3), (4, 5, 6), (7,))
                for stage in ("sample", "decode") for index in group
            ]
            components = video.get_components()
            assert components.images.shape[0] == total_frames and components.audio["sample_rate"] == 32000
            cursor = 0
            for index, (_, _, keep) in enumerate(kept):
                value = (index + 1) / 10
                for frame in (cursor, cursor + keep - 1):
                    assert abs(float(components.images[frame].mean()) - value) < 0.03
                cursor += keep
            assert not list(Path(temp).glob("h3_segments_*"))
            del components

            # save_latents: every segment's latent and MP4 plus a complete manifest.
            run_name, = store.list_runs()
            run_dir = Path(store.runs_root()) / run_name
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["status"] == "complete" and manifest["segments_saved"] == 7
            assert [s["seed"] for s in manifest["segments"]] == list(range(100, 107))
            assert sorted(p.name for p in run_dir.iterdir()) == ["manifest.json"] + sorted(
                f"seg_{i:04d}.{ext}" for i in range(1, 8) for ext in ("mp4", "safetensors"))
            assert [s["retained_frames"] for s in manifest["segments"]] == [keep for _, _, keep in kept]
            assert InputImpl.VideoFromFile(str(run_dir / "seg_0002.mp4")).get_frame_count() == plan[1][2]
            long_video, long_latent = video, last_latent

            # Load Latent: 'latest' and segment 0 pick the last saved segment.
            loaded, info, loaded_video = store.MiniMaxH3LongVideoLoadLatent.execute(store.LATEST, 0).result
            assert torch.all(loaded["samples"][0] == 7) and torch.all(loaded["samples"][1] == 7)
            assert "segment 7/7" in info and loaded_video.get_frame_count() == total_frames
            third, _, third_video = store.MiniMaxH3LongVideoLoadLatent.execute(run_name, 3).result
            assert torch.all(third["samples"][0] == 3)
            assert third_video.get_frame_count() == sum(keep for _, _, keep in kept[:3])
            for run, segment in [(run_name, 8), ("../elsewhere", 1)]:
                try:
                    store.MiniMaxH3LongVideoLoadLatent.execute(run, segment)
                except FileNotFoundError:
                    pass
                else:
                    raise AssertionError("A missing run or segment must fail")
            assert isinstance(store.MiniMaxH3LongVideoLoadLatent.fingerprint_inputs(run_name, 3), str)

            # frames: a cut inside a segment keeps a 17g+5 frame prefix of picture and sound.
            cuts = store.cut_points(manifest["segments"][2])
            assert cuts[-1][0] == manifest["segments"][2]["sampled_frames"] and len(cuts) > 1
            assert all((f - 5) % 17 == 0 and f >= store.MIN_CUT_FRAMES for f, _ in cuts)
            assert abs(cuts[-1][1] - manifest["segments"][2]["final_end_seconds"]) < 1e-9
            cut_frames, cut_time = cuts[0]
            cut, cut_info, cut_video = store.MiniMaxH3LongVideoLoadLatent.execute(run_name, 3, cut_frames).result
            assert cut["samples"][0].shape[2] == (cut_frames - 5) // 17 * 5 + 2
            assert cut["samples"][1].shape[-1] == round(cut_frames * 5 / 3)
            assert f"{cut_time:.2f}s" in cut_info
            # video: the saved picture and sound up to the cut, ending inside segment 3.
            components = cut_video.get_components()
            assert components.images.shape[0] == round(cut_time * long.FPS)
            assert abs(float(components.images[-1].mean()) - 0.3) < 0.03
            assert components.audio["waveform"].shape[-1] == round(cut_time * components.audio["sample_rate"])
            del components
            try:
                store.MiniMaxH3LongVideoLoadLatent.execute(run_name, 3, cut_frames + 1)
            except ValueError as error:
                assert f"nearest point is {cut_frames} frames" in str(error)
            else:
                raise AssertionError("An off-grid cut must fail")

            # context_latent: segment 1 is a continuation, pinned from the given latent.
            def continue_from(expected_value, **kwargs):
                samples.clear()
                vae = VideoVAE()
                result = node.execute(None, Clip(), vae, AudioVAE(), "Keep walking.", 5, width=32, height=32,
                                      segment_seconds=5, save_latents=False, **kwargs).result
                keyframes = samples[0][1]["minimax_keyframes"]
                video_keys = [k for k in keyframes if "latent" in k]
                assert len(video_keys) == 7 and len([k for k in keyframes if "audio_latent" in k]) == 1
                if expected_value is not None:
                    assert all(torch.all(k["latent"] == expected_value) for k in video_keys)
                assert result[0].get_frame_count() == 136
                return result, vae

            continue_from(7, context_latent=long_latent)
            continue_from(3, context_latent=third)
            continue_from(3, context_latent=cut)
            assert len(store.list_runs()) == 1

            # context_video: only its last context_length frames are encoded.
            _, vae = continue_from(None, context_video=long_video)
            assert vae.encoded[0].shape[0] == 22 and abs(float(vae.encoded[0].mean()) - 0.7) < 0.03

            short_clip = InputImpl.VideoFromComponents(Types.VideoComponents(
                images=torch.zeros(30, 32, 32, 3), audio=None, frame_rate=Fraction(30)))
            refusals = [
                (dict(context_latent=long_latent, context_video=long_video), "not both"),
                (dict(context_latent=long_latent, first_frame=torch.zeros(1, 32, 32, 3)), "first_frame"),
                (dict(context_latent=long_latent, width=64), "cannot be resized"),
                (dict(context_latent={"samples": [long_latent["samples"].unbind()[0]]}), "no audio stream"),
                (dict(context_video=long_video, width=64), "context_video is 32x32"),
                (dict(context_video=short_clip), "30.000 fps"),
            ]
            for kwargs, message in refusals:
                samples.clear()
                kwargs = {"width": 32, "height": 32} | kwargs
                with patch.object(long, "split_prompts") as split:
                    try:
                        node.execute(None, Clip(), VideoVAE(), AudioVAE(), "Keep walking.", 14,
                                     segment_seconds=5, prompt_api=api_settings, save_latents=False, **kwargs)
                    except ValueError as error:
                        assert message in str(error), (message, str(error))
                    else:
                        raise AssertionError(f"Must refuse: {message}")
                    split.assert_not_called()
                assert not samples

            samples.clear()
            clip = Clip()
            first = torch.zeros(1, 32, 32, 3)
            node.execute(None, clip, VideoVAE(), AudioVAE(), "Walk.", 7,
                         width=32, height=32, first_frame=first, tiled_decode=False, segment_seconds=5, prompt_api=api_settings)
            assert len(clip.calls) == 2
            assert len(clip.calls[0]["images"]) == 1 and not clip.calls[1]["images"]

            samples.clear()
            clip = Clip()
            node.execute(None, clip, VideoVAE(), AudioVAE(), "<Picture 1> walks.", 7,
                         width=32, height=32, first_frame=first, reference_images=first.repeat(2, 1, 1, 1), segment_seconds=5,
                         prompt_api=api_settings)
            assert len(clip.calls) == 1
            assert all(len(s[1]["minimax_refs"]) == 2 for s in samples)
            assert len(samples[0][1]["minimax_keyframes"]) == 1

            if "ref_image_size" in inspect.signature(long.MiniMaxH3ReferenceToVideo.execute).parameters:
                # 'match' scales a 64 px reference to the 32 px video's area; 'max' keeps it.
                for size, latent_h in [("match", 2), ("max", 4)]:
                    samples.clear()
                    node.execute(None, Clip(), VideoVAE(), AudioVAE(), "<Picture 1> walks.", 5, width=32, height=32,
                                 reference_images=torch.zeros(1, 64, 64, 3), ref_image_size=size, save_latents=False)
                    assert samples[0][1]["minimax_refs"][0]["latent_h"] == latent_h

            # A 30 fps reference video is resampled to 24 fps; its soundtrack is <Audio 1>, reference_audio <Audio 2>.
            samples.clear()
            clip = Clip()
            vae = VideoVAE()
            ref_clip = InputImpl.VideoFromComponents(Types.VideoComponents(
                images=torch.zeros(60, 32, 32, 3), frame_rate=Fraction(30),
                audio={"waveform": torch.zeros(1, 2, 64000), "sample_rate": 32000}))
            voice = {"waveform": torch.zeros(1, 1, 16000), "sample_rate": 16000}
            with patch.object(long, "split_prompts", side_effect=lambda prompt, schedule, mode, counts, **kwargs: (
                    (schedule, [prompt] * len(schedule)) if mode == "Ref2VA" and counts == {"Picture": 0, "Video": 1, "Audio": 2}
                    else None)):
                node.execute(None, clip, vae, AudioVAE(), "<Video 1> speaks with <Audio 2>.", 7, width=32, height=32,
                             segment_seconds=5, prompt_api=api_settings, save_latents=False,
                             reference_videos={"reference_video_0": ref_clip}, reference_audios={"reference_audio_0": voice})
            assert [b["kind"] for b in samples[0][1]["minimax_refs"]] == ["video_audio", "audio"]
            assert all(s[1]["minimax_refs"] is samples[0][1]["minimax_refs"] for s in samples)
            assert [item["type"] for item in clip.calls[0]["minimax_ref_items"]] == ["audio", "video", "audio"]
            assert vae.encoded[0].shape[0] == 39

            full_prompt = "detailed_description: [Shot 1] A continuous 14-second dinner conversation."
            def adapt(prompt, schedule, mode, reference_count, **settings):
                assert prompt == full_prompt and settings == api_settings
                assert schedule == planner.segment_schedule(long.plan_segments(14, segment_seconds, 22))
                assert mode == expected_mode and reference_count == {"Picture": expected_refs, "Video": 0, "Audio": 0}
                return schedule, [f"Segment {s['segment']}: continue dinner." for s in schedule]

            for segment_seconds, expected_count, expected_mode, expected_refs in [
                (5.0, 3, "Ref2VA", 3), (5.5, 3, "I2VA", 0), (5.0, 3, "T2VA", 0),
            ]:
                samples.clear()
                events.clear()
                clip = Clip(events)
                vae = VideoVAE(events)
                with patch.object(long, "split_prompts", side_effect=adapt) as split:
                    video, preview, _ = node.execute(
                        None, clip, vae, AudioVAE(), full_prompt, 14,
                        width=32, height=32, segment_seconds=segment_seconds,
                        first_frame=first if expected_mode != "T2VA" else None,
                        reference_images=first.repeat(expected_refs, 1, 1, 1) if expected_refs else None,
                        prompt_api=api_settings).result
                    split.assert_called_once()
                assert len(samples) == expected_count and video.get_frame_count() == 345
                assert clip.texts == [f"Segment {i + 1}: continue dinner." for i in range(expected_count)]
                assert events == [("encode", text) for text in clip.texts] + [
                    (stage, index + 1) for stage in ("sample", "decode") for index in range(expected_count)
                ]
                assert f"Segment {expected_count} | final" in preview and "smoke-test-placeholder" not in preview
                if expected_refs:
                    assert all(len(s[1]["minimax_refs"]) == expected_refs for s in samples)
                    assert all(s[1]["minimax_refs"] is samples[0][1]["minimax_refs"] for s in samples)
                    assert vae.encode_calls == expected_refs + 1
                    assert all(len(c["minimax_ref_items"]) == expected_refs for c in clip.calls)
                    assert len(samples[0][1]["minimax_keyframes"]) == 1

            samples.clear()
            adjusted = planner.segment_schedule([(124, 0, 124), (90, 22, 68), (175, 22, 144)])
            with patch.object(long, "split_prompts", return_value=(adjusted, ["Greeting.", "Eating.", "Toast."])):
                video, preview, _ = node.execute(
                    None, Clip(), VideoVAE(), AudioVAE(), full_prompt, 14,
                    width=32, height=32, segment_seconds=5, prompt_api=api_settings).result
            assert len(samples) == 3 and video.get_frame_count() == 345
            assert 'final 8.000-14.375s' in preview and 'sampled 7.292s' in preview

            samples.clear()
            clip = Clip()
            with patch.object(long, "split_prompts") as split:
                node.execute(None, clip, VideoVAE(), AudioVAE(), full_prompt, 14,
                             width=32, height=32, prompt_api=api_settings)
                split.assert_not_called()
                assert clip.texts == [full_prompt]

            samples.clear()
            with patch.object(long, "split_prompts") as split:
                try:
                    node.execute(None, Clip(), VideoVAE(), AudioVAE(), full_prompt, 14,
                                 width=32, height=32, segment_seconds=5)
                except ValueError as error:
                    assert "needs 3 segments" in str(error)
                else:
                    raise AssertionError("Multiple segments without prompt_api must not run")
                split.assert_not_called()
                assert not samples

            samples.clear()
            with patch.object(long, "split_prompts", side_effect=RuntimeError("API failed")):
                try:
                    node.execute(None, Clip(), VideoVAE(), AudioVAE(), full_prompt, 14,
                                 width=32, height=32, prompt_api=api_settings, segment_seconds=5)
                except RuntimeError as error:
                    assert str(error) == "API failed"
                else:
                    raise AssertionError("API failure must propagate before sampling")
                assert not samples

            files_before = set(Path(temp).iterdir())
            samples.clear()

            def fail_second_segment(*args):
                if samples:
                    raise RuntimeError("cancelled")
                return sample(*args)

            with patch.object(long.SamplerCustomAdvanced, "execute", side_effect=fail_second_segment):
                try:
                    node.execute(None, Clip(), VideoVAE(), AudioVAE(), "Walk.", 7, width=32, height=32, segment_seconds=5,
                                 prompt_api=api_settings)
                except RuntimeError as error:
                    assert str(error) == "cancelled"
                else:
                    raise AssertionError("Sampling failure must propagate")
            assert set(Path(temp).iterdir()) == files_before
        finally:
            folder_paths.set_temp_directory(original_temp)
    print("PASS: registration, 15s default, frame planning, plain JSON prompt planning, speech/dialogue validation, credential-safe logs, API bypass, multi-segment API requirement, local LLM VRAM handover, schema-constrained output, code-calculated event times, plan reuse, model list, grouped encoding/sampling, cross-group latent/audio continuation, real MP4 frame order, overall progress and hook cleanup, reference reuse, failure cleanup, saved segments and Load Latent, context_latent/context_video continuation and refusals, ref_image_size, reference videos and audio")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as output_root, patch.object(folder_paths, "get_output_directory", return_value=output_root):
        main()
