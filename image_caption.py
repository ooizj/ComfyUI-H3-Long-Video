"""Image descriptions written by the vision model behind H3 Prompt API."""

import logging
import sys
import time

import numpy as np
from PIL import Image

from comfy_api.latest import io

from .prompt_builder import jpeg_url
from .prompt_log import new_prompt_log_path, prompt_request_log, prompt_trace_text, write_prompt_log
from .prompt_planner import chat_endpoint, release_llm, request_chat, response_message

_LOG = logging.getLogger("h3_motion_context")
_PROMPT = """Describe the supplied image as a prompt that recreates it. Output only the description,
as one plain paragraph without headings, lists or Markdown.
Cover what is visible: the subjects and their count, appearance, hairstyle, clothing with colours and
materials, pose, expression and gaze; props; the setting from foreground to background; shot size,
camera angle and composition; lighting direction and quality; colour palette; and the style or medium,
such as photograph, 3D render or anime illustration.
Describe only what can be seen. Do not guess names, identities, relationships or a story, and state
unclear details only as far as they can be confirmed. Copy visible text verbatim in its original language.
"""
SYSTEM_PROMPTS = {
    "English": _PROMPT + "Write the description in English.",
    "中文": _PROMPT + "Write the description in Simplified Chinese.",
}


def save_caption_log(descriptions, language, model, elapsed, responses, requests_log, api_key, error):
    report = {"operation": "image_caption", "model": model, "language": language, "elapsed_seconds": round(elapsed, 3),
              "descriptions": descriptions, "responses": responses, "requests": requests_log,
              "error": f"{type(error).__name__}: {error}" if error else None,
              "status": "failed" if error else "ok"}
    text = f"Model: {model}\nElapsed: {elapsed:.3f}s\nLanguage: {language}\n\n{prompt_trace_text(requests_log, responses)}"
    if error:
        text += f"\n\nError: {report['error']}"
    return write_prompt_log(new_prompt_log_path("caption"), report, text, api_key)


def describe_images(images, config, language="English"):
    key = config.get("api_key", "").strip()
    endpoint, headers = chat_endpoint(config["api_url"]), {"Authorization": f"Bearer {key}"} if key else {}
    descriptions, responses, requests_log = [], [], []
    started = time.monotonic()
    try:
        for index, image in enumerate(images):
            stage = f"image {index + 1}"
            url, jpeg_bytes = jpeg_url(Image.fromarray(np.clip(255.0 * image.cpu().numpy(), 0, 255).astype(np.uint8)))
            payload = {
                "model": config["model"], "max_tokens": config.get("max_tokens", 4096), "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPTS[language]},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": url}},
                                                 {"type": "text", "text": "Describe this image."}]},
                ],
            }
            _LOG.info("H3 Image Caption: %s, %s, %.1f KiB JPEG", payload["model"], stage, jpeg_bytes / 1024)
            requests_log.append(prompt_request_log(payload, stage))
            data = request_chat(endpoint, payload, headers, config.get("timeout_seconds", 600), local_llm=config.get("local_llm", False))
            text = (response_message(data, responses, stage).get("content") or "").strip()
            if not text:
                raise RuntimeError("AI returned an empty description. Use a vision model, or raise max_tokens for a reasoning model.")
            descriptions.append(text)
        return "\n\n".join(descriptions)
    finally:
        release_llm(config.get("local_llm", False), config.get("unload_url", ""))
        if config.get("log_prompts", True):
            save_caption_log(descriptions, language, config["model"], time.monotonic() - started,
                             responses, requests_log, config.get("api_key", ""), sys.exception())


class MiniMaxH3ImageCaption(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ImageCaption", display_name="H3 Image Caption",
            category="video/minimax",
            description="Describe images with the vision model of the connected H3 Prompt API, e.g. to write a prompt from a reference picture.",
            inputs=[
                io.Image.Input("image", tooltip="Each image of a batch is described separately; descriptions are separated by a blank line."),
                io.Custom("H3_PROMPT_API").Input("prompt_api", tooltip="Its model must accept images."),
                io.Combo.Input("language", options=list(SYSTEM_PROMPTS), default="English",
                               tooltip="Description language. Text visible in the image keeps its original language."),
            ],
            outputs=[io.String.Output(display_name="description")],
        )

    @classmethod
    def execute(cls, image, prompt_api, language="English"):
        return io.NodeOutput(describe_images(image, prompt_api, language))


NODE_CLASS_MAPPINGS = {"MiniMaxH3ImageCaption": MiniMaxH3ImageCaption}
NODE_DISPLAY_NAME_MAPPINGS = {"MiniMaxH3ImageCaption": "H3 Image Caption"}
