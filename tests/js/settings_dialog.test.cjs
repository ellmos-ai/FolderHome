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
    this.href = "";
  }
  append(...items) {
    for (const item of items) {
      item.parent = this;
      this.children.push(item);
    }
  }
  setAttribute(name, val) { this.attributes[name] = String(val); }
  getAttribute(name) { return this.attributes[name] !== undefined ? this.attributes[name] : null; }
  addEventListener(event, fn) {
    this.listeners[event] = this.listeners[event] || [];
    this.listeners[event].push(fn);
  }
  click() {
    for (const fn of this.listeners.click || []) {
      fn({ target: this });
    }
  }
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

test("open-settings-btn and settings-dialog exist in shipped HTML", () => {
  assert.match(html, /id="open-settings-btn"/);
  assert.match(html, /id="settings-dialog"/);
  assert.match(html, /id="close-settings-dialog-btn"/);
  assert.match(html, /id="settings-command"/);
  assert.match(html, /id="copy-settings-command-btn"/);
  assert.match(html, /scripts\\START\.cmd/);
});

test("openSettingsModal opens dialog and closeSettingsModal closes it", () => {
  const settingsDialog = new MockElement("div");
  settingsDialog.hidden = true;
  const setupServerActiveBox = new MockElement("div");
  setupServerActiveBox.hidden = true;
  const openSetupServerLink = new MockElement("a");

  const context = vm.createContext({
    settingsDialog,
    setupServerActiveBox,
    openSetupServerLink,
    appStatus: null,
  });

  const openFn = appSource.match(/function openSettingsModal\(\) \{[\s\S]*?\n\}/);
  const closeFn = appSource.match(/function closeSettingsModal\(\) \{[\s\S]*?\n\}/);
  assert.ok(openFn);
  assert.ok(closeFn);

  vm.runInContext(openFn[0], context);
  vm.runInContext(closeFn[0], context);

  context.openSettingsModal();
  assert.equal(settingsDialog.hidden, false);
  assert.equal(setupServerActiveBox.hidden, true);

  context.closeSettingsModal();
  assert.equal(settingsDialog.hidden, true);
});

test("openSettingsModal displays running setup link when setup_url is present", () => {
  const settingsDialog = new MockElement("div");
  settingsDialog.hidden = true;
  const setupServerActiveBox = new MockElement("div");
  setupServerActiveBox.hidden = true;
  const openSetupServerLink = new MockElement("a");

  const context = vm.createContext({
    settingsDialog,
    setupServerActiveBox,
    openSetupServerLink,
    appStatus: { setup_url: "http://127.0.0.1:8766/" },
  });

  const openFn = appSource.match(/function openSettingsModal\(\) \{[\s\S]*?\n\}/);
  assert.ok(openFn);
  vm.runInContext(openFn[0], context);

  context.openSettingsModal();
  assert.equal(settingsDialog.hidden, false);
  assert.equal(setupServerActiveBox.hidden, false);
  assert.equal(openSetupServerLink.href, "http://127.0.0.1:8766/");
  // Does not disclose app session token
  assert.ok(!openSetupServerLink.href.includes("token="));
});

test("copySettingsCommand copies command to clipboard and shows feedback", async () => {
  let copiedText = null;
  const copySettingsCommandButton = new MockElement("button");
  copySettingsCommandButton.textContent = "Copy";

  const context = vm.createContext({
    copySettingsCommandButton,
    navigator: {
      clipboard: {
        writeText: async (text) => { copiedText = text; },
      },
    },
    t: (key) => key === "commandCopied" ? "Copied!" : "Copy",
    setTimeout: (fn) => fn(),
  });

  const copyFn = appSource.match(/async function copySettingsCommand\(\) \{[\s\S]*?\n\}/);
  assert.ok(copyFn);
  vm.runInContext(copyFn[0], context);

  await context.copySettingsCommand();
  assert.equal(copiedText, "scripts\\START.cmd");
  assert.equal(copySettingsCommandButton.textContent, "Copy");
});
