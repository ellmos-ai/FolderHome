const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { test } = require("node:test");

class MockElement {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.attributes = {};
    this.hidden = false;
    this.textContent = "";
  }
  append(...items) {
    for (const item of items) {
      item.parent = this;
      this.children.push(item);
    }
  }
  replaceChildren(...items) {
    this.children = [];
    this.append(...items);
  }
  setAttribute(name, val) { this.attributes[name] = String(val); }
  getAttribute(name) { return this.attributes[name] !== undefined ? this.attributes[name] : null; }
  querySelector(selector) {
    if (selector.startsWith("#")) {
      const id = selector.slice(1);
      const walk = (node) => {
        if (node.attributes && node.attributes.id === id) return node;
        for (const child of node.children) {
          const found = walk(child);
          if (found) return found;
        }
        return null;
      };
      return walk(this);
    }
    return null;
  }
}

const appSource = readFileSync(join(__dirname, "../../src/folderhome/web_ui/app.js"), "utf8");

function setupContext(initialState = {}) {
  const root = new MockElement("div");

  const localBadgeEl = new MockElement("span");
  localBadgeEl.setAttribute("id", "local-boundary-badge");
  const boundaryScopeEl = new MockElement("strong");
  boundaryScopeEl.setAttribute("id", "boundary-scope");
  const boundaryProfilesEl = new MockElement("small");
  boundaryProfilesEl.setAttribute("id", "boundary-profiles-claim");
  const localBadgeContainer = new MockElement("div");
  localBadgeContainer.className = "local-badge";
  localBadgeContainer.append(localBadgeEl);

  const topologyBadge = new MockElement("span");
  topologyBadge.setAttribute("id", "topology-badge");

  const modelStatus = new MockElement("div");
  modelStatus.setAttribute("id", "model-status");
  const modelStatusTitle = new MockElement("strong");
  modelStatusTitle.setAttribute("id", "model-status-title");
  const modelStatusDetail = new MockElement("small");
  modelStatusDetail.setAttribute("id", "model-status-detail");
  modelStatus.append(modelStatusTitle, modelStatusDetail);

  const connectionState = new MockElement("span");
  connectionState.setAttribute("id", "connection-state");

  root.append(
    localBadgeContainer,
    boundaryScopeEl,
    boundaryProfilesEl,
    topologyBadge,
    modelStatus,
    connectionState
  );

  const transContext = vm.createContext({});
  const transBlock = appSource.slice(
    appSource.indexOf("const translations ="),
    appSource.indexOf("const capabilityTitles =")
  );
  vm.runInContext(transBlock.replace("const translations =", "var translations ="), transContext);

  const context = vm.createContext({
    document: {
      querySelector: (sel) => root.querySelector(sel),
    },
    localBadgeEl,
    boundaryScopeEl,
    boundaryProfilesEl,
    localBadgeContainer,
    topologyBadge,
    modelStatus,
    modelStatusTitle,
    modelStatusDetail,
    connectionState,
    language: initialState.language || "en",
    connectionStatus: initialState.connectionStatus || "ready",
    appStatus: initialState.appStatus || null,
    modelConnection: initialState.modelConnection || null,
    renderPseudonymizationStatus: () => {},
    t: (key, replacements = {}) => {
      const lang = context.language;
      let val = transContext.translations[lang]?.[key] || transContext.translations.en?.[key] || key;
      for (const [k, v] of Object.entries(replacements)) {
        val = val.replace(`{${k}}`, String(v));
      }
      return val;
    },
  });

  const renderTopologyMatch = appSource.match(/function renderTopologyBadge\(\) \{[\s\S]*?\n\}/);
  const renderBoundaryMatch = appSource.match(/function renderBoundary\(\) \{[\s\S]*?\n\}/);
  const renderModelStatusMatch = appSource.match(/function renderModelStatus\(\) \{[\s\S]*?\n\}/);
  const renderConnectionMatch = appSource.match(/function renderConnection\(\) \{[\s\S]*?\n\}/);

  vm.runInContext(renderTopologyMatch[0], context);
  vm.runInContext(renderBoundaryMatch[0], context);
  vm.runInContext(renderModelStatusMatch[0], context);
  vm.runInContext(renderConnectionMatch[0], context);

  return { context, root, localBadgeEl, boundaryScopeEl, topologyBadge, modelStatus, modelStatusTitle, modelStatusDetail, connectionState };
}

test("app and documents are always described as local to operating-system account across all topologies", () => {
  for (const topology of ["loopback_local", "remote_host", "cloud"]) {
    for (const lang of ["en", "de"]) {
      const { context, localBadgeEl, boundaryScopeEl } = setupContext({
        language: lang,
        connectionStatus: "ready",
        appStatus: { runtime_topology: topology },
      });

      context.renderBoundary();

      if (lang === "en") {
        assert.equal(localBadgeEl.textContent, "Local to this operating-system account");
        assert.equal(boundaryScopeEl.textContent, "Operating-system account");
      } else {
        assert.equal(localBadgeEl.textContent, "Lokal auf diesem Betriebssystemkonto");
        assert.equal(boundaryScopeEl.textContent, "Betriebssystemkonto");
      }
    }
  }
});

test("Remote Ollama truthfully describes model host as remote and topology as REMOTE", () => {
  for (const lang of ["en", "de"]) {
    const { context, topologyBadge, modelStatusTitle, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "ready",
      appStatus: {
        model_provider: "ollama",
        model_state: "configured_unverified",
        runtime_topology: "remote_host",
        successful_live_model_turns: 0,
      },
      modelConnection: {
        provider: "ollama",
        model_id: "llama3.2:3b",
        ollama_host: "http://192.168.1.50:11434",
        runtime_topology: "remote_host",
      },
    });

    context.renderTopologyBadge();
    context.renderModelStatus();

    assert.equal(topologyBadge.textContent, "REMOTE");
    assert.equal(topologyBadge.dataset.topology, "remote_host");

    if (lang === "en") {
      assert.match(modelStatusTitle.textContent, /Remote model configured \(Ollama\)/);
      assert.match(modelStatusDetail.textContent, /on remote host http:\/\/192\.168\.1\.50:11434/);
      assert.match(modelStatusDetail.textContent, /FolderHome and its files stay local/);
    } else {
      assert.match(modelStatusTitle.textContent, /Remote-Modell konfiguriert \(Ollama\)/);
      assert.match(modelStatusDetail.textContent, /auf dem Remote-Host http:\/\/192\.168\.1\.50:11434/);
      assert.match(modelStatusDetail.textContent, /FolderHome und seine Dateien bleiben lokal/);
    }
  }
});

test("Cloud Bedrock describes provider as cloud with AWS region", () => {
  for (const lang of ["en", "de"]) {
    const { context, topologyBadge, modelStatusTitle, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "ready",
      appStatus: {
        model_provider: "bedrock",
        model_state: "configured_unverified",
        runtime_topology: "cloud",
        successful_live_model_turns: 0,
      },
      modelConnection: {
        provider: "bedrock",
        model_id: "amazon.nova-micro-v1:0",
        aws_region: "eu-central-1",
        runtime_topology: "cloud",
      },
    });

    context.renderTopologyBadge();
    context.renderModelStatus();

    assert.match(topologyBadge.textContent, /CLOUD/);
    assert.equal(topologyBadge.dataset.topology, "cloud");

    if (lang === "en") {
      assert.match(modelStatusTitle.textContent, /Amazon Bedrock configured/);
      assert.match(modelStatusDetail.textContent, /in AWS region eu-central-1/);
    } else {
      assert.match(modelStatusTitle.textContent, /Amazon Bedrock konfiguriert/);
      assert.match(modelStatusDetail.textContent, /in AWS-Region eu-central-1/);
    }
  }
});

test("Cloud Anthropic describes provider as cloud API and does NOT mention AWS region", () => {
  for (const lang of ["en", "de"]) {
    const { context, topologyBadge, modelStatusTitle, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "ready",
      appStatus: {
        model_provider: "anthropic",
        model_state: "configured_unverified",
        runtime_topology: "cloud",
        successful_live_model_turns: 0,
      },
      modelConnection: {
        provider: "anthropic",
        model_id: "claude-3-5-sonnet",
        runtime_topology: "cloud",
      },
    });

    context.renderTopologyBadge();
    context.renderModelStatus();

    assert.match(topologyBadge.textContent, /CLOUD/);
    assert.equal(topologyBadge.dataset.topology, "cloud");

    const title = modelStatusTitle.textContent;
    const detail = modelStatusDetail.textContent;

    assert.doesNotMatch(title, /AWS|Bedrock|region/i);
    assert.doesNotMatch(detail, /AWS|Bedrock|region/i);

    if (lang === "en") {
      assert.match(title, /Anthropic cloud model/);
      assert.match(detail, /via Anthropic cloud API/);
      assert.match(detail, /FolderHome and its files stay local/);
    } else {
      assert.match(title, /Anthropic-Cloud-Modell/);
      assert.match(detail, /über die Anthropic-Cloud-API/);
      assert.match(detail, /FolderHome und seine Dateien bleiben lokal/);
    }
  }
});

test("Cloud OpenAI describes provider as cloud API and does NOT mention AWS region", () => {
  for (const lang of ["en", "de"]) {
    const { context, topologyBadge, modelStatusTitle, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "ready",
      appStatus: {
        model_provider: "openai",
        model_state: "configured_unverified",
        runtime_topology: "cloud",
        successful_live_model_turns: 0,
      },
      modelConnection: {
        provider: "openai",
        model_id: "gpt-4o",
        openai_base_url: "https://api.openai.com/v1",
        runtime_topology: "cloud",
      },
    });

    context.renderTopologyBadge();
    context.renderModelStatus();

    assert.match(topologyBadge.textContent, /CLOUD/);
    assert.equal(topologyBadge.dataset.topology, "cloud");

    const title = modelStatusTitle.textContent;
    const detail = modelStatusDetail.textContent;

    assert.doesNotMatch(title, /AWS|Bedrock|region/i);
    assert.doesNotMatch(detail, /AWS|Bedrock|region/i);

    if (lang === "en") {
      assert.match(title, /OpenAI-compatible cloud model/);
      assert.match(detail, /via OpenAI-compatible cloud API/);
      assert.match(detail, /https:\/\/api\.openai\.com\/v1/);
    } else {
      assert.match(title, /OpenAI-kompatibles Cloud-Modell/);
      assert.match(detail, /über die OpenAI-kompatible Cloud-API/);
      assert.match(detail, /https:\/\/api\.openai\.com\/v1/);
    }
  }
});

test("Disconnected and blocked error states are truthfully displayed", () => {
  // Disconnected
  for (const lang of ["en", "de"]) {
    const { context, localBadgeEl, boundaryScopeEl, connectionState, modelStatus, modelStatusTitle, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "disconnected",
      appStatus: null,
      modelConnection: null,
    });

    context.renderBoundary();
    context.renderConnection();
    context.renderModelStatus();

    assert.equal(connectionState.textContent, lang === "en" ? "Disconnected" : "Getrennt");
    assert.equal(localBadgeEl.textContent, lang === "en" ? "Disconnected from service" : "Vom Dienst getrennt");
    assert.equal(boundaryScopeEl.textContent, lang === "en" ? "Disconnected" : "Getrennt");
    assert.equal(modelStatus.dataset.state, "error");
    assert.equal(modelStatusTitle.textContent, lang === "en" ? "Disconnected" : "Getrennt");
    assert.match(modelStatusDetail.textContent, lang === "en" ? /unreachable/ : /nicht erreichbar/);
  }

  // Blocked
  for (const lang of ["en", "de"]) {
    const { context, localBadgeEl, boundaryScopeEl, connectionState, modelStatus, modelStatusTitle, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "blocked",
      appStatus: null,
      modelConnection: null,
    });

    context.renderBoundary();
    context.renderConnection();
    context.renderModelStatus();

    assert.equal(connectionState.textContent, lang === "en" ? "Local connection blocked" : "Lokale Verbindung blockiert");
    assert.equal(localBadgeEl.textContent, lang === "en" ? "Connection blocked" : "Verbindung blockiert");
    assert.equal(boundaryScopeEl.textContent, lang === "en" ? "Disconnected" : "Getrennt");
    assert.equal(modelStatus.dataset.state, "error");
    assert.equal(modelStatusTitle.textContent, lang === "en" ? "Local connection blocked" : "Lokale Verbindung blockiert");
    assert.match(modelStatusDetail.textContent, lang === "en" ? /blocked/ : /blockiert/);
  }
});

test("Ollama host display retains truthful host/topology without leaking credentials or query fragments", () => {
  for (const lang of ["en", "de"]) {
    const { context, topologyBadge, modelStatusDetail } = setupContext({
      language: lang,
      connectionStatus: "ready",
      appStatus: {
        model_provider: "ollama",
        model_state: "configured_unverified",
        runtime_topology: "remote_host",
        successful_live_model_turns: 0,
      },
      modelConnection: {
        provider: "ollama",
        model_id: "qwen3:4b",
        ollama_host: "http://remote.host.internal:11434",
        runtime_topology: "remote_host",
      },
    });

    context.renderTopologyBadge();
    context.renderModelStatus();

    assert.equal(topologyBadge.textContent, "REMOTE");
    assert.match(modelStatusDetail.textContent, /http:\/\/remote\.host\.internal:11434/);
    assert.doesNotMatch(modelStatusDetail.textContent, /secret/);
    assert.doesNotMatch(modelStatusDetail.textContent, /token/);
  }
});
