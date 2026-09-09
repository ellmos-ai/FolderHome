// Real complete UI script with inert DOM/network fixtures; not browser acceptance.
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const {test} = require("node:test");
const source = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");
const html = readFileSync(join(__dirname, "../../src/folderhome/web_ui/index.html"), "utf8");

function view() {
  const elements = new Map(), calls = [];
  class Element {
    constructor(tag) {
      Object.assign(this, {tag, children: [], listeners: {}, textContent: "", value: "",
        disabled: false, hidden: false, dataset: {}, isConnected: true});
    }
    append(...items) {this.children.push(...items); if (this.tag === "select" && !this.value) this.value = items[0]?.value || "";}
    replaceChildren(...items) {this.children = []; this.append(...items);}
    addEventListener(name, callback) {this.listeners[name] = callback;}
    setAttribute(name, value) {this[name] = value;}
    scrollIntoView() {}
    focus() {}
  }
  const element = id => {
    if (!elements.has(id)) elements.set(id, new Element(id.endsWith("select") ? "select" : "div"));
    return elements.get(id);
  };
  const context = vm.createContext({
    URLSearchParams, Headers, HTMLElement: Element, console,
    window: {location: {search: "?token=test-session"}, localStorage: {getItem() {return null;}, setItem() {}}},
    document: {querySelector: element, querySelectorAll: () => [],
      createElement: tag => new Element(tag), documentElement: new Element("html")},
    fetch: async (url, options) => {
      calls.push({url, body: options.body ? JSON.parse(options.body) : null});
      return {ok: true, status: 200, json: async () => context.response || {profile_id: "lukas", runs: [], recipes: [], results: []}};
    },
  });
  vm.runInContext(source.slice(0, source.lastIndexOf("setLanguage(language, { persist: false });")), context);
  element("#profile-select").value = "lukas";
  return {context, element, calls};
}
function nodes(node) {return [node, ...node.children.flatMap(nodes)];}
function text(node) {return nodes(node).map(item => item.textContent).join(" ");}
const run = {run_id: "recipe_run_one", recipe_id: "journey", profile_id: "lukas", language: "en",
  status: "ready", completed_step_refs: ["source"], pending_plan_id: null, cleanup_pending_count: 0};
function proposal() {
  return {schema: "folderhome.recipe-stage-plan.v1", recipe_id: "journey",
    run: {...run, status: "awaiting_approval", pending_plan_id: "plan-one"},
    plan: {plan_id: "plan-one", plan_sha256: "exact-hash", profile_id: "lukas", summary: "Follow-up",
      confirmation_required: true, approval_context: {run_id: run.run_id, stage_number: 2,
        result_bindings: [{from_step: "source", to_step: "letter", source_path: ["name"],
          target_field: "recipient", value_type: "string", value: "<img src=x onerror=alert(1)>",
          source_execution_id: "workflow_execution_source"}]},
      steps: [{step_id: "step-two", workflow_id: "letter", goal: "Draft letter", confirmation_required: true,
        execution_envelope: {domain_plan: {recipient: "<img src=x onerror=alert(1)>"}}}]},
  };
}

test("run controls exist in shipped HTML with accessible headings and status", () => {
  assert.match(html, /id="recipe-runs-content"/);
  assert.match(html, /id="recipe-runs-title"/);
  assert.match(html, /id="refresh-recipe-runs"/);
});

test("run list renders confirmed progress and status, never executes", async () => {
  const {context, element, calls} = view();
  context.response = {profile_id: "lukas", runs: [run, {...run, run_id: "foreign", profile_id: "hanna"}]};
  await context.loadRecipeRuns();
  const content = element("#recipe-runs-content");
  assert.match(text(content), /source/);
  assert.match(text(content), /Prepare next section/);
  assert.doesNotMatch(text(content), /foreign/);
  assert.equal(calls.filter(call => call.body).length, 0);
});

test("next posts only run/profile, exposes bindings, and waits for separate exact approval", async () => {
  const {context, element, calls} = view();
  context.response = {profile_id: "lukas", runs: [run]};
  await context.loadRecipeRuns();
  context.response = proposal();
  await context.recipeRunAction("next", run.run_id);
  const posted = calls.filter(call => call.body);
  assert.deepEqual(posted.map(call => call.body), [{schema: "folderhome.local-recipe-next-request.v1", profile_id: "lukas", run_id: run.run_id}]);
  const content = element("#result-content");
  assert.match(text(content), /separate approval|this section/i);
  assert.match(text(content), /source/);
  assert.match(text(content), /letter.recipient/);
  assert.match(text(content), /<img src=x onerror=alert\(1\)>/);
  assert.equal(nodes(content).some(node => node.tag === "img" || node.tag === "a"), false);
  assert.doesNotMatch(text(content), /one confirmation covers all steps/);
  const button = nodes(content).find(node => node.tag === "button" && !node.disabled);
  assert.ok(button);
  context.response = {execution_performed: true, recipe_run: {...run, status: "completed"}, execution_reports: []};
  await context.confirmPlan(proposal().plan, button);
  const confirmation = calls.find(call => call.url.endsWith("/confirm"));
  assert.equal(confirmation.body.plan_sha256, "exact-hash");
  assert.deepEqual(confirmation.body.step_ids, ["step-two"]);
});

for (const status of ["completed", "aborted", "closed"]) {
  test(`${status} run does not offer or perform a next section`, async () => {
    const {context, element, calls} = view();
    context.response = {profile_id: "lukas", runs: [{...run, status}]};
    await context.loadRecipeRuns();
    await context.recipeRunAction("next", run.run_id);
    assert.equal(calls.filter(call => call.body).length, 0);
    assert.equal(nodes(element("#recipe-runs-content")).some(node => node.tag === "button" && /next section/i.test(node.textContent)), false);
  });
}

test("close consumes the pending visible plan, not earlier effects", async () => {
  const {context, element, calls} = view();
  context.response = {profile_id: "lukas", runs: [proposal().run]};
  await context.loadRecipeRuns();
  context.showAgent({agent: {response_text: "Review", proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}});
  context.response = {recipe_run: {...run, status: "closed"}};
  await context.recipeRunAction("close", run.run_id);
  assert.equal(calls.filter(call => call.body).length, 1);
  assert.equal(calls.find(call => call.body).url.endsWith("/close"), true);
  assert.equal(nodes(element("#result-content")).filter(node => node.tag === "button").every(node => node.disabled), true);
  assert.match(text(element("#result-content")), /closed|discarded/i);
});

test("double click produces only one next request", async () => {
  const {context} = view();
  context.response = {profile_id: "lukas", runs: [run]};
  await context.loadRecipeRuns();
  let resolve, posts = 0;
  context.fetch = async (url, options) => {
    if (options.body) {posts++; return new Promise(done => {resolve = done;});}
    return {ok: true, json: async () => ({profile_id: "lukas", runs: [run]})};
  };
  const first = context.recipeRunAction("next", run.run_id);
  await context.recipeRunAction("next", run.run_id);
  resolve({ok: true, json: async () => proposal()});
  await first;
  assert.equal(posts, 1);
});

for (const change of ["profile", "language", "reset", "profile-roundtrip"]) {
  test(`late next plan cannot revive after ${change}`, async () => {
    const {context, element} = view();
    context.response = {profile_id: "lukas", runs: [run]};
    await context.loadRecipeRuns();
    let resolve;
    context.fetch = async (url, options) => {
      if (url.endsWith("/next")) return new Promise(done => {resolve = done;});
      return {ok: true, json: async () => ({profile_id: element("#profile-select").value, runs: [], recipes: [], results: []})};
    };
    const pending = context.recipeRunAction("next", run.run_id);
    if (change.startsWith("profile")) {
      element("#profile-select").value = "hanna";
      element("#profile-select").listeners.change();
      if (change === "profile-roundtrip") {
        element("#profile-select").value = "lukas";
        element("#profile-select").listeners.change();
      }
    } else if (change === "language") context.setLanguage("de", {persist: false});
    else await context.resetConversation();
    resolve({ok: true, json: async () => proposal()});
    await pending;
    assert.doesNotMatch(text(element("#result-content")), /Follow-up|letter.recipient/);
  });
}

test("out-of-order run reads cannot replace a newer state", async () => {
  const {context, element} = view();
  const reads = [];
  context.fetch = () => new Promise(done => reads.push(done));
  const old = context.loadRecipeRuns(), latest = context.loadRecipeRuns();
  reads[1]({ok: true, json: async () => ({profile_id: "lukas", runs: [{...run, status: "completed"}]})});
  await latest;
  reads[0]({ok: true, json: async () => ({profile_id: "lukas", runs: [run]})});
  await old;
  assert.doesNotMatch(text(element("#recipe-runs-content")), /Prepare next section/);
});

test("failed action hides private errors and never retries a POST", async () => {
  const {context, element} = view();
  context.response = {profile_id: "lukas", runs: [run]};
  await context.loadRecipeRuns();
  let posts = 0;
  context.fetch = async (_url, options) => {
    if (options.body) {posts++; throw new Error("PRIVATE provider path");}
    return {ok: true, json: async () => ({profile_id: "lukas", runs: [proposal().run]})};
  };
  await context.recipeRunAction("next", run.run_id);
  assert.equal(posts, 1);
  assert.doesNotMatch(text(element("#recipe-runs-content")), /PRIVATE/);
  assert.match(text(element("#recipe-runs-content")), /not confirmed|Check.*status/i);
});

test("v2 aborted outcome names prior completed, failed, and untouched steps", () => {
  const {context} = view();
  const value = context.recipeOutcomeText({schema: "folderhome.recipe-stage-execution.v1", completed_step_refs: ["source"],
    outcomes: [{step_ref: "letter", status: "failed"}, {step_ref: "draft", status: "not_attempted"}]});
  assert.match(value, /source/); assert.match(value, /letter/); assert.match(value, /draft/);
});

test("pending close prevents a concurrent confirmation of the same section", async () => {
  const {context, element} = view();
  context.response = {profile_id: "lukas", runs: [proposal().run]};
  await context.loadRecipeRuns();
  context.showAgent({agent: {response_text: "Review", proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}});
  let finish, confirmations = 0;
  context.fetch = async (url) => {
    if (url.endsWith("/close")) return new Promise(done => {finish = done;});
    if (url.endsWith("/confirm")) confirmations++;
    return {ok: true, json: async () => ({profile_id: "lukas", runs: [], results: []})};
  };
  const closing = context.recipeRunAction("close", run.run_id);
  const buttons = nodes(element("#result-content")).filter(node => node.tag === "button");
  await context.confirmPlan(proposal().plan, buttons[0]);
  const wasDisabled = buttons.every(node => node.disabled);
  finish({ok: true, json: async () => ({recipe_run: {...run, status: "closed"}})});
  await closing;
  assert.equal(confirmations, 0);
  assert.equal(wasDisabled, true);
});

test("pending confirmation prevents close or next from racing it", async () => {
  const {context, element} = view();
  context.response = {profile_id: "lukas", runs: [proposal().run]};
  await context.loadRecipeRuns();
  context.showAgent({agent: {response_text: "Review", proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}});
  let finish, mutations = 0;
  context.fetch = async (url, options) => {
    if (url.endsWith("/confirm")) return new Promise(done => {finish = done;});
    if (options.body) mutations++;
    return {ok: true, json: async () => ({profile_id: "lukas", runs: [], results: []})};
  };
  const confirming = context.confirmPlan(proposal().plan, nodes(element("#result-content")).find(node => node.tag === "button"));
  await context.recipeRunAction("close", run.run_id);
  await context.recipeRunAction("next", run.run_id);
  finish({ok: true, json: async () => ({execution_performed: true, execution_reports: [], recipe_run: {...run, status: "completed"}})});
  await confirming;
  assert.equal(mutations, 0);
});

test("v2 selector prepares only the first section and blocks double submit", async () => {
  const {context, element} = view();
  context.response = {recipes: [{recipe_id: "journey", title: "Journey", summary: "Two sections", available: true, approval_mode: "per_section"}]};
  await context.loadRecipes();
  assert.match(element("#prepare-recipe").textContent, /first section/i);
  assert.match(element("#recipe-hint").textContent, /separate approval/);
  let finish, posts = 0;
  context.fetch = async (url, options) => {
    if (options.body) {posts++; return new Promise(done => {finish = done;});}
    return {ok: true, json: async () => ({profile_id: "lukas", runs: []})};
  };
  const preparing = context.prepareRecipe({preventDefault() {}});
  await context.prepareRecipe({preventDefault() {}});
  finish({ok: true, json: async () => proposal()});
  await preparing;
  assert.equal(posts, 1);
});

test("English and German recipe labels have exact parity and real umlauts", () => {
  const {context} = view();
  const translations = vm.runInContext("translations", context);
  const keys = Object.keys(translations.en).filter(key => key.startsWith("recipe"));
  assert.deepEqual(keys.sort(), Object.keys(translations.de).filter(key => key.startsWith("recipe")).sort());
  assert.equal(keys.every(key => translations.de[key] && translations.en[key]), true);
  assert.match(translations.de.recipeNext, /Nächsten/);
  assert.match(translations.de.recipeClose, /schließen/);
  assert.equal(JSON.stringify(translations).includes("\ufffd"), false);
});

test("close invalidates a newer visible plan even when the last run snapshot has no plan ID", async () => {
  const {context, element} = view();
  context.response = {profile_id: "lukas", runs: [run]};
  await context.loadRecipeRuns();
  context.showAgent({agent: {response_text: "Review", proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}});
  context.fetch = async (url) => ({ok: true, json: async () => url.endsWith("/close")
    ? {recipe_run: {...run, status: "closed"}} : {profile_id: "lukas", runs: []}});
  await context.recipeRunAction("close", run.run_id);
  assert.equal(nodes(element("#result-content")).filter(node => node.tag === "button").every(node => node.disabled), true);
});

test("late close after A to B to A refreshes current state without restoring old preview", async () => {
  const {context, element} = view();
  context.response = {profile_id: "lukas", runs: [proposal().run]};
  await context.loadRecipeRuns();
  let finish, closed = false, freshReads = 0;
  context.fetch = async (url) => {
    if (url.endsWith("/close")) return new Promise(done => {finish = done;});
    if (url.includes("/recipes/runs") && closed) freshReads++;
    return {ok: true, json: async () => ({profile_id: element("#profile-select").value,
      runs: closed ? [] : [proposal().run], recipes: [], results: []})};
  };
  const pending = context.recipeRunAction("close", run.run_id);
  element("#profile-select").value = "hanna";
  element("#profile-select").listeners.change();
  element("#profile-select").value = "lukas";
  element("#profile-select").listeners.change();
  await context.loadRecipeRuns();
  assert.match(text(element("#recipe-runs-content")), /Waiting/);
  closed = true;
  finish({ok: true, json: async () => ({recipe_run: {...run, status: "closed"}})});
  await pending;
  assert.ok(freshReads >= 1);
  assert.doesNotMatch(text(element("#recipe-runs-content")), /Waiting/);
  assert.doesNotMatch(text(element("#result-content")), /Follow-up/);
});

test("fresh run status invalidates an open preview removed on the server", async () => {
  const {context, element} = view();
  context.showAgent({agent: {response_text: "Review", proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}});
  context.response = {profile_id: "lukas", runs: []};
  await context.loadRecipeRuns();
  assert.equal(nodes(element("#result-content")).filter(node => node.tag === "button").every(node => node.disabled), true);
});

test("uncertain stage still displays actual failed and untouched steps plus incomplete delivery", async () => {
  const {context, element} = view();
  context.showAgent({agent: {response_text: "Review", proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}});
  context.response = {execution_outcome_unknown: true, retry_safe: false, result_delivery_incomplete: true,
    recipe_run: {...run, status: "aborted"}, recipe_execution: {status: "aborted", completed_step_refs: ["source"],
      outcomes: [{step_ref: "failed-letter", status: "failed"}, {step_ref: "untouched-draft", status: "not_attempted"}]},
    uncertain_results: [], execution_reports: []};
  await context.confirmPlan(proposal().plan, nodes(element("#result-content")).find(node => node.tag === "button"));
  const visible = text(element("#result-content"));
  assert.match(visible, /failed-letter/); assert.match(visible, /untouched-draft/);
  assert.match(visible, /result.*incomplete|incomplete.*result/i);
});

test("late recipe proposal from chat is discarded after language change and loading ends", async () => {
  const {context, element} = view();
  element("#message").value = "Prepare my journey";
  let finish;
  context.fetch = async (url) => {
    if (url.endsWith("/chat")) return new Promise(done => {finish = done;});
    return {ok: true, json: async () => ({profile_id: "lukas", runs: [], recipes: [], results: []})};
  };
  const pending = context.runAgent();
  context.setLanguage("de", {persist: false});
  finish({ok: true, json: async () => ({agent: {response_text: "OLD-LANGUAGE-REPLY",
    proposed_plans: [proposal().plan], proposed_recipes: [proposal()]}})});
  await pending;
  assert.doesNotMatch(text(element("#result-content")), /Follow-up/);
  assert.doesNotMatch(text(element("#chat-transcript")), /OLD-LANGUAGE-REPLY/);
  assert.equal(element("#result-section").hidden, true);
});
