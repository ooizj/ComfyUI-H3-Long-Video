"""Keep speech intact on H3's frame grid and check adapted prompts."""

from collections import Counter
import math
import re

from comfy_extras.nodes_minimax_h3 import align_frame_count


_DIALOGUE = re.compile(r"<d>(.*?)</d>", re.DOTALL)
_LANGUAGE = re.compile(r"\s*(\[[^\]]*\]\s*)?")
_PAUSE = re.compile(r"(?<=[。！？；，、…])|(?<=[.!?;,])(?=\s)")
# When another line follows directly, a segment may end this many frames before a line's stated end
# (at most half the line). H3 segment lengths step by 17 frames, so such lines still leave a cut point
# between them; the earlier line just has to finish up to 0.67s sooner than stated.
LINE_END_SLACK = 16
FULL_WIDTH_SPEAKER = re.compile(r"（(S\d+)）")
EVENT_KINDS = ("cut", "action", "sound", "music")
FIRST_FRAME_INSTRUCTION ="For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."


def dialogue_lines(text):
    return Counter(line.strip() for line in _DIALOGUE.findall(text))


def valid_seconds(start, end):
    return (type(start) in (int, float) and type(end) in (int, float)
            and math.isfinite(start) and math.isfinite(end) and 0 <= start <= end)


def validate_timeline(timeline, source):
    """Return (speech, events): timed speech copied from the source, and the other timed details."""
    speech = timeline.get("speech") if isinstance(timeline, dict) else None
    if not isinstance(speech, list):
        raise RuntimeError("LLM must return a speech list.")
    for event in speech:
        if not isinstance(event, dict):
            raise RuntimeError("LLM returned an invalid speech range.")
        passage = event.get("text")
        if not isinstance(passage, str) or not passage.strip() or passage not in source:
            raise RuntimeError("LLM speech text was changed or is missing from the original prompt.")
        start, end = event.get("start_seconds"), event.get("end_seconds")
        if not valid_seconds(start, end) or end == start:
            raise RuntimeError("LLM returned invalid speech start/end seconds.")
    # Plain JSON mode cannot force the events list; without it clips simply get no event times.
    events = timeline.get("events", [])
    if not isinstance(events, list) or any(
            not isinstance(e, dict) or e.get("kind") not in EVENT_KINDS
            or not isinstance(e.get("text"), str) or not e["text"].strip()
            or not valid_seconds(e.get("start_seconds"), e.get("end_seconds")) for e in events):
        raise RuntimeError("LLM returned an invalid timed event. Change variation and retry.")
    return speech, events


def queue_shared_speech(events):
    """Lines given the same source range, e.g. two speakers under one '40–65 秒' heading, are spoken one
    after another in source order instead of all at once, each taking time in proportion to its text."""
    shared = {}
    for event in events:
        shared.setdefault((event["start_seconds"], event["end_seconds"]), []).append(event)
    for (start, end), lines in shared.items():
        if len(lines) < 2:
            continue
        sizes = [len("".join(_LANGUAGE.sub("", d, count=1) for d in _DIALOGUE.findall(e["text"])) or e["text"])
                 for e in lines]
        done = 0
        for event, size in zip(lines, sizes):
            event["start_seconds"] = round(start + (end - start) * done / sum(sizes), 2)
            done += size
            event["end_seconds"] = round(start + (end - start) * done / sum(sizes), 2)
    return events


def split_long_speech(events, source, seconds):
    """Split timed lines longer than one segment at their pauses, so segments can end between the parts.

    Parts get time in proportion to their text. A single <d> block becomes adjacent <d> blocks, so the
    source with those blocks is returned for writing and checking the clip prompts."""
    parts = []
    for event in events:
        start, end, text = event["start_seconds"], event["end_seconds"], event["text"]
        blocks = list(_DIALOGUE.finditer(text))
        if end - start <= seconds or len(blocks) > 1:
            parts.append(event)
            continue
        if blocks:
            inner = blocks[0].group(1)
            language = _LANGUAGE.match(inner).group(0)
            before, after, body = text[:blocks[0].start()], text[blocks[0].end():], inner[len(language):]
        else:
            language, before, after, body = "", "", "", text
        groups, length = [""], 0
        for phrase in _PAUSE.split(body):
            weight = len(phrase.strip()) * (end - start) / max(1, len(body.strip()))
            if phrase.strip() and groups[-1].strip() and length + weight > seconds / 2:
                groups.append("")
                length = 0
            groups[-1] += phrase
            length += weight
        if len(groups) == 1:
            parts.append(event)
            continue
        texts = [f"<d>{language}{g.strip()}</d>" if blocks else g for g in groups]
        texts[0], texts[-1] = before + texts[0], texts[-1] + after
        source = source.replace(text, "".join(texts), 1)
        done, total = 0, sum(len(g.strip()) for g in groups)
        for group, part in zip(groups, texts):
            parts.append({"start_seconds": round(start + (end - start) * done / total, 2),
                          "end_seconds": round(start + (end - start) * (done + len(group.strip())) / total, 2), "text": part})
            done += len(group.strip())
    return parts, source


def protect_dialogue_boundaries(schedule, events, fps):
    ranges = [(round(e["start_seconds"] * fps), round(e["end_seconds"] * fps)) for e in events]
    ranges = [(a, b - min(LINE_END_SLACK, (b - a) // 2)) if any(a < c <= b + LINE_END_SLACK for c, _ in ranges) else (a, b)
              for a, b in ranges]
    original = [(s["sampled_frames"], s["overlap_frames"], s["retained_frames"]) for s in schedule]
    if not ranges:
        return original
    cursor = 0
    for _, _, keep in original[:-1]:
        cursor += keep
        if any(a < cursor < b for a, b in ranges):
            break
    else:
        return original

    total = sum(s[2] for s in original)
    target = original[0][0]
    # A continuation of an existing clip pins context on its first segment too.
    first_overlap = original[0][1]
    context = original[1][1]
    tail_limit = align_frame_count(target + fps)
    plan, cursor = [], 0
    while cursor < total:
        overlap = context if plan else first_overlap
        tail = align_frame_count(max(5, total - cursor + overlap))
        length = tail if tail <= tail_limit else target
        minimum = align_frame_count(max(5, overlap + fps))
        # Intermediate tails must stay on H3's 17-frame grid: the next clip
        # reads the actual latent tail, so trimming an intermediate tail is wrong.
        for delta in range(0, max(tail - length, length) + 17, 17):
            candidates = (length + delta, length - delta) if delta else (length,)
            chosen = None
            for candidate in candidates:
                if candidate > tail or (candidate < minimum and candidate != tail):
                    continue
                end = min(total, cursor + candidate - overlap)
                if end == total or not any(a < end < b for a, b in ranges):
                    chosen = candidate
                    break
            if chosen is not None:
                break
        keep = min(total - cursor, chosen - overlap)
        plan.append((chosen, overlap, keep))
        cursor += keep
    return plan


def validate_prompts(prompts, schedule, events, source, input_mode):
    if (not isinstance(prompts, list) or len(prompts) != len(schedule)
            or any(not isinstance(p, str) or not p.strip() for p in prompts)):
        got = (f"{sum(isinstance(p, str) and bool(p.strip()) for p in prompts)} nonempty of {len(prompts)}"
               if isinstance(prompts, list) else "no prompts list")
        raise RuntimeError(f"LLM must return {len(schedule)} nonempty prompts, one per segment; it returned {got}. "
                           "Change variation and retry, or use a stronger model.")
    if dialogue_lines(source) != dialogue_lines("\n".join(prompts)):
        raise RuntimeError("LLM changed, omitted or repeated quoted <d> dialogue. Change variation and retry.")
    owners = {}
    for event in events:
        for index, segment in enumerate(schedule, 1):
            if segment["final_start_seconds"] <= event["start_seconds"] < segment["final_end_seconds"]:
                for line in _DIALOGUE.findall(event["text"]):
                    owners.setdefault(line.strip(), set()).add(index)
    for index, prompt in enumerate(prompts, 1):
        if any(line.strip() in owners and index not in owners[line.strip()]
               for line in _DIALOGUE.findall(prompt)):
            raise RuntimeError("LLM moved quoted dialogue outside its assigned segment. Change variation and retry.")
    prompts = [FULL_WIDTH_SPEAKER.sub(r"(\1)", prompt) for prompt in prompts]
    if input_mode == "I2VA":
        prompts[0] = FIRST_FRAME_INSTRUCTION + "\n\n" + prompts[0]
    return prompts
