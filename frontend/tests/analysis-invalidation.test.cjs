const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

// Execute the real app.js handlers with a minimal DOM and a fake API.
// No browser, network, credentials or database are needed.
class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.listeners = {};
    this.dataset = {};
    this.value = "";
    this.disabled = false;
    this.hidden = false;
  }

  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  add(option) { this.append(option); }
  addEventListener(event, handler) {
    (this.listeners[event] ??= []).push(handler);
  }
  async fire(event) {
    for (const handler of this.listeners[event] ?? []) {
      await handler({ preventDefault() {} });
    }
  }
  querySelectorAll(selector) {
    const tags = selector.split(",").map((tag) => tag.trim());
    return this.children.flatMap((child) => [
      ...(tags.includes(child.tag) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
  setCustomValidity() {}
  reportValidity() { return true; }
}

function candidate(text) {
  return {
    candidate_id: text,
    values: {
      title: text, description: null, responsible: "Ana",
      counterparty: null, due_date: "2026-10-21", due_time: null,
      timezone: "America/Bogota", priority: "medium", condition: null,
    },
    source_quote: text, confidence: 0.9, priority_origin: "default",
    ambiguities: [], missing_information: [], status: "pending",
  };
}

function setup() {
  const root = resolve(__dirname, "..");
  const html = readFileSync(resolve(root, "index.html"), "utf8");
  const elements = Object.fromEntries(
    [...html.matchAll(/id="([^"]+)"/g)].map((match) => [
      match[1], new Element(),
    ]),
  );
  elements.timezone.value = "America/Bogota";
  elements["source-kind"].value = "text";
  const calls = [];
  const analyses = [];
  const storage = new Map();
  const context = vm.createContext({
    document: {
      getElementById: (id) => elements[id],
      createElement: (tag) => new Element(tag),
    },
    Option: class extends Element {
      constructor(text, value) { super("option"); this.value = value; }
    },
    window: { confirm: () => true, location: {} },
    sessionStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    },
    crypto: { randomUUID: () => "save-key" },
    getToken: () => "test-token",
    getUser: () => null,
    logout() {},
    request(path, options) {
      calls.push({ path, options });
      if (path === "/api/analyses") {
        return new Promise((resolve, reject) => {
          analyses.push({ resolve, reject });
        });
      }
      return Promise.resolve({
        items: options.body.items.map((item) => ({
          ...item.values, id: item.candidate_id, status: "pending",
        })),
      });
    },
  });
  const source = readFileSync(resolve(root, "app.js"), "utf8")
    .replace(/^import[^\n]+from "\.\/api\.js";\r?\n/, "");
  vm.runInContext(source, context, { filename: "frontend/app.js" });

  async function analyze(text) {
    elements.text.value = text;
    const submission = elements["analysis-form"].fire("submit");
    analyses.at(-1).resolve({
      analysis_id: text, reference_date: "2026-10-20",
      source: { kind: "text" }, candidates: [candidate(text)],
    });
    await submission;
  }

  async function selectFirst() {
    const checkbox = elements["candidate-list"]
      .querySelectorAll("input")
      .find((input) => input.type === "checkbox");
    checkbox.checked = true;
    await checkbox.fire("change");
  }

  return { elements, calls, analyses, context, analyze, selectFirst };
}

for (const replacement of ["Texto B", "", "Texto A "]) {
  test(`editing the input invalidates A: ${JSON.stringify(replacement)}`, async () => {
    const app = setup();
    await app.analyze("Texto A");
    await app.selectFirst();
    assert.equal(app.elements["save-button"].disabled, false);

    app.elements.text.value = replacement;
    await app.elements.text.fire("input");

    assert.equal(app.elements["candidate-list"].children.length, 0);
    assert.equal(app.elements["review-section"].hidden, true);
    assert.equal(app.elements["save-button"].disabled, true);
    assert.equal(vm.runInContext("state.analysis", app.context), null);
    assert.equal(vm.runInContext("acceptedCandidates().length", app.context), 0);

    // Even a direct call to the click handler cannot submit stale data.
    await app.elements["save-button"].fire("click");
    assert.equal(app.calls.filter((call) => call.path === "/api/commitments").length, 0);
  });
}

test("returning to A does not restore its previous selection", async () => {
  const app = setup();
  await app.analyze("Texto A");
  await app.selectFirst();
  for (const text of ["Texto B", "Texto A"]) {
    app.elements.text.value = text;
    await app.elements.text.fire("input");
  }
  assert.equal(app.elements["save-button"].disabled, true);
  assert.equal(app.elements["candidate-list"].children.length, 0);
});

test("saving after replacing A never sends the old commitments", async () => {
  const app = setup();
  await app.analyze("Texto A");
  await app.selectFirst();
  app.elements.text.value = "Texto B";
  await app.elements.text.fire("input");
  await app.elements["save-button"].fire("click");
  assert.equal(app.calls.filter((call) => call.path === "/api/commitments").length, 0);
});

test("a new analysis of B can be selected and saved", async () => {
  const app = setup();
  await app.analyze("Texto A");
  await app.selectFirst();
  app.elements.text.value = "Texto B";
  await app.elements.text.fire("input");

  await app.analyze("Texto B");
  assert.equal(app.elements["save-button"].disabled, true);
  await app.selectFirst();
  await app.elements["save-button"].fire("click");
  const saved = app.calls.filter((call) => call.path === "/api/commitments");
  assert.equal(saved.length, 1);
  assert.equal(saved[0].options.body.analysis_id, "Texto B");
  assert.equal(saved[0].options.body.items[0].values.title, "Texto B");
});

test("a late response cannot restore candidates after invalidation", async () => {
  const app = setup();
  app.elements.text.value = "Texto A";
  const submission = app.elements["analysis-form"].fire("submit");
  app.elements.text.value = "Texto B";
  await app.elements.text.fire("input");
  app.analyses[0].resolve({ candidates: [candidate("Texto A")] });
  await submission;
  assert.equal(app.elements["candidate-list"].children.length, 0);
  assert.equal(app.elements["save-button"].disabled, true);
  assert.equal(app.elements["input-fields"].disabled, false);
});

test("a late error cannot overwrite the invalidation message", async () => {
  const app = setup();
  app.elements.text.value = "Texto A";
  const submission = app.elements["analysis-form"].fire("submit");
  app.elements.text.value = "Texto B";
  await app.elements.text.fire("input");
  const message = app.elements.message.textContent;
  app.analyses[0].reject(new Error("Late error"));
  await submission;
  assert.equal(app.elements.message.textContent, message);
  assert.equal(app.elements["input-fields"].disabled, false);
});
