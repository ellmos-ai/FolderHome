// Executes the real form functions against a small DOM boundary double.
// This is a logic regression test, not a browser/layout acceptance claim.
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.value = "";
  }
  append(...children) {
    for (const child of children) {
      child.parent = this;
      this.children.push(child);
      if (this.tag === "select" && this.children.length === 1) this.value = child.value;
    }
  }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
  addEventListener(event, callback) { this.listeners[event] = callback; }
  querySelectorAll(selector) {
    return this.children.flatMap(child => [
      ...((selector === "[data-calendar-field]" ? child.dataset.calendarField : child.tag === selector) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
}

function form() {
  const controls = new Map();
  const element = key => {
    if (!controls.has(key)) controls.set(key, new Element(key === "#calendar-backend" ? "select" : "div"));
    return controls.get(key);
  };
  const saved = {
    default_backend: "google", timezone: "UTC", ics_directory: "C:/calendar-output",
    accounts: [{ profile_id: "hanna", backend: "google", account_id: "hanna-google",
      display_name: "Hannas Kalender", provider_id: "google-calendar",
      provider_revision: "v3", calendar_id: "primary", credential_ref: "connector://google-calendar/hanna" }],
  };
  const context = vm.createContext({
    document: { createElement: tag => new Element(tag), querySelector: element },
    state: { profiles: [{profile_id: "lukas", display_name: "Lukas"}, {profile_id: "hanna", display_name: "Hanna"}],
      calendar_backends: ["folderhome_local", "google"], current_calendar: saved },
    calendarAccounts: element("#calendar-accounts"), calendarEnabled: element("#calendar-enabled"),
    calendarDirty: false, invalidate() {}, t: key => key,
    async pickFolder(input) { if (context.chosenPath) input.value = context.chosenPath; },
    textElement: tag => new Element(tag), showError(error) { throw error; },
  });
  const source = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
  vm.runInContext(source.slice(source.indexOf("function calendarAccountRow("), source.indexOf("// ------------------------------------------------------------------ profiles")), context);
  vm.runInContext(source.slice(source.indexOf('calendarEnabled.addEventListener("change"'), source.indexOf('document.querySelector("#ollama-host").addEventListener')), context);
  context.renderCalendar();
  return { context, saved, element };
}

test("unchanged reload omits the calendar write even while the section is visible", () => {
  const {context} = form();
  assert.equal(context.calendarEnabled.checked, true);
  assert.equal(context.buildCalendar(), null);
});

test("editing a calendar retains each existing account profile, backend and secret reference", () => {
  const {context, saved, element} = form();
  context.calendarDirty = true;
  element("#calendar-timezone").value = "Europe/Berlin";
  const request = JSON.parse(JSON.stringify(context.buildCalendar()));
  assert.deepEqual(request, {...saved, timezone: "Europe/Berlin"});
});

test("removing the last account is an explicit edit with an empty accounts list", () => {
  const {context} = form();
  context.calendarAccounts.querySelectorAll("button")[0].listeners.click();
  assert.equal(context.calendarDirty, true);
  assert.deepEqual(JSON.parse(JSON.stringify(context.buildCalendar().accounts)), []);
});

test("a successful state reload clears the old calendar write intent", () => {
  const {context} = form();
  context.calendarDirty = true;
  context.renderCalendar();
  assert.equal(context.buildCalendar(), null);
});

test("calendar field edits and account additions set write intent", () => {
  for (const event of ["input", "change"]) {
    const {context, element} = form();
    element("#calendar-fields").listeners[event]();
    assert.notEqual(context.buildCalendar(), null);
  }
  const {context, element} = form();
  element("#calendar-account-add").listeners.click();
  assert.equal(context.buildCalendar().accounts.length, 2);
});

test("folder picker cancellation preserves config and a chosen folder marks an edit", async () => {
  const {context, element} = form();
  await element("#calendar-directory-choose").listeners.click();
  assert.equal(context.buildCalendar(), null);
  context.chosenPath = "C:/different-folder";
  await element("#calendar-directory-choose").listeners.click();
  assert.equal(context.buildCalendar().ics_directory, "C:/different-folder");
});
