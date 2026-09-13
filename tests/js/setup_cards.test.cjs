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
  makeCard("folders", "2. Folders");
  const runtimeCard = makeCard("runtime", "6. Runtime");
  const outsideHome = new MockElement("input");
  outsideHome.setAttribute("id", "outside-home");
  outsideHome.setAttribute("type", "checkbox");
  outsideHome.focus = () => { outsideHome._focused = true; };
  const checkboxLabel = new MockElement("label");
  checkboxLabel.classList.add("checkbox");
  checkboxLabel.append(outsideHome);
  outsideHome.closest = sel => sel === ".checkbox" ? checkboxLabel : null;
  runtimeCard.querySelector(".card-body").append(checkboxLabel);
  makeCard("calendar", "7. Calendar");
  makeCard("summary", "9. Summary and save");

  const context = vm.createContext({
    document: {
      querySelectorAll: sel => root.querySelectorAll(sel),
      querySelector: sel => root.querySelector(sel),
      createElement: tag => new MockElement(tag),
    },
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
