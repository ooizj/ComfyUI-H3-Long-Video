import { t } from "./h3_i18n.js";

// Shared look for the pack's preview dialogs; colors follow the active ComfyUI theme.
const css = document.createElement("style");
css.textContent = `
.h3-dlg,.h3-themed{--h3-bg:var(--comfy-menu-bg,#1f2329);--h3-panel:var(--comfy-menu-secondary-bg,#262b33);--h3-input:var(--comfy-input-bg,#15181d);--h3-fg:var(--fg-color,#e6e6e6);--h3-muted:var(--descrip-text,#9aa3ad);--h3-border:var(--border-color,#3a414b);--h3-accent:var(--p-primary-color,#4f9cf7);--h3-accent-fg:var(--p-primary-contrast-color,#fff)}
.h3-dlg{width:min(1120px,94vw);height:min(780px,90vh);max-width:94vw;max-height:90vh;margin:auto;padding:0;overflow:hidden;border:1px solid var(--h3-border);border-radius:12px;background:var(--h3-bg);color:var(--h3-fg);box-shadow:0 24px 64px #0009;font:13px/1.5 system-ui,sans-serif}
.h3-dlg::backdrop{background:#000a}.h3-dlg *{box-sizing:border-box}
.h3-dlg-shell{display:flex;flex-direction:column;height:100%}
.h3-dlg-header{display:flex;align-items:center;gap:12px;padding:12px 12px 12px 20px;border-bottom:1px solid var(--h3-border)}
.h3-dlg-header h3{margin:0;font-size:16px;font-weight:600;white-space:nowrap}
.h3-dlg-subtitle{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--h3-muted);font-size:12px}
.h3-dlg-body{flex:1;min-height:0;display:flex}
.h3-dlg-list{flex:0 0 250px;overflow:auto;display:flex;flex-direction:column;gap:4px;padding:10px;border-right:1px solid var(--h3-border);background:var(--h3-panel)}
.h3-dlg-main{position:relative;flex:1;min-width:0;overflow:auto;display:flex;flex-direction:column;gap:14px;padding:16px 20px}
.h3-dlg-footer{display:flex;align-items:center;gap:10px;padding:12px 20px;border-top:1px solid var(--h3-border)}
.h3-dlg-hint{flex:1;min-width:0;color:var(--h3-muted);font-size:12px}
.h3-dlg-empty{margin:auto;padding:24px;color:var(--h3-muted);text-align:center;white-space:pre-wrap}
.h3-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:6px 14px;border:1px solid var(--h3-border);border-radius:6px;background:transparent;color:inherit;font:inherit;cursor:pointer;white-space:nowrap}
.h3-btn:hover{background:color-mix(in srgb,var(--h3-fg) 8%,transparent)}.h3-btn:disabled{opacity:.45;cursor:default;background:transparent}
.h3-btn:focus-visible,.h3-card:focus-visible{outline:2px solid var(--h3-accent);outline-offset:1px}
.h3-btn-primary{border-color:var(--h3-accent);background:var(--h3-accent);color:var(--h3-accent-fg);font-weight:600}.h3-btn-primary:hover{background:var(--h3-accent);filter:brightness(1.12)}.h3-btn-primary:disabled{background:var(--h3-accent)}
.h3-btn-icon{width:32px;height:32px;padding:0;border-color:transparent;font-size:16px;line-height:1}
.h3-card{display:flex;gap:10px;align-items:flex-start;width:100%;flex-shrink:0;padding:8px;border:0;border-left:3px solid transparent;border-radius:6px;background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer}
.h3-card:hover{background:color-mix(in srgb,var(--h3-fg) 6%,transparent)}.h3-card[aria-pressed=true]{border-left-color:var(--h3-accent);background:color-mix(in srgb,var(--h3-accent) 16%,transparent)}.h3-card:disabled{opacity:.55;cursor:default}
.h3-card-thumb{flex:0 0 76px;height:50px;display:flex;gap:1px;overflow:hidden;border-radius:4px;background:var(--h3-input)}.h3-card-thumb img,.h3-card-thumb video{flex:1;min-width:0;height:100%;object-fit:cover;pointer-events:none}
.h3-card-text{flex:1;min-width:0}.h3-card-title{font-weight:600}.h3-card-meta{color:var(--h3-muted);font-size:12px}
.h3-clamp{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:12px;overflow-wrap:anywhere}
.h3-badge{display:inline-block;padding:0 6px;border-radius:4px;background:color-mix(in srgb,#e0a84f 25%,transparent);font-size:11px;line-height:18px}
.h3-prompt{user-select:text;line-height:1.7;overflow-wrap:anywhere}.h3-prompt p{margin:0 0 4px;white-space:pre-wrap}
.h3-prompt-heading{margin:14px 0 6px;padding-bottom:3px;border-bottom:1px solid var(--h3-border);color:var(--h3-muted);font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}.h3-prompt-heading:first-child{margin-top:0}
.h3-tag{display:inline-block;margin:0 1px;padding:0 5px;border-radius:4px;background:color-mix(in srgb,var(--h3-accent) 22%,transparent);font-size:12px;line-height:19px;white-space:nowrap}.h3-tag-picture{background:color-mix(in srgb,#e0a84f 28%,transparent)}.h3-shot{color:var(--h3-accent);font-weight:600}
.h3-lightbox{position:absolute;inset:0;z-index:5;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:24px;background:#000d;cursor:zoom-out}.h3-lightbox img{max-width:100%;max-height:calc(100% - 40px);object-fit:contain}
@media(max-width:700px){.h3-dlg-body{flex-direction:column}.h3-dlg-list{flex:0 0 150px;border-right:0;border-bottom:1px solid var(--h3-border)}.h3-dlg-main{padding:12px}}
`;
document.head.append(css);

export function element(tag, className = "", text = "") {
  const el = document.createElement(tag);
  el.className = className;
  el.textContent = text;
  return el;
}

export function button(label, action, className = "h3-btn") {
  const control = element("button", className, label);
  control.type = "button";
  control.onclick = action;
  return control;
}

// A modal with header (title, subtitle, close), a list column, a main column and a footer.
export function openDialog({ title, label, onClose }) {
  const dialog = element("dialog", "h3-dlg");
  dialog.setAttribute("aria-label", label || title);
  const shell = element("div", "h3-dlg-shell");
  const header = element("div", "h3-dlg-header");
  const subtitle = element("div", "h3-dlg-subtitle");
  const close = button("✕", () => dialog.close(), "h3-btn h3-btn-icon");
  close.title = close.ariaLabel = t("关闭", "Close");
  header.append(element("h3", "", title), subtitle, close);
  const body = element("div", "h3-dlg-body");
  const list = element("div", "h3-dlg-list");
  const main = element("div", "h3-dlg-main");
  body.append(list, main);
  const footer = element("div", "h3-dlg-footer");
  shell.append(header, body, footer);
  dialog.append(shell);
  for (const type of ["pointerdown", "pointermove", "pointerup", "mousedown", "dblclick", "keydown", "keyup", "wheel"]) {
    dialog.addEventListener(type, e => e.stopPropagation());
  }
  dialog.addEventListener("close", () => { onClose?.(); dialog.remove(); }, { once: true });
  document.body.append(dialog);
  dialog.showModal();
  return { dialog, subtitle, list, main, footer };
}

export function showLightbox(dialog, src, caption) {
  const box = element("div", "h3-lightbox");
  const img = element("img");
  img.src = src;
  img.alt = caption;
  box.append(img, element("div", "", caption));
  const cancel = e => { e.preventDefault(); hide(); };
  const hide = () => { box.remove(); dialog.removeEventListener("cancel", cancel); };
  box.onclick = hide;
  dialog.addEventListener("cancel", cancel);
  dialog.querySelector(".h3-dlg-shell").append(box);
}

// "name:" lines on their own start a section, as in the H3 prompt layout.
export function promptSections(text) {
  const sections = [{ name: "", lines: [] }];
  for (const line of String(text || "").split(/\r?\n/)) {
    const heading = line.match(/^([a-z][a-z_]*):\s*$/);
    if (heading) sections.push({ name: heading[1], lines: [] });
    else sections.at(-1).lines.push(line);
  }
  return sections.map(s => ({ name: s.name, body: s.lines.join("\n").trim() })).filter(s => s.name || s.body);
}

export function promptSummary(text) {
  const sections = promptSections(text);
  const summary = sections.find(s => s.name === "summary")?.body ?? sections.find(s => s.body)?.body ?? "";
  return summary.replace(/^(\s*\[[^\]]*\])+/, "").replace(/\s+/g, " ").trim();
}

function inline(parent, text) {
  for (const part of text.split(/(<(?:Subject|Picture)\s*\d+>|\[Shot\s*\d+\])/)) {
    if (!part) continue;
    if (part.startsWith("<")) parent.append(element("span", part.startsWith("<Picture") ? "h3-tag h3-tag-picture" : "h3-tag", part.slice(1, -1)));
    else if (part.startsWith("[Shot")) parent.append(element("span", "h3-shot", part));
    else parent.append(part);
  }
}

// Read-only prompt view: section headings, and subject/picture labels as tags. Only textContent is used.
export function renderPrompt(sections) {
  const root = element("div", "h3-prompt");
  for (const section of sections) {
    if (section.name) root.append(element("div", "h3-prompt-heading", section.name.replaceAll("_", " ")));
    for (const paragraph of section.body.split(/\n{2,}/)) {
      const p = element("p");
      inline(p, paragraph);
      root.append(p);
    }
  }
  return root;
}

export function clock(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${(seconds - minutes * 60).toFixed(2).padStart(5, "0")}`;
}

export function dateLabel(date) {
  if (Number.isNaN(date.getTime())) return "";
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(date).setHours(0, 0, 0, 0)) / 86400000);
  if (days === 0) return `${t("今天", "Today")} ${time}`;
  if (days === 1) return `${t("昨天", "Yesterday")} ${time}`;
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return `${date.toLocaleDateString([], { year: sameYear ? undefined : "numeric", month: "numeric", day: "numeric" })} ${time}`;
}
