# H3 Long Video

[简体中文](README_zh-CN.md)

Generate MiniMax H3 videos of any length from one prompt and a total duration. Based on [NikoDemon80/ComfyUI-H3-Motion-Context](https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context).

- **One prompt, any length**: the video is sampled in segments that continue each other's picture and sound, then joined at 24 fps.
- **Continue any video**: from a saved latent at any point (exact, no re-encoding) or from a video file.
- **Prompt editors**: H3 Image & Prompt with backups, and H3 Ref Prompt Builder for the six Ref2VA sections.
- **Cloud or local LLM** splits the story into segment prompts with the right timing.

## Install

Install **H3 Long Video** from ComfyUI Manager, or clone it into `ComfyUI/custom_nodes`, then restart ComfyUI and refresh the browser.

```sh
git clone https://github.com/ooizj/ComfyUI-H3-Long-Video.git comfyui-h3-long-video
```

- Requires **ComfyUI 0.36.0** or newer (native H3 and **Concatenate Video**).
- **Uninstall the original H3 Motion Context first**: both packs register the same node ids.

## Quick start

[![H3 Long Video (Simple) example](docs/images/long-video-connections.png)](docs/images/long-video-connections.png)

1. Open an example workflow and select your models and images:
   - [H3 Long Video - Simple](example_workflows/H3%20Long%20Video%20-%20Simple.json): type the prompt directly; load the first frame and references with image nodes.
   - [H3 Long Video - Ref Prompt Builder](example_workflows/H3%20Long%20Video%20-%20Ref%20Prompt%20Builder.json): manage references and the six prompt sections in the editor.
2. Connect **H3 Prompt API** to `prompt_api` and enter your API key or local server. **Required when the video needs more than one segment**; see [Why split the prompt?](#why-split-the-prompt).
3. Write the prompt for the whole video, set `total_seconds` and run. `VIDEO` goes to **Save Video**.

The screenshot uses `total_seconds=14` and `segment_seconds=7`: the node works out the segments itself. Shorter segments use less VRAM per sampling pass but add encoding, decoding and continuation overhead, so they are not necessarily faster.

<details>
<summary>Notes on the example workflows</summary>

The examples keep LoRA/attention settings inside their model subgraphs; adjust them to your installation. The Builder example includes a resolution selector; if you do not have it, set Long Video's `width` and `height` directly. API keys are cleared in the published files.

</details>

## H3 Long Video (Simple)

| Input / output | Use |
| --- | --- |
| `prompt`, `total_seconds` | The whole story and its duration. |
| `prompt_api` | Splits the prompt into segment prompts. Required for more than one segment. |
| `reference_images` | Optional pictures in `<Picture N>` order, used in every segment. Use a Ref2VA model with references, or a compatible FL2VA/T2VA model without them. |
| `reference_videos` / `reference_audios` | Optional Ref2VA references, up to 3 each, used in every segment: `<Video N>` and `<Audio N>`, such as a voice. A reference video's soundtrack takes the next `<Audio N>` before `reference_audios`. Other frame rates are resampled to 24 fps. |
| `first_frame` | Optional opening image for the first segment. |
| `context_latent` / `context_video` | Optional: continue an earlier video. See [Continue a video](#continue-a-video). |
| `VIDEO` | The finished video. |
| `prompt_preview` | The actual segment prompts and timing windows; connect a text display to check them. |
| `latent` | The last segment's latent, for another Long Video's `context_latent`. |

> **⚠ `save_latents` is on by default.** Every segment's latent, MP4 and `manifest.json` go to `output/h3_long_video/<run>` so you can continue from them later. **They are never deleted automatically; delete old runs yourself.**

<details>
<summary>All parameters</summary>

| Parameter | Default | Purpose |
| --- | --- | --- |
| `total_seconds` | `30` | Final duration. The video can run up to 16 frames (0.67 s) longer, rounded up to H3's frame grid so its end can be continued exactly. |
| `segment_seconds` | `15` | Target sampled duration per segment, including overlap; frame alignment and dialogue protection change actual lengths. |
| `width` / `height` | `960` / `544` | Output size, rounded up to multiples of 32. |
| `seed` | `0` | Segment seeds are `seed + segment index`, starting at 0. |
| `steps` | `20` | Sampling steps per segment. |
| `sampler_name` / `scheduler` | `res_multistep` / `simple` | Sampler and schedule. |
| `context_length` | `22` | Video overlap in frames: `5`, `22`, `39` or `56`. |
| `audio_context_length` | `24` | Audio continuation window in video frames; `0` follows the video overlap. |
| `tiled_decode` | `true` | Tiled decoding to reduce decoding memory. |
| `ref_image_size` | `match` | Ref2VA reference size: `match` scales references to the video's pixel area; `max` keeps up to a 2048 px short edge for best identity but can sample several times slower. Needs a ComfyUI whose H3 reference node has this option. |
| `⚠ save_latents` | `true` | Saves every segment's latent, MP4 and `manifest.json`; see above. |

</details>

## Continue a video

Connect **one** of `context_latent` or `context_video`. The new video starts where the source ends, and `VIDEO` contains only the new part: join the two with **Concatenate Video**. Write the prompt for the new part only, starting from 0 seconds.

| | From a saved latent (`context_latent`) | From a video (`context_video`) |
| --- | --- | --- |
| Source | A Long Video run with `save_latents` on | Any video, exactly `width` x `height` at 24 fps |
| Where | Any point, about every 0.71 s | Any frame |
| Quality | Exact: no decoding or re-encoding | The last frames are re-encoded |

### From a saved latent

[![Continue from a saved latent with H3 Long Video Load Latent](docs/images/long-video-continue.png)](docs/images/long-video-continue.png)

1. Add **H3 Long Video Load Latent** and connect `latent` to Long Video's `context_latent`.
2. Click **Preview and choose…**: pick a saved video, play it or drag the timeline, and click **Continue from …**. The node then shows the frame it continues from.
3. Set `width`/`height` to the saved video's size.
4. Join Load Latent's `video` (the saved video up to the continuation point) and Long Video's `VIDEO` with **Concatenate Video**.

By default it continues the end of the latest saved video. Points sit on H3's 17-frame latent grid, about every 0.71 s; the picker snaps to the nearest one, and **Previous / Next point** step through them. Another Long Video's `latent` output also works for `context_latent`.

### From a video

[![Continue from a video with Trim Video](docs/images/long-video-continue-video.png)](docs/images/long-video-continue-video.png)

1. **Load Video** → **Trim Video (Advanced)** → Long Video's `context_video`. Trimming is optional: set the end frame to continue from earlier than the end.
2. Set `width`/`height` to the video's size.
3. The last `context_length` frames and `audio_context_length` of sound are pinned.

<details>
<summary>Rules and errors</summary>

- Nothing is resized or converted: a size or frame-rate mismatch stops the node with the reason. Convert other videos first, for example `ffmpeg -i in.mp4 -vf "fps=24,scale=960:544:force_original_aspect_ratio=increase,crop=960:544" out.mp4`.
- Connecting both inputs, or `first_frame` together with either, is refused.
- A `context_latent` must be a complete H3 audio/video latent or one cut by Load Latent; a size mismatch is refused because a latent cannot be resized.

</details>

## Why split the prompt?

Each segment is sampled separately, with its own time starting at zero. Giving every segment the whole story repeats opening actions and dialogue, or mixes up whole-video times with segment times. **So a video that needs more than one segment requires `prompt_api`; without it the node stops with an error.** For a single segment, set `total_seconds` no higher than `segment_seconds`.

Write explicit whole-video time ranges and dialogue in your prompt; without them, the story is spread over the segments in order.

<details>
<summary>How splitting works</summary>

1. The LLM lists the prompt's timed dialogue, cuts, actions, sounds and music.
2. The node places segment boundaries without cutting a spoken line, then converts whole-video times to each segment's local times, accounting for overlap.
3. The LLM adapts the full prompt to each segment using these times, in the source's description language.

Segment boundaries:

- Between lines that follow each other directly, a segment may end up to 0.67 s before the earlier line's stated end.
- A line longer than a segment is split at its punctuation, with time in proportion to the text.
- A line timed only by its shot ends once spoken (about 4 Chinese characters or 2.5 words a second) instead of filling the shot, which H3 fills by repeating the line. Lines with their own time range, such as `Narrator (6–15 s):`, and sung lines keep their range.
- When no cut point is close enough, the segment becomes longer than `segment_seconds`, and the console warns because it needs more VRAM.

| Situation | Does Long Video call the API? |
| --- | --- |
| `prompt_api` disconnected and multiple segments needed | Does not run; connect `prompt_api`. |
| Only one segment needed, even with `prompt_api` connected | No; uses the original prompt. |
| `prompt_api` connected and multiple segments needed | Yes; analyzes timing, then rewrites segment prompts. |
| Same prompt, duration and API settings as a recent run, e.g. only the seed changed | No; reuses the planned segment prompts. Change Prompt API's `variation` for new ones. |

Builder's AI buttons are separate and call their connected API when clicked. Omitting timestamps does not disable API calls.

</details>

### H3 Prompt API: cloud or local models

`model` lists the models reported by the API's `/models` endpoint (refreshed when `api_url` or `api_key` changes, or with **Refresh model list**; `default` when none are listed). Cloud APIs and local servers (llama.cpp / llama-swap, Ollama, LM Studio) work the same way.

Prompt splitting needs a capable model. In our tests a local 27B dense model wrote correct segment times for timed dialogue, a cut and music, and DeepSeek did for timed dialogue; a 35B-A3B MoE model sometimes dropped a cut, and 9B models often broke dialogue rules.

<details>
<summary>Local LLMs and VRAM</summary>

A local LLM shares the GPU with H3. `local_llm` (advanced, `auto`) treats an `api_url` on this computer (`localhost`, `127.0.0.1`) as local: ComfyUI models are unloaded before each LLM request, and after planning or an AI rewrite the node POSTs `unload_url` so the server frees its VRAM before sampling. For llama-swap use `http://127.0.0.1:8081/api/models/unload`; leave `unload_url` empty for a server that unloads idle models by itself.

With `json_mode` on, requests to a local LLM carry a JSON schema, so llama.cpp, Ollama and LM Studio can only produce the expected structure: one object per segment with one field per prompt section, or the six Builder fields. The node writes the section names itself.

</details>

<details>
<summary>Prompt logs</summary>

With `log_prompts` on, logs go to `output/h3_prompt_logs/` (TXT + JSON): `*_builder` records editor input/output, `*_planner` API planning, and `*_video` the final segment prompts and settings before sampling. Builder logging also needs its connected API's `log_prompts` on. `prepared` means ready for sampling only. The key mask hides the key on screen, not in the saved workflow: clear key fields before sharing workflows.

</details>

## H3 Image & Prompt

[![H3 Image & Prompt example](docs/images/image-and-prompt.png)](docs/images/image-and-prompt.png)

Pictures and a prompt in one node (`video/minimax`). Add, drop or paste pictures, reorder them with the arrows (`<Picture N>` references in the prompt follow), and click a thumbnail to insert its reference. Connect `prompt` and `reference_images` to Long Video.

<details>
<summary>Backup and load</summary>

- **backup** saves the original pictures, `prompt.txt` and a manifest (image order, sources, hashes) to a new timestamped folder in `output/h3_prompt_backups`. Backups never overwrite each other, and queue runs never create one.
- **load** lists backups newest first with thumbnails and each prompt's summary. Select one to see its pictures (click to enlarge) and the formatted prompt, then click **Load selected backup**. Loaded pictures come from the backup copies, so the original uploads are not needed.
- Pictures of different sizes are padded, not cropped. A prompt without pictures works too.

</details>

## H3 Ref Prompt Builder

[![H3 Ref Prompt Builder example](docs/images/ref-prompt-builder.png)](docs/images/ref-prompt-builder.png)

Edits reference pictures and the six Ref2VA prompt sections (`video/minimax`). Manual editing needs no API.

1. Add, drop or paste pictures; they become `<Picture 1>`, `<Picture 2>`, etc. Drag cards or use the arrows to reorder, and references in the text update. **换** replaces a picture and keeps its number.
2. Fill the six fields. Click a thumbnail to insert a reference, or type `<Pic` / `<Sub` and complete with the arrow keys and Tab/Enter. Bind each `<Subject N>` to its source pictures explicitly; subject and picture numbers need not match.
3. Connect `prompt` and `reference_images` to Long Video, check the preview and run.

<details>
<summary>The six fields</summary>

| Field | Content |
| --- | --- |
| `subject_definitions` | Subject features and image sources, e.g. `<Subject 1> is the man wearing a dark shirt in <Picture 1>.` |
| `summary` | Main events, prefixed with `[reference generation]`, or `[keyframe completion + reference generation]` with a first frame/keyframe. |
| `retention_analysis` | Identity, clothing, environment and other reference features to preserve. |
| `detailed_description` | Composition, actions, camera, dialogue and local sound effects, timed against the whole final video. |
| `overall_soundscape` | Shared ambience and overall sound balance. |
| `non_diegetic_music` | Music instructions, or `N/A` for no music. |

Use `[Shot 1]` for the opening and `[Shot 2] At 00:06.000, ...` for a cut at six seconds; an event range such as `0–3 seconds: ...` is not a cut. Keep the prompt's total duration equal to Long Video's `total_seconds`.

</details>

<details>
<summary>Import, AI editing and languages</summary>

- **Import a full prompt:** **Split by headings** splits text by the six English field headings (Markdown headings or colons), without an API. Use **AI to six fields** for free-form text, or **Fill example** for an editable example.
- **AI editing:** connect H3 Prompt API to Builder's `prompt_api`. Only **AI rewrite** and **AI to six fields** call the API; they queue prompt processing without starting video generation. Results refill the fields and can be edited or undone; if you edited the original while waiting, click **Apply AI result** to apply it.
- **AI output language:** the English / 中文 switch, English by default (the official H3 Ref2VA format). Dialogue, lyrics and on-screen text keep their language. The choice is saved with the node and becomes the default for new nodes.
- **AI reads reference images:** on by default; sends compressed JPEG copies (1024 px long edge) to a vision model. Turn it off for text-only models. Video generation uses the source pictures.
- **Interface language:** editors, node descriptions and tooltips follow ComfyUI's language: Chinese for Chinese locales, English otherwise.

</details>

[GPL-3.0 license](LICENSE)
