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
      toggle: (c, force) => {
        const has = this.classList._classes.has(c);
        const next = force !== undefined ? Boolean(force) : !has;
        if (next) this.classList._classes.add(c);
        else this.classList._classes.delete(c);
        return next;
      },
      contains: c => this.classList._classes.has(c),
    };
    Object.defineProperty(this, "className", {
      get: () => [...this.classList._classes].join(" "),
      set: (val) => {
        this.classList._classes.clear();
        (val || "").split(/\s+/).filter(Boolean).forEach(c => this.classList._classes.add(c));
      },
    });
    this.hidden = false;
    this.value = "";
    this.textContent = "";
  }
  append(...items) {
    for (const item of items) {
      item.parent = this;
      item.parentNode = this;
      this.children.push(item);
    }
  }
  replaceChildren(...items) {
    this.children = [];
    this.append(...items);
  }
  insertBefore(newChild, refChild) {
    newChild.parent = this;
    newChild.parentNode = this;
    const idx = this.children.indexOf(refChild);
    if (idx >= 0) this.children.splice(idx, 0, newChild);
    else this.children.push(newChild);
    return newChild;
  }
  remove() {
    const p = this.parentNode || this.parent;
    if (p) {
      const idx = p.children.indexOf(this);
      if (idx >= 0) p.children.splice(idx, 1);
    }
  }
  closest(sel) {
    let curr = this;
    while (curr) {
      if (curr.classList && sel.startsWith(".") && curr.classList.contains(sel.slice(1))) return curr;
      if (curr.attributes && sel.startsWith("#") && curr.attributes.id === sel.slice(1)) return curr;
      if (curr.tag && curr.tag.toLowerCase() === sel.toLowerCase()) return curr;
      curr = curr.parentNode || curr.parent;
    }
    return null;
  }
  setAttribute(name, val) { this.attributes[name] = String(val); }
  getAttribute(name) { return this.attributes[name] !== undefined ? this.attributes[name] : null; }
  removeAttribute(name) { delete this.attributes[name]; }
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
      const classMatches = s.matchAll(/\.([a-zA-Z0-9_-]+)/g);
      for (const m of classMatches) {
        if (!node.classList || !node.classList.contains(m[1])) return false;
      }
      const attrMatches = s.matchAll(/\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]/g);
      for (const m of attrMatches) {
        const attrName = m[1];
        const attrVal = m[2];
        let val = node.attributes ? node.attributes[attrName] : undefined;
        if (val === undefined && attrName.startsWith("data-")) {
          const camel = attrName.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
          val = node.dataset ? node.dataset[camel] : undefined;
        }
        if (val === undefined || val === null) return false;
        if (attrVal !== undefined && String(val) !== String(attrVal)) return false;
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

function setupDOM() {
  const root = new MockElement("div");
  const storage = new Map();
  const sessionStorage = {
    getItem: k => storage.get(k) || null,
    setItem: (k, v) => storage.set(k, String(v)),
  };

  const makeCard = (id, title) => {
    const card = new MockElement("section");
    card.classList.add("card");
    card.dataset.cardId = id;

    const head = new MockElement("div");
    head.classList.add("card-head");

    const h2 = new MockElement("h2");
    h2.textContent = title;
    h2.setAttribute("aria-expanded", "true");
    head.append(h2);

    const chevron = new MockElement("span");
    chevron.classList.add("card-chevron");
    head.append(chevron);

    const body = new MockElement("div");
    body.classList.add("card-body");
    body.setAttribute("id", `card-body-${id}`);

    card.append(head, body);
    root.append(card);
    return card;
  };

  makeCard("profiles", "1. Profiles");
  const foldersCard = makeCard("folders", "2. Folders");
  const folderGrid = new MockElement("div");
  folderGrid.setAttribute("id", "folder-grid");
  const folderInput0 = new MockElement("input");
  folderInput0.value = "/path/to/my/docs";
  folderGrid.append(folderInput0);
  foldersCard.querySelector(".card-body").append(folderGrid);

  const modelCard = makeCard("model", "3. Model");
  const presetList = new MockElement("div");
  presetList.setAttribute("id", "preset-list");
  const presetRow = new MockElement("div");
  presetRow.classList.add("field-input");
  presetRow.dataset.presetName = "bedrock-nova-micro";
  presetList.append(presetRow);
  modelCard.querySelector(".card-body").append(presetList);

  const runtimeCard = makeCard("runtime", "6. Runtime");
  const portInput = new MockElement("input");
  portInput.setAttribute("id", "port");
  portInput.value = "8765";
  runtimeCard.querySelector(".card-body").append(portInput);

  const outsideHome = new MockElement("input");
  outsideHome.setAttribute("id", "outside-home");
  outsideHome.setAttribute("type", "checkbox");
  outsideHome.focus = () => { outsideHome._focused = true; };
  const checkboxLabel = new MockElement("label");
  checkboxLabel.classList.add("checkbox");
  checkboxLabel.append(outsideHome);
  runtimeCard.querySelector(".card-body").append(checkboxLabel);

  makeCard("calendar", "7. Calendar");
  const summaryCard = makeCard("summary", "9. Summary and save");
  const summary = new MockElement("div");
  summary.setAttribute("id", "summary");
  summaryCard.querySelector(".card-body").append(summary);

  const context = vm.createContext({
    document: {
      querySelectorAll: sel => root.querySelectorAll(sel),
      querySelector: sel => root.querySelector(sel),
      createElement: tag => new MockElement(tag),
    },
    folderGrid,
    presetList,
    summary,
    sessionStorage,
    saveButton: { disabled: false },
    checkedPlan: null,
    t: k => k,
    setTimeout: (fn, ms) => ({ fn, ms }),
  });

  const source = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
  const helperStart = source.indexOf("function getStoredCardState(");
  const helperEnd = source.indexOf("async function pickFolder(");
  vm.runInContext(source.slice(helperStart, helperEnd), context);

  return { context, root, sessionStorage };
}

test("setup card heading toggles aria-expanded and is-collapsed class on click", () => {
  const { context, root, sessionStorage } = setupDOM();
  context.initCollapsibleCards();

  const profilesCard = root.querySelector('[data-card-id="profiles"]');
  const h2 = profilesCard.querySelector("h2");
  const head = profilesCard.querySelector(".card-head");

  // Initial state: first card is highlighted as active but still starts collapsed
  assert.equal(h2.getAttribute("aria-expanded"), "false");
  assert.equal(profilesCard.classList.contains("is-collapsed"), true);
  assert.equal(profilesCard.classList.contains("is-active"), true);

  // Click card head to expand
  head.listeners.click();
  assert.equal(h2.getAttribute("aria-expanded"), "true");
  assert.equal(profilesCard.classList.contains("is-collapsed"), false);
  assert.equal(sessionStorage.getItem("fh_setup_card_profiles"), "true");

  // Click card head again to collapse
  head.listeners.click();
  assert.equal(h2.getAttribute("aria-expanded"), "false");
  assert.equal(profilesCard.classList.contains("is-collapsed"), true);
  assert.equal(sessionStorage.getItem("fh_setup_card_profiles"), "false");
});

test("setup card heading toggles on Enter or Space key", () => {
  const { context, root } = setupDOM();
  context.initCollapsibleCards();

  const foldersCard = root.querySelector('[data-card-id="folders"]');
  const h2 = foldersCard.querySelector("h2");
  const head = foldersCard.querySelector(".card-head");

  // Press Enter key to toggle
  head.listeners.keydown({ key: "Enter", preventDefault() {} });
  const stateAfterEnter = h2.getAttribute("aria-expanded");

  // Press Space key to toggle back
  head.listeners.keydown({ key: " ", preventDefault() {} });
  assert.notEqual(h2.getAttribute("aria-expanded"), stateAfterEnter);
});

test("validation error expands the corresponding card and sets has-error", () => {
  const { context, root } = setupDOM();
  context.initCollapsibleCards();

  const calendarCard = root.querySelector('[data-card-id="calendar"]');
  const h2 = calendarCard.querySelector("h2");

  // Initially calendar card is collapsed
  assert.equal(calendarCard.classList.contains("is-collapsed"), true);

  // Trigger error targeting calendar
  context.expandCardForError("calendar_id must not be primary");

  assert.equal(h2.getAttribute("aria-expanded"), "true");
  assert.equal(calendarCard.classList.contains("is-collapsed"), false);
  assert.equal(calendarCard.classList.contains("has-error"), true);
  assert.equal(calendarCard.classList.contains("is-active"), true);
});

test("outside-home error navigates to section 6, focuses outside-home checkbox, and highlights it", () => {
  const { context, root } = setupDOM();
  context.initCollapsibleCards();

  const runtimeCard = root.querySelector('[data-card-id="runtime"]');
  const h2 = runtimeCard.querySelector("h2");
  const outsideHome = root.querySelector("#outside-home");

  assert.equal(runtimeCard.classList.contains("is-collapsed"), true);
  assert.equal(h2.getAttribute("aria-expanded"), "false");

  context.jumpToError("folders[0]", "Ordner liegt außerhalb des eigenen Benutzerordners; bestätige das ausdrücklich (→ Bestätigung in Abschnitt 6).");

  assert.equal(runtimeCard.classList.contains("is-collapsed"), false);
  assert.equal(h2.getAttribute("aria-expanded"), "true");
  assert.equal(outsideHome._focused, true);
  const label = outsideHome.parent;
  assert.equal(label.classList.contains("is-highlight-target"), true);
});

test("button:disabled does not use cursor: wait and aria-busy provides progress state", () => {
  const css = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.css"), "utf8");

  // Verify button:disabled no longer has cursor: wait
  assert.equal(/button:disabled\s*\{[^}]*cursor:\s*wait/i.test(css), false);
  // Verify button:disabled uses not-allowed
  assert.equal(/button:disabled\s*\{[^}]*cursor:\s*not-allowed/i.test(css), true);
  // Verify button[aria-busy="true"] uses cursor: progress and inline spinner animation
  assert.equal(/button\[aria-busy="true"\]\s*\{[^}]*cursor:\s*progress/i.test(css), true);
  assert.equal(css.includes("button-spin"), true);
  // Verify .results[aria-busy] uses progress bar instead of border-color: var(--folder)
  assert.equal(/\.results\[aria-busy="true"\]\s*\{[^}]*border-color:\s*var\(--folder\)/i.test(css), false);
  assert.equal(css.includes("progress-bar-slide"), true);
});

test("pickFolder provides button aria-busy state and handles 409 already open gracefully", async () => {
  const { context } = setupDOM();
  const source = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
  const pickStart = source.indexOf("async function pickFolder(");
  const pickEnd = source.indexOf("function folderRow(");

  let invalidated = false;
  let shownError = null;
  let mockApiResolves = null;
  let mockApiRejects = null;

  context.invalidate = () => { invalidated = true; };
  context.showError = (err) => { shownError = err; };
  context.t = (k) => k;
  context.api = () => new Promise((resolve, reject) => {
    mockApiResolves = resolve;
    mockApiRejects = reject;
  });

  vm.runInContext(source.slice(pickStart, pickEnd), context);

  const input = new MockElement("input");
  input.value = "/initial/path";
  const button = new MockElement("button");
  button.textContent = "Choose folder";

  // 1. Start pickFolder - check immediate busy state
  const pickPromise = context.pickFolder(input, button);
  assert.equal(button.getAttribute("aria-busy"), "true");
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, "dialogOpening");

  // Complete api call successfully
  mockApiResolves({ path: "/new/chosen/folder" });
  await pickPromise;

  assert.equal(input.value, "/new/chosen/folder");
  assert.equal(invalidated, true);
  assert.equal(button.getAttribute("aria-busy"), null);
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, "Choose folder");

  // 2. Test 409 conflict: another dialog is already open
  const conflictPromise = context.pickFolder(input, button);
  assert.equal(button.getAttribute("aria-busy"), "true");
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, "dialogOpening");

  const err409 = new Error("Es ist bereits ein Verzeichnisdialog offen.");
  err409.status = 409;
  mockApiRejects(err409);
  await conflictPromise;

  assert.equal(shownError !== null, true);
  assert.equal(shownError.message, "dialogAlreadyOpen");
  assert.equal(button.getAttribute("aria-busy"), null);
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, "Choose folder");
});

test("error card can be collapsed after validation error and app.css lacks display: block !important", () => {
  const { context, root } = setupDOM();
  context.initCollapsibleCards();

  const calendarCard = root.querySelector('[data-card-id="calendar"]');
  const h2 = calendarCard.querySelector("h2");
  const head = calendarCard.querySelector(".card-head");

  // Trigger error targeting calendar
  context.expandCardForError("calendar_id must not be primary");
  assert.equal(calendarCard.classList.contains("has-error"), true);
  assert.equal(h2.getAttribute("aria-expanded"), "true");
  assert.equal(calendarCard.classList.contains("is-collapsed"), false);

  // User clicks card head to collapse the error card
  head.listeners.click();
  assert.equal(h2.getAttribute("aria-expanded"), "false");
  assert.equal(calendarCard.classList.contains("is-collapsed"), true);
  // Still has-error and retains badge
  assert.equal(calendarCard.classList.contains("has-error"), true);
  const badge = calendarCard.querySelector(".card-error-badge");
  assert.equal(badge !== null, true);

  // User clicks again to re-expand
  head.listeners.click();
  assert.equal(h2.getAttribute("aria-expanded"), "true");
  assert.equal(calendarCard.classList.contains("is-collapsed"), false);

  // Verify app.css does NOT force display: block !important on error cards
  const css = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.css"), "utf8");
  assert.equal(/\.card\.has-error\s+\.card-body\s*\{[^}]*display:\s*block\s*!important/i.test(css), false);
});

test("resolveElementForField maps field path to element and renderPlan adds error badges and aria-invalid", () => {
  const { context, root } = setupDOM();
  context.initCollapsibleCards();

  const source = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
  const textElStart = source.indexOf("function textElement(");
  const textElEnd = source.indexOf("async function api(");
  vm.runInContext(source.slice(textElStart, textElEnd), context);

  const planStart = source.indexOf("function renderPlan(");
  const planEnd = source.indexOf("async function check(");
  vm.runInContext(source.slice(planStart, planEnd), context);

  // 1. Test resolveElementForField mapping
  const presetEl = context.resolveElementForField("model_presets[bedrock-nova-micro]");
  assert.equal(presetEl !== null, true);
  assert.equal(presetEl.dataset.presetName, "bedrock-nova-micro");

  const portEl = context.resolveElementForField("port");
  assert.equal(portEl !== null, true);
  assert.equal(portEl.attributes.id, "port");

  const folderEl = context.resolveElementForField("folders[0]");
  assert.equal(folderEl !== null, true);
  assert.equal(folderEl.value, "/path/to/my/docs");

  // 2. Test renderPlan error processing
  const invalidPlan = {
    valid: false,
    errors: [
      { field: "port", message: "Invalid port number" },
      { field: "folders[0]", message: "Folder does not exist" },
      { field: "model_presets[bedrock-nova-micro]", message: "Region missing" },
    ],
  };

  context.renderPlan(invalidPlan);

  // Check field-level invalid attributes
  assert.equal(portEl.getAttribute("aria-invalid"), "true");
  assert.equal(portEl.classList.contains("is-invalid"), true);
  assert.equal(folderEl.getAttribute("aria-invalid"), "true");
  assert.equal(folderEl.classList.contains("is-invalid"), true);

  // Check card-level error badges
  const runtimeCard = root.querySelector('[data-card-id="runtime"]');
  const foldersCard = root.querySelector('[data-card-id="folders"]');
  const modelCard = root.querySelector('[data-card-id="model"]');

  assert.equal(runtimeCard.classList.contains("has-error"), true);
  assert.equal(runtimeCard.querySelector(".card-error-badge").textContent, "1");

  assert.equal(foldersCard.classList.contains("has-error"), true);
  assert.equal(foldersCard.querySelector(".card-error-badge").textContent, "1");

  assert.equal(modelCard.classList.contains("has-error"), true);
  assert.equal(modelCard.querySelector(".card-error-badge").textContent, "1");

  // 3. Test error clearing
  context.clearValidationErrors();
  assert.equal(runtimeCard.classList.contains("has-error"), false);
  assert.equal(runtimeCard.querySelector(".card-error-badge"), null);
  assert.equal(portEl.getAttribute("aria-invalid"), null);
  assert.equal(portEl.classList.contains("is-invalid"), false);
});
