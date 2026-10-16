import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { t } from "./h3_i18n.js";
import { button, clock, dateLabel, element, openDialog, promptSections, promptSummary, renderPrompt } from "./h3_dialog.js";

const css = document.createElement("style");
css.textContent = `
.h3-seg-player{position:relative;flex-shrink:0;overflow:hidden;border-radius:8px;background:#000;cursor:pointer}.h3-seg-player video{display:block;width:100%;max-height:min(50vh,470px);object-fit:contain;background:#000;outline:none}.h3-seg-player:fullscreen video{max-height:none;height:100%}
.h3-seg-big{position:absolute;left:50%;top:50%;width:64px;height:64px;margin:-32px 0 0 -32px;border-radius:50%;background:#0009;color:#fff;font-size:26px;line-height:64px;text-align:center;pointer-events:none;transition:opacity .15s}.h3-seg-player.playing .h3-seg-big{opacity:0}
.h3-seg-controls{display:flex;align-items:center;gap:6px;margin-top:-6px}.h3-seg-time{font-variant-numeric:tabular-nums}.h3-seg-time span{color:var(--h3-muted)}.h3-seg-spacer{flex:1}
.h3-seg-track{position:relative;flex-shrink:0;margin-top:18px;user-select:none;touch-action:none;cursor:pointer}
.h3-seg-blocks{display:flex;gap:2px;height:30px}.h3-seg-block{flex-basis:0;min-width:0;display:flex;align-items:center;justify-content:center;overflow:hidden;background:color-mix(in srgb,var(--h3-fg) 11%,transparent);color:var(--h3-muted);font-size:11px;white-space:nowrap}
.h3-seg-block:first-child{border-radius:5px 0 0 5px}.h3-seg-block:last-child{border-radius:0 5px 5px 0}.h3-seg-block:hover{background:color-mix(in srgb,var(--h3-fg) 18%,transparent)}
.h3-seg-block[aria-selected=true]{background:color-mix(in srgb,var(--h3-accent) 38%,transparent);color:var(--h3-fg);font-weight:600}
.h3-seg-mark{position:absolute;top:24px;width:1px;height:6px;background:color-mix(in srgb,var(--h3-fg) 45%,transparent);pointer-events:none}
.h3-seg-played{position:absolute;left:0;bottom:-6px;height:3px;border-radius:2px;background:var(--h3-accent);pointer-events:none}
.h3-seg-head{position:absolute;top:-4px;bottom:-4px;width:2px;margin-left:-1px;background:var(--h3-fg);box-shadow:0 0 0 1px #0006;pointer-events:none}
.h3-seg-cut{position:absolute;top:-18px;bottom:0;width:2px;margin-left:-1px;background:#ffb547;pointer-events:none}.h3-seg-cut span{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);padding:0 5px;border-radius:3px;background:#ffb547;color:#1b1b1b;font-size:10px;font-weight:700;line-height:15px;white-space:nowrap}
.h3-seg-tip{position:absolute;bottom:calc(100% + 22px);padding:2px 7px;border-radius:4px;background:var(--h3-input);border:1px solid var(--h3-border);font-size:11px;white-space:nowrap;pointer-events:none;transform:translateX(-50%)}
.h3-seg-ticks{position:relative;height:16px;margin-top:8px;color:var(--h3-muted);font-size:11px}.h3-seg-ticks span{position:absolute;transform:translateX(-50%)}.h3-seg-ticks span:first-child{transform:none}
.h3-seg-info{display:flex;flex-direction:column;gap:6px}.h3-seg-info-head{display:flex;align-items:baseline;gap:10px}.h3-seg-info-head strong{font-size:14px}.h3-seg-info-head span{color:var(--h3-muted);font-size:12px}
.h3-seg-info details summary{color:var(--h3-muted);font-size:12px;cursor:pointer}.h3-seg-info details .h3-prompt{margin-top:8px;padding:10px 12px;border-radius:6px;background:var(--h3-input)}
.h3-latent{display:flex;flex-direction:column;gap:6px;width:100%;height:100%;padding:8px;overflow:hidden;border-radius:8px;background:var(--h3-panel);color:var(--h3-fg);font:12px/1.45 system-ui,sans-serif;cursor:pointer}.h3-latent *{box-sizing:border-box}
.h3-latent-frame{position:relative;flex:1;min-height:60px;overflow:hidden;border-radius:6px;background:#000}.h3-latent-frame video{width:100%;height:100%;object-fit:contain;pointer-events:none}
.h3-latent-frame .h3-badge{position:absolute;left:6px;bottom:6px;background:#ffb547;color:#1b1b1b;font-weight:700}.h3-latent-frame .h3-latent-seg{position:absolute;left:6px;top:6px;padding:0 6px;border-radius:4px;background:#000a;color:#fff;font-size:11px;line-height:18px}
.h3-latent-title{font-weight:600}.h3-latent-meta{color:var(--h3-muted)}.h3-latent-empty{margin:auto;color:var(--h3-muted);text-align:center;white-space:pre-wrap}
`;
document.head.append(css);

const HIDDEN = ["run", "segment", "frames"];
// Show the last frame before a cut: half a frame back from the cut time.
const HALF_FRAME = 0.5 / 24;

const segmentUrl = (folder, run, segment) => api.apiURL(`/view?${new URLSearchParams({
  filename: segment.video, subfolder: `${folder}/${run}`, type: "output",
})}`);

function runDate(name) {
  const m = name.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
  return m ? new Date(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +m[6]) : new Date(NaN);
}

const segmentLabel = (segment, count) => t(`第 ${segment.segment}/${count} 段`, `Segment ${segment.segment}/${count}`);
const seconds = value => `${value.toFixed(1)} s`;
const cutsOf = run => run.segments.flatMap(segment => segment.cuts.map(cut => ({ ...cut, segment })));
const isEnd = cut => cut.frames === cut.segment.cuts.at(-1).frames;

// The cut that the node's run/segment/frames values point at, or null.
function cutFor(entry, segmentNumber, frames) {
  const segment = segmentNumber <= 0 ? entry.segments.at(-1) : entry.segments.find(s => s.segment === segmentNumber);
  const cut = segment && (frames > 0 ? segment.cuts.find(c => c.frames === frames) : segment.cuts.at(-1));
  return cut ? { ...cut, segment } : null;
}

async function fetchRuns(signal) {
  const response = await api.fetchApi("/h3_long_video/runs", { signal, cache: "no-store" });
  if (response.status === 404) throw new Error(t("请重启 ComfyUI 并刷新页面，以加载视频列表。", "Restart ComfyUI and reload the page to list saved videos."));
  const result = await response.json();
  if (!response.ok) throw new Error(t("读取列表失败：", "Could not list saved videos: ") + (result.error || `HTTP ${response.status}`));
  return result;
}

function tickStep(duration) {
  return [1, 2, 5, 10, 15, 30, 60, 120, 300, 600].find(step => duration / step <= 8) ?? 1200;
}

function openPicker(node, onApply) {
  const widgets = Object.fromEntries(node.widgets.map(widget => [widget.name, widget]));
  const controller = new AbortController();
  const video = element("video");
  const ui = openDialog({
    title: t("选择接续位置", "Choose where to continue"),
    label: t("预览保存的视频并选择接续位置", "Preview saved videos and choose where to continue"),
    onClose: () => { controller.abort(); video.pause(); video.removeAttribute("src"); video.load(); },
  });
  ui.list.append(element("div", "h3-dlg-empty", t("正在读取保存的视频…", "Reading saved videos…")));

  const player = element("div", "h3-seg-player");
  video.preload = "auto";
  video.playsInline = true;
  player.append(video, element("div", "h3-seg-big", "▶"));
  const controls = element("div", "h3-seg-controls");
  const play = button("▶", () => togglePlay(), "h3-btn h3-btn-icon");
  const time = element("div", "h3-seg-time");
  const previous = button(t("◀ 上一个续接点", "◀ Previous point"), () => step(-1));
  const next = button(t("下一个续接点 ▶", "Next point ▶"), () => step(1));
  const mute = button("🔊", () => { video.muted = !video.muted; mute.textContent = video.muted ? "🔇" : "🔊"; }, "h3-btn h3-btn-icon");
  const full = button("⛶", () => void player.requestFullscreen?.(), "h3-btn h3-btn-icon");
  play.title = t("播放/暂停", "Play/pause"); mute.title = t("静音", "Mute"); full.title = t("全屏", "Fullscreen");
  controls.append(play, time, element("div", "h3-seg-spacer"), previous, next, mute, full);
  const track = element("div", "h3-seg-track");
  const blocks = element("div", "h3-seg-blocks");
  const marks = element("div");
  const played = element("div", "h3-seg-played");
  const head = element("div", "h3-seg-head");
  const cutMark = element("div", "h3-seg-cut");
  cutMark.append(element("span", "", t("接续点", "Continue")));
  const tip = element("div", "h3-seg-tip");
  tip.hidden = true;
  track.append(blocks, marks, played, head, cutMark, tip);
  const ticks = element("div", "h3-seg-ticks");
  const info = element("div", "h3-seg-info");

  const hint = element("div", "h3-dlg-hint");
  const cancel = button(t("取消", "Cancel"), () => ui.dialog.close());
  const apply = button(t("从这里接续", "Continue from here"), () => {
    onApply(run.run, cut.segment.segment, isEnd(cut) ? 0 : cut.frames);
    ui.dialog.close();
  }, "h3-btn h3-btn-primary");
  apply.disabled = true;
  ui.footer.append(hint, cancel, apply);

  let folder = "h3_long_video";
  let run = null;
  let cuts = [];
  let cut = null;
  let shown = null;
  let pendingSeek = 0;
  let autoplay = false;
  let ignorePause = false;
  const duration = () => run.segments.at(-1).end;
  const percent = value => `${Math.min(100, value / duration() * 100)}%`;
  const now = () => (shown ? shown.start + (video.currentTime || 0) : 0);
  const nearest = value => cuts.reduce((best, c) => (Math.abs(c.time - value) < Math.abs(best.time - value) ? c : best));

  function togglePlay() {
    if (!shown) return;
    if (video.paused) void video.play().catch(() => {}); else video.pause();
  }
  player.onclick = togglePlay;
  const syncPlaying = () => {
    player.classList.toggle("playing", !video.paused);
    play.textContent = video.paused ? "▶" : "❚❚";
  };
  video.addEventListener("play", syncPlaying);
  video.addEventListener("pause", syncPlaying);

  // Play or seek a segment's MP4; offset is seconds into it.
  function showSegment(segment, offset = 0, start = false) {
    if (shown !== segment) {
      shown = segment;
      for (const block of blocks.children) block.setAttribute("aria-selected", String(block.dataset.segment === String(segment.segment)));
      const sections = promptSections(segment.prompt);
      const details = sections.filter(s => !["", "subject_definitions", "summary", "retention_analysis"].includes(s.name) && s.body && s.body !== "N/A");
      const heading = element("div", "h3-seg-info-head");
      heading.append(element("strong", "", segmentLabel(segment, run.segments.length)),
        element("span", "", `${clock(segment.start)} – ${clock(segment.end)} · ${seconds(segment.end - segment.start)}`));
      info.replaceChildren(heading, element("div", "", promptSummary(segment.prompt) || t("（无提示词）", "(no prompt)")));
      if (details.length) {
        const more = element("details");
        more.append(element("summary", "", t("镜头与声音描述", "Shots and sound")), renderPrompt(details));
        info.append(more);
      }
    }
    pendingSeek = Math.max(0, offset);
    autoplay = start;
    const url = segmentUrl(folder, run.run, segment);
    if (video.dataset.url !== url) {
      video.dataset.url = url;
      video.src = url;
    } else {
      video.currentTime = pendingSeek;
      if (start) void video.play().catch(() => {});
    }
    updateTime();
  }

  function setCut(value) {
    cut = value;
    cutMark.style.left = percent(cut.time);
    const where = isEnd(cut) ? t(`第 ${cut.segment.segment} 段结尾`, `the end of segment ${cut.segment.segment}`)
      : t(`第 ${cut.segment.segment} 段中间`, `inside segment ${cut.segment.segment}`);
    hint.textContent = t(`新视频从 ${clock(cut.time)}（${where}）开始。续接点约每 0.71 秒一个，会吸附到最近的一个。`,
      `The new video starts at ${clock(cut.time)} (${where}). Points are about 0.71 s apart; the nearest one is used.`);
    apply.textContent = t(`从 ${clock(cut.time)} 接续`, `Continue from ${clock(cut.time)}`);
    apply.disabled = false;
    const index = cuts.indexOf(cut);
    previous.disabled = index <= 0;
    next.disabled = index >= cuts.length - 1;
  }

  // Pause on a cut, showing the last frame the new video continues from.
  function showCut(value) {
    setCut(value);
    if (!video.paused) { ignorePause = true; video.pause(); }
    showSegment(value.segment, value.time - value.segment.start - HALF_FRAME);
  }

  const step = direction => showCut(cuts[cuts.indexOf(cut) + direction]);

  function updateTime() {
    if (!run || !shown) return;
    time.replaceChildren(clock(now()), element("span", "", ` / ${clock(duration())}`));
    head.style.left = played.style.width = percent(now());
  }

  function showRun(entry, control) {
    run = entry;
    cuts = cutsOf(entry);
    shown = null;
    for (const item of ui.list.children) item.setAttribute("aria-pressed", String(item === control));
    ui.subtitle.textContent = `${entry.run} · ${entry.width}×${entry.height} · seed ${entry.seed}`;
    video.style.aspectRatio = `${entry.width} / ${entry.height}`;
    blocks.replaceChildren();
    for (const segment of entry.segments) {
      const block = element("div", "h3-seg-block", String(segment.segment));
      block.dataset.segment = segment.segment;
      block.style.flexGrow = segment.end - segment.start;
      blocks.append(block);
    }
    marks.replaceChildren();
    for (const c of cuts) {
      const mark = element("div", "h3-seg-mark");
      mark.style.left = percent(c.time);
      marks.append(mark);
    }
    ticks.replaceChildren();
    const tick = tickStep(duration());
    for (let value = 0; value < duration() - tick * 0.3; value += tick) {
      const label = element("span", "", value < 60 ? `${value}s` : `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`);
      label.style.left = percent(value);
      ticks.append(label);
    }
    const current = entry.run === widgets.run.value && cutFor(entry, widgets.segment.value, widgets.frames.value);
    showCut((current && cuts.find(c => c.segment === current.segment && c.frames === current.frames)) || cuts.at(-1));
  }

  video.addEventListener("loadedmetadata", () => {
    video.currentTime = Math.min(pendingSeek, video.duration || 0);
    if (autoplay) void video.play().catch(() => {});
  });
  video.addEventListener("timeupdate", () => {
    updateTime();
    if (!video.paused) setCut(nearest(now()));
  });
  video.addEventListener("seeked", updateTime);
  // Pausing by hand snaps to the nearest cut; the pause at a segment's end is followed by "ended".
  video.addEventListener("pause", () => {
    if (ignorePause) { ignorePause = false; return; }
    if (run && !video.ended && !autoplay) showCut(nearest(now()));
  });
  video.addEventListener("playing", () => { autoplay = false; });
  video.addEventListener("ended", () => {
    const following = run.segments[run.segments.indexOf(shown) + 1];
    if (following) showSegment(following, 0, true);
    else showCut(cuts.at(-1));
  });

  const timeAt = event => {
    const box = blocks.getBoundingClientRect();
    return Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)) * duration();
  };
  const seek = event => {
    const value = timeAt(event);
    if (video.paused) { showCut(nearest(value)); return; }
    const segment = run.segments.find(s => value < s.end) ?? run.segments.at(-1);
    showSegment(segment, value - segment.start, true);
  };
  track.addEventListener("pointerdown", event => {
    if (!run) return;
    track.setPointerCapture(event.pointerId);
    seek(event);
  });
  track.addEventListener("pointermove", event => {
    if (!run) return;
    const target = nearest(timeAt(event));
    tip.hidden = false;
    tip.style.left = percent(target.time);
    tip.textContent = `${segmentLabel(target.segment, run.segments.length)} · ${clock(target.time)}`;
    if (track.hasPointerCapture(event.pointerId)) seek(event);
  });
  track.addEventListener("pointerleave", () => { tip.hidden = true; });

  void (async () => {
    try {
      const result = await fetchRuns(controller.signal);
      folder = result.folder;
      ui.list.replaceChildren();
      let initial = null;
      for (const entry of result.runs) {
        const control = button("", null, "h3-card");
        control.setAttribute("aria-pressed", "false");
        control.title = entry.run;
        const thumb = element("div", "h3-card-thumb");
        const text = element("div", "h3-card-text");
        control.append(thumb, text);
        text.append(element("div", "h3-card-title", dateLabel(runDate(entry.run)) || entry.run));
        if (entry.error) {
          text.append(element("div", "h3-card-meta", t("无法读取：", "Unreadable: ") + entry.error));
          control.disabled = true;
        } else {
          const preview = element("video");
          preview.muted = true;
          preview.preload = "metadata";
          preview.src = `${segmentUrl(folder, entry.run, entry.segments[0])}#t=0.1`;
          thumb.append(preview);
          const meta = `${seconds(entry.segments.at(-1).end)} · ${t(`${entry.segments.length} 段`, `${entry.segments.length} segments`)} · ${entry.width}×${entry.height}`;
          text.append(element("div", "h3-card-meta", meta));
          if (entry.status !== "complete") text.append(element("span", "h3-badge", t("未完成", "Unfinished")));
          text.append(element("div", "h3-clamp", promptSummary(entry.prompt)));
          control.onclick = () => showRun(entry, control);
          if (entry.run === widgets.run.value || !initial) initial = { entry, control };
        }
        ui.list.append(control);
      }
      if (initial) {
        ui.main.append(player, controls, track, ticks, info);
        showRun(initial.entry, initial.control);
        apply.focus();
      } else {
        ui.list.append(element("div", "h3-dlg-empty", t("没有可用的视频", "No usable videos")));
        ui.main.append(element("div", "h3-dlg-empty", t("还没有保存的视频。\n先运行 H3 Long Video 并打开 save_latents。", "No saved videos yet.\nRun H3 Long Video with save_latents on first.")));
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      ui.list.replaceChildren();
      ui.main.replaceChildren(element("div", "h3-dlg-empty", error.message));
    }
  })();
}

function install(node) {
  if (node.h3SegmentPicker) return;
  const widgets = Object.fromEntries(node.widgets.map(widget => [widget.name, widget]));
  // run/segment/frames are set by the picker; the card below shows what they point at.
  for (const name of HIDDEN) {
    const widget = widgets[name];
    widget.hidden = true;
    widget.options = { ...widget.options, hidden: true };
    widget.draw = () => {};
    widget.computeSize = () => [0, -4];
  }
  const card = element("div", "h3-latent h3-themed");
  card.title = t("点击预览并选择接续位置", "Click to preview and choose where to continue");
  for (const type of ["pointerdown", "pointermove", "pointerup", "mousedown", "dblclick", "wheel"]) {
    card.addEventListener(type, e => e.stopPropagation());
  }
  const frame = element("div", "h3-latent-frame");
  const video = element("video");
  video.muted = true;
  video.preload = "auto";
  let seekTo = 0;
  video.addEventListener("loadedmetadata", () => { video.currentTime = Math.max(0, Math.min(seekTo, video.duration - HALF_FRAME)); });
  let token = 0;

  async function refresh() {
    const mine = ++token;
    let result;
    try {
      result = await fetchRuns();
    } catch (error) {
      if (mine === token) card.replaceChildren(element("div", "h3-latent-empty", error.message));
      return;
    }
    if (mine !== token) return;
    widgets.run.options.values = ["latest", ...result.runs.map(r => r.run)];
    const usable = result.runs.filter(r => !r.error);
    const latest = widgets.run.value === "latest";
    const entry = latest ? usable[0] : usable.find(r => r.run === widgets.run.value);
    if (!entry) {
      card.replaceChildren(element("div", "h3-latent-empty", latest
        ? t("还没有保存的视频。\n点击这里选择，或先运行 H3 Long Video。", "No saved videos yet.\nClick to choose, or run H3 Long Video first.")
        : t(`找不到 ${widgets.run.value}\n可能已被删除，点击这里重新选择。`, `${widgets.run.value} was not found.\nIt may have been deleted; click to choose again.`)));
      return;
    }
    const cut = cutFor(entry, widgets.segment.value, widgets.frames.value);
    if (!cut) {
      card.replaceChildren(element("div", "h3-latent-empty", t("保存的视频里没有这个续接点，点击这里重新选择。", "The saved video has no such point; click to choose again.")));
      return;
    }
    seekTo = cut.time - cut.segment.start - HALF_FRAME;
    const url = segmentUrl(result.folder, entry.run, cut.segment);
    if (video.dataset.url !== url) { video.dataset.url = url; video.src = url; }
    else if (video.readyState) video.currentTime = Math.max(0, Math.min(seekTo, video.duration - HALF_FRAME));
    frame.replaceChildren(video, element("span", "h3-latent-seg", segmentLabel(cut.segment, entry.segments.length)),
      element("span", "h3-badge", t(`接续点 ${clock(cut.time)}`, `Continue at ${clock(cut.time)}`)));
    const automatic = latest && widgets.segment.value <= 0 && widgets.frames.value <= 0;
    const title = automatic ? t(`最新视频的结尾（${dateLabel(runDate(entry.run))}）`, `End of the latest video (${dateLabel(runDate(entry.run))})`)
      : dateLabel(runDate(entry.run)) || entry.run;
    const total = entry.segments.at(-1).end;
    const meta = `${entry.width}×${entry.height} · ${t("全片", "full")} ${seconds(total)} · context ${entry.context_length}`;
    card.replaceChildren(frame, element("div", "h3-latent-title", title), element("div", "h3-latent-meta", meta),
      element("div", "h3-clamp", promptSummary(cut.segment.prompt)));
  }

  const choose = () => openPicker(node, (run, segment, frames) => {
    if (!widgets.run.options.values.includes(run)) widgets.run.options.values = [...widgets.run.options.values, run];
    widgets.run.value = run;
    widgets.segment.value = segment;
    widgets.frames.value = frames;
    node.graph?.change();
    node.setDirtyCanvas(true, true);
    void refresh();
  });
  card.onclick = choose;
  const pick = node.addWidget("button", "choose_segment", null, choose);
  pick.label = t("预览并选择接续位置…", "Preview and choose…");
  pick.serialize = false;
  node.addDOMWidget("h3_latent_preview", "custom", card, {
    serialize: false, hideOnZoom: false, getMinHeight: () => 200,
    getHeight: () => Math.round((node.size[0] - 36) * 9 / 16) + 90,
  });
  const onDone = () => void refresh();
  api.addEventListener("execution_success", onDone);
  const oldRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    api.removeEventListener("execution_success", onDone);
    oldRemoved?.apply(this, args);
  };
  const oldConfigure = node.onConfigure;
  node.onConfigure = function (...args) { oldConfigure?.apply(this, args); void refresh(); };
  node.setSize([Math.max(340, node.size[0]), Math.max(330, node.computeSize()[1])]);
  node.h3SegmentPicker = true;
  void refresh();
}

app.registerExtension({
  name: "H3LongVideo.LoadLatent",
  nodeCreated(node) { if (node.comfyClass === "MiniMaxH3LongVideoLoadLatent") install(node); },
});
