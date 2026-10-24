"""Brief CPU checks; no models or remote APIs required."""

import importlib
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
import torch

caption = importlib.import_module(PACKAGE.name + ".image_caption")


def reply(text):
    return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}


def main(log_root):
    images = torch.zeros(2, 2048, 1024, 3)
    images[1, ..., 2] = 1
    config = {"model": "vision-test", "api_url": "http://localhost:1234/v1", "api_key": "test-secret", "log_prompts": True,
              "local_llm": True, "unload_url": "http://127.0.0.1:8081/api/models/unload"}
    with patch.object(caption, "request_chat", side_effect=[reply(" A black frame. "), reply("一块蓝色。")]) as request, \
            patch.object(caption, "release_llm") as release:
        result = caption.MiniMaxH3ImageCaption.execute(images, config, language="中文")
    assert result[0] == "A black frame.\n\n一块蓝色。"
    payload = request.call_args_list[0].args[1]
    assert payload["messages"][0]["content"] == caption.SYSTEM_PROMPTS["中文"] and "Simplified Chinese" in caption.SYSTEM_PROMPTS["中文"]
    assert payload["messages"][1]["content"][0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert request.call_args.kwargs["local_llm"] is True and "test-secret" not in json.dumps(payload)
    release.assert_called_once_with(True, "http://127.0.0.1:8081/api/models/unload")
    log_path = next((Path(log_root) / "h3_prompt_logs").glob("*_caption.json"))
    log = log_path.read_text(encoding="utf-8")
    assert "data:image" not in log and "test-secret" not in log
    assert json.loads(log)["descriptions"] == ["A black frame.", "一块蓝色。"] and json.loads(log)["status"] == "ok"
    readable = log_path.with_suffix(".txt").read_text(encoding="utf-8")
    assert "AI request: image 2" in readable and "一块蓝色。" in readable and "data:image" not in readable
    with patch.object(caption, "request_chat", return_value=reply("")):
        try:
            caption.describe_images(images[:1], {**config, "log_prompts": False})
        except RuntimeError as error:
            assert "empty" in str(error)
        else:
            raise AssertionError("empty description accepted")
    print("PASS: per-image requests, output language, compressed vision payload, safe logs, empty reply, local LLM unload")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as log_root, patch.object(folder_paths, "get_output_directory", return_value=log_root):
        main(log_root)
