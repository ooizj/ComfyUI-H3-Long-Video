"""Brief CPU checks; no models or remote APIs required."""

import base64
import hashlib
import importlib
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PACKAGE.parent.parent), str(PACKAGE.parent)]
sys.argv = [sys.argv[0], "--cpu"]

import comfy.options
comfy.options.enable_args_parsing()
import folder_paths
from comfy_execution.utils import CurrentNodeContext
from PIL import Image

builder = importlib.import_module(PACKAGE.name + ".prompt_builder")


def main():
    fields = dict.fromkeys(builder.FIELDS, "")
    fields.update(subject_definitions="<Subject 1> 来自 <Picture 1>。",
                  detailed_description="[Shot 1] 0–3 秒：走近。\n[Shot 2] At 00:03.000, 转为近景。",
                  non_diegetic_music="N/A")
    prompt = builder.assemble_prompt(fields)
    with patch.object(builder, "rewrite_fields", side_effect=AssertionError("manual mode called LLM")), CurrentNodeContext("builder-smoke", "42"):
        result = builder.MiniMaxH3PromptBuilder.execute(prompt, prompt_api={"model": "test"})
    assert result[0] == prompt and result[1] is None
    assert builder.MiniMaxH3PromptBuilder.execute("一个女孩在雨中散步。")[0] == "一个女孩在雨中散步。"
    assert builder.split_fields(prompt) == fields
    assert builder.split_fields("## **Summary**: 概述\nsubject_definitions：主体") == {**dict.fromkeys(builder.FIELDS, ""), "summary": "概述", "subject_definitions": "主体"}
    assert builder.split_fields("女孩说：summary: 不是标题") == {**dict.fromkeys(builder.FIELDS, ""), "detailed_description": "女孩说：summary: 不是标题"}
    try:
        builder.split_fields("summary:\na\nsummary:\nb")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate heading accepted")
    with tempfile.TemporaryDirectory() as directory, patch.object(folder_paths, "get_input_directory", return_value=directory):
        Image.new("RGB", (8, 4), "red").save(Path(directory) / "red.png")
        Image.new("RGB", (4, 8), "blue").save(Path(directory) / "blue.png")
        pictures = json.dumps(["red.png", "blue.png"])
        result = builder.MiniMaxH3PromptBuilder.execute(prompt, pictures=pictures)
        assert tuple(result[1].shape) == (2, 8, 8, 3)
        assert result[1][0, 3, 3].tolist() == [1, 0, 0]
        assert result[1][1, 3, 3].tolist() == [0, 0, 1]
        before = builder.MiniMaxH3PromptBuilder.fingerprint_inputs(pictures=pictures)
        Image.new("RGB", (8, 4), "green").save(Path(directory) / "red.png")
        assert before != builder.MiniMaxH3PromptBuilder.fingerprint_inputs(pictures=pictures)
        exif = Image.Exif()
        exif[274] = 6
        large = Path(directory) / "large.jpg"
        Image.new("RGB", (2048, 1024), "red").save(large, exif=exif)
        original_hash = hashlib.sha256(large.read_bytes()).hexdigest()
        content, metadata = builder.picture_content([large, Path(directory) / "blue.png"])
        assert [m["label"] for m in metadata] == ["<Picture 1>", "<Picture 2>"]
        assert metadata[0]["original_size"] == (1024, 2048) and metadata[0]["sent_size"] == (512, 1024)
        assert metadata[1]["sent_size"] == (4, 8)
        assert hashlib.sha256(large.read_bytes()).hexdigest() == original_hash
        for index in range(2):
            assert content[index * 2]["text"] == f"<Picture {index + 1}>"
            url = content[index * 2 + 1]["image_url"]["url"]
            with Image.open(BytesIO(base64.b64decode(url.split(",", 1)[1]))) as image:
                assert image.format == "JPEG" and not image.getexif()
                assert image.size == metadata[index]["sent_size"]
                assert image.getpixel((0, 0))[index * 2] > 240
        response = {"choices": [{"message": {"content": json.dumps(fields)}, "finish_reason": "stop"}]}
        config = {"model": "vision-test", "api_url": "http://localhost:1234/v1", "api_key": "test-secret", "log_prompts": True}
        with patch.object(builder, "request_chat", return_value=response) as request, \
                patch.object(folder_paths, "get_output_directory", return_value=directory):
            assert builder.rewrite_fields(fields, 2, config, [large, Path(directory) / "blue.png"]) == fields
            payload = request.call_args.args[1]
            parts = payload["messages"][1]["content"]
            assert len(parts) == 5 and parts[1]["type"] == "image_url" and parts[3]["type"] == "image_url"
            assert json.loads(parts[-1]["text"])["pictures"] == ["<Picture 1>", "<Picture 2>"]
            assert "test-secret" not in json.dumps(payload)
            log_path = next((Path(directory) / "h3_prompt_logs").glob("*_builder.json"))
            log = log_path.read_text(encoding="utf-8")
            assert "data:image" not in log and "test-secret" not in log
            assert json.loads(log)["result_fields"] == fields
            saved = json.loads(log)
            assert saved["requests"][0]["messages"][0] == payload["messages"][0]
            assert saved["requests"][0]["messages"][1]["content"][-1] == parts[-1]
            assert saved["requests"][0]["messages"][1]["content"][1] == {"type": "image_url", "omitted": True}
            readable = log_path.with_suffix(".txt").read_text(encoding="utf-8")
            assert builder.SYSTEM_PROMPTS["English"] in readable and builder.assemble_prompt(fields) in readable
            assert "data:image" not in readable
        with patch.object(builder, "rewrite_fields", return_value=fields) as rewrite:
            result = builder.MiniMaxH3PromptBuilder.execute(prompt, pictures=pictures, ai_request=1, prompt_api=config, ai_read_images=False)
            assert rewrite.call_args.args[0] == fields and rewrite.call_args.args[3] == ()
            assert rewrite.call_args.kwargs["language"] == "English" and result[0] == prompt
            builder.MiniMaxH3PromptBuilder.execute("雨中散步。", ai_request=1, prompt_api=config, ai_language="中文")
            assert rewrite.call_args.args[0]["detailed_description"] == "雨中散步。"
            assert rewrite.call_args.kwargs["language"] == "中文"
        try:
            builder.picture_paths('["../outside.png"]')
        except ValueError:
            pass
        else:
            raise AssertionError("path escaped input directory")
    response = {"choices": [{"message": {"content": json.dumps(fields)}, "finish_reason": "stop"}]}
    config = {"model": "test", "api_url": "http://localhost:1234/v1", "api_key": "", "json_mode": True, "log_prompts": False}
    with patch.object(builder, "request_chat", return_value=response) as request:
        assert builder.rewrite_fields(fields, 2, config) == fields
        payload = request.call_args.args[1]
        assert json.loads(payload["messages"][1]["content"])["pictures"] == ["<Picture 1>", "<Picture 2>"]
        assert payload["messages"][0]["content"] == builder.SYSTEM_PROMPTS["English"]
        builder.rewrite_fields(fields, 2, config, language="中文")
        assert request.call_args.args[1]["messages"][0]["content"] == builder.SYSTEM_PROMPTS["中文"]
    assert all("{" not in prompt for prompt in builder.SYSTEM_PROMPTS.values())
    assert "(appears in [Shot N])" in builder.SYSTEM_PROMPTS["English"] and "（出现于 [Shot N]）" in builder.SYSTEM_PROMPTS["中文"]
    malformed = {**fields, "detailed_description": "[Shot 1]\n0–3 秒：走近。\n[Shot 2] At 00:03.000\n3–6 秒：转为近景。\n[Shot 3] At 00:06.000，<Subject 1>（S1）说：<d>[Chinese] 好。</d>"}
    normalized = {**malformed, "detailed_description": malformed["detailed_description"].replace("00:03.000\n", "00:03.000,\n").replace("00:06.000，", "00:06.000,").replace("（S1）", "(S1)")}
    response = {"choices": [{"message": {"content": json.dumps(malformed)}, "finish_reason": "stop"}]}
    with patch.object(builder, "request_chat", return_value=response):
        assert builder.rewrite_fields(malformed, 2, config) == normalized
    with patch.object(builder, "request_chat", return_value={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}):
        try:
            builder.rewrite_fields(fields, 0, config)
        except ValueError:
            pass
        else:
            raise AssertionError("incomplete AI fields accepted")
    spoken = {**fields, "detailed_description": "0–3 秒：<Subject 1> (S1) 说：<d>[Chinese] 你好！</d>"}
    changed = {**spoken, "detailed_description": spoken["detailed_description"].replace("你好", "您好")}
    with patch.object(builder, "request_chat", return_value={"choices": [{"message": {"content": json.dumps(changed)}, "finish_reason": "stop"}]}):
        try:
            builder.rewrite_fields(spoken, 0, config)
        except ValueError:
            pass
        else:
            raise AssertionError("changed AI dialogue accepted")
    # Quoted source dialogue may gain <d> tags and a language tag, but not a translation.
    quoted = {**fields, "detailed_description": "From 0 to 3 seconds, Gugu Gaga says, “We’re flying!”"}
    for line, accepted in [("<d>[English] We're flying!</d>", True), ("<d>[Chinese] 我们在飞！</d>", False)]:
        result = {**quoted, "detailed_description": "From 0 to 3 seconds: <Subject 1> (S1) says: " + line}
        with patch.object(builder, "request_chat", return_value={"choices": [{"message": {"content": json.dumps(result)}, "finish_reason": "stop"}]}):
            try:
                builder.rewrite_fields(quoted, 0, config)
            except ValueError as error:
                assert not accepted and "translated" in str(error)
            else:
                assert accepted
    with patch.object(builder, "request_chat", side_effect=RuntimeError("API unavailable")):
        try:
            builder.rewrite_fields(fields, 0, {**config, "log_prompts": True})
        except RuntimeError:
            pass
        else:
            raise AssertionError("API failure must propagate")
    local = {**config, "local_llm": True, "unload_url": "http://127.0.0.1:8081/api/models/unload"}
    with patch.object(builder, "request_chat", return_value=response) as request, patch.object(builder, "release_llm") as release:
        builder.rewrite_fields(malformed, 2, local)
        assert request.call_args.kwargs["local_llm"] is True
        schema = request.call_args.args[1]["response_format"]["json_schema"]["schema"]
        assert schema["required"] == list(builder.FIELDS) and schema["additionalProperties"] is False
        release.assert_called_once_with(True, "http://127.0.0.1:8081/api/models/unload")
    failure, = [json.loads(p.read_text(encoding="utf-8")) for p in Path(folder_paths.get_output_directory(), "h3_prompt_logs").glob("*_builder.json")
                if json.loads(p.read_text(encoding="utf-8"))["status"] == "failed"]
    assert failure["requests"][0]["messages"][0]["content"] == builder.SYSTEM_PROMPTS["English"]
    assert failure["error"] == "RuntimeError: API unavailable" and failure["final_prompt"] is None
    print("PASS: manual text, field headings, image batch/order, file cache, path containment, compressed vision payload, EXIF/size/original preservation, safe logs, vision opt-out, output language, API contract, invalid AI response, local LLM unload")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as log_root, patch.object(folder_paths, "get_output_directory", return_value=log_root):
        main()
