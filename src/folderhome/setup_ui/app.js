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
    subscriptionsStep1: "Start the app with the command shown in section 8 after saving.",
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
    portLabel: "Port",
    outsideHome: "I confirm folders outside my user folder",
    summaryTitle: "8. Summary and save",
    checkButton: "Check",
    saveButton: "Save",
    saveNote: "Nothing is saved automatically. Check first, then save; saving writes the profile files, resources.json and launch.json.",
    accountLine: "Operating system account {account} · configuration in {dir}",
    checkOk: "The plan is valid. These files will be written:",
    checkFailed: "Please correct this first:",
    overwriteHint:
      "Saving replaces resources.json completely. Entries you added by hand are "
      + "lost; the previous version stays next to it as .bak-<timestamp>.",
    savedTitle: "Written. Start FolderHome with:",
    backupNote: "The previous version was kept as a .bak file.",
    requestFailed: "The setup service refused the request ({status}).",
    calendarTitle: "7. Calendar",
    calendarHint: "This writes calendar.json and calendar-accounts.json. The calendar commands read them; the app itself does not, and there is no Outlook backend in this build. An account stores a reference to a secret, never the secret.",
    calendarEnable: "Write calendar configuration",
    calendarBackend: "Default backend",
    calendarTimezone: "Default time zone",
    calendarDirectory: "UpToday ICS folder",
    calendarAddAccount: "+ another account",
    calendarAccount: "Account",
    calendarProfile: "Profile",
    calendarCredential: "Connector reference (google only)",
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
    subscriptionsStep1: "Starte die App mit dem Befehl, den Abschnitt 8 nach dem Speichern anzeigt.",
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
    portLabel: "Port",
    outsideHome: "Ich bestätige Ordner außerhalb meines Benutzerordners",
    summaryTitle: "8. Zusammenfassung und Speichern",
    checkButton: "Prüfen",
    saveButton: "Speichern",
    saveNote: "Es wird nichts automatisch gespeichert. Erst Prüfen, dann Speichern; das Speichern schreibt die Profildateien, resources.json und launch.json.",
    accountLine: "Betriebssystemkonto {account} · Konfiguration in {dir}",
    checkOk: "Der Plan ist gültig. Diese Dateien werden geschrieben:",
    checkFailed: "Bitte zuerst korrigieren:",
    overwriteHint:
      "Das Speichern ersetzt resources.json vollständig. Von Hand ergänzte "
      + "Einträge gehen verloren; die Vorversion bleibt als .bak-<Zeitstempel> daneben.",
    savedTitle: "Geschrieben. Starte FolderHome mit:",
    backupNote: "Die Vorversion wurde als .bak-Datei behalten.",
    requestFailed: "Der Einrichtungsdienst hat die Anfrage abgelehnt ({status}).",
    calendarTitle: "7. Kalender",
    calendarHint: "Dies schreibt calendar.json und calendar-accounts.json. Die Kalenderbefehle lesen sie; die App selbst nicht, und ein Outlook-Backend gibt es in dieser Fassung nicht. Ein Konto speichert einen Verweis auf ein Geheimnis, nie das Geheimnis selbst.",
    calendarEnable: "Kalenderkonfiguration schreiben",
    calendarBackend: "Standard-Backend",
    calendarTimezone: "Standardzeitzone",
    calendarDirectory: "UpToday-ICS-Ordner",
    calendarAddAccount: "+ weiteres Konto",
    calendarAccount: "Konto",
    calendarProfile: "Profil",
    calendarCredential: "Connector-Referenz (nur google)",
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
    throw new Error(message);
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

async function pickFolder(input) {
  const chosen = await api("/api/v1/setup/pick-folder", { method: "POST" });
  if (!chosen.path) return;
  input.value = chosen.path;
  invalidate();
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
  choose.addEventListener("click", () => pickFolder(input).catch(showError));
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
  return {
    provider: providerSelect.value,
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
  providerSelect.value = model.provider || model.model_provider || "fixture";
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
    document.querySelector(selector).value = value || "";
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
    const entry = presets[name];
    const row = document.createElement("div");
    row.className = "field-input";
    const model =
      entry.ollama_model_id
      || entry.bedrock_model_id
      || entry.anthropic_model_id
      || entry.openai_model_id
      || "-";
    const label = `${name} · ${entry.provider} · ${model}`;
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
  block.append(textElement("legend", t("calendarAccount")));
  const profile = document.createElement("select");
  profile.dataset.calendarField = "profile_id";
  for (const item of state.profiles) {
    const option = document.createElement("option");
    option.value = item.profile_id;
    option.textContent = `${item.display_name} (${item.profile_id})`;
    profile.append(option);
  }
  block.append(labelled(t("calendarProfile"), profile));
  const backend = document.createElement("select");
  backend.dataset.calendarField = "backend";
  for (const item of state.calendar_backends) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    backend.append(option);
  }
  block.append(labelled(t("calendarBackend"), backend));
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
    block.append(labelled(caption, input));
  }
  const credential = document.createElement("input");
  credential.spellcheck = false;
  credential.dataset.calendarField = "credential_ref";
  credential.placeholder = "connector://google-calendar/default";
  block.append(labelled(t("calendarCredential"), credential));
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button compact";
  remove.dataset.i18n = "removeSource";
  remove.textContent = t("removeSource");
  remove.addEventListener("click", () => {
    block.remove();
    invalidate();
  });
  block.append(remove);
  return block;
}

function labelled(caption, control) {
  const label = document.createElement("label");
  label.className = "field";
  label.append(textElement("span", caption), control);
  return label;
}

function buildCalendar() {
  if (!calendarEnabled.checked) return null;
  const accounts = [];
  for (const block of calendarAccounts.querySelectorAll("fieldset")) {
    const account = {};
    for (const control of block.querySelectorAll("[data-calendar-field]")) {
      account[control.dataset.calendarField] = control.value.trim() || null;
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
  block.append(textElement("legend", profile.display_name || t("profileAdd")));

  const id = document.createElement("input");
  id.dataset.profileField = "profile_id";
  id.spellcheck = false;
  id.value = profile.profile_id || "";
  // Renaming an id would move the file and drop every binding to it, so an
  // existing profile keeps its id and is replaced by delete plus add instead.
  id.readOnly = knownProfileIds.has(profile.profile_id);
  id.addEventListener("input", invalidate);
  block.append(labelled(t("profileId"), id));
  if (id.readOnly) block.append(textElement("p", t("profileIdLocked"), "hint"));

  const name = document.createElement("input");
  name.dataset.profileField = "display_name";
  name.spellcheck = false;
  name.value = profile.display_name || "";
  name.addEventListener("input", invalidate);
  block.append(labelled(t("profileName"), name));

  block.append(textElement("p", t("profileRules"), "hint"));
  block.append(ruleTable(profile.rules, state.profile_rule_scopes || []));

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
  block.append(remove);
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
    block.append(textElement("legend", `${profile.display_name} (${profile.profile_id})`));
    for (const purpose of state.purposes) {
      const paths = current.get(`${profile.profile_id}|${purpose}`) || [""];
      block.append(
        purposeField(profile.profile_id, purpose, paths, repeatable.has(purpose)),
      );
    }
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
    profiles: buildProfiles(),
    household_rules: readRules(householdRules.querySelector("[data-rules]")),
    port: Number(document.querySelector("#port").value) || 8765,
    state_dir: document.querySelector("#state-dir").value.trim(),
    profiles_dir: profilesDir.value.trim(),
  };
}

function renderPlan(plan) {
  summary.replaceChildren();
  if (!plan.valid) {
    summary.append(textElement("p", t("checkFailed"), "error"));
    const list = document.createElement("ul");
    for (const item of plan.errors) {
      list.append(textElement("li", `${item.field}: ${item.message}`));
    }
    summary.append(list);
    return;
  }
  summary.append(textElement("p", t("checkOk")));
  const list = document.createElement("ul");
  list.append(textElement("li", plan.targets.resources_file));
  list.append(textElement("li", plan.targets.launch_file));
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
}

async function check() {
  const plan = await api("/api/v1/setup/validate", {
    method: "POST",
    body: JSON.stringify(buildRequest()),
  });
  checkedPlan = plan.valid ? plan : null;
  saveButton.disabled = !plan.valid;
  saveNote.hidden = false;
  renderPlan(plan);
}

async function save() {
  if (!checkedPlan) return;
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
  if ((saved.backups || []).length) {
    summary.append(textElement("p", t("backupNote"), "hint"));
  }
  saveButton.disabled = true;
  saveNote.hidden = true;
  checkedPlan = null;
  keyRemovals.clear();
  // Ask the service what is stored now instead of guessing from the form.
  state = await api("/api/v1/setup/state");
  renderKeys();
}

function showError(error) {
  summary.replaceChildren(textElement("p", error.message, "error"));
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
document.querySelector("#profiles-dir-choose").addEventListener("click", () =>
  pickFolder(profilesDir).catch(showError),
);
profilesDir.addEventListener("input", invalidate);
calendarEnabled.addEventListener("change", () => {
  document.querySelector("#calendar-fields").hidden = !calendarEnabled.checked;
  invalidate();
});
document.querySelector("#calendar-account-add").addEventListener("click", () => {
  calendarAccounts.append(calendarAccountRow(null));
  invalidate();
});
document.querySelector("#calendar-directory-choose").addEventListener("click", () =>
  pickFolder(document.querySelector("#calendar-directory")).catch(showError),
);
document.querySelector("#ollama-host").addEventListener("input", renderGateHint);
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
    applyTranslations();
  })
  .catch(showError);
