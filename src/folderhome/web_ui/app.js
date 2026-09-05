"use strict";

const queryParameters = new URLSearchParams(window.location.search);
const token = queryParameters.get("token") || "";
const supportedLanguages = ["en", "de"];
const supportedThemes = ["light", "dark"];

const translations = {
  en: {
    skipLink: "Skip to content",
    brandHome: "FolderHome home",
    languageSwitch: "FolderHome language",
    useEnglish: "Use English",
    useGerman: "Use German",
    themeSwitch: "FolderHome theme",
    lightTheme: "Light",
    darkTheme: "Dark",
    localBadge: "Local to this operating-system account",
    serviceEyebrow: "Document and assistance service",
    heroDocuments: "Your documents.",
    heroDaily: "Your everyday life.",
    heroPlace: "One place.",
    heroCopy: "Find scattered information, build topic summaries, and keep track of private documents locally.",
    securityBoundary: "Security boundary",
    operatingSystemAccount: "Operating-system account",
    familyProfiles: "Family profiles organize information; they do not grant access.",
    activeFolder: "Active workspace",
    agentChat: "FolderHome agent",
    whatHelp: "What can I help you with?",
    modelChecking: "Checking model …",
    modelCheckingDetail: "Reading the local runtime configuration.",
    modelFixture: "Demo model (fixture)",
    modelFixtureDetail: "FolderHome and its files stay local. No live LLM is connected; responses use deterministic test behavior.",
    modelConfigured: "Amazon Bedrock configured",
    modelConfiguredDetail: "FolderHome and its files stay local; model inference is configured for {model} in {region}. No successful live chat has been verified in this process yet.",
    modelVerified: "Amazon Bedrock active",
    modelVerifiedDetail: "FolderHome and its files stay local; prompts and bounded tool results use {model} in {region}. {count} successful live model turn(s) in this process.",
    resultsEyebrow: "Delivery",
    resultsTitle: "Results you can pick up",
    refreshResults: "Refresh",
    resultsEmpty: "Nothing has run yet in this process. Confirmed plans and their files appear here, including runs started through the API or an editor.",
    resultArtifacts: "Files",
    resultNoArtifacts: "This run changed local state and produced no file.",
    modelLocalConfigured: "Local model configured (Ollama)",
    modelLocalConfiguredDetail: "FolderHome and its files stay local; model inference is configured for {model} at {host}. No successful live chat has been verified in this process yet.",
    modelLocalVerified: "Local model active (Ollama)",
    modelLocalVerifiedDetail: "FolderHome and its files stay local; prompts and bounded tool results use {model} at {host}. {count} successful live model turn(s) in this process.",
    welcomeMessage: "Tell me what you want to find, understand, organize, or prepare. I will use a safe tool directly or propose a bounded workflow.",
    chatPlaceholder: "Find my latest Hyundai i10 insurance and show me what changed …",
    sendButton: "Send",
    newConversation: "New conversation",
    conversationReset: "A new process-local conversation has started.",
    exampleDossier: "Try a topic dossier",
    chatHint: "Conversation is never an approval. FolderHome shows a separate plan before any workflow with side effects.",
    planEyebrow: "Agent details",
    planTitle: "Tools and proposed plans",
    assistantLabel: "FolderHome",
    youLabel: "You",
    agentWorking: "FolderHome is thinking and using bounded tools …",
    toolUsed: "Tool used",
    proposedWorkflow: "Proposed workflow",
    approvalRequired: "Separate approval required",
    readOnlyPlan: "Read-only; no approval required",
    confirmPlan: "Confirm for workflow handoff",
    confirmExecute: "Confirm and execute",
    planConfirmed: "Plan confirmed; no workflow has been executed yet.",
    executionCompleted: "Workflow executed successfully ({id}).",
    executionReport: "Execution report",
    workflowConnected: "Connected executor ready",
    workflowPlanningOnly: "This system endpoint is intentionally planning-only.",
    workflowNotConnected: "No typed chat executor is connected yet; confirmation creates a handoff only.",
    documentSearch: "Document search",
    whatFind: "What would you like to find?",
    profile: "Profile",
    profileLabel: "Organizational profile",
    searchPlaceholder: "I am looking for a document about my health insurance …",
    searchButton: "Find document",
    dossierButton: "Build topic dossier",
    searchHint: "Search reads only the existing local index. It does not change files.",
    resultEyebrow: "Result",
    localMatches: "Local matches",
    capabilityEyebrow: "One home, many workflows",
    capabilityTitle: "What FolderHome brings together",
    connectionChecking: "Checking connection …",
    connectionReady: "Local connection ready",
    connectionBlocked: "Local connection blocked",
    footer: "FolderHome works locally, transparently, and with deliberate approvals.",
    processAccount: "Process account: {account}",
    directUse: "Available here",
    cliUse: "Through safe CLI workflows",
    agentUse: "Guided by the FolderHome agent",
    running: "running",
    searching: "Searching the local index …",
    blocked: "blocked",
    requestFailed: "The local request was blocked (status {status}).",
    noHits: "No local match found.",
    hitCountOne: "1 match",
    hitCountMany: "{count} matches",
  },
  de: {
    skipLink: "Zum Inhalt springen",
    brandHome: "FolderHome Startseite",
    languageSwitch: "FolderHome Sprache",
    useEnglish: "Englisch verwenden",
    useGerman: "Deutsch verwenden",
    themeSwitch: "FolderHome Erscheinungsbild",
    lightTheme: "Hell",
    darkTheme: "Dunkel",
    localBadge: "Lokal auf diesem Betriebssystemkonto",
    serviceEyebrow: "Dokument- und Assistenzservice",
    heroDocuments: "Deine Dokumente.",
    heroDaily: "Dein Alltag.",
    heroPlace: "Ein Ort.",
    heroCopy: "Finde verstreute Informationen, fasse Themen zusammen und behalte deine privaten Unterlagen lokal im Blick.",
    securityBoundary: "Sicherheitsgrenze",
    operatingSystemAccount: "Betriebssystemkonto",
    familyProfiles: "Familienprofile organisieren – sie erteilen keine Zugriffsrechte.",
    activeFolder: "Aktiver Arbeitsordner",
    agentChat: "FolderHome-Agent",
    whatHelp: "Wobei kann ich dir helfen?",
    modelChecking: "Modell wird geprüft …",
    modelCheckingDetail: "Die lokale Laufzeitkonfiguration wird gelesen.",
    modelFixture: "Demomodell (Fixture)",
    modelFixtureDetail: "FolderHome und seine Dateien bleiben lokal. Kein Live-LLM ist verbunden; Antworten verwenden deterministisches Testverhalten.",
    modelConfigured: "Amazon Bedrock konfiguriert",
    modelConfiguredDetail: "FolderHome und seine Dateien bleiben lokal; die Modellinferenz ist für {model} in {region} konfiguriert. In diesem Prozess wurde noch kein erfolgreicher Live-Chat bestätigt.",
    modelVerified: "Amazon Bedrock aktiv",
    modelVerifiedDetail: "FolderHome und seine Dateien bleiben lokal; Prompts und begrenzte Werkzeugresultate verwenden {model} in {region}. {count} erfolgreiche Live-Modellrunde(n) in diesem Prozess.",
    resultsEyebrow: "Zustellung",
    resultsTitle: "Ergebnisse zum Abholen",
    refreshResults: "Aktualisieren",
    resultsEmpty: "In diesem Prozess lief noch nichts. Freigegebene Pläne und ihre Dateien erscheinen hier, auch wenn sie über die API oder einen Editor gestartet wurden.",
    resultArtifacts: "Dateien",
    resultNoArtifacts: "Dieser Lauf hat lokalen Zustand geändert und keine Datei erzeugt.",
    modelLocalConfigured: "Lokales Modell konfiguriert (Ollama)",
    modelLocalConfiguredDetail: "FolderHome und seine Dateien bleiben lokal; die Modellinferenz ist für {model} auf {host} konfiguriert. In diesem Prozess wurde noch kein erfolgreicher Live-Chat bestätigt.",
    modelLocalVerified: "Lokales Modell aktiv (Ollama)",
    modelLocalVerifiedDetail: "FolderHome und seine Dateien bleiben lokal; Prompts und begrenzte Werkzeugresultate verwenden {model} auf {host}. {count} erfolgreiche Live-Modellrunde(n) in diesem Prozess.",
    welcomeMessage: "Sag mir, was du finden, verstehen, ordnen oder vorbereiten möchtest. Ich nutze direkt ein sicheres Werkzeug oder schlage einen begrenzten Workflow vor.",
    chatPlaceholder: "Finde meine neueste Hyundai-i10-Versicherung und zeige mir die Änderungen …",
    sendButton: "Senden",
    newConversation: "Neue Unterhaltung",
    conversationReset: "Eine neue prozesslokale Unterhaltung wurde begonnen.",
    exampleDossier: "Themendossier ausprobieren",
    chatHint: "Ein Gespräch ist niemals eine Freigabe. Vor jedem Workflow mit Nebenwirkungen zeigt FolderHome einen eigenen Plan.",
    planEyebrow: "Agentendetails",
    planTitle: "Werkzeuge und vorgeschlagene Pläne",
    assistantLabel: "FolderHome",
    youLabel: "Du",
    agentWorking: "FolderHome denkt nach und nutzt begrenzte Werkzeuge …",
    toolUsed: "Verwendetes Werkzeug",
    proposedWorkflow: "Vorgeschlagener Workflow",
    approvalRequired: "Eigene Freigabe erforderlich",
    readOnlyPlan: "Nur lesend; keine Freigabe erforderlich",
    confirmPlan: "Für Workflow-Übergabe freigeben",
    confirmExecute: "Freigeben und ausführen",
    planConfirmed: "Plan freigegeben; noch wurde kein Workflow ausgeführt.",
    executionCompleted: "Workflow erfolgreich ausgeführt ({id}).",
    executionReport: "Ausführungsbericht",
    workflowConnected: "Verbundener Executor ist bereit",
    workflowPlanningOnly: "Dieser Systemendpunkt ist absichtlich nur planend.",
    workflowNotConnected: "Noch ist kein typisierter Chat-Executor verbunden; die Freigabe erzeugt nur eine Übergabe.",
    documentSearch: "Dokumentensuche",
    whatFind: "Was möchtest du finden?",
    profile: "Profil",
    profileLabel: "Organisatorisches Profil",
    searchPlaceholder: "Ich suche ein Dokument über meine Krankenversicherung …",
    searchButton: "Dokument suchen",
    dossierButton: "Themendossier erstellen",
    searchHint: "Die Suche liest nur den vorhandenen lokalen Index. Sie verändert keine Datei.",
    resultEyebrow: "Ergebnis",
    localMatches: "Lokale Fundstellen",
    capabilityEyebrow: "Ein Zuhause, viele Abläufe",
    capabilityTitle: "Was FolderHome zusammenführt",
    connectionChecking: "Verbindung wird geprüft …",
    connectionReady: "Lokale Verbindung bereit",
    connectionBlocked: "Lokale Verbindung blockiert",
    footer: "FolderHome arbeitet lokal, transparent und mit bewussten Freigaben.",
    processAccount: "Prozesskonto: {account}",
    directUse: "Hier direkt nutzbar",
    cliUse: "Über sichere CLI-Workflows",
    agentUse: "Durch den FolderHome-Agenten begleitet",
    running: "läuft",
    searching: "Der lokale Index wird durchsucht …",
    blocked: "blockiert",
    requestFailed: "Die lokale Anfrage wurde blockiert (Status {status}).",
    noHits: "Keine lokale Fundstelle gefunden.",
    hitCountOne: "1 Fundstelle",
    hitCountMany: "{count} Fundstellen",
  },
};

const capabilityTitles = {
  en: {
    "documents.search": "Document search",
    "documents.theme_dossier": "Topic dossiers",
    "folders.organize": "Organize folders",
    "documents.create": "Create documents and presentations",
    "communications.manage": "Letters, email, and contacts",
    "calendar.manage": "Appointments and calendar handoffs",
    "finance.overview": "Finance and contract overview",
    "health.organize": "Organize health documents",
    "legal.orient": "Understand notices and legal changes",
    "household.manage": "Manage household and medication",
  },
  de: {
    "documents.search": "Dokumentensuche",
    "documents.theme_dossier": "Themendossier",
    "folders.organize": "Ordner organisieren",
    "documents.create": "Dokumente und Präsentationen erstellen",
    "communications.manage": "Briefe, Mail und Kontakte",
    "calendar.manage": "Termine und Kalenderhandoffs",
    "finance.overview": "Finanzen und Verträge überblicken",
    "health.organize": "Gesundheitsunterlagen organisieren",
    "legal.orient": "Bescheide und Rechtsänderungen verstehen",
    "household.manage": "Haushalt und Medikamente verwalten",
  },
};

const profileSelect = document.querySelector("#profile-select");
const resultSection = document.querySelector("#result-section");
const resultsSection = document.querySelector("#results-section");
const resultsContent = document.querySelector("#results-content");
const refreshResultsButton = document.querySelector("#refresh-results");
const resultContent = document.querySelector("#result-content");
const resultCount = document.querySelector("#result-count");
const messageInput = document.querySelector("#message");
const newConversationButton = document.querySelector("#new-conversation");
const chatTranscript = document.querySelector("#chat-transcript");
const connectionState = document.querySelector("#connection-state");
const capabilityGrid = document.querySelector("#capability-grid");
const runtimeAccount = document.querySelector("#runtime-account");
const modelStatus = document.querySelector("#model-status");
const modelStatusTitle = document.querySelector("#model-status-title");
const modelStatusDetail = document.querySelector("#model-status-detail");
const actionButtons = [...document.querySelectorAll(".actions button")];
const languageButtons = [...document.querySelectorAll("[data-language]")];
const themeButtons = [...document.querySelectorAll("[data-theme-mode]")];
const promptExamples = [...document.querySelectorAll(".prompt-example")];

let language = initialLanguage();
let theme = initialTheme();
let capabilityItems = [];
let executorItems = {};
let processAccountName = "";
let modelConnection = null;
let connectionStatus = "checking";
let currentView = null;
const planOutcomes = {};

class LocalRequestError extends Error {
  constructor(status) {
    super(`Local request failed with status ${status}`);
    this.status = status;
  }
}

function initialLanguage() {
  const requested = queryParameters.get("lang");
  if (supportedLanguages.includes(requested)) return requested;
  try {
    const stored = window.localStorage.getItem("folderhome.language");
    if (supportedLanguages.includes(stored)) return stored;
  } catch (_error) {
    // Storage can be unavailable in hardened browser profiles.
  }
  return "en";
}

function initialTheme() {
  const requested = queryParameters.get("theme");
  if (supportedThemes.includes(requested)) return requested;
  try {
    const stored = window.localStorage.getItem("folderhome.theme");
    if (supportedThemes.includes(stored)) return stored;
  } catch (_error) {
    // Storage can be unavailable in hardened browser profiles.
  }
  return "light";
}

function t(key, replacements = {}) {
  let value = translations[language][key] || translations.en[key] || key;
  for (const [name, replacement] of Object.entries(replacements)) {
    value = value.replace(`{${name}}`, String(replacement));
  }
  return value;
}

function setLanguage(nextLanguage, { persist = true } = {}) {
  if (!supportedLanguages.includes(nextLanguage)) return;
  language = nextLanguage;
  document.documentElement.lang = language;
  if (persist) {
    try {
      window.localStorage.setItem("folderhome.language", language);
    } catch (_error) {
      // The current view still changes when storage is unavailable.
    }
  }
  applyStaticTranslations();
  renderConnection();
  renderModelStatus();
  renderRuntimeAccount();
  renderCapabilities();
  renderCurrentView(false);
}

function setTheme(nextTheme, { persist = true } = {}) {
  if (!supportedThemes.includes(nextTheme)) return;
  theme = nextTheme;
  document.documentElement.dataset.theme = theme;
  if (persist) {
    try {
      window.localStorage.setItem("folderhome.theme", theme);
    } catch (_error) {
      // The current view still changes when storage is unavailable.
    }
  }
  themeButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.themeMode === theme));
  });
}

function applyStaticTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
  document.querySelector("#language-switch").setAttribute("aria-label", t("languageSwitch"));
  document.querySelector("#theme-switch").setAttribute("aria-label", t("themeSwitch"));
  languageButtons.forEach((button) => {
    const isActive = button.dataset.language === language;
    button.setAttribute("aria-pressed", String(isActive));
    button.setAttribute("aria-label", t(button.dataset.language === "en" ? "useEnglish" : "useGerman"));
  });
  themeButtons.forEach((button) => {
    button.setAttribute("aria-label", t(button.dataset.themeMode === "light" ? "lightTheme" : "darkTheme"));
  });
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-FolderHome-Token", token);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers, credentials: "omit" });
  const payload = await response.json();
  if (!response.ok) throw new LocalRequestError(response.status);
  return payload;
}

function textElement(tag, value, className = "") {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}

function hitCount(count) {
  return t(count === 1 ? "hitCountOne" : "hitCountMany", { count });
}

function renderConnection() {
  const key = connectionStatus === "ready"
    ? "connectionReady"
    : connectionStatus === "blocked"
      ? "connectionBlocked"
      : "connectionChecking";
  connectionState.textContent = t(key);
}

function renderRuntimeAccount() {
  runtimeAccount.textContent = processAccountName
    ? t("processAccount", { account: processAccountName })
    : "";
}

function renderModelStatus() {
  if (!modelConnection) {
    modelStatus.dataset.state = "checking";
    modelStatusTitle.textContent = t("modelChecking");
    modelStatusDetail.textContent = t("modelCheckingDetail");
    return;
  }
  modelStatus.dataset.state = modelConnection.connection_status;
  if (modelConnection.connection_status === "fixture_only") {
    modelStatusTitle.textContent = t("modelFixture");
    modelStatusDetail.textContent = t("modelFixtureDetail");
    return;
  }
  const isOllama = modelConnection.provider === "ollama";
  const values = {
    model: modelConnection.model_id || (isOllama ? "Ollama model" : "Bedrock model"),
    region: modelConnection.aws_region || "AWS region",
    host: modelConnection.ollama_host || "the configured Ollama host",
    count: modelConnection.successful_live_model_turns || 0,
  };
  const verified = modelConnection.connection_status === "verified_in_process";
  const titleKey = isOllama
    ? (verified ? "modelLocalVerified" : "modelLocalConfigured")
    : (verified ? "modelVerified" : "modelConfigured");
  modelStatusTitle.textContent = t(titleKey);
  modelStatusDetail.textContent = t(`${titleKey}Detail`, values);
}

function renderCapabilities() {
  if (!capabilityItems.length) return;
  const cards = capabilityItems.map((item) => {
    const card = document.createElement("article");
    card.className = "capability-card";
    card.dataset.status = item.surface_status;
    card.append(textElement("strong", capabilityTitles[language][item.capability_id] || item.title));
    card.append(textElement(
      "small",
      t(
        item.surface_status === "interactive_read_only"
          ? "directUse"
          : item.surface_status === "agent_guided"
            ? "agentUse"
            : "cliUse",
      ),
    ));
    return card;
  });
  capabilityGrid.replaceChildren(...cards);
}

function renderCurrentView(scroll = true) {
  if (!currentView) return;
  resultSection.hidden = false;
  if (currentView.kind === "loading") {
    resultCount.textContent = t("running");
    resultContent.replaceChildren(textElement("div", t("agentWorking"), "result-card"));
  } else if (currentView.kind === "error") {
    resultCount.textContent = t("blocked");
    resultContent.replaceChildren(textElement(
      "div",
      t("requestFailed", { status: currentView.status || "?" }),
      "result-card error",
    ));
  } else if (currentView.kind === "agent") {
    const report = currentView.payload.agent;
    const tools = report.tool_events || [];
    const plans = report.proposed_plans || [];
    resultCount.textContent = `${tools.length} / ${plans.length}`;
    const cards = [];
    for (const event of tools) {
      const card = document.createElement("article");
      card.className = "result-card tool-card";
      card.append(textElement("small", t("toolUsed"), "card-label"));
      card.append(textElement("h3", event.tool_name));
      cards.push(card);
    }
    for (const plan of plans) {
      for (const step of plan.steps || []) {
        const card = document.createElement("article");
        card.className = "result-card plan-card";
        card.append(textElement("small", t("proposedWorkflow"), "card-label"));
        card.append(textElement("h3", step.workflow_id));
        card.append(textElement(
          "p",
          step.confirmation_required ? t("approvalRequired") : t("readOnlyPlan"),
        ));
        const executor = executorItems[step.workflow_id];
        if (step.confirmation_required && executor) {
          card.append(textElement(
            "p",
            executor.status === "connected"
              ? t("workflowConnected")
              : executor.status === "planning_only"
                ? t("workflowPlanningOnly")
                : t("workflowNotConnected"),
            `executor-status ${executor.status}`,
          ));
        }
        cards.push(card);
      }
      if (plan.confirmation_required) {
        const outcome = planOutcomes[plan.plan_id];
        const approvalCard = document.createElement("article");
        approvalCard.className = "result-card approval-card";
        const executionReady = (plan.steps || []).some((step) => step.execution_envelope);
        const button = textElement(
          "button",
          outcome?.execution_performed
            ? t("executionCompleted", {
              id: outcome.execution_reports?.[0]?.execution_id || "unknown",
            })
            : outcome
              ? t("planConfirmed")
              : t(executionReady ? "confirmExecute" : "confirmPlan"),
          "button primary",
        );
        button.type = "button";
        button.disabled = Boolean(outcome);
        if (!outcome) {
          button.addEventListener("click", () => confirmPlan(plan, button).catch(showError));
        }
        approvalCard.append(button);
        cards.push(approvalCard);
        for (const report of outcome?.execution_reports || []) {
          const executionCard = document.createElement("article");
          executionCard.className = "result-card execution-card";
          executionCard.append(textElement("small", t("executionReport"), "card-label"));
          executionCard.append(textElement("h3", report.workflow_id));
          executionCard.append(textElement("p", `${report.status} · ${report.execution_id}`));
          cards.push(executionCard);
        }
      }
    }
    if (!cards.length) cards.push(textElement("div", report.response_text, "result-card"));
    resultContent.replaceChildren(...cards);
  }
  if (scroll) resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadResults() {
  const profileId = profileSelect.value;
  if (!profileId) return;
  const payload = await api(`/api/v1/agent/results?profile_id=${encodeURIComponent(profileId)}`);
  renderResults(payload.results || []);
}

function renderResults(items) {
  resultsSection.hidden = false;
  resultsContent.replaceChildren();
  if (!items.length) {
    resultsContent.append(textElement("p", t("resultsEmpty")));
    return;
  }
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "result-card";
    card.append(textElement("h3", `${item.workflow_id} · ${item.status}`));
    card.append(textElement("p", `${item.executed_at} · ${(item.side_effects || []).join(", ")}`));
    const artifacts = item.artifacts || [];
    if (!artifacts.length) {
      card.append(textElement("p", t("resultNoArtifacts")));
    } else {
      const list = document.createElement("p");
      list.append(textElement("strong", `${t("resultArtifacts")}: `));
      for (const artifact of artifacts) {
        const link = document.createElement("button");
        link.type = "button";
        link.className = "button secondary";
        link.textContent = `${artifact.name} (${artifact.size_bytes} B)`;
        link.addEventListener("click", () => {
          downloadArtifact(item.execution_id, artifact.index, artifact.name).catch(showError);
        });
        list.append(link);
      }
      card.append(list);
    }
    resultsContent.append(card);
  }
}

async function downloadArtifact(executionId, index, filename) {
  const response = await fetch(
    `/api/v1/agent/results/${encodeURIComponent(executionId)}/artifacts/${index}`,
    { headers: { "X-FolderHome-Token": token }, credentials: "omit" },
  );
  if (!response.ok) throw new LocalRequestError(response.status);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function confirmPlan(plan, button) {
  button.disabled = true;
  const payload = await api("/api/v1/agent/confirm", {
    method: "POST",
    body: JSON.stringify({
      schema: "folderhome.local-agent-confirmation-request.v1",
      plan_id: plan.plan_id,
      plan_sha256: plan.plan_sha256,
      step_ids: (plan.steps || []).filter((step) => step.confirmation_required).map((step) => step.step_id),
    }),
  });
  planOutcomes[plan.plan_id] = payload;
  if (payload.execution_performed) {
    const reports = payload.execution_reports || [];
    const firstId = reports[0]?.execution_id || "unknown";
    appendChatMessage("assistant", t("executionCompleted", { id: firstId }));
  } else if (payload.receipt?.status === "confirmed_for_workflow_handoff") {
    appendChatMessage("assistant", t("planConfirmed"));
  }
  renderCurrentView(false);
  await loadResults();
}

function appendChatMessage(kind, value) {
  const message = document.createElement("article");
  message.className = `chat-message ${kind}`;
  message.append(textElement(
    "span",
    kind === "assistant" ? t("assistantLabel") : t("youLabel"),
    "chat-speaker",
  ));
  message.append(textElement("p", value));
  chatTranscript.append(message);
}

function showError(error) {
  currentView = { kind: "error", status: error instanceof LocalRequestError ? error.status : 0 };
  renderCurrentView();
}

function showAgent(payload) {
  currentView = { kind: "agent", payload };
  appendChatMessage("assistant", payload.agent.response_text || t("planTitle"));
  renderCurrentView();
}

async function runAgent() {
  const value = messageInput.value.trim();
  if (!value) {
    messageInput.focus();
    return;
  }
  const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  appendChatMessage("user", value);
  messageInput.value = "";
  resultSection.setAttribute("aria-busy", "true");
  actionButtons.forEach((button) => { button.disabled = true; });
  currentView = { kind: "loading" };
  renderCurrentView();
  try {
    const payload = await api("/api/v1/agent/chat", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-agent-chat-request.v1",
        profile_id: profileSelect.value,
        message: value,
      }),
    });
    showAgent(payload);
  } finally {
    resultSection.setAttribute("aria-busy", "false");
    actionButtons.forEach((button) => { button.disabled = false; });
    returnFocus?.focus({ preventScroll: true });
  }
}

async function resetConversation() {
  const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  actionButtons.forEach((button) => { button.disabled = true; });
  try {
    await api("/api/v1/agent/conversation/reset", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-agent-conversation-reset-request.v1",
        profile_id: profileSelect.value,
      }),
    });
    for (const planId of Object.keys(planOutcomes)) delete planOutcomes[planId];
    chatTranscript.replaceChildren();
    appendChatMessage("assistant", t("conversationReset"));
    currentView = null;
    renderCurrentView(false);
  } finally {
    actionButtons.forEach((button) => { button.disabled = false; });
    (returnFocus || messageInput)?.focus({ preventScroll: true });
  }
}

async function bootstrap() {
  const [status, profiles, capabilities, executors] = await Promise.all([
    api("/api/v1/status"),
    api("/api/v1/profiles"),
    api("/api/v1/capabilities"),
    api("/api/v1/agent/executors"),
  ]);
  for (const profile of profiles.profiles) {
    const option = document.createElement("option");
    option.value = profile.profile_id;
    option.textContent = profile.display_name;
    profileSelect.append(option);
  }
  processAccountName = status.process_identity.account_name;
  modelConnection = status.model_connection;
  connectionStatus = "ready";
  capabilityItems = capabilities.capabilities;
  executorItems = Object.fromEntries(
    (executors.workflows || []).map((item) => [item.workflow_id, item]),
  );
  renderRuntimeAccount();
  renderModelStatus();
  renderConnection();
  renderCapabilities();
  await loadResults();
}

languageButtons.forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});
themeButtons.forEach((button) => {
  button.addEventListener("click", () => setTheme(button.dataset.themeMode));
});
document.querySelector("#agent-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAgent().catch(showError);
});
refreshResultsButton.addEventListener("click", () => {
  loadResults().catch(showError);
});
profileSelect.addEventListener("change", () => {
  loadResults().catch(showError);
});
newConversationButton.addEventListener("click", () => {
  resetConversation().catch(showError);
});
promptExamples.forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = language === "de" ? button.dataset.promptDe : button.dataset.promptEn;
    runAgent().catch(showError);
  });
});

setLanguage(language, { persist: false });
setTheme(theme, { persist: false });
bootstrap().catch((error) => {
  connectionStatus = "blocked";
  renderConnection();
  showError(error);
});
