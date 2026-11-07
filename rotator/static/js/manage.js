// Teacher tools drawer (spec 06): the four accordion sections, focus trap,
// and the queue ("Fairness & up next") and Settings sections. The Students
// and Jobs sections live in manage-roster.js (keeps this file under the
// 250-line rule). Every change needs the PIN (api.js sends it); a 401
// re-locks via kr:locked (handled in auth.js).

import { h, clear, toast } from "./dom.js";
import { api } from "./api.js";
import { state } from "./app.js"; // referenced at call time only (circular import is safe)
import { shortDate } from "./dates.js";
import { renderToday } from "./today.js";
import { renderCalendar } from "./calendar.js";
import { loadStudents, loadJobs } from "./manage-roster.js";

let opener = null; // element that opened the drawer (focus returns to it)
let open = false;

/** Open the drawer: build the four sections, trap focus, load their data. */
export function openDrawer() {
  if (open) return;
  open = true;
  opener = document.activeElement;
  const box = document.getElementById("drawer");
  clear(box);
  box.append(
    h("div", { class: "drawer-head" },
      h("h2", { class: "drawer-title" }, "Teacher tools"),
      h("button", { type: "button", class: "btn btn-secondary drawer-close", "aria-label": "Close teacher tools",
        onclick: () => closeDrawer() }, "✕")),
    section("students", "Students"),
    section("jobs", "Jobs"),
    section("queue", "Fairness & up next"),
    section("settings", "Settings"));
  box.hidden = false;
  box.addEventListener("keydown", trapKey);
  box.querySelector(".drawer-close").focus();
  loadStudents();
  loadJobs();
  loadQueue();
  renderSettings();
}

/** Close the drawer and return focus to the opener. */
export function closeDrawer() {
  if (!open) return;
  open = false;
  const box = document.getElementById("drawer");
  box.hidden = true;
  box.removeEventListener("keydown", trapKey);
  if (opener && opener.isConnected) opener.focus();
}

/** Tab wraps inside the drawer; Esc closes it. */
function trapKey(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    closeDrawer();
    return;
  }
  if (event.key !== "Tab") return;
  const focusables = [...document.getElementById("drawer").querySelectorAll(
    "button, input, select, textarea, [tabindex]:not([tabindex='-1'])")]
    .filter((el) => !el.disabled && el.getClientRects().length > 0);
  if (focusables.length === 0) return;
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

/** One accordion section: a toggle button above a body we fill with data. */
function section(key, title) {
  const body = h("div", { class: "drawer-section-body", id: `sec-${key}` });
  const arrow = h("span", { class: "acc-arrow", "aria-hidden": "true" }, "▾");
  const button = h("button", {
    type: "button", class: "drawer-section-btn", "aria-expanded": "true",
    "aria-controls": `sec-${key}`,
    onclick: () => {
      const expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", expanded ? "false" : "true");
      arrow.textContent = expanded ? "▸" : "▾";
      body.hidden = expanded;
    },
  }, arrow, title);
  return h("section", { class: "drawer-section" }, button, body);
}

/** The body element of a section (fresh on every call, safe after rebuilds). */
export const sectionBody = (key) => document.getElementById(`sec-${key}`);

/** Toast "Saved ✓", refresh every drawer section and the visible tab. */
export async function afterChange() {
  toast("Saved ✓");
  await Promise.all([loadStudents(), loadJobs(), loadQueue()]);
  rerenderTab();
}

/** A one-line "could not load" with a Retry button inside a section body. */
export function errorRow(body, err, reload) {
  clear(body);
  body.append(h("p", { class: "form-error" }, err.message),
    h("button", { type: "button", class: "btn btn-small", onclick: reload }, "Retry"));
}

/** Re-render whichever tab (Today / Calendar) is currently visible. */
function rerenderTab() {
  if (state.tab === "today") renderToday(document.getElementById("panel-today"));
  else if (state.tab === "calendar") renderCalendar(document.getElementById("panel-calendar"), state.month);
}

/* ---------------- Fairness & up next ---------------- */

/** Refresh the queue section from GET /api/queue. */
async function loadQueue() {
  const body = sectionBody("queue");
  let entries;
  try {
    ({ jobs: entries } = await api.get("/api/queue"));
  } catch (err) {
    return errorRow(body, err, loadQueue);
  }
  clear(body);
  for (const entry of entries) {
    body.append(h("h3", { class: "queue-title" }, entry.job.icon ? `${entry.job.icon} ${entry.job.name}` : entry.job.name));
    if (entry.single_volunteer) {
      body.append(h("p", { class: "queue-hint" }, "Only one volunteer — they will do this job every time and can't be given other jobs."));
    }
    if (entry.queue.length === 0) {
      body.append(h("p", { class: "queue-hint" }, "No volunteers yet."));
    } else {
      body.append(h("ol", { class: "queue-list" },
        ...entry.queue.map((person, i) => {
          const meta = `${person.turns} turn${person.turns === 1 ? "" : "s"}` +
            (person.last_served ? `, last ${shortDate(person.last_served)}` : ", never");
          return h("li", { class: i === 0 ? "queue-first" : "" },
            h("span", { class: "roster-name" }, person.student.name),
            h("span", { class: "queue-meta" }, meta));
        })));
    }
  }
  body.append(h("p", { class: "queue-help" }, "Whoever waited longest goes next. Nobody repeats a job until everyone who volunteered has had a turn."));
}

/* ---------------- Settings ---------------- */

/** Build the Settings section (start date + export/import backup). */
function renderSettings() {
  const body = sectionBody("settings");
  clear(body);
  const dateInput = h("input", { id: "start-date", type: "date", value: state.config ? state.config.start_date : "" });
  const error = h("p", { class: "form-error", hidden: true });
  const importFile = h("input", { type: "file", id: "import-file", accept: ".json,application/json" });
  body.append(
    h("div", { class: "setting-row" },
      h("label", { for: "start-date" }, "Class starts on"),
      dateInput,
      h("button", {
        type: "button", class: "btn btn-small btn-primary",
        onclick: async () => {
          try {
            const saved = await api.send("PUT", "/api/settings", { start_date: dateInput.value });
            state.config.start_date = saved.start_date;
            dateInput.value = saved.start_date;
            error.hidden = true;
            toast("Saved ✓");
            rerenderTab();
          } catch (err) {
            error.hidden = false;
            error.textContent = err.message;
          }
        },
      }, "Save")),
    error,
    h("div", { class: "setting-row" },
      h("span", { class: "setting-label" }, "Backup"),
      h("span", { class: "roster-actions" },
        h("button", {
          type: "button", class: "btn btn-small",
          onclick: async () => {
            try {
              const data = await api.get("/api/export");
              const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
              const link = h("a", { href: url, download: `khidmah-roster-${state.config ? state.config.today : "backup"}.json` });
              link.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
              toast("Backup downloaded");
            } catch (err) {
              toast(err.message);
            }
          },
        }, "Export"),
        h("button", {
          type: "button", class: "btn btn-small btn-danger",
          onclick: async () => {
            if (importFile.files.length === 0) {
              error.hidden = false;
              error.textContent = "Choose a backup file first.";
              return;
            }
            if (!window.confirm("This replaces everything. Import this backup?")) return;
            let data;
            try {
              data = JSON.parse(await importFile.files[0].text());
            } catch {
              error.hidden = false;
              error.textContent = "That file is not valid JSON.";
              return;
            }
            try {
              await api.send("POST", "/api/import", data);
              error.hidden = true;
              importFile.value = "";
              await afterChange();
              toast("Backup imported");
            } catch (err) {
              error.hidden = false;
              error.textContent = err.message;
            }
          },
        }, "Import")),
      importFile));
}
