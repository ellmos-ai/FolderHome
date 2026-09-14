const { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } = require("node:fs");
const { join } = require("node:path");
const { tmpdir } = require("node:os");
const { spawnSync } = require("node:child_process");
const assert = require("node:assert/strict");
const { test, describe, beforeEach, afterEach } = require("node:test");

const pythonBin = process.env.PYTHON || "python";
const repoRoot = join(__dirname, "../..");
const startCmdPath = join(repoRoot, "scripts/START.cmd");
const startMenuScript = join(repoRoot, "scripts/start_menu.py");

function createTempDir(prefix) {
  const dir = join(tmpdir(), `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  mkdirSync(dir, { recursive: true });
  return dir;
}

function runMenu(args, options = {}) {
  return spawnSync(pythonBin, [startMenuScript, ...args], {
    encoding: "utf8",
    timeout: options.timeout || 10000,
    ...options,
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
      ...(options.env || {}),
    },
  });
}

// ============================================================================
// 1. Pure ASCII Verification for START.cmd
// ============================================================================

test("scripts/START.cmd exists and is strictly pure ASCII", () => {
  assert.ok(existsSync(startCmdPath), "scripts/START.cmd must exist");

  const rawBuffer = readFileSync(startCmdPath);
  assert.ok(rawBuffer.length > 0, "scripts/START.cmd must not be empty");

  const nonAscii = [];
  for (let i = 0; i < rawBuffer.length; i++) {
    if (rawBuffer[i] >= 128) {
      nonAscii.push({ index: i, byte: rawBuffer[i] });
    }
  }
  assert.deepEqual(nonAscii, [], "START.cmd must not contain non-ASCII bytes");

  const text = rawBuffer.toString("ascii");
  assert.match(text, /^[\r\n\t\x20-\x7E]*$/, "Content must match printable ASCII and whitespace");
  assert.match(text, /@echo off/i, "START.cmd must contain @echo off");
  assert.match(text, /start_menu\.py/i, "START.cmd must invoke start_menu.py");
});

// ============================================================================
// 2. Menu Options 1, 2, 3, 4, quit & Choice Normalization
// ============================================================================

describe("Menu options and choice normalization", () => {
  let tmp;

  beforeEach(() => {
    tmp = createTempDir("fh-js-test-options");
  });

  afterEach(() => {
    rmSync(tmp, { recursive: true, force: true });
  });

  test("option 1 (FolderHome) supports numeric '1' and alias names", () => {
    writeFileSync(join(tmp, "START-APP.cmd"), "@echo off\r\n", "ascii");

    for (const choice of ["1", "folderhome", "FolderHome", "app", "folder-home"]) {
      const res = runMenu(["--config-dir", tmp, "--dry-run", "--action", choice]);
      assert.equal(res.status, 0, `Choice '${choice}' failed with status ${res.status}`);
      assert.match(res.stdout, /Starting FolderHome\.\.\./);
      assert.match(res.stdout, /\[Dry-run Command\] .*START-APP\.cmd --json/);
      assert.doesNotMatch(res.stdout, /http:\/\/127\.0\.0\.1/);
      assert.match(res.stdout, /\[Dry-run\] Operation completed without launching subprocesses\./);
    }
  });

  test("option 2 (Setup) supports numeric '2' and alias names", () => {
    writeFileSync(join(tmp, "START-SETUP.cmd"), "@echo off\r\n", "ascii");

    for (const choice of ["2", "setup", "Setup", "einrichtung"]) {
      const res = runMenu(["--config-dir", tmp, "--dry-run", "--action", choice]);
      assert.equal(res.status, 0, `Choice '${choice}' failed with status ${res.status}`);
      assert.match(res.stdout, /Starting Setup\.\.\./);
      assert.match(res.stdout, /\[Dry-run Command\] .*START-SETUP\.cmd --config-dir .* --json/);
      assert.doesNotMatch(res.stdout, /http:\/\/127\.0\.0\.1/);
    }
  });

  test("option 3 (both) supports numeric '3' and alias names", () => {
    writeFileSync(join(tmp, "START-APP.cmd"), "@echo off\r\n", "ascii");
    writeFileSync(join(tmp, "START-SETUP.cmd"), "@echo off\r\n", "ascii");

    for (const choice of ["3", "both", "Both", "beides"]) {
      const res = runMenu(["--config-dir", tmp, "--dry-run", "--action", choice]);
      assert.equal(res.status, 0, `Choice '${choice}' failed with status ${res.status}`);
      assert.match(res.stdout, /Starting FolderHome\.\.\./);
      assert.match(res.stdout, /Starting Setup\.\.\./);
      assert.match(res.stdout, /\[Dry-run Command\] .*START-APP\.cmd --json/);
      assert.match(res.stdout, /\[Dry-run Command\] .*START-SETUP\.cmd --config-dir .* --json/);
      assert.doesNotMatch(res.stdout, /http:\/\/127\.0\.0\.1/);
    }
  });

  test("option 4 (language) and option q (quit) choices", () => {
    // Quit aliases in default English
    for (const quitChoice of ["q", "quit", "Quit", "exit", "beenden"]) {
      const res = runMenu(["--config-dir", tmp, "--action", quitChoice]);
      assert.equal(res.status, 0, `Quit choice '${quitChoice}' failed`);
      assert.match(res.stdout, /Exiting starter menu\./);
    }

    // Invalid choice returns exit code 1 with English error message
    const resInvalidEn = runMenu(["--config-dir", tmp, "--action", "invalid_choice_xyz"]);
    assert.equal(resInvalidEn.status, 1);
    assert.match(resInvalidEn.stdout, /Unknown option 'invalid_choice_xyz'/);

    // Action 4 piped input: choose Deutsch (2)
    const resLang = runMenu(["--config-dir", tmp, "--action", "4"], {
      input: "2\n",
    });
    assert.equal(resLang.status, 0);
    assert.match(resLang.stdout, /Sprache auf Deutsch gesetzt\./);

    // Invalid choice now returns exit code 1 with German error message
    const resInvalidDe = runMenu(["--config-dir", tmp, "--action", "invalid_choice_xyz"]);
    assert.equal(resInvalidDe.status, 1);
    assert.match(resInvalidDe.stdout, /Unbekannte Option 'invalid_choice_xyz'/);
  });

  test("missing wrappers on option 1, 2, 3 return non-zero exit status 1", () => {
    // Missing START-APP.cmd on option 1
    const res1 = runMenu(["--config-dir", tmp, "--action", "1"]);
    assert.equal(res1.status, 1);
    assert.match(res1.stdout, /START-APP\.cmd was not found/);

    // Missing START-SETUP.cmd on option 2
    const res2 = runMenu(["--config-dir", tmp, "--action", "2"]);
    assert.equal(res2.status, 1);
    assert.match(res2.stdout, /START-SETUP\.cmd was not found/);

    // Missing wrappers on option 3
    const res3 = runMenu(["--config-dir", tmp, "--action", "3"]);
    assert.equal(res3.status, 1);
    assert.match(res3.stdout, /START-APP\.cmd was not found/);
    assert.match(res3.stdout, /START-SETUP\.cmd was not found/);
  });
});

// ============================================================================
// 3. English Default Behavior
// ============================================================================

test("English is the default language when no configuration exists", () => {
  const tmp = createTempDir("fh-js-test-default");
  try {
    const res = runMenu(["--config-dir", tmp, "--action", "q"]);
    assert.equal(res.status, 0);
    assert.match(res.stdout, /Exiting starter menu\./);
    assert.doesNotMatch(res.stdout, /Starter-Menü beendet\./);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

// ============================================================================
// 4. start_menu.json Language Persistence
// ============================================================================

test("start_menu.json persists language preference and schema", () => {
  const tmp = createTempDir("fh-js-test-persistence");
  try {
    // Explicitly set language to 'de'
    const res1 = runMenu(["--config-dir", tmp, "--language", "de", "--action", "q"]);
    assert.equal(res1.status, 0);

    const cfgPath = join(tmp, "start_menu.json");
    assert.ok(existsSync(cfgPath), "start_menu.json must be created");

    const parsed = JSON.parse(readFileSync(cfgPath, "utf8"));
    assert.equal(parsed.schema, "folderhome.start-menu-config.v1");
    assert.equal(parsed.language, "de");

    // Subsequent run without --language flag inherits 'de' from start_menu.json
    const res2 = runMenu(["--config-dir", tmp, "--action", "q"]);
    assert.equal(res2.status, 0);
    assert.match(res2.stdout, /Starter-Menü beendet\./);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

// ============================================================================
// 5. Explicit Network and Cloud Gates
// ============================================================================

describe("Explicit network and cloud gates", () => {
  let tmp;

  beforeEach(() => {
    tmp = createTempDir("fh-js-test-gates");
    writeFileSync(join(tmp, "START-APP.cmd"), "@echo off\r\n", "ascii");
    writeFileSync(
      join(tmp, "launch.json"),
      JSON.stringify({ model_preset: "cloud-remote", model_provider: "bedrock" }, null, 2),
      "utf8",
    );
  });

  afterEach(() => {
    rmSync(tmp, { recursive: true, force: true });
  });

  test("remote preset with --deny-gates fails closed", () => {
    const res = runMenu(["--config-dir", tmp, "--action", "1", "--dry-run", "--deny-gates"]);
    assert.equal(res.status, 0);
    assert.match(res.stdout, /Remote\/cloud model preset 'cloud-remote' \(provider: bedrock\) detected\./);
    assert.match(res.stdout, /No network or cloud gates granted \(fail-closed\)\./);
    assert.doesNotMatch(res.stdout, /--allow-network/);
    assert.doesNotMatch(res.stdout, /--approve-sensitive-cloud-data/);
  });

  test("remote preset with --confirm-gates grants permissions", () => {
    const res = runMenu(["--config-dir", tmp, "--action", "1", "--dry-run", "--confirm-gates"]);
    assert.equal(res.status, 0);
    assert.match(res.stdout, /Remote\/cloud model preset 'cloud-remote' \(provider: bedrock\) detected\./);
    assert.match(res.stdout, /Network and cloud data gates approved\./);
    assert.match(res.stdout, /--allow-network/);
    assert.match(res.stdout, /--approve-sensitive-cloud-data/);
  });

  test("remote preset with interactive default prompt fails closed on empty input", () => {
    const res = runMenu(["--config-dir", tmp, "--action", "1", "--dry-run"], {
      input: "\n",
    });
    assert.equal(res.status, 0);
    assert.match(res.stdout, /No network or cloud gates granted \(fail-closed\)\./);
    assert.doesNotMatch(res.stdout, /--allow-network/);
  });
});

// ============================================================================
// 6. Ollama 600 Second Timeout
// ============================================================================

test("Ollama model presets receive --model-timeout-seconds 600", () => {
  const tmp = createTempDir("fh-js-test-ollama");
  try {
    writeFileSync(join(tmp, "START-APP.cmd"), "@echo off\r\n", "ascii");
    writeFileSync(
      join(tmp, "launch.json"),
      JSON.stringify({ model_preset: "deepseek-coder", model_provider: "ollama" }),
      "utf8",
    );

    const res = runMenu(["--config-dir", tmp, "--action", "1", "--dry-run"]);
    assert.equal(res.status, 0);
    assert.match(res.stdout, /Applied Ollama model timeout: 600s/);
    assert.match(res.stdout, /--model-timeout-seconds 600/);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

// ============================================================================
// 7. Dry-Run (No Subprocess & No User-Config Mutation)
// ============================================================================

test("dry-run mode executes zero subprocesses and causes zero user-config mutation", () => {
  const tmp = createTempDir("fh-js-test-dryrun");
  try {
    writeFileSync(join(tmp, "START-APP.cmd"), "@echo off\r\n", "ascii");
    writeFileSync(join(tmp, "START-SETUP.cmd"), "@echo off\r\n", "ascii");

    const originalConfig = JSON.stringify({
      model_preset: "custom-preset",
      model_provider: "fixture",
      custom_setting: "do_not_mutate",
    }, null, 2);
    const configPath = join(tmp, "launch.json");
    writeFileSync(configPath, originalConfig, "utf8");

    const res = runMenu(["--config-dir", tmp, "--dry-run", "--action", "3"]);
    assert.equal(res.status, 0);
    assert.match(res.stdout, /\[Dry-run Command\]/);
    assert.doesNotMatch(res.stdout, /http:\/\/127\.0\.0\.1/);
    assert.match(res.stdout, /\[Dry-run\] Operation completed without launching subprocesses\./);

    // Verify user config was completely unmutated
    const contentAfter = readFileSync(configPath, "utf8");
    assert.equal(contentAfter, originalConfig, "launch.json must remain byte-for-byte identical");
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});
