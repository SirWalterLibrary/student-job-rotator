// Tab 2: Monthly calendar (specs 06 + 07).
// "Today" always comes from the server (/api/config); the UI only formats it.

import { h, clear } from "./dom.js";
import { api } from "./api.js";
import { state } from "./app.js"; // referenced at call time only (circular import is safe)
import { renderSessionTable } from "./today.js";
import { hijriDate, longDate, shortDate } from "./dates.js";
const NARROW = window.matchMedia("(max-width: 700px)");
const WEEKDAY_HEADS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

let panel = null;       // #panel-calendar, set on the first renderCalendar()
let month = null;       // the "YYYY-MM" currently shown
let data = null;        // the last successful /api/calendar response
let inflight = false;   // guard against overlapping loads
let listenerOn = false; // the single matchMedia change listener

const utcNoon = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12)); // noon UTC avoids a Hijri off-by-one
};
const pad = (n) => String(n).padStart(2, "0");
const isoOf = (y, m, d) => `${y}-${pad(m)}-${pad(d)}`;

/** Approximate Hijri month range for the month's class days ("Rajab 1448 AH"). */
function hijriRange(sessions) {
  if (sessions.length === 0) return "";
  let fmt = null;
  try {
    fmt = new Intl.DateTimeFormat("en-u-ca-islamic-umalqura-nu-latn", {
      month: "long", year: "numeric", timeZone: "UTC",
    });
  } catch {
    return ""; // browser without the Umm al-Qura calendar
  }
  const first = fmt.format(utcNoon(sessions[0].date));
  const last = fmt.format(utcNoon(sessions[sessions.length - 1].date));
  return first === last ? first : `${first} – ${last}`;
}

/** The month's session views keyed by ISO date. */
function sessionByDate() {
  const map = {};
  for (const session of data.sessions) map[session.date] = session;
  return map;
}

/** ‹ Previous / month label + Hijri range / Next › / This month. */
function toolbar() {
  const current = state.config ? state.config.today.slice(0, 7) : null;
  return h("div", { class: "cal-toolbar" },
    h("button", { type: "button", class: "btn btn-secondary cal-nav", disabled: data.prev === null, onclick: () => goMonth(data.prev) }, "‹ Previous"),
    h("div", { class: "cal-month" },
      h("span", { class: "cal-month-name" }, data.label),
      h("span", { class: "cal-month-hijri" }, hijriRange(data.sessions))),
    h("button", { type: "button", class: "btn btn-secondary cal-nav", disabled: data.next === null, onclick: () => goMonth(data.next) }, "Next ›"),
    h("button", { type: "button", class: "btn btn-secondary cal-nav", disabled: current !== null && current === month, onclick: () => goMonth(current) }, "This month"));
}

/** Mon–Fri: the day number only, dimmed (today still keeps its ring). */
function weekdayCell(d, iso, todayIso) {
  return h("div", { class: "cal-cell weekday" + (iso === todayIso ? " today" : "") },
    h("span", { class: "cal-num" }, String(d)));
}

/** One compact "Job — Student" line; a swapped row carries ⇄ (note in its title). */
function roleLine(role) {
  const { job, student, source, note } = role;
  const line = h("span", { class: "cal-role-line" },
    h("span", { class: "cal-role" }, `${job.name} — ${student ? student.name : "No one"}`));
  if (source === "swap") {
    const mark = h("span", { class: "cal-swap", "aria-hidden": "true" }, "⇄");
    if (note) mark.title = note;
    line.append(mark);
  }
  return line;
}

/**
 * A Saturday/Sunday cell: day number, Hijri date, one line per role.
 * A real <button> (click or Enter opens the day dialog) when the month
 * includes a session for that date; a dimmed div otherwise.
 */
function weekendCell(d, iso, session, todayIso, stacked = false) {
  const classes = ["cal-cell", "weekend", iso === todayIso ? "today" : "",
    session && session.is_past ? "past" : "", session && session.status === "cancelled" ? "cancelled" : "",
    !session ? "empty" : "", stacked ? "stacked" : ""].filter(Boolean).join(" ");
  const top = h("span", { class: "cal-top" },
    h("span", { class: "cal-num" }, String(d)),
    h("span", { class: "cal-hijri" }, hijriDate(iso)));
  if (!session) return h("div", { class: classes }, top);
  const cell = h("button", {
    type: "button", class: classes,
    "aria-label": `${longDate(iso)}${session.status === "cancelled" ? ", no class" : ""}`,
    onclick: () => openDayDialog(session),
  }, top);
  if (session.status === "cancelled") cell.append(h("span", { class: "cal-noclass" }, "No class"));
  else for (const role of session.roles) cell.append(roleLine(role));
  return cell;
}

/** The full 7-column, Monday-first grid for the current month. */
function buildGrid() {
  const [y, m] = data.month.split("-").map(Number);
  const lead = (new Date(Date.UTC(y, m - 1, 1)).getUTCDay() + 6) % 7; // blanks before day 1
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const sessions = sessionByDate();
  const today = state.config ? state.config.today : null;
  const grid = h("div", { class: "cal-grid" });
  for (const name of WEEKDAY_HEADS) grid.append(h("div", { class: "cal-head" }, name));
  for (let i = 0; i < lead; i += 1) grid.append(h("div", { class: "cal-cell blank", "aria-hidden": "true" }));
  for (let d = 1; d <= days; d += 1) {
    const iso = isoOf(y, m, d);
    if ((lead + d - 1) % 7 < 5) grid.append(weekdayCell(d, iso, today));
    else grid.append(weekendCell(d, iso, sessions[iso] || null, today));
  }
  for (let i = 0; i < (7 - (lead + days) % 7) % 7; i += 1) grid.append(h("div", { class: "cal-cell blank", "aria-hidden": "true" }));
  return grid;
}

/** <700px: each weekend as a stacked block, Saturday and Sunday one under the other. */
function buildWeekends() {
  const groups = [];
  for (const session of data.sessions) {
    const last = groups[groups.length - 1];
    if (session.weekday === "Saturday") groups.push({ saturday: session, sunday: null });
    else if (last && last.sunday === null) last.sunday = session;
    else groups.push({ saturday: null, sunday: session });
  }
  const today = state.config ? state.config.today : null;
  const wrap = h("div", { class: "cal-weekends" });
  for (const group of groups) {
    const first = group.saturday || group.sunday;
    const block = h("div", { class: "cal-weekend" },
      h("h3", { class: "cal-weekend-title" }, `Weekend of ${shortDate(first.date)}`));
    for (const session of [group.saturday, group.sunday]) {
      if (session) block.append(weekendCell(Number(session.date.slice(8, 10)), session.date, session, today, true));
    }
    wrap.append(block);
  }
  return wrap;
}

/** The day dialog: the Tab 1 table, or the cancelled / empty-roster message. */
function openDayDialog(session) {
  const dialog = document.getElementById("dialog");
  const opener = document.activeElement;
  clear(dialog);
  const body = h("div", { class: "dialog-body" });
  if (session.status === "cancelled") {
    body.append(h("p", { class: "day-msg" }, "No class — the teacher is away."));
    if (session.note) body.append(h("p", { class: "day-msg" }, session.note));
  } else if (session.roles.length === 0) {
    body.append(h("p", { class: "day-msg" }, "No jobs yet. Teacher tools → Jobs to add some."));
  } else {
    body.append(renderSessionTable(session, { editable: false }));
  }
  const badge = session.status === "cancelled" ? h("span", { class: "badge badge-noclass" }, "No class")
    : h("span", { class: session.is_today ? "badge badge-today" : "badge badge-upcoming" }, session.is_today ? "Today" : "Upcoming");
  dialog.append(
    h("div", { class: "dialog-head" },
      h("div", { class: "day-title-row" },
        h("span", { class: "star", "aria-hidden": "true" }, "✶"), h("h2", { class: "day-title" }, longDate(session.date))),
      badge),
    body,
    h("div", { class: "dialog-actions" },
      h("button", { type: "button", class: "btn btn-secondary", onclick: () => dialog.close() }, "Close")));
  // Esc closes natively; make sure focus returns to the cell that opened it.
  dialog.onclose = () => {
    if (opener && opener.isConnected) opener.focus();
  };
  dialog.showModal();
}

/** Skeleton card shown while /api/calendar is loading. */
function skeleton() {
  const rows = [];
  for (let i = 0; i < 5; i += 1) {
    rows.push(h("div", { class: "skel-row" },
      h("span", { class: "skeleton", style: "width: 30%" }),
      h("span", { class: "skeleton", style: "width: 70%" })));
  }
  return h("div", { class: "card" }, h("div", { class: "card-body" }, ...rows));
}

/** Friendly error card with a Retry button (never a blank page). */
function showError() {
  clear(panel);
  panel.append(h("div", { class: "card" },
    h("div", { class: "card-body error-box" },
      h("p", { class: "day-msg" }, "We could not load the calendar just now."),
      h("button", { type: "button", class: "btn btn-primary", onclick: () => load() }, "Retry"))));
}

/** Fetch /api/calendar for the current month, then render. */
async function load() {
  if (inflight || panel === null || month === null) return;
  inflight = true;
  clear(panel);
  panel.append(skeleton());
  try {
    data = await api.get(`/api/calendar?month=${month}`);
    render();
  } catch (err) {
    console.error(err);
    showError();
  } finally {
    inflight = false;
  }
}

/** Draw toolbar + grid (wide) or stacked weekends (narrow) from the cached response. */
function render() {
  if (panel === null || data === null) return;
  clear(panel);
  panel.append(toolbar());
  panel.append(NARROW.matches ? buildWeekends() : buildGrid());
}

/** Switch months: record it in the hash (refresh/back), then load it. */
function goMonth(target) {
  if (target === null || target === month) return;
  month = target;
  state.month = target;
  history.pushState(null, "", `#calendar/${target}`);
  load();
}

/**
 * Render Tab 2 into panelEl. monthIso defaults to the current month
 * (from config.today); a repeat call for the cached month just re-renders.
 */
export function renderCalendar(panelEl, monthIso) {
  panel = panelEl;
  if (!listenerOn) {
    listenerOn = true;
    NARROW.addEventListener("change", () => {
      if (state.tab === "calendar" && data !== null) render();
    });
  }
  const target = monthIso || (state.config ? state.config.today.slice(0, 7) : null);
  if (target === null) return;
  if (target !== month || data === null) {
    month = target;
    load();
  } else {
    render();
  }
}
