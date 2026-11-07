// Teacher action dialogs (spec 06 "Dialogs"): absent/swap, shift day, bring
// back, change student, leave empty. Each opens its own <dialog>, shows the
// server error inline on failure, and on success closes, toasts, and calls
// the shared refreshAll(). A 401 re-locks via kr:locked; the dialog closes.

import { h, toast } from "./dom.js";
import { api } from "./api.js";
import { state } from "./app.js"; // referenced at call time only (circular import is safe)
import { isUnlocked } from "./auth.js";
import { longDate, shortDate } from "./dates.js";
import { renderToday } from "./today.js";
import { renderCalendar, refreshCalendar } from "./calendar.js";

/** The one action dialog currently open (or null). */
let active = null;
let nameById = {}; // student id → name, from the latest /api/students fetch

/** One <dialog>: midnight header, a form body slot, and an inline error slot. */
function dialogFrame(title) {
  const dialog = h("dialog", { class: "act-dialog" });
  const body = h("div", { class: "dialog-body act-form" });
  const error = h("p", { class: "form-error", role: "alert", hidden: true }); body.append(error);
  dialog.append(h("div", { class: "dialog-head" }, h("h2", { class: "day-title" }, title)), body);
  document.body.append(dialog);
  dialog.addEventListener("close", () => { if (active === dialog) active = null; });
  dialog.showModal(); active = dialog;
  return { dialog, body, error };
}

/** A 401 re-locks the UI (auth.js); close the action dialog so it cannot act. */
window.addEventListener("kr:locked", () => { if (active && active.open) active.close(); });

/** Show the server error text in the dialog (it stays open). */
function showFrameError(frame, err) {
  frame.error.hidden = false;
  frame.error.textContent = err.message;
}

/** Shared post-action refresh: close the day dialog, re-render the visible tab, and refresh the calendar cache. */
export async function refreshAll() {
  const day = document.getElementById("dialog");
  if (day && day.open) day.close();
  const jobs = [refreshCalendar()];
  if (state.tab === "today") jobs.push(renderToday(document.getElementById("panel-today")));
  else if (state.tab === "calendar") jobs.push(renderCalendar(document.getElementById("panel-calendar"), state.month));
  await Promise.all(jobs);
}

/** The ids of every student holding a role in this session. */
function busyIds(session) {
  const ids = new Set();
  for (const role of session.roles) if (role.student) ids.add(role.student.id);
  return ids;
}

/** Fetch the jobs + student names used to build the volunteer dropdowns. */
async function loadRoster() {
  const [jobsRes, studentsRes] = await Promise.all([api.get("/api/jobs"), api.get("/api/students")]);
  nameById = Object.fromEntries(studentsRes.students.map((s) => [s.id, s.name]));
  return jobsRes.jobs;
}

/** Find a job in a fetched list, or a friendly Error (shown inline). */
function findJob(jobs, id) {
  const job = jobs.find((j) => j.id === id);
  if (!job) throw new Error("That job is no longer active.");
  return job;
}

/** The "Who covers today?" select: recommended pick, then free volunteers. */
function partnerSelect(session, job, absentId) {
  const select = h("select", { id: "absent-partner" });
  select.append(h("option", { value: "" }, "Let the system choose (recommended)"));
  const busy = busyIds(session);
  for (const id of job.volunteer_ids) {
    if (id === absentId || busy.has(id)) continue; // absent student; anyone busy that day
    select.append(h("option", { value: String(id) }, nameById[id] || `Student ${id}`));
  }
  return select;
}

/** Absent / swap dialog for one role row (spec 06 "Dialogs"): POST /api/sessions/<date>/absent. */
export async function openAbsentDialog(session, role) {
  if (!isUnlocked() || !role.student || !role.job) return;
  const a = role.student;
  const frame = dialogFrame(`${a.name} is absent`);
  frame.body.append(h("p", { class: "day-msg" },
    `${a.name} will take ${role.job.name} on the next class day; someone else covers today.`));
  let select;
  try {
    const jobs = await loadRoster();
    select = partnerSelect(session, findJob(jobs, role.job.id), a.id);
  } catch (err) {
    showFrameError(frame, new Error(err.message || "Could not load the volunteer list."));
    return;
  }
  const form = h("form");
  form.append(h("label", { for: "absent-partner" }, "Who covers today?"), select,
    h("div", { class: "dialog-actions" },
      h("button", { type: "submit", class: "btn btn-primary" }, "Swap"),
      h("button", { type: "button", class: "btn btn-secondary", onclick: () => send(true) }, "Leave job empty today"),
      h("button", { type: "button", class: "btn btn-secondary", onclick: () => frame.dialog.close() }, "Cancel")));
  frame.body.append(form);
  select.focus();
  async function send(vacant) {
    frame.error.hidden = true;
    const body = { job_id: role.job.id };
    if (vacant) body.vacant = true;
    else if (select.value !== "") body.partner_id = Number(select.value);
    try {
      const res = await api.send("POST", `/api/sessions/${session.date}/absent`, body);
      frame.dialog.close();
      // vacant returns the session view; a swap returns { covering, absent, next_date }
      if (res.covering) toast(`${res.covering.name} covers today. ${res.absent.name} takes it on ${longDate(res.next_date)}.`);
      else toast(`${role.job.name} left empty. ${a.name} is first in line.`);
      await refreshAll();
    } catch (err) {
      showFrameError(frame, err);
      select.focus();
    }
  }
  form.addEventListener("submit", (event) => { event.preventDefault(); send(false); });
}

/** "Teacher away — shift this day": confirm, optional note, POST cancel. */
export function openShiftDialog(session) {
  if (!isUnlocked() || session.status !== "held") return;
  const frame = dialogFrame("Teacher away?");
  frame.body.append(h("p", { class: "day-msg" },
    `Teacher away on ${longDate(session.date)}? No jobs will be assigned that day, and everyone's turn moves to the next class day.`));
  const note = h("input", { id: "shift-note", type: "text", placeholder: "Note (optional)" });
  const form = h("form");
  form.append(h("label", { for: "shift-note" }, "Note (optional)"), note,
    h("div", { class: "dialog-actions" },
      h("button", { type: "submit", class: "btn btn-primary" }, "Shift day"),
      h("button", { type: "button", class: "btn btn-secondary", onclick: () => frame.dialog.close() }, "Cancel")));
  frame.body.append(form);
  note.focus();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    frame.error.hidden = true;
    try {
      await api.send("POST", `/api/sessions/${session.date}/cancel`, { note: note.value.trim() });
      frame.dialog.close();
      toast(`No class on ${shortDate(session.date)} — turns move to the next class day.`);
      await refreshAll();
    } catch (err) {
      showFrameError(frame, err);
      note.focus();
    }
  });
}

/** "Bring back this day": confirm, then POST /api/sessions/<date>/restore. */
export function openRestoreConfirm(session) {
  if (!isUnlocked() || session.status !== "cancelled") return;
  const frame = dialogFrame("Bring back this day?");
  const actions = h("div", { class: "dialog-actions" },
    h("button", { type: "button", class: "btn btn-primary", onclick: () => send() }, "Bring back this day"),
    h("button", { type: "button", class: "btn btn-secondary", onclick: () => frame.dialog.close() }, "Cancel"));
  frame.body.append(h("p", { class: "day-msg" },
    `Class on ${longDate(session.date)} is restored and its jobs are staffed again.`), actions);
  actions.querySelector(".btn-primary").focus();
  async function send() {
    frame.error.hidden = true;
    try {
      await api.send("POST", `/api/sessions/${session.date}/restore`);
      frame.dialog.close();
      toast(`Class restored on ${shortDate(session.date)}.`);
      await refreshAll();
    } catch (err) {
      showFrameError(frame, err);
    }
  }
}

/** "Change student" manual override: PUT /api/sessions/<date>/assignments/<job_id>. */
export async function openChangeDialog(session, role) {
  if (!isUnlocked() || !role.job) return;
  const frame = dialogFrame(`Change student — ${role.job.name}`);
  frame.body.append(h("p", { class: "day-msg" },
    `Choose who does ${role.job.name} on ${longDate(session.date)}.`));
  let select;
  try {
    const jobs = await loadRoster();
    const job = findJob(jobs, role.job.id);
    const busy = busyIds(session);
    const current = role.student ? role.student.id : null;
    select = h("select", { id: "change-student" });
    if (current === null) select.append(h("option", { value: "", disabled: true }, "Choose a student…"));
    for (const id of job.volunteer_ids) {
      // Busy = holds another role that day; the current holder stays selectable.
      if (busy.has(id) && id !== current) continue;
      select.append(h("option", { value: String(id) }, nameById[id] || `Student ${id}`));
    }
    if (current !== null && job.volunteer_ids.includes(current)) select.value = String(current);
  } catch (err) {
    showFrameError(frame, new Error(err.message || "Could not load the volunteer list."));
    return;
  }
  const form = h("form");
  form.append(h("label", { for: "change-student" }, "Student"), select,
    h("div", { class: "dialog-actions" },
      h("button", { type: "submit", class: "btn btn-primary" }, "Save"),
      h("button", { type: "button", class: "btn btn-secondary", onclick: () => frame.dialog.close() }, "Cancel")));
  frame.body.append(form);
  select.focus();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    frame.error.hidden = true;
    if (select.value === "") { frame.error.hidden = false; frame.error.textContent = "Choose a student first."; return; }
    try {
      await api.send("PUT", `/api/sessions/${session.date}/assignments/${role.job.id}`,
        { student_id: Number(select.value) });
      frame.dialog.close();
      toast(`${nameById[Number(select.value)] || "Student"} set for ${role.job.name}.`);
      await refreshAll();
    } catch (err) {
      showFrameError(frame, err);
      select.focus();
    }
  });
}

/** "Leave empty": confirm, then DELETE the stored assignment (hidden for projected rows). */
export function clearAssignment(session, role) {
  if (!isUnlocked() || !role.student || !role.job || role.projected) return;
  const frame = dialogFrame(`Leave ${role.job.name} empty?`);
  const actions = h("div", { class: "dialog-actions" },
    h("button", { type: "button", class: "btn btn-danger", onclick: () => send() }, "Leave empty"),
    h("button", { type: "button", class: "btn btn-secondary", onclick: () => frame.dialog.close() }, "Cancel"));
  frame.body.append(h("p", { class: "day-msg" },
    `${role.student.name} will not do ${role.job.name} on ${longDate(session.date)}. They stay first in line for the next turn.`), actions);
  actions.querySelector(".btn-danger").focus();
  async function send() {
    frame.error.hidden = true;
    try {
      await api.send("DELETE", `/api/sessions/${session.date}/assignments/${role.job.id}`);
      frame.dialog.close();
      toast(`${role.job.name} left empty. ${role.student.name} stays first in line.`);
      await refreshAll();
    } catch (err) {
      showFrameError(frame, err);
    }
  }
}
