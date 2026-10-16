import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { localizer, t } from "./h3_i18n.js";
import { button as dialogButton, dateLabel, openDialog, promptSections, promptSummary, renderPrompt, showLightbox } from "./h3_dialog.js";

const css = document.createElement("style");
css.textContent = `
.h3-backup{box-sizing:border-box;display:flex;flex-direction:column;gap:10px;width:100%;height:100%;overflow:auto;padding:14px;background:#131b23;color:#e4ebf2;border:1px solid #344352;border-radius:9px;font:13px/1.5 system-ui,sans-serif;cursor:default}
.h3-backup *{box-sizing:border-box}.h3-backup button{border:1px solid #405366;background:#223343;border-radius:5px;padding:5px 10px;color:inherit;font:inherit;cursor:pointer}.h3-backup button:hover{background:#30485c}.h3-backup button:disabled{opacity:.4;cursor:default}.h3-backup button:focus-visible,.h3-backup textarea:focus{outline:1px solid #75cabc}
.h3-backup-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.h3-backup-gallery{display:flex;gap:8px;flex-shrink:0;overflow-x:auto;min-height:150px;padding:4px 0 10px;scrollbar-color:#648f9f #0b131b}.h3-backup-card{flex:0 0 142px;border:1px solid #344d5d;border-radius:6px;padding:6px;background:#1b2732}.h3-backup-card img{display:block;width:128px;height:90px;object-fit:contain;background:#10161c;cursor:pointer}.h3-backup-card strong{display:block;color:#8bdbcb;text-align:center;font-size:12px}.h3-backup-card button{padding:2px 7px}.h3-backup-card .h3-backup-row{gap:3px;justify-content:center}
.h3-backup textarea{flex:1;min-height:180px;width:100%;resize:none;padding:10px;border:1px solid #344352;border-radius:5px;background:#0c141c;color:inherit;font:13px/1.6 system-ui,sans-serif}.h3-backup-path,.h3-backup-status{white-space:pre-wrap;overflow-wrap:anywhere;user-select:text;color:#a6b7c6;font-size:12px}.h3-backup .h3-backup-primary{background:#275b53;border-color:#559486}.h3-backup-empty{align-self:center;color:#a6b7c6}.h3-backup-status:empty{display:none}
.h3-backup-strip{display:flex;gap:10px;overflow-x:auto;flex-shrink:0;padding-bottom:4px}.h3-backup-strip figure{position:relative;flex-shrink:0;margin:0}.h3-backup-strip img{display:block;height:150px;max-width:260px;object-fit:contain;border-radius:6px;background:var(--h3-input);cursor:zoom-in}.h3-backup-strip .h3-badge{position:absolute;left:6px;top:6px;background:#000b;color:#fff}
`;
document.head.append(css);

function element(tag, className = "", text = "") {
  const el = document.createElement(tag);
  el.className = className;
  el.textContent = text;
  return el;
}

function viewUrl(path) {
  const match = path.match(/ \[(input|output|temp)\]$/);
  const name = (match ? path.slice(0, match.index) : path).replaceAll("\\", "/");
  const slash = name.lastIndexOf("/");
  return api.apiURL(`/view?${new URLSearchParams({
    filename: name.slice(slash + 1), subfolder: name.slice(0, Math.max(0, slash)), type: match?.[1] || "input",
  })}`);
}

function install(node) {
  if (node.h3PromptBackup) return;
  const widgets = Object.fromEntries(node.widgets.map(widget => [widget.name, widget]));
  for (const name of ["pictures", "prompt"]) {
    const widget = widgets[name];
    widget.hidden = true;
    widget.options = { ...widget.options, hidden: true };
    widget.draw = () => {};
    widget.computeSize = () => [0, -4];
    if (widget.inputEl) widget.inputEl.hidden = true;
    if (widget.element) widget.element.hidden = true;
  }
  const root = element("div", "h3-backup");
  root.tabIndex = 0;
  // Nodes 2.0 zooms on wheel unless the focused element sits inside data-capture-wheel.
  root.dataset.captureWheel = "true";
  for (const type of ["pointerdown", "pointermove", "pointerup", "mousedown", "dblclick", "keydown", "keyup", "wheel"]) {
    root.addEventListener(type, e => {
      if (type === "keydown" && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") return;
      e.stopPropagation();
    });
  }
  let busy = false;
  let replacing = null;
  let directory = "output/h3_prompt_backups";
  const i18n = localizer(() => { renderGallery(); showLocation(); });
  const pictures = () => JSON.parse(widgets.pictures.value || "[]");
  const changed = () => { node.graph?.change(); node.setDirtyCanvas(true); };
  const button = (label, action, parent) => {
    const control = element("button", "", label);
    control.type = "button";
    control.onclick = action;
    parent.append(control);
    return control;
  };
  const toolbar = element("div", "h3-backup-row");
  const picker = element("input");
  picker.type = "file";
  picker.accept = "image/*";
  picker.hidden = true;
  const add = i18n.set(button("", () => { replacing = null; picker.multiple = true; picker.click(); }, toolbar), "＋ 添加图片", "＋ Add images");
  const count = element("span");
  toolbar.append(count, picker);
  const gallery = element("div", "h3-backup-gallery");
  const label = i18n.set(element("label"), "提示词", "Prompt");
  const prompt = element("textarea");
  i18n.set(prompt, "输入或粘贴提示词…", "Type or paste a prompt…", "placeholder");
  i18n.set(prompt, "提示词", "Prompt", "ariaLabel");
  prompt.spellcheck = false;
  prompt.oninput = () => { widgets.prompt.value = prompt.value; changed(); };
  const footer = element("div", "h3-backup-row");
  const backup = button("backup", () => void save(), footer);
  backup.className = "h3-backup-primary";
  const load = button("load", () => void browseBackups(), footer);
  let backupDialog = null;
  const location = element("div", "h3-backup-path");
  const showLocation = () => { location.textContent = t("备份目录：", "Backup folder: ") + directory; };
  const status = element("div", "h3-backup-status");
  status.setAttribute("role", "status");
  root.append(toolbar, gallery, label, prompt, footer, location, status);

  function renderGallery() {
    gallery.replaceChildren();
    const paths = pictures();
    count.textContent = t(`${paths.length} 张`, `${paths.length} images`);
    paths.forEach((path, index) => {
      const card = element("div", "h3-backup-card");
      const img = element("img");
      img.src = viewUrl(path);
      img.alt = `<Picture ${index + 1}>`;
      img.title = `${path}\n${t("点击插入图片引用", "Click to insert image label")}`;
      img.draggable = false;
      img.onclick = () => {
        if (busy) return;
        prompt.focus();
        prompt.setRangeText(img.alt, prompt.selectionStart, prompt.selectionEnd, "end");
        prompt.dispatchEvent(new Event("input"));
      };
      const actions = element("div", "h3-backup-row");
      card.append(img, element("strong", "", img.alt), actions);
      const left = button("←", () => move(index, index - 1), actions);
      left.title = t("向前移动", "Move earlier"); left.disabled = busy || index === 0;
      const right = button("→", () => move(index, index + 1), actions);
      right.title = t("向后移动", "Move later"); right.disabled = busy || index === paths.length - 1;
      button(t("换", "Swap"), () => { replacing = index; picker.multiple = false; picker.click(); }, actions).disabled = busy;
      button("×", () => reorder(paths.map((_, i) => i).filter(i => i !== index)), actions).disabled = busy;
      gallery.append(card);
    });
    if (!paths.length) gallery.append(element("div", "h3-backup-empty", t("添加、拖入或粘贴图片", "Add, drop or paste images")));
    add.disabled = backup.disabled = load.disabled = prompt.readOnly = busy;
  }

  function reorder(order) {
    if (busy) return;
    const paths = pictures();
    prompt.value = prompt.value.replace(/<Picture\s+(\d+)>/g, (label, number) => {
      const old = Number(number) - 1;
      if (old < 0 || old >= paths.length) return label;
      const next = order.indexOf(old);
      return next < 0 ? t("<Picture 已删除>", "<Picture deleted>") : `<Picture ${next + 1}>`;
    });
    widgets.prompt.value = prompt.value;
    widgets.pictures.value = JSON.stringify(order.map(index => paths[index]));
    renderGallery(); changed();
  }

  function move(from, to) {
    const order = pictures().map((_, index) => index);
    order.splice(to, 0, order.splice(from, 1)[0]);
    reorder(order);
  }

  async function upload(files, replaceIndex = null) {
    if (busy) return;
    const images = [...files].filter(file => file.type.startsWith("image/"));
    if (!images.length) return;
    busy = true; renderGallery();
    status.textContent = t("正在添加图片…", "Adding images…");
    try {
      for (const file of images) {
        const form = new FormData();
        form.append("image", file); form.append("type", "input"); form.append("subfolder", "h3_prompt_backup");
        const response = await api.fetchApi("/upload/image", { method: "POST", body: form });
        if (!response.ok) throw new Error(t(`图片上传失败：HTTP ${response.status}`, `Image upload failed: HTTP ${response.status}`));
        const result = await response.json();
        const path = `${result.subfolder ? result.subfolder + "/" : ""}${result.name} [${result.type || "input"}]`;
        const paths = pictures();
        if (replaceIndex === null) paths.push(path); else paths[replaceIndex] = path;
        widgets.pictures.value = JSON.stringify(paths);
        if (replaceIndex !== null) break;
      }
      status.textContent = "";
    } catch (error) { status.textContent = error.message; }
    finally { busy = false; renderGallery(); changed(); }
  }
  picker.onchange = () => { void upload(picker.files, replacing); picker.value = ""; };
  root.addEventListener("dragover", e => { e.preventDefault(); e.stopPropagation(); });
  root.addEventListener("drop", e => { e.preventDefault(); e.stopPropagation(); void upload(e.dataTransfer.files); });
  root.addEventListener("paste", e => {
    if (e.clipboardData.files.length) { e.preventDefault(); e.stopPropagation(); void upload(e.clipboardData.files); }
  });

  async function save() {
    if (busy) return;
    busy = true; renderGallery();
    status.textContent = t("正在备份…", "Backing up…");
    try {
      const response = await api.fetchApi("/h3_motion_context/prompt_backup", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.value, pictures: pictures() }),
      });
      if (response.status === 404) throw new Error(t("请重启 ComfyUI 并刷新页面，以加载备份功能。", "Restart ComfyUI and reload the page to enable backups."));
      const result = await response.json();
      if (!response.ok) throw new Error(t("备份失败：", "Backup failed: ") + (result.error || `HTTP ${response.status}`));
      directory = result.directory; showLocation();
      status.textContent = t(`已备份 ${result.image_count} 张图片和提示词`, `Backed up ${result.image_count} images and the prompt`) + `\n${result.backup_path}`;
      node.properties.h3_backup_path = result.backup_path;
      changed();
    } catch (error) { status.textContent = error.message; }
    finally { busy = false; renderGallery(); }
  }

  async function browseBackups() {
    if (busy) return;
    busy = true; renderGallery();
    const listController = new AbortController();
    let previewController = null;
    let selected = null;
    const ui = openDialog({
      title: t("加载备份", "Load backup"),
      label: t("预览并载入备份", "Preview and load a backup"),
      onClose: () => { listController.abort(); previewController?.abort(); backupDialog = null; busy = false; renderGallery(); },
    });
    backupDialog = ui.dialog;
    ui.list.append(element("div", "h3-dlg-empty", t("正在读取备份…", "Reading backups…")));
    const where = element("div", "h3-dlg-hint");
    const copy = dialogButton(t("复制路径", "Copy path"), async () => {
      await navigator.clipboard?.writeText(selected.backup_path);
      copy.textContent = t("已复制", "Copied");
      setTimeout(() => { copy.textContent = t("复制路径", "Copy path"); }, 1200);
    });
    copy.hidden = true;
    const apply = dialogButton(t("载入所选备份", "Load selected backup"), () => {
      widgets.pictures.value = JSON.stringify(selected.pictures);
      widgets.prompt.value = prompt.value = selected.prompt;
      node.properties.h3_backup_path = selected.backup_path;
      status.textContent = t(`已载入 ${selected.pictures.length} 张图片和提示词`, `Loaded ${selected.pictures.length} images and the prompt`) + `\n${selected.backup_path}`;
      changed();
      ui.dialog.close();
    }, "h3-btn h3-btn-primary");
    apply.disabled = true;
    apply.title = t("载入会替换当前节点中的图片和提示词", "Loading replaces this node's images and prompt");
    ui.footer.append(where, copy, dialogButton(t("取消", "Cancel"), () => ui.dialog.close()), apply);

    async function previewEntry(entry, control) {
      previewController?.abort();
      const controller = new AbortController();
      previewController = controller;
      selected = null; apply.disabled = true; copy.hidden = true;
      for (const item of ui.list.children) item.setAttribute("aria-pressed", String(item === control));
      ui.main.replaceChildren(element("div", "h3-dlg-empty", t("正在读取预览…", "Reading preview…")));
      try {
        const response = await api.fetchApi(`/h3_motion_context/prompt_backups/${encodeURIComponent(entry.id)}`, {
          signal: controller.signal, cache: "no-store",
        });
        const result = await response.json();
        if (controller.signal.aborted || !ui.dialog.open) return;
        if (!response.ok) throw new Error(t("读取备份失败：", "Could not read backup: ") + (result.error || `HTTP ${response.status}`));
        const time = dateLabel(new Date(result.created_at)) || result.id;
        const count = result.prompt.length.toLocaleString();
        ui.subtitle.textContent = `${time} · ${t(`${result.pictures.length} 张图片`, `${result.pictures.length} images`)} · ${t(`${count} 字`, `${count} characters`)}`;
        const gallery = element("div", "h3-backup-strip");
        for (const [index, path] of result.pictures.entries()) {
          const figure = element("figure");
          const img = element("img");
          const label = `Picture ${index + 1}`;
          img.src = viewUrl(path); img.alt = label; img.title = t("点击放大", "Click to enlarge");
          img.onclick = () => showLightbox(ui.dialog, img.src, label);
          figure.append(img, element("span", "h3-badge", label));
          gallery.append(figure);
        }
        // Summary first: it says what the backup is about; the rest keeps its order.
        const sections = promptSections(result.prompt);
        const ordered = [...sections.filter(s => s.name === "summary"), ...sections.filter(s => s.name !== "summary")];
        const text = ordered.length ? renderPrompt(ordered) : element("div", "h3-dlg-empty", t("（空提示词）", "(empty prompt)"));
        ui.main.replaceChildren(...(result.pictures.length ? [gallery] : []), text);
        where.textContent = `h3_prompt_backups/${result.id}`;
        where.title = result.backup_path;
        selected = result; apply.disabled = false; copy.hidden = !navigator.clipboard;
      } catch (error) {
        if (!controller.signal.aborted && ui.dialog.open) ui.main.replaceChildren(element("div", "h3-dlg-empty", error.message));
      }
    }

    try {
      const response = await api.fetchApi("/h3_motion_context/prompt_backups", {
        signal: listController.signal, cache: "no-store",
      });
      if (response.status === 404) throw new Error(t("请重启 ComfyUI 并刷新页面，以加载备份列表。", "Restart ComfyUI and reload the page to list backups."));
      const result = await response.json();
      if (listController.signal.aborted || !ui.dialog.open) return;
      if (!response.ok) throw new Error(t("读取备份列表失败：", "Could not list backups: ") + (result.error || `HTTP ${response.status}`));
      ui.list.replaceChildren();
      let first = null;
      for (const entry of result.backups) {
        const control = dialogButton("", null, "h3-card");
        control.setAttribute("aria-pressed", "false");
        control.title = entry.id;
        const thumb = element("div", "h3-card-thumb");
        for (const cover of entry.covers || []) {
          const img = element("img");
          img.src = viewUrl(cover); img.alt = ""; img.loading = "lazy";
          thumb.append(img);
        }
        const text = element("div", "h3-card-text");
        text.append(element("div", "h3-card-title", dateLabel(new Date(entry.created_at)) || entry.id));
        control.append(thumb, text);
        if (entry.error) {
          text.append(element("div", "h3-card-meta", t("无法读取：", "Unreadable: ") + entry.error));
          control.disabled = true;
        } else {
          text.append(element("div", "h3-card-meta", t(`${entry.image_count} 张图片`, `${entry.image_count} images`)),
            element("div", "h3-clamp", promptSummary(entry.prompt) || t("（空提示词）", "(empty prompt)")));
          control.onclick = () => void previewEntry(entry, control);
          first ??= { entry, control };
        }
        ui.list.append(control);
      }
      if (first) void previewEntry(first.entry, first.control);
      else ui.main.replaceChildren(element("div", "h3-dlg-empty", result.backups.length ? t("没有可载入的备份，请检查列表中的错误。", "No loadable backups; check the errors in the list.") : t("暂无备份，先点击 backup 保存。", "No backups yet; click backup to save one.")));
    } catch (error) {
      if (!listController.signal.aborted && ui.dialog.open) {
        ui.list.replaceChildren();
        ui.main.replaceChildren(element("div", "h3-dlg-empty", error.message));
      }
    }
  }

  const oldRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    backupDialog?.close();
    i18n.dispose();
    oldRemoved?.apply(this, args);
  };

  const syncWidth = () => { root.style.width = `${Math.max(1, node.size[0] - 20)}px`; };
  const oldResize = node.onResize;
  node.onResize = function (...args) { oldResize?.apply(this, args); syncWidth(); };
  function restore() {
    if (node.title === "H3 Image & Prompt Backup") node.title = "H3 Image & Prompt";
    prompt.value = widgets.prompt.value ?? "";
    status.textContent = node.properties.h3_backup_path ? t("上次备份：", "Last backup: ") + node.properties.h3_backup_path : "";
    renderGallery(); showLocation(); syncWidth();
  }
  const oldConfigure = node.onConfigure;
  node.onConfigure = function (...args) { oldConfigure?.apply(this, args); restore(); };
  node.addDOMWidget("h3_backup_editor", "custom", root, {
    serialize: false, hideOnZoom: false, getMinHeight: () => 480, getHeight: () => 570,
    onDraw: widget => { widget.width = node.size[0]; },
  });
  node.h3PromptBackup = { restore };
  node.setSize([Math.max(600, node.size[0]), Math.max(650, node.size[1])]);
  restore();
  void (async () => {
    try {
      const response = await api.fetchApi("/h3_motion_context/prompt_backup");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      directory = result.directory; showLocation();
    } catch { status.textContent = t("无法读取备份目录，请重启 ComfyUI 并刷新页面。", "Could not read the backup folder; restart ComfyUI and reload the page."); }
  })();
}

app.registerExtension({
  name: "H3MotionContext.PromptBackup",
  nodeCreated(node) { if (node.comfyClass === "MiniMaxH3PromptBackup") install(node); },
  loadedGraphNode(node) { if (node.comfyClass === "MiniMaxH3PromptBackup") { install(node); node.h3PromptBackup.restore(); } },
});
