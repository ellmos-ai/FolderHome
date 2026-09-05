const token = new URLSearchParams(window.location.search).get("token") || "";

const translations = {
  en: {
    subtitle: "Local setup",
    eyebrow: "Installer",
    title: "Set up FolderHome",
    lead: "This program is the only place that writes FolderHome configuration. The app itself never changes it. Nothing is written before you confirm the exact plan.",
    foldersTitle: "1. Folders",
    foldersHint: "Give each profile a folder per purpose. Source folders are read, output folders receive files. Leave a field empty to skip that purpose.",
    modelTitle: "2. Model",
    modelHint: "The provider is a start-up choice. Network and data approvals stay command-line flags and are never written to a file.",
    providerLabel: "Provider",
    ollamaHost: "Ollama host",
    ollamaModel: "Ollama model id",
    bedrockModel: "Bedrock model id",
    awsRegion: "AWS region",
    gateHintFixture: "The deterministic fixture needs no approval and no network.",
    gateHintLoopback: "A model on this machine needs no approval, because nothing leaves the loopback interface.",
    gateHintRemote: "Start the app with --allow-network and --approve-sensitive-cloud-data for this provider.",
    runtimeTitle: "3. Runtime",
    stateDir: "App state folder",
    portLabel: "Port",
    outsideHome: "I confirm folders outside my user folder",
    summaryTitle: "4. Summary and save",
    checkButton: "Check",
    saveButton: "Write these two files",
    accountLine: "Operating system account {account} · configuration in {dir}",
    checkOk: "The plan is valid. These two files will be written:",
    checkFailed: "Please correct this first:",
    savedTitle: "Written. Start FolderHome with:",
    backupNote: "The previous version was kept as a .bak file.",
    requestFailed: "The setup service refused the request ({status}).",
  },
  de: {
    subtitle: "Lokale Einrichtung",
    eyebrow: "Einrichtung",
    title: "FolderHome einrichten",
    lead: "Dieses Programm ist der einzige Ort, der FolderHome-Konfiguration schreibt. Die App selbst ändert sie nie. Es wird nichts geschrieben, bevor du genau diesen Plan bestätigst.",
    foldersTitle: "1. Ordner",
    foldersHint: "Gib jedem Profil je Zweck einen Ordner. Quellordner werden gelesen, Ausgabeordner nehmen Dateien auf. Ein leeres Feld lässt den Zweck aus.",
    modelTitle: "2. Modell",
    modelHint: "Der Provider ist eine Startentscheidung. Netz- und Datenfreigaben bleiben Kommandozeilen-Schalter und werden nie in eine Datei geschrieben.",
    providerLabel: "Provider",
    ollamaHost: "Ollama-Host",
    ollamaModel: "Ollama-Modell-ID",
    bedrockModel: "Bedrock-Modell-ID",
    awsRegion: "AWS-Region",
    gateHintFixture: "Das deterministische Fixture braucht keine Freigabe und kein Netz.",
    gateHintLoopback: "Ein Modell auf diesem Rechner braucht keine Freigabe, weil nichts die Loopback-Schnittstelle verlässt.",
    gateHintRemote: "Starte die App für diesen Provider mit --allow-network und --approve-sensitive-cloud-data.",
    runtimeTitle: "3. Laufzeit",
    stateDir: "App-State-Ordner",
    portLabel: "Port",
    outsideHome: "Ich bestätige Ordner außerhalb meines Benutzerordners",
    summaryTitle: "4. Zusammenfassung und Speichern",
    checkButton: "Prüfen",
    saveButton: "Diese zwei Dateien schreiben",
    accountLine: "Betriebssystemkonto {account} · Konfiguration in {dir}",
    checkOk: "Der Plan ist gültig. Diese zwei Dateien werden geschrieben:",
    checkFailed: "Bitte zuerst korrigieren:",
    savedTitle: "Geschrieben. Starte FolderHome mit:",
    backupNote: "Die Vorversion wurde als .bak-Datei behalten.",
    requestFailed: "Der Einrichtungsdienst hat die Anfrage abgelehnt ({status}).",
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

function renderFolders() {
  folderGrid.replaceChildren();
  const current = new Map(
    (state.current_folders || []).map((item) => [`${item.profile_id}|${item.purpose}`, item.path]),
  );
  for (const profile of state.profiles) {
    const block = document.createElement("fieldset");
    block.append(textElement("legend", `${profile.display_name} (${profile.profile_id})`));
    for (const purpose of state.purposes) {
      const label = document.createElement("label");
      label.className = "field";
      label.append(textElement("span", purpose));
      const input = document.createElement("input");
      input.spellcheck = false;
      input.dataset.profileId = profile.profile_id;
      input.dataset.purpose = purpose;
      input.value = current.get(`${profile.profile_id}|${purpose}`) || "";
      label.append(input);
      block.append(label);
    }
    folderGrid.append(block);
  }
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
    model: {
      provider: providerSelect.value,
      ollama_host: document.querySelector("#ollama-host").value.trim() || null,
      ollama_model_id: document.querySelector("#ollama-model-id").value.trim() || null,
      bedrock_model_id: document.querySelector("#bedrock-model-id").value.trim() || null,
      aws_region: document.querySelector("#aws-region").value.trim() || null,
    },
    port: Number(document.querySelector("#port").value) || 8765,
    state_dir: document.querySelector("#state-dir").value.trim(),
    profiles_dir: state.profiles_dir,
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
  summary.append(list);
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
  renderPlan(plan);
}

async function save() {
  if (!checkedPlan) return;
  const request = buildRequest();
  request.confirm = true;
  request.plan_sha256 = checkedPlan.plan_sha256;
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
  checkedPlan = null;
}

function showError(error) {
  summary.replaceChildren(textElement("p", error.message, "error"));
}

providerSelect.addEventListener("change", () => {
  document.querySelector("#ollama-fields").hidden = providerSelect.value !== "ollama";
  document.querySelector("#bedrock-fields").hidden = providerSelect.value !== "bedrock";
  saveButton.disabled = true;
  checkedPlan = null;
  renderGateHint();
});
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
    document.querySelector("#state-dir").value = payload.config_dir;
    renderFolders();
    applyTranslations();
  })
  .catch(showError);
