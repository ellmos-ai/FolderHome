"use strict";

const SCRIPTED_PLAN_ID = "accident_demo_94b8b3bd56d00cafe000000000000001";
const liveConfiguration = window.FOLDERHOME_LIVE_DEMO || { enabled: false };
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
      resultGrid.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
  figcaption.dataset.en = "Live architecture: this AWS page invokes the synthetic AgentCore runtime; real household execution remains local behind exact confirmation.";
  figcaption.dataset.de = "Live-Architektur: Diese AWS-Seite ruft die synthetische AgentCore-Runtime auf; echte Haushaltsausführung bleibt lokal hinter der exakten Bestätigung.";
  setLanguage(language);
}
