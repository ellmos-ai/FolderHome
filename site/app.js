"use strict";

const SCRIPTED_PLAN_ID = "accident_demo_94b8b3bd56d00cafe000000000000001";
const liveConfiguration = window.FOLDERHOME_LIVE_DEMO || { enabled: false };
const cloudModeBadge = document.querySelector("#cloud-mode-badge");
if (cloudModeBadge) cloudModeBadge.hidden = liveConfiguration.enabled !== true;
const DEFAULT_PROMPTS = {
  en: "I had an accident with my Hyundai i10. Find my current car insurance, compare it with older policies, identify the right contact, prepare a claim letter, and save the next follow-up locally.",
  de: "Ich hatte einen Unfall mit meinem Hyundai i10. Finde meine aktuelle KFZ-Versicherung, vergleiche sie mit älteren Policen, ermittle den richtigen Kontakt, bereite eine Schadensmeldung vor und speichere die nächste Wiedervorlage lokal.",
};

const transcript = document.querySelector("#transcript");
const promptForm = document.querySelector("#prompt-form");
const promptField = document.querySelector("#prompt");
const planCard = document.querySelector("#plan-card");
const confirmForm = document.querySelector("#confirm-form");
const confirmation = document.querySelector("#confirmation");
const confirmHelp = document.querySelector("#confirm-help");
const resultGrid = document.querySelector("#result-grid");
const generatedFiles = document.querySelector("#generated-files");
const resetButton = document.querySelector("#reset-demo");
const workflowSteps = Array.from(document.querySelectorAll("#workflow-steps li"));
const initialTranscript = transcript.cloneNode(true);

let language = "en";
let planId = SCRIPTED_PLAN_ID;
let runtimeSessionId = createRuntimeSessionId();

function createRuntimeSessionId() {
  const randomPart = window.crypto.randomUUID().replaceAll("-", "");
  return `folderhome-public-demo-${randomPart}`;
}

function text(en, de) {
  return language === "de" ? de : en;
}

function addMessage(role, content) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const speaker = document.createElement("span");
  speaker.className = "speaker";
  speaker.textContent = role === "user" ? "YOU" : "FH";
  const body = document.createElement("div");
  const label = document.createElement("small");
  label.textContent = role === "user" ? text("YOU", "DU") : "FOLDERHOME";
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  body.append(label, paragraph);
  article.append(speaker, body);
  transcript.append(article);
  transcript.scrollTop = transcript.scrollHeight;
}

function decodeResult(entry) {
  if (entry.content_encoding === "base64") {
    const binary = window.atob(entry.content);
    const bytes = Uint8Array.from(binary, (ch) => ch.charCodeAt(0));
    return new Blob([bytes], { type: entry.content_type || "application/octet-stream" });
  }
  return new Blob([entry.content], { type: entry.content_type || "text/plain; charset=utf-8" });
}

function formatBytes(size) {
  return size < 1024 ? `${size} B` : `${(size / 1024).toFixed(1)} KB`;
}

// The runtime carries every generated file inline (text or base64, sha256, size);
// the cloud page has no file route, so viewing and downloading happen from that payload.
function renderGeneratedFiles(entries) {
  if (!generatedFiles) return;
  generatedFiles.replaceChildren();
  const files = Array.isArray(entries)
    ? entries.filter((e) => e && e.inline === true && typeof e.content === "string")
    : [];
  if (files.length === 0) {
    generatedFiles.hidden = true;
    return;
  }
  const heading = document.createElement("h3");
  heading.textContent = text("Generated files (synthetic, from this run)", "Erzeugte Dateien (synthetisch, aus diesem Lauf)");
  generatedFiles.append(heading);
  files.forEach((entry) => {
    const article = document.createElement("article");
    const icon = document.createElement("span");
    icon.className = "result-icon";
    icon.textContent = entry.filename.endsWith(".json") ? "{}" : "¶";
    const meta = document.createElement("div");
    const kind = document.createElement("small");
    kind.textContent = String(entry.content_type || "").split(";")[0].toUpperCase();
    const name = document.createElement("b");
    name.textContent = entry.filename;
    const info = document.createElement("p");
    info.textContent = `${formatBytes(entry.size_bytes || 0)} · sha256 ${String(entry.sha256 || "").slice(0, 12)}…`;
    meta.append(kind, name, info);
    const actions = document.createElement("span");
    actions.className = "file-actions";
    const view = document.createElement("button");
    view.type = "button";
    view.className = "file-action";
    view.textContent = text("View", "Ansehen");
    const download = document.createElement("a");
    download.className = "file-action";
    download.textContent = text("Download", "Herunterladen");
    download.download = entry.filename;
    download.href = URL.createObjectURL(decodeResult(entry));
    actions.append(view, download);
    article.append(icon, meta, actions);
    const preview = document.createElement("pre");
    preview.className = "file-preview";
    preview.hidden = true;
    preview.textContent = entry.content_encoding === "base64"
      ? text("Binary content; use Download.", "Binärinhalt; bitte herunterladen.")
      : entry.content;
    view.addEventListener("click", () => {
      preview.hidden = !preview.hidden;
      view.textContent = preview.hidden ? text("View", "Ansehen") : text("Hide", "Ausblenden");
    });
    generatedFiles.append(article, preview);
  });
  generatedFiles.hidden = false;
}

function setStepState(doneCount) {
  workflowSteps.forEach((step, index) => {
    step.dataset.state = index < doneCount ? "done" : index === doneCount ? "active" : "idle";
  });
}

function setLanguage(nextLanguage) {
  language = nextLanguage;
  document.documentElement.lang = language;
  document.querySelectorAll("[data-en][data-de]").forEach((node) => {
    node.textContent = node.dataset[language];
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === language));
  });
  if (!planCard.hidden) {
    confirmation.value = `/confirm ${planId}`;
  } else {
    promptField.value = DEFAULT_PROMPTS[language];
  }
  localStorage.setItem("folderhome-site-language", language);
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelectorAll("[data-theme]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.theme === theme));
  });
  localStorage.setItem("folderhome-site-theme", theme);
}

function resetDemo() {
  transcript.replaceChildren(...Array.from(initialTranscript.childNodes).map((node) => node.cloneNode(true)));
  promptField.value = DEFAULT_PROMPTS[language];
  planCard.hidden = true;
  resultGrid.hidden = true;
  if (generatedFiles) { generatedFiles.hidden = true; generatedFiles.replaceChildren(); }
  confirmHelp.classList.remove("error");
  setStepState(-1);
  promptField.focus();
}

async function invokeLiveDemo(prompt) {
  const headers = { "Content-Type": "application/json" };
  if (liveConfiguration.apiKey) {
    headers["X-Api-Key"] = liveConfiguration.apiKey;
  }
  const response = await fetch(liveConfiguration.apiBaseUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({ prompt, session_id: runtimeSessionId }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
  }
  return payload;
}

function setBusy(form, busy) {
  Array.from(form.elements).forEach((element) => {
    element.disabled = busy;
  });
}

promptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptField.value.trim();
  if (!prompt) {
    promptField.focus();
    return;
  }
  addMessage("user", prompt);
  if (liveConfiguration.enabled) {
    setBusy(promptForm, true);
    try {
      const payload = await invokeLiveDemo(prompt);
      planId = payload.plan.plan_id;
      addMessage("assistant", payload.response);
      planCard.hidden = false;
      resultGrid.hidden = true;
  if (generatedFiles) { generatedFiles.hidden = true; generatedFiles.replaceChildren(); }
      confirmation.value = `/confirm ${planId}`;
      confirmHelp.classList.remove("error");
      setStepState(0);
      planCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      addMessage(
        "assistant",
        text(`The AWS demo is temporarily unavailable: ${error.message}`, `Die AWS-Demo ist vorübergehend nicht verfügbar: ${error.message}`)
      );
    } finally {
      setBusy(promptForm, false);
    }
    return;
  }
  addMessage(
    "assistant",
    text(
      "I found the current synthetic policy SYN-I10-2026 and the older policy SYN-I10-2025. Review the hash-bound plan below; no action has run.",
      "Ich habe die aktuelle synthetische Police SYN-I10-2026 und die ältere Police SYN-I10-2025 gefunden. Prüfe den hashgebundenen Plan unten; es wurde noch nichts ausgeführt."
    )
  );
  planCard.hidden = false;
  resultGrid.hidden = true;
  if (generatedFiles) { generatedFiles.hidden = true; generatedFiles.replaceChildren(); }
  confirmation.value = `/confirm ${planId}`;
  confirmHelp.classList.remove("error");
  setStepState(0);
  planCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

confirmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (confirmation.value.trim() !== `/confirm ${planId}`) {
    confirmHelp.textContent = text(
      `Use exactly /confirm ${planId}. Conversation text is not approval.`,
      `Verwende exakt /confirm ${planId}. Gesprächstext gilt nicht als Freigabe.`
    );
    confirmHelp.classList.add("error");
    confirmation.focus();
    return;
  }
  confirmHelp.classList.remove("error");
  if (liveConfiguration.enabled) {
    setBusy(confirmForm, true);
    try {
      const payload = await invokeLiveDemo(confirmation.value.trim());
      addMessage("assistant", payload.response);
      setStepState(4);
      resultGrid.hidden = false;
      renderGeneratedFiles(payload.result && payload.result.generated_results);
      (generatedFiles && !generatedFiles.hidden ? generatedFiles : resultGrid).scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      confirmHelp.textContent = text(
        `The AWS demo is temporarily unavailable: ${error.message}`,
        `Die AWS-Demo ist vorübergehend nicht verfügbar: ${error.message}`
      );
      confirmHelp.classList.add("error");
    } finally {
      setBusy(confirmForm, false);
    }
    return;
  }
  addMessage(
    "assistant",
    text(
      "Confirmed. The walkthrough now shows the four synthetic local results. No email was sent, no cloud was called and the older policy was not archived automatically.",
      "Bestätigt. Der Rundgang zeigt nun die vier synthetischen lokalen Ergebnisse. Es wurde keine E-Mail gesendet, keine Cloud aufgerufen und die ältere Police nicht automatisch archiviert."
    )
  );
  setStepState(4);
  resultGrid.hidden = false;
  resultGrid.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

resetButton.addEventListener("click", () => {
  runtimeSessionId = createRuntimeSessionId();
  planId = SCRIPTED_PLAN_ID;
  resetDemo();
});
document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});
document.querySelectorAll("[data-theme]").forEach((button) => {
  button.addEventListener("click", () => setTheme(button.dataset.theme));
});

const savedLanguage = localStorage.getItem("folderhome-site-language");
const savedTheme = localStorage.getItem("folderhome-site-theme");
setLanguage(savedLanguage === "de" ? "de" : "en");
setTheme(savedTheme === "light" ? "light" : "dark");
setStepState(-1);

if (liveConfiguration.enabled) {
  const runtimeLabel = document.querySelector(".chat-topbar span");
  runtimeLabel.dataset.en = "FolderHome master · live AWS Bedrock demo";
  runtimeLabel.dataset.de = "FolderHome-Master · Live-AWS-Bedrock-Demo";
  const disclosureTitle = document.querySelector(".disclosure strong");
  const disclosureText = document.querySelector(".disclosure span");
  disclosureTitle.dataset.en = "Live synthetic AWS walkthrough";
  disclosureTitle.dataset.de = "Synthetische Live-AWS-Demo";
  disclosureText.dataset.en = "This AWS-hosted page invokes the bounded AgentCore runtime with synthetic data only. External actions remain disabled.";
  disclosureText.dataset.de = "Diese AWS-gehostete Seite ruft die begrenzte AgentCore-Runtime ausschließlich mit synthetischen Daten auf. Externe Aktionen bleiben deaktiviert.";
  const figcaption = document.querySelector(".architecture-diagram figcaption");
  figcaption.dataset.en = "Synthetic accident-demo view: four demo adapters, not the full endpoint catalog. This AWS page is configured to invoke AgentCore; configuration alone does not prove a successful model call. Household execution remains local behind exact confirmation.";
  figcaption.dataset.de = "Synthetische Unfall-Demo: vier Demo-Adapter, nicht der gesamte Endpunktkatalog. Diese AWS-Seite ist für AgentCore-Aufrufe konfiguriert; die Konfiguration allein belegt keinen erfolgreichen Modellaufruf. Haushaltsausführung bleibt lokal hinter exakter Bestätigung.";
  setLanguage(language);
}
