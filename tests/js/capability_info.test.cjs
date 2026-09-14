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

test("unavailable journey copy is generic and does not mislabel every recipe as an accident", () => {
  assert.match(appSource, /readiness condition remains in force/);
  assert.match(appSource, /Bereitschaftsbedingung bleibt bestehen/);
  assert.doesNotMatch(appSource, /recipeUnavailable: "This packaged accident journey/);
  assert.doesNotMatch(appSource, /recipeUnavailable: "Diese mitgelieferte Unfallreise/);
  assert.doesNotMatch(appSource, /recipeUnavailable: .*because required resources/);
  assert.doesNotMatch(appSource, /recipeUnavailable: .*weil benötigte Ressourcen/);
});

test("capability info button and grid exist in shipped HTML with visible ⓘ symbol, localized aria-label/title and default closed state", () => {
  assert.match(html, /id="capability-info-btn"[^>]*>ⓘ<\/button>/, "button must visibly display ⓘ symbol");
  assert.match(html, /id="capability-info-btn"[^>]*aria-expanded="false"/);
  assert.match(html, /id="capability-info-btn"[^>]*aria-controls="home-info-panel"/);
  assert.match(html, /id="capability-info-btn"[^>]*data-i18n-aria-label="capabilityInfoShow"/);
  assert.match(html, /id="capability-info-btn"[^>]*data-i18n-title="capabilityInfoShow"/);
  assert.match(html, /id="capability-info-btn"[^>]*aria-label="Show security and capabilities"/);
  assert.match(html, /id="capability-info-btn"[^>]*title="Show security and capabilities"/);
  // Ensure the button is not a pure text button with data-i18n text replacement
  assert.doesNotMatch(html, /id="capability-info-btn"[^>]*data-i18n="capabilityInfoShow"/);
  assert.match(html, /id="home-info-panel"[^>]*hidden/);
  assert.match(html, /id="capability-grid"[^>]*aria-live="polite"/);
});

test("home info panel and capability-info-btn styles exist in app.css", () => {
  assert.match(css, /\.home-info-panel\s*\{/);
  assert.match(css, /\.capability-info-btn\s*\{/);
  assert.match(css, /\.capability-info-btn\[aria-expanded="true"\]/);
});

test("toggleCapabilityInfo toggles aria-expanded, hidden, aria-label, title, preserves visible ⓘ and persists state in sessionStorage", () => {
  const capabilityInfoButton = new MockElement("button");
  capabilityInfoButton.setAttribute("aria-expanded", "false");
  capabilityInfoButton.setAttribute("aria-label", "Show security and capabilities");
  capabilityInfoButton.setAttribute("title", "Show security and capabilities");
  capabilityInfoButton.textContent = "ⓘ";

  const capabilityGrid = new MockElement("div");
  const homeInfoPanel = new MockElement("section");
  homeInfoPanel.hidden = true;

  const mockSessionStorage = new MockStorage();

  const sampleItems = [
    { capability_id: "documents.search", title: "Document search", surface_status: "interactive_read_only" },
    { capability_id: "documents.create", title: "Create documents", surface_status: "agent_guided" },
  ];

  const context = vm.createContext({
    capabilityInfoButton,
    capabilityGrid,
    homeInfoPanel,
    capabilityItems: sampleItems,
    connectionStatus: "ready",
    language: "en",
    window: {
      sessionStorage: mockSessionStorage,
    },
    t: (key) => {
      const dict = {
        capabilityInfoShow: "Show security and capabilities",
        capabilityInfoHide: "Hide security and capabilities",
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
  assert.equal(homeInfoPanel.hidden, true);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Show security and capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Show security and capabilities");
  assert.equal(capabilityInfoButton.textContent, "ⓘ");
  assert.equal(mockSessionStorage.getItem("folderhome.capability_info_open"), null);

  // 2. Open: expands, unhides grid, updates aria-label/title, retains ⓘ, renders cards, persists true
  context.toggleCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "true");
  assert.equal(homeInfoPanel.hidden, false);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Hide security and capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Hide security and capabilities");
  assert.equal(capabilityInfoButton.textContent, "ⓘ");
  assert.equal(mockSessionStorage.getItem("folderhome.capability_info_open"), "true");
  assert.equal(capabilityGrid.children.length, 2);
  assert.equal(capabilityGrid.children[0].children[0].textContent, "Document search");

  // 3. Close: collapses, hides grid, updates aria-label/title, retains ⓘ, persists false
  context.toggleCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "false");
  assert.equal(homeInfoPanel.hidden, true);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Show security and capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Show security and capabilities");
  assert.equal(capabilityInfoButton.textContent, "ⓘ");
  assert.equal(mockSessionStorage.getItem("folderhome.capability_info_open"), "false");
});

test("sessionStorage initialization: defaults to closed when key is absent, restores open when sessionStorage is true", () => {
  const capabilityInfoButton = new MockElement("button");
  const capabilityGrid = new MockElement("div");
  const homeInfoPanel = new MockElement("section");
  const mockSessionStorage = new MockStorage();

  const context = vm.createContext({
    capabilityInfoButton,
    capabilityGrid,
    homeInfoPanel,
    capabilityItems: [],
    language: "en",
    window: {
      sessionStorage: mockSessionStorage,
    },
    t: (key) => (key === "capabilityInfoHide" ? "Hide security and capabilities" : "Show security and capabilities"),
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
  assert.equal(homeInfoPanel.hidden, true);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Show security and capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Show security and capabilities");

  // Case B: Stored state is "true" -> restores open state
  mockSessionStorage.setItem("folderhome.capability_info_open", "true");
  context.initCapabilityInfo();
  assert.equal(capabilityInfoButton.getAttribute("aria-expanded"), "true");
  assert.equal(homeInfoPanel.hidden, false);
  assert.equal(capabilityInfoButton.getAttribute("aria-label"), "Hide security and capabilities");
  assert.equal(capabilityInfoButton.getAttribute("title"), "Hide security and capabilities");
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
  assert.equal(context.translations.en.capabilityInfoShow, "Show security and capabilities");
  assert.equal(context.translations.en.capabilityInfoHide, "Hide security and capabilities");
  assert.equal(context.translations.de.capabilityInfoShow, "Sicherheit und Funktionen anzeigen");
  assert.equal(context.translations.de.capabilityInfoHide, "Sicherheit und Funktionen ausblenden");
});

test("renderCapabilities truthfully displays not_connected and planning_only without false claims", () => {
  const capabilityGrid = new MockElement("div");
  const items = [
    { capability_id: "documents.search", title: "Document search", surface_status: "interactive_read_only" },
    { capability_id: "documents.create", title: "Create documents", surface_status: "agent_guided" },
    { capability_id: "calendar.manage", title: "Calendar appointments", surface_status: "planning_only" },
    { capability_id: "finance.overview", title: "Finance overview", surface_status: "not_connected" },
  ];

  const transContext = vm.createContext({});
  const transBlock = appSource.slice(
    appSource.indexOf("const translations ="),
    appSource.indexOf("const capabilityTitles =")
  );
  vm.runInContext(transBlock.replace("const translations =", "var translations ="), transContext);

  for (const lang of ["en", "de"]) {
    const context = vm.createContext({
      capabilityGrid,
      capabilityItems: items,
      connectionStatus: "ready",
      language: lang,
      t: (key) => transContext.translations[lang][key] || key,
      textElement: (tag, text, cls) => {
        const el = new MockElement(tag);
        el.textContent = text;
        if (cls) el.className = cls;
        return el;
      },
      document: { createElement: (tag) => new MockElement(tag) },
    });

    const capTitlesMatch = appSource.match(/const capabilityTitles = \{[\s\S]*?\n\};/);
    const renderFn = appSource.match(/function renderCapabilities\(\) \{[\s\S]*?\n\}/);
    vm.runInContext(capTitlesMatch[0], context);
    vm.runInContext(renderFn[0], context);

    context.renderCapabilities();

    assert.equal(capabilityGrid.children.length, 4);

    // 0: interactive_read_only -> directUse ("Available here" / "Hier direkt nutzbar")
    const card0 = capabilityGrid.children[0];
    assert.equal(card0.dataset.status, "interactive_read_only");
    assert.equal(card0.children[1].textContent, lang === "en" ? "Available here" : "Hier direkt nutzbar");

    // 1: agent_guided -> agentUse (connected and ready through the agent)
    const card1 = capabilityGrid.children[1];
    assert.equal(card1.dataset.status, "agent_guided");
    assert.equal(card1.children[1].textContent, lang === "en" ? "Ready through the FolderHome agent" : "Über den FolderHome-Agenten bereit");

    // 2: planning_only -> planningOnly ("Planning only" / "Nur Planung")
    const card2 = capabilityGrid.children[2];
    assert.equal(card2.dataset.status, "planning_only");
    assert.equal(card2.children[1].textContent, lang === "en" ? "Planning only" : "Nur Planung");
    assert.notEqual(card2.children[1].textContent, "Available here");
    assert.notEqual(card2.children[1].textContent, "Through safe CLI workflows");
    assert.notEqual(card2.children[1].textContent, "Guided by the FolderHome agent");

    // 3: not_connected -> notConnected ("Not connected in this installation" / "In dieser Installation nicht verbunden")
    const card3 = capabilityGrid.children[3];
    assert.equal(card3.dataset.status, "not_connected");
    assert.equal(card3.children[1].textContent, lang === "en" ? "Not connected in this installation" : "In dieser Installation nicht verbunden");
    assert.notEqual(card3.children[1].textContent, "Available here");
    assert.notEqual(card3.children[1].textContent, "Through safe CLI workflows");
    assert.notEqual(card3.children[1].textContent, "Guided by the FolderHome agent");
  }
});
