// Tab 1: Today / Next Weekend (specs 06 + 07).
// "Today" always comes from the server (/api/today); the UI only formats it.

import { h, clear } from "./dom.js";
import { api } from "./api.js";
import { state } from "./app.js"; // referenced at call time only (circular import is safe)
import { isUnlocked } from "./auth.js";
import { hijriDate, longDate, monthName, weekdayName } from "./dates.js";
import { openAbsentDialog, openShiftDialog, openRestoreConfirm, openChangeDialog, clearAssignment } from "./actions.js";

const REFRESH_MS = 5 * 60 * 1000;

let panel = null;       // #panel-today, set on the first renderToday()
let timer = null;       // the one shared 5-minute interval
let lastToday = null;   // today from the last successful /api/today response
let inflight = false;   // guard against overlapping loads
let lastData = null;    // last successful /api/today response (re-render on lock change)
let lockListenerOn = false; // the single kr:lockchange listener

/** Label the Tab 1 button from the /api/today mode ("today" | "upcoming"). */
export function setTodayLabel(mode) {
  document.getElementById("tab-today").textContent = mode === "today" ? "Today" : "Next Weekend";
}

/**
 * The Job | Student table for one session view.
 * `editable` (unlocked and not a past day) adds the per-row teacher actions.
 */
export function renderSessionTable(session, { editable = false } = {}) {
  return h(
    "table",
    { class: "roles" },
    h("caption", { class: "sr-only" }, `Jobs for ${longDate(session.date)}`),
    h("thead", {},
      h("tr", {},
        h("th", { scope: "col" }, "Job"),
        h("th", { scope: "col" }, "Student"))),
    h("tbody", {}, session.roles.map((role) => roleRow(session, role, editable))),
  );
}

/** One Job | Student row: icon + name (+ description), name large, swap/manual chips. */
function roleRow(session, role, editable) {
  const { job, student, source, note, projected } = role;
  const jobCell = h("td", { class: "job" },
    job.icon ? h("span", { class: "job-icon" }, job.icon) : null,
    h("span", { class: "job-name" }, job.name));
  if (job.description) jobCell.append(h("small", { class: "job-desc" }, job.description));
  const studentCell = h("td", { class: "student" });
  if (student === null) {
    studentCell.append(h("span", { class: "no-one" }, "No one available"));
  } else {
    studentCell.append(h("span", { class: "student-name" }, student.name));
    if (source === "swap" && note) {
      studentCell.append(h("span", { class: "chip chip-swap" }, `⇄ ${note}`));
    }
    if (source === "manual") {
      studentCell.append(h("span", { class: "chip chip-manual" }, "Set by teacher"));
    }
  }
  if (editable) {
    // Projected rows have no stored assignment, so "Leave empty" would 404;
    // the other two actions work on projected picks (they create stored rows).
    const buttons = [h("button", { type: "button", class: "act", onclick: () => openChangeDialog(session, role) }, "Change student")];
    if (student !== null) {
      buttons.unshift(h("button", { type: "button", class: "act", onclick: () => openAbsentDialog(session, role) }, "Absent"));
      if (!projected) buttons.push(h("button", { type: "button", class: "act", onclick: () => clearAssignment(session, role) }, "Leave empty"));
    }
    studentCell.append(h("div", { class: "row-actions" }, ...buttons));
  }
  return h("tr", {}, jobCell, studentCell);
}

/** Today / Upcoming / No class badge for the card header. */
function cardBadge(session) {
  if (session.status === "cancelled") {
    return h("span", { class: "badge badge-noclass" }, "No class");
  }
  return h("span", {
    class: session.is_today ? "badge badge-today" : "badge badge-upcoming",
  }, session.is_today ? "Today" : "Upcoming");
}

/** One day card: held (table), empty roster (hint), or cancelled (muted). */
function dayCard(session, data) {
  const head = h("div", { class: "card-header day-head" },
    h("div", { class: "day-title-row" },
      h("span", { class: "star", "aria-hidden": "true" }, "✶"),
      h("h2", { class: "day-title" }, longDate(session.date)),
      cardBadge(session)),
    h("p", { class: "hijri" }, hijriDate(session.date)));
  const body = h("div", { class: "card-body" });
  const card = h("div", {
    class: "card day-card" + (session.status === "cancelled" ? " cancelled" : ""),
  }, head, body);
  // Unlocked viewers get the teacher actions; past days are read-only.
  const editable = isUnlocked() && !session.is_past;
  if (session.status === "cancelled") {
    body.append(h("p", { class: "day-msg" }, "No class — the teacher is away."));
    if (session.note) body.append(h("p", { class: "day-msg" }, session.note));
    if (data.next_held) {
      body.append(h("p", { class: "day-msg day-msg-strong" },
        `Roles move to ${longDate(data.next_held.date)}`));
    }
    if (editable) {
      body.append(h("div", { class: "card-actions" },
        h("button", { type: "button", class: "act", onclick: () => openRestoreConfirm(session) }, "Bring back this day")));
    }
    return card;
  }
  if (session.roles.length === 0) {
    body.append(h("p", { class: "day-msg" }, "No jobs yet. Teacher tools → Jobs to add some."));
  } else {
    body.append(renderSessionTable(session, { editable }));
  }
  if (editable) {
    body.append(h("div", { class: "card-actions" },
      h("button", { type: "button", class: "act", onclick: () => openShiftDialog(session) }, "Teacher away — shift this day")));
  }
  return card;
}

/** Tomorrow's ISO date for an ISO date (pure formatting aid, not "today"). */
function addOneDay(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + 1));
  const pad = (n) => String(n).padStart(2, "0");
  return `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`;
}

/** On a real Saturday, the compact "Tomorrow: Sunday, November 8" line. */
function tomorrowLine(session, data) {
  if (data.mode !== "today" || session.weekday !== "Saturday") return null;
  const tomorrow = addOneDay(session.date);
  const day = Number(tomorrow.slice(8, 10));
  const label = `${weekdayName(tomorrow)}, ${monthName(tomorrow)} ${day}`;
  return h("p", { class: "tomorrow" }, "Tomorrow: ",
    h("a", { href: `#calendar/${tomorrow.slice(0, 7)}` }, label));
}

/** Skeleton card shown while /api/today is loading. */
function skeletonCard() {
  const rows = [];
  for (let i = 0; i < 4; i += 1) {
    rows.push(h("div", { class: "skel-row" },
      h("span", { class: "skeleton", style: "width: 45%" }),
      h("span", { class: "skeleton", style: "width: 65%" })));
  }
  return h("div", { class: "card day-card" },
    h("div", { class: "card-header day-head" },
      h("div", { class: "day-title-row" },
        h("span", { class: "skeleton", style: "width: 220px" }))),
    h("div", { class: "card-body" }, ...rows));
}

/** Friendly error card with a Retry button (never a blank page). */
function showError() {
  clear(panel);
  panel.append(h("div", { class: "card" },
    h("div", { class: "card-body error-box" },
      h("p", { class: "day-msg" }, "We could not load the roster just now."),
      h("button", { class: "btn btn-primary", type: "button", onclick: () => load() }, "Retry"))));
}

/** Fetch /api/today and render; reloads config when the server's day changed. */
async function load() {
  if (inflight || panel === null) return;
  inflight = true;
  clear(panel);
  panel.append(skeletonCard());
  try {
    const fresh = await api.get("/api/today");
    if (lastToday !== null && fresh.today !== lastToday) {
      state.config = await api.get("/api/config"); // midnight passed; refresh shared state
    }
    lastToday = fresh.today;
    lastData = fresh;
    render(fresh);
  } catch (err) {
    console.error(err);
    showError();
  } finally {
    inflight = false;
  }
}

/** Draw the whole tab from a /api/today response. */
function render(data) {
  if (panel === null) return;
  clear(panel);
  setTodayLabel(data.mode);
  for (const session of data.sessions) {
    panel.append(dayCard(session, data));
    const line = tomorrowLine(session, data);
    if (line) panel.append(line);
  }
}

/** Re-draw from the cached response: the button set depends on lock state. */
function onLockChange() {
  if (lastData !== null) render(lastData);
}

/**
 * Render Tab 1 into panelEl: fetch /api/today, then keep it fresh every 5
 * minutes and whenever the page becomes visible again.
 */
export function renderToday(panelEl) {
  panel = panelEl;
  if (timer === null) {
    timer = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, REFRESH_MS);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") load();
    });
  }
  if (!lockListenerOn) {
    lockListenerOn = true;
    window.addEventListener("kr:lockchange", onLockChange);
  }
  load();
}
