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
    this.classList = { add: () => {}, remove: () => {}, contains: () => false };
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

test("reloadSettings reconciles recipe catalog and runs jointly and handles sync errors safely", async () => {
  let recipesLoaded = false;
  let recipeRunsLoaded = false;
  const messages = [];

  const context = vm.createContext({
    window: {
      confirm: () => true,
      alert: () => {},
    },
    t: (key) => key,
    reloadSettingsButton: { disabled: false },
    api: async (url) => {
      if (url === "/api/v1/settings/reload") return { status: "reloaded" };
      if (url === "/api/v1/status") return { model_provider: "ollama", running_preset: "ollama-local" };
    },
    renderTopologyBadge: () => {},
    renderModelStatus: () => {},
    renderRunningSettings: () => {},
    renderConnection: () => {},
    renderCurrentView: () => {},
    resetRecipeControls: () => {},
    renderRecipeSelection: () => {},
    renderRecipeRuns: () => {},
    loadRecipes: async () => {
      recipesLoaded = true;
      throw new Error("Recipes service unreachable");
    },
    loadRecipeRuns: async () => {
      recipeRunsLoaded = true;
    },
    conversationRevision: 0,
    currentView: null,
    chatTranscript: { replaceChildren: () => {} },
    appendChatMessage: (role, text) => { messages.push({ role, text }); },
  });

  const fnMatch = appSource.match(/async function reloadSettings\(\) \{[\s\S]*?\n\}/);
  assert.ok(fnMatch);
  vm.runInContext(fnMatch[0], context);

  await context.reloadSettings();
  assert.equal(recipesLoaded, true);
  assert.equal(recipeRunsLoaded, true);
  assert.ok(messages.some((m) => m.text === "recipeSyncWarning"));
});

test("reloadSettings invalidates conversation/recipe state fail-closed on POST success and locks UI on status readback failure", async () => {
  let chatCleared = false;
  let recipeControlsReset = false;
  let resultsCleared = false;
  let stateAtReadback = null;
  let alertMsg = null;
  const messages = [];
  const connectionState = new MockElement("span");
  const messageInput = { disabled: false };
  const prepareRecipeButton = { disabled: false };
  const newConversationButton = { disabled: false };
  const reloadSettingsButton = { disabled: false };
  const actionButtons = [{ disabled: false }, { disabled: false }];
  const resultsContent = { replaceChildren: () => { resultsCleared = true; } };
  const resultsSection = { hidden: false };

  let context;
  context = vm.createContext({
    window: {
      confirm: () => true,
      alert: (msg) => { alertMsg = msg; },
    },
    t: (key) => key,
    connectionState,
    messageInput,
    prepareRecipeButton,
    newConversationButton,
    reloadSettingsButton,
    api: async (url) => {
      if (url === "/api/v1/settings/reload") {
        return { status: "reloaded" };
      }
      if (url === "/api/v1/status") {
        stateAtReadback = {
          currentView: context.currentView,
          planKeys: Object.keys(context.planOutcomes),
          chatCleared,
          recipeControlsReset,
          resultsCleared,
        };
        throw new Error("Status endpoint connection reset");
      }
    },
    conversationRevision: 0,
    currentView: { kind: "agent", payload: { old: "state" } },
    appStatus: { setup_url: "http://127.0.0.1:8766/?token=old" },
    modelConnection: { provider: "fixture" },
    connectionStatus: "connected",
    planOutcomes: { "old-plan": { confirmation_pending: true } },
    resultsRequestVersion: 2,
    resultsContent,
    resultsSection,
    actionButtons,
    chatTranscript: {
      replaceChildren: () => { chatCleared = true; },
    },
    appendChatMessage: (role, text) => { messages.push({ role, text }); },
    renderCurrentView: () => {},
    resetRecipeControls: () => { recipeControlsReset = true; },
    renderRecipeSelection: () => {},
    renderRecipeRuns: () => {},
  });

  const fnMatch = appSource.match(/async function reloadSettings\(\) \{[\s\S]*?\n\}/);
  assert.ok(fnMatch);
  vm.runInContext(fnMatch[0], context);

  await context.reloadSettings();

  // 1. Old conversation and recipe/plan state must be cleared fail-closed
  assert.equal(chatCleared, true);
  assert.equal(recipeControlsReset, true);
  assert.equal(resultsCleared, true);
  assert.equal(resultsSection.hidden, true);
  assert.equal(context.currentView, null);
  assert.deepEqual(Object.keys(context.planOutcomes), []);
  assert.equal(context.appStatus, null);
  assert.equal(context.modelConnection, null);
  assert.equal(context.connectionStatus, "disconnected");
  assert.deepEqual(stateAtReadback, {
    currentView: null,
    planKeys: [],
    chatCleared: true,
    recipeControlsReset: true,
    resultsCleared: true,
  });
  assert.ok(messages.some((m) => m.text === "conversationReset"));

  // 2. Safe readback error must be presented (not old state, not unmutated reload error)
  assert.ok(messages.some((m) => m.text === "statusReadbackError"));
  assert.equal(alertMsg, "statusReadbackError");
  assert.ok(!alertMsg.includes("Status endpoint connection reset"));
  assert.equal(connectionState.textContent, "statusReadbackError");

  // 3. UI interactions must remain locked/disabled until refresh
  assert.equal(messageInput.disabled, true);
  assert.equal(prepareRecipeButton.disabled, true);
  assert.equal(newConversationButton.disabled, true);
  assert.equal(reloadSettingsButton.disabled, true);
  assert.ok(actionButtons.every((button) => button.disabled));
});

test("isLoopbackHost and isLoopbackUrl validate genuine 127/8 and IPv6 loopback addresses and reject fake domains", () => {
  const hostFnMatch = appSource.match(/function isLoopbackHost\(hostname\) \{[\s\S]*?\n\}/);
  const urlFnMatch = appSource.match(/function isLoopbackUrl\(rawUrl\) \{[\s\S]*?\n\}/);
  assert.ok(hostFnMatch);
  assert.ok(urlFnMatch);

  const context = vm.createContext({ URL });
  vm.runInContext(hostFnMatch[0], context);
  vm.runInContext(urlFnMatch[0], context);

  // Accepted loopback hosts (127.0.0.0/8, localhost, IPv6 ::1)
  assert.equal(context.isLoopbackHost("127.0.0.1"), true);
  assert.equal(context.isLoopbackHost("127.0.0.2"), true);
  assert.equal(context.isLoopbackHost("127.255.255.254"), true);
  assert.equal(context.isLoopbackHost("127.12.34.56"), true);
  assert.equal(context.isLoopbackHost("localhost"), true);
  assert.equal(context.isLoopbackHost("::1"), true);
  assert.equal(context.isLoopbackHost("[::1]"), true);

  // Rejected non-loopback hosts and subdomain spoofs
  assert.equal(context.isLoopbackHost("127.evil.example"), false);
  assert.equal(context.isLoopbackHost("127.0.0.1.evil.com"), false);
  assert.equal(context.isLoopbackHost("localhost.attacker.org"), false);
  assert.equal(context.isLoopbackHost("192.168.1.1"), false);
  assert.equal(context.isLoopbackHost("example.com"), false);
  assert.equal(context.isLoopbackHost("256.0.0.1"), false);
  assert.equal(context.isLoopbackHost(""), false);
  assert.equal(context.isLoopbackHost(null), false);

  // Accepted loopback URLs (using URL parsing)
  assert.equal(context.isLoopbackUrl("http://127.0.0.1:8765"), true);
  assert.equal(context.isLoopbackUrl("http://127.0.0.2:8766/status"), true);
  assert.equal(context.isLoopbackUrl("http://[::1]:8765/"), true);
  assert.equal(context.isLoopbackUrl("http://localhost:8080"), true);
  assert.equal(context.isLoopbackUrl("https://127.0.0.1:8765/"), true);

  // Rejected URLs
  assert.equal(context.isLoopbackUrl("http://127.evil.example:8765"), false);
  assert.equal(context.isLoopbackUrl("http://127.0.0.1.attacker.com:8765"), false);
  assert.equal(context.isLoopbackUrl("http://attacker.com/"), false);
  assert.equal(context.isLoopbackUrl("ftp://127.0.0.1:8765"), false);
  assert.equal(context.isLoopbackUrl("javascript:alert(1)"), false);
  assert.equal(context.isLoopbackUrl("not a url"), false);

  // Ensure parsing does not forward or leak query token
  const parsed = new URL("http://127.0.0.1:8766/?token=secret123");
  assert.equal(context.isLoopbackUrl(parsed.href), true);
  // Extracted hostname has zero token disclosure
  assert.equal(parsed.hostname, "127.0.0.1");
  assert.equal(parsed.hostname.includes("token"), false);
});
