const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const assert = require("node:assert/strict");
const { test } = require("node:test");

const html = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/index.html"), "utf8");
const app = readFileSync(join(__dirname, "../../src/folderhome/setup_ui/app.js"), "utf8");

test("setup exposes the pseudonymization default without calling it anonymity", () => {
  assert.match(html, /id="cloud-pseudonymization"[^>]*type="checkbox"[^>]*checked/);
  assert.match(app, /cloud_pseudonymization:\s*cloudPseudonymization\.checked \? "on" : "off"/);
  assert.match(app, /cloudPseudonymization\.checked = payload\.cloud_pseudonymization !== "off"/);
  assert.match(app, /Remote-Modellverkehr pseudonymisieren \(empfohlen\)/);
  assert.match(app, /ist aber keine Anonymität/);
});
