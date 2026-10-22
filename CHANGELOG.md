# Changelog

Newest first. Dates are release dates.

ComfyUI's H3 layout changed shape once so far: `PackedLayout.__init__`
dropped its `frame_count` parameter along with the restriction that
rejected any keyframe anchor other than the first or last frame. That
landed in ComfyUI 0.34.0. Every release through 0.33.4 has the older
layout. Each entry below says which of the two it works with.

## Unreleased

- **H3 Ref Prompt Builder** node id is now
  `MiniMaxH3LongVideoRefPromptBuilder`. The old id `MiniMaxH3PromptBuilder`
  belongs to the Fantastic MiniMax H3 Prompt Builder pack, and having both
  installed broke one of the two nodes. Workflows saved with the old id are
  converted when opened in the ComfyUI editor; API-format prompts must change
  `class_type` by hand.
- New **Qwen Image 2.1 Prompt Builder** node (`video/minimax`): assembles
  Qwen Image 2.1 prompts for H3 pre-production images (character sheets,
  empty scene cards, product anchors, game menus, RGBA cutouts) from an
  asset type, style, shot size, camera angle and lighting.
  The editor shows an example image for every option and, like the other
  editors, follows ComfyUI's language (Chinese or English). Connect `width` and
  `height` from Resolution Selector; the prompt names the frame wide,
  vertical or square to match, and both values pass through to the outputs.
  No LLM is needed; for a short description, turn on `refine_prompt` in the
  official Qwen Image 2.1 workflow. For a bust or waist-up shot, leave
  trousers and shoes out of the description, or the image comes out
  full-length. An empty scene card never mentions a figure: person-only
  shot sizes and angles are hidden for it, and the editor shows scene
  examples for shot size, angle and lighting.

## 0.11.1 - 2026-10-20

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.

- Prompt planning no longer stops with "LLM returned invalid speech
  start/end seconds" when the LLM lists something that is not a spoken
  line as speech. A pacing note such as "over 1 minute" read as a line,
  and any entry without a usable time range, is now dropped with a console
  warning; a quoted `<d>` line still has to be intact and timed, since
  segment boundaries are planned around it. When the prompt quotes its
  lines in `<d>`, entries without a `<d>` block are ignored.
- The timeline instructions say that a note on how long or how fast
  something runs is never speech, and that a prompt without spoken words
  returns an empty speech list.
- Timeline errors now name the offending entry's text and times, instead
  of only saying that something was invalid.

## 0.11.0 - 2026-10-19

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.

- Long Video takes `reference_videos` and `reference_audios` (up to 3 each)
  for a Ref2VA model, attached to every segment like `reference_images`. A
  reference video's soundtrack becomes the next `<Audio N>`, numbered before
  `reference_audios`. Prompt API receives the counts of pictures, videos and
  audio.
- H3 Long Video Load Latent has a new `video` output: the run's saved
  video up to the continuation point, cut on the same frame as the latent.
  Join it with Long Video's `VIDEO` using **Concatenate Video**.
- A line timed only by its shot now ends once spoken instead of filling
  the shot. H3 repeated such lines to fill the range, and the stretched
  line could push a segment end just before a cut, where the next segment
  sometimes drew a character twice. Lines with their own time range and
  sung lines keep their range.
- Prompt planning no longer stops with "LLM speech text was changed" when
  the LLM wraps an untagged line in a `<d>` block.

## 0.10.0 - 2026-10-16

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.

- H3 Long Video can continue an earlier video:
  - `context_latent` continues an H3 latent exactly, without decoding and
    re-encoding.
  - `context_video` continues any video from its last `context_length`
    frames and `audio_context_length` of sound.
  - Nothing is resized or converted: a size or frame-rate mismatch, both
    inputs at once, or `first_frame` with either stops the node with the
    reason.
- New `latent` output: the last segment's latent, for another Long Video.
- `⚠ save_latents`, on by default: saves every segment's latent, MP4 and
  `manifest.json` to `output/h3_long_video/<run>`. These files are never
  deleted automatically.
- New **H3 Long Video Load Latent** node loads a saved segment latent for
  `context_latent`. **Preview and choose…** plays the saved video on a
  timeline; the continuation point can be any point on H3's 17 frame grid
  (about every 0.71 s), not only a segment end, and the latent is cut there
  exactly. The node shows the frame it continues from, with the segment,
  size and summary. `latest` skips runs
  that saved no segment.
- The Image & Prompt **load** dialog shows the prompt's summary, larger
  pictures (click to enlarge) and a formatted read-only prompt, in
  ComfyUI's theme colors.
- `ref_image_size` (`match` / `max`) for Ref2VA reference images.
- The video keeps the last segment's rounding up to H3's frame grid, so it
  can run up to 16 frames (0.67 s) longer than `total_seconds`. Its end then
  matches the last latent exactly, so continuing from it does not jump.

## 0.9.3 - 2026-10-15

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.

- H3 Long Video refuses to run a multi-segment video without `prompt_api`
  instead of only warning: every segment would repeat the whole story.
  Single-segment videos still run without it.

## 0.9.2 - 2026-10-15

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.

- H3 Long Video warns when a multi-segment video has no `prompt_api`:
  every segment then reuses the whole prompt, so the story repeats.
- Segment planning with Prompt API:
  - A time range covering several shots (e.g. `20–45 seconds:` followed
    by three shots) is divided among those shots in order. Before, every
    shot and line got the whole range, so shots played at once, short
    lines stretched over many seconds and segments grew far past
    `segment_seconds`.
  - Lines that share one time range are spoken one after another.
  - A detail lasting "from N seconds" ends with its shot or scene instead
    of the end of the video.
  - Characters, places and narrators without a reference picture are
    defined only in segments where they appear, so they no longer show up
    in other scenes. Picture-bound subjects stay in every segment.
- Ref Prompt Builder AI rewrite keeps a line's own time, e.g. `A (6–9 s):`,
  instead of spreading the line over its whole shot.

## 0.9.1 - 2026-10-11

Requires ComfyUI 0.36.0 or newer.

- Ref Prompt Builder AI rewrite keeps dialogue in its own language with
  English output too: the prompt asks for the line's actual language tag
  instead of always `[Chinese]`, and a result whose `<d>` lines are not
  the source's own words (translated or invented) is rejected, leaving
  the original unchanged.

## 0.9.0 - 2026-10-11

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.
Workflows saved with 0.8.0 still load; the new Prompt API inputs use
their defaults.

- H3 Prompt API `model` is a dropdown of the models the API lists, with
  `default` when it lists none.
- Local LLMs: with `local_llm` (`auto` for localhost URLs), ComfyUI models
  are unloaded before each LLM request, and the new `unload_url` is called
  afterwards so the LLM frees VRAM before sampling.
- Local LLMs get JSON-schema constrained output (exact segment count and
  prompt sections; the six Builder fields), so small models no longer
  return the wrong number of segments or drop section names.
- Long Video prompt splitting: the LLM lists timed cuts, actions, sounds
  and music as well as speech, and the node calculates each segment's
  local times for them instead of leaving the subtraction to the LLM.
  Cut markers are given ready-made, and events already in progress are
  marked so later segments do not repeat their start time.
- Back-to-back timed lines no longer merge the video into one long
  segment: a segment may end up to 0.67 s before a line's stated end when
  the next line follows directly, and a line longer than a segment is
  split at its punctuation. The console warns when a segment still samples
  longer than `segment_seconds`, since it needs more VRAM.
- Clearer errors: the server's message for HTTP errors, and how many
  segment prompts the LLM actually returned.
- Long Video reuses recently planned segment prompts when the prompt,
  duration and API settings are unchanged, e.g. when only the seed
  changes. Change `variation` for new prompts.

## 0.8.0 - 2026-10-10

Requires ComfyUI 0.36.0 or newer. Restart ComfyUI after updating.

- Long Video prompt splitting also adapts prompts without timestamps:
  events are spread over the segments in story order and one-off events
  are not replayed in later segments.
- Cuts inside a segment's pinned opening are marked at their local time.
- The first segment keeps the source task prefix and first-frame
  instruction; segment prompts keep the source description language and
  use the official retention_analysis format.
- Prompt API `max_tokens` defaults to 65535; reasoning tokens count toward it.
- Ref Prompt Builder: English or Chinese AI output (English by default),
  editor text follows the ComfyUI language, `N/A` for absent music, and an
  AI rewrite that changes `<d>` dialogue is rejected.
- Full-width speaker IDs such as `（S1）` are written as `(S1)`.

## 0.7.0 - 2026-10-10

Requires ComfyUI 0.36.0 or newer for Long Video (native Concatenate Video).
Published to the Comfy Registry as `comfyui-h3-long-video` by `misaka`.
Node ids are unchanged, so uninstall the original H3 Motion Context first.

- H3 Long Video (Simple): one prompt and a total duration produce one video;
  segments are sampled with motion/audio continuation and joined.
- H3 Prompt API: optional Chat Completions settings that split the prompt
  into timed segment prompts before sampling.
- H3 Ref Prompt Builder: six-field Ref2VA editor with reference pictures and
  an optional AI rewrite.
- H3 Image & Prompt: image and prompt editor with timestamped backups.

## 0.6.2 - 2026-09-06

Requires ComfyUI 0.34.0 or newer. Use 0.3.1 on anything older.

- Chain `segments` treats a blank value as 0. Graphs saved when the
  button row was the only widget stored `""` there; after `segments` was
  added that empty string failed INT validation.
- Example workflow: both Chain nodes (fl2va and ref2va) now store
  `segments` 0 instead of that leftover blank.

## 0.6.1 - 2026-09-05

Requires ComfyUI 0.34.0 or newer. Use 0.3.1 on anything older.

- The mock harness no longer uses `importlib.import_module` (that YARA
  hit flagged 0.5.x/0.6.0). `tests/` still ships, including the smoke
  test, seam probe, freeze detect, and level step.
- Clear latents and slot-exists POST routes require Origin to match Host
  (CSRF). Latent paths must stay inside ComfyUI's output folder.

## 0.6.0 - 2026-09-03

Requires ComfyUI 0.34.0 or newer. Use 0.3.1 on anything older.

- Chain is Approve on a loop: it advances Load/Save, then queues, then
  keeps going. At Load 0 / Save 1 with no clip 1 on disk it generates
  that first clip instead of walking into a missing file. `segments` is
  how many clips that loop runs (0 = until Stop). Reset sets 0/1 and
  does not delete files. Clear latents deletes numbered chain slots;
  custom filenames are left alone.

## 0.5.1 - 2026-09-02

Requires ComfyUI 0.34.0 or newer. Use 0.3.1 on anything older.

- Example workflow updated.

## 0.5.0 - 2026-09-02

Requires ComfyUI 0.34.0 or newer. Use 0.3.1 on anything older.

#25 by feigo313 is why Load 0 is first-clip/no-context, so Motion Context
stays enabled from the first clip, and why the Chain node exists: walking
those indices with run-on-change queues twice and skips slots.

- Load Latent `clip_index` 0 is first-clip/no-context: nothing is read,
  Motion Context passes the original conditioning through, and
  `trim_frames` is 0. Leave the node enabled. The chain is Load 0 / Save 1,
  then Load 1 / Save 2. Positive indices still load that exact slot.
  The old load-newest meaning of index 0 is gone.
- H3 Motion Context Chain node: Approve advances Load/Save then queues
  once, Run/Re-roll repeats the current slot (use it instead of
  ComfyUI's Run), Chain auto-approves from the current indices, Reset
  sets 0/1 without queuing. Load, Save, and Chain must share one canvas
  group or the buttons do nothing. Button clicks do not open the node
  menu. Do not use queue "run on change" to walk indices.
- Save Latent can overwrite a slot that Load still has memory-mapped on
  Windows (os error 1224). Load copies tensors off the file first, and
  Save writes through a temp file.

## 0.4.0 - 2026-08-26

Requires ComfyUI 0.34.0 or newer. Use 0.3.1 on anything older.

ComfyUI now places keyframe anchors at any frame itself, so the two
runtime patches this pack carried are gone. Nothing in ComfyUI is
modified any more.

- `patch_layout.py` and `patch_payload.py` removed. The node builds plain
  keyframe dicts and hands them to stock code.
- `layout_contract.py` added. It proves, once before the first render,
  that anchors sit where the arithmetic says and that the pinned audio
  window is placed literally from a fractional, negative anchor index.
  No stock node can produce such an index, so nothing upstream tests it,
  and an integer cast added later would move the pinned sound silently.
  If a check fails the node refuses and names what moved.
- The pinned audio is a keyframe rather than a reference block. A Ref2VA
  graph's reference list is left untouched.
- Add Guide for MiniMax H3 anchors survive alongside a chained head,
  including ones carrying their own audio. Guides landing inside the
  pinned head are dropped with a warning, as `first_frame` anchors are.
- Other packs may patch the layout without this one standing down, since
  it no longer competes for that code. If it finds the constructor
  wrapped it says who by and checks the behaviour anyway.
- Anchor and audio window coordinates are identical to 0.3.1, verified
  against the real upstream layout on both shapes.

## 0.3.1 - 2026-08-14

Works with both H3 layouts.

Fixed the crash on the newer layout, reported in #12 by javawock7618 and
#8 by azra1l. The patch had passed `frame_count` unconditionally, so its
self-test raised `TypeError` and the node refused to run.

- The patch reads the layout constructor's signature and adapts, rather
  than assuming either shape. Verified against the real upstream file on
  both: identical anchor and audio window coordinates to the last bit.
- Keyframe audio latents are no longer dropped from the payload. The
  newer layout lets a keyframe carry audio of its own, and rebuilding the
  list from references alone filled every audio conditioning row with the
  wrong content.
- Pinned anchors pair with the correct rows when a stock anchor that
  carries audio but no picture shares the graph.
- The mixed keyframe guard is retired on the newer layout, where stock
  compensates untagged keyframes for reference blocks itself. A Ref2VA
  graph carrying a stock anchor is now supported rather than refused.
- The test harness fakes both layout shapes.

## 0.3.0 - 2026-08-11

Works with the older H3 layout only. Refuses to run on the newer one.

- **Seam Probe node.** Measures join quality inline in the graph: lag,
  correlation, RMS step and floor level step across the join. Passes
  clip B through unchanged so it can sit inline without rewiring.
- **last_frame passthrough.** An fl2va graph's own anchors used to be
  replaced outright. A last-frame anchor now survives a chained head,
  tagged so it gets the same reference compensation as the pinned run.
  Anchors falling inside the pinned head are dropped with a warning,
  since the pinned run already decides those frames.
- Conditioning carrying keyframes resolved against a different clip
  length is refused rather than rendered at the wrong frame.

## 0.2.0 - 2026-08-09

Works with the older H3 layout only. First release published to the
ComfyUI registry.

- **Reference mode support.** `patch_layout.py` was rewritten to locate
  reference blocks by segment table rather than by recomputing cursor
  arithmetic, which made multiple reference blocks work cleanly. Ref2VA
  graphs can carry their own image, video and audio references alongside
  a chained head.
- **Latent picture path.** The pinned run is sliced straight out of the
  previous clip's latent, skipping the decode and re-encode round trip
  that dulls the picture a little more at every link.
- **Patches install on first use, not at import.** Having the pack in
  `custom_nodes` now changes nothing until a Motion Context node
  actually runs.
- **Coexistence detection.** A second copy of the patch, vendored into
  another pack, recognises the first and stands down instead of
  wrapping it.
- The payload patch is gated on this pack's own markers, so unrelated H3
  graphs stay bit-identical to stock.
- Two settings exposed; everything with only one correct answer was
  removed from the UI.
- `freeze_detect.py` and `level_step.py` added to the measurement
  scripts.
- The example workflow was replaced with an fl2va / ref2va one.

## Initial release - 2026-08-06

Works with the older H3 layout only. Not published to the registry; no
version number, as `pyproject.toml` came later.

Clip chaining for MiniMax H3 with audio continuation rather than
imitation. Four nodes: Motion Context, Trim, Save Latent, Load Latent.
The pinned audio window is placed so it ends at the join and reaches
backwards, which is what makes the model continue a soundtrack instead
of starting something that merely resembles it.
