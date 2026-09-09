// Exercises real API/error/confirmation/render functions; not browser acceptance.
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");
const source = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");

function element(tag) {
  return {
    tag, textContent: "", children: [], disabled: false,
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute() {}, addEventListener() {},
  };
}
function text(node) {
  return [node.textContent, ...(node.children || []).map(text)].join(" ");
}
const result = {
  execution_id: "workflow_attempt_example", profile_id: "lukas", plan_id: "plan-one",
  workflow_id: "calendar-connectors", status: "uncertain", retry_safe: false,
  executed_at: "2026-09-09T10:00:00+02:00", artifacts: [], side_effects: [],
  possible_side_effects: ["external.calendar.write"],
  evidence: { schema: "folderhome.google-calendar-partial-evidence.v1",
    confirmed_event_references: [{ provider_id: "google-calendar", account_id: "synthetic",
      calendar_id: "test@example.invalid", provider_event_id: "fh-confirmed-one" }] },
};
const uncertain = { schema: "folderhome.local-api-error.v1", status: "uncertain",
  status_code: 409, execution_outcome_unknown: true, retry_safe: false,
  uncertain_results: [result], message: "UNTRUSTED-ERROR-TEXT" };

function view() {
  const messages = [], requests = [], content = element("section");
  const context = vm.createContext({
    Headers, token: "synthetic-session", encodeURIComponent,
    document: { createElement: element }, resultsSection: element("section"),
    resultsContent: content, profileSelect: { value: "lukas" }, planOutcomes: {}, resultsRequestVersion: 0,
    t: (key, values = {}) => key + JSON.stringify(values),
    appendChatMessage: (_role, message) => messages.push(message),
    renderCurrentView: () => {},
    fetch: async (path, options) => {
      requests.push({ path, options });
      return path.endsWith("/confirm")
        ? { ok: false, status: 409, json: async () => uncertain }
        : { ok: true, status: 200, json: async () => ({ results: [result] }) };
    },
  });
  vm.runInContext(source.slice(source.indexOf("class LocalRequestError"), source.indexOf("function initialLanguage")), context);
  for (const name of ["api", "textElement", "renderCalendarEditors", "renderCalendarVersions", "renderCalendarMutation", "renderUncertainResult", "renderResults", "loadResults", "confirmPlan", "recipeOutcomeText"]) {
    const pattern = new RegExp(`^(?:async )?function ${name}\\(`, "m");
    const match = pattern.exec(source);
    if (!match) continue;
    const rest = source.slice(match.index);
    const next = /\n(?:async )?function \w+\(/.exec(rest);
    vm.runInContext(next ? rest.slice(0, next.index) : rest, context);
  }
  return { context, messages, requests, content };
}
const plan = { plan_id: "plan-one", plan_sha256: "exact-plan-hash", profile_id: "lukas",
  steps: [{ step_id: "one" }] };

test("confirmed event versions are readable inert text for subsequent change planning", () => {
  const {context, content} = view();
  context.renderResults([{...result, status: "executed", evidence: {
    event_versions: [{schema: "folderhome.google-calendar-event-version.v1",
      provider_event_id: "fh-one", etag: '"v1"', event: {title: "<img src=x onerror=alert(1)>"}}],
  }}]);
  assert.match(text(content), /calendarEventVersions/);
  assert.match(text(content), /fh-one/);
  assert.match(text(content), /<img src=x onerror=alert\(1\)>/);
  function nodes(node) { return [node, ...node.children.flatMap(nodes)]; }
  assert.equal(nodes(content).some(node => node.tag === "img" || node.tag === "a"), false);
});

for (const operation of ["update", "delete"]) {
  for (const uncertainRun of [false, true]) {
    test(`calendar ${operation} receipt remains visible with uncertainty=${uncertainRun}`, () => {
      const {context, content} = view();
      context.renderResults([{...result, status: uncertainRun ? "uncertain" : "executed", evidence: {
        confirmed_mutation: {schema: "folderhome.google-calendar-mutation-result.v1",
          operation, status: operation === "update" ? "updated" : "absent",
          provider_event_id: "<img src=x onerror=alert(1)>"},
      }}]);
      assert.match(text(content), new RegExp(operation === "update" ? "calendarMutationUpdated" : "calendarMutationAbsent"));
      assert.match(text(content), /<img src=x onerror=alert\(1\)>/);
      if (uncertainRun) assert.match(text(content), /executionUncertain/);
      function nodes(node) { return [node, ...node.children.flatMap(nodes)]; }
      assert.equal(nodes(content).some(node => node.tag === "img" || node.tag === "a"), false);
    });
  }
}

test("409 confirmation retains uncertainty and renders confirmed references without retry", async () => {
  const { context, messages, requests, content } = view();
  const button = element("button");
  await context.confirmPlan(plan, button);
  assert.equal(context.planOutcomes[plan.plan_id].execution_outcome_unknown, true);
  assert.equal(button.disabled, true);
  assert.match(messages.join(" "), /executionUncertain/);
  assert.match(text(content), /fh-confirmed-one/);
  assert.match(text(content), /executionUncertain/);
  assert.doesNotMatch(text(content) + messages.join(" "), /UNTRUSTED-ERROR-TEXT|executionCompleted/);
  await context.confirmPlan(plan, element("button"));
  assert.equal(requests.filter(item => item.path.endsWith("/confirm")).length, 1);
});

test("uncertain result with no confirmed entries stays uncertain, not successful or empty", () => {
  const { context, content } = view();
  context.renderResults([{ ...result, evidence: { confirmed_event_references: [] } }]);
  assert.match(text(content), /executionUncertain/);
  assert.match(text(content), /confirmedCalendarEntries.*0/);
  assert.doesNotMatch(text(content), /executionCompleted|resultsEmpty/);
});

test("provider references are inert text, never HTML or executable links", () => {
  const { context, content } = view();
  context.renderResults([{ ...result, evidence: { confirmed_event_references: [{
    provider_event_id: "<img src=x onerror=alert(1)>", calendar_id: "javascript:alert(1)",
  }] } }]);
  assert.match(text(content), /<img src=x onerror=alert\(1\)>/);
  function nodes(node) { return [node, ...node.children.flatMap(nodes)]; }
  assert.equal(nodes(content).some(node => node.tag === "img" || node.tag === "a"), false);
});

test("a lost confirmation response prevents retry even without server evidence", async () => {
  const { context, messages } = view();
  let attempts = 0;
  context.fetch = async () => { attempts++; throw new TypeError("network lost"); };
  await context.confirmPlan(plan, element("button"));
  assert.equal(context.planOutcomes[plan.plan_id].execution_outcome_unknown, true);
  assert.match(messages.join(" "), /executionUncertain/);
  await context.confirmPlan(plan, element("button"));
  assert.equal(attempts, 1);
});

test("a late result read cannot populate the newly selected profile", async () => {
  const { context, content } = view();
  let resolve;
  context.fetch = () => new Promise(done => { resolve = done; });
  const pending = context.loadResults();
  context.profileSelect.value = "hanna";
  resolve({ ok: true, status: 200, json: async () => ({ results: [result] }) });
  await pending;
  assert.doesNotMatch(text(content), /fh-confirmed-one/);
});

test("A to B to A cannot let an older read replace a newer result", async () => {
  const { context, content } = view();
  const reads = [];
  context.fetch = () => new Promise(done => reads.push(done));
  const old = context.loadResults();
  context.profileSelect.value = "hanna";
  const other = context.loadResults();
  context.profileSelect.value = "lukas";
  const latest = context.loadResults();
  reads[2]({ ok: true, json: async () => ({ results: [result] }) });
  await latest;
  reads[1]({ ok: true, json: async () => ({ results: [] }) });
  reads[0]({ ok: true, json: async () => ({ results: [] }) });
  await Promise.all([old, other]);
  assert.match(text(content), /fh-confirmed-one/);
});

test("late confirmation keeps evidence for its plan but does not write into another profile's chat", async () => {
  const { context, messages } = view();
  let resolve;
  context.fetch = () => new Promise(done => { resolve = done; });
  const pending = context.confirmPlan(plan, element("button"));
  context.profileSelect.value = "hanna";
  resolve({ ok: false, status: 409, json: async () => uncertain });
  // A wrong implementation may start a list read; provide a terminal response too.
  await new Promise(done => setImmediate(done));
  resolve({ ok: true, status: 200, json: async () => ({ results: [] }) });
  await pending;
  assert.equal(context.planOutcomes[plan.plan_id].execution_outcome_unknown, true);
  assert.deepEqual(messages, []);
});

for (const lang of ["en", "de"]) {
  test(`calendar version references and mutation receipts are localized in ${lang}`, () => {
    const {context, content} = view();
    context.language = lang;
    vm.runInContext(source.slice(source.indexOf("const translations ="), source.indexOf("const capabilityTitles =")), context);
    vm.runInContext(source.slice(source.indexOf("function t("), source.indexOf("function setLanguage(")), context);
    context.renderResults([{...result, status: "executed", evidence: {
      confirmed_mutation: {schema: "folderhome.google-calendar-mutation-result.v1", operation: "update", status: "updated"},
      event_versions: [{schema: "folderhome.google-calendar-event-version.v1", etag: '"v2"'}],
    }}]);
    assert.doesNotMatch(text(content), /calendarEventVersions|calendarVersionCaution|calendarMutationUpdated|calendarMutationEvidence/);
    assert.match(text(content), lang === "de" ? /Folgeänderungen/ : /follow-up changes/);
    assert.match(text(content), lang === "de" ? /erneute Prüfung/ : /fresh check/);
  });
  test(`partial evidence is readable in ${lang} without fallback keys`, () => {
    const { context, content } = view();
    context.language = lang;
    vm.runInContext(source.slice(source.indexOf("const translations ="), source.indexOf("const capabilityTitles =")), context);
    vm.runInContext(source.slice(source.indexOf("function t("), source.indexOf("function setLanguage(")), context);
    context.renderResults([result]);
    assert.doesNotMatch(text(content), /executionUncertain|confirmedCalendarEntries|confirmedCalendarReferences/);
    assert.match(text(content), lang === "de" ? /Bestätigte.*1/ : /Confirmed.*1/);
    assert.match(text(content), lang === "de" ? /prüfen/ : /Check/);
  });
}
