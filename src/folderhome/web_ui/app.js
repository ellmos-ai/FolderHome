"use strict";

const token = new URLSearchParams(window.location.search).get("token") || "";
const profileSelect = document.querySelector("#profile-select");
const resultSection = document.querySelector("#result-section");
const resultContent = document.querySelector("#result-content");
const resultCount = document.querySelector("#result-count");
const queryInput = document.querySelector("#query");
const connectionState = document.querySelector("#connection-state");
const actionButtons = [...document.querySelectorAll(".actions button")];

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-FolderHome-Token", token);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers, credentials: "omit" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || `Lokaler Fehler ${response.status}`);
  return payload;
}

function textElement(tag, value, className = "") {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}

function showError(error) {
  resultSection.hidden = false;
  resultCount.textContent = "blockiert";
  resultContent.replaceChildren(textElement("div", error.message, "result-card error"));
}

function showSearch(payload) {
  const hits = payload.result.hits;
  resultSection.hidden = false;
  resultCount.textContent = `${hits.length} Fundstelle${hits.length === 1 ? "" : "n"}`;
  const cards = hits.map((hit) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.append(textElement("h3", hit.filename));
    card.append(textElement("p", hit.snippet.replaceAll(">>>", "").replaceAll("<<<", "")));
    return card;
  });
  if (!cards.length) cards.push(textElement("div", "Keine lokale Fundstelle gefunden.", "result-card"));
  resultContent.replaceChildren(...cards);
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showDossier(payload) {
  resultSection.hidden = false;
  resultCount.textContent = `${payload.result.total_hits} Fundstellen`;
  resultContent.replaceChildren(textElement("div", payload.result.markdown, "dossier"));
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function runSearch(mode) {
  const value = queryInput.value.trim();
  if (!value) {
    queryInput.focus();
    return;
  }
  const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  resultSection.hidden = false;
  resultSection.setAttribute("aria-busy", "true");
  actionButtons.forEach((button) => { button.disabled = true; });
  resultCount.textContent = "läuft";
  resultContent.replaceChildren(textElement("div", "Der lokale Index wird durchsucht …", "result-card"));
  const isDossier = mode === "dossier";
  try {
    const payload = await api(`/api/v1/documents/${isDossier ? "dossier" : "search"}`, {
      method: "POST",
      body: JSON.stringify({
        schema: isDossier ? "folderhome.local-dossier-request.v1" : "folderhome.local-search-request.v1",
        profile_id: profileSelect.value,
        [isDossier ? "topic" : "query"]: value,
        limit: isDossier ? 25 : 10,
      }),
    });
    if (isDossier) showDossier(payload); else showSearch(payload);
  } finally {
    resultSection.setAttribute("aria-busy", "false");
    actionButtons.forEach((button) => { button.disabled = false; });
    returnFocus?.focus({ preventScroll: true });
  }
}

async function bootstrap() {
  const [status, profiles, capabilities] = await Promise.all([
    api("/api/v1/status"),
    api("/api/v1/profiles"),
    api("/api/v1/capabilities"),
  ]);
  for (const profile of profiles.profiles) {
    const option = document.createElement("option");
    option.value = profile.profile_id;
    option.textContent = profile.display_name;
    profileSelect.append(option);
  }
  document.querySelector("#runtime-account").textContent = `Prozesskonto: ${status.process_identity.account_name}`;
  connectionState.textContent = "Lokale Verbindung bereit";
  const cards = capabilities.capabilities.map((item) => {
    const card = document.createElement("article");
    card.className = "capability-card";
    card.dataset.status = item.surface_status;
    card.append(textElement("strong", item.title));
    card.append(textElement("small", item.surface_status === "interactive_read_only" ? "Hier direkt nutzbar" : "Über sichere CLI-Workflows"));
    return card;
  });
  document.querySelector("#capability-grid").replaceChildren(...cards);
}

document.querySelector("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch("search").catch(showError);
});
document.querySelector("#dossier-button").addEventListener("click", () => {
  runSearch("dossier").catch(showError);
});

bootstrap().catch((error) => {
  connectionState.textContent = "Lokale Verbindung blockiert";
  showError(error);
});
