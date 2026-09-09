"use strict";

const queryParameters = new URLSearchParams(window.location.search);
const token = queryParameters.get("token") || "";
const supportedLanguages = ["en", "de"];
const supportedThemes = ["light", "dark"];

const translations = {
  en: {
    skipLink: "Skip to content",
    schedulerTitle: "Regular folder checks",
    schedulerUnavailable: "Service control is not configured or unavailable. Check the selected profile's Scheduler settings in Setup.",
    schedulerRefresh: "Refresh service status",
    schedulerScope: "Uses the selected profile. Status covers this app only; other instances are not observed. Checks prepare proposals, not document actions.",
    schedulerGate: "Configure in Setup and register the job separately. Starting also requires --approve-scheduler-consumer at app launch. Closing the app signals a stop after the current check.",
    schedulerPreview: "Preview service start",
    schedulerStart: "Start this exact service",
    schedulerStop: "Stop this app's service",
    schedulerState_unknown: "Service status has not been observed.",
    schedulerState_not_started_in_this_app: "No service has been started in this app.",
    schedulerState_running: "This app's service is running.",
    schedulerState_stopping: "Stopping after the current check; not stopped yet.",
    schedulerState_stopped: "This app's service has stopped.",
    schedulerState_failed: "This app's service failed. Review its private report before starting again.",
    schedulerControlError: "The request could not be confirmed. Check configuration and refresh status before retrying; an interrupted start request may already have started the service.",
    schedulerProposal: "Profile: {profile}. Every {interval} minutes from {start} ({zone}). Watches: {watches}. Registration is required and will be checked at start.",
    schedulerLastObservation: "Last check: {time}; result: {status}.",
    schedulerNoObservation: "No completed check has been observed in this app.",
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
    resultNoArtifacts: "No downloadable file is available for this run.",
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
    recipeLabel: "Multi-step journey",
    recipePrepare: "Prepare whole journey",
    recipeHint: "Preparation runs no workflow. Review every step before the separate confirmation.",
    recipeUnavailable: "Not ready: required resources or connected executors are missing.",
    recipeEmpty: "No journey available",
    recipeReview: "Deterministic recipe review passed; one confirmation covers all steps.",
    recipeAborted: "Journey stopped. Completed: {completed}; failed: {failed}; not started: {pending}. A failed step may already have had effects. Check the actual state before retrying.",
    planDetails: "Review the exact prepared step",
    planConfirmed: "Plan confirmed; no workflow has been executed yet.",
    executionCompleted: "Workflow executed successfully ({id}).",
    executionReport: "Execution report",
    confirmationInProgress: "Confirmation in progress…",
    executionUncertainTitle: "Run incomplete or uncertain",
    executionUncertain: "An effect may already exist. Check the affected target and private evidence before any new approval; do not repeat automatically. Confirmed entries below do not account for every possible effect.",
    confirmedCalendarEntries: "Confirmed calendar entries: {count}",
    confirmedCalendarReferences: "Show confirmed event references",
    calendarMutationUpdated: "Calendar change verified by readback.",
    calendarMutationAbsent: "Calendar event confirmed absent; this does not prove which request removed it.",
    calendarMutationEvidence: "Show calendar version evidence",
    calendarEventVersions: "Show event references for follow-up changes",
    calendarVersionCaution: "Previously confirmed versions; each new change requires a fresh check and approval.",
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
    schedulerTitle: "Regelmäßige Ordnerprüfungen",
    schedulerUnavailable: "Dienststeuerung ist nicht eingerichtet oder nicht verfügbar. Scheduler-Einstellungen des ausgewählten Profils im Setup prüfen.",
    schedulerRefresh: "Dienststatus aktualisieren",
    schedulerScope: "Verwendet das ausgewählte Profil. Der Status gilt nur für diese App; andere Instanzen werden nicht beobachtet. Prüfungen bereiten Vorschläge vor, keine Dokumentaktionen.",
    schedulerGate: "Im Setup einrichten und den Job separat registrieren. Starten benötigt zusätzlich --approve-scheduler-consumer beim App-Start. App-Schließen signalisiert einen Stopp nach der laufenden Prüfung.",
    schedulerPreview: "Dienststart vorschauen",
    schedulerStart: "Genau diesen Dienst starten",
    schedulerStop: "Dienst dieser App stoppen",
    schedulerState_unknown: "Dienststatus wurde noch nicht beobachtet.",
    schedulerState_not_started_in_this_app: "In dieser App wurde kein Dienst gestartet.",
    schedulerState_running: "Der Dienst dieser App läuft.",
    schedulerState_stopping: "Stoppt nach der laufenden Prüfung; noch nicht gestoppt.",
    schedulerState_stopped: "Der Dienst dieser App ist gestoppt.",
    schedulerState_failed: "Der Dienst dieser App ist fehlgeschlagen. Vor erneutem Start den privaten Bericht prüfen.",
    schedulerControlError: "Die Anfrage konnte nicht bestätigt werden. Konfiguration prüfen und vor Wiederholung den Status aktualisieren; eine unterbrochene Startanfrage kann den Dienst bereits gestartet haben.",
    schedulerProposal: "Profil: {profile}. Alle {interval} Minuten ab {start} ({zone}). Watches: {watches}. Registrierung ist erforderlich und wird beim Start geprüft.",
    schedulerLastObservation: "Letzte Prüfung: {time}; Ergebnis: {status}.",
    schedulerNoObservation: "In dieser App wurde noch keine abgeschlossene Prüfung beobachtet.",
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
    resultNoArtifacts: "Für diesen Lauf ist keine herunterladbare Datei verfügbar.",
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
    recipeLabel: "Mehrschritt-Aufgabe",
    recipePrepare: "Gesamte Aufgabe vorbereiten",
    recipeHint: "Die Vorbereitung führt keinen Workflow aus. Vor der getrennten Freigabe alle Schritte prüfen.",
    recipeUnavailable: "Noch nicht bereit: Benötigte Ressourcen oder verbundene Ausführer fehlen.",
    recipeEmpty: "Keine Mehrschritt-Aufgabe verfügbar",
    recipeReview: "Deterministische Rezeptprüfung bestanden; eine Bestätigung gilt für alle Schritte.",
    recipeAborted: "Aufgabe gestoppt. Ausgeführt: {completed}; gescheitert: {failed}; nicht gestartet: {pending}. Ein gescheiterter Schritt kann bereits gewirkt haben. Vor einem neuen Versuch den tatsächlichen Zustand prüfen.",
    planDetails: "Genau vorbereiteten Schritt prüfen",
    planConfirmed: "Plan freigegeben; noch wurde kein Workflow ausgeführt.",
    executionCompleted: "Workflow erfolgreich ausgeführt ({id}).",
    executionReport: "Ausführungsbericht",
    confirmationInProgress: "Bestätigung läuft…",
    executionUncertainTitle: "Lauf unvollständig oder unklar",
    executionUncertain: "Eine Wirkung kann bereits bestehen. Vor einer neuen Freigabe betroffenes Zielsystem und privaten Nachweis prüfen; nicht automatisch wiederholen. Die bestätigten Einträge unten erfassen nicht jede mögliche Wirkung.",
    confirmedCalendarEntries: "Bestätigte Kalendereinträge: {count}",
    confirmedCalendarReferences: "Bestätigte Ereignisreferenzen anzeigen",
    calendarMutationUpdated: "Kalenderänderung durch Rücklesen bestätigt.",
    calendarMutationAbsent: "Abwesenheit des Termins bestätigt; dies beweist nicht, welcher Aufruf ihn entfernt hat.",
    calendarMutationEvidence: "Kalender-Versionsnachweis anzeigen",
    calendarEventVersions: "Ereignisreferenzen für Folgeänderungen anzeigen",
    calendarVersionCaution: "Zuvor bestätigte Versionen; jede weitere Änderung benötigt eine erneute Prüfung und Freigabe.",
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
const recipeSelect = document.querySelector("#recipe-select");
const prepareRecipeButton = document.querySelector("#prepare-recipe");
const recipeHint = document.querySelector("#recipe-hint");
let recipeItems = [];
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
let resultsRequestVersion = 0;

class LocalRequestError extends Error {
  constructor(status, outcome = null) {
    super(`Local request failed with status ${status}`);
    this.status = status;
    this.outcome = outcome;
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
  if (profileSelect.value) loadRecipes().catch(showError);
  renderSchedulerControl();
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
  if (!response.ok) {
    const outcome = response.status === 409
      && payload?.schema === "folderhome.local-api-error.v1"
      && payload.execution_outcome_unknown === true && payload.retry_safe === false
      ? payload : null;
    throw new LocalRequestError(response.status, outcome);
  }
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
      const recipe = (report.proposed_recipes || []).find((item) => item.plan.plan_id === plan.plan_id);
      if (recipe) {
        cards.push(textElement("p", `${plan.summary} ${t("recipeReview")}`, "result-card"));
      }
      for (const step of plan.steps || []) {
        const card = document.createElement("article");
        card.className = "result-card plan-card";
        card.append(textElement("small", t("proposedWorkflow"), "card-label"));
        card.append(textElement("h3", step.workflow_id));
        card.append(textElement("p", step.goal));
        if (step.execution_envelope) {
          const details = document.createElement("details");
          details.className = "plan-details";
          details.append(textElement("summary", t("planDetails")));
          details.append(textElement("pre", JSON.stringify(step.execution_envelope.domain_plan, null, 2)));
          card.append(details);
        }
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
          outcome?.confirmation_pending
            ? t("confirmationInProgress")
            : outcome?.execution_outcome_unknown
            ? t("executionUncertainTitle")
            : outcome?.recipe_execution?.status === "aborted"
            ? recipeOutcomeText(outcome.recipe_execution)
            : outcome?.execution_performed
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
        if (outcome?.execution_outcome_unknown) {
          const uncertainResults = outcome.uncertain_results || [];
          for (const item of uncertainResults.length ? uncertainResults : [{}]) {
            renderUncertainResult(approvalCard, item);
          }
        }
        cards.push(approvalCard);
        for (const report of outcome?.execution_reports || []) {
          const executionCard = document.createElement("article");
          executionCard.className = "result-card execution-card";
          executionCard.append(textElement("small", t("executionReport"), "card-label"));
          executionCard.append(textElement("h3", report.workflow_id));
          executionCard.append(textElement("p", `${report.status} · ${report.execution_id}`));
          renderCalendarMutation(executionCard, report.domain_report?.mutation);
          renderCalendarVersions(executionCard, report.domain_report?.event_versions);
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
  const version = ++resultsRequestVersion;
  if (!profileId) return;
  const payload = await api(`/api/v1/agent/results?profile_id=${encodeURIComponent(profileId)}`);
  if (version !== resultsRequestVersion || profileSelect.value !== profileId) return;
  renderResults(payload.results || []);
}

function renderCalendarVersions(card, versions) {
  if (!Array.isArray(versions) || !versions.length) return;
  const confirmed = versions.filter(item => item?.schema === "folderhome.google-calendar-event-version.v1");
  if (!confirmed.length) return;
  const details = document.createElement("details");
  details.append(textElement("summary", t("calendarEventVersions")));
  details.append(textElement("p", t("calendarVersionCaution")));
  details.append(textElement("pre", JSON.stringify(confirmed, null, 2)));
  card.append(details);
}

function renderCalendarMutation(card, mutation) {
  if (!mutation || mutation.schema !== "folderhome.google-calendar-mutation-result.v1") return;
  const updated = mutation.operation === "update" && mutation.status === "updated";
  const absent = mutation.operation === "delete" && mutation.status === "absent";
  if (!updated && !absent) return;
  card.append(textElement("strong", t(updated ? "calendarMutationUpdated" : "calendarMutationAbsent")));
  const details = document.createElement("details");
  details.append(textElement("summary", t("calendarMutationEvidence")));
  details.append(textElement("pre", JSON.stringify(mutation, null, 2)));
  card.append(details);
}

function renderUncertainResult(card, item) {
  const warning = textElement("p", t("executionUncertain"), "result-warning");
  warning.setAttribute("role", "status");
  card.append(warning);
  renderCalendarMutation(card, item.evidence?.confirmed_mutation);
  const refs = item.evidence?.confirmed_event_references;
  if (Array.isArray(refs)) {
    card.append(textElement("strong", t("confirmedCalendarEntries", { count: refs.length })));
    if (refs.length) {
      const details = document.createElement("details");
      details.append(textElement("summary", t("confirmedCalendarReferences")));
      details.append(textElement("pre", JSON.stringify(refs, null, 2)));
      card.append(details);
    }
  }
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
    const status = item.status === "uncertain" ? t("executionUncertainTitle") : item.status;
    card.append(textElement("h3", `${item.workflow_id} · ${status}`));
    card.append(textElement("p", `${item.executed_at} · ${(item.side_effects || []).join(", ")}`));
    if (item.status === "uncertain") renderUncertainResult(card, item);
    else renderCalendarMutation(card, item.evidence?.confirmed_mutation);
    renderCalendarVersions(card, item.evidence?.event_versions);
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
  if (planOutcomes[plan.plan_id]) return;
  planOutcomes[plan.plan_id] = { confirmation_pending: true };
  let payload;
  try {
    payload = await api("/api/v1/agent/confirm", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-agent-confirmation-request.v1",
        plan_id: plan.plan_id,
        plan_sha256: plan.plan_sha256,
        step_ids: (plan.steps || []).map((step) => step.step_id),
      }),
    });
  } catch (error) {
    if (error instanceof LocalRequestError && error.outcome) {
      payload = error.outcome;
    } else if (!(error instanceof LocalRequestError) || error.status >= 500) {
      // No reliable acknowledgement: the POST may have committed before disconnect.
      payload = {
        execution_outcome_unknown: true, retry_safe: false,
        confirmation_response_missing: true, uncertain_results: [],
      };
    } else {
      delete planOutcomes[plan.plan_id];
      throw error;
    }
  }
  planOutcomes[plan.plan_id] = payload;
  if (profileSelect.value !== plan.profile_id) return;
  if (payload.execution_outcome_unknown) {
    appendChatMessage("assistant", t("executionUncertain"));
  } else if (payload.recipe_execution?.status === "aborted") {
    appendChatMessage("assistant", recipeOutcomeText(payload.recipe_execution));
  } else if (payload.execution_performed) {
    const reports = payload.execution_reports || [];
    const firstId = reports[0]?.execution_id || "unknown";
    appendChatMessage("assistant", t("executionCompleted", { id: firstId }));
  } else if (payload.receipt?.status === "confirmed_for_workflow_handoff") {
    appendChatMessage("assistant", t("planConfirmed"));
  }
  renderCurrentView(false);
  if (payload.confirmation_response_missing) return;
  if (payload.execution_outcome_unknown) {
    // A failed list refresh must not hide the already displayed uncertainty.
    try { await loadResults(); } catch (_error) { /* Manual refresh remains available. */ }
  } else {
    await loadResults();
  }
}

function recipeOutcomeText(result) {
  return t("recipeAborted", {
    completed: (result.executed_step_refs || []).join(", ") || "—",
    failed: (result.failed_step_refs || []).join(", ") || "—",
    pending: (result.not_attempted_step_refs || []).join(", ") || "—",
  });
}

async function loadRecipes() {
  const profileId = profileSelect.value;
  const requestedLanguage = language;
  if (!profileId) return;
  const payload = await api(`/api/v1/agent/recipes?profile_id=${encodeURIComponent(profileId)}&language=${requestedLanguage}`);
  if (profileSelect.value !== profileId || language !== requestedLanguage) return;
  recipeItems = payload.recipes || [];
  recipeSelect.replaceChildren();
  for (const item of recipeItems) {
    const option = document.createElement("option");
    option.value = item.recipe_id;
    option.textContent = item.title;
    recipeSelect.append(option);
  }
  renderRecipeSelection();
}

function renderRecipeSelection() {
  const selected = recipeItems.find((item) => item.recipe_id === recipeSelect.value);
  prepareRecipeButton.disabled = !selected?.available;
  recipeHint.textContent = !selected ? t("recipeEmpty") : selected.available
    ? `${selected.summary} ${t("recipeHint")}` : t("recipeUnavailable");
}

async function prepareRecipe(event) {
  event.preventDefault();
  const selected = recipeItems.find((item) => item.recipe_id === recipeSelect.value);
  if (!selected?.available) return;
  const profileId = profileSelect.value;
  prepareRecipeButton.disabled = true;
  try {
    const recipe = await api("/api/v1/agent/recipes/plan", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-recipe-plan-request.v1", profile_id: profileId,
        recipe_id: selected.recipe_id, language,
      }),
    });
    if (profileSelect.value !== profileId) return;
    showAgent({ agent: {
      response_text: recipe.plan.summary, tool_events: [],
      proposed_plans: [recipe.plan], proposed_recipes: [recipe],
    } });
  } finally {
    renderRecipeSelection();
  }
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

// Scheduler consumer controls
let schedulerView = { busy: false, preview: null, status: null, error: null };

function resetSchedulerControl() {
  schedulerView = { busy: false, preview: null, status: null, error: null };
  renderSchedulerControl();
}

function renderSchedulerControl() {
  const view = schedulerView;
  const status = view.status?.status || "unknown";
  document.querySelector("#scheduler-status").textContent = t(view.error || `schedulerState_${status}`);
  const observation = view.status?.last_observation;
  document.querySelector("#scheduler-last-observation").textContent = observation
    ? t("schedulerLastObservation", { time: observation.observed_at, status: observation.status })
    : t("schedulerNoObservation");
  const details = document.querySelector("#scheduler-preview-details");
  details.hidden = !view.preview;
  details.textContent = view.preview ? t("schedulerProposal", {
    profile: view.preview.profile_id, interval: view.preview.interval_minutes,
    start: view.preview.start_at, zone: view.preview.timezone, watches: view.preview.watch_ids.join(", "),
  }) : "";
  document.querySelector("#scheduler-start").disabled = view.busy || !view.preview?.live_effect_approved;
  document.querySelector("#scheduler-stop").disabled = view.busy || status !== "running";
  document.querySelector("#scheduler-preview").disabled = view.busy || !profileSelect.value;
  document.querySelector("#scheduler-status-refresh").disabled = view.busy || !profileSelect.value;
}

async function schedulerAction(action) {
  const profile = profileSelect.value;
  const view = schedulerView;
  if (!profile || view.busy) return;
  if (action === "start" && (!view.preview?.live_effect_approved || view.preview.profile_id !== profile)) return;
  if (action === "stop" && (view.status?.status !== "running" || view.status.profile_id !== profile)) return;
  const payload = { schema: `folderhome.scheduler-consumer-${action}-request.v1`, profile_id: profile };
  if (action === "start") {
    payload.plan_id = view.preview.plan_id;
    payload.plan_sha256 = view.preview.plan_sha256;
  }
  if (action === "stop") payload.worker_id = view.status.worker_id;
  if (action !== "status") view.preview = null;
  view.busy = true;
  view.error = null;
  renderSchedulerControl();
  try {
    const result = action === "status"
      ? await api(`/api/v1/scheduler/status?profile_id=${encodeURIComponent(profile)}`)
      : await api(`/api/v1/scheduler/${action}`, { method: "POST", body: JSON.stringify(payload) });
    if (schedulerView !== view || profileSelect.value !== profile) return;
    if (action === "preview") view.preview = result;
    else view.status = result;
  } catch (_error) {
    if (schedulerView !== view || profileSelect.value !== profile) return;
    view.error = action === "status" && _error.status === 503 ? "schedulerUnavailable" : "schedulerControlError";
    view.preview = null;
  } finally {
    if (schedulerView === view) {
      view.busy = false;
      renderSchedulerControl();
      if (view.refreshAfter) {
        view.refreshAfter = false;
        await schedulerAction("status");
      }
    } else if (profileSelect.value === profile && ["start", "stop"].includes(action)) {
      // A late effect may invalidate an earlier status read after A → B → A.
      // Reconcile through a fresh GET; never restore the abandoned approval.
      schedulerView.refreshAfter = true;
      if (!schedulerView.busy) {
        schedulerView.refreshAfter = false;
        await schedulerAction("status");
      }
    }
  }
}
// End scheduler consumer controls

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
  await loadRecipes();
  await schedulerAction("status");
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
  resetSchedulerControl();
  schedulerAction("status");
  currentView = null;
  renderCurrentView(false);
  prepareRecipeButton.disabled = true;
  loadResults().catch(showError);
  loadRecipes().catch(showError);
});
recipeSelect.addEventListener("change", renderRecipeSelection);
document.querySelector("#recipe-form").addEventListener("submit", (event) => {
  prepareRecipe(event).catch(showError);
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

for (const [id, action] of Object.entries({
  "scheduler-preview": "preview", "scheduler-start": "start",
  "scheduler-stop": "stop", "scheduler-status-refresh": "status",
})) {
  document.querySelector(`#${id}`).addEventListener("click", () => schedulerAction(action));
}

setLanguage(language, { persist: false });
setTheme(theme, { persist: false });
bootstrap().catch((error) => {
  connectionStatus = "blocked";
  renderConnection();
  showError(error);
});
