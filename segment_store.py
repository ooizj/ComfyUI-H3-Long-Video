"""Per-segment latents, MP4s and a manifest saved by H3 Long Video, and the node that loads them back.

Each run gets its own folder under output/h3_long_video:

    20261016_153000_ab12cd/
        manifest.json          settings, schedule, prompts and seeds
        seg_0001.safetensors   sampler output latent (video + audio streams)
        seg_0001.mp4           decoded segment with its overlap trimmed
        ...

Latents use the same file layout as H3 Motion Context Save Latent, so either loader reads them.
"""

from datetime import datetime, timezone
import json
import logging
import os

import folder_paths
from comfy_api.latest import io

from .nodes import _st_load, _st_save, _streams_from_latent, _write_safetensors

_LOG = logging.getLogger("h3_motion_context")

RUNS_FOLDER = "h3_long_video"
MANIFEST = "manifest.json"
LATEST = "latest"


def runs_root():
    return os.path.join(folder_paths.get_output_directory(), RUNS_FOLDER)


def new_run_directory():
    """A new folder named by local time, so names sort by age; a suffix separates runs in the same second."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(runs_root(), exist_ok=True)
    for suffix in range(1000):
        path = os.path.join(runs_root(), f"{stamp}_{suffix:03d}")
        try:
            os.mkdir(path)
            return path
        except FileExistsError:
            continue
    raise RuntimeError(f"H3 Long Video: too many runs started in one second in {runs_root()}.")


def segment_file(run_dir, index, extension):
    """index is 0-based; files are numbered from 1."""
    return os.path.join(run_dir, f"seg_{index + 1:04d}.{extension}")


def write_manifest(run_dir, manifest):
    path = os.path.join(run_dir, MANIFEST)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump({"updated_at": datetime.now(timezone.utc).isoformat(), **manifest}, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_segment_latent(run_dir, index, latent):
    if _st_save is None:
        raise RuntimeError("H3 Long Video: safetensors is not available, so save_latents cannot save latents. Turn save_latents off.")
    parts = _streams_from_latent(latent)
    if len(parts) < 2:
        raise RuntimeError("H3 Long Video: the sampled latent has no audio stream, so it cannot be saved.")
    path = segment_file(run_dir, index, "safetensors")
    _write_safetensors(path, {"video": parts[0].cpu().contiguous(), "audio": parts[1].cpu().contiguous()})
    return path


def folder_size(path):
    return sum(entry.stat().st_size for entry in os.scandir(path) if entry.is_file())


def list_runs():
    """Saved run folder names, newest first."""
    root = runs_root()
    if not os.path.isdir(root):
        return []
    return sorted((entry.name for entry in os.scandir(root)
                   if entry.is_dir() and os.path.isfile(os.path.join(entry.path, MANIFEST))), reverse=True)


def read_manifest(run_dir):
    with open(os.path.join(run_dir, MANIFEST), encoding="utf-8") as handle:
        return json.load(handle)


def resolve_segment(run, segment):
    """Return (latent path, manifest, 1-based segment) for a saved run; segment 0 is the last saved one."""
    runs = list_runs()
    if not runs:
        raise FileNotFoundError(f"H3 Long Video Load Latent: no saved runs in output/{RUNS_FOLDER}. "
                                "Run H3 Long Video with save_latents on first.")
    name = runs[0] if run == LATEST else run
    # Only names listed from the runs folder are accepted, so the path cannot leave it.
    if name not in runs:
        raise FileNotFoundError(f"H3 Long Video Load Latent: run {run!r} was not found in output/{RUNS_FOLDER}. "
                                "Refresh the node list (press R) and pick another run.")
    run_dir = os.path.join(runs_root(), name)
    manifest = read_manifest(run_dir)
    saved = int(manifest.get("segments_saved", 0))
    if saved < 1:
        raise FileNotFoundError(f"H3 Long Video Load Latent: run {name} has no finished segment.")
    number = saved if segment <= 0 else segment
    if number > saved:
        raise FileNotFoundError(f"H3 Long Video Load Latent: run {name} has {saved} saved segment(s), "
                                f"so segment {segment} does not exist.")
    path = segment_file(run_dir, number - 1, "safetensors")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"H3 Long Video Load Latent: {path} is missing.")
    return path, manifest, number


class MiniMaxH3LongVideoLoadLatent(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3LongVideoLoadLatent",
            display_name="H3 Long Video Load Latent",
            category="video/minimax",
            description="Load a segment latent saved by H3 Long Video (save_latents on) and connect it to Long Video's context_latent to continue that video. The output is for context_latent only, not for VAE decoding.",
            inputs=[
                io.Combo.Input("run", options=[LATEST, *list_runs()], default=LATEST,
                    tooltip=f"A run folder in output/{RUNS_FOLDER}, newest first. 'latest' always picks the newest run when queued. Press R to refresh the list after a new run."),
                io.Int.Input("segment", default=0, min=0, max=9999,
                    tooltip="Segment to continue from, counted from 1. 0 = the last saved segment, which continues the end of that run's video."),
            ],
            outputs=[io.Latent.Output(display_name="latent"), io.String.Output(display_name="info")],
        )

    @classmethod
    def fingerprint_inputs(cls, run, segment):
        # 'latest' and an overwritten file keep the same inputs, so cache on the resolved file instead.
        try:
            path = resolve_segment(run, segment)[0]
            return f"{path}:{os.stat(path).st_mtime_ns}"
        except Exception:
            return float("nan")

    @classmethod
    def execute(cls, run, segment):
        if _st_load is None:
            raise RuntimeError("H3 Long Video Load Latent: safetensors is not available.")
        path, manifest, number = resolve_segment(run, segment)
        data = _st_load(path)
        if "video" not in data or "audio" not in data:
            raise ValueError(f"H3 Long Video Load Latent: {path} has no video/audio streams.")
        # Copy off the memory map so the file can be replaced later on Windows.
        video = data.pop("video").contiguous().clone()
        audio = data.pop("audio").contiguous().clone()
        info = (f"{os.path.basename(os.path.dirname(path))} segment {number}/{manifest.get('segments_saved')}, "
                f"{manifest.get('width')}x{manifest.get('height')}, context_length {manifest.get('context_length')}")
        _LOG.info("H3 Long Video Load Latent: loaded %s (%s)", path, info)
        # A plain list like H3 Motion Context Load Latent: only context_latent inputs accept it.
        return io.NodeOutput({"samples": [video, audio]}, info)


NODE_CLASS_MAPPINGS = {"MiniMaxH3LongVideoLoadLatent": MiniMaxH3LongVideoLoadLatent}
NODE_DISPLAY_NAME_MAPPINGS = {"MiniMaxH3LongVideoLoadLatent": "H3 Long Video Load Latent"}
