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
  replaceChildren(...items) {
    this.children = [];
    this.append(...items);
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
}

class MockStorage {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return Object.prototype.hasOwnProperty.call(this.store, key) ? this.store[key] : null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

const html = readFileSync(join(__dirname, "../../src/folderhome/web_ui/index.html"), "utf8");
const appSource = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");
const css = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.css"), "utf8");

test("capability info button and grid exist in shipped HTML with visible ⓘ symbol, localized aria-label/title and default closed state", () => {
  assert.match(html, /id="capability-info-btn"[^>]*>ⓘ<\/button>/, "button must visibly display ⓘ symbol");
  assert.match(html, /id="capability-info-btn"[^>]*aria-expanded="false"/);
  assert.match(html, /id="capability-info-btn"[^>]*aria-controls="capability-grid"/);
  assert.match(html, /id="capability-info-btn"[^>]*data-i18n-aria-label="capabilityInfoShow"/);
  assert.match(html, /id="capability-info-btn"[^>]*data-i18n-title="capabilityInfoShow"/);
  assert.match(html, /id="capability-info-btn"[^>]*aria-label="Show capabilities"/);
  assert.match(html, /id="capability-info-btn"[^>]*title="Show capabilities"/);
  // Ensure the button is not a pure text button with data-i18n text replacement
  assert.doesNotMatch(html, /id="capability-info-btn"[^>]*data-i18n="capabilityInfoShow"/);
  assert.match(html, /id="capability-grid"[^>]*hidden/);
  assert.match(html, /id="capability-grid"[^>]*aria-live="polite"/);
});

test("capability-controls and capability-info-btn styles exist in app.css", () => {
  assert.match(css, /\.capability-controls\s*\{/);
  assert.match(css, /\.capability-info-btn\s*\{/);
  assert.match(css, /\.capability-info-btn\[aria-expanded="true"\]/);
});

test("toggleCapabilityInfo toggles aria-expanded, hidden, aria-label, title, preserves visible ⓘ and persists state in sessionStorage", () => {
  const capabilityInfoButton = new MockElement("button");
  capabilityInfoButton.setAttribute("aria-expanded", "false");
  capabilityInfoButton.setAttribute("aria-label", "Show capabilities");
  capabilityInfoButton.setAttribute("title", "Show capabilities");
  capabilityInfoButton.textContent = "ⓘ";

  const capabilityGrid = new MockElement("div");
  capabilityGrid.hidden = true;

  const mockSessionStorage = new MockStorage();

  const sampleItems = [
    { capability_id: "documents.search", title: "Document search", surface_status: "interactive_read_only" },
    { capability_id: "documents.create", title: "Create documents", surface_status: "agent_guided" },
  ];

  const context = vm.createContext({
    capabilityInfoButton,
    capabilityGrid,
    capabilityItems: sampleItems,
    language: "en",
    window: {
      sessionStorage: mockSessionStorage,
    },
    t: (key) => {
      const dict = {
        capabilityInfoShow: "Show capabilities",
        capabilityInfoHide: "Hide capabilities",
        directUse: "Available here",
        agentUse: "Guided by the FolderHome agent",
        cliUse: "Through safe CLI workflows",
      };
      return dict[key] || key;
    },
    textElement: (tag, text, cls) => {
      const el = new MockElement(tag);
      el.textContent = text;
      if (cls) el.className = cls;
      return el;
    },
    document: {
      createElement: (tag) => new MockElement(tag),
    },
  });

  const storageKeyMatch = appSource.match(/const CAPABILITY_STORAGE_KEY = "([^"]+)";/);
  const getStoredFn = appSource.match(/function getStoredCapabilityState\(\) \{[\s\S]*?\n\}/);
  const setStoredFn = appSource.match(/function setStoredCapabilityState\([^)]*\) \{[\s\S]*?\n\}/);
  const setExpandedFn = appSource.match(/function setCapabilityExpanded\([^)]*\) \{[\s\S]*?\n\}/);
  const toggleFn = appSource.match(/function toggleCapabilityInfo\(\) \{[\s\S]*?\n\}/);
  const initFn = appSource.match(/function initCapabilityInfo\(\) \{[\s\S]*?\n\}/);
  const renderFn = appSource.match(/function renderCapabilities\(\) \{[\s\S]*?\n\}/);
  const capTitlesMatch = appSource.match(/const capabilityTitles = \{[\s\S]*?\n\};/);

  assert.ok(storageKeyMatch, "CAPABILITY_STORAGE_KEY found");
  assert.ok(getStoredFn, "getStoredCapabilityState function found");
  assert.ok(setStoredFn, "setStoredCapabilityState function found");
  assert.ok(setExpandedFn, "setCapabilityExpanded function found");
  assert.ok(toggleFn, "toggleCapabilityInfo function found");
  assert.ok(initFn, "initCapabilityInfo function found");
  assert.ok(renderFn, "renderCapabilities function found");
  assert.ok(capTitlesMatch, "capabilityTitles object found");

  vm.runInContext(storageKeyMatch[0], context);
  vm.runInContext(getStoredFn[0], context);
  vm.runInContext(setStoredFn[0], context);
  vm.runInContext(capTitlesMatch[0], context);
  vm.runInContext(renderFn[0], context);
  vm.runInContext(setExpandedFn[0], context);
  vm.runInContext(toggleFn[0], context);
  vm.runInContext(initFn[0], context);

  // 1. Initial State: closed by default
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "false");
  assert.equal(capabilityGrid.hidden, true);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Show capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Show capabilities");
  assert.equal(capabilityInfoButton.textContent, "ⓘ");
  assert.equal(mockSessionStorage.getItem("folderhome.capability_info_open"), null);

  // 2. Open: expands, unhides grid, updates aria-label/title, retains ⓘ, renders cards, persists true
  context.toggleCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "true");
  assert.equal(capabilityGrid.hidden, false);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Hide capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Hide capabilities");
  assert.equal(capabilityInfoButton.textContent, "ⓘ");
  assert.equal(mockSessionStorage.getItem("folderhome.capability_info_open"), "true");
  assert.equal(capabilityGrid.children.length, 2);
  assert.equal(capabilityGrid.children[0].children[0].textContent, "Document search");

  // 3. Close: collapses, hides grid, updates aria-label/title, retains ⓘ, persists false
  context.toggleCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "false");
  assert.equal(capabilityGrid.hidden, true);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Show capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Show capabilities");
  assert.equal(capabilityInfoButton.textContent, "ⓘ");
  assert.equal(mockSessionStorage.getItem("folderhome.capability_info_open"), "false");
});

test("sessionStorage initialization: defaults to closed when key is absent, restores open when sessionStorage is true", () => {
  const capabilityInfoButton = new MockElement("button");
  const capabilityGrid = new MockElement("div");
  const mockSessionStorage = new MockStorage();

  const context = vm.createContext({
    capabilityInfoButton,
    capabilityGrid,
    capabilityItems: [],
    language: "en",
    window: {
      sessionStorage: mockSessionStorage,
    },
    t: (key) => (key === "capabilityInfoHide" ? "Hide capabilities" : "Show capabilities"),
    renderCapabilities: () => {},
  });

  const storageKeyMatch = appSource.match(/const CAPABILITY_STORAGE_KEY = "([^"]+)";/);
  const getStoredFn = appSource.match(/function getStoredCapabilityState\(\) \{[\s\S]*?\n\}/);
  const setStoredFn = appSource.match(/function setStoredCapabilityState\([^)]*\) \{[\s\S]*?\n\}/);
  const setExpandedFn = appSource.match(/function setCapabilityExpanded\([^)]*\) \{[\s\S]*?\n\}/);
  const initFn = appSource.match(/function initCapabilityInfo\(\) \{[\s\S]*?\n\}/);

  vm.runInContext(storageKeyMatch[0], context);
  vm.runInContext(getStoredFn[0], context);
  vm.runInContext(setStoredFn[0], context);
  vm.runInContext(setExpandedFn[0], context);
  vm.runInContext(initFn[0], context);

  // Case A: Missing stored state -> defaults to closed
  context.initCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "false");
  assert.equal(capabilityGrid.hidden, true);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Show capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Show capabilities");

  // Case B: Stored state is "true" -> restores open state
  mockSessionStorage.setItem("folderhome.capability_info_open", "true");
  context.initCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "true");
  assert.equal(capabilityGrid.hidden, false);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Hide capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Hide capabilities");
});

test("capability titles and status descriptions have exact German parity and real umlauts", () => {
  const context = vm.createContext({});
  const transBlock = appSource.slice(
    appSource.indexOf("const translations ="),
    appSource.indexOf("const capabilityTitles =")
  );
  const capBlock = appSource.slice(
    appSource.indexOf("const capabilityTitles ="),
    appSource.indexOf("const profileSelect =")
  );

  vm.runInContext(transBlock.replace("const translations =", "var translations ="), context);
  vm.runInContext(capBlock.replace("const capabilityTitles =", "var capabilityTitles ="), context);

  const enKeys = Object.keys(context.capabilityTitles.en);
  const deKeys = Object.keys(context.capabilityTitles.de);
  assert.deepEqual(enKeys.sort(), deKeys.sort());

  // Check real umlauts in German capability titles
  assert.equal(context.capabilityTitles.de["documents.create"], "Dokumente und Präsentationen erstellen");
  assert.equal(context.capabilityTitles.de["finance.overview"], "Finanzen und Verträge überblicken");
  assert.equal(context.capabilityTitles.de["legal.orient"], "Bescheide und Rechtsänderungen verstehen");

  // Check translations for info button aria-label/title
  assert.equal(context.translations.en.capabilityInfoShow, "Show capabilities");
  assert.equal(context.translations.en.capabilityInfoHide, "Hide capabilities");
  assert.equal(context.translations.de.capabilityInfoShow, "Funktionen anzeigen");
  assert.equal(context.translations.de.capabilityInfoHide, "Funktionen ausblenden");
});
