// Tab 1: Today / Next Weekend (specs 06 + 07).
// "Today" always comes from the server (/api/today); the UI only formats it.

import { h, clear } from "./dom.js";
import { api } from "./api.js";
import { state } from "./app.js"; // referenced at call time only (circular import is safe)
import { hijriDate, longDate, monthName, weekdayName } from "./dates.js";

const REFRESH_MS = 5 * 60 * 1000;

let panel = null;      // #panel-today, set on the first renderToday()
let timer = null;      // the one shared 5-minute interval
let lastToday = null;  // today from the last successful /api/today response
let inflight = false;  // guard against overlapping loads

/** Label the Tab 1 button from the /api/today mode ("today" | "upcoming"). */
export function setTodayLabel(mode) {
  document.getElementById("tab-today").textContent = mode === "today" ? "Today" : "Next Weekend";
}

/**
 * The Job | Student table for one session view.
 * `editable` is a placeholder for T13 (per-row teacher actions); false for now.
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
    h("tbody", {}, session.roles.map((role) => roleRow(role, editable))),
  );
}

/** One Job | Student row: icon + name (+ description), name large, swap/manual chips. */
function roleRow(role, editable) {
  const { job, student, source, note } = role;
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
    // editable (T13): per-row teacher actions go here.
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
  if (session.status === "cancelled") {
    body.append(h("p", { class: "day-msg" }, "No class — the teacher is away."));
    if (session.note) body.append(h("p", { class: "day-msg" }, session.note));
    if (data.next_held) {
      body.append(h("p", { class: "day-msg day-msg-strong" },
        `Roles move to ${longDate(data.next_held.date)}`));
    }
    return card;
  }
  if (session.roles.length === 0) {
    body.append(h("p", { class: "day-msg" }, "No jobs yet. Teacher tools → Jobs to add some."));
    return card;
  }
  body.append(renderSessionTable(session, { editable: false }));
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
    const data = await api.get("/api/today");
    if (lastToday !== null && data.today !== lastToday) {
      state.config = await api.get("/api/config"); // midnight passed; refresh shared state
    }
    lastToday = data.today;
    render(data);
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
  load();
}
