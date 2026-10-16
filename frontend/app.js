import { request } from "./api.js";

const $ = (id) => document.getElementById(id);

const STORAGE_KEY = "commitai.pending-save.v1";

const state = {
  analysis: null,
  candidates: [],
  busy: false,
  pendingSave: null,
  generation: 0,
};

const statusLabels = {
  pending: "Pendiente",
  incomplete: "Incompleto",
  overdue: "Vencido",
  completed: "Completado",
  discarded: "Descartado",
};

const fieldLabels = {
  responsible: "responsable",
  due_date: "fecha límite",
  due_time: "hora límite",
};

function message(text, kind = "") {
  $("message").textContent = text;
  $("message").className = `message ${kind}`;
}

function nullable(value) {
  return value.trim() || null;
}

function localDate(timezone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const values = Object.fromEntries(
    parts.map((part) => [part.type, part.value]),
  );

  return `${values.year}-${values.month}-${values.day}`;
}

$("reference-date").value = localDate("America/Bogota");

function acceptedCandidates() {
  return state.candidates.filter(
    (candidate) => candidate.decision === "accepted",
  );
}

function updateControls() {
  const locked = state.busy || Boolean(state.pendingSave);
  const accepted = acceptedCandidates().length;

  $("input-fields").disabled = locked;
  $("review-fields").disabled = locked;

  $("analyze-button").textContent = state.busy
    ? "Procesando…"
    : "Analizar conversación";

  $("review-section").hidden = state.candidates.length === 0;

  $("save-section").hidden =
    state.candidates.length === 0 && !state.pendingSave;

  $("selection-summary").textContent = state.pendingSave
    ? "Hay un guardado pendiente de confirmar. Reintenta para verificarlo."
    : `${accepted} de ${state.candidates.length} candidatos seleccionados`;

  $("save-button").disabled =
    state.busy || (!state.pendingSave && accepted === 0);

  $("save-button").textContent = state.pendingSave
    ? "Reintentar guardado"
    : "Guardar seleccionados";
}

function updateMissing(candidate, element) {
  const missing = [];

  if (!candidate.values.responsible) missing.push("responsible");
  if (!candidate.values.due_date) missing.push("due_date");

  const unresolvedTime = candidate.ambiguities.some(
    (ambiguity) =>
      ambiguity.field === "due_time" &&
      !candidate.resolved.has("due_time"),
  );

  if (unresolvedTime) missing.push("due_time");

  element.textContent = missing.length
    ? `Por revisar: ${missing.map((field) => fieldLabels[field]).join(", ")}.`
    : "Responsable y fecha completos.";

  if (
    missing.length === 1 &&
    missing[0] === "due_time"
  ) {
    element.textContent += " La hora es opcional.";
  }
}

function addField(grid, candidate, field, label, options = {}) {
  const wrapper = document.createElement("label");
  wrapper.textContent = label;

  const input = document.createElement(
    options.multiline ? "textarea" : "input",
  );

  if (options.multiline) {
    input.rows = 2;
  } else {
    input.type = options.type || "text";
  }

  input.value = candidate.values[field] ?? "";
  input.dataset.field = field;
  input.required = Boolean(options.required);

  if (options.maxLength) input.maxLength = options.maxLength;

  input.addEventListener("input", () => {
    input.setCustomValidity("");
    candidate.values[field] = nullable(input.value);
    updateMissing(candidate, candidate.missingElement);
  });

  wrapper.append(input);
  grid.append(wrapper);
}

function renderCandidates() {
  const container = $("candidate-list");
  container.replaceChildren();

  state.candidates.forEach((candidate, index) => {
    const card = document.createElement("article");
    card.className = "candidate";
    candidate.element = card;

    const heading = document.createElement("h3");
    heading.textContent = `Compromiso ${index + 1}`;

    const meta = document.createElement("p");
    meta.className = "hint";
    meta.textContent =
      `Estado detectado: ${statusLabels[candidate.status]}. ` +
      `Confianza estimada: ${Math.round(candidate.confidence * 100)} %. ` +
      "El estado se recalculará al guardar.";

    const quote = document.createElement("blockquote");
    quote.textContent = candidate.source_quote;

    const missing = document.createElement("p");
    missing.className = "warning";
    candidate.missingElement = missing;

    const grid = document.createElement("div");
    grid.className = "grid";

    addField(grid, candidate, "title", "Título", {
      required: true,
      maxLength: 200,
    });
    addField(grid, candidate, "responsible", "Responsable", {
      maxLength: 200,
    });
    addField(grid, candidate, "counterparty", "Contraparte", {
      maxLength: 200,
    });
    addField(grid, candidate, "due_date", "Fecha límite", {
      type: "date",
    });
    addField(grid, candidate, "due_time", "Hora límite", {
      type: "time",
    });
    addField(grid, candidate, "timezone", "Zona horaria", {
      required: true,
    });
    addField(grid, candidate, "description", "Descripción", {
      multiline: true,
      maxLength: 2000,
    });
    addField(grid, candidate, "condition", "Condición", {
      multiline: true,
      maxLength: 1000,
    });

    const priorityLabel = document.createElement("label");
    priorityLabel.textContent = "Prioridad";

    const priority = document.createElement("select");
    priority.dataset.field = "priority";

    for (const [value, label] of [
      ["low", "Baja"],
      ["medium", "Media"],
      ["high", "Alta"],
    ]) {
      priority.add(new Option(label, value));
    }

    priority.value = candidate.values.priority;
    priority.addEventListener("change", () => {
      candidate.values.priority = priority.value;
    });

    priorityLabel.append(priority);
    grid.append(priorityLabel);

    const decisionLabel = document.createElement("label");
    decisionLabel.className = "check-label";

    const decision = document.createElement("input");
    decision.type = "checkbox";
    decision.checked = candidate.decision === "accepted";

    decision.addEventListener("change", () => {
    candidate.decision = decision.checked ? "accepted" : "review";
    updateControls();
    });

    const decisionText = document.createElement("span");
    decisionText.textContent = "Guardar este compromiso";

    decisionLabel.append(decision, decisionText);
    grid.append(decisionLabel);

    card.append(heading, meta, quote, missing, grid);

    const ambiguityFields = new Set();

    for (const ambiguity of candidate.ambiguities) {
      const explanation = document.createElement("p");
      explanation.className = "warning";
      explanation.textContent =
        `${fieldLabels[ambiguity.field]}: ${ambiguity.reason}`;

      card.append(explanation);

      if (ambiguityFields.has(ambiguity.field)) continue;
      ambiguityFields.add(ambiguity.field);

      const label = document.createElement("label");
      label.className = "check-label";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = candidate.resolved.has(ambiguity.field);

      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          candidate.resolved.add(ambiguity.field);
        } else {
          candidate.resolved.delete(ambiguity.field);
        }
        updateMissing(candidate, missing);
      });

      const text = document.createElement("span");
      text.textContent =
        `Ya revisé y resolví la ambigüedad de ` +
        `${fieldLabels[ambiguity.field]}.`;

      label.append(checkbox, text);
      card.append(label);
    }

    updateMissing(candidate, missing);
    container.append(card);
  });

  updateControls();
}

$("analysis-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  if (state.busy || state.pendingSave) return;

  const text = $("text").value.trim();

  if (!text) {
    message("Escribe una conversación para analizar.", "error");
    return;
  }

  if (
    state.candidates.length &&
    !window.confirm(
      "El nuevo análisis reemplazará los candidatos que aún no guardaste. " +
      "¿Quieres continuar?",
    )
  ) {
    return;
  }

  const payload = {
    text,
    reference_date: $("reference-date").value,
    timezone: $("timezone").value.trim(),
    participants: [
      ...new Set(
        $("participants").value
          .split(",")
          .map((name) => name.trim())
          .filter(Boolean),
      ),
    ],
    speaker: nullable($("speaker").value),
    addressee: nullable($("addressee").value),
    source: {
      kind: $("source-kind").value,
      label: nullable($("source-label").value),
      external_id: null,
    },
  };

  const generation = ++state.generation;
  state.busy = true;
  updateControls();
  message("Analizando la conversación…");

  try {
    const result = await request("/api/analyses", {
      method: "POST",
      body: payload,
    });

    if (generation !== state.generation) return;

    state.analysis = result;
    state.candidates = result.candidates.map((candidate) => ({
      ...candidate,
      values: { ...candidate.values },
      decision: "review",
      resolved: new Set(),
    }));

    renderCandidates();

    message(
      result.candidates.length
        ? `Se detectaron ${result.candidates.length} candidatos. ` +
          "Revísalos antes de guardarlos."
        : "No se detectaron compromisos en este texto.",
      "success",
    );
  } catch (error) {
    message(error.message, "error");
  } finally {
    if (generation === state.generation) {
      state.busy = false;
      updateControls();
    }
  }
});

function buildSavePayload(selected) {
  return {
    analysis_id: state.analysis.analysis_id,
    reference_date: state.analysis.reference_date,
    source: state.analysis.source,
    items: selected.map((candidate) => ({
      candidate_id: candidate.candidate_id,
      values: { ...candidate.values },
      extraction: {
        source_quote: candidate.source_quote,
        confidence: candidate.confidence,
        priority_origin: candidate.priority_origin,
        ambiguities: candidate.ambiguities,
      },
      resolved_ambiguities: [...candidate.resolved],
    })),
  };
}

function validateSelected(selected) {
  for (const candidate of selected) {
    for (const input of candidate.element.querySelectorAll(
      "input, textarea, select",
    )) {
      if (!input.reportValidity()) return false;
    }
  }
  return true;
}

function showFieldErrors(error, selected) {
  for (const detail of error.details || []) {
    const match = detail.field?.match(
      /^body\.items\.(\d+)\.values\.([a-z_]+)$/,
    );

    if (!match) continue;

    const candidate = selected[Number(match[1])];
    const input = candidate?.element.querySelector(
      `[data-field="${match[2]}"]`,
    );

    if (input) {
      input.setCustomValidity(detail.message);
      input.reportValidity();
    }
  }
}

$("save-button").addEventListener("click", async () => {
  if (state.busy) return;

  let selected = acceptedCandidates();

  if (!state.pendingSave) {
    if (!selected.length || !validateSelected(selected)) return;

    state.pendingSave = {
      key: crypto.randomUUID(),
      payload: buildSavePayload(selected),
    };
  }

  // En un reintento se reutilizan exactamente el mismo cuerpo y clave.
  const pending = state.pendingSave;
  const selectedIds = new Set(
    pending.payload.items.map((item) => item.candidate_id),
  );

  selected = state.candidates.filter(
    (candidate) => selectedIds.has(candidate.candidate_id),
  );

  state.busy = true;
  updateControls();
  message("Guardando los compromisos seleccionados…");

  try {
    // Permite recuperar un guardado incierto si se recarga esta pestaña.
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(pending));

    const result = await request("/api/commitments", {
      method: "POST",
      headers: { "Idempotency-Key": pending.key },
      body: pending.payload,
      timeout: 20000,
    });

    sessionStorage.removeItem(STORAGE_KEY);
    state.pendingSave = null;

    state.candidates = state.candidates.filter(
      (candidate) => !selectedIds.has(candidate.candidate_id),
    );

    const savedList = $("saved-list");
    savedList.replaceChildren();

    for (const item of result.items) {
      const li = document.createElement("li");
      li.textContent =
        `${item.title} · ${statusLabels[item.status]} · ID: ${item.id}`;
      savedList.append(li);
    }

    $("saved-section").hidden = false;
    renderCandidates();

    message(
      `${result.items.length} compromisos guardados. ` +
      "Los candidatos no seleccionados no se guardaron.",
      "success",
    );
  } catch (error) {
    // Estos errores confirman que este lote no se creó.
    if (error.status === 422 || error.status === 409) {
      sessionStorage.removeItem(STORAGE_KEY);
      state.pendingSave = null;
    }

    state.busy = false;
    updateControls();
    showFieldErrors(error, selected);

    const retry = state.pendingSave
      ? " Reintenta el guardado: se conservará la misma solicitud " +
        "para evitar duplicados."
      : " Revisa los campos antes de volver a guardar.";

    message(error.message + retry, "error");
  } finally {
    state.busy = false;
    updateControls();
  }
});

try {
  const stored = sessionStorage.getItem(STORAGE_KEY);

  if (stored) {
    const pending = JSON.parse(stored);

    if (
      typeof pending.key !== "string" ||
      !Array.isArray(pending.payload?.items)
    ) {
      throw new Error("Registro de recuperación inválido.");
    }

    state.pendingSave = pending;

    message(
      "Hay un guardado pendiente de confirmar de esta pestaña. " +
      "Pulsa «Reintentar guardado» antes de iniciar otro análisis.",
    );
  }
} catch {
  message(
    "No se pudo acceder al registro de recuperación de esta pestaña. " +
    "Comprueba que el navegador permita almacenamiento de sesión.",
    "error",
  );
}

updateControls();