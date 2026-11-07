// Boot: load config, render the selected tab, and wire tab routing (hash + arrow keys).
// T10 renders Tab 1 (today.js); T11 renders Tab 2 (calendar.js).

import { h, clear } from "./dom.js";
import { api } from "./api.js";
import { renderToday, setTodayLabel } from "./today.js";
import { renderCalendar } from "./calendar.js";
import { initAuth } from "./auth.js";

/** Shared app state, imported by the other modules. */
export const state = {
  config: null,   // /api/config (today, weekday, timezone, pin_required, start_date)
  unlocked: false,
  tab: "today",   // "today" | "calendar"
  month: null,    // "YYYY-MM" while the calendar tab is showing
};

const TABS = [
  { id: "tab-today", name: "today", panel: "panel-today" },
  { id: "tab-calendar", name: "calendar", panel: "panel-calendar" },
];

/** Show the temporary "Loading…" placeholder in a panel. */
function placeholder(panelId) {
  const panel = document.getElementById(panelId);
  clear(panel);
  panel.append(h("p", { class: "placeholder" }, "Loading…"));
}

/** Select a tab: ARIA state, hidden panels, location.hash, and render. */
function selectTab(name, month) {
  if (name !== "today" && name !== "calendar") name = "today";
  state.tab = name;
  for (const tab of TABS) {
    const selected = tab.name === name;
    document.getElementById(tab.id).setAttribute("aria-selected", selected ? "true" : "false");
    document.getElementById(tab.panel).hidden = !selected;
  }
  if (name === "today") renderToday(document.getElementById("panel-today"));
  if (name === "calendar") {
    state.month = month || state.month || (state.config ? state.config.today.slice(0, 7) : null);
    renderCalendar(document.getElementById("panel-calendar"), state.month);
  }
  const hash = name === "calendar" ? (state.month ? `#calendar/${state.month}` : "#calendar") : "#today";
  if (location.hash !== hash) history.pushState(null, "", hash);
}

/** Read the current hash and select the tab it names (also syncs the month). */
function applyHash() {
  const [name, month] = location.hash.slice(1).split("/");
  const tab = name === "calendar" ? "calendar" : "today";
  if (tab !== state.tab) selectTab(tab, month || null);
  else if (tab === "calendar" && month && month !== state.month) {
    state.month = month;
    renderCalendar(document.getElementById("panel-calendar"), month);
  }
}

/** Fetch /api/today once to choose the Tab 1 label ("Today" / "Next Weekend"). */
async function refreshTabLabel() {
  setTodayLabel((await api.get("/api/today")).mode);
}

/** Wire up keyboard tab switching (left/right move, Enter/Space activate). */
function wireTabs() {
  const tablist = document.querySelector(".tabs");
  tablist.addEventListener("click", (event) => {
    const button = event.target.closest('[role="tab"]');
    if (button) selectTab(button.dataset.tab);
  });
  tablist.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const ids = TABS.map((tab) => tab.id);
    const current = ids.indexOf(document.activeElement && document.activeElement.id);
    if (current === -1) return;
    const next = (current + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    document.getElementById(ids[next]).focus();
  });
}

/** Wire the Teacher tools button and PIN lock/unlock (auth.js + manage.js). */
function wireHeader() {
  initAuth();
}

async function boot() {
  for (const tab of TABS) placeholder(tab.panel);
  try {
    state.config = await api.get("/api/config");
  } catch (err) {
    console.error(err);
    const panel = document.getElementById("panel-today");
    clear(panel);
    panel.append(h("p", { class: "placeholder" }, "Could not reach the Khidmah Roster. Is the server running?"));
    return;
  }
  wireTabs();
  wireHeader();
  applyHash(); // honors #calendar or #calendar/YYYY-MM on reload; no-op otherwise
  if (state.tab === "today") {
    renderToday(document.getElementById("panel-today")); // also sets the Tab 1 label
  } else {
    refreshTabLabel().catch((err) => console.error(err)); // keep the label right on other tabs
  }
  window.addEventListener("hashchange", applyHash);
  window.addEventListener("popstate", applyHash);
}

boot();
