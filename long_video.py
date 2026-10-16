"""Generate and join an H3 chain in one execution."""

from fractions import Fraction
import inspect
import logging
import math
import os
import tempfile
import time
import uuid

import comfy.model_management
import comfy.samplers
import comfy.utils
import folder_paths
import node_helpers
import nodes
from comfy_api.latest import InputImpl, Types, io
from comfy_execution.utils import get_executing_context
from comfy_extras.nodes_audio import VAEDecodeAudio
from comfy_extras.nodes_custom_sampler import (
    BasicGuider, BasicScheduler, KSamplerSelect, RandomNoise, SamplerCustomAdvanced,
)
from comfy_extras.nodes_minimax_h3 import (
    EmptyMiniMaxH3LatentAV, MiniMaxH3AddGuide, MiniMaxH3ImageToVideo,
    MiniMaxH3ReferenceToVideo, align_frame_count,
)

from .nodes import (
    AUDIO_HZ, FPS, MiniMaxH3MotionContext, MiniMaxH3MotionContextTrim,
    _steps_for_frames, _streams_from_latent, _video_from_latent,
)
from .segment_store import (
    folder_size, new_run_directory, save_segment_latent, segment_file, write_manifest,
)
from .prompt_planner import prompt_preview, segment_schedule, split_prompts
from .prompt_log import new_prompt_log_path, write_prompt_log

_LOG = logging.getLogger("h3_motion_context")


class _LongVideoProgress:
    def __init__(self, total):
        self.bar = comfy.utils.ProgressBar(total)
        self.original_hook = self.bar.hook
        self.context = get_executing_context()
        self.hook = self.update
        self.active = False
        self.completed = 0
        self.units = 0
        self.track = False

    def __enter__(self):
        self.bar.update_absolute(0)
        self.active = self.original_hook is not None and self.context is not None
        if self.active:
            comfy.utils.set_progress_bar_global_hook(self.hook)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.active = False
        if comfy.utils.PROGRESS_BAR_HOOK is self.hook:
            comfy.utils.set_progress_bar_global_hook(self.original_hook)

    def begin(self, units, track=False):
        self.units = units
        self.track = track

    def finish(self):
        self.completed += self.units
        self.units = 0
        self.track = False
        self.bar.update_absolute(self.completed)

    def update(self, value, total, preview, prompt_id=None, node_id=None):
        # Native samplers and VAEs report their own 0-100% to the same node.
        if (self.active and get_executing_context() == self.context
                and prompt_id in (None, self.context.prompt_id)
                and node_id in (None, self.context.node_id)):
            fraction = min(1.0, max(0.0, value / total)) if self.track and total > 0 else 0.0
            current = max(self.bar.current, self.completed + self.units * fraction)
            self.bar.update_absolute(current, preview=preview)
        else:
            kwargs = {"node_id": node_id}
            if prompt_id is not None:
                kwargs["prompt_id"] = prompt_id
            self.original_hook(value, total, preview, **kwargs)


def plan_segments(total_seconds, segment_seconds, context_length, continuing=False):
    """continuing: the first segment also continues an existing clip (context_latent/context_video)."""
    if not math.isfinite(total_seconds) or total_seconds <= 0:
        raise ValueError("Total duration must be a positive number of seconds.")
    if not math.isfinite(segment_seconds) or segment_seconds <= 0:
        raise ValueError("Segment duration must be a positive number of seconds.")
    remaining = max(1, round(total_seconds * FPS))
    clip_frames = align_frame_count(max(5, round(segment_seconds * FPS), context_length + 1))
    tail_limit = align_frame_count(clip_frames + FPS)
    plan = []
    while remaining:
        overlap = context_length if plan or continuing else 0
        tail_frames = align_frame_count(max(5, remaining + overlap))
        # Allow one extra second, aligned to H3's grid, to avoid a tiny last clip.
        length = tail_frames if tail_frames <= tail_limit else clip_frames
        keep = min(remaining, length - overlap)
        plan.append((length, overlap, keep))
        remaining -= keep
    return plan


def check_context_latent(latent, width, height, context_length, audio_context_length):
    """Refuse a context_latent that cannot be continued exactly, before prompt planning starts."""
    try:
        parts = _streams_from_latent(latent)
        video = _video_from_latent(latent)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError("H3 Long Video: context_latent is not an H3 audio/video latent. Connect the latent output of "
                         "H3 Long Video, H3 Long Video Load Latent or an H3 sampler.") from None
    if len(parts) < 2:
        raise ValueError("H3 Long Video: context_latent has no audio stream. Connect the full audio/video latent of an H3 clip.")
    latent_width, latent_height = int(video.shape[4]) * 16, int(video.shape[3]) * 16
    if (latent_width, latent_height) != (width, height):
        raise ValueError(f"H3 Long Video: context_latent is {latent_width}x{latent_height}, but width/height are "
                         f"{width}x{height}. A latent cannot be resized: set width to {latent_width} and height to "
                         f"{latent_height}.")
    steps, needed = int(video.shape[2]), _steps_for_frames(context_length)
    if steps < needed or (steps - needed) % 5:
        raise ValueError(f"H3 Long Video: context_latent has {steps} latent steps, which do not end on H3's frame grid "
                         f"for context_length {context_length}. Use the complete latent of a generated clip, not a cut "
                         "one, or connect context_video instead.")
    audio_steps = int(parts[1].shape[-1])
    wanted = round((audio_context_length or context_length) / FPS * AUDIO_HZ)
    if audio_steps < wanted:
        raise ValueError(f"H3 Long Video: context_latent holds {audio_steps / AUDIO_HZ:.2f}s of audio, shorter than "
                         f"audio_context_length ({audio_context_length or context_length} frames). Lower "
                         "audio_context_length.")


def context_video_tail(video, width, height, context_length, audio_context_length):
    """Return the last context_length frames and the audio of context_video, refusing a video that does not match."""
    video_width, video_height = video.get_dimensions()
    if (video_width, video_height) != (width, height):
        raise ValueError(f"H3 Long Video: context_video is {video_width}x{video_height}, but width/height are "
                         f"{width}x{height}. Set width/height to the video's size; H3 needs multiples of 32, so "
                         "resize or crop the video first if its size is not.")
    rate = Fraction(video.get_frame_rate())
    if rate != FPS:
        raise ValueError(f"H3 Long Video: context_video runs at {float(rate):.3f} fps; H3 runs at {FPS} fps. Convert "
                         f"the video to {FPS} fps first.")
    audio_frames = audio_context_length or context_length
    seconds = max(context_length, audio_frames) / FPS
    duration = float(video.get_duration())
    if duration * FPS < context_length:
        raise ValueError(f"H3 Long Video: context_video has {duration:.2f}s of frames, fewer than context_length "
                         f"({context_length} frames).")
    # Decode only the end of a long video; one extra second covers keyframe seeking.
    start = max(0.0, duration - seconds - 1.0)
    tail = video.as_trimmed(start_time=start) if start > 0 and hasattr(video, "as_trimmed") else None
    components = (tail or video).get_components()
    images = components.images
    if images.shape[0] < context_length:
        raise ValueError(f"H3 Long Video: decoded {images.shape[0]} frames from the end of context_video, fewer than "
                         f"context_length ({context_length}).")
    audio = components.audio
    if audio is None or audio["waveform"].shape[-1] == 0:
        _LOG.warning("H3 Long Video: context_video has no audio track, so only its picture is continued.")
        audio = None
    elif audio["waveform"].shape[-1] / audio["sample_rate"] < audio_frames / FPS - 1 / FPS:
        raise ValueError(f"H3 Long Video: context_video audio is shorter than audio_context_length ({audio_frames} "
                         "frames). Lower audio_context_length.")
    return images[-context_length:].clone(), audio


class MiniMaxH3LongVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3LongVideo",
            display_name="H3 Long Video (Simple)",
            category="video/minimax",
            description="Generate short H3 clips, continue their motion and audio, and return one video. Connect VIDEO to Save Video. Requires ComfyUI's native Concatenate Video support. Use an FL2VA/T2VA model without references, or a Ref2VA model with reference images.",
            inputs=[
                io.Model.Input("model"),
                io.Clip.Input("clip"),
                io.Vae.Input("vae"),
                io.Vae.Input("audio_vae"),
                io.String.Input("prompt", default="", multiline=True, dynamic_prompts=True, optional=True,
                    tooltip="Write one complete H3 prompt for the entire video, with final-video timestamps if wanted. prompt_api adapts it to each sampled segment."),
                io.Float.Input("total_seconds", default=30.0, min=0.1, max=86400.0, step=0.1, optional=True,
                    tooltip="Final duration at 24 fps. Segment count is calculated automatically from segment_seconds and context_length. The video can run up to 16 frames (0.67 s) longer, rounded up to H3's frame grid so its end can be continued exactly."),
                io.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, control_after_generate=True, optional=True),
                io.Int.Input("width", default=960, min=32, max=nodes.MAX_RESOLUTION, step=32, advanced=True, optional=True),
                io.Int.Input("height", default=544, min=32, max=nodes.MAX_RESOLUTION, step=32, advanced=True, optional=True),
                io.Float.Input("segment_seconds", default=15.0, min=0.1, max=150.0, step=0.1, advanced=True, optional=True,
                    tooltip="Target duration sampled per segment, INCLUDING overlap. Use 15 seconds when memory allows; shorter segments add encoding, decoding and continuation overhead. Prompt API may rebalance or lengthen clips to keep timed speech intact. The last segment may extend by about one second, rounded up to H3's frame grid."),
                io.Int.Input("steps", default=20, min=1, max=10000, advanced=True, optional=True),
                io.Combo.Input("sampler_name", options=comfy.samplers.SAMPLER_NAMES, default="res_multistep", advanced=True, optional=True),
                io.Combo.Input("scheduler", options=comfy.samplers.SCHEDULER_NAMES, default="simple", advanced=True, optional=True),
                io.Combo.Input("context_length", options=["22", "5", "39", "56"], default="22", advanced=True, optional=True),
                io.Int.Input("audio_context_length", default=24, min=0, max=240, advanced=True, optional=True),
                io.Boolean.Input("tiled_decode", default=True, advanced=True, optional=True,
                    tooltip="Use the stock tiled video VAE decoder to reduce decoding memory."),
                io.Image.Input("first_frame", optional=True,
                    tooltip="Optional opening image, used only for the first segment."),
                io.Latent.Input("context_latent", optional=True,
                    tooltip="Continue an earlier H3 clip exactly, from H3 Long Video Load Latent or the latent output of another Long Video. Its size must equal width/height. The new video starts where it ends; join them with Concatenate Video. Connect either this or context_video, not both."),
                io.Video.Input("context_video", optional=True,
                    tooltip="Continue any video: its last context_length frames and audio_context_length of sound are pinned. It must be exactly width x height at 24 fps; nothing is resized or converted. The output contains only the new part; join them with Concatenate Video. Connect either this or context_latent, not both."),
                io.Image.Input("reference_images", optional=True,
                    tooltip="Optional image batch for a Ref2VA model. Every image is a reference: <Picture 1>, <Picture 2>, etc. Use Image Batch to combine images. References stay attached throughout the chain."),
                io.Custom("H3_PROMPT_API").Input("prompt_api", optional=True,
                    tooltip="Connect H3 Prompt API to split the prompt into segment prompts. Required when the video needs more than one segment; a single-segment video runs without it and skips the API."),
                io.Boolean.Input("log_prompts", default=True, optional=True, advanced=True,
                    tooltip="Save the input and final per-segment prompts, seeds and task ID to output/h3_prompt_logs before sampling, including when Prompt Builder is cached. Prompt API log_prompts controls AI planning logs separately."),
                io.Combo.Input("ref_image_size", options=["match", "max"], default="match", advanced=True, optional=True,
                    tooltip="Reference image size for a Ref2VA model. 'match' scales references to the video's pixel area; 'max' keeps up to a 2048 px short edge for best identity, but sampling can be several times slower. Needs a ComfyUI version whose H3 reference node has ref_image_size."),
                io.Boolean.Input("save_latents", display_name="⚠ save_latents", default=True, optional=True,
                    tooltip="⚠ Saves every segment's latent and MP4 plus manifest.json to output/h3_long_video/<run>. These files are never deleted automatically and use disk space on every run; delete old runs yourself. Load them with H3 Long Video Load Latent to continue a video."),
            ],
            outputs=[io.Video.Output(), io.String.Output(display_name="prompt_preview"),
                     io.Latent.Output(display_name="latent", tooltip="Last segment's latent, for another Long Video's context_latent.")],
        )

    @classmethod
    def execute(cls, model, clip, vae, audio_vae, prompt="", total_seconds=30.0, seed=0,
                width=960, height=544, segment_seconds=15.0, steps=20,
                sampler_name="res_multistep", scheduler="simple", context_length="22",
                audio_context_length=24, tiled_decode=True, first_frame=None, context_latent=None,
                context_video=None, reference_images=None, prompt_api=None, log_prompts=True,
                ref_image_size="match", save_latents=True):
        if not hasattr(InputImpl, "VideoFromList"):
            raise RuntimeError("H3 Long Video needs native Concatenate Video support. Update ComfyUI to use this node.")
        width = max(32, math.ceil(width / 32) * 32)
        height = max(32, math.ceil(height / 32) * 32)
        if context_latent is not None and context_video is not None:
            raise ValueError("H3 Long Video: connect either context_latent or context_video, not both.")
        continues = "latent" if context_latent is not None else "video" if context_video is not None else None
        if continues and first_frame is not None:
            raise ValueError(f"H3 Long Video: context_{continues} already supplies the opening frames, so first_frame "
                             "cannot be used with it. Disconnect first_frame.")
        ref_size = {}
        if ref_image_size == "max" and reference_images is not None:
            if "ref_image_size" not in inspect.signature(MiniMaxH3ReferenceToVideo.execute).parameters:
                raise RuntimeError("H3 Long Video: this ComfyUI's H3 reference node has no ref_image_size option. "
                                   "Update ComfyUI or set ref_image_size to match.")
            ref_size = {"ref_image_size": "max"}
        context_frames = context_audio = None
        if continues == "latent":
            check_context_latent(context_latent, width, height, int(context_length), audio_context_length)
        elif continues == "video":
            context_frames, context_audio = context_video_tail(
                context_video, width, height, int(context_length), audio_context_length)
        plan = plan_segments(total_seconds, segment_seconds, int(context_length), continuing=bool(continues))
        schedule = segment_schedule(plan)
        prompts = [prompt] * len(plan)
        reference_count = len(reference_images) if reference_images is not None else 0
        if len(plan) > 1:
            if prompt_api is None:
                raise ValueError(f"H3 Long Video: this video needs {len(plan)} segments, so connect H3 Prompt API to prompt_api to "
                                 "split the prompt; without it every segment repeats the whole story. For one segment, set "
                                 "total_seconds no higher than segment_seconds.")
            input_mode = "Ref2VA" if reference_count else "I2VA" if first_frame is not None else "T2VA"
            schedule, prompts = split_prompts(prompt, schedule, input_mode, reference_count, **prompt_api)
            plan = [(s["sampled_frames"], s["overlap_frames"], s["retained_frames"]) for s in schedule]
        # Keep the last clip's rounding up to H3's grid too (at most 16 frames), so the video ends where its
        # latent ends and can be continued without a jump. Prompts treat those frames as a padded tail.
        length, overlap, _ = plan[-1]
        plan[-1] = (length, overlap, length - overlap)
        schedule = segment_schedule(plan)
        _LOG.info("H3 Long Video: %.3fs output, %d segment(s), %.3fs sampled before trimming",
                  sum(keep for _, _, keep in plan) / FPS, len(plan), sum(length for length, _, _ in plan) / FPS)
        preview = prompt_preview(schedule, prompts)
        seeds = [(seed + i) % (1 << 64) for i in range(len(plan))]
        if log_prompts:
            report = {
                "operation": "video_generation", "status": "prepared",
                "original_prompt": prompt, "prompts": prompts, "schedule": schedule,
                "seeds": seeds,
                "width": width, "height": height, "steps": steps,
                "sampler_name": sampler_name, "scheduler": scheduler,
                "reference_image_count": reference_count, "has_first_frame": first_frame is not None,
                "continues": continues,
            }
            text = (f"Seeds: {report['seeds']}\nSize: {width}x{height}\nSteps: {steps}\n"
                    f"Sampler: {sampler_name}\nScheduler: {scheduler}\n\nOriginal prompt:\n\n{prompt}\n\n"
                    f"Final sampling prompts (prepared before sampling):\n\n{preview}")
            write_prompt_log(new_prompt_log_path("video"), report, text, (prompt_api or {}).get("api_key", ""))
        sampler, = KSamplerSelect.execute(sampler_name).result
        sigmas, = BasicScheduler.execute(model, scheduler, steps, 1.0).result
        references = {f"ref_image_{i}": img.unsqueeze(0) for i, img in enumerate(reference_images)} if reference_images is not None else {}
        context = MiniMaxH3MotionContext()
        trim = MiniMaxH3MotionContextTrim()
        sampling_steps = max(0, sigmas.shape[-1] - 1)
        previous = context_latent
        conditioning = None
        reference_latents = None
        temp_root = folder_paths.get_temp_directory()
        os.makedirs(temp_root, exist_ok=True)
        final_path = os.path.join(temp_root, f"h3_long_{uuid.uuid4().hex}.mp4")
        run_dir = None
        if save_latents:
            run_dir = new_run_directory()
            _LOG.warning("H3 Long Video: save_latents is on, so every segment's latent and MP4 are saved to %s. "
                         "They are never deleted automatically; delete old runs yourself.", run_dir)
            manifest = {
                "version": 1, "status": "running", "segments_saved": 0, "seed": seed,
                "width": width, "height": height, "fps": FPS, "total_seconds": total_seconds,
                "segment_seconds": segment_seconds, "context_length": int(context_length),
                "audio_context_length": audio_context_length, "steps": steps, "sampler_name": sampler_name,
                "scheduler": scheduler, "reference_image_count": reference_count,
                "has_first_frame": first_frame is not None, "continues": continues, "original_prompt": prompt,
                "segments": [{**entry, "prompt": text, "seed": seeds[i], "latent": None, "video": None}
                             for i, (entry, text) in enumerate(zip(schedule, prompts))],
            }
            write_manifest(run_dir, manifest)

        with tempfile.TemporaryDirectory(prefix="h3_segments_", dir=temp_root) as segment_dir, \
                _LongVideoProgress(len(plan) * (sampling_steps + 3) + 1) as progress:
            videos = []
            # Group model work without retaining a whole film's conditioning or latents.
            for batch_start in range(0, len(plan), 3):
                batch_end = min(batch_start + 3, len(plan))
                _LOG.info("H3 Long Video: preparing prompts %d-%d/%d", batch_start + 1, batch_end, len(plan))
                prepared = []
                for index in range(batch_start, batch_end):
                    comfy.model_management.throw_exception_if_processing_interrupted()
                    progress.begin(1)
                    encoding_started = time.perf_counter()
                    length = plan[index][0]
                    prompt = prompts[index]
                    if (conditioning is None or prompt != prompts[index - 1]
                            or (index == 1 and first_frame is not None and not references)):
                        if references:
                            conditioning, latent = MiniMaxH3ReferenceToVideo.execute(
                                clip=clip, vae=vae if reference_latents is None else None,
                                audio_vae=audio_vae, prompt=prompt,
                                width=width, height=height, length=length,
                                ref_images=references, **ref_size).result
                            if reference_latents is None:
                                reference_latents = conditioning[0][1]["minimax_refs"]
                            else:
                                conditioning = node_helpers.conditioning_set_values(
                                    conditioning, {"minimax_refs": reference_latents})
                        else:
                            conditioning, latent = MiniMaxH3ImageToVideo.execute(
                                clip=clip, vae=vae, prompt=prompt, width=width, height=height,
                                length=length, first_frame=first_frame if index == 0 else None).result
                    else:
                        latent, = EmptyMiniMaxH3LatentAV.execute(width, height, length).result
                    prepared.append((conditioning, latent, time.perf_counter() - encoding_started))
                    progress.finish()

                sampled_segments = []
                for index in range(batch_start, batch_end):
                    comfy.model_management.throw_exception_if_processing_interrupted()
                    _LOG.info("H3 Long Video: sampling segment %d/%d, %d new frames", index + 1, len(plan), plan[index][2])
                    preparation_started = time.perf_counter()
                    positive, latent, conditioning_seconds = prepared[index - batch_start]
                    prepared[index - batch_start] = None
                    if index == 0 and references and first_frame is not None:
                        positive, = MiniMaxH3AddGuide.execute(
                            positive, latent, frame_idx=0, vae=vae, image=first_frame[:1]).result
                    if index == 0 and context_frames is not None:
                        positive, trim_frames = context.apply(
                            positive, vae, latent, context_length, audio_context_length,
                            context_frames=context_frames, audio_vae=audio_vae, context_audio=context_audio)
                        context_frames = context_audio = None
                    else:
                        positive, trim_frames = context.apply(
                            positive, vae, latent, context_length, audio_context_length,
                            context_latent=previous)
                    guider, = BasicGuider.execute(model, positive).result
                    noise, = RandomNoise.execute(seeds[index]).result
                    sampling_started = time.perf_counter()
                    conditioning_seconds += sampling_started - preparation_started
                    progress.begin(sampling_steps, track=True)
                    sampled, denoised = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent).result
                    sampling_seconds = time.perf_counter() - sampling_started
                    progress.finish()
                    previous = sampled
                    if run_dir:
                        manifest["segments"][index]["latent"] = os.path.basename(save_segment_latent(run_dir, index, sampled))
                    sampled_segments.append((sampled, trim_frames, conditioning_seconds, sampling_seconds))
                    del denoised, sampled, positive, guider, noise, latent

                for index in range(batch_start, batch_end):
                    comfy.model_management.throw_exception_if_processing_interrupted()
                    _LOG.info("H3 Long Video: decoding segment %d/%d", index + 1, len(plan))
                    progress.begin(1, track=True)
                    decoding_started = time.perf_counter()
                    sampled, trim_frames, conditioning_seconds, sampling_seconds = sampled_segments[index - batch_start]
                    sampled_segments[index - batch_start] = None
                    _, overlap, keep = plan[index]
                    if tiled_decode:
                        images, = nodes.VAEDecodeTiled().decode(vae, sampled, tile_size=512)
                    else:
                        images, = nodes.VAEDecode().decode(vae, sampled)
                    audio, = VAEDecodeAudio.execute(audio_vae, sampled).result
                    del sampled
                    if trim_frames != overlap or images.shape[0] < trim_frames + keep:
                        raise RuntimeError("H3 frame layout changed: decoded frames or context overlap do not match the segment plan.")
                    images, audio = trim.trim(images[:trim_frames + keep], trim_frames, audio, fps=FPS, match_tail=True)
                    progress.finish()
                    progress.begin(1, track=True)
                    saving_started = time.perf_counter()
                    segment = InputImpl.VideoFromComponents(Types.VideoComponents(
                        images=images, audio=audio, frame_rate=Fraction(FPS)))
                    path = segment_file(run_dir, index, "mp4") if run_dir else os.path.join(segment_dir, f"{index:06d}.mp4")
                    segment.save_to(path, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.H264)
                    videos.append(InputImpl.VideoFromFile(path))
                    if run_dir:
                        # A segment counts as saved once both its latent and MP4 are on disk.
                        manifest["segments"][index]["video"] = os.path.basename(path)
                        manifest["segments_saved"] = index + 1
                        write_manifest(run_dir, manifest)
                    del images, audio, segment
                    _LOG.info("H3 Long Video: segment %d wall time: conditioning %.1fs, sampling %.1fs, decoding %.1fs, saving %.1fs",
                              index + 1, conditioning_seconds, sampling_seconds,
                              saving_started - decoding_started, time.perf_counter() - saving_started)
                    progress.finish()

            del conditioning, reference_latents
            comfy.model_management.throw_exception_if_processing_interrupted()
            progress.begin(1)
            joining_started = time.perf_counter()
            InputImpl.VideoFromList(videos).save_to(final_path, format=Types.VideoContainer.MP4)
            _LOG.info("H3 Long Video: final video assembly %.1fs", time.perf_counter() - joining_started)
            progress.finish()
        if run_dir:
            manifest["status"] = "complete"
            write_manifest(run_dir, manifest)
            _LOG.warning("H3 Long Video: saved %d segment(s), %.1f MB, to %s",
                         len(plan), folder_size(run_dir) / 1e6, run_dir)
        return io.NodeOutput(InputImpl.VideoFromFile(final_path), preview, previous)


NODE_CLASS_MAPPINGS = {"MiniMaxH3LongVideo": MiniMaxH3LongVideo}
NODE_DISPLAY_NAME_MAPPINGS = {"MiniMaxH3LongVideo": "H3 Long Video (Simple)"}
