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

const html = readFileSync(join(__dirname, "../../src/folderhome/web_ui/index.html"), "utf8");
const appSource = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");

test("topology badge exists in shipped HTML in model status banner", () => {
  assert.match(html, /id="topology-badge"/);
  assert.match(html, /id="model-status-banner"[\s\S]*?id="topology-badge"/);
});

test("topology badge shows CLOUD when runtime_topology is cloud", () => {
  const badge = new MockElement("span");
  badge.setAttribute("id", "topology-badge");
  badge.dataset.topology = "loopback_local";
  badge.textContent = "LOCAL";

  const root = new MockElement("div");
  root.append(badge);

  const context = vm.createContext({
    document: {
      querySelector: sel => root.querySelector(sel),
      querySelectorAll: sel => root.querySelectorAll(sel),
    },
    appStatus: { runtime_topology: "cloud" },
    modelConnection: null,
  });

  const fnStart = appSource.indexOf("function renderTopologyBadge(");
  const fnEnd = appSource.indexOf("class LocalRequestError", fnStart);
  vm.runInContext(appSource.slice(fnStart, fnEnd), context);

  context.renderTopologyBadge();

  assert.match(badge.textContent, /CLOUD/);
  assert.equal(badge.dataset.topology, "cloud");
});

test("topology badge shows LOCAL for loopback_local and REMOTE for remote_host", () => {
  const badge = new MockElement("span");
  badge.setAttribute("id", "topology-badge");

  const root = new MockElement("div");
  root.append(badge);

  const context = vm.createContext({
    document: {
      querySelector: sel => root.querySelector(sel),
      querySelectorAll: sel => root.querySelectorAll(sel),
    },
    appStatus: { runtime_topology: "loopback_local" },
    modelConnection: null,
  });

  const fnStart = appSource.indexOf("function renderTopologyBadge(");
  const fnEnd = appSource.indexOf("class LocalRequestError", fnStart);
  vm.runInContext(appSource.slice(fnStart, fnEnd), context);

  context.renderTopologyBadge();
  assert.equal(badge.textContent, "LOCAL");
  assert.equal(badge.dataset.topology, "loopback_local");

  context.appStatus = { runtime_topology: "remote_host" };
  context.renderTopologyBadge();
  assert.equal(badge.textContent, "REMOTE");
  assert.equal(badge.dataset.topology, "remote_host");
});

test("collapsible panel toggles aria-expanded and is-collapsed on click and keydown", () => {
  const panel = new MockElement("section");
  panel.classList.add("collapsible-panel", "is-collapsed");

  const head = new MockElement("div");
  head.classList.add("panel-head");
  head.setAttribute("role", "button");
  head.setAttribute("tabindex", "0");
  head.setAttribute("aria-expanded", "false");

  const body = new MockElement("div");
  body.classList.add("panel-body");
  body.hidden = true;

  panel.append(head, body);
  const root = new MockElement("div");
  root.append(panel);

  const context = vm.createContext({
    document: {
      querySelector: sel => root.querySelector(sel),
      querySelectorAll: sel => root.querySelectorAll(sel),
    },
  });

  const setPanelStart = appSource.indexOf("function setPanelExpanded(");
  const initPanelEnd = appSource.indexOf("function renderModelStatus(", setPanelStart);
  vm.runInContext(appSource.slice(setPanelStart, initPanelEnd), context);

  context.initCollapsiblePanels();

  // Click to expand
  head.listeners.click({});
  assert.equal(head.getAttribute("aria-expanded"), "true");
  assert.equal(panel.classList.contains("is-collapsed"), false);
  assert.equal(body.hidden, false);

  // Keydown Enter to collapse
  head.listeners.keydown({ key: "Enter", preventDefault() {} });
  assert.equal(head.getAttribute("aria-expanded"), "false");
  assert.equal(panel.classList.contains("is-collapsed"), true);
  assert.equal(body.hidden, true);

  // Keydown Space to expand
  head.listeners.keydown({ key: " ", preventDefault() {} });
  assert.equal(head.getAttribute("aria-expanded"), "true");
  assert.equal(panel.classList.contains("is-collapsed"), false);
  assert.equal(body.hidden, false);
});
