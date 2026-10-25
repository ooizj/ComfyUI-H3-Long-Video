import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { localizer, t } from "./h3_i18n.js";

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
.q21vp textarea:disabled{opacity:.5}
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

// Catalog labels are [zh, en] pairs.
const optionLabel = (opt, key) => (opt ? t(...opt.label) : key);

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

async function postJson(path, body) {
  const resp = await api.fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return resp.json();
}

// Hide the node's own widgets behind the custom editor and return them by name.
function setupPanel(node, hiddenNames) {
  const widgets = Object.fromEntries((node.widgets || []).map(w => [w.name, w]));
  for (const name of hiddenNames) {
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
  return { widgets, root, syncWidth };
}

// Thumbnail pickers share one gallery, opened under the row of the clicked button; one is open at a time.
function createPickers(root) {
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
    const closeBtn = el("button", "", t("收起", "Close"));
    closeBtn.type = "button";
    closeBtn.onclick = closeGallery;
    head.append(el("span", "", `${t(...picker.title)} · ${t("点图选择", "click an image to pick")}`), el("small", "", t(...picker.note)), closeBtn);
    const grid = el("div", "q21vp-gallery-grid");
    for (const [key, opt] of Object.entries(picker.options)) {
      const card = el("button", "q21vp-card");
      card.type = "button";
      card.title = optionLabel(opt, key);
      card.classList.toggle("is-selected", key === picker.value);
      const img = el("img");
      img.alt = "";
      img.loading = "lazy";
      img.src = exampleUrl(picker.group, key);
      img.onerror = () => img.replaceWith(el("div", "q21vp-card-noimg", t("无示例", "No example")));
      card.append(img, el("span", "", shortLabel(optionLabel(opt, key))));
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

  function makePicker(group, title, note) {
    const trigger = el("button", "q21vp-pick");
    trigger.type = "button";
    const thumb = el("img", "q21vp-pick-thumb");
    thumb.alt = "";
    thumb.onerror = () => { thumb.style.visibility = "hidden"; };
    const text = el("span", "q21vp-pick-text", "");
    trigger.append(thumb, text, el("span", "q21vp-pick-caret", "▾"));
    let current = "";
    const picker = {
      el: trigger, group, title, note, options: {}, onchange: null,
      get value() { return current; },
      set value(v) {
        current = v;
        const label = optionLabel(picker.options[v], v);
        text.textContent = shortLabel(label);
        trigger.title = label;
        thumb.style.visibility = "";
        thumb.src = exampleUrl(picker.group, v);
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

  root.addEventListener("keydown", e => {
    if (e.key === "Escape" && openPicker) closeGallery();
  });
  function relabel() {
    for (const p of pickers) p.value = p.value;
    if (openPicker) renderGallery(openPicker);
  }
  return { makePicker, relabel };
}

function field(i18n, label, control) {
  const f = el("div", "q21vp-field");
  f.append(i18n.set(el("div", "q21vp-label"), ...label), control);
  return f;
}

// Preview box: shows the assembled prompt; a manual edit is output as-is until the user unlocks it.
function createPreview(widgets, i18n, title, onRefresh) {
  const sec = el("div", "q21vp-sec");
  const header = el("div", "q21vp-sec-title");
  const titleSpan = el("span", "", "");
  const actions = el("div", "q21vp-preview-actions");
  const wordCount = el("small", "", "");
  const unlockBtn = i18n.set(el("button"), "🔄 恢复自动生成", "🔄 Back to automatic");
  unlockBtn.type = "button";
  unlockBtn.hidden = true;
  const copyBtn = i18n.set(el("button"), "📋 复制", "📋 Copy");
  copyBtn.type = "button";
  actions.append(wordCount, unlockBtn, copyBtn);
  header.append(titleSpan, actions);
  const txt = el("textarea", "q21vp-preview-box");
  const statusEl = el("div", "q21vp-status", "");
  sec.append(header, txt, statusEl);

  const preview = {
    sec,
    setStatus(msg, isWarn = false) {
      statusEl.textContent = msg || "";
      statusEl.classList.toggle("q21vp-warn", Boolean(isWarn));
    },
    isManual: () => Boolean(widgets.manual_prompt?.value) && Boolean(txt.value.trim()),
    updateLockUI() {
      const manual = preview.isManual();
      unlockBtn.hidden = !manual;
      titleSpan.textContent = manual
        ? t(`📤 ${title[0]}：当前使用你手动修改的版本 (已锁定)`, `📤 ${title[1]}: using your hand-edited version (locked)`)
        : t(`📤 ${title[0]} (可直接微调)`, `📤 ${title[1]} (edit to adjust)`);
    },
    setManual(on) {
      if (widgets.manual_prompt) widgets.manual_prompt.value = on;
      preview.updateLockUI();
    },
    show(text) {
      if (!preview.isManual()) {
        txt.value = text || "";
        if (widgets.final_prompt) widgets.final_prompt.value = txt.value;
      }
      const words = txt.value.trim().split(/\s+/).filter(Boolean).length;
      wordCount.textContent = t(`${words} 词`, `${words} words`);
    },
    restore() {
      txt.value = widgets.final_prompt?.value ?? "";
      preview.updateLockUI();
    },
    warnIfManual() {
      if (preview.isManual()) {
        preview.setStatus(t("⚠️ 当前使用你手动修改的版本，修改的选项不会生效；点击「🔄 恢复自动生成」放弃手动修改。",
          "⚠️ Your hand-edited version is in use, so option changes have no effect. Click \"🔄 Back to automatic\" to discard the edit."), true);
      }
    },
  };

  unlockBtn.onclick = () => {
    preview.setManual(false);
    onRefresh();
    preview.setStatus(t("已恢复为自动生成模式。", "Back to automatic prompt."));
  };
  txt.addEventListener("input", () => {
    if (widgets.final_prompt) widgets.final_prompt.value = txt.value;
    preview.setManual(Boolean(txt.value.trim()));
    if (preview.isManual()) preview.setStatus(t("✍️ 已保存你的手动修改，运行时将直接使用编辑框中的内容。", "✍️ Your edit is saved; the run uses the text in this box as-is."));
    else onRefresh();
  });
  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(txt.value || "");
      preview.setStatus(t("✅ 已复制到剪贴板。", "✅ Copied to the clipboard."));
    } catch {
      preview.setStatus(t("复制失败，请手动全选复制。", "Copy failed; select the text and copy it by hand."), true);
    }
  };
  return preview;
}

function debounce(fn, ms) {
  let timer = null;
  return () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(fn, ms);
  };
}

function installQwen21Builder(node) {
  if (node.qwen21Builder) return;
  const { widgets, root, syncWidth } = setupPanel(node, [
    "asset_type", "style_preset", "medium_shot", "camera_angle", "lighting_preset", "subject", "manual_prompt", "final_prompt",
  ]);

  let catalog = null;
  let lastSizeKey = "";
  let promptLinked = false;
  const schedule = debounce(() => runAssemble(), 120);
  const i18n = localizer(() => { relabel(); preview.updateLockUI(); schedule(); });

  const header = el("div", "q21vp-header");
  const titleWrap = el("div", "q21vp-title");
  titleWrap.append(el("span", "", "🎬 Qwen Image 2.1 Prompt Builder"));
  const sizeBadge = el("span", "q21vp-badge", t("宽高未连接", "Size not linked"));
  i18n.set(sizeBadge, "width / height 接「分辨率选择器」，提示词按宽高写横图、竖图或方图",
    "Link width / height from Resolution Selector; the prompt names the frame wide, vertical or square to match", "title");
  titleWrap.append(sizeBadge);
  header.append(titleWrap);
  root.append(header);

  // Step 1: person or scene description
  const heroSec = el("div", "q21vp-hero-sec");
  const heroTitle = el("div", "q21vp-hero-title");
  heroTitle.append(i18n.set(el("span"), "✏️ 第一步：输入你要生成的人物或场景描述", "✏️ Step 1: describe the person or scene to generate"));
  const clearInputBtn = i18n.set(el("button"), "🗑️ 清空", "🗑️ Clear");
  clearInputBtn.type = "button";
  heroTitle.append(clearInputBtn);
  const txtSubject = i18n.set(el("textarea", "q21vp-hero-input"),
    "在这里输入描述（然后在下方【第二步】选择对应的资产类型）：\n" +
    "• 人物设定卡：写人物年龄、发型、五官、上衣、下装、鞋子（如：一个亚洲女性，高马尾，穿米白色针织开衫与深蓝牛仔裤）\n" +
    "• 纯场景空镜：写环境与家具陈设（如：温馨的现代极简客厅，浅橡木地板，米白布艺沙发与落地窗阳光）\n" +
    "• 视频关键帧：写角色动作、所处环境与镜头感（选胸像/半身时不要写裤子和鞋）",
    "Write the description here, then pick the matching asset type in Step 2 below:\n" +
    "• Character sheet: age, hairstyle, face, top, bottoms and shoes (e.g. an Asian woman with a high ponytail, cream knit cardigan and dark blue jeans)\n" +
    "• Empty scene card: the setting and furniture (e.g. a cosy minimalist living room, light oak floor, cream fabric sofa, sunlight through tall windows)\n" +
    "• Video keyframe: the character's action, surroundings and camera feel (for a bust or waist-up shot, leave out trousers and shoes)",
    "placeholder");
  const linkedHint = i18n.set(el("div", "q21vp-hint"), "🔗 已连接 prompt 输入：运行时用上游文本作为描述，这里不用填写。",
    "🔗 prompt is linked: the run uses the linked text as the description, so nothing is needed here.");
  linkedHint.hidden = true;
  heroSec.append(heroTitle, txtSubject, linkedHint);
  root.append(heroSec);

  // Step 2: asset type and style
  const secPreset = el("div", "q21vp-sec");
  secPreset.append(i18n.set(el("div", "q21vp-sec-title"), "🎯 第二步：选择图片类型与视觉风格（点按钮看示例图）", "🎯 Step 2: pick the image type and visual style (click a button to see examples)"));
  const { makePicker, relabel } = createPickers(root);
  const note = ["示例图：同一 seed、同一段描述，只改这一项", "Examples: same seed and description, only this option changes"];
  const labels = {
    asset: ["① 视频图片资产类型", "① Asset type"],
    style: ["② 画面视觉风格", "② Visual style"],
    medium: ["③ 景别", "③ Shot size"],
    angle: ["④ 摄影机位视角", "④ Camera angle"],
    light: ["⑤ 光影氛围预设", "⑤ Lighting"],
  };
  const selAsset = makePicker("asset_type", labels.asset, note);
  const selStyle = makePicker("style_preset", labels.style, note);
  const selMedium = makePicker("medium_shot", labels.medium, note);
  const selAngle = makePicker("camera_angle", labels.angle, note);
  const selLight = makePicker("lighting_preset", labels.light, note);
  for (const pair of [
    [field(i18n, labels.asset, selAsset.el), field(i18n, labels.style, selStyle.el)],
    [field(i18n, labels.medium, selMedium.el), field(i18n, labels.angle, selAngle.el)],
    [field(i18n, labels.light, selLight.el)],
  ]) {
    const row = el("div", "q21vp-grid2");
    row.append(...pair);
    secPreset.append(row);
  }
  const mediumHint = i18n.set(el("div", "q21vp-hint"), "💡 胸像/半身：描述里不要写裤子、鞋子等画面外的东西，否则模型会画成全身。",
    "💡 Bust or waist-up: leave trousers, shoes and anything else outside the frame out of the description, or the model draws a full-length figure.");
  mediumHint.hidden = true;
  secPreset.append(mediumHint);
  root.append(secPreset);

  // Step 3: prompt preview and manual edits
  const preview = createPreview(widgets, i18n, ["第三步：生成的提示词", "Step 3: generated prompt"], () => schedule());
  preview.sec.append(i18n.set(el("div", "q21vp-hint"), "💡 描述写得简短时，可在官方 Qwen Image 2.1 流程中开启 refine_prompt，由官方扩写模型补全画面细节。",
    "💡 For a short description, turn on refine_prompt in the official Qwen Image 2.1 workflow to let its rewrite model fill in the details."));
  const negLabel = i18n.set(el("div", "q21vp-label"), "Negative Prompt（negative_prompt 输出；cfg 为 1 时不生效）", "Negative prompt (negative_prompt output; no effect at cfg 1)");
  negLabel.style.marginTop = "8px";
  const txtNegPreview = el("textarea");
  txtNegPreview.readOnly = true;
  txtNegPreview.style.minHeight = "38px";
  txtNegPreview.style.marginTop = "4px";
  preview.sec.append(negLabel, txtNegPreview);
  root.append(preview.sec);

  function onOptionChange() {
    preview.warnIfManual();
    schedule();
    node.setDirtyCanvas(true, true);
  }

  function updateHints() {
    mediumHint.hidden = !["bust_headroom", "medium_waist"].includes(selMedium.value);
  }

  // A scene card hides the person-only shots and angles and shows scene examples for the framing options.
  function applyAssetScope() {
    const noPeople = Boolean(catalog.asset_types[selAsset.value]?.no_people);
    const scoped = map => (noPeople ? Object.fromEntries(Object.entries(map).filter(([k]) => !catalog.person_only.includes(k))) : map);
    for (const [picker, group, map, wName] of [
      [selMedium, "medium_shot", catalog.medium_shots, "medium_shot"],
      [selAngle, "camera_angle", catalog.camera_angles, "camera_angle"],
      [selLight, "lighting_preset", catalog.lighting_presets, "lighting_preset"],
    ]) {
      picker.group = noPeople ? `${group}_scene` : group;
      picker.setOptions(scoped(map));
      if (widgets[wName]) widgets[wName].value = picker.value;
    }
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

  async function runAssemble() {
    const size = linkedSize();
    sizeBadge.textContent = size ? `${size[0]} × ${size[1]}` : t("宽高未连接", "Size not linked");
    try {
      const data = await postJson("/h3_motion_context/qwen21_assemble", {
        asset_type: selAsset.value,
        width: size?.[0],
        height: size?.[1],
        style_preset: selStyle.value,
        medium_shot: selMedium.value,
        camera_angle: selAngle.value,
        lighting_preset: selLight.value,
        subject: txtSubject.value,
      });
      txtNegPreview.value = data.negative_prompt || "";
      preview.show(data.prompt);
      if (promptLinked) {
        preview.setStatus(t("🔗 prompt 已连接：运行时使用上游文本，预览中的主体只是占位。",
          "🔗 prompt is linked: the run uses the linked text; the subject in this preview is a placeholder."));
      }
    } catch (err) {
      preview.setStatus(t(`同步参数出错: ${err.message}`, `Could not update the prompt: ${err.message}`), true);
    }
  }

  selAsset.onchange = () => {
    if (widgets.asset_type) widgets.asset_type.value = selAsset.value;
    const preset = catalog?.asset_types?.[selAsset.value];
    if (preset) {
      selMedium.value = preset.default_medium;
      if (widgets.medium_shot) widgets.medium_shot.value = preset.default_medium;
      selLight.value = preset.default_lighting;
      if (widgets.lighting_preset) widgets.lighting_preset.value = preset.default_lighting;
      applyAssetScope();
    }
    updateHints();
    onOptionChange();
  };
  for (const [picker, wName] of [[selStyle, "style_preset"], [selMedium, "medium_shot"], [selAngle, "camera_angle"], [selLight, "lighting_preset"]]) {
    picker.onchange = () => {
      if (widgets[wName]) widgets[wName].value = picker.value;
      updateHints();
      onOptionChange();
    };
  }
  txtSubject.addEventListener("input", () => {
    if (widgets.subject) widgets.subject.value = txtSubject.value;
    onOptionChange();
  });
  clearInputBtn.onclick = () => {
    txtSubject.value = "";
    if (widgets.subject) widgets.subject.value = "";
    preview.setManual(false);
    schedule();
    txtSubject.focus();
    preview.setStatus(t("已清空输入内容。", "Description cleared."));
  };

  // A linked prompt, e.g. from Image to Prompt, replaces the Step 1 description at run time.
  function updatePromptLink() {
    const linked = node.inputs?.some(input => input.name === "prompt" && input.link != null) ?? false;
    if (linked === promptLinked) return;
    promptLinked = linked;
    txtSubject.disabled = linked;
    clearInputBtn.disabled = linked;
    linkedHint.hidden = !linked;
    if (!linked) preview.setStatus("");
    if (catalog) schedule();
  }

  function restoreFromWidgets() {
    // Graph loading configures the node before the catalog arrives; the catalog callback restores again.
    if (!catalog) return;
    const curAsset = widgets.asset_type?.value;
    selAsset.value = catalog.asset_types[curAsset] ? curAsset : "character_4view";
    if (widgets.style_preset?.value) selStyle.value = widgets.style_preset.value;
    if (widgets.medium_shot?.value) selMedium.value = widgets.medium_shot.value;
    if (widgets.camera_angle?.value) selAngle.value = widgets.camera_angle.value;
    if (widgets.lighting_preset?.value) selLight.value = widgets.lighting_preset.value;
    applyAssetScope();
    updateHints();
    txtSubject.value = widgets.subject?.value ?? "";
    preview.restore();
    updatePromptLink();
    schedule();
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
  const oldConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function (...args) {
    oldConnectionsChange?.apply(this, args);
    updatePromptLink();
  };
  const oldRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    i18n.dispose();
    oldRemoved?.apply(this, args);
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
        schedule();
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
