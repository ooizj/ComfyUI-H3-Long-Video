"""Image generation prompts written from pictures by the vision model behind H3 Prompt API."""

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
MODES = {
    "full_prompt": """Describe the supplied image as a text-to-image prompt that recreates it. Output only the prompt,
as one plain paragraph without headings, lists or Markdown.
Open with the style or medium, such as photograph, 3D render or anime illustration, the shot size and the camera angle.
Cover the subjects and their count, appearance, build, hairstyle, clothing with colours and materials, pose,
expression and gaze; props; and the setting from foreground to background. Say where each subject and each
block of text sits in the frame (left, centre or right; top or bottom; foreground or background), how much
of the frame it fills and which way it faces. Close with the lighting direction and quality, the time of day
and the colour palette.""",
    # Qwen Image 2.1 Prompt Builder writes "The image is a <style> <shot> of <subject>, ..." and adds the rest from its presets.
    "subject_only": """Describe the subjects of the supplied image for a prompt template that adds the style, shot size,
camera angle and lighting itself. Output only one noun phrase, such as "a young woman with ..., wearing ...,
standing in ...", without "The image shows", headings or Markdown.
Cover the subjects and their count, appearance, hairstyle, clothing with colours and materials, pose,
expression and gaze; props; and the setting. Leave out the style or medium, shot size, camera angle,
composition, lighting and image quality.""",
}
_RULES = """Describe only what can be seen. Do not guess names, identities, relationships or a story, and state
unclear details only as far as they can be confirmed. Name every distinctive feature, such as a tail, wings,
a thin or muscular build, or a wiry, curly or sleek coat, and look closely at colours before naming them.
When the image shows one subject several times, as in a turnaround sheet or side-by-side panels, say it is
the same subject and describe each view, instead of counting separate subjects.
Copy all visible text verbatim in its original language, including small captions and seals."""
LANGUAGES = {"English": "Write in English.", "中文": "Write in Simplified Chinese."}


def system_prompt(mode, language):
    return f"{MODES[mode]}\n{_RULES}\n{LANGUAGES[language]}"


def save_log(prompts, mode, language, model, elapsed, responses, requests_log, api_key, error):
    report = {"operation": "image_to_prompt", "model": model, "mode": mode, "language": language,
              "elapsed_seconds": round(elapsed, 3), "prompts": prompts, "responses": responses, "requests": requests_log,
              "error": f"{type(error).__name__}: {error}" if error else None,
              "status": "failed" if error else "ok"}
    text = (f"Model: {model}\nElapsed: {elapsed:.3f}s\nMode: {mode}\nLanguage: {language}\n\n"
            f"{prompt_trace_text(requests_log, responses)}")
    if error:
        text += f"\n\nError: {report['error']}"
    return write_prompt_log(new_prompt_log_path("image_prompt"), report, text, api_key)


def describe_images(images, config, mode="full_prompt", language="English"):
    key = config.get("api_key", "").strip()
    endpoint, headers = chat_endpoint(config["api_url"]), {"Authorization": f"Bearer {key}"} if key else {}
    prompts, responses, requests_log = [], [], []
    started = time.monotonic()
    try:
        for index, image in enumerate(images):
            stage = f"image {index + 1}"
            url, jpeg_bytes = jpeg_url(Image.fromarray(np.clip(255.0 * image.cpu().numpy(), 0, 255).astype(np.uint8)))
            payload = {
                "model": config["model"], "max_tokens": config.get("max_tokens", 4096), "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt(mode, language)},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": url}},
                                                 {"type": "text", "text": "Describe this image."}]},
                ],
            }
            _LOG.info("Image to Prompt: %s, %s, %.1f KiB JPEG", payload["model"], stage, jpeg_bytes / 1024)
            requests_log.append(prompt_request_log(payload, stage))
            data = request_chat(endpoint, payload, headers, config.get("timeout_seconds", 600), free_vram=config.get("free_vram", False))
            text = (response_message(data, responses, stage).get("content") or "").strip()
            if not text:
                raise RuntimeError("AI returned an empty description. Use a vision model, or raise max_tokens for a reasoning model.")
            prompts.append(text)
        return "\n\n".join(prompts)
    finally:
        release_llm(config.get("free_vram", False), config.get("unload_url", ""))
        if config.get("log_prompts", True):
            save_log(prompts, mode, language, config["model"], time.monotonic() - started,
                     responses, requests_log, config.get("api_key", ""), sys.exception())


class ImageToPrompt(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="PromptAPIImageToPrompt", display_name="Image to Prompt",
            category="video/minimax",
            description="Write an image generation prompt from a picture with the vision model of the connected H3 Prompt API. "
                        "Connect prompt to any text prompt input, or to prompt of Qwen Image 2.1 Prompt Builder with mode subject_only.",
            inputs=[
                io.Image.Input("image", tooltip="Each image of a batch is described separately; prompts are separated by a blank line."),
                io.Custom("H3_PROMPT_API").Input("prompt_api", tooltip="Its model must accept images."),
                io.Combo.Input("mode", options=list(MODES), default="full_prompt",
                               tooltip="full_prompt: a complete prompt with setting, composition, camera, lighting and style, for any text-to-image model. "
                                       "subject_only: people, objects and setting without style, shot, camera or lighting, for prompt of Qwen Image 2.1 Prompt Builder, whose presets add those."),
                io.Combo.Input("language", options=list(LANGUAGES), default="English",
                               tooltip="Prompt language. Text visible in the image keeps its original language."),
            ],
            outputs=[io.String.Output(display_name="prompt")],
        )

    @classmethod
    def execute(cls, image, prompt_api, mode="full_prompt", language="English"):
        return io.NodeOutput(describe_images(image, prompt_api, mode, language))


NODE_CLASS_MAPPINGS = {"PromptAPIImageToPrompt": ImageToPrompt}
NODE_DISPLAY_NAME_MAPPINGS = {"PromptAPIImageToPrompt": "Image to Prompt"}
