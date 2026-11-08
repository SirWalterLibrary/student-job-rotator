// Teacher tools drawer: the Students and Jobs sections (spec 06).
// The shared drawer helpers come from manage.js; that import is circular
// (manage.js imports the loaders back) but safe: both sides are only
// referenced at call time, after both modules have finished loading.

import { h, clear, toast } from "./dom.js";
import { api } from "./api.js";
import { sectionBody, errorRow, afterChange } from "./manage.js";

/* ---------------- Students ---------------- */

/** One student row: name, Rename (inline edit), Remove (confirm). */
function studentRow(student) {
  const row = h("li", { class: "roster-row" });
  const fill = () => {
    clear(row);
    row.append(h("span", { class: "roster-name" }, student.name));
    row.append(h("span", { class: "roster-actions" },
      h("button", {
        type: "button", class: "btn btn-small",
        onclick: () => {
          clear(row);
          const input = h("input", { type: "text", value: student.name, maxlength: 40 });
          const error = h("p", { class: "form-error", hidden: true });
          row.append(input, error,
            h("button", {
              type: "button", class: "btn btn-small btn-primary",
              onclick: async () => {
                const name = input.value.trim();
                if (name === "") {
                  error.hidden = false;
                  error.textContent = "Name is required";
                  return;
                }
                try {
                  student.name = (await api.send("PATCH", `/api/students/${student.id}`, { name })).name;
                  await afterChange();
                  fill();
                } catch (err) {
                  error.hidden = false;
                  error.textContent = err.message;
                }
              },
            }, "Save"),
            h("button", { type: "button", class: "btn btn-small", onclick: fill }, "Cancel"));
          input.focus();
          input.select();
        },
      }, "Rename"),
      h("button", {
        type: "button", class: "btn btn-small btn-danger",
        onclick: async () => {
          if (!window.confirm(`Remove ${student.name}? They lose this job and any future turns.`)) return;
          try {
            await api.send("DELETE", `/api/students/${student.id}`);
            await afterChange();
          } catch (err) {
            toast(err.message);
          }
        },
      }, "Remove")));
  };
  fill();
  return row;
}

/** Refresh the Students section: alphabetical list + add form (Enter submits). */
export async function loadStudents() {
  const body = sectionBody("students");
  let students;
  try {
    ({ students } = await api.get("/api/students"));
  } catch (err) {
    return errorRow(body, err, loadStudents);
  }
  clear(body);
  const input = h("input", { type: "text", placeholder: "New student name", maxlength: 40 });
  const error = h("p", { class: "form-error", hidden: true });
  const form = h("form", { class: "add-form" },
    input, error,
    h("button", { type: "submit", class: "btn btn-small btn-primary" }, "Add student"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (name === "") {
      error.hidden = false;
      error.textContent = "Name is required";
      return;
    }
    try {
      await api.send("POST", "/api/students", { name });
      input.value = "";
      error.hidden = true;
      await afterChange();
    } catch (err) {
      error.hidden = false;
      error.textContent = err.message;
    }
  });
  // The add form goes ABOVE the list so it is never scrolled out of view (T18);
  // a long list scrolls inside its own box (.student-list in manage.css).
  body.append(
    form,
    h("ul", { class: "roster-list student-list" }, ...students.map((s) => studentRow(s))));
}

/* ---------------- Jobs ---------------- */

/** Save the checked volunteer set (called on every checkbox change). */
function saveVolunteers(job, box) {
  const ids = [...box.querySelectorAll("input")].filter((c) => c.checked).map((c) => Number(c.value));
  api.send("PUT", `/api/jobs/${job.id}/volunteers`, { student_ids: ids })
    .then(() => afterChange())
    .catch((err) => {
      toast(err.message);
      loadJobs(); // revert the checkboxes to the server's set
    });
}

/** The expandable edit area: name/description/icon + volunteer checkboxes. */
function jobEditPanel(job, students) {
  const inputs = {
    name: h("input", { type: "text", value: job.name, maxlength: 60 }),
    description: h("input", { type: "text", value: job.description || "", maxlength: 200, placeholder: "Short description (optional)" }),
    icon: h("input", { type: "text", value: job.icon || "", maxlength: 8, placeholder: "Icon (optional emoji)" }),
  };
  const error = h("p", { class: "form-error", hidden: true });
  const volunteers = h("fieldset", { class: "volunteers" }, h("legend", {}, "Volunteers"),
    ...students.map((s) => h("label", { class: "check" },
      h("input", { type: "checkbox", value: String(s.id),
        checked: job.volunteer_ids.includes(s.id),
        onchange: () => saveVolunteers(job, volunteers) }),
      s.name)));
  return h("div", { class: "job-edit-panel" },
    h("label", { for: "job-name" }, "Name"), inputs.name,
    h("label", { for: "job-desc" }, "Description"), inputs.description,
    h("label", { for: "job-icon" }, "Icon"), inputs.icon,
    error,
    h("button", {
      type: "button", class: "btn btn-small btn-primary",
      onclick: async () => {
        try {
          await api.send("PATCH", `/api/jobs/${job.id}`, {
            name: inputs.name.value.trim(),
            description: inputs.description.value,
            icon: inputs.icon.value.trim(),
          });
          await afterChange();
        } catch (err) {
          error.hidden = false;
          error.textContent = err.message;
        }
      },
    }, "Save"),
    volunteers);
}

/** One job row: ▲/▼ reorder, Expand (edit + volunteers), Remove (confirm). */
function jobRow(job, index, jobs, students) {
  const row = h("li", { class: "roster-row job-row" });
  clear(row);
  row.append(h("span", { class: "roster-name" }, job.icon ? `${job.icon} ${job.name}` : job.name));
  const move = (delta) => {
    const target = index + delta;
    if (target < 0 || target >= jobs.length) return;
    const ids = jobs.map((j) => j.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    api.send("POST", "/api/jobs/reorder", { ids }).then(() => afterChange())
      .catch((err) => toast(err.message));
  };
  row.append(h("span", { class: "roster-actions" },
    h("button", { type: "button", class: "btn btn-small", "aria-label": `Move ${job.name} up`, onclick: () => move(-1) }, "▲"),
    h("button", { type: "button", class: "btn btn-small", "aria-label": `Move ${job.name} down`, onclick: () => move(1) }, "▼"),
    h("button", {
      type: "button", class: "btn btn-small",
      onclick: (event) => {
        const edit = row.querySelector(".job-edit");
        edit.hidden = !edit.hidden;
        event.currentTarget.textContent = edit.hidden ? "Expand" : "Collapse";
      },
    }, "Expand"),
    h("button", {
      type: "button", class: "btn btn-small btn-danger",
      onclick: async () => {
        if (!window.confirm(`Remove ${job.name}? Past history is kept.`)) return;
        try {
          await api.send("DELETE", `/api/jobs/${job.id}`);
          await afterChange();
        } catch (err) {
          toast(err.message);
        }
      },
    }, "Remove")));
  row.append(h("div", { class: "job-edit", hidden: true }, jobEditPanel(job, students)));
  return row;
}

/** Refresh the Jobs section: list in sort_order + add-job form. */
export async function loadJobs() {
  const body = sectionBody("jobs");
  let jobs;
  let students;
  try {
    [{ jobs }, { students }] = await Promise.all([api.get("/api/jobs"), api.get("/api/students")]);
  } catch (err) {
    return errorRow(body, err, loadJobs);
  }
  clear(body);
  body.append(h("ol", { class: "roster-list" }, ...jobs.map((job, i) => jobRow(job, i, jobs, students))));
  const name = h("input", { id: "new-job-name", type: "text", placeholder: "Job name", maxlength: 60 });
  const description = h("input", { id: "new-job-desc", type: "text", placeholder: "Short description (optional)", maxlength: 200 });
  const icon = h("input", { id: "new-job-icon", type: "text", placeholder: "Icon (optional emoji)", maxlength: 8 });
  const error = h("p", { class: "form-error", hidden: true });
  // Labels sit above their fields; each field is a single-line input (T18).
  const form = h("form", { class: "add-form add-job" },
    h("label", { for: "new-job-name" }, "Job name"), name,
    h("label", { for: "new-job-desc" }, "Short description"), description,
    h("label", { for: "new-job-icon" }, "Icon"), icon,
    error,
    h("button", { type: "submit", class: "btn btn-small btn-primary" }, "Add job"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api.send("POST", "/api/jobs", {
        name: name.value.trim(),
        description: description.value,
        icon: icon.value.trim(),
      });
      name.value = "";
      description.value = "";
      icon.value = "";
      error.hidden = true;
      await afterChange();
    } catch (err) {
      error.hidden = false;
      error.textContent = err.message;
    }
  });
  body.append(form);
}
