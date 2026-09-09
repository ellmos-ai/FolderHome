const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const {test} = require("node:test");
const source = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");
function element(tag) {
  return {tag, children: [], listeners: {}, textContent: "", value: "", checked: false,
    disabled: false, isConnected: true,
    append(...items) {this.children.push(...items);},
    addEventListener(name, callback) {this.listeners[name] = callback;},
    setAttribute() {},
  };
}
function nodes(node) {return [node, ...node.children.flatMap(nodes)];}
function text(node) {return nodes(node).map(item => item.textContent).join(" ");}
const item = {execution_id: "execution-one", profile_id: "lukas", status: "executed",
  evidence: {calendar_edit_context: {account_id: "private-account"}, event_versions: [{
    schema: "folderhome.google-calendar-event-version.v1", etag: '"v2"',
    event: {profile_id: "lukas", title: "Prüftermin", start: "2026-09-12T14:00:00+02:00",
      end: "2026-09-12T15:00:00+02:00", timezone: "Europe/Berlin", all_day: false, location: null, reminders: []},
  }]},
};
function view() {
  const calls = [], shown = [], card = element("article");
  const context = vm.createContext({document: {createElement: element},
    profileSelect: {value: "lukas"}, resultsRequestVersion: 1, language: "de",
    conversationRevision: 0, conversationResetPending: false,
    HTMLElement: class {}, actionButtons: [], planOutcomes: {},
    chatTranscript: {replaceChildren() {}}, appendChatMessage() {},
    renderCurrentView() {}, messageInput: {focus() {}}, currentView: null,
    resetRecipeControls() {}, renderRecipeSelection() {}, renderRecipeRuns() {},
    loadRecipes: async () => {}, loadRecipeRuns: async () => {}, showError() {},
    t: key => key, showAgent: value => shown.push(value),
    api: async (url, options) => {calls.push({url, body: JSON.parse(options.body)});
      return {plan: {profile_id: "lukas", summary: "review", steps: []}};},
  });
  for (const name of ["textElement", "renderCalendarEditors", "renderCalendarChangePreview", "resetConversation"]) {
    const match = new RegExp(`^(?:async )?function ${name}\\(`, "m").exec(source);
    if (!match) continue;
    const rest = source.slice(match.index), next = /\n(?:async )?function \w+\(/.exec(rest);
    vm.runInContext(next ? rest.slice(0, next.index) : rest, context);
  }
  return {context, card, calls, shown};
}

for (const operation of ["update", "delete"]) {
  test(`guided ${operation} posts only a reference and edits, never confirms automatically`, async () => {
    const {context, card, calls, shown} = view();
    context.renderCalendarEditors(card, item);
    const form = nodes(card).find(node => node.tag === "form");
    const title = nodes(card).find(node => node.name === "title");
    assert.equal(title.value, "Prüftermin");
    assert.equal(nodes(card).find(node => node.name === "end").required, true);
    title.value = "Anderer Termin";
    if (operation === "update") await form.listeners.submit({preventDefault() {}});
    else await nodes(card).find(node => node.textContent === "calendarPlanDelete").listeners.click();
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/api/v1/agent/calendar/plan");
    assert.equal(calls[0].body.execution_id, item.execution_id);
    assert.equal(calls[0].body.version_index, 0);
    assert.equal(calls[0].body.operation, operation);
    assert.equal(calls[0].body.changes.title, operation === "update" ? "Anderer Termin" : undefined);
    assert.equal(calls[0].body.expected_etag, undefined);
    assert.equal(calls[0].body.account_id, undefined);
    assert.equal(shown.length, 1);
  });
}

for (const change of ["profile", "generation", "edit", "detached"]) {
  test(`late editor plan is discarded after ${change}`, async () => {
    const {context, card, shown} = view();
    let resolve;
    context.api = () => new Promise(done => {resolve = done;});
    context.renderCalendarEditors(card, item);
    const form = nodes(card).find(node => node.tag === "form");
    const pending = form.listeners.submit({preventDefault() {}});
    if (change === "profile") context.profileSelect.value = "hanna";
    if (change === "generation") context.resultsRequestVersion += 2;
    if (change === "edit") form.listeners.input();
    if (change === "detached") form.isConnected = false;
    resolve({plan: {summary: "outdated", profile_id: "lukas"}});
    await pending;
    assert.equal(shown.length, 0);
  });
}

test("unknown or foreign results expose no editing control", () => {
  const {context, card} = view();
  context.renderCalendarEditors(card, {...item, status: "uncertain"});
  context.renderCalendarEditors(card, {...item, profile_id: "hanna"});
  assert.equal(nodes(card).some(node => node.tag === "form"), false);
});

test("mutation review exposes old and new values as text", () => {
  const {context, card} = view();
  context.renderCalendarChangePreview(card, {operation: "update",
    previous_event: item.evidence.event_versions[0].event,
    replacement: {...item.evidence.event_versions[0].event, title: "<img src=x>"},
  });
  assert.match(text(card), /Prüftermin/);
  assert.match(text(card), /<img src=x>/);
  assert.equal(nodes(card).some(node => node.tag === "img"), false);
});

test("popup reminders use the actual calendar contract", async () => {
  const {context, card, calls} = view();
  context.renderCalendarEditors(card, item);
  nodes(card).find(node => node.name === "reminders").value = "5, 30";
  await nodes(card).find(node => node.tag === "form").listeners.submit({preventDefault() {}});
  assert.deepEqual(calls[0].body.changes.reminders, [5, 30].map(minutes_before => ({
    schema: "folderhome.calendar-reminder.v1", method: "popup", minutes_before,
  })));
});

test("double submit creates only one preview request", async () => {
  const {context, card, shown} = view();
  let count = 0, resolve;
  context.api = () => {count++; return new Promise(done => {resolve = done;});};
  context.renderCalendarEditors(card, item);
  const form = nodes(card).find(node => node.tag === "form");
  const first = form.listeners.submit({preventDefault() {}});
  await form.listeners.submit({preventDefault() {}});
  await nodes(card).find(node => node.textContent === "calendarPlanDelete").listeners.click();
  assert.equal(count, 1);
  resolve({plan: {profile_id: "lukas", summary: "review"}});
  await first;
  assert.equal(shown.length, 1);
});

test("completed conversation reset discards an earlier delayed editor plan", async () => {
  const {context, card, shown} = view();
  let resolve;
  context.api = url => url.endsWith("/reset") ? Promise.resolve({}) : new Promise(done => {resolve = done;});
  context.renderCalendarEditors(card, item);
  const pending = nodes(card).find(node => node.tag === "form").listeners.submit({preventDefault() {}});
  await context.resetConversation();
  resolve({plan: {profile_id: "lukas", summary: "already discarded"}});
  await pending;
  assert.equal(shown.length, 0);
});

test("no editor preparation starts during a pending conversation reset", async () => {
  const {context, card, calls} = view();
  let finish;
  const api = context.api;
  context.api = (url, options) => url.endsWith("/reset") ? new Promise(done => {finish = done;}) : api(url, options);
  context.renderCalendarEditors(card, item);
  const pending = context.resetConversation();
  await nodes(card).find(node => node.tag === "form").listeners.submit({preventDefault() {}});
  finish({});
  await pending;
  assert.equal(calls.length, 0);
});

for (const language of ["en", "de"]) {
  test(`calendar form and review use translated labels in ${language}`, () => {
    const {context, card} = view();
    context.language = language;
    vm.runInContext(source.slice(source.indexOf("const translations ="), source.indexOf("const capabilityTitles =")), context);
    vm.runInContext(source.slice(source.indexOf("function t("), source.indexOf("function setLanguage(")), context);
    context.renderCalendarEditors(card, item);
    context.renderCalendarChangePreview(card, {operation: "delete", previous_event: item.evidence.event_versions[0].event, replacement: null});
    assert.doesNotMatch(text(card), /calendarEdit|calendarTitle|calendarPlanDelete|calendarBefore|calendarDateHelp/);
    assert.match(text(card), language === "de" ? /Löschung prüfen/ : /Review deletion/);
    assert.match(text(card), language === "de" ? /exklusiv/ : /exclusive/);
  });
}
