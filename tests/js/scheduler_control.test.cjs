// Real UI control logic with a bounded DOM/network double, not browser acceptance.
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");

function view() {
  const elements = new Map();
  function element(key) {
    if (!elements.has(key)) elements.set(key, {
      value: "", textContent: "", disabled: false, hidden: false,
      listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; },
    });
    return elements.get(key);
  }
  const requests = [];
  const context = vm.createContext({
    document: { querySelector: element }, profileSelect: { value: "lukas" },
    t: (key, data = {}) => key + JSON.stringify(data), encodeURIComponent,
    api: async (path, options) => {
      requests.push({ path, payload: options?.body ? JSON.parse(options.body) : null });
      return context.response;
    },
  });
  const source = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");
  const start = source.indexOf("// Scheduler consumer controls");
  if (start >= 0) vm.runInContext(source.slice(start, source.indexOf("// End scheduler consumer controls", start)), context);
  assert.equal(typeof context.schedulerAction, "function", "visible consumer controls are required");
  context.renderSchedulerControl();
  return { context, element, requests };
}

const proposal = { profile_id: "lukas", plan_id: "consumer_start_abc", plan_sha256: "exact-hash",
  live_effect_approved: true, interval_minutes: 30, start_at: "2100-01-01T00:00:00Z",
  timezone: "UTC", watch_ids: ["watch_inbox"] };

test("initial view never starts work and disables confirmation", () => {
  const { element, requests } = view();
  assert.equal(requests.length, 0);
  assert.equal(element("#scheduler-start").disabled, true);
  assert.equal(element("#scheduler-stop").disabled, true);
});

test("preview alone cannot bypass the separate launch gate", async () => {
  const { context, element, requests } = view();
  context.response = { ...proposal, live_effect_approved: false };
  await context.schedulerAction("preview");
  assert.equal(element("#scheduler-start").disabled, true);
  await context.schedulerAction("start");
  assert.equal(requests.length, 1);
});

test("explicit start submits the exact preview once", async () => {
  const { context, element, requests } = view();
  context.response = proposal;
  await context.schedulerAction("preview");
  assert.equal(element("#scheduler-start").disabled, false);
  context.response = { profile_id: "lukas", status: "running", worker_id: "own-worker" };
  await context.schedulerAction("start");
  assert.deepEqual(requests[1].payload, {
    schema: "folderhome.scheduler-consumer-start-request.v1", profile_id: "lukas",
    plan_id: proposal.plan_id, plan_sha256: proposal.plan_sha256,
  });
  assert.equal(element("#scheduler-stop").disabled, false);
  await context.schedulerAction("start");
  assert.equal(requests.length, 2);
});

test("stop carries only the owned worker and displays draining honestly", async () => {
  const { context, element, requests } = view();
  context.response = { profile_id: "lukas", status: "running", worker_id: "own-worker" };
  await context.schedulerAction("status");
  context.response = { profile_id: "lukas", status: "stopping", worker_id: "own-worker" };
  await context.schedulerAction("stop");
  assert.equal(requests[1].payload.worker_id, "own-worker");
  assert.match(element("#scheduler-status").textContent, /schedulerState_stopping/);
  assert.equal(element("#scheduler-stop").disabled, true);
});

test("a stale response after changing profile cannot enable a start", async () => {
  const { context, element } = view();
  let resolve;
  context.api = () => new Promise(done => { resolve = done; });
  const pending = context.schedulerAction("preview");
  context.profileSelect.value = "hanna";
  context.resetSchedulerControl();
  resolve(proposal);
  await pending;
  assert.equal(element("#scheduler-start").disabled, true);
  assert.equal(element("#scheduler-preview-details").hidden, true);
});

test("uncertain start response invalidates approval and requests a status check", async () => {
  const { context, element } = view();
  context.response = proposal;
  await context.schedulerAction("preview");
  context.api = async () => { throw new Error("private response detail"); };
  await context.schedulerAction("start");
  assert.equal(element("#scheduler-start").disabled, true);
  assert.match(element("#scheduler-status").textContent, /schedulerControlError/);
  assert.doesNotMatch(element("#scheduler-status").textContent, /private response/);
});

test("an unconfigured service has a setup hint, not an uncertain-start warning", async () => {
  const { context, element } = view();
  context.api = async () => { throw Object.assign(new Error("unavailable"), { status: 503 }); };
  await context.schedulerAction("status");
  assert.match(element("#scheduler-status").textContent, /schedulerUnavailable/);
});

for (const pendingStatus of [false, true]) test(`returning to a profile reconciles late start (pending status: ${pendingStatus})`, async () => {
  const { context, element } = view();
  context.response = proposal;
  await context.schedulerAction("preview");
  let resolveStart;
  let resolveStatus;
  let statusReads = 0;
  context.api = (path) => {
    if (path.endsWith("/start")) return new Promise(done => { resolveStart = done; });
    statusReads++;
    if (pendingStatus && statusReads === 1) return new Promise(done => { resolveStatus = done; });
    return Promise.resolve({ profile_id: "lukas", worker_id: statusReads > 1 ? "own-worker" : null,
      status: statusReads > 1 ? "running" : "not_started_in_this_app" });
  };
  const pending = context.schedulerAction("start");
  context.profileSelect.value = "hanna";
  context.resetSchedulerControl();
  context.profileSelect.value = "lukas";
  context.resetSchedulerControl();
  const statusRequest = context.schedulerAction("status");
  if (!pendingStatus) await statusRequest;
  resolveStart({ profile_id: "lukas", status: "running", worker_id: "own-worker" });
  await pending;
  if (pendingStatus) {
    resolveStatus({ profile_id: "lukas", status: "not_started_in_this_app", worker_id: null });
    await statusRequest;
  }
  assert.equal(statusReads, 2);
  assert.equal(element("#scheduler-stop").disabled, false);
  assert.equal(element("#scheduler-start").disabled, true);
});

test("scheduler controls have complete matching English and German labels", () => {
  const source = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");
  const html = readFileSync(join(__dirname, "../../src/folderhome/web_ui/index.html"), "utf8");
  const context = vm.createContext({});
  vm.runInContext(source.slice(source.indexOf("const translations ="), source.indexOf("const profileSelect =")), context);
  const translations = vm.runInContext("translations", context);
  const keys = Object.keys(translations.en).filter(key => key.startsWith("scheduler"));
  assert.deepEqual(keys.sort(), Object.keys(translations.de).filter(key => key.startsWith("scheduler")).sort());
  for (const key of keys) {
    assert.ok(translations.en[key] && translations.de[key]);
    assert.doesNotMatch(translations.de[key], /\uFFFD/);
    assert.deepEqual((translations.en[key].match(/\{[^}]+\}/g) || []).sort(),
                     (translations.de[key].match(/\{[^}]+\}/g) || []).sort());
  }
  for (const match of html.matchAll(/data-i18n="(scheduler[^\"]+)"/g)) {
    assert.ok(translations.en[match[1]] && translations.de[match[1]]);
  }
  assert.match(translations.de.schedulerTitle, /ä|ö|ü/);
});
