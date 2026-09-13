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
      ...((selector === "[data-calendar-field]" ? child.dataset.calendarField :
          selector === "[data-google-field]" ? child.dataset.googleField : child.tag === selector) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
}

function form({readEnabled = false, lookup} = {}) {
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
      calendar_backends: ["folderhome_local", "google"], current_calendar: saved,
      google_calendar_read_enabled: readEnabled },
    calendarAccounts: element("#calendar-accounts"), calendarEnabled: element("#calendar-enabled"),
    calendarDirty: false, invalidate() {}, t: key => key,
    async pickFolder(input) { if (context.chosenPath) input.value = context.chosenPath; },
    textElement: (tag, value) => { const el = new Element(tag); if (value !== undefined) el.textContent = value; return el; }, showError(error) { throw error; },
    api: lookup || (async () => { throw new Error("Unexpected network request"); }),
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
  context.calendarAccounts.querySelectorAll("button")
    .find(control => control.dataset.i18n === "removeSource").listeners.click();
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

test("private Google paths enter the setup request only with their separate binding checkbox", () => {
  const {context} = form();
  const fields = Object.fromEntries(context.calendarAccounts.querySelectorAll("[data-google-field]")
    .map(control => [control.dataset.googleField, control]));
  assert.ok(fields.credential_file && fields.ledger_dir && fields.bind_private_resources);
  fields.credential_file.value = "C:/private/oauth.json";
  fields.ledger_dir.value = "C:/private/receipts";
  context.calendarDirty = true;
  assert.equal(context.buildCalendar().accounts[0].credential_file, undefined);
  fields.bind_private_resources.checked = true;
  const account = context.buildCalendar().accounts[0];
  assert.equal(account.bind_private_resources, true);
  assert.equal(account.credential_file, "C:/private/oauth.json");
  assert.equal(account.ledger_dir, "C:/private/receipts");
  context.renderCalendar();
  context.calendarDirty = true;
  assert.equal(context.buildCalendar().accounts[0].bind_private_resources, undefined);
});

test("calendar lookup is disabled unless the setup start allowed metadata reads", () => {
  const {context} = form();
  const button = context.calendarAccounts.querySelectorAll("button")
    .find(control => control.dataset.action === "google-lookup");
  assert.ok(button);
  assert.equal(button.disabled, true);
});

test("an explicit calendar lookup updates only the form and does not grant private binding", async () => {
  const calls = [];
  const {context} = form({readEnabled: true, lookup: async (path, options) => {
    calls.push({path, body: JSON.parse(options.body)});
    return {schema: "folderhome.google-calendar-identity.v1", requested_calendar_id: "primary",
      calendar_id: "resolved@example.invalid", provider_id: "google-calendar", provider_revision: "v3", read_only: true};
  }});
  const privateFields = context.calendarAccounts.querySelectorAll("[data-google-field]");
  privateFields.find(control => control.dataset.googleField === "credential_file").value = "C:/private/oauth.json";
  const button = context.calendarAccounts.querySelectorAll("button")
    .find(control => control.dataset.action === "google-lookup");
  assert.ok(button);
  assert.deepEqual(calls, []);
  await button.listeners.click();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, "/api/v1/setup/google-calendar-id");
  assert.equal(calls[0].body.confirm, true);
  assert.equal(calls[0].body.profile_id, "hanna");
  assert.equal(context.buildCalendar().accounts[0].calendar_id, "resolved@example.invalid");
  assert.equal(context.buildCalendar().accounts[0].bind_private_resources, undefined);
});

test("changed account fields discard a late calendar lookup response and double clicks do not duplicate reads", async () => {
  let finish;
  let calls = 0;
  const {context} = form({readEnabled: true, lookup: () => {
    calls += 1;
    return new Promise(resolve => {finish = resolve;});
  }});
  const button = context.calendarAccounts.querySelectorAll("button")
    .find(control => control.dataset.action === "google-lookup");
  assert.ok(button);
  const pending = button.listeners.click();
  await button.listeners.click();
  const id = context.calendarAccounts.querySelectorAll("[data-calendar-field]")
    .find(control => control.dataset.calendarField === "calendar_id");
  id.value = "manually-edited@example.invalid";
  finish({schema: "folderhome.google-calendar-identity.v1", requested_calendar_id: "primary",
    calendar_id: "stale@example.invalid", provider_id: "google-calendar", provider_revision: "v3", read_only: true});
  await pending;
  assert.equal(id.value, "manually-edited@example.invalid");
  assert.equal(calls, 1);
});

test("a rerender discards lookup responses even when the new fields have identical values", async () => {
  let finish;
  const {context} = form({readEnabled: true, lookup: () => new Promise(resolve => {finish = resolve;})});
  const button = context.calendarAccounts.querySelectorAll("button")
    .find(control => control.dataset.action === "google-lookup");
  const pending = button.listeners.click();
  context.renderCalendar();
  finish({schema: "folderhome.google-calendar-identity.v1", requested_calendar_id: "primary",
    calendar_id: "stale@example.invalid", provider_id: "google-calendar", provider_revision: "v3", read_only: true});
  await pending;
  assert.equal(context.calendarAccounts.querySelectorAll("[data-calendar-field]")
    .find(control => control.dataset.calendarField === "calendar_id").value, "primary");
  assert.equal(context.buildCalendar(), null);
});

for (const mutation of [
  {read_only: false}, {calendar_id: "primary"}, {calendar_id: "bad\nvalue"},
  {requested_calendar_id: "another@example.invalid"}, {provider_revision: "v4"},
  {schema: "unknown"},
]) {
  test(`invalid lookup response does not mutate the form: ${JSON.stringify(mutation)}`, async () => {
    const errors = [];
    const {context} = form({readEnabled: true, lookup: async () => ({
      schema: "folderhome.google-calendar-identity.v1", requested_calendar_id: "primary",
      calendar_id: "resolved@example.invalid", provider_id: "google-calendar", provider_revision: "v3", read_only: true,
      ...mutation,
    })});
    context.showError = error => errors.push(error.message);
    const button = context.calendarAccounts.querySelectorAll("button")
      .find(control => control.dataset.action === "google-lookup");
    await button.listeners.click();
    assert.deepEqual(errors, ["googleLookupFailed"]);
    assert.equal(context.buildCalendar(), null);
    assert.equal(button.disabled, false);
  });
}

test("checkbox line is a flex row with label to the right of the box", () => {
  const {context} = form();
  const input = {type: "checkbox", tag: "input"};
  const row = context.labelled("Bind resources", input);
  assert.equal(row.className, "checkbox");
  assert.equal(row.children[0], input);
  assert.equal(row.children[1].tag, "span");
  assert.equal(row.children[1].textContent, "Bind resources");
});
