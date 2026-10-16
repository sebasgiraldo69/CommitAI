import { request } from "./api.js";

const $ = (id) => document.getElementById(id);

const labels = {
  pending: "Pendientes",
  incomplete: "Incompletos",
  overdue: "Vencidos",
  completed: "Completados",
  discarded: "Descartados",
};

const singularLabels = {
  pending: "Pendiente",
  incomplete: "Incompleto",
  overdue: "Vencido",
  completed: "Completado",
  discarded: "Descartado",
};

const fieldNames = {
  responsible: "responsable",
  due_date: "fecha límite",
  due_time: "hora límite",
};

const priorityLabels = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
};

const state = {
  status: "",
  responsible: "",
  sort: "due_asc",
  offset: 0,
  limit: 10,
  total: 0,
  busy: false,
  editing: null,
  saving: false,
  counts: {},
};

const fields = [
  ["title", "Título", "text", 200, true],
  ["responsible", "Responsable", "text", 200],
  ["counterparty", "Contraparte", "text", 200],
  ["due_date", "Fecha límite", "date"],
  ["due_time", "Hora límite", "time"],
  ["timezone", "Zona horaria", "text", null, true],
  ["description", "Descripción", "textarea", 2000],
  ["condition", "Condición", "textarea", 1000],
];

function notify(text, kind = "") {
  $("dashboard-message").textContent = text;
  $("dashboard-message").className = `message ${kind}`;
}

function editNotify(text, kind = "") {
  $("edit-message").textContent = text;
  $("edit-message").className = `message ${kind}`;
}

function node(tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  element.className = className;
  return element;
}

function controls() {
  const locked = state.busy || state.saving;

  $("filter-fields").disabled = locked;
  $("refresh").disabled = locked;
  $("previous").disabled = locked || state.offset === 0;
  $("next").disabled =
    locked || state.offset + state.limit >= state.total;

  document.querySelectorAll(
    "#status-tabs button, #commitment-list button",
  ).forEach((button) => {
    button.disabled = locked;
  });

  $("edit-fields").disabled = state.saving;
}

function renderTabs() {
  const container = $("status-tabs");
  container.replaceChildren();

  const total = Object.values(state.counts).reduce(
    (sum, value) => sum + value,
    0,
  );

  for (const [value, label] of [
    ["", "Todos"],
    ...Object.entries(labels),
  ]) {
    const button = node("button", label, "status-tab");
    button.type = "button";
    button.setAttribute(
      "aria-pressed",
      String(state.status === value),
    );

    const count = value ? state.counts[value] || 0 : total;
    button.append(node("strong", String(count)));

    button.addEventListener("click", () => {
      if (state.busy) return;
      state.status = value;
      state.offset = 0;
      loadList();
    });

    container.append(button);
  }
}

function renderList(items) {
  const container = $("commitment-list");
  container.replaceChildren();

  if (!items.length) {
    container.append(
      node(
        "p",
        "No hay compromisos que coincidan con estos filtros.",
        "empty-state",
      ),
    );
  }

  for (const item of items) {
    const article = document.createElement("article");
    article.className = "commitment-item";

    const heading = document.createElement("div");
    heading.className = "item-heading";

    heading.append(
      node("h3", item.title),
      node(
        "span",
        singularLabels[item.status],
        `status-pill status-${item.status}`,
      ),
    );

    const due = item.due_date
      ? `${item.due_date} · ${item.due_time || "Sin hora"}`
      : item.due_time
        ? `Sin fecha · ${item.due_time}`
        : "Sin fecha";

    article.append(
      heading,
      node(
        "p",
        `Responsable: ${item.responsible || "Por definir"} · ` +
        `Prioridad: ${priorityLabels[item.priority]}`,
        "hint",
      ),
      node(
        "p",
        `Vencimiento: ${due} · ${item.timezone}`,
        "hint",
      ),
    );

    if (item.description) {
      article.append(
        node("p", item.description, "item-description"),
      );
    }

    if (item.missing_information.length) {
      article.append(
        node(
          "p",
          "Por revisar: " + item.missing_information
            .map((field) => fieldNames[field] || field)
            .join(", "),
          "warning",
        ),
      );
    }

    if (item.is_past_due && item.status === "incomplete") {
      article.append(
        node(
          "p",
          "La fecha también está vencida.",
          "warning",
        ),
      );
    }

    const actions = document.createElement("div");
    actions.className = "item-actions";

    const edit = node("button", "Ver y editar", "secondary");
    edit.type = "button";
    edit.addEventListener("click", () => openEditor(item.id));
    actions.append(edit);

    article.append(actions);
    container.append(article);
  }

  $("page-info").textContent = state.total
    ? `${state.offset + 1}–${Math.min(
        state.offset + state.limit,
        state.total,
      )} de ${state.total}`
    : "0 compromisos";
}

async function loadList({ quiet = false } = {}) {
  if (state.busy || state.saving || $("editor").open) return false;

  state.busy = true;
  controls();

  if (!quiet) notify("Cargando compromisos…");

  try {
    const params = new URLSearchParams({
      limit: String(state.limit),
      offset: String(state.offset),
      sort: state.sort,
    });

    if (state.status) params.set("status", state.status);
    if (state.responsible) {
      params.set("responsible", state.responsible);
    }

    const result = await request(
      `/api/commitments?${params.toString()}`,
      { timeout: 15000 },
    );

    // Si una edición deja vacía la última página, vuelve a la primera.
    if (state.offset > 0 && result.items.length === 0) {
      state.offset = 0;
      state.busy = false;
      return await loadList({ quiet });
    }

    state.total = result.total;
    state.counts = result.counts;

    renderTabs();
    renderList(result.items);

    $("updated-at").textContent =
      "Última actualización: " + new Date().toLocaleTimeString("es-CO");

    notify("");
    return true;
  } catch (error) {
    notify(
      `${error.message} La lista no se ha actualizado.`,
      "error",
    );
    return false;
  } finally {
    state.busy = false;
    controls();
  }
}

function buildEditor(item) {
  const container = $("edit-inputs");
  container.replaceChildren();

  for (const [field, label, type, maxLength, required] of fields) {
    const wrapper = node("label", label);
    const input = document.createElement(
      type === "textarea" ? "textarea" : "input",
    );

    if (type === "textarea") {
      input.rows = 2;
    } else {
      input.type = type;
    }

    input.id = `edit-${field}`;
    input.value = item[field] ?? "";
    input.required = Boolean(required);

    if (maxLength) input.maxLength = maxLength;

    wrapper.append(input);
    container.append(wrapper);
  }

  const priorityLabel = node("label", "Prioridad");
  const priority = document.createElement("select");
  priority.id = "edit-priority";

  for (const [value, label] of Object.entries(priorityLabels)) {
    priority.add(new Option(label, value));
  }

  priority.value = item.priority;
  priorityLabel.append(priority);
  container.append(priorityLabel);

  const ambiguities = $("edit-ambiguities");
  ambiguities.replaceChildren();

  const rendered = new Set();

  for (const ambiguity of item.extraction.ambiguities) {
    ambiguities.append(
      node("p", ambiguity.reason, "warning"),
    );

    if (rendered.has(ambiguity.field)) continue;
    rendered.add(ambiguity.field);

    const label = document.createElement("label");
    label.className = "check-label";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = ambiguity.field;
    checkbox.checked = item.resolved_ambiguities.includes(
      ambiguity.field,
    );

    label.append(
      checkbox,
      node(
        "span",
        `He resuelto la ambigüedad de ${fieldNames[ambiguity.field]}.`,
      ),
    );

    ambiguities.append(label);
  }

  $("edit-status").textContent =
    `Estado actual: ${singularLabels[item.status]} · ID: ${item.id}`;

  $("edit-origin").textContent =
    `Origen: ${item.source.label || item.source.kind} · ` +
    `Fecha de conversación: ${item.reference_date}`;

  $("edit-quote").textContent = item.extraction.source_quote;
  $("edit-action").value = "";
  editNotify("");
}

async function openEditor(id) {
  if (state.busy || state.saving) return;

  state.busy = true;
  controls();
  notify("Cargando detalle…");

  try {
    const item = await request(`/api/commitments/${id}`, {
      timeout: 15000,
    });

    state.editing = item;
    buildEditor(item);
    $("editor").showModal();
    notify("");
  } catch (error) {
    notify(error.message, "error");
  } finally {
    state.busy = false;
    controls();
  }
}

$("edit-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  if (state.saving || !state.editing) return;

  const changes = {};

  for (const [field] of fields) {
    const value = $(`edit-${field}`).value.trim();
    changes[field] = value || null;
  }

  changes.priority = $("edit-priority").value;
  changes.resolved_ambiguities = [
    ...$("edit-ambiguities").querySelectorAll("input:checked"),
  ].map((checkbox) => checkbox.value);

  const payload = { changes };
  const action = $("edit-action").value;
  if (action) payload.action = action;

  state.saving = true;
  controls();
  editNotify("Guardando cambios…");

  try {
    const result = await request(
      `/api/commitments/${state.editing.id}`,
      {
        method: "PATCH",
        body: payload,
        timeout: 15000,
      },
    );

    $("editor").close();
    state.editing = null;
    state.saving = false;

    const refreshed = await loadList();

    if (refreshed) {
      notify(
        `Cambios guardados. Estado: ${singularLabels[result.status]}.`,
        "success",
      );
    }
  } catch (error) {
    const uncertain = error.status === 0 || error.status >= 500;

    editNotify(
      error.message + (
        uncertain
          ? " No se pudo confirmar el resultado. Puedes cerrar el detalle " +
            "y actualizar la lista para comprobar si se guardó."
          : " Corrige los datos o selecciona una acción compatible."
      ),
      "error",
    );
  } finally {
    state.saving = false;
    controls();
  }
});

$("cancel-edit").addEventListener("click", () => {
  if (state.saving) return;
  $("editor").close();
  state.editing = null;
});

$("editor").addEventListener("cancel", (event) => {
  if (state.saving) {
    event.preventDefault();
  } else {
    state.editing = null;
  }
});

$("filters").addEventListener("submit", (event) => {
  event.preventDefault();
  if (state.busy) return;

  state.responsible = $("responsible").value.trim();
  state.sort = $("sort").value;
  state.offset = 0;
  loadList();
});

$("clear-filters").addEventListener("click", () => {
  $("responsible").value = "";
  $("sort").value = "due_asc";

  state.responsible = "";
  state.sort = "due_asc";
  state.status = "";
  state.offset = 0;
  loadList();
});

$("refresh").addEventListener("click", () => loadList());

$("previous").addEventListener("click", () => {
  if (state.busy) return;
  state.offset = Math.max(0, state.offset - state.limit);
  loadList();
});

$("next").addEventListener("click", () => {
  if (state.busy) return;
  state.offset += state.limit;
  loadList();
});

// No interrumpir una edición ni actualizar una pestaña oculta.
setInterval(() => {
  if (!document.hidden) loadList({ quiet: true });
}, 30000);

loadList();