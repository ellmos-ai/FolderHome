const token = new URLSearchParams(window.location.search).get("token") || "";

const translations = {
  en: {
    subtitle: "Local setup",
    eyebrow: "Installer",
    title: "Set up FolderHome",
    lead: "This program is the only place that writes FolderHome configuration. The app itself never changes it. Nothing is written before you confirm the exact plan.",
    profilesTitle: "1. Profiles",
    profilesHint: "A profile organises documents inside this operating system account; it is not an access boundary. Every folder, rule and calendar account below binds to one of these profiles.",
    profilesDir: "Profile folder",
    profilesEmpty: "This folder holds no profiles yet. Take the shipped examples as a starting point, or begin with an empty list and add your own.",
    profilesTakeExamples: "Take the examples",
    profilesStartEmpty: "Start empty",
    profileAdd: "+ Profile",
    profileId: "Profile id",
    profileName: "Display name",
    profileIdLocked: "The file name follows this id, so it stays as it is. Delete the profile to replace it.",
    profileDelete: "Delete profile",
    profileDeleteConfirm: "Delete the profile {name}? Its folders and calendar accounts go with it. The file is kept in a .deleted folder.",
    profileLast: "At least one profile has to remain.",
    profileRules: "Rules for this profile",
    householdRules: "Rules for everyone",
    householdHint: "These live in household.json and apply to every profile. A profile rule of the same key wins over them.",
    ruleAdd: "+ Rule",
    ruleKey: "Key",
    ruleValue: "Value",
    ruleScope: "Applies to",
    ruleArea: "Area",
    cascadeTitle: "Removed along with it:",
    profileTargets: "Profile files:",
    foldersTitle: "2. Folders",
    foldersHint: "Give each profile a folder per purpose. Source folders are read, output folders receive files. Leave a field empty to skip that purpose. A source purpose may list several folders; the first one is the default.",
    chooseButton: "Choose folder",
    dialogOpening: "Opening folder dialog...",
    dialogAlreadyOpen: "A folder dialog is already open. Please complete or close it first.",
    addSource: "+ another source",
    removeSource: "Remove",
    modelTitle: "3. Model",
    modelHint: "The provider is a start-up choice: the app reads the active preset when it starts. Network and data approvals stay command-line flags and are never written to a file.",
    presetFormTitle: "New or edited preset",
    presetName: "Preset name (optional)",
    presetSave: "Save as preset",
    presetActivate: "Activate",
    presetDelete: "Delete",
    presetActive: "active",
    presetNone: "No presets saved yet. The form below is used as it stands.",
    presetNameInvalid: "A preset name uses letters, digits, _ . - and at most 40 characters.",
    anthropicModel: "Anthropic model id",
    openaiModel: "OpenAI model id",
    openaiBaseUrl: "OpenAI base URL (optional)",
    providerLabel: "Provider",
    ollamaHost: "Ollama host",
    ollamaModel: "Ollama model id",
    bedrockModel: "Bedrock model id",
    awsRegion: "AWS region",
    gateHintFixture: "The deterministic fixture needs no approval and no network.",
    gateHintLoopback: "A model on this machine needs no approval, because nothing leaves the loopback interface.",
    gateHintRemote: "Start the app with --allow-network and --approve-sensitive-cloud-data for this provider.",
    subscriptionsTitle: "4. Subscriptions",
    subscriptionsHint: "Claude Code with a Claude subscription and the Codex CLI with a ChatGPT subscription can drive FolderHome as a tool: the agent is the brain, FolderHome is the tool. FolderHome needs no key of its own for this, and the provider above may stay fixture. Nothing here reads, stores or checks a subscription.",
    subscriptionsStep1: "Start the app with the command shown in section 9 after saving.",
    subscriptionsStep2: "Take the access URL from its start output and put it in place of the placeholder below.",
    subscriptionsStep3: "Run the command in Claude Code, or paste the block into ~/.codex/config.toml for Codex.",
    subscriptionsToken: "The token changes on every app start, so a stored editor entry goes stale with it. After a restart, put the new access URL in again.",
    copyButton: "Copy",
    copyDone: "Copied.",
    copyFallback: "Selected — copy it with Ctrl+C.",
    keysTitle: "5. API keys",
    keysHint: "Hosted providers need a key. The installer stores it in a .env file next to launch.json and never shows it again; on Windows only your user account protects that file. Leave a field empty to keep the stored key.",
    keyStored: "A key is stored.",
    keyMissing: "No key stored.",
    keyRemove: "Remove key",
    keyPendingRemoval: "Will be removed when you save.",
    runtimeTitle: "6. Runtime",
    stateDir: "App state folder",
    stateDirHelp: "Without a saved launch.json, setup suggests a separate state subfolder of the configuration folder. A saved launch path is kept. Changing this path does not move or copy existing data: the app uses the selected folder on its next start. To keep existing state, select its current folder; profile and state folders must not overlap. Back up existing data before a manual move.",
    portLabel: "Port",
    outsideHome: "I confirm folders outside my user folder",
    summaryTitle: "9. Summary and save",
    schedulerTitle: "8. Regular folder checks",
    schedulerHint: "Prepare one profile at a time. Saving writes local configuration only: no job is registered and no service starts. Registration and execution require separate approval in the app. Existing registrations cannot be changed here.",
    schedulerEnable: "Edit scheduler settings for this profile",
    schedulerProfile: "Profile",
    schedulerSource: "Which folder should be checked?",
    schedulerTarget: "Destination for later filing proposals",
    schedulerArea: "Document area",
    schedulerInterval: "Check every (minutes, 5–1440)",
    schedulerStart: "First check (ISO date and time with UTC offset)",
    schedulerTimezone: "Time zone (must match the UTC offset)",
    schedulerRecursive: "Include subfolders",
    schedulerRead: "Allow local reading of these documents",
    schedulerLoadError: "Saved scheduler settings could not be loaded. Check the existing files before replacing them; this section is disabled.",
    schedulerSaved: "Scheduler configuration saved. No job registered and no service started. The saved request is available below for a separate registration preview.",
    checkButton: "Check",
    saveButton: "Save",
    saveNote: "Nothing is saved automatically. Check first, then save; saving writes the profile files, resources.json and launch.json.",
    accountLine: "Operating system account {account} · configuration in {dir}",
    checkOk: "The plan is valid. These files will be written:",
    checkFailed: "Please correct this first:",
    overwriteHint:
      "Saving merges folder bindings and preserves custom resources and stricter "
      + "permissions. Existing JSON configuration files receive dated backups when changed; "
      + "the secret .env file is never backed up.",
    savedTitle: "Written. Start FolderHome with:",
    backupNote: "The previous version was kept as a .bak file.",
    requestFailed: "The setup service refused the request ({status}).",
    calendarTitle: "7. Calendar",
    calendarHint: "The app loads these files through launch.json as private, profile-bound resources. Select a calendar.source folder explicitly. Local calendar, optional ICS export and the separately gated Google connector are supported; configuring an account grants no network permission. There is no Outlook backend. Unchanged fields preserve existing file references. Editing this section writes setup-owned copies, shown in the preview; custom source files stay untouched.",
    calendarEnable: "Write calendar configuration",
    calendarLoadError: "The saved calendar configuration could not be loaded. Check its files before replacing it.",
    calendarBackend: "Default backend",
    calendarTimezone: "Default time zone",
    calendarDirectory: "UpToday ICS folder",
    calendarAddAccount: "+ another account",
    calendarAccount: "Account",
    calendarProfile: "Profile",
    calendarCredential: "Connector reference (google only)",
    googleBindingHint: "Google: use provider google-calendar, revision v3 and a concrete calendar ID, not primary. Supply an existing authorized_user OAuth file with calendar.events permission, never paste its contents here. Setup checks paths only, not token validity. Private paths must be outside document/output folders; the OAuth file must also be outside setup/profile folders. Existing bindings stay unchanged unless explicitly selected below; conflicting existing bindings require a separate registry review.",
    googleCredentialFile: "Existing private OAuth JSON file (absolute path)",
    googleLedgerDir: "Existing private receipt folder (absolute path; no database created by setup)",
    googleBind: "Explicitly bind these private Google resources (no login or calendar access)",
    googleExecutionHint: "Install FolderHome with the calendar extra. Later start the app with --approve-calendar-write and confirm the exact calendar plan separately. Saving setup does neither. Initial Google login and live acceptance remain separate steps.",
    googleLookup: "Read calendar ID from Google (uses the OAuth file above)",
    googleLookupHint: "Optional: start setup serve with --approve-calendar-read and use an existing grant containing calendar.calendars.readonly. This button reads calendar metadata only (possibly refreshing the token once); it does not log in, save files or grant calendar writes. Save new profiles first. The returned ID changes only this form until you review and save setup.",
    googleLookupFailed: "Calendar ID could not be verified. Check the private file, metadata scope and selected account.",
    cloudTitle: "Cloud variant",
    cloudHint: "In the AWS or browser variant there are no local output folders. There the results view is the delivery path: files are downloaded into the download folder of the browser.",
  },
  de: {
    subtitle: "Lokale Einrichtung",
    eyebrow: "Einrichtung",
    title: "FolderHome einrichten",
    lead: "Dieses Programm ist der einzige Ort, der FolderHome-Konfiguration schreibt. Die App selbst ändert sie nie. Es wird nichts geschrieben, bevor du genau diesen Plan bestätigst.",
    profilesTitle: "1. Profile",
    profilesHint: "Ein Profil organisiert Dokumente innerhalb dieses Betriebssystemkontos; es ist keine Zugriffsgrenze. Jeder Ordner, jede Regel und jedes Kalenderkonto weiter unten hängt an einem dieser Profile.",
    profilesDir: "Profilordner",
    profilesEmpty: "In diesem Ordner liegt noch kein Profil. Übernimm die mitgelieferten Beispiele als Ausgangspunkt oder beginne mit einer leeren Liste.",
    profilesTakeExamples: "Beispiele übernehmen",
    profilesStartEmpty: "Leer beginnen",
    profileAdd: "+ Profil",
    profileId: "Profil-ID",
    profileName: "Anzeigename",
    profileIdLocked: "Der Dateiname folgt dieser ID, deshalb bleibt sie stehen. Zum Ersetzen das Profil löschen.",
    profileDelete: "Profil löschen",
    profileDeleteConfirm: "Profil {name} löschen? Seine Ordner und Kalenderkonten gehen mit. Die Datei bleibt in einem .deleted-Ordner erhalten.",
    profileLast: "Mindestens ein Profil muss bestehen bleiben.",
    profileRules: "Regeln dieses Profils",
    householdRules: "Regeln für alle",
    householdHint: "Diese stehen in household.json und gelten für jedes Profil. Eine Profilregel mit demselben Schlüssel gewinnt.",
    ruleAdd: "+ Regel",
    ruleKey: "Schlüssel",
    ruleValue: "Wert",
    ruleScope: "Gilt für",
    ruleArea: "Bereich",
    cascadeTitle: "Wird mitentfernt:",
    profileTargets: "Profildateien:",
    foldersTitle: "2. Ordner",
    foldersHint: "Gib jedem Profil je Zweck einen Ordner. Quellordner werden gelesen, Ausgabeordner nehmen Dateien auf. Ein leeres Feld lässt den Zweck aus. Ein Quellzweck darf mehrere Ordner haben; der erste ist der Standard.",
    chooseButton: "Ordner wählen",
    dialogOpening: "Ordnerdialog öffnet sich...",
    dialogAlreadyOpen: "Es ist bereits ein Ordnerdialog geöffnet. Bitte wähle dort einen Ordner oder schließe das Dialogfenster.",
    addSource: "+ weitere Quelle",
    removeSource: "Entfernen",
    modelTitle: "3. Modell",
    modelHint: "Der Provider ist eine Startentscheidung: Die App liest beim Start das aktive Preset. Netz- und Datenfreigaben bleiben Kommandozeilen-Schalter und werden nie in eine Datei geschrieben.",
    presetFormTitle: "Neues oder bearbeitetes Preset",
    presetName: "Preset-Name (optional)",
    presetSave: "Als Preset speichern",
    presetActivate: "Aktivieren",
    presetDelete: "Löschen",
    presetActive: "aktiv",
    presetNone: "Noch keine Presets gespeichert. Es gilt das Formular darunter.",
    presetNameInvalid: "Ein Preset-Name besteht aus Buchstaben, Ziffern, _ . - und höchstens 40 Zeichen.",
    anthropicModel: "Anthropic-Modell-ID",
    openaiModel: "OpenAI-Modell-ID",
    openaiBaseUrl: "OpenAI-Basis-URL (optional)",
    providerLabel: "Provider",
    ollamaHost: "Ollama-Host",
    ollamaModel: "Ollama-Modell-ID",
    bedrockModel: "Bedrock-Modell-ID",
    awsRegion: "AWS-Region",
    gateHintFixture: "Das deterministische Fixture braucht keine Freigabe und kein Netz.",
    gateHintLoopback: "Ein Modell auf diesem Rechner braucht keine Freigabe, weil nichts die Loopback-Schnittstelle verlässt.",
    gateHintRemote: "Starte die App für diesen Provider mit --allow-network und --approve-sensitive-cloud-data.",
    subscriptionsTitle: "4. Abonnements",
    subscriptionsHint: "Claude Code mit Claude-Abo und die Codex-CLI mit ChatGPT-Abo können FolderHome als Werkzeug steuern: Der Agent ist das Gehirn, FolderHome ist das Werkzeug. FolderHome braucht dafür keinen eigenen Schlüssel, und der Provider oben darf fixture bleiben. Hier wird kein Abo gelesen, gespeichert oder geprüft.",
    subscriptionsStep1: "Starte die App mit dem Befehl, den Abschnitt 9 nach dem Speichern anzeigt.",
    subscriptionsStep2: "Nimm die Zugriffs-URL aus der Startausgabe und setze sie anstelle des Platzhalters unten ein.",
    subscriptionsStep3: "Führe den Befehl in Claude Code aus oder trage den Block für Codex in ~/.codex/config.toml ein.",
    subscriptionsToken: "Das Token wechselt bei jedem App-Start, ein hinterlegter Editor-Eintrag veraltet also mit ihm. Nach einem Neustart die neue Zugriffs-URL erneut eintragen.",
    copyButton: "Kopieren",
    copyDone: "Kopiert.",
    copyFallback: "Markiert — mit Strg+C kopieren.",
    keysTitle: "5. API-Schlüssel",
    keysHint: "Fremdgehostete Anbieter brauchen einen Schlüssel. Die Einrichtung legt ihn in einer .env-Datei neben launch.json ab und zeigt ihn nie wieder; unter Windows schützt ihn allein dein Benutzerkonto. Ein leeres Feld behält den hinterlegten Schlüssel.",
    keyStored: "Ein Schlüssel ist hinterlegt.",
    keyMissing: "Kein Schlüssel hinterlegt.",
    keyRemove: "Schlüssel entfernen",
    keyPendingRemoval: "Wird beim Speichern entfernt.",
    runtimeTitle: "6. Laufzeit",
    stateDir: "App-State-Ordner",
    stateDirHelp: "Ohne gespeicherte launch.json schlägt das Setup einen separaten Unterordner state im Konfigurationsordner vor. Ein gespeicherter Launch-Pfad bleibt erhalten. Eine Pfadänderung verschiebt oder kopiert keine vorhandenen Daten: Die App verwendet den gewählten Ordner beim nächsten Start. Wähle für den bisherigen Datenbestand dessen aktuellen Ordner; Profil- und State-Ordner dürfen sich nicht überlappen. Sichere vorhandene Daten vor einem manuellen Umzug.",
    portLabel: "Port",
    outsideHome: "Ich bestätige Ordner außerhalb meines Benutzerordners",
    summaryTitle: "9. Zusammenfassung und Speichern",
    schedulerTitle: "8. Regelmäßige Ordnerprüfung",
    schedulerHint: "Richte jeweils ein Profil ein. Speichern schreibt nur lokale Einstellungen: kein Job wird registriert, kein Dienst gestartet. Registrierung und Ausführung benötigen eine getrennte Freigabe in der App. Bestehende Registrierungen lassen sich hier nicht ändern.",
    schedulerEnable: "Scheduler-Einstellungen für dieses Profil bearbeiten",
    schedulerProfile: "Profil",
    schedulerSource: "Welchen Ordner prüfen?",
    schedulerTarget: "Ziel für spätere Ablagevorschläge",
    schedulerArea: "Dokumentbereich",
    schedulerInterval: "Prüfen alle (Minuten, 5–1440)",
    schedulerStart: "Erster Termin (ISO-Datum und Uhrzeit mit UTC-Versatz)",
    schedulerTimezone: "Zeitzone (muss zum UTC-Versatz passen)",
    schedulerRecursive: "Unterordner einbeziehen",
    schedulerRead: "Lokales Lesen dieser Dokumente erlauben",
    schedulerLoadError: "Die gespeicherten Scheduler-Einstellungen konnten nicht geladen werden. Prüfe die bestehenden Dateien vor dem Ersetzen; dieser Bereich ist gesperrt.",
    schedulerSaved: "Scheduler-Konfiguration gespeichert. Kein Job registriert, kein Dienst gestartet. Der gespeicherte Antrag steht unten für eine separate Registrierungsvorschau bereit.",
    checkButton: "Prüfen",
    saveButton: "Speichern",
    saveNote: "Es wird nichts automatisch gespeichert. Erst Prüfen, dann Speichern; das Speichern schreibt die Profildateien, resources.json und launch.json.",
    accountLine: "Betriebssystemkonto {account} · Konfiguration in {dir}",
    checkOk: "Der Plan ist gültig. Diese Dateien werden geschrieben:",
    checkFailed: "Bitte zuerst korrigieren:",
    overwriteHint:
      "Das Speichern führt Ordnerbindungen zusammen und erhält eigene Ressourcen "
      + "und strengere Rechte. Bestehende JSON-Konfigurationsdateien erhalten bei Änderungen "
      + "datierte Backups; die Geheimnisdatei .env wird niemals gesichert.",
    savedTitle: "Geschrieben. Starte FolderHome mit:",
    backupNote: "Die Vorversion wurde als .bak-Datei behalten.",
    requestFailed: "Der Einrichtungsdienst hat die Anfrage abgelehnt ({status}).",
    calendarTitle: "7. Kalender",
    calendarHint: "Die App lädt diese Dateien über launch.json als private, profilgebundene Ressourcen. Wähle ausdrücklich einen calendar.source-Ordner. Lokaler Kalender, optionaler ICS-Export und der getrennt freizugebende Google-Connector sind unterstützt; ein konfiguriertes Konto erteilt keine Netzwerkfreigabe. Ein Outlook-Backend gibt es nicht. Unveränderte Felder erhalten bestehende Dateiverweise. Änderungen in diesem Abschnitt schreiben Setup-eigene Kopien, die die Vorschau zeigt; benutzerdefinierte Quelldateien bleiben unangetastet.",
    calendarEnable: "Kalenderkonfiguration schreiben",
    calendarLoadError: "Die gespeicherte Kalenderkonfiguration konnte nicht geladen werden. Prüfe ihre Dateien, bevor du sie ersetzt.",
    calendarBackend: "Standard-Backend",
    calendarTimezone: "Standardzeitzone",
    calendarDirectory: "UpToday-ICS-Ordner",
    calendarAddAccount: "+ weiteres Konto",
    calendarAccount: "Konto",
    calendarProfile: "Profil",
    calendarCredential: "Connector-Referenz (nur google)",
    googleBindingHint: "Google: Provider google-calendar, Revision v3 und eine konkrete Kalender-ID statt primary verwenden. Eine vorhandene authorized_user-OAuth-Datei mit calendar.events-Recht angeben, ihren Inhalt niemals hier einfügen. Das Setup prüft nur Pfade, nicht die Token-Gültigkeit. Private Pfade müssen außerhalb von Dokument-/Ausgabeordnern liegen, die OAuth-Datei zusätzlich außerhalb von Setup-/Profilordnern. Bestehende Bindungen bleiben ohne ausdrückliche Auswahl unten unverändert; widersprüchliche Bindungen benötigen eine separate Registerprüfung.",
    googleCredentialFile: "Vorhandene private OAuth-JSON-Datei (absoluter Pfad)",
    googleLedgerDir: "Vorhandener privater Nachweisordner (absoluter Pfad; Setup erzeugt keine Datenbank)",
    googleBind: "Diese privaten Google-Ressourcen ausdrücklich binden (keine Anmeldung oder Kalenderabfrage)",
    googleExecutionHint: "FolderHome mit dem Kalenderextra installieren. Die App später mit --approve-calendar-write starten und den genauen Kalenderplan separat bestätigen. Das Speichern der Einrichtung erledigt beides nicht. Erste Google-Anmeldung und Live-Abnahme bleiben eigene Schritte.",
    googleLookup: "Kalender-ID bei Google lesen (verwendet die OAuth-Datei oben)",
    googleLookupHint: "Optional: setup serve mit --approve-calendar-read starten und eine vorhandene Zustimmung mit calendar.calendars.readonly verwenden. Dieser Knopf liest nur Kalendermetadaten, gegebenenfalls mit einmaliger Token-Erneuerung; er meldet sich nicht neu an, speichert keine Dateien und erteilt keine Kalender-Schreibrechte. Neue Profile zuerst speichern. Die gelesene ID ändert bis zur Prüfung und Speicherung nur dieses Formular.",
    googleLookupFailed: "Kalender-ID konnte nicht geprüft werden. Private Datei, Metadaten-Scope und ausgewähltes Konto prüfen.",
    cloudTitle: "Cloud-Variante",
    cloudHint: "In der AWS- oder Browser-Variante gibt es keine lokalen Ausgabeordner. Dort ist die Ergebnisansicht der Zustellweg: Dateien landen im Download-Ordner des Browsers.",
  },
};

let language = "en";
let state = null;
let checkedPlan = null;

const folderGrid = document.querySelector("#folder-grid");
const summary = document.querySelector("#summary");
const providerSelect = document.querySelector("#provider");
const saveButton = document.querySelector("#save");
const gateHint = document.querySelector("#gate-hint");
const saveNote = document.querySelector("#save-note");
const keyFields = document.querySelector("#key-fields");
// Names only; a value lives in the field until save and never in this object.
const keyRemovals = new Set();
const presetList = document.querySelector("#preset-list");
let presets = {};
const profileList = document.querySelector("#profile-list");
const householdRules = document.querySelector("#household-rules");
const profilesDir = document.querySelector("#profiles-dir");
let knownProfileIds = new Set();
const calendarAccounts = document.querySelector("#calendar-accounts");
const calendarEnabled = document.querySelector("#calendar-enabled");
let calendarDirty = false;
let activePreset = null;

function t(key, replacements = {}) {
  let value = translations[language][key] || translations.en[key] || key;
  for (const [name, replacement] of Object.entries(replacements)) {
    value = value.replace(`{${name}}`, String(replacement));
  }
  return value;
}

function textElement(tag, value, className = "") {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-FolderHome-Token", token);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers, credentials: "omit" });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload.message || t("requestFailed", { status: response.status });
    const err = new Error(message);
    err.status = response.status;
    throw err;
  }
  return payload;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === language));
  });
  if (state) {
    document.querySelector("#account-line").textContent = t("accountLine", {
      account: state.os_account,
      dir: state.config_dir,
    });
  }
  renderGateHint();
}

function renderGateHint() {
  const provider = providerSelect.value;
  if (provider === "fixture") {
    gateHint.textContent = t("gateHintFixture");
    return;
  }
  const host = document.querySelector("#ollama-host").value.trim();
  const loopback = provider === "ollama" && /^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(:|\/|$)/.test(host);
  gateHint.textContent = loopback ? t("gateHintLoopback") : t("gateHintRemote");
}

function invalidate() {
  saveButton.disabled = true;
  checkedPlan = null;
}

function getStoredCardState(cardId) {
  try {
    if (typeof sessionStorage !== "undefined") {
      return sessionStorage.getItem(`fh_setup_card_${cardId}`);
    }
  } catch (_e) {}
  return null;
}

function setStoredCardState(cardId, expanded) {
  try {
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(`fh_setup_card_${cardId}`, String(expanded));
    }
  } catch (_e) {}
}

function setCardExpanded(card, expanded) {
  if (!card) return;
  const cardId = card.dataset.cardId;
  const h2 = card.querySelector("h2");
  const head = card.querySelector(".card-head");
  const body = card.querySelector(".card-body");
  if (!h2 || !body) return;

  if (card.classList) card.classList.toggle("is-collapsed", !expanded);
  if (h2.setAttribute) h2.setAttribute("aria-expanded", String(expanded));
  if (head && head.setAttribute) head.setAttribute("aria-expanded", String(expanded));
  body.hidden = !expanded;
  if (cardId) setStoredCardState(cardId, expanded);
}

function setActiveCard(card) {
  if (!card) return;
  document.querySelectorAll(".card").forEach(c => {
    if (c.classList) c.classList.remove("is-active");
  });
  if (card.classList) card.classList.add("is-active");
  setCardExpanded(card, true);
}

function getCardForFieldOrText(text) {
  const str = String(text || "").toLowerCase();
  let targetId = "profiles";
  if (str.includes("außerhalb") || str.includes("abschnitt 6") || str.includes("outside_home") || str.includes("outside home") || str.includes("outside user folder")) targetId = "runtime";
  else if (str.includes("folder") || str.includes("source") || str.includes("target") || str.includes("path")) targetId = "folders";
  else if (str.includes("model") || str.includes("preset") || str.includes("ollama") || str.includes("bedrock") || str.includes("anthropic") || str.includes("openai") || str.includes("provider")) targetId = "model";
  else if (str.includes("key") || str.includes("api_key")) targetId = "keys";
  else if (str.includes("runtime") || str.includes("port") || str.includes("state_dir")) targetId = "runtime";
  else if (str.includes("calendar")) targetId = "calendar";
  else if (str.includes("scheduler")) targetId = "scheduler";
  else if (str.includes("profile") || str.includes("rule") || str.includes("household")) targetId = "profiles";

  return document.querySelector(`.card[data-card-id="${targetId}"]`);
}

function resolveElementForField(field, message = "") {
  if (!field && !message) return null;
  const f = String(field || "").trim();
  const m = String(message || "").toLowerCase();

  // Special case: outside home confirmation in section 6
  if (m.includes("außerhalb") || m.includes("abschnitt 6") || m.includes("outside_home") || m.includes("outside home") || m.includes("outside user folder")) {
    return document.querySelector("#outside-home");
  }

  // folders[index]
  const folderMatch = f.match(/^folders\[(\d+)\]/);
  const fg = typeof folderGrid !== "undefined" && folderGrid ? folderGrid : document.querySelector("#folder-grid");
  if (folderMatch && fg) {
    const idx = parseInt(folderMatch[1], 10);
    const inputs = [...fg.querySelectorAll("input")].filter((inp) => inp.value && inp.value.trim());
    if (inputs[idx]) return inputs[idx];
    const allInputs = fg.querySelectorAll("input");
    if (allInputs[idx]) return allInputs[idx];
    return fg;
  }
  if (f === "folders") {
    return (fg && fg.querySelector("input")) || fg || document.querySelector('.card[data-card-id="folders"]');
  }

  // model_presets[name]
  const presetMatch = f.match(/^model_presets\[([^\]]+)\]/);
  const pl = typeof presetList !== "undefined" && presetList ? presetList : document.querySelector("#preset-list");
  if (presetMatch) {
    const presetName = presetMatch[1];
    if (pl) {
      const row = pl.querySelector(`[data-preset-name="${presetName}"]`);
      if (row) return row;
      return pl;
    }
    return document.querySelector('.card[data-card-id="model"]');
  }

  // model fields
  if (f === "model_preset") return document.querySelector("#preset-name") || pl || document.querySelector('.card[data-card-id="model"]');
  if (f === "model.provider" || f === "model.model_provider" || f === "model") return document.querySelector("#provider");
  if (f === "model.ollama_host") return document.querySelector("#ollama-host");
  if (f === "model.ollama_model_id") return document.querySelector("#ollama-model-id");
  if (f === "model.bedrock_model_id") return document.querySelector("#bedrock-model-id");
  if (f === "model.aws_region") return document.querySelector("#bedrock-region");
  if (f === "model.anthropic_model_id") return document.querySelector("#anthropic-model-id");
  if (f === "model.openai_model_id") return document.querySelector("#openai-model-id");
  if (f === "model.openai_base_url") return document.querySelector("#openai-base-url");

  // runtime fields
  if (f === "port" || f === "runtime.port") return document.querySelector("#port");
  if (f === "state_dir" || f === "runtime.state_dir") return document.querySelector("#state-dir");
  if (f === "profiles_dir") return document.querySelector("#profiles-dir");

  // calendar fields
  if (f === "calendar.directory") return document.querySelector("#calendar-directory");
  if (f === "calendar.backend") return document.querySelector("#calendar-backend");
  if (f === "calendar.timezone") return document.querySelector("#calendar-timezone");
  if (f.startsWith("calendar")) return document.querySelector("#calendar-fields") || document.querySelector("#card-calendar");

  // scheduler fields
  if (f === "scheduler.source") return document.querySelector("#scheduler-source");
  if (f === "scheduler.target") return document.querySelector("#scheduler-target");
  if (f === "scheduler.interval_minutes") return document.querySelector("#scheduler-interval");
  if (f === "scheduler.start") return document.querySelector("#scheduler-start");
  if (f === "scheduler.timezone") return document.querySelector("#scheduler-timezone");
  if (f.startsWith("scheduler")) return document.querySelector("#scheduler-fields") || document.querySelector("#card-scheduler");

  // profiles / household
  const prl = typeof profileList !== "undefined" && profileList ? profileList : document.querySelector("#profile-list");
  const profileMatch = f.match(/^profiles\[(\d+)\]/);
  if (profileMatch && prl) {
    const idx = parseInt(profileMatch[1], 10);
    const cards = prl.querySelectorAll(".card, [data-profile-id]");
    if (cards[idx]) return cards[idx];
    return prl;
  }
  if (f === "profiles") return prl || document.querySelector('.card[data-card-id="profiles"]');
  const hr = typeof householdRules !== "undefined" && householdRules ? householdRules : document.querySelector("#household-rules");
  if (f.startsWith("household_rules")) return hr || document.querySelector('.card[data-card-id="profiles"]');

  // Direct ID match fallback
  const direct = document.querySelector(`#${f}`);
  if (direct) return direct;

  return null;
}

function clearValidationErrors() {
  document.querySelectorAll(".card").forEach((c) => {
    if (c.classList) c.classList.remove("has-error");
    const badge = c.querySelector(".card-error-badge");
    if (badge) badge.remove();
  });
  document.querySelectorAll("[aria-invalid='true']").forEach((el) => {
    if (el.removeAttribute) el.removeAttribute("aria-invalid");
    if (el.classList) el.classList.remove("is-invalid");
  });
  document.querySelectorAll(".is-invalid").forEach((el) => {
    if (el.classList) el.classList.remove("is-invalid");
  });
  document.querySelectorAll(".field-error-msg").forEach((el) => el.remove());
}

function expandCardForError(text) {
  const card = getCardForFieldOrText(text);
  if (card) {
    if (card.classList) card.classList.add("has-error");
    setCardExpanded(card, true);
    setActiveCard(card);
    let badge = card.querySelector(".card-error-badge");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "card-error-badge";
      badge.textContent = "1";
      const chevron = card.querySelector(".card-chevron");
      if (chevron && chevron.parentNode) {
        chevron.parentNode.insertBefore(badge, chevron);
      } else {
        const head = card.querySelector(".card-head");
        if (head) head.append(badge);
      }
    }
  }
  return card;
}

function jumpToError(field, message) {
  const element = resolveElementForField(field, message);
  if (element) {
    const card = (element.closest && element.closest(".card")) || getCardForFieldOrText(`${field} ${message}`);
    if (card) {
      setCardExpanded(card, true);
      setActiveCard(card);
    }
    if (element.scrollIntoView) {
      try { element.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (_) {}
    }
    if (element.focus) {
      try { element.focus(); } catch (_) {}
    }
    const highlightTarget = (element.closest && (element.closest(".field") || element.closest(".field-input") || element.closest(".checkbox"))) || element;
    if (highlightTarget && highlightTarget.classList) {
      highlightTarget.classList.add("is-highlight-target");
      if (typeof setTimeout === "function") {
        setTimeout(() => highlightTarget.classList.remove("is-highlight-target"), 2500);
      }
    }
    return;
  }
  expandCardForError(`${field} ${message}`);
}

function initCollapsibleCards() {
  const cards = document.querySelectorAll(".card[data-card-id]");
  cards.forEach((card, index) => {
    const cardId = card.dataset.cardId;
    if (cardId === "summary") return;

    const head = card.querySelector(".card-head");
    const h2 = card.querySelector("h2");
    if (!head || !h2) return;
    // initCollapsibleCards runs at load and again after the setup payload arrives;
    // a second pass must not add a second toggle (two toggles per click cancel out).
    if (card.dataset.collapsibleInit === "1") return;
    card.dataset.collapsibleInit = "1";

    const stored = getStoredCardState(cardId);
    let expanded = stored !== null ? stored === "true" : false; // start collapsed; expand on demand

    setCardExpanded(card, expanded);
    if (index === 0 && (stored === null || stored === "true") && card.classList) {
      card.classList.add("is-active");
    }

    const toggle = () => {
      const isCurrentlyExpanded = h2.getAttribute ? h2.getAttribute("aria-expanded") === "true" : true;
      const nextState = !isCurrentlyExpanded;
      setCardExpanded(card, nextState);
      if (nextState) {
        setActiveCard(card);
      }
    };

    head.addEventListener("click", toggle);
    head.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });

    card.addEventListener("focusin", (e) => {
      // Focus on the head itself (click, Tab) must not re-expand the card; only
      // work inside the body marks the card as the one in focus.
      if (head.contains(e.target)) return;
      setActiveCard(card);
    });
  });
}

async function pickFolder(input, button = null) {
  const originalText = button ? button.textContent : "";
  if (button) {
    if (button.setAttribute) button.setAttribute("aria-busy", "true");
    button.disabled = true;
    button.textContent = t("dialogOpening");
  }
  try {
    const chosen = await api("/api/v1/setup/pick-folder", { method: "POST" });
    if (!chosen || !chosen.path) return chosen;
    input.value = chosen.path;
    invalidate();
    return chosen;
  } catch (error) {
    if (error && (error.status === 409 || (error.message && error.message.includes("bereits")))) {
      showError(new Error(t("dialogAlreadyOpen")));
      return null;
    }
    throw error;
  } finally {
    if (button) {
      if (button.removeAttribute) button.removeAttribute("aria-busy");
      button.disabled = false;
      button.textContent = originalText;
    }
  }
}

function folderRow(profileId, purpose, value, removable) {
  const row = document.createElement("div");
  row.className = "field-input";
  const input = document.createElement("input");
  input.spellcheck = false;
  input.dataset.profileId = profileId;
  input.dataset.purpose = purpose;
  input.value = value;
  input.setAttribute("aria-label", purpose);
  const choose = document.createElement("button");
  choose.type = "button";
  choose.className = "button compact";
  choose.dataset.i18n = "chooseButton";
  choose.textContent = t("chooseButton");
  choose.addEventListener("click", () => pickFolder(input, choose).catch(showError));
  row.append(input, choose);
  if (removable) {
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "button compact";
    remove.dataset.i18n = "removeSource";
    remove.textContent = t("removeSource");
    remove.addEventListener("click", () => {
      row.remove();
      invalidate();
    });
    row.append(remove);
  }
  return row;
}

function purposeField(profileId, purpose, paths, repeatable) {
  const group = document.createElement("div");
  group.className = "field";
  group.append(textElement("span", purpose));
  const rows = document.createElement("div");
  rows.className = "field-rows";
  for (const path of paths) {
    rows.append(folderRow(profileId, purpose, path, repeatable));
  }
  group.append(rows);
  if (repeatable) {
    const add = document.createElement("button");
    add.type = "button";
    add.className = "button compact";
    add.dataset.i18n = "addSource";
    add.textContent = t("addSource");
    add.addEventListener("click", () => {
      rows.append(folderRow(profileId, purpose, "", true));
      invalidate();
    });
    group.append(add);
  }
  return group;
}

const PRESET_NAME = /^[A-Za-z0-9_.-]{1,40}$/;

function modelFromForm() {
  const provider = providerSelect.value;
  return {
    model_provider: provider,
    provider,
    ollama_host: document.querySelector("#ollama-host").value.trim() || null,
    ollama_model_id: document.querySelector("#ollama-model-id").value.trim() || null,
    bedrock_model_id: document.querySelector("#bedrock-model-id").value.trim() || null,
    aws_region: document.querySelector("#aws-region").value.trim() || null,
    anthropic_model_id:
      document.querySelector("#anthropic-model-id").value.trim() || null,
    openai_model_id: document.querySelector("#openai-model-id").value.trim() || null,
    openai_base_url: document.querySelector("#openai-base-url").value.trim() || null,
  };
}

function fillForm(model) {
  if (!model) return;
  providerSelect.value = model.model_provider || model.provider || "fixture";
  const values = {
    "#ollama-host": model.ollama_host,
    "#ollama-model-id": model.ollama_model_id,
    "#bedrock-model-id": model.bedrock_model_id,
    "#aws-region": model.aws_region,
    "#anthropic-model-id": model.anthropic_model_id,
    "#openai-model-id": model.openai_model_id,
    "#openai-base-url": model.openai_base_url,
  };
  for (const [selector, value] of Object.entries(values)) {
    const el = document.querySelector(selector);
    if (el) el.value = value || "";
  }
  showProviderFields();
}

function showProviderFields() {
  for (const name of ["ollama", "bedrock", "anthropic", "openai"]) {
    document.querySelector(`#${name}-fields`).hidden = providerSelect.value !== name;
  }
  renderGateHint();
}

function renderPresets() {
  presetList.replaceChildren();
  const names = Object.keys(presets).sort();
  if (!names.length) {
    presetList.append(textElement("p", t("presetNone"), "hint"));
    return;
  }
  for (const name of names) {
    const entry = presets[name] || {};
    const row = document.createElement("div");
    row.className = "field-input";
    row.dataset.presetName = name;
    const model =
      entry.ollama_model_id
      || entry.bedrock_model_id
      || entry.anthropic_model_id
      || entry.openai_model_id
      || "-";
    const provider = entry.model_provider || entry.provider || "fixture";
    const label = `${name} · ${provider} · ${model}`;
    row.append(
      textElement("span", name === activePreset ? `${label} (${t("presetActive")})` : label),
    );
    const activate = document.createElement("button");
    activate.type = "button";
    activate.className = "button compact";
    activate.textContent = t("presetActivate");
    activate.disabled = name === activePreset;
    activate.addEventListener("click", () => {
      activePreset = name;
      fillForm(entry);
      renderPresets();
      invalidate();
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "button compact";
    remove.textContent = t("presetDelete");
    remove.addEventListener("click", () => {
      delete presets[name];
      if (activePreset === name) activePreset = null;
      renderPresets();
      invalidate();
    });
    row.append(activate, remove);
    presetList.append(row);
  }
}

function savePreset() {
  const name = document.querySelector("#preset-name").value.trim();
  if (!PRESET_NAME.test(name)) {
    showError(new Error(t("presetNameInvalid")));
    return;
  }
  presets[name] = modelFromForm();
  activePreset = name;
  renderPresets();
  invalidate();
}

function calendarAccountRow(account) {
  const block = document.createElement("fieldset");
  block.className = "collapsible-entry";

  const legend = document.createElement("legend");
  legend.className = "entry-legend";
  if (legend.setAttribute) {
    legend.setAttribute("role", "button");
    legend.setAttribute("tabindex", "0");
    legend.setAttribute("aria-expanded", "false");
  }
  const titleSpan = textElement("span", (account && (account.display_name || account.account_id)) || t("calendarAccount"), "entry-title");
  const statusSpan = textElement("span", (account && `${account.backend} · ${account.profile_id}`) || "new", "entry-status");
  const chevronSpan = textElement("span", "", "entry-chevron");
  if (chevronSpan.setAttribute) chevronSpan.setAttribute("aria-hidden", "true");
  legend.append(titleSpan, statusSpan, chevronSpan);
  block.append(legend);

  const body = document.createElement("div");
  body.className = "entry-body";

  const profile = document.createElement("select");
  profile.dataset.calendarField = "profile_id";
  for (const item of state.profiles) {
    const option = document.createElement("option");
    option.value = item.profile_id;
    option.textContent = `${item.display_name} (${item.profile_id})`;
    profile.append(option);
  }
  if (account) profile.value = account.profile_id;
  body.append(labelled(t("calendarProfile"), profile));

  const backend = document.createElement("select");
  backend.dataset.calendarField = "backend";
  for (const item of state.calendar_backends) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    backend.append(option);
  }
  if (account) backend.value = account.backend;
  body.append(labelled(t("calendarBackend"), backend));

  const fields = [
    ["account_id", "account_id"],
    ["display_name", "display_name"],
    ["provider_id", "provider_id"],
    ["provider_revision", "provider_revision"],
    ["calendar_id", "calendar_id"],
  ];
  for (const [name, caption] of fields) {
    const input = document.createElement("input");
    input.spellcheck = false;
    input.dataset.calendarField = name;
    input.value = (account && account[name]) || "";
    if (name === "display_name" || name === "account_id") {
      input.addEventListener("input", () => {
        titleSpan.textContent = input.value.trim() || t("calendarAccount");
      });
    }
    body.append(labelled(caption, input));
  }

  const credential = document.createElement("input");
  credential.spellcheck = false;
  credential.dataset.calendarField = "credential_ref";
  credential.placeholder = "connector://google-calendar/default";
  credential.value = (account && account.credential_ref) || "";
  body.append(labelled(t("calendarCredential"), credential));

  const googleFields = document.createElement("div");
  googleFields.append(textElement("p", t("googleBindingHint")));
  for (const [name, caption] of [["credential_file", "googleCredentialFile"], ["ledger_dir", "googleLedgerDir"]]) {
    const input = document.createElement("input");
    input.spellcheck = false;
    input.dataset.googleField = name;
    googleFields.append(labelled(t(caption), input));
  }
  const bind = document.createElement("input");
  bind.type = "checkbox";
  bind.checked = false;
  bind.dataset.googleField = "bind_private_resources";
  googleFields.append(labelled(t("googleBind"), bind));
  googleFields.append(textElement("p", t("googleExecutionHint")));
  googleFields.append(textElement("p", t("googleLookupHint")));

  const lookup = document.createElement("button");
  lookup.type = "button";
  lookup.className = "button compact";
  lookup.dataset.action = "google-lookup";
  lookup.textContent = t("googleLookup");
  lookup.disabled = state.google_calendar_read_enabled !== true;

  const values = () => Object.fromEntries([
    ...block.querySelectorAll("[data-calendar-field]"),
    ...googleFields.querySelectorAll("[data-google-field]"),
  ].map(control => [control.dataset.calendarField || control.dataset.googleField, control.value.trim()]));

  lookup.addEventListener("click", async () => {
    if (lookup.disabled || backend.value !== "google" || state.google_calendar_read_enabled !== true) return;
    const before = values();
    const current = () => [...calendarAccounts.querySelectorAll("fieldset")].includes(block)
      && JSON.stringify(values()) === JSON.stringify(before);
    lookup.disabled = true;
    try {
      if (before.provider_id !== "google-calendar" || before.provider_revision !== "v3") {
        throw new Error(t("googleLookupFailed"));
      }
      const result = await api("/api/v1/setup/google-calendar-id", {
        method: "POST", body: JSON.stringify({
          schema: "folderhome.google-calendar-lookup-request.v1", profile_id: before.profile_id,
          credential_file: before.credential_file, credential_ref: before.credential_ref,
          calendar_id: before.calendar_id, confirm: true,
        }),
      });
      if (!current()) return;
      if (result.schema !== "folderhome.google-calendar-identity.v1" || result.read_only !== true
          || result.provider_id !== "google-calendar" || result.provider_revision !== "v3"
          || result.requested_calendar_id !== before.calendar_id
          || typeof result.calendar_id !== "string" || !/^[\x21-\x7e]{1,1024}$/.test(result.calendar_id)
          || result.calendar_id.toLowerCase() === "primary") throw new Error(t("googleLookupFailed"));
      const id = [...block.querySelectorAll("[data-calendar-field]")]
        .find(control => control.dataset.calendarField === "calendar_id");
      id.value = result.calendar_id;
      calendarDirty = true;
      invalidate();
    } catch (error) {
      if (current()) showError(new Error(t("googleLookupFailed")));
    } finally {
      lookup.disabled = state.google_calendar_read_enabled !== true;
    }
  });

  googleFields.append(lookup);
  const updateGoogleFields = () => {
    googleFields.hidden = backend.value !== "google";
    if (googleFields.hidden) bind.checked = false;
  };
  backend.addEventListener("change", () => {
    updateGoogleFields();
    statusSpan.textContent = `${backend.value} · ${profile.value}`;
  });
  profile.addEventListener("change", () => {
    statusSpan.textContent = `${backend.value} · ${profile.value}`;
  });
  updateGoogleFields();
  body.append(googleFields);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button compact";
  remove.dataset.i18n = "removeSource";
  remove.textContent = t("removeSource");
  remove.addEventListener("click", () => {
    block.remove();
    calendarDirty = true;
    invalidate();
  });
  body.append(remove);
  block.append(body);
  body.hidden = true;
  if (block.classList) block.classList.add("collapsed");

  const toggle = () => {
    const isExpanded = legend.getAttribute ? legend.getAttribute("aria-expanded") === "true" : true;
    if (legend.setAttribute) legend.setAttribute("aria-expanded", String(!isExpanded));
    if (block.classList) block.classList.toggle("collapsed", isExpanded);
    body.hidden = isExpanded;
  };
  legend.addEventListener("click", toggle);
  legend.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggle();
    }
  });

  return block;
}

function labelled(caption, control) {
  const label = document.createElement("label");
  if (control && control.type === "checkbox") {
    label.className = "checkbox";
    label.append(control, textElement("span", caption));
  } else {
    label.className = "field";
    label.append(textElement("span", caption), control);
  }
  return label;
}

function buildCalendar() {
  if (!calendarEnabled.checked || !calendarDirty) return null;
  const accounts = [];
  for (const block of calendarAccounts.querySelectorAll("fieldset")) {
    const account = {};
    for (const control of block.querySelectorAll("[data-calendar-field]")) {
      account[control.dataset.calendarField] = control.value.trim() || null;
    }
    const google = Object.fromEntries([...block.querySelectorAll("[data-google-field]")]
      .map(control => [control.dataset.googleField, control]));
    if (account.backend === "google" && google.bind_private_resources.checked) {
      account.bind_private_resources = true;
      account.credential_file = google.credential_file.value.trim();
      account.ledger_dir = google.ledger_dir.value.trim();
    }
    accounts.push(account);
  }
  return {
    default_backend: document.querySelector("#calendar-backend").value,
    timezone: document.querySelector("#calendar-timezone").value.trim(),
    ics_directory: document.querySelector("#calendar-directory").value.trim(),
    accounts,
  };
}

function renderCalendar() {
  const backend = document.querySelector("#calendar-backend");
  backend.replaceChildren();
  for (const item of state.calendar_backends || []) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    backend.append(option);
  }
  calendarAccounts.replaceChildren();
  const saved = state.current_calendar;
  calendarEnabled.checked = Boolean(saved);
  document.querySelector("#calendar-fields").hidden = !saved;
  if (saved) {
    backend.value = saved.default_backend;
    document.querySelector("#calendar-timezone").value = saved.timezone;
    document.querySelector("#calendar-directory").value = saved.ics_directory;
    for (const account of saved.accounts || []) {
      calendarAccounts.append(calendarAccountRow(account));
    }
  }
  if (state.calendar_load_error) showError(new Error(t("calendarLoadError")));
  calendarDirty = false;
}

function buildScheduler() {
  if (!document.querySelector("#scheduler-enabled").checked) return null;
  if (state.scheduler_load_error) throw new Error(t("schedulerLoadError"));
  const value = id => document.querySelector(`#scheduler-${id}`).value.trim();
  return {
    profile_id: value("profile"), source_dir: value("source"), target_dir: value("target"),
    area: value("area"), interval_minutes: Number(document.querySelector("#scheduler-interval").value),
    start_at: value("start"), timezone: value("timezone"),
    recursive: document.querySelector("#scheduler-recursive").checked,
    allow_sensitive_local_read: document.querySelector("#scheduler-read").checked,
    confirm_outside_home: document.querySelector("#outside-home").checked,
  };
}

function refreshSchedulerProfiles() {
  const select = document.querySelector("#scheduler-profile");
  const previous = select.value;
  const profiles = plannedProfiles();
  select.replaceChildren();
  for (const profile of profiles) {
    const option = document.createElement("option");
    option.value = profile.profile_id;
    option.textContent = profile.display_name || profile.profile_id;
    select.append(option);
  }
  if (profiles.some(profile => profile.profile_id === previous)) select.value = previous;
  if (select.value !== previous) loadSchedulerProfile();
}

function loadSchedulerProfile() {
  const profile = document.querySelector("#scheduler-profile").value;
  const saved = (state.current_schedulers || {})[profile] || {};
  for (const [id, value] of Object.entries({
    source: saved.source_dir || "", target: saved.target_dir || "", area: saved.area || "documents",
    interval: saved.interval_minutes ?? 30,
    start: saved.start_at || new Date(Date.now() + 5 * 60000).toISOString(),
    timezone: saved.timezone || "UTC",
  })) document.querySelector(`#scheduler-${id}`).value = value;
  document.querySelector("#scheduler-recursive").checked = saved.recursive ?? true;
  document.querySelector("#scheduler-read").checked = saved.allow_sensitive_local_read === true;
}

function renderScheduler() {
  const enabled = document.querySelector("#scheduler-enabled");
  enabled.checked = false;
  enabled.disabled = Boolean(state.scheduler_load_error);
  document.querySelector("#scheduler-fields").hidden = true;
  document.querySelector("#scheduler-load-error").hidden = !state.scheduler_load_error;
  refreshSchedulerProfiles();
  loadSchedulerProfile();
}

function bindSchedulerEvents() {
  document.querySelector("#scheduler-enabled").addEventListener("change", () => {
    refreshSchedulerProfiles();
    document.querySelector("#scheduler-fields").hidden = !document.querySelector("#scheduler-enabled").checked;
    invalidate();
  });
  document.querySelector("#scheduler-profile").addEventListener("change", () => {
    loadSchedulerProfile();
    invalidate();
  });
  for (const event of ["input", "change"]) {
    document.querySelector("#scheduler-fields").addEventListener(event, invalidate);
  }
  for (const name of ["source", "target"]) {
    const chooseBtn = document.querySelector(`#scheduler-${name}-choose`);
    chooseBtn.addEventListener("click", async () => {
      const input = document.querySelector(`#scheduler-${name}`);
      const previous = input.value;
      try {
        await pickFolder(input, chooseBtn);
        if (previous !== input.value) invalidate();
      } catch (error) { showError(error); }
    });
  }
}

// ------------------------------------------------------------------ profiles
function integerRuleKeys() {
  return new Set(state.integer_rule_keys || []);
}

function ruleRow(container, rule, scopes) {
  const row = document.createElement("div");
  row.className = "field-input";
  row.dataset.ruleRow = "";

  const key = document.createElement("select");
  key.dataset.ruleField = "key";
  key.setAttribute("aria-label", t("ruleKey"));
  for (const item of state.rule_keys || []) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    key.append(option);
  }
  key.value = rule.key || (state.rule_keys || [])[0];

  const value = document.createElement("input");
  value.dataset.ruleField = "value";
  value.spellcheck = false;
  value.setAttribute("aria-label", t("ruleValue"));
  value.value = rule.value === null || rule.value === undefined ? "" : String(rule.value);

  const scope = document.createElement("select");
  scope.dataset.ruleField = "scope";
  scope.setAttribute("aria-label", t("ruleScope"));
  for (const item of scopes) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    scope.append(option);
  }
  scope.value = scopes.includes(rule.scope) ? rule.scope : scopes[0];

  const area = document.createElement("input");
  area.dataset.ruleField = "area";
  area.spellcheck = false;
  area.placeholder = t("ruleArea");
  area.setAttribute("aria-label", t("ruleArea"));
  area.value = rule.area || "";

  const applyKind = () => {
    // A count key gets a number field, so the contract is not told a word.
    value.type = integerRuleKeys().has(key.value) ? "number" : "text";
    area.hidden = !scope.value.endsWith("_area") && scope.value !== "area";
  };
  applyKind();
  key.addEventListener("change", () => {
    applyKind();
    invalidate();
  });
  scope.addEventListener("change", () => {
    applyKind();
    invalidate();
  });
  for (const control of [value, area]) control.addEventListener("input", invalidate);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button compact";
  remove.dataset.i18n = "removeSource";
  remove.textContent = t("removeSource");
  remove.addEventListener("click", () => {
    row.remove();
    invalidate();
  });

  row.append(key, value, scope, area, remove);
  container.append(row);
  return row;
}

function ruleTable(rules, scopes) {
  const block = document.createElement("div");
  const rows = document.createElement("div");
  rows.dataset.rules = "";
  block.append(rows);
  for (const rule of rules || []) ruleRow(rows, rule, scopes);
  const add = document.createElement("button");
  add.type = "button";
  add.className = "button compact";
  add.dataset.i18n = "ruleAdd";
  add.textContent = t("ruleAdd");
  add.addEventListener("click", () => {
    ruleRow(rows, {}, scopes);
    invalidate();
  });
  block.append(add);
  return block;
}

function profileCard(profile) {
  const block = document.createElement("fieldset");
  block.dataset.profile = "";
  block.className = "collapsible-entry";

  const legend = document.createElement("legend");
  legend.className = "entry-legend";
  if (legend.setAttribute) {
    legend.setAttribute("role", "button");
    legend.setAttribute("tabindex", "0");
    legend.setAttribute("aria-expanded", "false");
  }

  const titleSpan = textElement("span", profile.display_name || t("profileAdd"), "entry-title");
  const ruleCount = (profile.rules || []).length;
  const statusSpan = textElement("span", profile.profile_id ? `${profile.profile_id} · ${ruleCount} rules` : t("profileAdd"), "entry-status");
  const chevronSpan = textElement("span", "", "entry-chevron");
  if (chevronSpan.setAttribute) chevronSpan.setAttribute("aria-hidden", "true");
  legend.append(titleSpan, statusSpan, chevronSpan);
  block.append(legend);

  const body = document.createElement("div");
  body.className = "entry-body";

  const id = document.createElement("input");
  id.dataset.profileField = "profile_id";
  id.spellcheck = false;
  id.value = profile.profile_id || "";
  // Renaming an id would move the file and drop every binding to it, so an
  // existing profile keeps its id and is replaced by delete plus add instead.
  id.readOnly = knownProfileIds.has(profile.profile_id);
  id.addEventListener("input", () => {
    const rulesNow = body.querySelector("[data-rules]") ? readRules(body.querySelector("[data-rules]")).length : 0;
    statusSpan.textContent = id.value.trim() ? `${id.value.trim()} · ${rulesNow} rules` : t("profileAdd");
    invalidate();
  });
  body.append(labelled(t("profileId"), id));
  if (id.readOnly) body.append(textElement("p", t("profileIdLocked"), "hint"));

  const name = document.createElement("input");
  name.dataset.profileField = "display_name";
  name.spellcheck = false;
  name.value = profile.display_name || "";
  name.addEventListener("input", () => {
    titleSpan.textContent = name.value.trim() || t("profileAdd");
    invalidate();
  });
  body.append(labelled(t("profileName"), name));

  body.append(textElement("p", t("profileRules"), "hint"));
  body.append(ruleTable(profile.rules, state.profile_rule_scopes || []));

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button compact";
  remove.dataset.i18n = "profileDelete";
  remove.textContent = t("profileDelete");
  remove.addEventListener("click", () => {
    if (profileList.querySelectorAll("[data-profile]").length < 2) {
      showError(new Error(t("profileLast")));
      return;
    }
    const label = name.value.trim() || id.value.trim();
    if (!window.confirm(t("profileDeleteConfirm", { name: label }))) return;
    block.remove();
    renderFolders();
    invalidate();
  });
  body.append(remove);
  block.append(body);
  body.hidden = true;
  if (block.classList) block.classList.add("collapsed");

  const toggle = () => {
    const isExpanded = legend.getAttribute ? legend.getAttribute("aria-expanded") === "true" : true;
    if (legend.setAttribute) legend.setAttribute("aria-expanded", String(!isExpanded));
    if (block.classList) block.classList.toggle("collapsed", isExpanded);
    body.hidden = isExpanded;
  };
  legend.addEventListener("click", toggle);
  legend.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggle();
    }
  });

  return block;
}

function renderProfiles(profiles) {
  profileList.replaceChildren();
  for (const profile of profiles) profileList.append(profileCard(profile));
  document.querySelector("#profile-starters").hidden = profiles.length > 0;
}

function renderHousehold(rules) {
  householdRules.replaceChildren(ruleTable(rules, state.household_rule_scopes || []));
}

function readRules(container) {
  const integers = integerRuleKeys();
  return [...container.querySelectorAll("[data-rule-row]")].map((row) => {
    const key = row.querySelector('[data-rule-field="key"]').value;
    const raw = row.querySelector('[data-rule-field="value"]').value.trim();
    const area = row.querySelector('[data-rule-field="area"]').value.trim();
    return {
      key,
      value: integers.has(key) && raw !== "" ? Number(raw) : raw,
      scope: row.querySelector('[data-rule-field="scope"]').value,
      area: area || null,
    };
  });
}

function buildProfiles() {
  return [...profileList.querySelectorAll("[data-profile]")].map((block) => ({
    profile_id: block.querySelector('[data-profile-field="profile_id"]').value.trim(),
    display_name: block.querySelector('[data-profile-field="display_name"]').value.trim(),
    rules: readRules(block.querySelector("[data-rules]")),
  }));
}

function plannedProfiles() {
  // The folder grid follows the profiles in the form, not the ones on disk:
  // a profile added here has to be able to get a folder in the same plan.
  return buildProfiles()
    .filter((item) => item.profile_id)
    .map((item) => ({
      profile_id: item.profile_id,
      display_name: item.display_name || item.profile_id,
    }));
}

function templateProfiles() {
  const templates = state.profile_templates || { profiles: {}, household: null };
  return Object.entries(templates.profiles || {})
    .map(([name, document_]) => ({
      profile_id: String(document_.profile_id || name).toLowerCase(),
      display_name: document_.display_name || name,
      rules: document_.rules || [],
    }))
    .sort((left, right) => left.profile_id.localeCompare(right.profile_id));
}

function templateHouseholdRules(globalOnly) {
  const household = (state.profile_templates || {}).household;
  const rules = (household && household.rules) || [];
  return globalOnly ? rules.filter((rule) => rule.scope === "global") : rules;
}


function renderKeys() {
  keyFields.replaceChildren();
  const stored = {
    ANTHROPIC_API_KEY: state.has_anthropic_key,
    OPENAI_API_KEY: state.has_openai_key,
  };
  for (const [name, present] of Object.entries(stored)) {
    const label = document.createElement("label");
    label.className = "field";
    label.append(textElement("span", name));
    const row = document.createElement("div");
    row.className = "field-input";
    const input = document.createElement("input");
    input.type = "password";
    input.dataset.envName = name;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.addEventListener("input", invalidate);
    row.append(input);
    const status = textElement("p", t(present ? "keyStored" : "keyMissing"), "hint");
    if (present) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "button compact";
      remove.dataset.i18n = "keyRemove";
      remove.textContent = t("keyRemove");
      remove.addEventListener("click", () => {
        keyRemovals.add(name);
        remove.disabled = true;
        input.value = "";
        input.disabled = true;
        status.textContent = t("keyPendingRemoval");
        invalidate();
      });
      row.append(remove);
    }
    label.append(row);
    label.append(status);
    keyFields.append(label);
  }
}

function buildKeyChanges() {
  const changes = {};
  for (const name of keyRemovals) changes[name] = null;
  for (const input of keyFields.querySelectorAll("input")) {
    if (input.value) changes[input.dataset.envName] = input.value;
  }
  return changes;
}

function renderFolders() {
  folderGrid.replaceChildren();
  const current = new Map();
  for (const item of state.current_folders || []) {
    const key = `${item.profile_id}|${item.purpose}`;
    if (!current.has(key)) current.set(key, []);
    current.get(key).push(item.path);
  }
  const repeatable = new Set(state.repeatable_purposes || []);
  for (const profile of plannedProfiles()) {
    const block = document.createElement("fieldset");
    block.className = "collapsible-entry";

    const legend = document.createElement("legend");
    legend.className = "entry-legend";
    if (legend.setAttribute) {
      legend.setAttribute("role", "button");
      legend.setAttribute("tabindex", "0");
      legend.setAttribute("aria-expanded", "false");
    }

    const titleSpan = textElement("span", profile.display_name || profile.profile_id, "entry-title");
    const statusSpan = textElement("span", profile.profile_id, "entry-status");
    const chevronSpan = textElement("span", "", "entry-chevron");
    if (chevronSpan.setAttribute) chevronSpan.setAttribute("aria-hidden", "true");
    legend.append(titleSpan, statusSpan, chevronSpan);
    block.append(legend);

    const body = document.createElement("div");
    body.className = "entry-body";
    for (const purpose of state.purposes) {
      const paths = current.get(`${profile.profile_id}|${purpose}`) || [""];
      body.append(
        purposeField(profile.profile_id, purpose, paths, repeatable.has(purpose)),
      );
    }
    block.append(body);
    body.hidden = true;
    if (block.classList) block.classList.add("collapsed");

    const toggle = () => {
      const isExpanded = legend.getAttribute ? legend.getAttribute("aria-expanded") === "true" : true;
      if (legend.setAttribute) legend.setAttribute("aria-expanded", String(!isExpanded));
      if (block.classList) block.classList.toggle("collapsed", isExpanded);
      body.hidden = isExpanded;
    };
    legend.addEventListener("click", toggle);
    legend.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });

    folderGrid.append(block);
  }
}

function copyBlock(text, block, note) {
  const select = () => {
    const range = document.createRange();
    range.selectNodeContents(block);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    note.textContent = t("copyFallback");
  };
  if (!navigator.clipboard || !navigator.clipboard.writeText) return select();
  navigator.clipboard.writeText(text).then(() => {
    note.textContent = t("copyDone");
  }, select);
}

function integrationCard(title, text) {
  const card = document.createElement("fieldset");
  card.append(textElement("legend", title));
  const block = textElement("pre", text);
  const note = textElement("p", "", "hint");
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "button compact";
  copy.dataset.i18n = "copyButton";
  copy.textContent = t("copyButton");
  copy.addEventListener("click", () => copyBlock(text, block, note));
  card.append(block, copy, note);
  return card;
}

// Instructions only: the service hands over the same plan `mcp plan` prints.
function renderIntegrations() {
  const target = document.querySelector("#subscriptions");
  const plan = state.integrations || {};
  target.replaceChildren(
    integrationCard("Claude Code", plan.claude_code_command || ""),
    integrationCard("Codex CLI", plan.codex_config_toml || ""),
  );
}

function buildRequest() {
  const folders = [...folderGrid.querySelectorAll("input")]
    .filter((input) => input.value.trim())
    .map((input) => ({
      profile_id: input.dataset.profileId,
      purpose: input.dataset.purpose,
      path: input.value.trim(),
      confirm_outside_home: document.querySelector("#outside-home").checked,
    }));
  return {
    schema: "folderhome.setup-plan-request.v1",
    folders,
    // Without a preset the form counts as it stands; with one the preset wins.
    model: modelFromForm(),
    model_presets: presets,
    model_preset: activePreset,
    calendar: buildCalendar(),
    scheduler: buildScheduler(),
    profiles: buildProfiles(),
    household_rules: readRules(householdRules.querySelector("[data-rules]")),
    port: Number(document.querySelector("#port").value) || 8765,
    state_dir: document.querySelector("#state-dir").value.trim(),
    profiles_dir: profilesDir.value.trim(),
  };
}

function renderPlan(plan) {
  summary.replaceChildren();
  clearValidationErrors();
  if (!plan.valid) {
    summary.append(textElement("p", t("checkFailed"), "error"));
    const list = document.createElement("ul");
    list.className = "error-list";
    const cardErrorCounts = new Map();

    for (const item of plan.errors) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "error-jump-button";
      btn.textContent = `${item.field}: ${item.message}`;
      btn.addEventListener("click", () => jumpToError(item.field, item.message));
      li.append(btn);
      list.append(li);

      // Resolve element and highlight field
      const element = resolveElementForField(item.field, item.message);
      let targetCard = null;
      if (element) {
        if (element.setAttribute) element.setAttribute("aria-invalid", "true");
        if (element.classList) element.classList.add("is-invalid");
        const container = (element.closest && (element.closest(".field") || element.closest(".field-input") || element.closest(".checkbox"))) || element.parentNode;
        if (container && !container.querySelector(".field-error-msg")) {
          const msgEl = document.createElement("div");
          msgEl.className = "field-error-msg";
          msgEl.setAttribute("role", "alert");
          msgEl.textContent = item.message;
          container.append(msgEl);
        }
        targetCard = (element.closest && element.closest(".card")) || getCardForFieldOrText(`${item.field} ${item.message}`);
      } else {
        targetCard = getCardForFieldOrText(`${item.field} ${item.message}`);
      }
      if (targetCard) {
        const currentCount = cardErrorCounts.get(targetCard) || 0;
        cardErrorCounts.set(targetCard, currentCount + 1);
      }
    }
    summary.append(list);

    // Expand cards with errors once and update error badges
    let firstCard = null;
    for (const [card, count] of cardErrorCounts.entries()) {
      if (card.classList) card.classList.add("has-error");
      setCardExpanded(card, true);
      if (!firstCard) firstCard = card;

      let badge = card.querySelector(".card-error-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "card-error-badge";
        badge.setAttribute("aria-label", `${count} errors`);
        const chevron = card.querySelector(".card-chevron");
        if (chevron && chevron.parentNode) {
          chevron.parentNode.insertBefore(badge, chevron);
        } else {
          const head = card.querySelector(".card-head");
          if (head) head.append(badge);
        }
      }
      badge.textContent = String(count);
    }
    if (firstCard) {
      setActiveCard(firstCard);
    }
    return;
  }
  summary.append(textElement("p", t("checkOk")));
  const list = document.createElement("ul");
  list.append(textElement("li", plan.targets.resources_file));
  list.append(textElement("li", plan.targets.launch_file));
  if (plan.scheduler) {
    for (const item of plan.scheduler.documents) list.append(textElement("li", item.path));
    for (const path of plan.scheduler.directories) list.append(textElement("li", `${path}/`));
  }
  if (plan.profiles_json) {
    list.append(textElement("li", plan.targets.household_file));
    for (const id of Object.keys(plan.profiles_json).sort()) {
      list.append(textElement("li", `${plan.targets.profiles_dir}/${id}.json`));
    }
  }
  summary.append(list);
  const cascade = plan.cascade || {};
  const removed = [
    ...(plan.removed_profile_ids || []),
    ...(cascade.resource_ids || []),
    ...(cascade.calendar_account_ids || []),
  ];
  if (removed.length) {
    summary.append(textElement("p", t("cascadeTitle"), "hint"));
    const gone = document.createElement("ul");
    for (const item of removed) gone.append(textElement("li", item));
    summary.append(gone);
  }
  summary.append(textElement("pre", JSON.stringify(plan.resources_json, null, 2)));
  summary.append(textElement("pre", JSON.stringify(plan.launch_json, null, 2)));
  if (plan.scheduler) {
    summary.append(textElement("p", t("schedulerHint"), "hint"));
    for (const item of plan.scheduler.documents) {
      summary.append(textElement("pre", JSON.stringify(item.document, null, 2)));
    }
  }
}

async function check() {
  const checkBtn = document.querySelector("#check");
  const resultsArea = summary.closest ? summary.closest(".results") : null;
  if (checkBtn) {
    if (checkBtn.setAttribute) checkBtn.setAttribute("aria-busy", "true");
    checkBtn.disabled = true;
  }
  if (resultsArea && resultsArea.setAttribute) {
    resultsArea.setAttribute("aria-busy", "true");
  }
  try {
    const plan = await api("/api/v1/setup/validate", {
      method: "POST",
      body: JSON.stringify(buildRequest()),
    });
    checkedPlan = plan.valid ? plan : null;
    saveButton.disabled = !plan.valid;
    saveNote.hidden = false;
    renderPlan(plan);
  } finally {
    if (checkBtn) {
      if (checkBtn.removeAttribute) checkBtn.removeAttribute("aria-busy");
      checkBtn.disabled = false;
    }
    if (resultsArea && resultsArea.removeAttribute) {
      resultsArea.removeAttribute("aria-busy");
    }
  }
}

async function save() {
  if (!checkedPlan) return;
  if (saveButton.setAttribute) saveButton.setAttribute("aria-busy", "true");
  saveButton.disabled = true;
  const resultsArea = summary.closest ? summary.closest(".results") : null;
  if (resultsArea && resultsArea.setAttribute) {
    resultsArea.setAttribute("aria-busy", "true");
  }
  try {
    const request = buildRequest();
    request.confirm = true;
    request.plan_sha256 = checkedPlan.plan_sha256;
    // Keys ride along with the save alone: never with a check, never in the hash.
    const keyChanges = buildKeyChanges();
    if (Object.keys(keyChanges).length) request.api_keys = keyChanges;
    const saved = await api("/api/v1/setup/save", {
      method: "POST",
      body: JSON.stringify(request),
    });
    summary.replaceChildren();
    summary.append(textElement("p", t("savedTitle")));
    summary.append(textElement("pre", saved.launch_command));
    if (checkedPlan.scheduler) {
      summary.append(textElement("p", t("schedulerSaved")));
      summary.append(textElement("pre", JSON.stringify(checkedPlan.scheduler.request, null, 2)));
    }
    if ((saved.backups || []).length) {
      summary.append(textElement("p", t("backupNote"), "hint"));
    }
    saveNote.hidden = true;
    checkedPlan = null;
    keyRemovals.clear();
    // Ask the service what is stored now instead of guessing from the form.
    state = await api("/api/v1/setup/state");
    renderKeys();
    renderCalendar();
    renderScheduler();
  } finally {
    if (saveButton.removeAttribute) saveButton.removeAttribute("aria-busy");
    saveButton.disabled = !checkedPlan;
    if (resultsArea && resultsArea.removeAttribute) {
      resultsArea.removeAttribute("aria-busy");
    }
  }
}

function showError(error) {
  summary.replaceChildren(textElement("p", error.message, "error"));
  expandCardForError(error.message);
}

providerSelect.addEventListener("change", () => {
  showProviderFields();
  invalidate();
});
document.querySelector("#preset-save").addEventListener("click", savePreset);
document.querySelector("#profile-add").addEventListener("click", () => {
  profileList.append(profileCard({ profile_id: "", display_name: "", rules: [] }));
  document.querySelector("#profile-starters").hidden = true;
  invalidate();
});
document.querySelector("#profiles-take-examples").addEventListener("click", () => {
  renderProfiles(templateProfiles());
  renderHousehold(templateHouseholdRules(false));
  renderFolders();
  invalidate();
});
document.querySelector("#profiles-start-empty").addEventListener("click", () => {
  renderProfiles([]);
  renderHousehold(templateHouseholdRules(true));
  renderFolders();
  invalidate();
});
const profilesDirChoose = document.querySelector("#profiles-dir-choose");
profilesDirChoose.addEventListener("click", () =>
  pickFolder(profilesDir, profilesDirChoose).catch(showError),
);
profilesDir.addEventListener("input", invalidate);
calendarEnabled.addEventListener("change", () => {
  document.querySelector("#calendar-fields").hidden = !calendarEnabled.checked;
  calendarDirty = true;
  invalidate();
});
for (const event of ["input", "change"]) {
  document.querySelector("#calendar-fields").addEventListener(event, () => {
    calendarDirty = true;
    invalidate();
  });
}
document.querySelector("#calendar-account-add").addEventListener("click", () => {
  calendarAccounts.append(calendarAccountRow(null));
  calendarDirty = true;
  invalidate();
});
const calendarDirChoose = document.querySelector("#calendar-directory-choose");
calendarDirChoose.addEventListener("click", async () => {
  const input = document.querySelector("#calendar-directory");
  const previous = input.value;
  try {
    await pickFolder(input, calendarDirChoose);
    if (input.value !== previous) calendarDirty = true;
  } catch (error) {
    showError(error);
  }
});
document.querySelector("#ollama-host").addEventListener("input", renderGateHint);
bindSchedulerEvents();
document.querySelector("#check").addEventListener("click", () => check().catch(showError));
document.querySelector("#save").addEventListener("click", () => save().catch(showError));
document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => {
    language = button.dataset.language;
    document.documentElement.lang = language;
    applyTranslations();
  });
});

api("/api/v1/setup/state")
  .then((payload) => {
    state = payload;
    document.querySelector("#state-dir").value = payload.state_dir || payload.config_dir;
    // The shipped examples are a template; a write goes to an own folder.
    profilesDir.value = payload.profiles_dir_is_template
      ? payload.default_profiles_dir
      : payload.profiles_dir;
    knownProfileIds = new Set(
      (payload.profile_forms || []).map((item) => item.profile_id),
    );
    presets = payload.model_presets || {};
    activePreset = payload.model_preset || null;
    if (activePreset && presets[activePreset]) fillForm(presets[activePreset]);
    renderProfiles(payload.profile_forms || []);
    renderHousehold(payload.household_rules || []);
    renderFolders();
    renderKeys();
    renderPresets();
    renderIntegrations();
    renderCalendar();
    renderScheduler();
    applyTranslations();
    initCollapsibleCards();
  })
  .catch(showError);

initCollapsibleCards();
