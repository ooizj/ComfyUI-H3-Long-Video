import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const HIDDEN_WIDGETS = [
  "asset_type",
  "style_preset",
  "medium_shot",
  "camera_angle",
  "lighting_preset",
  "subject",
  "manual_prompt",
  "final_prompt",
];

const REF_CHIPS = [
  ["+ <image1> 主参考图", "<image1>"],
  ["+ <image2> 场景/副参考图", "<image2>"],
  [
    "+ 保留参考图人物长相服装",
    "保留图中人物(<image1>)的长相、发型、发饰和服装不变，仅将动作与场景改为：",
  ],
];

const css = document.createElement("style");
css.textContent = `
.q21vp{box-sizing:border-box;width:100%;height:100%;overflow:auto;background:#121921;color:#e5edf5;border:1px solid #324455;border-radius:9px;padding:12px 14px;font:12.5px/1.45 system-ui,-apple-system,"Microsoft YaHei",sans-serif;cursor:default}
.q21vp *{box-sizing:border-box}
.q21vp button{border:1px solid #3d5266;background:#1f3040;border-radius:5px;padding:5px 10px;color:#e5edf5;font:inherit;cursor:pointer;transition:background .12s,border-color .12s}
.q21vp button:hover{background:#2c4358;border-color:#5b7a96}
.q21vp button:disabled{opacity:.45;cursor:default}
.q21vp select,.q21vp input[type=text],.q21vp textarea{width:100%;background:#0b1117;color:#e5edf5;border:1px solid #34485a;border-radius:5px;padding:5px 8px;font:12px/1.5 ui-monospace,"Microsoft YaHei",monospace}
.q21vp select:focus,.q21vp input[type=text]:focus,.q21vp textarea:focus,.q21vp button:focus-visible{outline:1px solid #63c7b8;border-color:#63c7b8}
.q21vp textarea{resize:vertical;min-height:58px}
.q21vp-header{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding-bottom:9px;border-bottom:1px solid #253443;margin-bottom:10px}
.q21vp-title{font-size:15px;font-weight:700;color:#8ce0d0;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.q21vp-badge{font-size:11px;font-weight:600;padding:2px 8px;border-radius:99px;background:#1b3b38;color:#7ee2d1;border:1px solid #376e67}
.q21vp-hero-sec{background:#182631;border:2px solid #4fa394;border-radius:8px;padding:10px 12px;margin-bottom:10px;box-shadow:0 3px 12px rgba(0,0,0,.25)}
.q21vp-hero-title{font-size:13.5px;font-weight:700;color:#7ee2d1;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.q21vp-hero-input{min-height:86px!important;font-size:13px!important;background:#091017!important;border:1px solid #529c8e!important;color:#fff!important}
.q21vp-sec{background:#17212b;border:1px solid #283848;border-radius:7px;padding:9px 11px;margin-bottom:9px}
.q21vp-sec-title{font-size:12px;font-weight:700;color:#9ec3db;margin-bottom:7px;display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap}
.q21vp-grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.q21vp-field{display:flex;flex-direction:column;gap:3px;margin-bottom:7px}
.q21vp-field:last-child{margin-bottom:0}
.q21vp-label{font-size:11.5px;font-weight:600;color:#c3d4e3;display:flex;align-items:center;justify-content:space-between;gap:6px}
.q21vp-chips{display:flex;flex-wrap:wrap;gap:5px;margin:3px 0 6px}
.q21vp-chip{font-size:11px!important;padding:2px 7px!important;background:#192836!important;border-color:#354c61!important;color:#b8d4ea!important;border-radius:4px!important}
.q21vp-chip:hover{background:#253c50!important;color:#fff!important}
.q21vp-pick{display:grid!important;grid-template-columns:64px minmax(0,1fr) auto;align-items:center;gap:8px;width:100%;text-align:left;padding:4px 8px 4px 4px!important;background:#0b1117!important}
.q21vp-pick.is-open{border-color:#63c7b8!important}
.q21vp-pick-thumb{width:64px;height:36px;object-fit:cover;border-radius:3px;background:#1a2530;display:block}
.q21vp-pick-text{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px}
.q21vp-pick-caret{color:#8aa2b5;font-size:11px}
.q21vp-gallery{background:#0d141b;border:1px solid #3a5568;border-radius:7px;padding:8px;margin:0 0 9px}
.q21vp-gallery-head{display:flex;align-items:center;gap:8px;margin-bottom:7px;font-weight:700;color:#9ec3db;font-size:12px}
.q21vp-gallery-head small{flex:1;font-weight:400;color:#7f97aa}
.q21vp-gallery-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:7px}
.q21vp-card{display:flex!important;flex-direction:column;gap:4px;padding:4px!important;text-align:left;font-size:11px!important;line-height:1.3!important}
.q21vp-card img,.q21vp-card-noimg{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:3px;display:block;background:#1a2530}
.q21vp-card-noimg{display:grid;place-items:center;color:#5d7386}
.q21vp-card.is-selected{border-color:#63c7b8!important;background:#1b3b38!important}
.q21vp-hint{font-size:11.5px;color:#9ab4c9;margin-top:5px}
.q21vp-status{font-size:11.5px;color:#8ce0d0;min-height:17px;margin-top:5px;white-space:pre-wrap}
.q21vp-warn{color:#f2be72}
.q21vp-preview-box{background:#090e13;border:1px solid #395568;border-radius:5px;padding:8px;min-height:96px;font:12px/1.55 ui-monospace,"Microsoft YaHei",monospace;color:#dceaf5}
.q21vp-preview-actions{display:flex;align-items:center;gap:6px}
.q21vp [hidden]{display:none!important}
`;
document.head.append(css);

function exampleUrl(group, key) {
  return new URL(`./qwen21_examples/${group}.${key}.jpg`, import.meta.url).href;
}

function shortLabel(label) {
  return String(label).split(" (")[0];
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

let CATALOG_CACHE = null;
async function loadCatalog() {
  if (CATALOG_CACHE) return CATALOG_CACHE;
  const resp = await api.fetchApi("/h3_motion_context/qwen21_catalog");
  CATALOG_CACHE = await resp.json();
  return CATALOG_CACHE;
}

function installQwen21Builder(node) {
  if (node.qwen21Builder) return;

  const widgets = Object.fromEntries((node.widgets || []).map(w => [w.name, w]));
  for (const name of HIDDEN_WIDGETS) {
    const w = widgets[name];
    if (!w) continue;
    w.hidden = true;
    w.options = { ...w.options, hidden: true };
    w.draw = () => {};
    w.computeSize = () => [0, -4];
    if (w.inputEl) w.inputEl.hidden = true;
    if (w.element) w.element.hidden = true;
  }

  const root = el("div", "q21vp");
  root.tabIndex = 0;
  root.dataset.captureWheel = "true";
  for (const evt of ["pointerdown", "pointermove", "pointerup", "mousedown", "dblclick", "keydown", "keyup", "wheel"]) {
    root.addEventListener(evt, e => e.stopPropagation());
  }

  const syncWidth = () => {
    root.style.width = `${Math.max(1, node.size[0] - 20)}px`;
  };
  const oldResize = node.onResize;
  node.onResize = function (...args) {
    oldResize?.apply(this, args);
    syncWidth();
  };

  const header = el("div", "q21vp-header");
  const titleWrap = el("div", "q21vp-title");
  titleWrap.append(el("span", "", "🎬 Qwen Image 2.1 Prompt Builder"));
  const sizeBadge = el("span", "q21vp-badge", "宽高未连接");
  sizeBadge.title = "width / height 接「分辨率选择器」，提示词按宽高写横图、竖图或方图";
  titleWrap.append(sizeBadge);
  header.append(titleWrap);
  root.append(header);

  // 第一步：人物或场景描述
  const heroSec = el("div", "q21vp-hero-sec");
  const heroTitle = el("div", "q21vp-hero-title");
  heroTitle.append(el("span", "", "✏️ 第一步：输入你要生成的人物或场景描述"));
  const clearInputBtn = el("button", "", "🗑️ 清空");
  clearInputBtn.type = "button";
  heroTitle.append(clearInputBtn);
  heroSec.append(heroTitle);

  const refChipsRow = el("div", "q21vp-chips");
  refChipsRow.hidden = true;
  const txtSubject = el("textarea", "q21vp-hero-input");
  txtSubject.placeholder =
    "在这里输入描述（然后在下方【第二步】选择对应的资产类型）：\n" +
    "• 人物设定卡：写人物年龄、发型、五官、上衣、下装、鞋子（如：一个亚洲女性，高马尾，穿米白色针织开衫与深蓝牛仔裤）\n" +
    "• 纯场景空镜：写环境与家具陈设（如：温馨的现代极简客厅，浅橡木地板，米白布艺沙发与落地窗阳光）\n" +
    "• 视频关键帧：写角色动作、所处环境与镜头感（选胸像/半身时不要写裤子和鞋）";
  for (const [cLabel, cInsert] of REF_CHIPS) {
    const chip = el("button", "q21vp-chip", cLabel);
    chip.type = "button";
    chip.onclick = () => {
      insertAtCursor(txtSubject, cInsert);
      if (widgets.subject) widgets.subject.value = txtSubject.value;
      onOptionChange();
    };
    refChipsRow.append(chip);
  }
  heroSec.append(refChipsRow, txtSubject);
  root.append(heroSec);

  // 第二步：资产类型与风格
  const secPreset = el("div", "q21vp-sec");
  secPreset.append(el("div", "q21vp-sec-title", "🎯 第二步：选择图片类型与视觉风格（点按钮看示例图）"));

  // Thumbnail pickers share one gallery, opened under the row of the clicked button; one is open at a time.
  const gallery = el("div", "q21vp-gallery");
  gallery.hidden = true;
  const pickers = [];
  let openPicker = null;

  function closeGallery() {
    openPicker = null;
    gallery.hidden = true;
    gallery.replaceChildren();
    for (const p of pickers) p.el.classList.remove("is-open");
  }

  function renderGallery(picker) {
    const head = el("div", "q21vp-gallery-head");
    const closeBtn = el("button", "", "收起");
    closeBtn.type = "button";
    closeBtn.onclick = closeGallery;
    head.append(el("span", "", `${picker.title} · 点图选择`), el("small", "", "示例图：同一 seed、同一段描述，只改这一项"), closeBtn);
    const grid = el("div", "q21vp-gallery-grid");
    for (const [key, opt] of Object.entries(picker.options)) {
      const card = el("button", "q21vp-card");
      card.type = "button";
      card.title = opt.label;
      card.classList.toggle("is-selected", key === picker.value);
      const img = el("img");
      img.alt = "";
      img.loading = "lazy";
      img.src = exampleUrl(picker.group, key);
      img.onerror = () => img.replaceWith(el("div", "q21vp-card-noimg", "无示例"));
      card.append(img, el("span", "", shortLabel(opt.label)));
      card.onclick = () => {
        picker.value = key;
        closeGallery();
        picker.onchange?.();
      };
      grid.append(card);
    }
    gallery.replaceChildren(head, grid);
    picker.el.closest(".q21vp-grid2").after(gallery);
    gallery.hidden = false;
    for (const p of pickers) p.el.classList.toggle("is-open", p === picker);
  }

  function makePicker(group, title) {
    const trigger = el("button", "q21vp-pick");
    trigger.type = "button";
    const thumb = el("img", "q21vp-pick-thumb");
    thumb.alt = "";
    thumb.onerror = () => { thumb.style.visibility = "hidden"; };
    const text = el("span", "q21vp-pick-text", "");
    trigger.append(thumb, text, el("span", "q21vp-pick-caret", "▾"));
    let current = "";
    const picker = {
      el: trigger, group, title, options: {}, onchange: null,
      get value() { return current; },
      set value(v) {
        current = v;
        const label = picker.options[v]?.label ?? v;
        text.textContent = shortLabel(label);
        trigger.title = label;
        thumb.style.visibility = "";
        thumb.src = exampleUrl(group, v);
      },
      setOptions(options) {
        picker.options = options || {};
        picker.value = current in picker.options ? current : Object.keys(picker.options)[0] ?? "";
      },
    };
    trigger.onclick = () => (openPicker === picker ? closeGallery() : renderGallery((openPicker = picker)));
    pickers.push(picker);
    return picker;
  }

  function field(label, control) {
    const f = el("div", "q21vp-field");
    f.append(el("div", "q21vp-label", label), control);
    return f;
  }

  const selAsset = makePicker("asset_type", "① 视频图片资产类型");
  const selStyle = makePicker("style_preset", "② 画面视觉风格");
  const selMedium = makePicker("medium_shot", "③ 景别");
  const selAngle = makePicker("camera_angle", "④ 摄影机位视角");
  const selLight = makePicker("lighting_preset", "⑤ 光影氛围预设");
  for (const pair of [
    [field("① 视频图片资产类型", selAsset.el), field("② 画面视觉风格", selStyle.el)],
    [field("③ 景别", selMedium.el), field("④ 摄影机位视角", selAngle.el)],
    [field("⑤ 光影氛围预设", selLight.el)],
  ]) {
    const row = el("div", "q21vp-grid2");
    row.append(...pair);
    secPreset.append(row);
  }
  const mediumHint = el("div", "q21vp-hint", "💡 胸像/半身：描述里不要写裤子、鞋子等画面外的东西，否则模型会画成全身。");
  mediumHint.hidden = true;
  secPreset.append(mediumHint);
  root.addEventListener("keydown", e => {
    if (e.key === "Escape" && openPicker) closeGallery();
  });

  root.append(secPreset);

  // 第三步：提示词预览与微调
  const secPreview = el("div", "q21vp-sec");
  const previewHeader = el("div", "q21vp-sec-title");
  const previewTitleSpan = el("span", "", "");
  const previewRight = el("div", "q21vp-preview-actions");
  const wordCountSpan = el("small", "", "0 words");
  const unlockManualBtn = el("button", "", "🔄 恢复自动生成");
  unlockManualBtn.type = "button";
  unlockManualBtn.hidden = true;
  const copyBtn = el("button", "", "📋 复制");
  copyBtn.type = "button";
  previewRight.append(wordCountSpan, unlockManualBtn, copyBtn);
  previewHeader.append(previewTitleSpan, previewRight);
  secPreview.append(previewHeader);

  const txtFinalPrompt = el("textarea", "q21vp-preview-box");
  secPreview.append(txtFinalPrompt);
  secPreview.append(el("div", "q21vp-hint", "💡 描述写得简短时，可在官方 Qwen Image 2.1 流程中开启 refine_prompt，由官方扩写模型补全画面细节。"));
  const statusEl = el("div", "q21vp-status", "");
  secPreview.append(statusEl);

  const negLabel = el("div", "q21vp-label", "Negative Prompt（negative_prompt 输出；cfg 为 1 时不生效）");
  negLabel.style.marginTop = "8px";
  const txtNegPreview = el("textarea");
  txtNegPreview.readOnly = true;
  txtNegPreview.style.minHeight = "38px";
  txtNegPreview.style.marginTop = "4px";
  secPreview.append(negLabel, txtNegPreview);
  root.append(secPreview);

  let catalog = null;
  let assembleTimer = null;
  let lastSizeKey = "";

  // A manual edit of the preview is output as-is until the user unlocks it; option changes do not overwrite it.
  function isManual() {
    return Boolean(widgets.manual_prompt?.value) && Boolean(txtFinalPrompt.value.trim());
  }

  function setManual(on) {
    if (widgets.manual_prompt) widgets.manual_prompt.value = on;
    updateManualLockUI();
  }

  function updateManualLockUI() {
    const manual = isManual();
    unlockManualBtn.hidden = !manual;
    previewTitleSpan.textContent = manual
      ? "📤 第三步：当前使用你手动修改的提示词 (已锁定)"
      : "📤 第三步：生成的提示词 (可直接微调)";
  }

  function onOptionChange() {
    if (isManual()) {
      setStatus("⚠️ 当前使用你手动修改的提示词，修改的选项不会生效；点击「🔄 恢复自动生成」放弃手动修改。", true);
    }
    scheduleAssemble();
    node.setDirtyCanvas(true, true);
  }

  unlockManualBtn.onclick = () => {
    setManual(false);
    scheduleAssemble();
    setStatus("已恢复为自动生成模式。");
  };

  clearInputBtn.onclick = () => {
    txtSubject.value = "";
    if (widgets.subject) widgets.subject.value = "";
    setManual(false);
    scheduleAssemble();
    txtSubject.focus();
    setStatus("已清空输入内容。");
  };

  function insertAtCursor(input, textToInsert) {
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    input.value = input.value.slice(0, start) + textToInsert + input.value.slice(end);
    const nextPos = start + textToInsert.length;
    input.focus();
    input.setSelectionRange(nextPos, nextPos);
  }

  function setStatus(msg, isWarn = false) {
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("q21vp-warn", Boolean(isWarn));
  }

  function updateWordCount(text) {
    const words = (text || "").trim().split(/\s+/).filter(Boolean).length;
    wordCountSpan.textContent = `${words} words`;
  }

  function updateHints() {
    refChipsRow.hidden = selAsset.value !== "ref_image_edit";
    mediumHint.hidden = !["bust_headroom", "medium_waist"].includes(selMedium.value);
  }

  // width/height are linked inputs; read the upstream node so the preview uses the same orientation word as the run.
  function linkedValue(name) {
    const slot = node.findInputSlot(name);
    const link = slot >= 0 ? node.getInputLink(slot) : null;
    const origin = link ? node.getInputNode(slot) : null;
    if (!origin) return null;
    const w = Object.fromEntries((origin.widgets || []).map(x => [x.name, x.value]));
    const outName = origin.outputs?.[link.origin_slot]?.name;
    if (origin.comfyClass === "ResolutionSelector") {
      const [rw, rh] = String(w.aspect_ratio).split(" ")[0].split(":").map(Number);
      const scale = Math.sqrt((w.megapixels * 1024 * 1024) / (rw * rh));
      return Math.round(((outName === "height" ? rh : rw) * scale) / w.multiple) * w.multiple;
    }
    const v = Number(w[outName] ?? w.value);
    return Number.isFinite(v) ? v : null;
  }

  function linkedSize() {
    const width = linkedValue("width");
    const height = linkedValue("height");
    return width && height ? [width, height] : null;
  }

  async function runAssemblePreview() {
    const size = linkedSize();
    sizeBadge.textContent = size ? `${size[0]} × ${size[1]}` : "宽高未连接";
    try {
      const resp = await api.fetchApi("/h3_motion_context/qwen21_assemble", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_type: selAsset.value,
          width: size?.[0],
          height: size?.[1],
          style_preset: selStyle.value,
          medium_shot: selMedium.value,
          camera_angle: selAngle.value,
          lighting_preset: selLight.value,
          subject: txtSubject.value,
        }),
      });
      const data = await resp.json();
      txtNegPreview.value = data.negative_prompt || "";
      if (!isManual()) {
        txtFinalPrompt.value = data.prompt || "";
        if (widgets.final_prompt) widgets.final_prompt.value = data.prompt || "";
      }
      updateWordCount(txtFinalPrompt.value);
    } catch (err) {
      setStatus(`同步参数出错: ${err.message}`, true);
    }
  }

  function scheduleAssemble() {
    if (assembleTimer) clearTimeout(assembleTimer);
    assembleTimer = setTimeout(runAssemblePreview, 120);
  }

  selAsset.onchange = () => {
    const val = selAsset.value;
    if (widgets.asset_type) widgets.asset_type.value = val;
    updateHints();
    const preset = catalog?.asset_types?.[val];
    if (preset) {
      selMedium.value = preset.default_medium;
      if (widgets.medium_shot) widgets.medium_shot.value = preset.default_medium;
      updateHints();
      selLight.value = preset.default_lighting;
      if (widgets.lighting_preset) widgets.lighting_preset.value = preset.default_lighting;
    }
    onOptionChange();
  };

  const bindSelect = (selEl, wName) => {
    selEl.onchange = () => {
      if (widgets[wName]) widgets[wName].value = selEl.value;
      updateHints();
      onOptionChange();
    };
  };
  bindSelect(selStyle, "style_preset");
  bindSelect(selMedium, "medium_shot");
  bindSelect(selAngle, "camera_angle");
  bindSelect(selLight, "lighting_preset");

  txtSubject.addEventListener("input", () => {
    if (widgets.subject) widgets.subject.value = txtSubject.value;
    onOptionChange();
  });

  txtFinalPrompt.addEventListener("input", () => {
    if (widgets.final_prompt) widgets.final_prompt.value = txtFinalPrompt.value;
    updateWordCount(txtFinalPrompt.value);
    setManual(Boolean(txtFinalPrompt.value.trim()));
    if (isManual()) setStatus("✍️ 已保存你的手动修改，运行时将直接使用上方编辑框中的提示词。");
    else scheduleAssemble();
  });

  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(txtFinalPrompt.value || "");
      setStatus("✅ 已复制提示词到剪贴板。");
    } catch {
      setStatus("复制失败，请手动全选复制。", true);
    }
  };

  function restoreFromWidgets() {
    // Graph loading configures the node before the catalog arrives; the catalog callback restores again.
    if (!catalog) return;
    const curAsset = widgets.asset_type?.value;
    selAsset.value = catalog.asset_types[curAsset] ? curAsset : "character_4view";

    if (widgets.style_preset?.value) selStyle.value = widgets.style_preset.value;
    if (widgets.medium_shot?.value) selMedium.value = widgets.medium_shot.value;
    updateHints();
    if (widgets.camera_angle?.value) selAngle.value = widgets.camera_angle.value;
    if (widgets.lighting_preset?.value) selLight.value = widgets.lighting_preset.value;

    txtSubject.value = widgets.subject?.value ?? "";
    txtFinalPrompt.value = widgets.final_prompt?.value ?? "";

    updateManualLockUI();
    scheduleAssemble();
    syncWidth();
  }

  loadCatalog().then(cat => {
    catalog = cat;
    selAsset.setOptions(cat.asset_types);
    selStyle.setOptions(cat.style_presets);
    selMedium.setOptions(cat.medium_shots);
    selAngle.setOptions(cat.camera_angles);
    selLight.setOptions(cat.lighting_presets);
    restoreFromWidgets();
  });

  const oldConfigure = node.onConfigure;
  node.onConfigure = function (...args) {
    oldConfigure?.apply(this, args);
    restoreFromWidgets();
  };

  node.addDOMWidget("qwen21_video_prompt_ui", "custom", root, {
    serialize: false,
    hideOnZoom: false,
    getMinHeight: () => 600,
    getHeight: () => 760,
    onDraw: widget => {
      widget.width = node.size[0];
      // Pick up changes made on the linked Resolution Selector.
      const key = String(linkedSize());
      if (catalog && key !== lastSizeKey) {
        lastSizeKey = key;
        scheduleAssemble();
      }
    },
  });

  node.qwen21Builder = { root, restore: restoreFromWidgets };
  node.setSize([Math.max(660, node.size[0]), Math.max(740, node.size[1])]);
}

app.registerExtension({
  name: "H3MotionContext.QwenImage21VideoPrompt",
  nodeCreated(node) {
    if (node.comfyClass === "QwenImage21VideoPrompt") installQwen21Builder(node);
  },
  loadedGraphNode(node) {
    if (node.comfyClass === "QwenImage21VideoPrompt") {
      installQwen21Builder(node);
      node.qwen21Builder.restore();
    }
  },
});
