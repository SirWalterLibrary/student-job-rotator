// Teacher PIN (spec 06 "Unlock / PIN"): locked/unlocked state, the header
// button ("Teacher login" ↔ "Lock"), and the PIN dialog. api.js holds the PIN
// in sessionStorage and dispatches "kr:locked" on any 401.

import { h } from "./dom.js";
import { api, storePin, clearPin, storedPin } from "./api.js";
import { state } from "./app.js"; // referenced at call time only (circular import is safe)
import { openDrawer, closeDrawer } from "./manage.js";

/** Unlocked = no PIN configured, or a PIN is stored in sessionStorage. */
export function isUnlocked() {
  if (state.config === null) return false;
  return !state.config.pin_required || Boolean(storedPin());
}

/** Record the locked/unlocked state and relabel the header button. */
function setUnlocked(value) {
  state.unlocked = value;
  const button = document.getElementById("teacher-tools");
  if (!button) return;
  button.textContent = !state.config.pin_required ? "Teacher tools" : (value ? "Lock" : "Teacher login");
}

/** The PIN dialog element, created once and reused. */
let pinDialog = null;
function ensureDialog() {
  if (pinDialog && pinDialog.isConnected) return pinDialog;
  pinDialog = h("dialog", { id: "pin-dialog" },
    h("div", { class: "pin-head" }, h("h2", { class: "pin-title" }, "Teacher login")),
    h("form", { class: "pin-body" },
      h("label", { for: "pin-input" }, "Enter the teacher PIN"),
      h("input", { id: "pin-input", type: "password", autocomplete: "off" }),
      h("p", { class: "form-error", role: "alert", hidden: true }),
      h("div", { class: "dialog-actions" },
        h("button", { type: "submit", class: "btn btn-primary" }, "Unlock"),
        h("button", { type: "button", class: "btn btn-secondary pin-cancel" }, "Cancel"))));
  document.body.append(pinDialog);
  pinDialog.querySelector("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const ok = await unlock(event.target.querySelector("input").value);
    if (ok) openDrawer(); // the PIN was accepted: open the tools drawer
  });
  pinDialog.querySelector(".pin-cancel").addEventListener("click", () => pinDialog.close());
  return pinDialog;
}

/** Show (or refocus) the PIN dialog with a clean form. */
export function openPinDialog() {
  const box = ensureDialog();
  const input = box.querySelector("input");
  input.value = "";
  const error = box.querySelector(".form-error");
  error.hidden = true;
  error.textContent = "";
  if (!box.open) box.showModal();
  input.focus();
}

/** Check a PIN against POST /api/auth; on success store it and unlock. */
export async function unlock(pin) {
  const box = ensureDialog();
  const input = box.querySelector("input");
  const error = box.querySelector(".form-error");
  try {
    await api.send("POST", "/api/auth", { pin });
  } catch (err) {
    error.hidden = false;
    error.textContent = err.message;
    input.focus();
    return false;
  }
  storePin(pin);
  setUnlocked(true);
  if (box.open) box.close();
  return true;
}

/** Lock: forget the PIN, close the drawer, relabel the header button. */
export function lock() {
  clearPin();
  setUnlocked(false);
  closeDrawer();
}

/** Wire the header button and re-lock + re-open the dialog on any 401. */
export function initAuth() {
  setUnlocked(isUnlocked());
  document.getElementById("teacher-tools").addEventListener("click", () => {
    if (!state.config.pin_required) { openDrawer(); return; }
    if (state.unlocked) lock();
    else openPinDialog();
  });
  window.addEventListener("kr:locked", () => {
    setUnlocked(false);
    closeDrawer();
    openPinDialog();
  });
}
