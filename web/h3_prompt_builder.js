import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { localizer, t } from "./h3_i18n.js";

const FIELDS = ["subject_definitions", "summary", "retention_analysis", "detailed_description", "overall_soundscape", "non_diegetic_music"];
const EXAMPLE = [
  "subject_definitions:\n<Subject 1> 是 <Picture 1> 中穿红色外套的女孩。\n\nsummary:\n[reference generation] 参考 <Picture 1> 的人物，生成 <Subject 1> 在雨后街道行走的短片。\n\nretention_analysis:\n<Subject 1>（出现于 [Shot 1]、[Shot 2]）：fully_preserved - 脸部、发型和红色外套保持一致。\n\ndetailed_description:\n写实电影风格，雨后傍晚，柔和侧光。\n[Shot 1] 中景，<Subject 1> 站在街道左侧。\n0–3 秒：女孩沿街向前走，镜头缓慢跟拍。\n[Shot 2] At 00:03.000, 镜头切到女孩面部近景。\n3–6 秒：她轻轻微笑。\n\noverall_soundscape:\n低音量的街道环境声。\n\nnon_diegetic_music:\nN/A",
  "subject_definitions:\n<Subject 1> is the girl in <Picture 1>, wearing a red coat.\n\nsummary:\n[reference generation] A short video of <Subject 1> walking down a street after rain.\n\nretention_analysis:\n<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - her face, hairstyle and red coat stay consistent.\n\ndetailed_description:\nRealistic cinematic style, a street after rain at dusk, soft side light.\n[Shot 1] A medium shot frames <Subject 1> on the left side of the street.\nFrom 0 to 3 seconds: she walks forward as the camera slowly tracks her.\n[Shot 2] At 00:03.000, the shot cuts to a close-up of her face.\nFrom 3 to 6 seconds: she smiles softly.\n\noverall_soundscape:\nLow street ambience.\n\nnon_diegetic_music:\nN/A",
];
const AI_LANGUAGES = ["English", "中文"];
const DELETED_PICTURE = /<Picture (?:已删除|deleted)>/;
const LANGUAGE_KEY = "H3MotionContext.PromptBuilder.ai_language";

const css = document.createElement("style");
css.textContent = `
.h3pb{box-sizing:border-box;display:flex;flex-direction:column;width:100%;height:100%;overflow:auto;background:#131b23;color:#e4ebf2;border:1px solid #344352;border-radius:9px;padding:12px 14px;font:13px/1.5 system-ui,sans-serif;cursor:default}
.h3pb *{box-sizing:border-box}.h3pb button{border:1px solid #405366;background:#223343;border-radius:5px;padding:5px 10px;color:#e4ebf2;font:inherit;cursor:pointer}.h3pb button:hover{background:#30485c}.h3pb button:disabled{opacity:.4;cursor:default}.h3pb button:focus-visible,.h3pb textarea:focus{outline:1px solid #75cabc}
.h3pb .h3pb-row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.h3pb .h3pb-title{font-size:17px;font-weight:650;margin-right:auto}.h3pb small{color:#a6b7c6;font-size:11px}.h3pb .h3pb-gap{margin-left:auto}.h3pb .h3pb-primary{background:#275b53;border-color:#559486}.h3pb .h3pb-pictures{display:flex;gap:8px;width:100%;min-width:0;flex-shrink:0;overflow-x:auto;overflow-y:hidden;padding:8px 0;min-height:110px;scrollbar-width:auto;scrollbar-color:#648f9f #0b131b}
.h3pb .h3pb-pictures::-webkit-scrollbar{height:14px}
.h3pb .h3pb-pictures::-webkit-scrollbar-track{background:#0b131b;border-radius:7px}
.h3pb .h3pb-pictures::-webkit-scrollbar-thumb{background:#648f9f;border:3px solid #0b131b;border-radius:7px}
.h3pb .h3pb-card{flex:0 0 126px;border:1px solid #344d5d;border-radius:6px;padding:5px;position:relative;background:#1b2732}.h3pb .h3pb-card img{width:114px;height:78px;object-fit:contain;background:#10161c;display:block;cursor:pointer}.h3pb .h3pb-card strong{display:block;font-size:11px;color:#8bdbcb;text-align:center}.h3pb .h3pb-card .h3pb-row{gap:3px;justify-content:center;margin-top:4px}.h3pb .h3pb-card button{font-size:11px;padding:1px 5px}.h3pb .h3pb-drop{display:grid;place-items:center;min-width:150px;border:1px dashed #648174;border-radius:6px;color:#9dbcb0;padding:10px;flex:1;font-size:12px;text-align:center}.h3pb .h3pb-segment{display:inline-flex;border:1px solid #405366;border-radius:6px;overflow:hidden}.h3pb .h3pb-segment button{border:0;border-radius:0;background:#1b2732;padding:3px 12px}.h3pb .h3pb-segment button+button{border-left:1px solid #405366}.h3pb .h3pb-segment button[aria-pressed=true]{background:#275b53;color:#fff;font-weight:600}.h3pb .h3pb-head{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-top:8px;font-weight:600}.h3pb .h3pb-editor{position:relative;display:flex;flex:1 1 auto;min-height:240px;margin-top:5px}.h3pb .h3pb-editor.h3pb-source{flex:none;min-height:0}.h3pb .h3pb-source textarea{min-height:150px;resize:vertical}.h3pb textarea{display:block;flex:1;width:100%;resize:none;padding:9px;background:#0b131b;color:#e3edf5;border:1px solid #364958;border-radius:5px;font:12px/1.6 ui-monospace,"Microsoft YaHei",monospace;tab-size:2}.h3pb textarea::placeholder{color:#66798a}.h3pb .h3pb-complete{position:absolute;z-index:20;left:6px;right:6px;top:6px;max-height:165px;overflow:auto;background:#203342;border:1px solid #76b9ad;border-radius:5px;box-shadow:0 6px 18px #0008}.h3pb .h3pb-complete button{display:flex;align-items:center;gap:9px;width:100%;border:0;border-radius:0;text-align:left;background:transparent}.h3pb .h3pb-complete button[aria-selected=true]{background:#365c69}.h3pb .h3pb-complete img{width:32px;height:25px;object-fit:contain}.h3pb .h3pb-complete span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.h3pb .h3pb-info{margin-top:5px;color:#a6b7c6;font-size:12px;white-space:pre-wrap}.h3pb .h3pb-warning{color:#edbf7e;font-size:12px;white-space:pre-wrap}.h3pb .h3pb-status{min-height:18px;margin-top:4px;font-size:12px;color:#8bdbcb;white-space:pre-wrap;overflow-wrap:anywhere}.h3pb [hidden]{display:none!important}
`;
document.head.append(css);

function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function viewUrl(path) {
  const match = path.match(/ \[(input|output|temp)\]$/);
  const name = match ? path.slice(0, match.index) : path;
  const slash = name.lastIndexOf("/");
  return api.apiURL(`/view?${new URLSearchParams({
    filename: name.slice(slash + 1), subfolder: name.slice(0, Math.max(0, slash)), type: match?.[1] || "input",
  })}`);
}

// Latest end second of the timed passages, e.g. "3–6 秒" or "From 3 to 6 seconds".
function timelineEnd(text) {
  let end = 0;
  for (const match of text.matchAll(/(\d+(?:\.\d+)?)\s*(?:[–—~-]|to)\s*(\d+(?:\.\d+)?)\s*(?:秒|s\b|sec|second)/gi)) end = Math.max(end, Number(match[2]));
  return end;
}

function connectedTotalSeconds(node) {
  for (const id of node.outputs?.[0]?.links ?? []) {
    const link = node.graph?.getLink?.(id) ?? node.graph?.links?.[id];
    const total = node.graph?.getNodeById(link?.target_id)?.widgets?.find(w => w.name === "total_seconds");
    if (total) return Number(total.value);
  }
  return null;
}

function install(node) {
  if (node.h3PromptBuilder) return;
  const widgets = Object.fromEntries(node.widgets.map(w => [w.name, w]));
  for (const name of ["prompt", "pictures", "ai_request", "ai_read_images", "ai_language"]) {
    const widget = widgets[name];
    widget.hidden = true;
    widget.options = { ...widget.options, hidden: true };
    widget.draw = () => {};
    widget.computeSize = () => [0, -4];
    if (widget.inputEl) widget.inputEl.hidden = true;
    if (widget.element) widget.element.hidden = true;
  }
  widgets.ai_request.value = 0;
  // New nodes start with the last chosen language; saved workflows restore their own value on configure.
  try {
    const saved = localStorage.getItem(LANGUAGE_KEY);
    if (AI_LANGUAGES.includes(saved)) widgets.ai_language.value = saved;
  } catch {}
  const root = element("div", "h3pb");
  const syncWidth = () => { root.style.width = `${Math.max(1, node.size[0] - 20)}px`; };
  const oldResize = node.onResize;
  node.onResize = function (...args) {
    oldResize?.apply(this, args);
    syncWidth();
  };
  root.tabIndex = 0;
  // Nodes 2.0 zooms on wheel unless the focused element sits inside data-capture-wheel.
  root.dataset.captureWheel = "true";
  for (const type of ["pointerdown", "pointermove", "pointerup", "mousedown", "dblclick", "keydown", "keyup", "wheel"]) {
    root.addEventListener(type, e => e.stopPropagation());
  }
  // total_seconds lives on the connected Long Video, so recheck the timeline when the pointer comes back.
  root.addEventListener("pointerenter", () => refresh());
  const i18n = localizer(() => { renderGallery(); refresh(); });
  const local = i18n.set;
  const button = (label, handler, parent) => {
    const btn = element("button");
    if (Array.isArray(label)) local(btn, ...label); else btn.textContent = label;
    btn.type = "button";
    btn.onclick = handler;
    parent.append(btn);
    return btn;
  };
  const header = element("div", "h3pb-row");
  header.append(local(element("div", "h3pb-title"), "H3 参考提示词", "H3 Reference Prompt"));
  const pictureRow = element("div", "h3pb-row");
  const picker = element("input");
  picker.type = "file";
  picker.accept = "image/*";
  picker.multiple = true;
  picker.hidden = true;
  let replacing = null;
  button(["＋ 添加图片", "＋ Add images"], () => { replacing = null; picker.multiple = true; picker.click(); }, pictureRow);
  const count = element("small");
  pictureRow.append(count);
  const gallery = element("div", "h3pb-pictures");
  local(gallery, "可多选、拖入或粘贴图片。点缩略图插入引用；拖动卡片或用箭头排序，正文编号同步更新。", "Select, drop or paste images. Click a thumbnail to insert its label; drag cards or use the arrows to reorder and the labels in the text follow.", "title");

  const toolbar = element("div", "h3pb-row");
  const sourceHead = element("div", "h3pb-head");
  sourceHead.append(local(element("span"), "描述", "Description"), local(element("small", ""), "普通描述或完整 H3 提示词，AI 据此生成下方提示词", "Plain description or a full H3 prompt; AI writes the prompt below from it"));
  const convertBtn = button(["AI 生成 H3 提示词 ↓", "AI to H3 prompt ↓"], () => {
    if (!sourceText.value.trim()) { setStatus(t("请先在描述框写下要转换的内容。", "Write the description to convert first.")); return; }
    void requestAI(sourceText.value);
  }, sourceHead);
  convertBtn.classList.add("h3pb-primary", "h3pb-gap");
  local(convertBtn, "用 prompt_api 连接的模型把描述写成六段 H3 提示词，替换下方内容，可用 ComfyUI 的撤销恢复。只运行此节点，不生成视频。", "Write the description as the six-field H3 prompt with the model on prompt_api, replacing the text below; ComfyUI's undo restores it. Only this node runs, no video is generated.", "title");
  const promptHead = element("div", "h3pb-head");
  promptHead.append(local(element("span"), "H3 提示词", "H3 prompt"), local(element("small", ""), "输出给 Long Video", "Sent to Long Video"));
  const headingsBtn = button(["插入六段标题", "Insert field headings"], () => {
    const text = textarea.value;
    const missing = FIELDS.filter(name => !new RegExp(`^[ \\t]*${name}[ \\t]*[:：]`, "im").test(text));
    if (!missing.length) { setStatus(t("六段标题都已存在。", "All six headings are already there.")); return; }
    setPrompt(text.trimEnd() + (text.trim() ? "\n\n" : "") + missing.map(name => `${name}:\n${name === "non_diegetic_music" ? "N/A" : ""}`).join("\n\n"));
    checkpoint();
  }, promptHead);
  headingsBtn.classList.add("h3pb-gap");
  local(headingsBtn, "在末尾补上缺少的 Ref2VA 字段标题，手动填写时使用。", "Append the missing Ref2VA field headings, for writing by hand.", "title");
  const languageGroup = element("div", "h3pb-segment h3pb-gap");
  languageGroup.setAttribute("role", "group");
  local(languageGroup, "AI 输出语言", "AI output language", "ariaLabel");
  local(languageGroup, "AI 生成和整理提示词时使用的描述语言。English 符合 H3 官方 Ref2VA 格式；台词、歌词和画面文字始终保留原语言。", "Description language of AI rewrites. English follows the official H3 Ref2VA format; dialogue, lyrics and on-screen text keep their original language.", "title");
  const languageButtons = AI_LANGUAGES.map(value => button(value, () => {
    setLanguage(value);
    try { localStorage.setItem(LANGUAGE_KEY, value); } catch {}
    changed();
  }, languageGroup));
  const setLanguage = value => {
    widgets.ai_language.value = value;
    languageButtons.forEach((btn, index) => btn.setAttribute("aria-pressed", String(AI_LANGUAGES[index] === value)));
  };
  const visionLabel = element("label", "h3pb-row");
  visionLabel.style.gap = "4px";
  const visionInput = element("input");
  visionInput.type = "checkbox";
  visionInput.onchange = () => { widgets.ai_read_images.value = visionInput.checked; changed(); };
  visionLabel.append(visionInput, local(element("span", ""), "识图", "Read images"));
  local(visionLabel, "AI 按图片顺序读取最长边 1024px 的 JPEG 副本；需要视觉模型，纯文字模型请关闭。视频生成仍使用原图。", "AI reads JPEG copies (longest side 1024px) in picture order. Requires a vision model; turn off for a text-only model. Video generation still uses the originals.", "title");
  toolbar.append(languageGroup, visionLabel);
  const aiBtn = button(["AI 整理", "AI rewrite"], () => { void requestAI(); }, promptHead);
  local(aiBtn, "用 prompt_api 连接的模型按六段整理下方提示词；没有字段标题的文字会被展开成六段。只运行此节点，不生成视频。", "Rewrite the prompt below field by field with the model on prompt_api; text without field headings is expanded into the six fields. Only this node runs, no video is generated.", "title");
  const applyBtn = button(["应用 AI 结果", "Apply AI result"], () => {
    if (candidate === null) return;
    setPrompt(candidate); checkpoint(); candidate = null; applyBtn.hidden = true;
    setStatus("");
  }, promptHead);
  applyBtn.classList.add("h3pb-primary");
  applyBtn.hidden = true;
  const status = element("div", "h3pb-status");
  status.setAttribute("role", "status");

  const sourceText = element("textarea");
  local(sourceText, "描述", "Description", "ariaLabel");
  local(sourceText, "直接描述人物、场景、动作、对白和时间安排，例如：总时长 8 秒，林婉（图1）在茶室（图2）倒茶……\n也可以粘贴完整 H3 提示词，让 AI 按段整理。", "Describe the characters, scene, actions, dialogue and timing, e.g. 8 seconds total, Lin (picture 1) pours tea in the tea room (picture 2)…\nOr paste a full H3 prompt for AI to rewrite field by field.", "placeholder");
  sourceText.spellcheck = false;
  sourceText.rows = 7;
  const textarea = element("textarea");
  local(textarea, "H3 提示词", "H3 prompt", "ariaLabel");
  local(textarea, ...EXAMPLE, "placeholder");
  textarea.spellcheck = false;
  const info = element("div", "h3pb-info");
  const warning = element("div", "h3pb-warning");
  root.append(header, pictureRow, gallery, picker, toolbar, status,
    sourceHead, completingEditor(sourceText, "h3pb-editor h3pb-source", () => { node.properties.h3_import_text = sourceText.value; changed(); }),
    promptHead, completingEditor(textarea, "h3pb-editor", () => { widgets.prompt.value = textarea.value; refresh(); changed(); }),
    local(element("small", ""), "输入 <Pic / <Sub 补全 · ↑↓ 选择，Tab / Enter 插入。[Shot 2] At 00:06.000 表示第 6 秒切镜；“0–3 秒：”是事件时间段，不等于切镜。", "Type <Pic / <Sub to complete · ↑↓ to choose, Tab / Enter to insert. [Shot 2] At 00:06.000 cuts at 6 seconds; \"From 0 to 3 seconds:\" is an event range, not a cut."),
    info, warning);

  let pending = null;
  let candidate = null;
  let uploading = false;
  let ignoreClickUntil = 0;
  let lastInput = textarea;
  const pictures = () => JSON.parse(widgets.pictures.value || "[]");
  const snapshot = () => ({ source: sourceText.value, prompt: String(widgets.prompt.value ?? ""), pictures: pictures() });
  const changed = () => { node.graph?.change(); node.graph?.setDirtyCanvas(true, true); };
  const setPrompt = value => { widgets.prompt.value = textarea.value = value; refresh(); changed(); };
  const setSource = value => { node.properties.h3_import_text = sourceText.value = value; changed(); };
  // Each editor action becomes one step of ComfyUI's own undo/redo.
  const checkpoint = () => app.extensionManager.workflow.activeWorkflow?.changeTracker?.captureCanvasState();
  function setStatus(message) { status.textContent = message; }
  const insert = value => {
    lastInput.focus();
    lastInput.setRangeText(value, lastInput.selectionStart, lastInput.selectionEnd, "end");
    lastInput.dispatchEvent(new Event("input"));
  };
  function renderGallery() {
    gallery.replaceChildren();
    const paths = pictures();
    count.textContent = t(`${paths.length} 张 · 顺序对应 <Picture N>`, `${paths.length} images · order matches <Picture N>`);
    paths.forEach((path, index) => {
      const card = element("div", "h3pb-card");
      card.style.userSelect = "none";
      card.dataset.index = index;
      const img = element("img");
      img.src = viewUrl(path);
      img.alt = `<Picture ${index + 1}>`;
      img.title = `${path}\n${t("点击插入引用", "Click to insert label")}`;
      img.draggable = false;
      card.onclick = e => {
        if (!e.target.closest("button") && performance.now() >= ignoreClickUntil) insert(`<Picture ${index + 1}>`);
      };
      card.append(img, element("strong", "", `<Picture ${index + 1}>`));
      const actions = element("div", "h3pb-row");
      card.append(actions);
      const left = button("←", () => movePicture(index, index - 1), actions);
      left.title = t("向前移动", "Move earlier"); left.disabled = index === 0 || uploading;
      const right = button("→", () => movePicture(index, index + 1), actions);
      right.title = t("向后移动", "Move later"); right.disabled = index === paths.length - 1 || uploading;
      button(t("换", "Swap"), () => { replacing = index; picker.multiple = false; picker.click(); }, actions).title = t("替换图片，保留编号", "Replace image, keep its number");
      button("×", () => {
        if (!uploading) remapPictures(paths, paths.map((_, i) => i).filter(i => i !== index));
      }, actions).title = t("移除图片", "Remove image");
      let drag = null;
      card.onpointerdown = e => {
        if (uploading || e.button !== 0 || e.target.closest("button")) return;
        drag = { x: e.clientX, y: e.clientY, moved: false };
        card.setPointerCapture(e.pointerId);
      };
      card.onpointermove = e => {
        if (!drag) return;
        if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 6) drag.moved = true;
        if (drag.moved) { e.preventDefault(); card.style.borderColor = "#8bdbcb"; }
      };
      card.onpointerup = e => {
        const moved = drag?.moved;
        drag = null; card.style.borderColor = "";
        if (!moved) return;
        ignoreClickUntil = performance.now() + 250;
        const target = document.elementFromPoint(e.clientX, e.clientY)?.closest(".h3pb-card");
        if (target && gallery.contains(target)) movePicture(index, Number(target.dataset.index));
      };
      card.onpointercancel = () => { drag = null; card.style.borderColor = ""; };
      card.ondragstart = e => e.preventDefault();
      gallery.append(card);
    });
    if (!paths.length) gallery.append(element("div", "h3pb-drop", t("＋ 将参考图片拖到这里，或点击添加图片", "＋ Drop reference images here, or click Add images")));
  }
  function remapPictures(paths, order) {
    const remap = text => text.replace(/<Picture\s+(\d+)>/g, (label, number) => {
      const old = Number(number) - 1;
      if (old >= paths.length) return label;
      const next = order.indexOf(old);
      return next < 0 ? t("<Picture 已删除>", "<Picture deleted>") : `<Picture ${next + 1}>`;
    });
    widgets.pictures.value = JSON.stringify(order.map(i => paths[i]));
    setSource(remap(sourceText.value));
    setPrompt(remap(String(widgets.prompt.value ?? "")));
    renderGallery(); checkpoint();
  }
  function movePicture(from, to) {
    const paths = pictures();
    if (uploading || from === to || from < 0 || to < 0 || from >= paths.length || to >= paths.length) return;
    const order = paths.map((_, i) => i);
    order.splice(to, 0, order.splice(from, 1)[0]);
    remapPictures(paths, order);
  }
  async function upload(files, replaceIndex = null) {
    if (uploading) return;
    const images = [...files].filter(f => f.type.startsWith("image/"));
    if (!images.length) return;
    uploading = true;
    setStatus(t("正在保存图片…", "Saving images…"));
    try {
      for (const file of images) {
        const form = new FormData();
        form.append("image", file); form.append("type", "input"); form.append("subfolder", "h3_prompt_builder");
        const response = await api.fetchApi("/upload/image", { method: "POST", body: form });
        if (!response.ok) throw new Error(t(`图片上传失败：HTTP ${response.status}`, `Image upload failed: HTTP ${response.status}`));
        const result = await response.json();
        const path = `${result.subfolder ? result.subfolder + "/" : ""}${result.name} [${result.type || "input"}]`;
        const paths = pictures();
        if (replaceIndex === null) paths.push(path); else paths[replaceIndex] = path;
        widgets.pictures.value = JSON.stringify(paths);
        if (replaceIndex !== null) break;
      }
      setStatus("");
    } catch (error) { setStatus(error.message); }
    finally { uploading = false; renderGallery(); refresh(); changed(); checkpoint(); }
  }
  picker.onchange = () => { void upload(picker.files, replacing); picker.value = ""; };
  root.addEventListener("dragover", e => { e.preventDefault(); e.stopPropagation(); });
  root.addEventListener("drop", e => { e.preventDefault(); e.stopPropagation(); void upload(e.dataTransfer.files); });
  root.addEventListener("paste", e => {
    if (e.clipboardData.files.length) { e.preventDefault(); e.stopPropagation(); void upload(e.clipboardData.files); }
  });

  // Wraps a text box with <Picture N> / <Subject N> completion; onInput stores its value.
  function completingEditor(input, className, onInput) {
    const editor = element("div", className);
    const menu = element("div", "h3pb-complete");
    menu.setAttribute("role", "listbox");
    menu.hidden = true;
    editor.append(input, menu);
    let matches = [], selected = 0, start = 0;
    const choose = index => {
      input.focus();
      input.setRangeText(matches[index].label, start, input.selectionStart, "end");
      menu.hidden = true; onInput();
    };
    const paintMenu = () => {
      menu.replaceChildren();
      matches.forEach((entry, index) => {
        const option = button("", () => choose(index), menu);
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", String(index === selected));
        option.onpointerdown = e => e.preventDefault();
        if (entry.path) { const thumb = element("img"); thumb.src = viewUrl(entry.path); thumb.alt = ""; option.append(thumb); }
        option.append(element("span", "", entry.label + (entry.description ? `  ${entry.description}` : "")));
      });
      menu.hidden = !matches.length;
    };
    const complete = () => {
      const prefix = input.value.slice(0, input.selectionStart).match(/<([A-Za-z]*(?:\s+\d*)?)$/);
      if (!prefix || input.selectionStart !== input.selectionEnd) { menu.hidden = true; return; }
      start = input.selectionStart - prefix[0].length;
      const entries = pictures().map((path, index) => ({ label: `<Picture ${index + 1}>`, path }));
      const ids = new Set();
      // subject_definitions comes first, so each subject's first line is its definition.
      for (const match of textarea.value.matchAll(/^[ \t]*<Subject\s+(\d+)>[^\n]*/gm)) {
        if (ids.has(match[1])) continue;
        ids.add(match[1]);
        entries.push({ label: `<Subject ${match[1]}>`, description: match[0].replace(/^\s*<[^>]+>\s*/, "") });
      }
      matches = entries.filter(entry => entry.label.toLowerCase().startsWith(prefix[0].toLowerCase()));
      selected = 0; paintMenu();
    };
    input.onfocus = () => { lastInput = input; };
    input.oninput = () => { onInput(); complete(); };
    input.onkeyup = e => { if (["ArrowLeft", "ArrowRight"].includes(e.key)) complete(); };
    input.onblur = () => { checkpoint(); setTimeout(() => { menu.hidden = true; }, 150); };
    input.onkeydown = e => {
      if (e.isComposing || menu.hidden) return;
      if (e.key === "Escape") { e.preventDefault(); menu.hidden = true; }
      if (["ArrowDown", "ArrowUp"].includes(e.key)) {
        e.preventDefault(); selected = (selected + (e.key === "ArrowDown" ? 1 : -1) + matches.length) % matches.length; paintMenu();
      }
      if (["Enter", "Tab"].includes(e.key)) { e.preventDefault(); choose(selected); }
    };
    return editor;
  }

  // source is the description to convert; without it AI rewrites the H3 prompt itself.
  async function requestAI(source = null) {
    if (pending || uploading) return;
    if (source === null && !String(widgets.prompt.value ?? "").trim()) { setStatus(t("H3 提示词为空；可在描述框写好后点“AI 生成 H3 提示词”。", "The H3 prompt is empty; write a description and click \"AI to H3 prompt\".")); return; }
    const configInput = node.inputs.find(i => i.name === "prompt_api");
    if (configInput?.link == null) { setStatus(t("连接 H3 Prompt API 后即可使用；手动编辑无需连接。", "Connect H3 Prompt API to use AI; manual editing needs no connection.")); return; }
    aiBtn.disabled = convertBtn.disabled = true;
    try {
      const before = JSON.stringify(snapshot());
      const graph = await app.graphToPrompt();
      const id = String(node.id);
      if (!graph.output[id]) throw new Error(t("请在主画布中使用 AI 整理按钮。节点不能处于禁用状态。", "Use AI rewrite from the main canvas, with the node not bypassed or muted."));
      const output = {};
      function include(key) {
        if (output[key]) return;
        const entry = graph.output[key];
        if (!entry) throw new Error(t("未找到上游配置节点，请检查连接。", "Upstream configuration node not found; check the connection."));
        output[key] = structuredClone(entry);
        for (const value of Object.values(entry.inputs)) if (Array.isArray(value) && value.length === 2 && typeof value[0] === "string") include(value[0]);
      }
      include(id);
      if (source !== null) output[id].inputs.prompt = source;
      const request = Math.floor(Math.random() * 0x7ffffffe) + 1;
      output[id].inputs.ai_request = request;
      pending = { request, before, promptId: null };
      setStatus(source === null
        ? t("AI 整理已提交；仅运行此提示词节点。等待期间仍可编辑。", "AI rewrite queued; only this prompt node runs. You can keep editing while waiting.")
        : t("正在根据描述生成 H3 提示词；仅运行此提示词节点，完成后填入下方。", "Writing the H3 prompt from the description; only this prompt node runs and the result fills in below."));
      const queued = await api.queuePrompt(0, { output, workflow: graph.workflow });
      if (pending?.request === request) pending.promptId = queued.prompt_id;
    } catch (error) { pending = null; aiBtn.disabled = convertBtn.disabled = false; setStatus(error.message || t("AI 提交失败，请检查队列。", "AI request failed to queue; check the queue.")); }
  }

  function refresh() {
    const text = String(widgets.prompt.value ?? "");
    const total = pictures().length;
    const unresolved = [...new Set([...text.matchAll(/<Picture\s+(\d+)>/g)].map(m => Number(m[1])).filter(n => n < 1 || n > total))];
    const notes = [], messages = [];
    const end = timelineEnd(text);
    const seconds = connectedTotalSeconds(node);
    if (end) notes.push(t(`时间线写到 ${end} 秒`, `Timeline ends at ${end} s`) + (seconds ? t(`，Long Video total_seconds 为 ${seconds} 秒`, `; Long Video total_seconds is ${seconds} s`) : ""));
    if (end && seconds && Math.abs(end - seconds) > 0.05) messages.push(t("提示词时间线与 Long Video 的 total_seconds 不一致。", "The prompt timeline does not match Long Video total_seconds."));
    if (text.trim() && !new RegExp(`^\\s*(?:#{1,6}\\s+)?(?:\\*\\*)?(?:${FIELDS.join("|")})\\b`, "i").test(text)) notes.push(t("未按六段标题书写：Long Video 会直接使用原文；可点 AI 整理转成六段。", "No field headings: Long Video uses the text as is; click AI rewrite to turn it into the six fields."));
    if (!total) messages.push(t("尚未添加参考图：接入 Ref2VA 生成前请添加图片。", "No reference images yet: add images before Ref2VA generation."));
    if (unresolved.length) messages.push(t("缺少图片：", "Missing images: ") + unresolved.map(n => `<Picture ${n}>`).join(t("、", ", ")));
    if (DELETED_PICTURE.test(text)) messages.push(t("有图片引用已删除，请替换正文中的 <Picture 已删除>。", "Some image labels were deleted; replace <Picture deleted> in the text."));
    info.textContent = notes.join("\n");
    warning.textContent = messages.join("\n");
  }
  function restore() {
    widgets.ai_request.value = 0;
    if (typeof widgets.ai_read_images.value !== "boolean") widgets.ai_read_images.value = true;
    visionInput.checked = widgets.ai_read_images.value;
    setLanguage(AI_LANGUAGES.includes(widgets.ai_language.value) ? widgets.ai_language.value : "English");
    sourceText.value = node.properties.h3_import_text || "";
    textarea.value = String(widgets.prompt.value ?? "");
    renderGallery(); refresh();
    syncWidth();
  }
  const oldConfigure = node.onConfigure;
  node.onConfigure = function (...args) { oldConfigure?.apply(this, args); restore(); };
  const oldExecuted = node.onExecuted;
  node.onExecuted = function (data) {
    oldExecuted?.apply(this, arguments);
    if (!pending || data.h3_ai_request?.[0] !== pending.request) return;
    const value = data.h3_prompt?.[0];
    const unchanged = JSON.stringify(snapshot()) === pending.before;
    pending = null; aiBtn.disabled = convertBtn.disabled = false;
    if (typeof value !== "string") { setStatus(t("AI 未返回可用结果，原文已保留。", "AI returned no usable result; the original was kept.")); return; }
    if (unchanged) {
      setPrompt(value); checkpoint(); candidate = null; applyBtn.hidden = true;
      setStatus("");
    } else {
      candidate = value; applyBtn.hidden = false;
      setStatus(t("AI 已完成。期间你修改过内容，原文已保留；点击“应用 AI 结果”可替换。", "AI finished. You edited meanwhile, so your text was kept; click \"Apply AI result\" to replace it."));
    }
  };
  const failed = e => {
    if (!pending || e.detail.prompt_id !== pending.promptId) return;
    pending = null; aiBtn.disabled = convertBtn.disabled = false;
    setStatus(t("AI 执行失败或已中断，原文未改动。请查看队列错误信息。", "AI failed or was interrupted; the original is unchanged. Check the queue error."));
  };
  api.addEventListener("execution_error", failed);
  api.addEventListener("execution_interrupted", failed);
  const oldRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    api.removeEventListener("execution_error", failed); api.removeEventListener("execution_interrupted", failed);
    i18n.dispose();
    oldRemoved?.apply(this, args);
  };
  node.addDOMWidget("h3_ref_editor", "custom", root, {
    serialize: false, hideOnZoom: false, getMinHeight: () => 560,
    onDraw: widget => { widget.width = node.size[0]; },
  });
  node.h3PromptBuilder = { root, restore };
  node.setSize([Math.max(640, node.size[0]), Math.max(720, node.size[1])]);
  restore();
}

const NODE_TYPE = "MiniMaxH3LongVideoRefPromptBuilder";
// Up to 0.11.1 this node used the id MiniMaxH3PromptBuilder, which another node pack also registers.
// Only rename ours: its second output is reference_images, the other pack's is picture_1.
const OLD_NODE_TYPE = "MiniMaxH3PromptBuilder";
// Up to 0.12.0 the six fields were separate widgets, followed by these.
const OLD_WIDGETS = [...FIELDS, "pictures", "ai_request", "ai_read_images", "log_prompts", "ai_language"];

function joinFields(node) {
  const values = node.widgets_values_named
    ?? (typeof node.widgets_values?.[7] === "number" ? Object.fromEntries(node.widgets_values.map((v, i) => [OLD_WIDGETS[i], v])) : {});
  if (!Object.hasOwn(values, "subject_definitions")) return;
  const named = {
    prompt: FIELDS.map(name => `${name}:\n${values[name] ?? ""}`).join("\n\n"),
    pictures: values.pictures ?? "[]",
    ai_request: 0,
    ai_read_images: typeof values.ai_read_images === "boolean" ? values.ai_read_images : true,
    ai_language: AI_LANGUAGES.includes(values.ai_language) ? values.ai_language : "English",
  };
  node.widgets_values_named = named;
  node.widgets_values = Object.values(named);
  const dropped = [...FIELDS.slice(1), "log_prompts"];
  node.inputs = node.inputs?.filter(input => input.link != null || !dropped.includes(input.widget?.name))
    .map(input => input.widget?.name === FIELDS[0] ? { ...input, name: "prompt", localized_name: "prompt", label: undefined, widget: { name: "prompt" } } : input);
  delete node.properties?.h3_import_open;
}

app.registerExtension({
  name: "H3MotionContext.PromptBuilder",
  beforeConfigureGraph(graph) {
    const nodes = [graph.nodes, ...(graph.definitions?.subgraphs ?? []).map(subgraph => subgraph.nodes)].flat();
    for (const node of nodes) {
      if (node?.type === OLD_NODE_TYPE && node.outputs?.[1]?.name === "reference_images") node.type = NODE_TYPE;
      if (node?.type === NODE_TYPE) joinFields(node);
    }
  },
  nodeCreated(node) { if (node.comfyClass === NODE_TYPE) install(node); },
  loadedGraphNode(node) { if (node.comfyClass === NODE_TYPE) { install(node); node.h3PromptBuilder.restore(); } },
});
