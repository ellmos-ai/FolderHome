const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");

const setupSource = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");
const webSource = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");

function languageFunctions(source, endMarker) {
  const start = source.indexOf("function browserLanguage()");
  const end = source.indexOf(endMarker, start);
  assert.ok(start >= 0 && end > start, "language initialization functions are present");
  return source.slice(start, end);
}

function contextFor(source, endMarker, { search = "", stored = null, languages = [], language = "" } = {}) {
  const values = new Map(stored === null ? [] : [["folderhome.language", stored]]);
  const localStorage = {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); },
  };
  const context = vm.createContext({
    URLSearchParams,
    window: { location: { search }, localStorage },
    navigator: { languages, language },
    supportedLanguages: ["en", "de"],
    queryParameters: new URLSearchParams(search),
  });
  vm.runInContext(languageFunctions(source, endMarker), context);
  return { context, values };
}

for (const [name, source, endMarker] of [
  ["setup", setupSource, "let language = initialLanguage();"],
  ["web", webSource, "function initialTheme()"],
]) {
  test(`${name} locale initialization keeps query, saved, and browser preference order`, () => {
    let result = contextFor(source, endMarker, {
      search: "?lang=en", stored: "de", languages: ["de-DE"], language: "de-DE",
    });
    assert.equal(result.context.initialLanguage(), "en");

    result = contextFor(source, endMarker, {
      search: "?lang=fr", stored: "de", languages: ["en-US"], language: "en-US",
    });
    assert.equal(result.context.initialLanguage(), "de");

    result = contextFor(source, endMarker, {
      search: "", languages: ["fr-CA", "de-DE"], language: "en-US",
    });
    assert.equal(result.context.initialLanguage(), "de");
  });

  test(`${name} locale initialization falls back when storage or preferences are unavailable`, () => {
    const result = contextFor(source, endMarker, { languages: ["fr-FR"], language: "de-AT" });
    assert.equal(result.context.initialLanguage(), "de");

    const noSupportedLanguage = contextFor(source, endMarker, {
      stored: "fr", languages: ["fr-FR"], language: "es-ES",
    });
    assert.equal(noSupportedLanguage.context.initialLanguage(), "en");

    Object.defineProperty(result.context.window, "localStorage", {
      configurable: true,
      get() { throw new Error("storage disabled"); },
    });
    assert.equal(result.context.initialLanguage(), "de");
  });
}

test("setup language switch persists when possible and still changes the current view when storage fails", () => {
  const { context, values } = contextFor(
    setupSource,
    "let language = initialLanguage();",
    { stored: "en" },
  );
  context.document = { documentElement: { lang: "en" } };
  context.renderCount = 0;
  vm.runInContext(
    "let language = initialLanguage(); function applyTranslations() { document.documentElement.lang = language; renderCount += 1; }",
    context,
  );

  vm.runInContext("setLanguage('de')", context);
  assert.equal(vm.runInContext("language", context), "de");
  assert.equal(values.get("folderhome.language"), "de");
  assert.equal(context.document.documentElement.lang, "de");
  assert.equal(context.renderCount, 1);

  Object.defineProperty(context.window, "localStorage", {
    configurable: true,
    get() { throw new Error("storage disabled"); },
  });
  vm.runInContext("setLanguage('en')", context);
  assert.equal(vm.runInContext("language", context), "en");
  assert.equal(context.document.documentElement.lang, "en");
  assert.equal(context.renderCount, 2);
  vm.runInContext("setLanguage('fr')", context);
  assert.equal(vm.runInContext("language", context), "en");
  assert.equal(context.renderCount, 2);
});
