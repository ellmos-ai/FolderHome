const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");

class MockElement {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.attributes = {};
    this.classList = {
      _classes: new Set(),
      add: (...cls) => cls.forEach(c => this.classList._classes.add(c)),
      remove: (...cls) => cls.forEach(c => this.classList._classes.delete(c)),
      contains: c => this.classList._classes.has(c),
    };
    this.hidden = false;
    this.value = "";
    this.textContent = "";
  }
  append(...items) {
    for (const item of items) {
      item.parent = this;
      this.children.push(item);
    }
  }
  replaceChildren(...items) {
    this.children = [];
    this.append(...items);
  }
  setAttribute(name, val) { this.attributes[name] = String(val); }
  getAttribute(name) { return this.attributes[name] !== undefined ? this.attributes[name] : null; }
  addEventListener(event, fn) { this.listeners[event] = fn; }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
  querySelectorAll(selector) {
    const matches = [];
    const checkMatch = (node, sel) => {
      let s = sel.trim();
      const tagMatch = s.match(/^([a-z0-9]+)/i);
      if (tagMatch) {
        if (node.tag.toLowerCase() !== tagMatch[1].toLowerCase()) return false;
        s = s.slice(tagMatch[1].length);
      }
      const idMatch = s.match(/#([a-zA-Z0-9_-]+)/);
      if (idMatch) {
        if (!node.attributes || node.attributes.id !== idMatch[1]) return false;
      }
      return true;
    };
    const walk = (node) => {
      for (const child of node.children) {
        if (checkMatch(child, selector)) {
          matches.push(child);
        }
        walk(child);
      }
    };
    walk(this);
    return matches;
  }
}

function setupPresetDOM() {
  const root = new MockElement("div");

  const providerSelect = new MockElement("select");
  providerSelect.setAttribute("id", "provider");
  providerSelect.value = "fixture";
  root.append(providerSelect);

  const fields = [
    "ollama-host",
    "ollama-model-id",
    "bedrock-model-id",
    "aws-region",
    "anthropic-model-id",
    "openai-model-id",
    "openai-base-url",
    "preset-name",
  ];
  for (const f of fields) {
    const el = new MockElement("input");
    el.setAttribute("id", f);
    root.append(el);
  }

  for (const name of ["ollama", "bedrock", "anthropic", "openai"]) {
    const group = new MockElement("div");
    group.setAttribute("id", `${name}-fields`);
    group.hidden = true;
    root.append(group);
  }

  const presetList = new MockElement("div");
  presetList.setAttribute("id", "preset-list");
  root.append(presetList);

  const context = vm.createContext({
    document: {
      querySelectorAll: sel => root.querySelectorAll(sel),
      querySelector: sel => root.querySelector(sel),
      createElement: tag => new MockElement(tag),
    },
    providerSelect,
    presetList,
    presets: {},
    activePreset: null,
    t: k => k,
    renderGateHint: () => {},
    invalidate: () => {},
    textElement: (tag, text, cls) => {
      const el = new MockElement(tag);
      el.textContent = text;
      if (cls) el.classList.add(cls);
      return el;
    },
    showError: () => {},
  });

  const source = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
  const modelStart = source.indexOf("const PRESET_NAME =");
  const modelEnd = source.indexOf("function calendarAccountRow(");
  vm.runInContext(source.slice(modelStart, modelEnd), context);

  return { context, root, providerSelect, presetList };
}

test("modelFromForm returns both model_provider and provider", () => {
  const { context, root, providerSelect } = setupPresetDOM();

  providerSelect.value = "ollama";
  root.querySelector("#ollama-host").value = "http://127.0.0.1:11434";
  root.querySelector("#ollama-model-id").value = "qwen3:4b";

  const model = context.modelFromForm();
  assert.equal(model.model_provider, "ollama");
  assert.equal(model.provider, "ollama");
  assert.equal(model.ollama_host, "http://127.0.0.1:11434");
  assert.equal(model.ollama_model_id, "qwen3:4b");
});

test("fillForm populates fields from entry with model_provider key", () => {
  const { context, root, providerSelect } = setupPresetDOM();

  const entry = {
    model_provider: "bedrock",
    bedrock_model_id: "eu.amazon.nova-micro-v1:0",
    aws_region: "eu-central-1",
  };

  context.fillForm(entry);
  assert.equal(providerSelect.value, "bedrock");
  assert.equal(root.querySelector("#bedrock-model-id").value, "eu.amazon.nova-micro-v1:0");
  assert.equal(root.querySelector("#aws-region").value, "eu-central-1");
  assert.equal(root.querySelector("#bedrock-fields").hidden, false);
});

test("renderPresets renders preset label with provider name from model_provider", () => {
  const { context, presetList } = setupPresetDOM();

  context.presets = {
    "bedrock-nova": {
      model_provider: "bedrock",
      bedrock_model_id: "eu.amazon.nova-micro-v1:0",
    },
  };
  context.activePreset = "bedrock-nova";

  context.renderPresets();
  assert.equal(presetList.children.length, 1);
  const row = presetList.children[0];
  const span = row.children[0];
  assert.match(span.textContent, /bedrock-nova · bedrock · eu\.amazon\.nova-micro-v1:0/);
});
