const scriptUrl = new URL(document.currentScript.src);
const token = scriptUrl.searchParams.get("token") || "";

const copy = {
  en: {
    skip: "Skip to the demo",
    eyebrow: "Local-first household document agent",
    headline: "From accident paperwork to a safe next step.",
    lede: "FolderHome finds the current policy, preserves older evidence, identifies the responsible contact, drafts a letter, and records a local follow-up — with one explicit confirmation.",
    synthetic: "Synthetic demo data",
    noExternal: "No mail, call, or external calendar",
    forWhom: "For people managing scattered household documents",
    impact: "Less searching. Clearer decisions. Deliberate actions.",
    liveJourney: "Reproducible product journey",
    chatTitle: "Talk to the FolderHome master agent",
    welcome: "This fixture runs the real local agent and real FolderHome tools. It never uses personal data.",
    promptLabel: "Your request",
    prepare: "Find and prepare",
    reset: "Reset demo",
    evidence: "Evidence, plan, and results",
    stateTitle: "Nothing runs silently",
    found: "Found",
    planned: "Planned",
    approval: "Confirmation required",
    executed: "Executed",
    externalActions: "External actions",
    simulatedOnly: "Simulation only",
    waiting: "Waiting",
    ready: "Fixture ready",
    blocked: "Blocked",
    working: "Working …",
    currentPolicy: "Current policy",
    olderPolicy: "Older evidence",
    planId: "Hash-bound plan",
    confirmLabel: "Exact confirmation command",
    confirm: "Confirm and run locally",
    results: "Generated local results",
    beforeState: "Before · source documents",
    afterState: "After · generated results",
    noSourceFiles: "Waiting for document search",
    noGeneratedFiles: "No generated results yet",
    openResult: "Open",
    downloadResult: "Download",
    noExternalResult: "No email, phone call, external calendar action, or automatic archive was performed.",
    architecture: "Architecture",
    oneLoop: "One agent loop, bounded tools",
    person: "Person",
    tools: "Local tools",
    outputs: "Local outputs",
    boundaries: "Security boundaries",
    safeByDesign: "Safe by construction",
    boundaryOne: "Synthetic fixtures only; no uploads or personal paths.",
    boundaryTwo: "Conversation never counts as approval.",
    boundaryThree: "Older policies are proposed for archiving, not moved.",
    boundaryFour: "The follow-up stays in FolderHome's local calendar.",
    videoPending: "Verified demo video pending",
    footer: "Fixture runtime: local, reversible where supported, and explicit about what did not happen.",
    resetDone: "The synthetic workspace is ready for another run.",
  },
  de: {
    skip: "Zur Demo springen",
    eyebrow: "Lokaler Agent für Haushaltsdokumente",
    headline: "Vom Unfallpapier zum sicheren nächsten Schritt.",
    lede: "FolderHome findet den aktuellen Vertrag, bewahrt ältere Belege, ermittelt den zuständigen Kontakt, entwirft ein Schreiben und hält eine lokale Wiedervorlage fest — nach einer ausdrücklichen Bestätigung.",
    synthetic: "Synthetische Demodaten",
    noExternal: "Keine Mail, kein Anruf, kein externer Kalender",
    forWhom: "Für Menschen mit verteilten Haushaltsdokumenten",
    impact: "Weniger suchen. Klarer entscheiden. Bewusst handeln.",
    liveJourney: "Reproduzierbare Produktgeschichte",
    chatTitle: "Mit dem FolderHome-Master-Agenten sprechen",
    welcome: "Diese Fixture verwendet den echten lokalen Agenten und echte FolderHome-Werkzeuge. Sie nutzt keine persönlichen Daten.",
    promptLabel: "Deine Anfrage",
    prepare: "Finden und vorbereiten",
    reset: "Demo zurücksetzen",
    evidence: "Evidenz, Plan und Ergebnisse",
    stateTitle: "Nichts läuft unbemerkt",
    found: "Gefunden",
    planned: "Geplant",
    approval: "Bestätigung erforderlich",
    executed: "Ausgeführt",
    externalActions: "Externe Aktionen",
    simulatedOnly: "Nur simuliert",
    waiting: "Wartet",
    ready: "Fixture bereit",
    blocked: "Blockiert",
    working: "Arbeitet …",
    currentPolicy: "Aktueller Vertrag",
    olderPolicy: "Älterer Beleg",
    planId: "Hashgebundener Plan",
    confirmLabel: "Exakter Bestätigungsbefehl",
    confirm: "Bestätigen und lokal ausführen",
    results: "Erzeugte lokale Ergebnisse",
    beforeState: "Vorher · Quelldokumente",
    afterState: "Nachher · erzeugte Ergebnisse",
    noSourceFiles: "Wartet auf die Dokumentensuche",
    noGeneratedFiles: "Noch keine Ergebnisse erzeugt",
    openResult: "Öffnen",
    downloadResult: "Herunterladen",
    noExternalResult: "Es wurden keine E-Mail, kein Anruf, kein externer Kalendereintrag und keine automatische Archivierung ausgeführt.",
    architecture: "Architektur",
    oneLoop: "Ein Agentenloop, begrenzte Werkzeuge",
    person: "Mensch",
    tools: "Lokale Werkzeuge",
    outputs: "Lokale Ergebnisse",
    boundaries: "Sicherheitsgrenzen",
    safeByDesign: "Sicher durch Konstruktion",
    boundaryOne: "Nur synthetische Fixtures; keine Uploads oder persönlichen Pfade.",
    boundaryTwo: "Ein Gespräch gilt niemals als Freigabe.",
    boundaryThree: "Ältere Verträge werden zur Archivierung vorgeschlagen, nicht verschoben.",
    boundaryFour: "Die Wiedervorlage bleibt im lokalen FolderHome-Kalender.",
    videoPending: "Verifiziertes Demovideo folgt",
    footer: "Fixture-Laufzeit: lokal, soweit unterstützt reversibel und eindeutig darüber, was nicht passiert ist.",
    resetDone: "Der synthetische Arbeitsbereich ist für einen weiteren Lauf bereit.",
  },
};

let language = localStorage.getItem("folderhome-demo-language") === "de" ? "de" : "en";
let theme = localStorage.getItem("folderhome-demo-theme") === "dark" ? "dark" : "light";
let defaultPrompt = "";

const prompt = document.querySelector("#prompt");
const promptForm = document.querySelector("#prompt-form");
const confirmForm = document.querySelector("#confirm-form");
const confirmCommand = document.querySelector("#confirm-command");
const transcript = document.querySelector("#transcript");
const runtimeStatus = document.querySelector("#runtime-status");
const statusItems = [...document.querySelectorAll("#status-list li")];
const planView = document.querySelector("#plan-view");
const results = document.querySelector("#results");
const resetButton = document.querySelector("#reset");
const beforeFiles = document.querySelector("#before-files");
const afterFiles = document.querySelector("#after-files");

function t(key) { return copy[language][key] || key; }

function setLanguage(value) {
  language = value;
  localStorage.setItem("folderhome-demo-language", value);
  document.documentElement.lang = value;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === value));
  });
}

function setTheme(value) {
  theme = value;
  localStorage.setItem("folderhome-demo-theme", value);
  document.documentElement.dataset.theme = value;
  document.querySelectorAll("[data-theme-mode]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.themeMode === value));
  });
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-FolderHome-Token", token);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers, credentials: "omit" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || `HTTP ${response.status}`);
  return payload;
}

function addMessage(kind, value) {
  const article = document.createElement("article");
  article.className = `message ${kind}`;
  const speaker = document.createElement("span");
  speaker.textContent = kind === "assistant" ? "FH" : "YOU";
  const text = document.createElement("p");
  text.textContent = value;
  article.append(speaker, text);
  transcript.append(article);
  transcript.scrollTop = transcript.scrollHeight;
}

function setSteps(states) {
  statusItems.forEach((item, index) => {
    const state = states[index] || (index === 4 ? "simulated" : "idle");
    item.dataset.state = state;
    item.querySelector("small").textContent = state === "done"
      ? t("executed")
      : state === "active"
        ? t("working")
        : state === "blocked"
          ? t("blocked")
          : state === "simulated"
            ? t("simulatedOnly")
          : t("waiting");
  });
}

function renderFileList(container, filenames, emptyKey) {
  const items = filenames.length
    ? filenames.map((filename) => {
        const item = document.createElement("li");
        item.textContent = filename;
        return item;
      })
    : (() => {
        const item = document.createElement("li");
        item.textContent = t(emptyKey);
        return [item];
      })();
  container.replaceChildren(...items);
}

function tokenizedUrl(path) {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("token", token);
  return `${url.pathname}${url.search}`;
}

function renderPlan(plan) {
  planView.hidden = false;
  const title = document.createElement("p");
  const titleLabel = document.createElement("strong");
  titleLabel.dataset.i18n = "planId";
  titleLabel.textContent = t("planId");
  const titleBreak = document.createElement("br");
  const titleCode = document.createElement("code");
  titleCode.textContent = `${plan.plan_id} · ${plan.plan_sha256}`;
  title.append(titleLabel, titleBreak, titleCode);
  const docs = plan.detected_documents.map((item) => {
    const line = document.createElement("div");
    line.className = "plan-step";
    const label = document.createElement("strong");
    label.dataset.i18n = item.classification === "current"
      ? "currentPolicy"
      : "olderPolicy";
    label.textContent = t(label.dataset.i18n);
    line.append(label, document.createTextNode(`: ${item.filename}`));
    return line;
  });
  const steps = plan.steps.map((item) => {
    const line = document.createElement("div");
    line.className = "plan-step";
    const strong = document.createElement("strong");
    strong.textContent = `${item.sequence}. ${item.workflow_id}`;
    const small = document.createElement("small");
    small.textContent = `${item.expert_id} · ${item.request_sha256.slice(0, 16)}…`;
    line.append(strong, small);
    return line;
  });
  planView.replaceChildren(title, ...docs, ...steps);
  renderFileList(
    beforeFiles,
    plan.detected_documents.map((item) => item.filename),
    "noSourceFiles",
  );
  renderFileList(afterFiles, [], "noGeneratedFiles");
  confirmCommand.value = plan.confirmation_command;
  confirmForm.hidden = false;
}

function renderResults(items) {
  results.hidden = false;
  const heading = document.createElement("h3");
  heading.dataset.i18n = "results";
  heading.textContent = t("results");
  const links = items.map((item) => {
    const row = document.createElement("div");
    row.className = "result-row";
    const label = document.createElement("code");
    label.textContent = `${item.filename} · SHA-256 ${item.sha256.slice(0, 16)}…`;
    const actions = document.createElement("div");
    actions.className = "result-actions";
    const view = document.createElement("a");
    view.href = tokenizedUrl(item.view_url);
    view.target = "_blank";
    view.rel = "noopener noreferrer";
    view.dataset.i18n = "openResult";
    view.textContent = t("openResult");
    const download = document.createElement("a");
    download.href = tokenizedUrl(item.download_url);
    download.download = item.filename;
    download.dataset.i18n = "downloadResult";
    download.textContent = t("downloadResult");
    actions.append(view, download);
    row.append(label, actions);
    return row;
  });
  const boundary = document.createElement("p");
  boundary.dataset.i18n = "noExternalResult";
  boundary.textContent = t("noExternalResult");
  results.replaceChildren(heading, ...links, boundary);
  renderFileList(afterFiles, items.map((item) => item.filename), "noGeneratedFiles");
}

function setBusy(busy) {
  [...document.querySelectorAll("button")].forEach((button) => { button.disabled = busy; });
  runtimeStatus.textContent = busy ? t("working") : t("ready");
  runtimeStatus.dataset.state = busy ? "checking" : "ready";
}

promptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = prompt.value.trim();
  addMessage("user", value);
  setBusy(true);
  setSteps(["active", "idle", "idle", "idle"]);
  try {
    const response = await api("/demo/api/prepare", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.synthetic-accident-demo-prepare-request.v1",
        prompt: value,
      }),
    });
    renderPlan(response.plan);
    addMessage("assistant", response.plan.agent_search.response_text);
    setSteps(["done", "done", "active", "idle"]);
  } catch (error) {
    addMessage("assistant", error.message);
    setSteps(["blocked", "idle", "idle", "idle"]);
    runtimeStatus.dataset.state = "blocked";
    runtimeStatus.textContent = t("blocked");
  } finally {
    setBusy(false);
  }
});

confirmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  setSteps(["done", "done", "active", "idle"]);
  try {
    const response = await api("/demo/api/confirm", {
      method: "POST",
      body: JSON.stringify({
        schema: "folderhome.synthetic-accident-demo-confirm-request.v1",
        command: confirmCommand.value.trim(),
      }),
    });
    addMessage("assistant", t("noExternalResult"));
    renderResults(response.result.generated_results);
    confirmForm.hidden = true;
    setSteps(["done", "done", "done", "done"]);
  } catch (error) {
    addMessage("assistant", error.message);
    setSteps(["done", "done", "blocked", "idle"]);
  } finally {
    setBusy(false);
  }
});

resetButton.addEventListener("click", async () => {
  setBusy(true);
  try {
    await api("/demo/api/reset", {
      method: "POST",
      body: JSON.stringify({ schema: "folderhome.synthetic-accident-demo-reset-request.v1" }),
    });
    transcript.querySelectorAll(".message:not(:first-child)").forEach((node) => node.remove());
    addMessage("assistant", t("resetDone"));
    prompt.value = defaultPrompt;
    planView.hidden = true;
    confirmForm.hidden = true;
    results.hidden = true;
    renderFileList(beforeFiles, [], "noSourceFiles");
    renderFileList(afterFiles, [], "noGeneratedFiles");
    setSteps(["idle", "idle", "idle", "idle"]);
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    setBusy(false);
  }
});

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});
document.querySelectorAll("[data-theme-mode]").forEach((button) => {
  button.addEventListener("click", () => setTheme(button.dataset.themeMode));
});

setLanguage(language);
setTheme(theme);
api("/demo/api/status")
  .then((response) => {
    defaultPrompt = response.default_prompt;
    prompt.value = defaultPrompt;
    runtimeStatus.dataset.state = "ready";
    runtimeStatus.textContent = t("ready");
  })
  .catch((error) => {
    runtimeStatus.dataset.state = "blocked";
    runtimeStatus.textContent = t("blocked");
    addMessage("assistant", error.message);
  });
