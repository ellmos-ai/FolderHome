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
    this.hidden = false;
    this.textContent = "";
  }
  append(...items) {
    for (const item of items) {
      item.parent = this;
      this.children.push(item);
    }
  }
  setAttribute(name, val) { this.attributes[name] = String(val); }
  getAttribute(name) { return this.attributes[name] !== undefined ? this.attributes[name] : null; }
  querySelector(selector) {
    if (selector.startsWith("#")) {
      const id = selector.slice(1);
      const walk = (node) => {
        if (node.attributes && node.attributes.id === id) return node;
        for (const child of node.children) {
          const found = walk(child);
          if (found) return found;
        }
        return null;
      };
      return walk(this);
    }
    return null;
  }
}

const html = readFileSync(join(__dirname, "../../src/folderhome/web_ui/index.html"), "utf8");
const appSource = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");

test("running-settings exists in shipped HTML next to model-status", () => {
  assert.match(html, /id="running-settings"/);
  assert.match(html, /id="running-settings-summary"/);
  assert.match(html, /id="settings-stale-banner"/);
  assert.match(html, /id="reload-settings-btn"/);
});

test("renderRunningSettings displays running preset, provider and model id", () => {
  const root = new MockElement("div");
  const summary = new MockElement("span");
  summary.setAttribute("id", "running-settings-summary");
  const staleBanner = new MockElement("div");
  staleBanner.setAttribute("id", "settings-stale-banner");
  staleBanner.hidden = true;
  const staleText = new MockElement("span");
  staleText.setAttribute("id", "settings-stale-text");

  root.append(summary, staleBanner, staleText);

  // Extract translations and renderRunningSettings
  const transMatch = appSource.match(/const translations = \{[\s\S]*?\n\};\n/);
  assert.ok(transMatch);

  const context = vm.createContext({
    document: {
      querySelector: sel => root.querySelector(sel),
    },
    appStatus: {
      running_preset: "ollama-laptop",
      model_provider: "ollama",
      model_connection: { model_id: "qwen2.5:7b" },
      settings_stale: false,
      saved_preset: "ollama-laptop",
    },
    language: "en",
    t: (key, params) => {
      const trans = {
        runningLabel: "Running:",
        noPresetFlags: "no preset / flags",
        savedSettingDiffers: "Saved setting differs: {preset} — reload to apply",
      };
      let val = trans[key] || key;
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          val = val.replace(`{${k}}`, v);
        }
      }
      return val;
    },
  });

  const fnMatch = appSource.match(/function renderRunningSettings\(\) \{[\s\S]*?\n\}/);
  assert.ok(fnMatch);
  vm.runInContext(fnMatch[0], context);

  context.renderRunningSettings();

  assert.equal(summary.textContent, "ollama-laptop · ollama · qwen2.5:7b");
  assert.equal(staleBanner.hidden, true);
});

test("renderRunningSettings shows stale banner when launch.json has a different preset", () => {
  const root = new MockElement("div");
  const summary = new MockElement("span");
  summary.setAttribute("id", "running-settings-summary");
  const staleBanner = new MockElement("div");
  staleBanner.setAttribute("id", "settings-stale-banner");
  staleBanner.hidden = true;
  const staleText = new MockElement("span");
  staleText.setAttribute("id", "settings-stale-text");

  root.append(summary, staleBanner, staleText);

  const context = vm.createContext({
    document: {
      querySelector: sel => root.querySelector(sel),
    },
    appStatus: {
      running_preset: "ollama-laptop",
      model_provider: "ollama",
      model_connection: { model_id: "qwen2.5:7b" },
      settings_stale: true,
      saved_preset: "bedrock-nova-micro",
    },
    language: "en",
    t: (key, params) => {
      const trans = {
        runningLabel: "Running:",
        noPresetFlags: "no preset / flags",
        savedSettingDiffers: "Saved setting differs: {preset} — reload to apply",
      };
      let val = trans[key] || key;
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          val = val.replace(`{${k}}`, v);
        }
      }
      return val;
    },
  });

  const fnMatch = appSource.match(/function renderRunningSettings\(\) \{[\s\S]*?\n\}/);
  vm.runInContext(fnMatch[0], context);

  context.renderRunningSettings();

  assert.equal(summary.textContent, "ollama-laptop · ollama · qwen2.5:7b");
  assert.equal(staleBanner.hidden, false);
  assert.equal(staleText.textContent, "Saved setting differs: bedrock-nova-micro — reload to apply");
});

test("reloadSettings aborts when user declines confirmation", async () => {
  let confirmAsked = false;
  let apiCalled = false;
  const context = vm.createContext({
    window: {
      confirm: () => { confirmAsked = true; return false; },
      alert: () => {},
    },
    t: (key) => key,
    reloadSettingsButton: { disabled: false },
    api: async () => { apiCalled = true; },
  });

  const fnMatch = appSource.match(/async function reloadSettings\(\) \{[\s\S]*?\n\}/);
  assert.ok(fnMatch);
  vm.runInContext(fnMatch[0], context);

  await context.reloadSettings();
  assert.equal(confirmAsked, true);
  assert.equal(apiCalled, false);
});

test("reloadSettings posts reload request and updates status and resets transcript on success", async () => {
  const calls = [];
  let chatCleared = false;
  let assistantMessage = null;
  const context = vm.createContext({
    window: {
      confirm: () => true,
      alert: () => {},
    },
    t: (key) => key,
    reloadSettingsButton: { disabled: false },
    api: async (url, opts) => {
      calls.push({ url, opts });
      if (url === "/api/v1/settings/reload") {
        return { schema: "folderhome.local-settings-reload-response.v1", status: "reloaded" };
      }
      if (url === "/api/v1/status") {
        return {
          model_provider: "bedrock",
          model_state: "configured_unverified",
          running_preset: "bedrock-nova-micro",
          model_connection: { model_id: "amazon.nova-micro-v1:0" },
        };
      }
    },
    renderTopologyBadge: () => {},
    renderModelStatus: () => {},
    renderRunningSettings: () => {},
    renderConnection: () => {},
    renderCurrentView: () => {},
    conversationRevision: 0,
    currentView: "someView",
    chatTranscript: {
      replaceChildren: () => { chatCleared = true; },
    },
    appendChatMessage: (role, text) => { assistantMessage = { role, text }; },
  });

  const fnMatch = appSource.match(/async function reloadSettings\(\) \{[\s\S]*?\n\}/);
  assert.ok(fnMatch);
  vm.runInContext(fnMatch[0], context);

  await context.reloadSettings();
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "/api/v1/settings/reload");
  assert.equal(calls[1].url, "/api/v1/status");
  assert.equal(chatCleared, true);
  assert.equal(assistantMessage.text, "conversationReset");
});

test("reloadSettings displays error message when reload fails", async () => {
  let alertMsg = null;
  const context = vm.createContext({
    window: {
      confirm: () => true,
      alert: (msg) => { alertMsg = msg; },
    },
    t: (key) => key,
    reloadSettingsButton: { disabled: false },
    api: async () => {
      const err = new Error("Request failed");
      err.payload = { message: "Start the app with --allow-network --approve-sensitive-cloud-data to use bedrock-nova-micro" };
      throw err;
    },
  });

  const fnMatch = appSource.match(/async function reloadSettings\(\) \{[\s\S]*?\n\}/);
  assert.ok(fnMatch);
  vm.runInContext(fnMatch[0], context);

  await context.reloadSettings();
  assert.equal(
    alertMsg,
    "Start the app with --allow-network --approve-sensitive-cloud-data to use bedrock-nova-micro"
  );
});
