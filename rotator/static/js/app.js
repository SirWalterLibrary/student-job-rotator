// Boot: load config, label Tab 1, and wire tab routing (hash + arrow keys).
// T10/T11 render into the panels; this module only keeps them in a
// "Loading…" placeholder state and tracks selection.

import { h, clear, toast } from "./dom.js";
import { api, storedPin } from "./api.js";

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

/** Select a tab: ARIA state, hidden panels, and location.hash. */
function selectTab(name, month) {
  if (name !== "today" && name !== "calendar") name = "today";
  state.tab = name;
  for (const tab of TABS) {
    const selected = tab.name === name;
    document.getElementById(tab.id).setAttribute("aria-selected", selected ? "true" : "false");
    document.getElementById(tab.panel).hidden = !selected;
  }
  if (name === "calendar") state.month = month || (state.config ? state.config.today.slice(0, 7) : null);
  const hash = name === "calendar" ? (state.month ? `#calendar/${state.month}` : "#calendar") : "#today";
  if (location.hash !== hash) history.pushState(null, "", hash);
}

/** Read the current hash and select the tab it names (also syncs the month). */
function applyHash() {
  const [name, month] = location.hash.slice(1).split("/");
  const tab = name === "calendar" ? "calendar" : "today";
  if (tab !== state.tab) selectTab(tab, month || null);
  else if (tab === "calendar" && month && month !== state.month) state.month = month;
}

/** Fetch /api/today once to choose the Tab 1 label ("Today" / "Next Weekend"). */
async function refreshTabLabel() {
  const button = document.getElementById("tab-today");
  const data = await api.get("/api/today");
  button.textContent = data.mode === "today" ? "Today" : "Next Weekend";
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

/** Wire the (still inert) Teacher tools button and lock events. */
function wireHeader() {
  document.getElementById("teacher-tools").addEventListener("click", () => {
    toast("Teacher tools are coming soon.");
  });
  window.addEventListener("kr:locked", () => {
    state.unlocked = false;
  });
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
  state.unlocked = !state.config.pin_required || Boolean(storedPin());
  wireTabs();
  wireHeader();
  try {
    await refreshTabLabel();
  } catch (err) {
    console.error(err); // keep the "Today" label; panels stay on their placeholder
  }
  applyHash(); // honors #calendar or #calendar/YYYY-MM on reload; no-op otherwise
  window.addEventListener("hashchange", applyHash);
  window.addEventListener("popstate", applyHash);
}

boot();
