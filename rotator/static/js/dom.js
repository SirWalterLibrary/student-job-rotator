// Tiny DOM helpers. Children are strings (text nodes) or elements — never HTML.

/**
 * Create an element with attributes and children.
 * attrs: class, id, type, value, title, lang, dir, role, aria-* and other
 * plain attributes (boolean true sets it); keys starting with "on" plus a
 * function value are registered as event listeners. Strings become text nodes,
 * elements are appended as-is, null/undefined are skipped.
 */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (typeof value === "function" && key.startsWith("on")) {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

/** Remove every child of el. */
export function clear(el) {
  el.replaceChildren();
}

/** Show a brief toast (bottom center) that fades away on its own. */
let host = null;
export function toast(message) {
  if (!host) {
    host = h("div", { class: "toast-host", role: "status", "aria-live": "polite" });
    document.body.append(host);
  }
  const item = h("div", { class: "toast" }, message);
  host.append(item);
  setTimeout(() => item.remove(), 3200);
}
