// Real setup form logic; the small DOM double does not establish browser acceptance.
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");

function form() {
  const controls = new Map();
  function element(key) {
    if (!controls.has(key)) controls.set(key, {
      value: "", checked: false, hidden: false, disabled: false, children: [], listeners: {},
      append(child) { this.children.push(child); if (this.children.length === 1) this.value = child.value; },
      replaceChildren() { this.children = []; this.value = ""; },
      addEventListener(event, fn) { this.listeners[event] = fn; },
    });
    return controls.get(key);
  }
  const saved = {
    profile_id: "hanna", source_dir: "C:/source", target_dir: "C:/target", area: "insurance",
    interval_minutes: 45, start_at: "2026-09-10T08:00:00+02:00", timezone: "Europe/Berlin",
    recursive: false, allow_sensitive_local_read: true, confirm_outside_home: false,
  };
  const context = vm.createContext({
    document: { querySelector: element, createElement: () => ({ value: "", textContent: "" }) },
    state: { current_schedulers: { hanna: saved } },
    plannedProfiles: () => [{profile_id: "hanna", display_name: "Hanna"}, {profile_id: "lukas", display_name: "Lukas"}],
    t: key => key, invalidate() { context.invalidated = true; },
    async pickFolder(input) { if (context.chosenPath) input.value = context.chosenPath; },
    showError(error) { throw error; },
  });
  const source = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
  const start = source.indexOf("function buildScheduler(");
  if (start >= 0) vm.runInContext(source.slice(start, source.indexOf("// ------------------------------------------------------------------ profiles", start)), context);
  assert.equal(typeof context.renderScheduler, "function", "scheduler form must load saved configuration");
  context.renderScheduler();
  context.bindSchedulerEvents();
  return {context, saved, element};
}

test("reload shows stored scheduler fields but does not authorize a write", () => {
  const {context, element} = form();
  assert.equal(element("#scheduler-interval").value, 45);
  assert.equal(element("#scheduler-source").value, "C:/source");
  assert.equal(context.buildScheduler(), null);
});

test("explicit edit serializes the selected profile and all typed fields", () => {
  const {context, saved, element} = form();
  element("#scheduler-enabled").checked = true;
  element("#scheduler-enabled").listeners.change();
  element("#scheduler-interval").value = "60";
  element("#outside-home").checked = true;
  assert.deepEqual(JSON.parse(JSON.stringify(context.buildScheduler())), {
    ...saved, interval_minutes: 60, confirm_outside_home: true,
  });
  assert.equal(context.invalidated, true);
  context.renderScheduler();
  assert.equal(context.buildScheduler(), null);
});

test("changing profile resets the local-read grant and uses UTC for a new schedule", () => {
  const {context, element} = form();
  element("#scheduler-profile").value = "lukas";
  element("#scheduler-profile").listeners.change();
  element("#scheduler-enabled").checked = true;
  const request = context.buildScheduler();
  assert.equal(request.profile_id, "lukas");
  assert.equal(request.source_dir, "");
  assert.equal(request.allow_sensitive_local_read, false);
  assert.equal(request.timezone, "UTC");
  assert.match(request.start_at, /Z$/);
  assert.equal(request.interval_minutes, 30);
});

test("unreadable saved configuration cannot be silently replaced through the form", () => {
  const {context, element} = form();
  context.state.scheduler_load_error = "invalid stored data";
  context.renderScheduler();
  assert.equal(element("#scheduler-enabled").disabled, true);
  assert.equal(element("#scheduler-load-error").hidden, false);
  element("#scheduler-enabled").checked = true;
  assert.throws(() => context.buildScheduler(), /schedulerLoadError/);
});

test("folder selection updates only the selected field and invalidates an old preview", async () => {
  const {context, element} = form();
  await element("#scheduler-source-choose").listeners.click();
  assert.equal(element("#scheduler-source").value, "C:/source");
  context.chosenPath = "C:/new-source";
  await element("#scheduler-source-choose").listeners.click();
  assert.equal(element("#scheduler-source").value, "C:/new-source");
  assert.equal(element("#scheduler-target").value, "C:/target");
  assert.equal(context.invalidated, true);
});
