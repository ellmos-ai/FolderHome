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
const planSteps = document.querySelector("#plan-steps");
const initialPlanSteps = planSteps ? planSteps.cloneNode(true) : null;
const planDetectedDocs = document.querySelector("#plan-detected-docs");
const auditLine = document.querySelector("#audit-line");
const liveDataNote = document.querySelector("#live-data-note");
const modeChooser = document.querySelector("#mode-chooser");
const startCaseBtn = document.querySelector("#start-case-btn");
const startChatBtn = document.querySelector("#start-chat-btn");
const chatStaticNote = document.querySelector("#chat-static-note");
const backToChooserBtn = document.querySelector("#back-to-chooser");
const tryOwnQuestionBtn = document.querySelector("#try-own-question-btn");
const nextModeBanner = document.querySelector("#next-mode-banner");
const chatTopbarLabel = document.querySelector("#chat-topbar-label");
const sendButton = document.querySelector("#prompt-form .send-button");
const initialTranscript = transcript.cloneNode(true);

let language = "en";
let planId = SCRIPTED_PLAN_ID;
let runtimeSessionId = createRuntimeSessionId();

function getStoredMode() {
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      const stored = window.sessionStorage.getItem("folderhome-site-mode");
      if (stored === "case" || stored === "chat" || stored === "chooser") {
        return stored;
      }
    }
  } catch (_) {}
  return "chooser";
}

function storeMode(mode) {
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.setItem("folderhome-site-mode", mode);
    }
  } catch (_) {}
}

let currentMode = getStoredMode();

function setMode(mode) {
  if (mode !== "case" && mode !== "chat" && mode !== "chooser") {
    mode = "chooser";
  }
  currentMode = mode;
  if (document.documentElement) {
    if (document.documentElement.dataset) {
      document.documentElement.dataset.mode = mode;
    }
    if (typeof document.documentElement.setAttribute === "function") {
      document.documentElement.setAttribute("data-mode", mode);
    }
  }
  storeMode(mode);

  if (mode === "chooser") {
    if (modeChooser) modeChooser.hidden = false;
    if (nextModeBanner) nextModeBanner.hidden = true;
  } else if (mode === "case") {
    if (modeChooser) modeChooser.hidden = true;
    if (promptField) {
      promptField.value = DEFAULT_PROMPTS[language] || DEFAULT_PROMPTS.en;
    }
    if (sendButton) {
      sendButton.textContent = text("Build safe plan", "Sicheren Plan erstellen");
    }
    if (chatTopbarLabel) {
      const enLabel = liveConfiguration.enabled
        ? "FolderHome master · live AWS Bedrock demo"
        : "FolderHome master · fixture ready";
      const deLabel = liveConfiguration.enabled
        ? "FolderHome master · live AWS Bedrock demo"
        : "FolderHome-Master · Fixture bereit";
      chatTopbarLabel.dataset.en = enLabel;
      chatTopbarLabel.dataset.de = deLabel;
      chatTopbarLabel.textContent = text(enLabel, deLabel);
    }
  } else if (mode === "chat") {
    if (modeChooser) modeChooser.hidden = true;
    if (nextModeBanner) nextModeBanner.hidden = true;
    if (promptField) {
      if (promptField.value === DEFAULT_PROMPTS.en || promptField.value === DEFAULT_PROMPTS.de) {
        promptField.value = "";
      }
    }
    if (sendButton) {
      sendButton.textContent = text("Send prompt", "Anfrage senden");
    }
    if (chatTopbarLabel) {
      const enHeader = "Synthetic household · 104 documents · nothing here is real data";
      const deHeader = "Synthetischer Haushalt · 104 Dokumente · keine echten Daten";
      chatTopbarLabel.dataset.en = enHeader;
      chatTopbarLabel.dataset.de = deHeader;
      chatTopbarLabel.textContent = text(enHeader, deHeader);
    }
  }
}

const TOOL_LABELS = {
  search_home_documents: { en: "Search documents", de: "Suche in Dokumenten" },
  folderhome_search_documents: { en: "Search documents", de: "Suche in Dokumenten" },
  search_documents: { en: "Search documents", de: "Suche in Dokumenten" },
  topic_dossier: { en: "Topic dossier", de: "Themen-Dossier" },
  folderhome_topic_dossier: { en: "Topic dossier", de: "Themen-Dossier" },
  capabilities: { en: "Check capabilities", de: "Fähigkeiten prüfen" },
  folderhome_capabilities: { en: "Check capabilities", de: "Fähigkeiten prüfen" },
  status: { en: "Check status", de: "Status prüfen" },
  folderhome_status: { en: "Check status", de: "Status prüfen" },
  profiles: { en: "Load profiles", de: "Profile laden" },
  folderhome_profiles: { en: "Load profiles", de: "Profile laden" },
  executors: { en: "Check executors", de: "Ausführer prüfen" },
  folderhome_executors: { en: "Check executors", de: "Ausführer prüfen" },
  resources: { en: "List resources", de: "Ressourcen auflisten" },
  folderhome_resources: { en: "List resources", de: "Ressourcen auflisten" },
  results: { en: "Check results", de: "Ergebnisse prüfen" },
  folderhome_results: { en: "Check results", de: "Ergebnisse prüfen" },
  confirm_plan: { en: "Confirm plan", de: "Plan bestätigen" },
  folderhome_confirm_plan: { en: "Confirm plan", de: "Plan bestätigen" },
};

function formatToolName(name) {
  const str = String(name || "");
  if (TOOL_LABELS[str]) {
    return text(TOOL_LABELS[str].en, TOOL_LABELS[str].de);
  }
  const clean = str.replace(/^folderhome_/, "").replace(/_/g, " ");
  return clean ? clean.charAt(0).toUpperCase() + clean.slice(1) : str;
}

const WORKFLOW_LABELS = {
  search_local_documents: { en: "Search local documents", de: "Lokale Dokumente durchsuchen" },
  search_policies: { en: "Find policies", de: "Policen finden" },
  update_purpose_bound_contact: { en: "Update purpose-bound contact", de: "Zweckgebundenen Kontakt aktualisieren" },
  update_contact: { en: "Update purpose-bound contact", de: "Zweckgebundenen Kontakt aktualisieren" },
  resolve_contact: { en: "Resolve contact", de: "Kontakt ermitteln" },
  create_claim_draft: { en: "Create claim draft", de: "Schadensentwurf erstellen" },
  prepare_claim: { en: "Create claim draft", de: "Schadensentwurf erstellen" },
  add_local_follow_up: { en: "Add local follow-up", de: "Lokale Wiedervorlage hinzufügen" },
  save_follow_up: { en: "Add local follow-up", de: "Lokale Wiedervorlage hinzufügen" },
};

function formatWorkflowTitle(step) {
  if (step && step.title) return step.title;
  const wf = (step && step.workflow_id) || "";
  if (WORKFLOW_LABELS[wf]) {
    return text(WORKFLOW_LABELS[wf].en, WORKFLOW_LABELS[wf].de);
  }
  if (wf) {
    const clean = wf.replace(/_/g, " ");
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }
  return text("Step", "Schritt");
}

function formatStepDetail(step) {
  if (step && step.description) return step.description;
  const parts = [];
  if (step && step.expert_id) parts.push(step.expert_id);
  if (step && step.persona_id) parts.push(step.persona_id);
  if (step && step.status) parts.push(step.status);
  return parts.length > 0 ? parts.join(" · ") : ((step && step.workflow_id) || "");
}

function renderPlan(plan) {
  if (!plan) {
    planCard.hidden = true;
    if (confirmForm) confirmForm.hidden = true;
    return;
  }
  planId = plan.plan_id || SCRIPTED_PLAN_ID;
  if (planSteps && Array.isArray(plan.steps)) {
    planSteps.replaceChildren();
    plan.steps.forEach((step, index) => {
      const li = document.createElement("li");
      const seq = document.createElement("span");
      seq.textContent = String(step.sequence != null ? step.sequence : index + 1);
      const content = document.createElement("p");
      const title = document.createElement("b");
      title.textContent = formatWorkflowTitle(step);
      const detail = document.createElement("small");
      detail.textContent = formatStepDetail(step);
      content.append(title, detail);
      li.append(seq, content);
      planSteps.append(li);
    });
  }
  if (planDetectedDocs) {
    planDetectedDocs.replaceChildren();
    if (Array.isArray(plan.detected_documents) && plan.detected_documents.length > 0) {
      const label = document.createElement("small");
      label.className = "detected-docs-label";
      label.textContent = text("Detected documents", "Erkannte Dokumente");
      const ul = document.createElement("ul");
      ul.className = "detected-docs-list";
      plan.detected_documents.forEach((doc) => {
        const docLi = document.createElement("li");
        if (typeof doc === "string") {
          docLi.textContent = doc;
        } else if (doc && doc.filename) {
          const docName = document.createElement("code");
          docName.textContent = doc.filename;
          const docClass = document.createElement("span");
          if (doc.classification) {
            docClass.textContent = ` (${doc.classification})`;
          }
          docLi.append(docName, docClass);
        }
        ul.append(docLi);
      });
      planDetectedDocs.append(label, ul);
      planDetectedDocs.hidden = false;
    } else {
      planDetectedDocs.hidden = true;
    }
  }
  if (confirmation) {
    confirmation.value = plan.confirmation_command || `/confirm ${planId}`;
  }
  if (confirmForm) confirmForm.hidden = false;
  planCard.hidden = false;
}

function renderAudit(result) {
  if (!auditLine) return;
  if (!result || (result.network_used === undefined && result.external_actions_performed === undefined)) {
    auditLine.hidden = true;
    auditLine.replaceChildren();
    return;
  }
  const netUsed = result.network_used === true;
  let actionsCount = 0;
  if (Array.isArray(result.external_actions_performed)) {
    actionsCount = result.external_actions_performed.length;
  } else if (typeof result.external_actions_performed === "number") {
    actionsCount = result.external_actions_performed;
  } else if (result.external_actions_performed) {
    actionsCount = String(result.external_actions_performed);
  }
  auditLine.replaceChildren();
  const icon = document.createElement("span");
  icon.className = "shield";
  icon.textContent = "◇";
  const bold = document.createElement("b");
  bold.textContent = text("Audit", "Audit");
  const details = document.createElement("span");
  details.textContent = `network_used = ${netUsed} · external_actions_performed = ${actionsCount}`;
  auditLine.append(icon, bold, details);
  auditLine.hidden = false;
}

function formatApiError(status, detail) {
  if (status === 429) {
    return text(
      "Daily budget limit reached. Live turns are paused to protect cost boundaries; please try again later.",
      "Tagesbudget erreicht. Live-Züge sind zum Kostenschutz pausiert; bitte versuche es später erneut."
    );
  }
  if (status === 503) {
    return text(
      "The Bedrock runtime is currently busy or initializing. Please try again in a moment.",
      "Die Bedrock-Runtime ist ausgelastet oder initialisiert gerade. Bitte in Kürze erneut versuchen."
    );
  }
  if (status === 502) {
    return text(
      "Upstream model service temporarily unavailable. Please retry.",
      "Upstream-Modell-Dienst vorübergehend nicht erreichbar. Bitte erneut versuchen."
    );
  }
  const message = typeof detail === "string" ? detail : (detail && (detail.error || detail.message));
  return text(
    `The AWS demo is temporarily unavailable: ${message || `HTTP ${status || "unknown"}`}`,
    `Die AWS-Demo ist vorübergehend nicht verfügbar: ${message || `HTTP ${status || "unbekannt"}`}`
  );
}

function createRuntimeSessionId() {
  const randomPart = window.crypto.randomUUID().replaceAll("-", "");
  return `folderhome-public-demo-${randomPart}`;
}

function text(en, de) {
  return language === "de" ? de : en;
}

function addMessage(role, content, meta) {
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

  if (meta) {
    const metaContainer = document.createElement("div");
    metaContainer.className = "message-meta";
    let hasMeta = false;

    if (Array.isArray(meta.tool_events) && meta.tool_events.length > 0) {
      const toolList = document.createElement("div");
      toolList.className = "tool-chips";
      meta.tool_events.forEach((evt) => {
        if (!evt || !evt.tool_name) return;
        const chip = document.createElement("span");
        chip.className = `tool-chip ${evt.status === "error" ? "error" : "ok"}`;
        const toolLabel = formatToolName(evt.tool_name);
        chip.textContent = evt.status === "error" ? `${toolLabel} (${text("error", "Fehler")})` : toolLabel;
        toolList.append(chip);
      });
      if (toolList.children.length > 0) {
        metaContainer.append(toolList);
        hasMeta = true;
      }
    }

    if (typeof meta.model_turns === "number" && meta.model_turns > 0) {
      const turnChip = document.createElement("span");
      turnChip.className = "model-turns-chip";
      turnChip.textContent = meta.model_turns === 1
        ? text("1 model turn", "1 Modellzug")
        : text(`${meta.model_turns} model turns`, `${meta.model_turns} Modellzüge`);
      metaContainer.append(turnChip);
      hasMeta = true;
    }

    if (hasMeta) {
      body.append(metaContainer);
    }
  }

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
  if (!planCard.hidden && confirmation) {
    confirmation.value = `/confirm ${planId}`;
  } else if (currentMode === "case" && promptField && (promptField.value === DEFAULT_PROMPTS.en || promptField.value === DEFAULT_PROMPTS.de || !promptField.value)) {
    promptField.value = DEFAULT_PROMPTS[language];
  }
  if (currentMode === "chat") {
    if (sendButton) sendButton.textContent = text("Send prompt", "Anfrage senden");
    if (chatTopbarLabel) {
      chatTopbarLabel.textContent = text(
        "Synthetic household · 104 documents · nothing here is real data",
        "Synthetischer Haushalt · 104 Dokumente · keine echten Daten"
      );
    }
  } else if (currentMode === "case") {
    if (sendButton) sendButton.textContent = text("Build safe plan", "Sicheren Plan erstellen");
  }
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("folderhome-site-language", language);
    }
  } catch (_) {}
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelectorAll("[data-theme]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.theme === theme));
  });
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("folderhome-site-theme", theme);
    }
  } catch (_) {}
}

function resetDemo() {
  transcript.replaceChildren(...Array.from(initialTranscript.childNodes).map((node) => node.cloneNode(true)));
  promptField.value = currentMode === "case" ? DEFAULT_PROMPTS[language] : "";
  renderPlan(null);
  if (initialPlanSteps && planSteps) {
    planSteps.replaceChildren(...Array.from(initialPlanSteps.childNodes).map((node) => node.cloneNode(true)));
  }
  resultGrid.hidden = true;
  if (generatedFiles) { generatedFiles.hidden = true; generatedFiles.replaceChildren(); }
  if (auditLine) { auditLine.hidden = true; auditLine.replaceChildren(); }
  if (planDetectedDocs) { planDetectedDocs.hidden = true; planDetectedDocs.replaceChildren(); }
  if (nextModeBanner) { nextModeBanner.hidden = true; }
  confirmHelp.classList.remove("error");
  setStepState(-1);
  if (currentMode !== "chooser") {
    promptField.focus();
  }
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
  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    payload = null;
  }
  if (!response.ok) {
    const error = new Error((payload && (payload.error || payload.message)) || `HTTP ${response.status}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload || {};
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
      const meta = {
        tool_events: payload.tool_events,
        model_turns: payload.model_turns,
      };
      addMessage("assistant", payload.response || "", meta);

      // In Live-Modus statische Platzhalterkarten verbergen
      resultGrid.hidden = true;

      // Plan aus dem Payload
      if (payload.plan) {
        renderPlan(payload.plan);
        confirmHelp.classList.remove("error");
        setStepState(0);
        planCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else {
        renderPlan(null);
        // Bei Chat-Zügen ohne Plan Schritt 1 als "done"
        setStepState(1);
      }

      // Erzeugnisse nach jedem Zug
      if (payload.result && payload.result.generated_results) {
        renderGeneratedFiles(payload.result.generated_results);
      }

      // Audit rendern falls vorhanden
      if (payload.result) {
        renderAudit(payload.result);
      }

      // Prompt-Feld leeren und aktiv halten
      promptField.value = "";
    } catch (error) {
      addMessage(
        "assistant",
        formatApiError(error.status, error.payload || error.message)
      );
    } finally {
      setBusy(promptForm, false);
      promptField.focus();
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
  const entered = confirmation.value.trim();
  const expectedCommand = `/confirm ${planId}`;
  if (entered !== expectedCommand) {
    confirmHelp.textContent = text(
      `Use exactly ${expectedCommand}. Conversation text is not approval.`,
      `Verwende exakt ${expectedCommand}. Gesprächstext gilt nicht als Freigabe.`
    );
    confirmHelp.classList.add("error");
    confirmation.focus();
    return;
  }
  confirmHelp.classList.remove("error");
  if (liveConfiguration.enabled) {
    setBusy(confirmForm, true);
    try {
      const payload = await invokeLiveDemo(entered);
      const meta = {
        tool_events: payload.tool_events,
        model_turns: payload.model_turns,
      };
      addMessage("assistant", payload.response || "", meta);
      setStepState(4);
      // Statische Platzhalterkarten im Live-Modus niemals anzeigen
      resultGrid.hidden = true;
      if (payload.result) {
        renderGeneratedFiles(payload.result.generated_results);
        renderAudit(payload.result);
      }
      if (currentMode === "case" && nextModeBanner) {
        nextModeBanner.hidden = false;
      }
      (nextModeBanner && !nextModeBanner.hidden ? nextModeBanner : (generatedFiles && !generatedFiles.hidden ? generatedFiles : planCard)).scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      confirmHelp.textContent = formatApiError(error.status, error.payload || error.message);
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
  if (currentMode === "case" && nextModeBanner) {
    nextModeBanner.hidden = false;
  }
  (nextModeBanner && !nextModeBanner.hidden ? nextModeBanner : resultGrid).scrollIntoView({ behavior: "smooth", block: "nearest" });
});

resetButton.addEventListener("click", () => {
  runtimeSessionId = createRuntimeSessionId();
  planId = SCRIPTED_PLAN_ID;
  resetDemo();
  setMode("chooser");
});
if (startCaseBtn) {
  startCaseBtn.addEventListener("click", () => setMode("case"));
}
if (startChatBtn) {
  startChatBtn.addEventListener("click", () => {
    if (!startChatBtn.disabled) setMode("chat");
  });
}
if (backToChooserBtn) {
  backToChooserBtn.addEventListener("click", () => setMode("chooser"));
}
if (tryOwnQuestionBtn) {
  tryOwnQuestionBtn.addEventListener("click", () => setMode("chat"));
}
document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});
document.querySelectorAll("[data-theme]").forEach((button) => {
  button.addEventListener("click", () => setTheme(button.dataset.theme));
});
document.querySelectorAll(".prompt-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    if (chip.dataset.action === "switch-case") {
      setMode("case");
      return;
    }
    const textKey = language === "de" ? "promptDe" : "promptEn";
    const promptText = chip.dataset[textKey]
      || chip.dataset[language]
      || chip.textContent.trim();
    promptField.value = promptText;
    promptField.focus();
  });
});

function updateLiveConfigUI() {
  if (liveConfiguration.enabled) {
    if (startChatBtn) startChatBtn.disabled = false;
    if (chatStaticNote) chatStaticNote.hidden = true;
  } else {
    if (startChatBtn) startChatBtn.disabled = true;
    if (chatStaticNote) chatStaticNote.hidden = false;
  }
}

const savedLanguage = (function () {
  try { return window.localStorage ? window.localStorage.getItem("folderhome-site-language") : null; } catch (_) { return null; }
})();
const savedTheme = (function () {
  try { return window.localStorage ? window.localStorage.getItem("folderhome-site-theme") : null; } catch (_) { return null; }
})();
setLanguage(savedLanguage === "de" ? "de" : "en");
setTheme(savedTheme === "light" ? "light" : "dark");
setStepState(-1);
updateLiveConfigUI();
setMode(currentMode);

if (liveConfiguration.enabled) {
  if (chatTopbarLabel && currentMode === "case") {
    chatTopbarLabel.dataset.en = "FolderHome master · live AWS Bedrock demo";
    chatTopbarLabel.dataset.de = "FolderHome-Master · Live-AWS-Bedrock-Demo";
  }
  const disclosureTitle = document.querySelector(".disclosure strong");
  const disclosureText = document.querySelector(".disclosure span");
  if (disclosureTitle) {
    disclosureTitle.dataset.en = "Live synthetic AWS walkthrough";
    disclosureTitle.dataset.de = "Synthetische Live-AWS-Demo";
  }
  if (disclosureText) {
    disclosureText.dataset.en = "This AWS-hosted page runs the real FolderHome master agent on a synthetic household of 104 example documents. External actions stay disabled; every turn is budget-metered.";
    disclosureText.dataset.de = "Diese AWS-gehostete Seite führt den echten FolderHome-Master-Agenten auf einem synthetischen Haushalt mit 104 Beispieldokumenten aus. Externe Aktionen bleiben deaktiviert; jeder Zug ist budgetbegrenzt.";
  }
  const liveDataNoteElement = document.querySelector("#live-data-note");
  if (liveDataNoteElement) liveDataNoteElement.hidden = false;
  const figcaption = document.querySelector(".architecture-diagram figcaption");
  if (figcaption) {
    figcaption.dataset.en = "Synthetic accident-demo view: four demo adapters in the guided case; the free chat uses the full read-only tool set on a synthetic household. The hosted runtime was verified live with Amazon Bedrock on 2026-09-13. Household execution stays local behind exact confirmation.";
    figcaption.dataset.de = "Synthetische Unfall-Demo: vier Demo-Adapter im geführten Fall; der freie Chat nutzt das volle Lesewerkzeug-Set auf einem synthetischen Haushalt. Die gehostete Runtime wurde am 13.09.2026 live mit Amazon Bedrock verifiziert. Haushaltsausführung bleibt lokal hinter exakter Bestätigung.";
  }
  const slide0 = document.querySelector('.architecture-diagram .slide[data-index="0"]');
  if (slide0) {
    slide0.dataset.captionEn = "Synthetic accident-demo view: four demo adapters in the guided case; the free chat uses the full read-only tool set on a synthetic household. The hosted runtime was verified live with Amazon Bedrock on 2026-09-13. Household execution stays local behind exact confirmation.";
    slide0.dataset.captionDe = "Synthetische Unfall-Demo: vier Demo-Adapter im geführten Fall; der freie Chat nutzt das volle Lesewerkzeug-Set auf einem synthetischen Haushalt. Die gehostete Runtime wurde am 13.09.2026 live mit Amazon Bedrock verifiziert. Haushaltsausführung bleibt lokal hinter exakter Bestätigung.";
  }
  setLanguage(language);
}

/* --- Architecture Slideshow Block --- */
(function initArchitectureSlideshow() {
  const container = document.querySelector(".architecture-diagram");
  if (!container) return;

  const slides = Array.from(container.querySelectorAll(".slide"));
  const dots = Array.from(container.querySelectorAll(".slideshow-dot"));
  const prevBtn = container.querySelector("#arch-prev");
  const nextBtn = container.querySelector("#arch-next");
  const caption = container.querySelector("#architecture-caption");
  const fullsizeLink = document.querySelector("#architecture-fullsize-link");

  if (slides.length === 0) return;

  let currentSlideIndex = 0;

  function updateSlide(targetIndex) {
    if (targetIndex < 0) {
      targetIndex = slides.length - 1;
    } else if (targetIndex >= slides.length) {
      targetIndex = 0;
    }
    currentSlideIndex = targetIndex;

    slides.forEach((slide, idx) => {
      const isCurrent = idx === currentSlideIndex;
      slide.hidden = !isCurrent;
      if (isCurrent) {
        slide.classList.add("active");
      } else {
        slide.classList.remove("active");
      }
    });

    dots.forEach((dot, idx) => {
      const isCurrent = idx === currentSlideIndex;
      if (isCurrent) {
        dot.classList.add("active");
      } else {
        dot.classList.remove("active");
      }
      dot.setAttribute("aria-selected", String(isCurrent));
    });

    const activeSlide = slides[currentSlideIndex];
    if (activeSlide && caption) {
      const capEn = activeSlide.dataset.captionEn || "";
      const capDe = activeSlide.dataset.captionDe || "";
      caption.dataset.en = capEn;
      caption.dataset.de = capDe;
      caption.textContent = language === "de" ? capDe : capEn;
    }

    if (activeSlide && fullsizeLink) {
      const img = activeSlide.querySelector("img");
      const src = (img && typeof img.getAttribute === "function" ? img.getAttribute("src") : (img && img.src)) || "";
      if (src) {
        fullsizeLink.href = src;
      }
    }
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      updateSlide(currentSlideIndex - 1);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      updateSlide(currentSlideIndex + 1);
    });
  }

  dots.forEach((dot, idx) => {
    dot.addEventListener("click", () => {
      updateSlide(idx);
    });
  });

  container.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      updateSlide(currentSlideIndex - 1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      updateSlide(currentSlideIndex + 1);
    }
  });

  let touchStartX = null;
  container.addEventListener(
    "touchstart",
    (event) => {
      if (event.touches && event.touches.length > 0) {
        touchStartX = event.touches[0].clientX;
      }
    },
    { passive: true }
  );

  container.addEventListener(
    "touchend",
    (event) => {
      if (touchStartX === null) return;
      if (event.changedTouches && event.changedTouches.length > 0) {
        const deltaX = event.changedTouches[0].clientX - touchStartX;
        if (Math.abs(deltaX) > 40) {
          if (deltaX > 0) {
            updateSlide(currentSlideIndex - 1);
          } else {
            updateSlide(currentSlideIndex + 1);
          }
        }
      }
      touchStartX = null;
    },
    { passive: true }
  );

  updateSlide(0);
})();

