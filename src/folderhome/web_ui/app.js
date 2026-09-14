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
    runningLabel: "Running:",
    noPresetFlags: "no preset / flags",
    savedSettingDiffers: "Saved setting differs: {preset} — reload to apply",
    reloadButton: "Reload",
    reloadConfirm: "Reloading settings will apply the saved preset and reset the current conversation memory. Continue?",
    reloadError: "Settings could not be reloaded.",
    openSettings: "Open settings",
    settingsDialogTitle: "FolderHome Settings",
    settingsDialogText: "To configure models or workspaces, run the start menu in your terminal and select Option 2 (Setup):",
    copyCommand: "Copy",
    commandCopied: "Copied!",
    closeDialog: "Close",
    setupServerActiveText: "A setup server is currently running:",
    openSetupPage: "Open Setup page",
    serviceEyebrow: "Document and assistance service",
    heroDocuments: "Your documents.",
    heroDaily: "Your everyday life.",
    heroPlace: "One place.",
    heroCopy: "Find scattered information, build topic summaries, and keep track of private documents locally.",
    securityBoundary: "Security boundary",
    operatingSystemAccount: "Operating-system account",
    boundaryScopeRemote: "Remote operating-system account",
    boundaryScopeCloud: "Cloud sandbox",
    boundaryScopeDisconnected: "Disconnected",
    familyProfiles: "Family profiles organize information; they do not grant access.",
    familyProfilesAuthorization: "Family profiles serve as authorization boundaries.",
    localBadge: "Local to this operating-system account",
    localBadgeLocal: "Local to this operating-system account",
    localBadgeDisconnected: "Disconnected from service",
    localBadgeBlocked: "Connection blocked",
    connectionBlockedDetail: "The local request was blocked (token missing, invalid, or forbidden origin).",
    serviceDisconnectedDetail: "The local FolderHome service is currently unreachable.",
    activeFolder: "Active workspace",
    agentChat: "FolderHome agent",
    whatHelp: "What can I help you with?",
    modelStatusBanner: "Model status",
    modelChecking: "Checking model …",
    modelCheckingDetail: "Reading the local runtime configuration.",
    modelFixture: "Demo model (fixture)",
    modelFixtureDetail: "FolderHome and its files stay local. No live LLM is connected; responses use deterministic test behavior.",
    modelConfigured: "Amazon Bedrock configured",
    modelConfiguredDetail: "FolderHome and its files stay local; model inference is configured for {model} in AWS region {region}. No successful live chat has been verified in this process yet.",
    modelVerified: "Amazon Bedrock active",
    modelVerifiedDetail: "FolderHome and its files stay local; prompts and bounded tool results use {model} in AWS region {region}. {count} successful live model turn(s) in this process.",
    modelAnthropicConfigured: "Anthropic cloud model configured",
    modelAnthropicConfiguredDetail: "FolderHome and its files stay local; model inference is configured for {model} via Anthropic cloud API. No successful live chat has been verified in this process yet.",
    modelAnthropicVerified: "Anthropic cloud model active",
    modelAnthropicVerifiedDetail: "FolderHome and its files stay local; prompts and bounded tool results use {model} via Anthropic cloud API. {count} successful live model turn(s) in this process.",
    modelOpenAIConfigured: "OpenAI-compatible cloud model configured",
    modelOpenAIConfiguredDetail: "FolderHome and its files stay local; model inference is configured for {model} via OpenAI-compatible cloud API{endpoint}. No successful live chat has been verified in this process yet.",
    modelOpenAIVerified: "OpenAI-compatible cloud model active",
    modelOpenAIVerifiedDetail: "FolderHome and its files stay local; prompts and bounded tool results use {model} via OpenAI-compatible cloud API{endpoint}. {count} successful live model turn(s) in this process.",
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
    modelRemoteConfigured: "Remote model configured (Ollama)",
    modelRemoteConfiguredDetail: "FolderHome and its files stay local; model inference is configured for {model} on remote host {host}. No successful live chat has been verified in this process yet.",
    modelRemoteVerified: "Remote model active (Ollama)",
    modelRemoteVerifiedDetail: "FolderHome and its files stay local; prompts and bounded tool results use {model} on remote host {host}. {count} successful live model turn(s) in this process.",
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
    recipePrepareSection: "Prepare first section",
    recipeRunsTitle: "Started journeys",
    recipeRunsRefresh: "Refresh journeys",
    recipeRunsHint: "Runs belong to this profile and app session. Closing discards open sections; completed effects are not undone.",
    recipeRunsEmpty: "No started journey in this profile.",
    recipeRunsLoading: "Reading current journeys …",
    recipeRunsError: "Journey status is unavailable. Refresh before taking another action.",
    recipeActionError: "The action was not confirmed. Check the current status before continuing; it was not retried.",
    recipeNext: "Prepare next section",
    recipeReviewPending: "Review open section",
    recipeClose: "Close journey",
    recipeClosed: "Journey closed; open plan discarded.",
    recipePlanUnavailable: "This section is no longer open. Check the current journey status.",
    recipeProgress: "Confirmed steps: {steps}",
    recipeState_ready: "Ready for the next section — not yet executed",
    recipeState_awaiting_approval: "Waiting for this section's approval",
    recipeState_running: "Section running",
    recipeState_preparing: "Preparing section",
    recipeState_completed: "Journey completed",
    recipeState_aborted: "Journey stopped — inspect the results; do not repeat effects automatically",
    recipeState_closed: "Closed",
    recipeState_unknown: "Unknown state — refresh the journey status",
    recipeStageReview: "Deterministic recipe review passed. Confirm only this section; later sections require separate approval.",
    recipeStageHint: "Preparation runs no workflow. Later sections use confirmed results and require separate approval.",
    recipeDeliveryIncomplete: "The result list may be incomplete. Keep this execution report and check the underlying state; do not repeat effects to recover a missing receipt.",
    recipeStageConfirm: "Confirm and execute this section",
    recipeBindings: "Values carried from confirmed results",
    recipeBindingSource: "Source: {step} · report path: {path}",
    recipeBindingEvidence: "Source execution: {id}",
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
    calendarEdit: "Edit appointment",
    calendarTitle: "Title", calendarStart: "Start", calendarEnd: "End",
    calendarTimezone: "Time zone", calendarAllDay: "All-day event", calendarLocation: "Location (optional)",
    calendarReminders: "Popup reminders: minutes before, separated by commas",
    calendarDateHelp: "All-day: YYYY-MM-DD; end date is exclusive. Otherwise use an ISO timestamp with offset, e.g. 2026-09-12T14:00:00+02:00.",
    calendarPlanUpdate: "Review change", calendarPlanDelete: "Review deletion",
    calendarBefore: "Previously confirmed", calendarAfter: "Proposed replacement",
    calendarEditFailure: "Could not prepare this change. Check the fields, current version and permissions.",
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
    capabilityInfoShow: "Show capabilities",
    capabilityInfoHide: "Hide capabilities",
    connectionChecking: "Checking connection …",
    connectionReady: "Local connection ready",
    connectionReadyRemote: "Remote connection ready",
    connectionReadyCloud: "Cloud connection ready",
    connectionBlocked: "Local connection blocked",
    connectionBlockedRemote: "Remote connection blocked",
    connectionBlockedCloud: "Cloud connection blocked",
    connectionDisconnected: "Disconnected",
    notConnected: "Not connected in this installation",
    planningOnly: "Planning only",
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
    runningLabel: "Aktiv:",
    noPresetFlags: "kein Preset / Parameter",
    savedSettingDiffers: "Gespeicherte Einstellung weicht ab: {preset} — neu laden zum Übernehmen",
    reloadButton: "Neu laden",
    reloadConfirm: "Beim Neuladen der Einstellungen wird das gespeicherte Preset angewendet und der bisherige Gesprächsverlauf zurückgesetzt. Fortfahren?",
    reloadError: "Einstellungen konnten nicht neu geladen werden.",
    openSettings: "Einstellungen öffnen",
    settingsDialogTitle: "FolderHome-Einstellungen",
    settingsDialogText: "Um Modelle oder Arbeitsordner zu konfigurieren, starte das Startmenü im Terminal und wähle Option 2 (Setup):",
    copyCommand: "Kopieren",
    commandCopied: "Kopiert!",
    closeDialog: "Schließen",
    setupServerActiveText: "Ein Setup-Server läuft derzeit:",
    openSetupPage: "Setup-Seite öffnen",
    serviceEyebrow: "Dokument- und Assistenzservice",
    heroDocuments: "Deine Dokumente.",
    heroDaily: "Dein Alltag.",
    heroPlace: "Ein Ort.",
    heroCopy: "Finde verstreute Informationen, fasse Themen zusammen und behalte deine privaten Unterlagen lokal im Blick.",
    securityBoundary: "Sicherheitsgrenze",
    operatingSystemAccount: "Betriebssystemkonto",
    boundaryScopeRemote: "Entferntes Betriebssystemkonto",
    boundaryScopeCloud: "Cloud-Sandbox",
    boundaryScopeDisconnected: "Getrennt",
    familyProfiles: "Familienprofile organisieren – sie erteilen keine Zugriffsrechte.",
    familyProfilesAuthorization: "Familienprofile bilden Autorisierungsgrenzen.",
    localBadge: "Lokal auf diesem Betriebssystemkonto",
    localBadgeLocal: "Lokal auf diesem Betriebssystemkonto",
    localBadgeDisconnected: "Vom Dienst getrennt",
    localBadgeBlocked: "Verbindung blockiert",
    connectionBlockedDetail: "Die lokale Anfrage wurde blockiert (Token fehlt, ist ungültig oder Origin abgewiesen).",
    serviceDisconnectedDetail: "Der lokale FolderHome-Dienst ist derzeit nicht erreichbar.",
    activeFolder: "Aktiver Arbeitsordner",
    agentChat: "FolderHome-Agent",
    whatHelp: "Wobei kann ich dir helfen?",
    modelStatusBanner: "Modellstatus",
    modelChecking: "Modell wird geprüft …",
    modelCheckingDetail: "Die lokale Laufzeitkonfiguration wird gelesen.",
    modelFixture: "Demomodell (Fixture)",
    modelFixtureDetail: "FolderHome und seine Dateien bleiben lokal. Kein Live-LLM ist verbunden; Antworten verwenden deterministisches Testverhalten.",
    modelConfigured: "Amazon Bedrock konfiguriert",
    modelConfiguredDetail: "FolderHome und seine Dateien bleiben lokal; die Modellinferenz ist für {model} in AWS-Region {region} konfiguriert. In diesem Prozess wurde noch kein erfolgreicher Live-Chat bestätigt.",
    modelVerified: "Amazon Bedrock aktiv",
    modelVerifiedDetail: "FolderHome und seine Dateien bleiben lokal; Prompts und begrenzte Werkzeugresultate verwenden {model} in AWS-Region {region}. {count} erfolgreiche Live-Modellrunde(n) in diesem Prozess.",
    modelAnthropicConfigured: "Anthropic-Cloud-Modell konfiguriert",
    modelAnthropicConfiguredDetail: "FolderHome und seine Dateien bleiben lokal; die Modellinferenz ist für {model} über die Anthropic-Cloud-API konfiguriert. In diesem Prozess wurde noch kein erfolgreicher Live-Chat bestätigt.",
    modelAnthropicVerified: "Anthropic-Cloud-Modell aktiv",
    modelAnthropicVerifiedDetail: "FolderHome und seine Dateien bleiben lokal; Prompts und begrenzte Werkzeugresultate verwenden {model} über die Anthropic-Cloud-API. {count} erfolgreiche Live-Modellrunde(n) in diesem Prozess.",
    modelOpenAIConfigured: "OpenAI-kompatibles Cloud-Modell konfiguriert",
    modelOpenAIConfiguredDetail: "FolderHome und seine Dateien bleiben lokal; die Modellinferenz ist für {model} über die OpenAI-kompatible Cloud-API{endpoint} konfiguriert. In diesem Prozess wurde noch kein erfolgreicher Live-Chat bestätigt.",
    modelOpenAIVerified: "OpenAI-kompatibles Cloud-Modell aktiv",
    modelOpenAIVerifiedDetail: "FolderHome und seine Dateien bleiben lokal; Prompts und begrenzte Werkzeugresultate verwenden {model} über die OpenAI-kompatible Cloud-API{endpoint}. {count} erfolgreiche Live-Modellrunde(n) in diesem Prozess.",
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
    modelRemoteConfigured: "Remote-Modell konfiguriert (Ollama)",
    modelRemoteConfiguredDetail: "FolderHome und seine Dateien bleiben lokal; die Modellinferenz ist für {model} auf dem Remote-Host {host} konfiguriert. In diesem Prozess wurde noch kein erfolgreicher Live-Chat bestätigt.",
    modelRemoteVerified: "Remote-Modell aktiv (Ollama)",
    modelRemoteVerifiedDetail: "FolderHome und seine Dateien bleiben lokal; Prompts und begrenzte Werkzeugresultate verwenden {model} auf dem Remote-Host {host}. {count} erfolgreiche Live-Modellrunde(n) in diesem Prozess.",
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
    recipePrepareSection: "Ersten Abschnitt vorbereiten",
    recipeRunsTitle: "Begonnene Abläufe",
    recipeRunsRefresh: "Abläufe aktualisieren",
    recipeRunsHint: "Läufe gehören zu diesem Profil und dieser App-Sitzung. Schließen verwirft offene Abschnitte; abgeschlossene Wirkungen werden nicht zurückgenommen.",
    recipeRunsEmpty: "Kein begonnener Ablauf in diesem Profil.",
    recipeRunsLoading: "Aktuelle Abläufe werden gelesen …",
    recipeRunsError: "Der Laufstatus ist nicht verfügbar. Vor einer weiteren Aktion aktualisieren.",
    recipeActionError: "Die Aktion wurde nicht bestätigt. Vor dem Fortsetzen den aktuellen Stand prüfen; sie wurde nicht wiederholt.",
    recipeNext: "Nächsten Abschnitt vorbereiten",
    recipeReviewPending: "Offenen Abschnitt prüfen",
    recipeClose: "Ablauf schließen",
    recipeClosed: "Ablauf geschlossen; offener Plan verworfen.",
    recipePlanUnavailable: "Dieser Abschnitt ist nicht mehr offen. Aktuellen Laufstatus prüfen.",
    recipeProgress: "Bestätigte Schritte: {steps}",
    recipeState_ready: "Bereit für den nächsten Abschnitt — noch nicht ausgeführt",
    recipeState_awaiting_approval: "Wartet auf die Freigabe dieses Abschnitts",
    recipeState_running: "Abschnitt läuft",
    recipeState_preparing: "Abschnitt wird vorbereitet",
    recipeState_completed: "Ablauf abgeschlossen",
    recipeState_aborted: "Ablauf gestoppt — Ergebnisse prüfen; Wirkungen nicht automatisch wiederholen",
    recipeState_closed: "Geschlossen",
    recipeState_unknown: "Unbekannter Zustand — Laufstatus aktualisieren",
    recipeStageReview: "Deterministische Rezeptprüfung bestanden. Nur diesen Abschnitt bestätigen; spätere Abschnitte brauchen eine eigene Freigabe.",
    recipeStageHint: "Die Vorbereitung führt keinen Workflow aus. Spätere Abschnitte verwenden bestätigte Ergebnisse und brauchen eine eigene Freigabe.",
    recipeDeliveryIncomplete: "Die Ergebnisliste ist möglicherweise unvollständig. Diesen Ausführungsbericht behalten und den tatsächlichen Stand prüfen; Wirkungen nicht für einen fehlenden Beleg wiederholen.",
    recipeStageConfirm: "Diesen Abschnitt bestätigen und ausführen",
    recipeBindings: "Übernommene Werte aus bestätigten Ergebnissen",
    recipeBindingSource: "Quelle: {step} · Berichtspfad: {path}",
    recipeBindingEvidence: "Quellausführung: {id}",
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
    calendarEdit: "Termin bearbeiten",
    calendarTitle: "Titel", calendarStart: "Beginn", calendarEnd: "Ende",
    calendarTimezone: "Zeitzone", calendarAllDay: "Ganztägiger Termin", calendarLocation: "Ort (optional)",
    calendarReminders: "Popup-Erinnerungen: Minuten vorher, durch Kommas getrennt",
    calendarDateHelp: "Ganztägig: JJJJ-MM-TT; das Enddatum ist exklusiv. Sonst ISO-Zeitstempel mit Offset verwenden, z. B. 2026-09-12T14:00:00+02:00.",
    calendarPlanUpdate: "Änderung prüfen", calendarPlanDelete: "Löschung prüfen",
    calendarBefore: "Zuvor bestätigt", calendarAfter: "Vorgeschlagener Ersatz",
    calendarEditFailure: "Änderung nicht vorbereitet. Felder, aktuelle Version und Berechtigungen prüfen.",
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
    capabilityInfoShow: "Funktionen anzeigen",
    capabilityInfoHide: "Funktionen ausblenden",
    connectionChecking: "Verbindung wird geprüft …",
    connectionReady: "Lokale Verbindung bereit",
    connectionReadyRemote: "Remote-Verbindung bereit",
    connectionReadyCloud: "Cloud-Verbindung bereit",
    connectionBlocked: "Lokale Verbindung blockiert",
    connectionBlockedRemote: "Remote-Verbindung blockiert",
    connectionBlockedCloud: "Cloud-Verbindung blockiert",
    connectionDisconnected: "Getrennt",
    notConnected: "In dieser Installation nicht verbunden",
    planningOnly: "Nur Planung",
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
let recipeCatalogVersion = 0;
let recipeRunView = { runs: [], busy: null, readVersion: 0, readFailed: false, message: null };
const recipeRunsContent = document.querySelector("#recipe-runs-content");
const refreshRecipeRunsButton = document.querySelector("#refresh-recipe-runs");
const resultSection = document.querySelector("#result-section");
const resultsSection = document.querySelector("#results-section");
const resultsContent = document.querySelector("#results-content");
const refreshResultsButton = document.querySelector("#refresh-results");
const resultContent = document.querySelector("#result-content");
const resultCount = document.querySelector("#result-count");
const messageInput = document.querySelector("#message");
const newConversationButton = document.querySelector("#new-conversation");
const reloadSettingsButton = document.querySelector("#reload-settings-btn");
const openSettingsButton = document.querySelector("#open-settings-btn");
const settingsDialog = document.querySelector("#settings-dialog");
const closeSettingsDialogButton = document.querySelector("#close-settings-dialog-btn");
const copySettingsCommandButton = document.querySelector("#copy-settings-command-btn");
const setupServerActiveBox = document.querySelector("#setup-server-active-box");
const openSetupServerLink = document.querySelector("#open-setup-server-link");
const chatTranscript = document.querySelector("#chat-transcript");
const connectionState = document.querySelector("#connection-state");
const capabilityGrid = document.querySelector("#capability-grid");
const capabilityInfoButton = document.querySelector("#capability-info-btn");
const runtimeAccount = document.querySelector("#runtime-account");
const localBoundaryBadge = document.querySelector("#local-boundary-badge");
const boundaryScope = document.querySelector("#boundary-scope");
const boundaryProfilesClaim = document.querySelector("#boundary-profiles-claim");
const capabilityWorkflows = {
  "documents.search": ["document-library"],
  "documents.theme_dossier": ["document-library"],
  "folders.organize": [
    "directory-observation",
    "document-action-execution",
    "document-action-plan",
    "folder-cleanup",
    "folder-routine",
    "routine-queue",
  ],
  "documents.create": [
    "artifact-studio",
    "document-bundle",
    "document-package",
  ],
  "communications.manage": [
    "calendar-connectors",
    "calendar-handoff",
    "contact-register",
    "correspondence-studio",
    "findcall",
    "mail-connector",
  ],
  "calendar.manage": [
    "calendar-connectors",
    "calendar-handoff",
  ],
  "finance.overview": [
    "contract-cockpit",
    "finance-import",
    "tax-workpaper",
  ],
  "health.organize": [
    "health-dossier",
    "medication-intake",
  ],
  "legal.orient": [
    "administrative-drafts",
    "benefit-screening",
    "legal-change-monitor",
    "official-notice-understanding",
  ],
  "household.manage": [
    "daily-briefing",
    "inventory-import",
  ],
};
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
let appStatus = null;
let connectionStatus = "checking";
let currentView = null;
const planOutcomes = {};
let resultsRequestVersion = 0;
let conversationRevision = 0;
let conversationResetPending = false;

function renderTopologyBadge() {
  const badge = document.querySelector("#topology-badge");
  if (!badge) return;
  const topology = appStatus?.runtime_topology
    || modelConnection?.runtime_topology
    || "loopback_local";
  const topo = String(topology).toLowerCase();
  if (topo === "cloud") {
    badge.dataset.topology = "cloud";
    badge.textContent = "☁ CLOUD";
  } else if (topo === "remote_host" || topo === "remote") {
    badge.dataset.topology = "remote_host";
    badge.textContent = "REMOTE";
  } else {
    badge.dataset.topology = "loopback_local";
    badge.textContent = "LOCAL";
  }
}

class LocalRequestError extends Error {
  constructor(status, outcome = null, payload = null) {
    super(payload?.message || `Local request failed with status ${status}`);
    this.status = status;
    this.outcome = outcome;
    this.payload = payload;
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
  renderBoundary();
  renderTopologyBadge();
  renderModelStatus();
  renderRunningSettings();
  renderRuntimeAccount();
  renderCapabilities();
  renderCurrentView(false);
  if (profileSelect.value) loadRecipes().catch(showError);
  renderRecipeRuns();
  if (profileSelect.value) loadRecipeRuns();
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
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.setAttribute("title", t(element.dataset.i18nTitle));
  });
  document.querySelector("#language-switch").setAttribute("aria-label", t("languageSwitch"));
  document.querySelector("#theme-switch").setAttribute("aria-label", t("themeSwitch"));
  if (capabilityInfoButton && typeof capabilityInfoButton.getAttribute === "function") {
    const isExpanded = capabilityInfoButton.getAttribute("aria-expanded") === "true";
    const labelKey = isExpanded ? "capabilityInfoHide" : "capabilityInfoShow";
    if (typeof capabilityInfoButton.setAttribute === "function") {
      capabilityInfoButton.setAttribute("aria-label", t(labelKey));
      capabilityInfoButton.setAttribute("title", t(labelKey));
    }
  }
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
    throw new LocalRequestError(response.status, outcome, payload);
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
  if (!connectionState) return;
  const topology = (
    appStatus?.runtime_topology
    || modelConnection?.runtime_topology
    || "loopback_local"
  ).toLowerCase();

  let key;
  if (connectionStatus === "checking") {
    key = "connectionChecking";
  } else if (connectionStatus === "blocked") {
    if (topology === "cloud") key = "connectionBlockedCloud";
    else if (topology === "remote_host" || topology === "remote") key = "connectionBlockedRemote";
    else key = "connectionBlocked";
  } else if (connectionStatus === "ready") {
    if (topology === "cloud") key = "connectionReadyCloud";
    else if (topology === "remote_host" || topology === "remote") key = "connectionReadyRemote";
    else key = "connectionReady";
  } else {
    key = "connectionDisconnected";
  }
  connectionState.textContent = t(key);
  if (typeof connectionState.setAttribute === "function") {
    connectionState.setAttribute("data-state", connectionStatus);
    connectionState.setAttribute("data-topology", topology);
  }
}

function renderBoundary() {
  const localBadgeEl = document.querySelector("#local-boundary-badge") || document.querySelector(".local-badge span:not(.status-dot)");
  const boundaryScopeEl = document.querySelector("#boundary-scope");
  const boundaryProfilesEl = document.querySelector("#boundary-profiles-claim");
  const localBadgeContainer = document.querySelector(".local-badge");

  const topology = (
    appStatus?.runtime_topology
    || modelConnection?.runtime_topology
    || "loopback_local"
  ).toLowerCase();

  const isConnected = connectionStatus === "ready";
  const isBlocked = connectionStatus === "blocked";

  if (localBadgeEl) {
    let badgeKey;
    if (isBlocked) {
      badgeKey = "localBadgeBlocked";
    } else if (!isConnected && connectionStatus !== "checking") {
      badgeKey = "localBadgeDisconnected";
    } else {
      badgeKey = "localBadgeLocal";
    }
    localBadgeEl.textContent = t(badgeKey);
    if (localBadgeEl.dataset) {
      localBadgeEl.dataset.i18n = badgeKey;
    }
  }
  if (localBadgeContainer && typeof localBadgeContainer.setAttribute === "function") {
    localBadgeContainer.setAttribute("data-topology", topology);
    localBadgeContainer.setAttribute("data-status", connectionStatus);
  }

  if (boundaryScopeEl) {
    let scopeKey;
    if (isBlocked || (!isConnected && connectionStatus !== "checking")) {
      scopeKey = "boundaryScopeDisconnected";
    } else {
      scopeKey = "operatingSystemAccount";
    }
    boundaryScopeEl.textContent = t(scopeKey);
    if (boundaryScopeEl.dataset) {
      boundaryScopeEl.dataset.i18n = scopeKey;
    }
  }

  if (boundaryProfilesEl) {
    const isAuthBoundary = Boolean(appStatus?.profiles_are_authorization_boundaries);
    const claimKey = isAuthBoundary ? "familyProfilesAuthorization" : "familyProfiles";
    boundaryProfilesEl.textContent = t(claimKey);
    if (boundaryProfilesEl.dataset) {
      boundaryProfilesEl.dataset.i18n = claimKey;
    }
  }
}

function renderRuntimeAccount() {
  runtimeAccount.textContent = processAccountName
    ? t("processAccount", { account: processAccountName })
    : "";
}

function setPanelExpanded(panel, expanded) {
  if (!panel || typeof panel.querySelector !== "function") return;
  const head = panel.querySelector(".panel-head");
  const body = panel.querySelector(".panel-body");
  if (panel.classList && typeof panel.classList.toggle === "function") {
    panel.classList.toggle("is-collapsed", !expanded);
  }
  if (head && typeof head.setAttribute === "function") {
    head.setAttribute("aria-expanded", String(expanded));
  }
  if (body) {
    body.hidden = !expanded;
  }
}

function initCollapsiblePanels() {
  if (typeof document === "undefined" || typeof document.querySelectorAll !== "function") return;
  const panels = document.querySelectorAll(".collapsible-panel");
  if (!panels || !panels.forEach) return;
  panels.forEach((panel) => {
    if (!panel || typeof panel.querySelector !== "function") return;
    const head = panel.querySelector(".panel-head");
    if (!head || typeof head.addEventListener !== "function") return;
    const toggle = (e) => {
      if (e && e.target && typeof e.target.closest === "function" && e.target.closest("button")) return;
      const isExpanded = typeof head.getAttribute === "function"
        ? head.getAttribute("aria-expanded") === "true"
        : true;
      setPanelExpanded(panel, !isExpanded);
    };
    head.addEventListener("click", toggle);
    head.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        if (e.target && typeof e.target.closest === "function" && e.target.closest("button")) return;
        if (e.preventDefault) e.preventDefault();
        toggle(e);
      }
    });
  });
}

function renderModelStatus() {
  if (!modelConnection && !appStatus) {
    if (connectionStatus === "blocked") {
      modelStatus.dataset.state = "error";
      modelStatusTitle.textContent = t("connectionBlocked");
      modelStatusDetail.textContent = t("connectionBlockedDetail");
    } else if (connectionStatus === "disconnected") {
      modelStatus.dataset.state = "error";
      modelStatusTitle.textContent = t("connectionDisconnected");
      modelStatusDetail.textContent = t("serviceDisconnectedDetail");
    } else {
      modelStatus.dataset.state = "checking";
      modelStatusTitle.textContent = t("modelChecking");
      modelStatusDetail.textContent = t("modelCheckingDetail");
    }
    return;
  }
  const state = appStatus?.model_state || modelConnection?.connection_status || "fixture_only";
  modelStatus.dataset.state = state;

  const directLabel = language === "de"
    ? (appStatus?.model_state_label_de || modelConnection?.model_state_label_de)
    : (appStatus?.model_state_label_en || modelConnection?.model_state_label_en);

  if (directLabel) {
    modelStatusTitle.textContent = directLabel;
    if (appStatus?.model_state_detail_de || appStatus?.model_state_detail_en) {
      modelStatusDetail.textContent = language === "de"
        ? (appStatus.model_state_detail_de || appStatus.model_state_detail_en)
        : (appStatus.model_state_detail_en || appStatus.model_state_detail_de);
      return;
    }
  }

  if (state === "fixture_only") {
    if (!directLabel) modelStatusTitle.textContent = t("modelFixture");
    modelStatusDetail.textContent = t("modelFixtureDetail");
    return;
  }
  const provider = appStatus?.model_provider || modelConnection?.provider || "fixture";
  const topology = (
    appStatus?.runtime_topology
    || modelConnection?.runtime_topology
    || "loopback_local"
  ).toLowerCase();
  const turns = appStatus?.successful_live_model_turns ?? modelConnection?.successful_live_model_turns ?? 0;
  const verified = state === "verified_in_process";

  if (provider === "ollama") {
    const isRemote = topology === "remote_host" || topology === "remote";
    const model = modelConnection?.model_id || "Ollama model";
    const host = modelConnection?.ollama_host || (isRemote ? "remote host" : "http://127.0.0.1:11434");
    const titleKey = isRemote
      ? (verified ? "modelRemoteVerified" : "modelRemoteConfigured")
      : (verified ? "modelLocalVerified" : "modelLocalConfigured");
    if (!directLabel) {
      modelStatusTitle.textContent = t(titleKey);
    }
    modelStatusDetail.textContent = t(`${titleKey}Detail`, { model, host, count: turns });
  } else if (provider === "bedrock") {
    const model = modelConnection?.model_id || "Bedrock model";
    const region = modelConnection?.aws_region || "AWS region";
    const titleKey = verified ? "modelVerified" : "modelConfigured";
    if (!directLabel) {
      modelStatusTitle.textContent = t(titleKey);
    }
    modelStatusDetail.textContent = t(`${titleKey}Detail`, { model, region, count: turns });
  } else if (provider === "anthropic") {
    const model = modelConnection?.model_id || "Anthropic model";
    const titleKey = verified ? "modelAnthropicVerified" : "modelAnthropicConfigured";
    if (!directLabel) {
      modelStatusTitle.textContent = t(titleKey);
    }
    modelStatusDetail.textContent = t(`${titleKey}Detail`, { model, count: turns });
  } else if (provider === "openai") {
    const model = modelConnection?.model_id || "OpenAI model";
    const baseUrl = modelConnection?.openai_base_url || "";
    const endpoint = baseUrl ? ` (${baseUrl})` : "";
    const titleKey = verified ? "modelOpenAIVerified" : "modelOpenAIConfigured";
    if (!directLabel) {
      modelStatusTitle.textContent = t(titleKey);
    }
    modelStatusDetail.textContent = t(`${titleKey}Detail`, { model, endpoint, count: turns });
  } else {
    if (!directLabel) modelStatusTitle.textContent = t("modelFixture");
    modelStatusDetail.textContent = t("modelFixtureDetail");
  }
}

function renderRunningSettings() {
  if (!appStatus) return;
  const runningPreset = appStatus.running_preset || t("noPresetFlags");
  const provider = appStatus.model_provider || "fixture";
  const modelId = (appStatus.model_connection && appStatus.model_connection.model_id) || (provider === "fixture" ? "fixture" : "none");

  const summaryEl = document.querySelector("#running-settings-summary");
  if (summaryEl) {
    summaryEl.textContent = `${runningPreset} · ${provider} · ${modelId}`;
  }

  const staleBanner = document.querySelector("#settings-stale-banner");
  const staleText = document.querySelector("#settings-stale-text");
  if (staleBanner && staleText) {
    if (appStatus.settings_stale && appStatus.saved_preset) {
      staleText.textContent = t("savedSettingDiffers", { preset: appStatus.saved_preset });
      staleBanner.hidden = false;
    } else {
      staleBanner.hidden = true;
      staleText.textContent = "";
    }
  }
}

async function reloadSettings() {
  const confirmed = window.confirm(t("reloadConfirm"));
  if (!confirmed) return;
  if (reloadSettingsButton) reloadSettingsButton.disabled = true;
  try {
    await api("/api/v1/settings/reload", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-settings-reload-request.v1",
      }),
    });
    appStatus = await api("/api/v1/status");
    modelConnection = appStatus.model_connection || null;
    renderTopologyBadge();
    renderModelStatus();
    renderRunningSettings();
    renderConnection();
    conversationRevision += 1;
    currentView = null;
    chatTranscript.replaceChildren();
    appendChatMessage("assistant", t("conversationReset"));
    renderCurrentView(false);
  } catch (error) {
    const message = error.payload?.message || error.message || t("reloadError");
    window.alert(message);
  } finally {
    if (reloadSettingsButton) reloadSettingsButton.disabled = false;
  }
}

function openSettingsModal() {
  if (!settingsDialog) return;
  if (appStatus?.setup_url && setupServerActiveBox && openSetupServerLink) {
    openSetupServerLink.href = appStatus.setup_url;
    setupServerActiveBox.hidden = false;
  } else if (setupServerActiveBox) {
    setupServerActiveBox.hidden = true;
  }
  settingsDialog.hidden = false;
}

function closeSettingsModal() {
  if (settingsDialog) settingsDialog.hidden = true;
}

async function copySettingsCommand() {
  if (!copySettingsCommandButton) return;
  const command = "scripts\\START.cmd";
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(command);
    }
  } catch (_error) {
    // Clipboard may be restricted in some environments
  }
  copySettingsCommandButton.textContent = t("commandCopied");
  setTimeout(() => {
    if (copySettingsCommandButton) {
      copySettingsCommandButton.textContent = t("copyCommand");
    }
  }, 2000);
}

const CAPABILITY_STORAGE_KEY = "folderhome.capability_info_open";

function getStoredCapabilityState() {
  try {
    return window.sessionStorage.getItem(CAPABILITY_STORAGE_KEY) === "true";
  } catch (_error) {
    return false;
  }
}

function setStoredCapabilityState(isOpen) {
  try {
    window.sessionStorage.setItem(CAPABILITY_STORAGE_KEY, String(isOpen));
  } catch (_error) {
    // SessionStorage may be restricted in some environments
  }
}

function setCapabilityExpanded(expanded, { persist = true } = {}) {
  if (!capabilityGrid || !capabilityInfoButton) return;
  const isExpanded = Boolean(expanded);
  if (typeof capabilityInfoButton.setAttribute === "function") {
    capabilityInfoButton.setAttribute("aria-expanded", String(isExpanded));
    const labelKey = isExpanded ? "capabilityInfoHide" : "capabilityInfoShow";
    capabilityInfoButton.setAttribute("aria-label", t(labelKey));
    capabilityInfoButton.setAttribute("title", t(labelKey));
  }
  capabilityGrid.hidden = !isExpanded;
  if (persist) {
    setStoredCapabilityState(isExpanded);
  }
  if (isExpanded) {
    renderCapabilities();
  }
}

function toggleCapabilityInfo() {
  if (!capabilityInfoButton) return;
  const isExpanded = typeof capabilityInfoButton.getAttribute === "function"
    ? capabilityInfoButton.getAttribute("aria-expanded") === "true"
    : false;
  setCapabilityExpanded(!isExpanded);
}

function initCapabilityInfo() {
  const isOpen = getStoredCapabilityState();
  if (isOpen) {
    setCapabilityExpanded(true, { persist: false });
  } else {
    setCapabilityExpanded(false, { persist: false });
  }
}

function renderCapabilities() {
  if (!capabilityItems.length || !capabilityGrid) return;
  const cards = capabilityItems.map((item) => {
    const card = document.createElement("article");
    card.className = "capability-card";
    card.dataset.status = item.surface_status;
    card.append(textElement("strong", capabilityTitles[language]?.[item.capability_id] || item.title));
    let statusKey;
    if (item.surface_status === "interactive_read_only") {
      statusKey = "directUse";
    } else if (item.surface_status === "agent_guided") {
      statusKey = "agentUse";
    } else if (item.surface_status === "planning_only") {
      statusKey = "planningOnly";
    } else if (item.surface_status === "not_connected") {
      statusKey = "notConnected";
    } else {
      statusKey = "notConnected";
    }
    card.append(textElement("small", t(statusKey)));
    return card;
  });
  capabilityGrid.replaceChildren(...cards);
}

function renderCurrentView(scroll = true) {
  if (!currentView) {
    resultContent.replaceChildren();
    resultSection.hidden = true;
    return;
  }
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
        cards.push(renderRecipeReview(recipe));
      }
      for (const step of plan.steps || []) {
        const card = document.createElement("article");
        card.className = "result-card plan-card";
        card.append(textElement("small", t("proposedWorkflow"), "card-label"));
        card.append(textElement("h3", step.workflow_id));
        card.append(textElement("p", step.goal));
        if (step.execution_envelope) {
          renderCalendarChangePreview(card, step.execution_envelope.domain_plan);
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
            : outcome?.plan_invalidated
            ? t(outcome.plan_invalidated === "stale" ? "recipePlanUnavailable" : "recipeClosed")
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
              : t(recipe?.schema === "folderhome.recipe-stage-plan.v1"
                ? "recipeStageConfirm" : executionReady ? "confirmExecute" : "confirmPlan"),
          "button primary",
        );
        button.type = "button";
        button.disabled = Boolean(outcome) || conversationResetPending
          || Boolean(plan.approval_context?.run_id && recipeRunView.busy);
        if (!outcome) {
          button.addEventListener("click", () => confirmPlan(plan, button).catch(showError));
        }
        approvalCard.append(button);
        if (outcome?.recipe_execution?.status === "aborted") {
          approvalCard.append(textElement("p", recipeOutcomeText(outcome.recipe_execution)));
        }
        if (outcome?.result_delivery_incomplete) {
          approvalCard.append(textElement("p", t("recipeDeliveryIncomplete"), "hint"));
        }
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

function renderCalendarChangePreview(card, domain) {
  if (!domain?.previous_event || !["update", "delete"].includes(domain.operation)) return;
  card.append(textElement("strong", t(domain.operation === "delete" ? "calendarPlanDelete" : "calendarPlanUpdate")));
  const table = document.createElement("table");
  table.className = "calendar-change-table";
  const header = document.createElement("tr");
  for (const label of ["", t("calendarBefore"), t("calendarAfter")]) header.append(textElement("th", label));
  table.append(header);
  for (const [field, label] of Object.entries({title: "calendarTitle", start: "calendarStart", end: "calendarEnd",
    timezone: "calendarTimezone", all_day: "calendarAllDay", location: "calendarLocation", reminders: "calendarReminders"})) {
    const row = document.createElement("tr");
    row.append(textElement("th", t(label)));
    for (const event of [domain.previous_event, domain.replacement]) {
      const value = event?.[field];
      row.append(textElement("td", value == null ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value)));
    }
    table.append(row);
  }
  card.append(table);
}

function renderCalendarEditors(card, item) {
  if (item.status !== "executed" || item.profile_id !== profileSelect.value || !item.evidence?.calendar_edit_context) return;
  const versions = item.evidence?.event_versions;
  if (!Array.isArray(versions)) return;
  const generation = resultsRequestVersion;
  versions.forEach((version, versionIndex) => {
    if (version?.schema !== "folderhome.google-calendar-event-version.v1" || version.event?.profile_id !== item.profile_id) return;
    const details = document.createElement("details");
    details.className = "calendar-editor";
    details.append(textElement("summary", `${t("calendarEdit")}: ${version.event.title}`));
    const form = document.createElement("form");
    const fields = {};
    for (const [name, label] of Object.entries({title: "calendarTitle", start: "calendarStart", end: "calendarEnd",
      timezone: "calendarTimezone", all_day: "calendarAllDay", location: "calendarLocation", reminders: "calendarReminders"})) {
      const wrapper = document.createElement("label"), input = document.createElement("input");
      input.name = name;
      input.type = name === "all_day" ? "checkbox" : "text";
      if (name === "all_day") input.checked = version.event.all_day;
      else input.value = name === "reminders" ? (version.event.reminders || []).map(value => value.minutes_before).join(", ") : version.event[name] || "";
      input.required = ["title", "start", "end", "timezone"].includes(name);
      input.maxLength = name === "reminders" ? 100 : 8192;
      if (name === "all_day") {
        wrapper.className = "checkbox";
        wrapper.append(input, textElement("span", t(label)));
      } else {
        wrapper.append(textElement("span", t(label)), input);
      }
      form.append(wrapper);
      fields[name] = input;
    }
    form.append(textElement("p", t("calendarDateHelp")));
    const update = textElement("button", t("calendarPlanUpdate"), "button secondary");
    update.type = "submit";
    const deletion = textElement("button", t("calendarPlanDelete"), "button secondary");
    deletion.type = "button";
    const status = textElement("p", "");
    status.setAttribute("role", "status");
    form.append(update, deletion, status);
    let revision = 0, pending = false;
    form.addEventListener("input", () => { revision += 1; });
    form.addEventListener("change", () => { revision += 1; });
    const current = () => form.isConnected && generation === resultsRequestVersion && profileSelect.value === item.profile_id;
    async function prepare(operation) {
      if (pending || conversationResetPending || !current()) return;
      pending = true;
      update.disabled = deletion.disabled = true;
      const requestedRevision = revision, requestedLanguage = language, requestedConversation = conversationRevision;
      status.textContent = "";
      try {
        let changes = {};
        if (operation === "update") {
          const reminderText = fields.reminders.value.trim();
          if (reminderText && !/^\d+(\s*,\s*\d+){0,4}$/.test(reminderText)) throw new Error("Invalid reminders");
          changes = {title: fields.title.value, start: fields.start.value,
            end: fields.end.value || null, timezone: fields.timezone.value,
            all_day: fields.all_day.checked, location: fields.location.value || null,
            reminders: reminderText ? reminderText.split(",").map(value => ({
              schema: "folderhome.calendar-reminder.v1", method: "popup", minutes_before: Number(value.trim()),
            })) : []};
        }
        const response = await api("/api/v1/agent/calendar/plan", {method: "POST", body: JSON.stringify({
          schema: "folderhome.calendar-event-edit-request.v1", profile_id: item.profile_id,
          execution_id: item.execution_id, version_index: versionIndex, operation, changes, language: requestedLanguage,
        })});
        if (!current() || revision !== requestedRevision || language !== requestedLanguage || conversationRevision !== requestedConversation || response.plan?.profile_id !== item.profile_id) return;
        showAgent({agent: {response_text: response.plan.summary, tool_events: [], proposed_plans: [response.plan]}});
      } catch (_error) {
        if (current() && revision === requestedRevision) status.textContent = t("calendarEditFailure");
      } finally {
        pending = false;
        update.disabled = deletion.disabled = false;
      }
    }
    form.addEventListener("submit", event => {event.preventDefault(); return prepare("update");});
    deletion.addEventListener("click", () => prepare("delete"));
    details.append(form);
    card.append(details);
  });
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
    if (typeof setPanelExpanded === "function") setPanelExpanded(resultsSection, false);
    return;
  }
  if (typeof setPanelExpanded === "function") setPanelExpanded(resultsSection, true);
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "result-card";
    const status = item.status === "uncertain" ? t("executionUncertainTitle") : item.status;
    card.append(textElement("h3", `${item.workflow_id} · ${status}`));
    card.append(textElement("p", `${item.executed_at} · ${(item.side_effects || []).join(", ")}`));
    if (item.status === "uncertain") renderUncertainResult(card, item);
    else renderCalendarMutation(card, item.evidence?.confirmed_mutation);
    renderCalendarVersions(card, item.evidence?.event_versions);
    renderCalendarEditors(card, item);
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
  if (profileSelect.value !== plan.profile_id || conversationResetPending) return;
  if (plan.approval_context?.run_id && recipeRunView.busy) return;
  const requestedConversation = conversationRevision;
  button.disabled = true;
  if (planOutcomes[plan.plan_id]) return;
  planOutcomes[plan.plan_id] = { confirmation_pending: true, run_id: plan.approval_context?.run_id };
  if (plan.approval_context?.run_id) renderRecipeRuns();
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
      if (plan.approval_context?.run_id) renderRecipeRuns();
      throw error;
    }
  }
  planOutcomes[plan.plan_id] = { ...payload, run_id: plan.approval_context?.run_id };
  if (profileSelect.value !== plan.profile_id || conversationRevision !== requestedConversation) {
    if (plan.approval_context?.run_id && profileSelect.value === plan.profile_id) await loadRecipeRuns();
    return;
  }
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
  if (payload.recipe_run || plan.approval_context?.run_id) await loadRecipeRuns();
  if (payload.confirmation_response_missing) return;
  if (payload.execution_outcome_unknown) {
    // A failed list refresh must not hide the already displayed uncertainty.
    try { await loadResults(); } catch (_error) { /* Manual refresh remains available. */ }
  } else {
    await loadResults();
  }
}

function recipeOutcomeText(result) {
  const outcomes = result.outcomes || [];
  return t("recipeAborted", {
    completed: (result.completed_step_refs || result.executed_step_refs || []).join(", ") || "—",
    failed: (result.failed_step_refs || outcomes.filter(item => item.status === "failed").map(item => item.step_ref)).join(", ") || "—",
    pending: (result.not_attempted_step_refs || outcomes.filter(item => item.status === "not_attempted").map(item => item.step_ref)).join(", ") || "—",
  });
}

function renderRecipeReview(recipe) {
  const card = textElement("article", "", "result-card recipe-stage-card");
  const plan = recipe.plan;
  const staged = recipe.schema === "folderhome.recipe-stage-plan.v1";
  card.append(textElement("h3", plan.summary));
  card.append(textElement("p", t(staged ? "recipeStageReview" : "recipeReview")));
  const bindings = staged ? plan.approval_context?.result_bindings || [] : [];
  if (bindings.length) card.append(textElement("h4", t("recipeBindings")));
  for (const binding of bindings) {
    const row = textElement("div", "", "recipe-binding");
    row.append(textElement("strong", `${binding.from_step} → ${binding.to_step}.${binding.target_field}`));
    row.append(textElement("p", t("recipeBindingSource", {
      step: binding.from_step, path: JSON.stringify(binding.source_path),
    })));
    row.append(textElement("pre", JSON.stringify(binding.value, null, 2)));
    row.append(textElement("small", t("recipeBindingEvidence", {id: binding.source_execution_id})));
    card.append(row);
  }
  return card;
}

function recipeContext() {
  return {profile: profileSelect.value, language, revision: conversationRevision, view: recipeRunView};
}

function recipeContextCurrent(context) {
  return context.view === recipeRunView && context.profile === profileSelect.value
    && context.language === language && context.revision === conversationRevision
    && !conversationResetPending;
}

function resetRecipeControls() {
  recipeRunView = {runs: [], busy: null, readVersion: 0, readFailed: false, message: null};
  recipeCatalogVersion += 1;
  recipeItems = [];
  recipeSelect.replaceChildren();
  renderRecipeSelection();
  renderRecipeRuns();
}

function renderRecipeRuns() {
  const view = recipeRunView;
  refreshRecipeRunsButton.disabled = Boolean(view.busy) || conversationResetPending;
  const cards = [];
  if (view.message) cards.push(textElement("p", t(view.message), "hint"));
  if (view.readFailed) cards.push(textElement("p", t("recipeRunsError"), "hint"));
  for (const run of view.runs) {
    if (run.profile_id !== profileSelect.value) continue;
    const card = textElement("article", "", "result-card recipe-run-card");
    const recipe = recipeItems.find(item => item.recipe_id === run.recipe_id);
    card.append(textElement("h4", recipe?.title || run.recipe_id));
    const known = ["ready", "awaiting_approval", "preparing", "running", "completed", "aborted", "closed"].includes(run.status);
    card.append(textElement("strong", t(`recipeState_${known ? run.status : "unknown"}`)));
    card.append(textElement("p", t("recipeProgress", {steps: (run.completed_step_refs || []).join(", ") || "—"})));
    card.append(textElement("small", `${run.profile_id} · ${run.run_id}`));
    const controls = textElement("div", "", "recipe-controls");
    const addAction = (action, label) => {
      const button = textElement("button", t(label), "button secondary");
      button.type = "button";
      button.disabled = Boolean(view.busy) || view.readFailed || conversationResetPending
        || recipeRunConfirmationPending(run.run_id);
      button.addEventListener("click", () => recipeRunAction(action, run.run_id));
      controls.append(button);
    };
    if (["ready", "awaiting_approval"].includes(run.status)) {
      addAction("next", run.status === "ready" ? "recipeNext" : "recipeReviewPending");
    }
    if (known && !["running", "preparing"].includes(run.status)) addAction("close", "recipeClose");
    card.append(controls);
    cards.push(card);
  }
  if (!cards.length) cards.push(textElement("p", t(view.reading ? "recipeRunsLoading" : "recipeRunsEmpty"), "hint"));
  recipeRunsContent.setAttribute("aria-busy", String(Boolean(view.busy || view.reading)));
  recipeRunsContent.replaceChildren(...cards);
  const runsForProfile = (view.runs || []).filter(r => r.profile_id === profileSelect.value);
  const runsPanel = document.querySelector(".recipe-runs");
  if (runsPanel && typeof setPanelExpanded === "function") {
    setPanelExpanded(runsPanel, runsForProfile.length > 0);
  }
}

function recipeRunConfirmationPending(runId) {
  return Object.values(planOutcomes).some(outcome => outcome.run_id === runId && outcome.confirmation_pending);
}

async function loadRecipeRuns() {
  const context = recipeContext(), view = context.view;
  if (!context.profile || conversationResetPending) return;
  const version = ++view.readVersion;
  view.reading = true;
  renderRecipeRuns();
  try {
    const payload = await api(`/api/v1/agent/recipes/runs?profile_id=${encodeURIComponent(context.profile)}`);
    if (!recipeContextCurrent(context) || version !== view.readVersion) return;
    if (payload.profile_id !== context.profile || !Array.isArray(payload.runs)) throw new Error("Invalid run list");
    view.runs = payload.runs.filter(run => run.profile_id === context.profile);
    view.readFailed = false;
    for (const plan of currentView?.payload?.agent?.proposed_plans || []) {
      const runId = plan.approval_context?.run_id;
      if (!runId || plan.profile_id !== context.profile || planOutcomes[plan.plan_id]) continue;
      const state = view.runs.find(run => run.run_id === runId);
      if (state?.status !== "awaiting_approval" || state.pending_plan_id !== plan.plan_id) {
        planOutcomes[plan.plan_id] = {plan_invalidated: "stale"};
      }
    }
    renderCurrentView(false);
  } catch (_error) {
    if (!recipeContextCurrent(context) || version !== view.readVersion) return;
    view.readFailed = true;
  }
  view.reading = false;
  renderRecipeRuns();
}

async function recipeRunAction(action, runId) {
  const context = recipeContext(), view = context.view;
  const run = view.runs.find(item => item.run_id === runId && item.profile_id === context.profile);
  if (!run || !recipeContextCurrent(context) || view.busy || view.readFailed) return;
  if (recipeRunConfirmationPending(runId)) return;
  if (action === "next" && !["ready", "awaiting_approval"].includes(run.status)) return;
  if (!["next", "close"].includes(action) || ["running", "preparing"].includes(run.status)) return;
  view.busy = runId;
  view.message = null;
  view.readVersion += 1;
  renderRecipeRuns();
  renderRecipeSelection();
  renderCurrentView(false);
  try {
    const payload = await api(`/api/v1/agent/recipes/${action}`, {method: "POST", body: JSON.stringify({
      schema: `folderhome.local-recipe-${action}-request.v1`, profile_id: context.profile, run_id: runId,
    })});
    if (!recipeContextCurrent(context)) return;
    if (action === "next") {
      if (payload.plan?.profile_id !== context.profile || payload.run?.run_id !== runId) throw new Error("Invalid section");
      showAgent({agent: {response_text: payload.plan.summary, tool_events: [],
        proposed_plans: [payload.plan], proposed_recipes: [payload]}});
    } else {
      if (payload.recipe_run?.run_id !== runId) throw new Error("Invalid closed run");
      if (run.pending_plan_id && !planOutcomes[run.pending_plan_id]) {
        planOutcomes[run.pending_plan_id] = {plan_invalidated: true};
      }
      for (const plan of currentView?.payload?.agent?.proposed_plans || []) {
        if (plan.approval_context?.run_id === runId && !planOutcomes[plan.plan_id]) {
          planOutcomes[plan.plan_id] = {plan_invalidated: true};
        }
      }
      view.runs = view.runs.filter(item => item.run_id !== runId);
      renderCurrentView(false);
    }
  } catch (_error) {
    if (recipeContextCurrent(context)) view.message = "recipeActionError";
  } finally {
    if (view === recipeRunView) {
      view.busy = null;
      renderRecipeRuns();
      renderRecipeSelection();
      renderCurrentView(false);
    }
    // A completed POST may have changed the server after A→B→A or a language change.
    // Read the currently visible profile anew; never restore its old proposal.
    if (context.profile === profileSelect.value) await loadRecipeRuns();
  }
}

async function loadRecipes() {
  const context = recipeContext();
  const profileId = context.profile;
  const requestedLanguage = context.language;
  const version = ++recipeCatalogVersion;
  if (!profileId) return;
  const payload = await api(`/api/v1/agent/recipes?profile_id=${encodeURIComponent(profileId)}&language=${requestedLanguage}`);
  if (!recipeContextCurrent(context) || version !== recipeCatalogVersion) return;
  const previousSelection = recipeSelect.value;
  recipeItems = payload.recipes || [];
  recipeSelect.replaceChildren();
  for (const item of recipeItems) {
    const option = document.createElement("option");
    option.value = item.recipe_id;
    option.textContent = item.title;
    recipeSelect.append(option);
  }
  if (recipeItems.some(item => item.recipe_id === previousSelection)) recipeSelect.value = previousSelection;
  renderRecipeSelection();
  renderRecipeRuns();
}

function renderRecipeSelection() {
  const selected = recipeItems.find((item) => item.recipe_id === recipeSelect.value);
  prepareRecipeButton.disabled = !selected?.available || Boolean(recipeRunView.busy) || conversationResetPending;
  prepareRecipeButton.textContent = t(selected?.approval_mode === "per_section" ? "recipePrepareSection" : "recipePrepare");
  recipeHint.textContent = !selected ? t("recipeEmpty") : selected.available
    ? `${selected.summary} ${t(selected.approval_mode === "per_section" ? "recipeStageHint" : "recipeHint")}`
    : selected.unavailable_reason
      ? `${t("recipeUnavailable")} ${selected.unavailable_reason}`
      : t("recipeUnavailable");
  // Journeys that cannot run here yet (missing resources or executors) stay out of the way:
  // the panel collapses; the user can still open it to see what is missing.
  const panel = recipeSelect && typeof recipeSelect.closest === "function"
    ? recipeSelect.closest(".collapsible-panel") : null;
  if (panel && recipeItems.length > 0 && !recipeItems.some((item) => item.available)) {
    setPanelExpanded(panel, false);
  }
}

async function prepareRecipe(event) {
  event.preventDefault();
  const selected = recipeItems.find((item) => item.recipe_id === recipeSelect.value);
  const context = recipeContext(), view = context.view;
  if (!selected?.available || !recipeContextCurrent(context) || view.busy) return;
  const profileId = context.profile;
  view.busy = "new";
  view.readVersion += 1;
  renderRecipeRuns();
  prepareRecipeButton.disabled = true;
  try {
    const recipe = await api("/api/v1/agent/recipes/plan", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-recipe-plan-request.v1", profile_id: profileId,
        recipe_id: selected.recipe_id, language: context.language,
      }),
    });
    if (!recipeContextCurrent(context)) return;
    if (recipe.plan?.profile_id !== profileId) throw new Error("Invalid recipe profile");
    showAgent({ agent: {
      response_text: recipe.plan.summary, tool_events: [],
      proposed_plans: [recipe.plan], proposed_recipes: [recipe],
    } });
  } catch (_error) {
    if (recipeContextCurrent(context)) view.message = "recipeActionError";
  } finally {
    if (view === recipeRunView) {
      view.busy = null;
      renderRecipeSelection();
      renderRecipeRuns();
    }
    if (context.profile === profileSelect.value) await loadRecipeRuns();
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
  const requestedProfile = profileSelect.value, requestedConversation = conversationRevision;
  const requestedLanguage = language;
  appendChatMessage("user", value);
  messageInput.value = "";
  resultSection.setAttribute("aria-busy", "true");
  actionButtons.forEach((button) => { button.disabled = true; });
  const loadingView = { kind: "loading" };
  currentView = loadingView;
  renderCurrentView();
  try {
    const payload = await api("/api/v1/agent/chat", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-agent-chat-request.v1",
        profile_id: requestedProfile,
        message: value,
      }),
    });
    if (profileSelect.value !== requestedProfile || conversationRevision !== requestedConversation || language !== requestedLanguage) return;
    showAgent(payload);
    await loadRecipeRuns();
  } finally {
    if (currentView === loadingView) {
      currentView = null;
      renderCurrentView(false);
    }
    resultSection.setAttribute("aria-busy", "false");
    actionButtons.forEach((button) => { button.disabled = false; });
    returnFocus?.focus({ preventScroll: true });
    if (profileSelect.value === requestedProfile && language !== requestedLanguage) await loadRecipeRuns();
  }
}

async function resetConversation() {
  if (conversationResetPending) return;
  conversationRevision += 1;
  conversationResetPending = true;
  const requestedProfile = profileSelect.value, requestedConversation = conversationRevision;
  currentView = null;
  renderCurrentView(false);
  resetRecipeControls();
  const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  actionButtons.forEach((button) => { button.disabled = true; });
  try {
    await api("/api/v1/agent/conversation/reset", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.local-agent-conversation-reset-request.v1",
        profile_id: requestedProfile,
      }),
    });
    if (profileSelect.value !== requestedProfile || conversationRevision !== requestedConversation) return;
    chatTranscript.replaceChildren();
    appendChatMessage("assistant", t("conversationReset"));
    currentView = null;
    renderCurrentView(false);
  } finally {
    conversationResetPending = false;
    renderRecipeSelection();
    renderRecipeRuns();
    loadRecipes().catch(showError);
    await loadRecipeRuns();
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
  appStatus = status;
  for (const profile of profiles.profiles) {
    const option = document.createElement("option");
    option.value = profile.profile_id;
    option.textContent = profile.display_name;
    profileSelect.append(option);
  }
  processAccountName = status.process_identity?.account_name || "";
  modelConnection = status.model_connection || null;
  connectionStatus = "ready";
  capabilityItems = capabilities.capabilities || [];
  executorItems = Object.fromEntries(
    (executors.workflows || []).map((item) => [item.workflow_id, item]),
  );
  renderRuntimeAccount();
  renderTopologyBadge();
  renderModelStatus();
  renderRunningSettings();
  renderConnection();
  renderCapabilities();
  initCollapsiblePanels();
  await loadResults();
  await loadRecipes();
  await loadRecipeRuns();
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
  conversationRevision += 1;
  resetRecipeControls();
  resetSchedulerControl();
  schedulerAction("status");
  currentView = null;
  renderCurrentView(false);
  chatTranscript.replaceChildren();
  resultsRequestVersion += 1;
  resultsContent.replaceChildren();
  resultsSection.hidden = true;
  prepareRecipeButton.disabled = true;
  loadResults().catch(showError);
  loadRecipes().catch(showError);
  loadRecipeRuns();
});
refreshRecipeRunsButton.addEventListener("click", () => {
  recipeRunView.message = null;
  loadRecipeRuns();
});
recipeSelect.addEventListener("change", renderRecipeSelection);
document.querySelector("#recipe-form").addEventListener("submit", (event) => {
  prepareRecipe(event).catch(showError);
});
newConversationButton.addEventListener("click", () => {
  resetConversation().catch(showError);
});
if (reloadSettingsButton) {
  reloadSettingsButton.addEventListener("click", () => {
    reloadSettings().catch(showError);
  });
}
if (openSettingsButton) {
  openSettingsButton.addEventListener("click", openSettingsModal);
}
if (closeSettingsDialogButton) {
  closeSettingsDialogButton.addEventListener("click", closeSettingsModal);
}
if (settingsDialog) {
  settingsDialog.addEventListener("click", (event) => {
    if (event.target === settingsDialog) closeSettingsModal();
  });
}
if (copySettingsCommandButton) {
  copySettingsCommandButton.addEventListener("click", () => {
    copySettingsCommand().catch(showError);
  });
}
if (capabilityInfoButton) {
  capabilityInfoButton.addEventListener("click", toggleCapabilityInfo);
}
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
initCapabilityInfo();
initCollapsiblePanels();
bootstrap().catch((error) => {
  if (error instanceof LocalRequestError && (error.status === 401 || error.status === 403)) {
    connectionStatus = "blocked";
  } else {
    connectionStatus = "disconnected";
  }
  renderConnection();
  renderBoundary();
  renderModelStatus();
  showError(error);
});
