// Entry point: load charm data, populate state, render, and wire controls.
import { viewerState } from "./state.js";
import { elementById } from "./dom-utils.js";
import { renderCategorySidebar } from "./category-sidebar.js";
import { renderCharmList } from "./charm-list.js";
import { showCharmDetail } from "./charm-detail.js";
import { updateSelectionSummary } from "./selection.js";
import { exportAllCharms, exportSelectedCharms } from "./export-controls.js";

// Best-effort load of a pre-parsed file (local dev convenience). The hosted
// app has no such file, so a failure here just means "wait for an upload".
async function loadPreparsedData() {
  const response = await fetch("../data/charms.json");
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

// Upload the chosen PDF and parse it server-side (in memory). XMLHttpRequest
// reports real upload progress; the server then streams newline-delimited JSON
// ({"progress"|"result"|"error"}) as it parses, giving a real "Parsing… X%".
function uploadAndParsePdf(file) {
  const request = new XMLHttpRequest();
  request.open("POST", "parse");

  let processedLength = 0;
  let finalResult = null;
  let finalError = null;

  // Parse whatever complete newline-terminated JSON lines have arrived so far.
  const consumeStreamedLines = () => {
    const responseText = request.responseText;
    const unprocessed = responseText.slice(processedLength);
    const lines = unprocessed.split("\n");
    // The last element is a partial line (no newline yet) — leave it buffered.
    processedLength += unprocessed.length - lines[lines.length - 1].length;
    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      let message;
      try { message = JSON.parse(line); } catch (_) { continue; }
      if (message.progress != null) {
        const percent = Math.round(message.progress * 100);
        setProgress(`Parsing charms, sorceries, and merits… ${percent}%`, percent);
      } else if (message.result) {
        finalResult = message.result;
      } else if (message.error) {
        finalError = message.error;
      }
    }
  };

  request.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      const percent = Math.round((event.loaded / event.total) * 100);
      setProgress(`Uploading ${file.name}… ${percent}%`, percent);
    }
  };
  request.upload.onload = () => setProgress("Parsing charms, sorceries, and merits… 0%", 0);

  request.onprogress = consumeStreamedLines;
  request.onload = () => {
    consumeStreamedLines();
    if (!finalResult && !finalError) {
      // Non-streamed error body (e.g. a 400 before streaming began).
      try { finalError = JSON.parse(request.responseText).error; } catch (_) { /* */ }
    }
    if (finalError) {
      setStatus(`Could not parse PDF: ${finalError}`);
    } else if (finalResult) {
      cacheCharmData(finalResult);
      loadCharmData(finalResult);
    } else {
      setStatus(`Server returned an unexpected response (status ${request.status}).`);
    }
  };
  request.onerror = () => setStatus("Upload failed (network error).");

  const formData = new FormData();
  formData.append("pdf", file);
  setProgress(`Uploading ${file.name}… 0%`, 0);
  request.send(formData);
}

function setStatus(message) {
  elementById("charmDetail").innerHTML =
    `<div class="placeholder">${message}</div>`;
}

// Render a progress bar in the detail pane. percent null = indeterminate.
function setProgress(label, percent) {
  const isIndeterminate = percent === null;
  const fillStyle = isIndeterminate
    ? "" : `style="width:${percent}%"`;
  elementById("charmDetail").innerHTML =
    `<div class="placeholder"><div class="progress-wrap">
       <div class="progress-label">${label}</div>
       <div class="progress-track">
         <div class="progress-fill${isIndeterminate ? " indeterminate" : ""}" ${fillStyle}></div>
       </div>
     </div></div>`;
}

// --- Session cache: keep parsed charms across a refresh for a few minutes. ---
// sessionStorage survives refreshes but clears when the tab closes, so nothing
// lingers after the user leaves; the timestamp expires it within the session.
const CACHE_KEY = "exalted-charms";
const CACHE_TTL_MS = 5 * 60 * 1000;

function cacheCharmData(charmData) {
  try {
    sessionStorage.setItem(CACHE_KEY,
      JSON.stringify({ savedAt: Date.now(), data: charmData }));
  } catch (_) { /* quota exceeded or storage disabled — skip caching */ }
}

function loadCachedCharmData() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { savedAt, data } = JSON.parse(raw);
    if (Date.now() - savedAt > CACHE_TTL_MS) {
      sessionStorage.removeItem(CACHE_KEY);
      return null;
    }
    return data;
  } catch (_) {
    return null;
  }
}

function populateStateFrom(charmData) {
  viewerState.allCharms = charmData.charms;
  viewerState.categoryNames = charmData.categories;
  viewerState.charmsById.clear();
  charmData.charms.forEach(
    (charm) => viewerState.charmsById.set(charm.id, charm));
  viewerState.abilityCategoryNames = charmData.categories.filter(
    (name) => !/ Style$/.test(name) && !/ Circle Spells$/.test(name)
      && !/ Merits$/.test(name));
  viewerState.martialArtsCategoryNames =
    charmData.categories.filter((name) => / Style$/.test(name));
  viewerState.sorceryCategoryNames =
    charmData.categories.filter((name) => / Circle Spells$/.test(name));
  viewerState.meritCategoryNames =
    charmData.categories.filter((name) => / Merits$/.test(name));
  // Reset per-dataset view state (relevant when a new PDF is uploaded).
  viewerState.selectedCharmIds.clear();
  viewerState.activeCategoryName = null;
  viewerState.openCharmId = null;
  viewerState.searchQuery = "";
}

function populateTypeFilter() {
  const typeFilterSelect = elementById("typeFilterSelect");
  typeFilterSelect.innerHTML = `<option value="">All types</option>`;
  const charmTypes = [...new Set(
    viewerState.allCharms.map((charm) => charm.type).filter(Boolean))].sort();
  charmTypes.forEach((charmType) => {
    const option = document.createElement("option");
    option.value = charmType;
    option.textContent = charmType;
    typeFilterSelect.appendChild(option);
  });
}

// Load a parsed dataset (from upload or the pre-parsed file) and render it.
function loadCharmData(charmData) {
  populateStateFrom(charmData);
  elementById("searchInput").value = "";
  const sorceryCount = viewerState.allCharms.filter(
    (entry) => / Circle Spells$/.test(entry.category)).length;
  const meritCount = viewerState.allCharms.filter(
    (entry) => / Merits$/.test(entry.category)).length;
  const charmCount = viewerState.allCharms.length - sorceryCount - meritCount;
  elementById("dataSummary").textContent =
    `${charmCount} charms · ${sorceryCount} sorceries · ${meritCount} merits`;
  populateTypeFilter();
  renderCategorySidebar();
  renderCharmList();
  updateSelectionSummary();
  setStatus("Select a charm to view its details.");
  openCharmFromUrlHash();
}

function wireControls() {
  elementById("searchInput").oninput = (event) => {
    viewerState.searchQuery = event.target.value;
    renderCharmList();
  };
  elementById("searchDescriptionsCheckbox").onchange = (event) => {
    viewerState.searchInDescriptions = event.target.checked;
    renderCharmList();
  };
  elementById("typeFilterSelect").onchange = (event) => {
    viewerState.activeTypeFilter = event.target.value;
    renderCharmList();
  };
  elementById("clearSelectionButton").onclick = () => {
    viewerState.selectedCharmIds.clear();
    updateSelectionSummary();
    renderCharmList();
    renderCategorySidebar();
  };
  elementById("exportAllButton").onclick = exportAllCharms;
  elementById("exportSelectedButton").onclick = exportSelectedCharms;
  elementById("pdfInput").onchange = (event) => {
    const file = event.target.files[0];
    if (file) uploadAndParsePdf(file);
    event.target.value = "";  // allow re-uploading the same file
  };
  updateSelectionSummary();
}

function openCharmFromUrlHash() {
  const charmIdInHash = decodeURIComponent(location.hash.slice(1));
  if (charmIdInHash && viewerState.charmsById.has(charmIdInHash)) {
    showCharmDetail(charmIdInHash);
  }
}

async function startViewer() {
  wireControls();
  // 1. Recently-parsed data cached this session (survives a refresh).
  const cached = loadCachedCharmData();
  if (cached) {
    loadCharmData(cached);
    return;
  }
  // 2. A pre-parsed file (local dev convenience).
  try {
    loadCharmData(await loadPreparsedData());
    return;
  } catch (_) { /* none — fall through to the upload prompt */ }
  // 3. Hosted, first visit: prompt for a PDF.
  setStatus("Upload your Exalted 3e core rulebook PDF to begin "
    + "(top-left button). It is parsed in memory and never stored.");
}

startViewer();
