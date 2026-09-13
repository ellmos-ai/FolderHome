const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const assert = require("node:assert/strict");
const { test } = require("node:test");

const html = readFileSync(join(__dirname, "../../src/folderhome/web_ui/index.html"), "utf8");
const css = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.css"), "utf8");
const appSource = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");

test("model status banner exists immediately above workspace tile in DOM order", () => {
  const bannerIdx = html.indexOf('id="model-status-banner"');
  const workspaceIdx = html.indexOf('class="workspace"');
  assert.ok(bannerIdx > -1, "model-status-banner must exist in HTML");
  assert.ok(workspaceIdx > -1, "workspace must exist in HTML");
  assert.ok(bannerIdx < workspaceIdx, "model-status-banner must appear before workspace in DOM order");
});

test("model status banner contains #model-status and #topology-badge", () => {
  const bannerMatch = html.match(/<section[^>]*id="model-status-banner"[\s\S]*?<\/section>/);
  assert.ok(bannerMatch, "model-status-banner element found");
  const bannerHtml = bannerMatch[0];

  assert.match(bannerHtml, /id="model-status"/, "banner must contain #model-status");
  assert.match(bannerHtml, /id="topology-badge"/, "banner must contain #topology-badge");
  assert.match(bannerHtml, /id="running-settings"/, "banner must contain #running-settings");
  assert.match(bannerHtml, /id="open-settings-btn"/, "banner must contain #open-settings-btn");
  assert.match(bannerHtml, /<svg class="model-banner-icon"/, "banner must contain inline SVG model icon");
});

test("model status banner retains existing live-region, IDs and data-state attributes", () => {
  assert.match(html, /id="model-status"[^>]*data-state="checking"/);
  assert.match(html, /id="model-status"[^>]*role="status"/);
  assert.match(html, /id="model-status"[^>]*aria-live="polite"/);
  assert.match(html, /id="model-status-title"/);
  assert.match(html, /id="model-status-detail"/);
  assert.match(html, /id="topology-badge"[^>]*data-topology="loopback_local"/);
});

test("model status banner has blue background gradient rules in app.css", () => {
  // Light-Mode #dbeafe -> #bfdbfe
  assert.match(css, /\.model-status-banner[\s\S]*?#dbeafe[\s\S]*?#bfdbfe/,
    "light mode blue gradient (#dbeafe -> #bfdbfe) required in app.css");
  // Dark-Mode #0f2a5a -> #1e40af
  assert.match(css, /\[data-theme="dark"\]\s+\.model-status-banner[\s\S]*?#0f2a5a[\s\S]*?#1e40af/,
    "dark mode blue gradient (#0f2a5a -> #1e40af) required in app.css");
});

test("model status accent color rules exist for fixture, configured_unverified, verified_in_process and error", () => {
  // Gray for fixture
  assert.match(css, /data-state="fixture_only"[\s\S]*?#94a3b8/, "gray accent for fixture state");
  // Yellow for configured_unverified / checking
  assert.match(css, /data-state="configured_unverified"[\s\S]*?#eab308/, "yellow accent for configured_unverified state");
  // Green for verified_in_process
  assert.match(css, /data-state="verified_in_process"[\s\S]*?#10b981/, "green accent for verified_in_process state");
  // Red for error / failed
  assert.match(css, /data-state="error"[\s\S]*?#ef4444/, "red accent for error state");
});

test("model status banner has responsive breakpoints down to 400px", () => {
  assert.match(css, /@media\s*\(\s*max-width:\s*850px\s*\)[\s\S]*?\.model-status-banner/,
    "850px breakpoint for banner");
  assert.match(css, /@media\s*\(\s*max-width:\s*560px\s*\)[\s\S]*?\.model-status-banner/,
    "560px breakpoint for banner");
  assert.match(css, /@media\s*\(\s*max-width:\s*400px\s*\)[\s\S]*?\.model-status-banner/,
    "400px breakpoint for banner");
});

test("model status banner data-i18n labels exist in app.js for en and de", () => {
  assert.match(appSource, /modelStatusBanner:\s*"Model status"/);
  assert.match(appSource, /modelStatusBanner:\s*"Modellstatus"/);
});
