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

// Upload the chosen PDF, parse it server-side (in memory), and load the result.
// Uses XMLHttpRequest so the upload can report real progress; the server-side
// parse that follows is a single opaque step, shown as an indeterminate bar.
function uploadAndParsePdf(file) {
  const request = new XMLHttpRequest();
  request.open("POST", "parse");

  request.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      const percent = Math.round((event.loaded / event.total) * 100);
      setProgress(`Uploading ${file.name}… ${percent}%`, percent);
    }
  };
  request.upload.onload = () =>
    setProgress("Parsing charms… (this can take a moment)", null);

  request.onload = () => {
    if (request.status >= 200 && request.status < 300) {
      let charmData;
      try {
        charmData = JSON.parse(request.responseText);
      } catch (_) {
        setStatus("Server returned an unexpected response.");
        return;
      }
      cacheCharmData(charmData);
      loadCharmData(charmData);
    } else {
      let message = `${request.status} ${request.statusText}`;
      try {
        message = JSON.parse(request.responseText).error || message;
      } catch (_) { /* non-JSON error body */ }
      setStatus(`Could not parse PDF: ${message}`);
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
    (name) => !/ Style$/.test(name) && !/ Circle Spells$/.test(name));
  viewerState.martialArtsCategoryNames =
    charmData.categories.filter((name) => / Style$/.test(name));
  viewerState.sorceryCategoryNames =
    charmData.categories.filter((name) => / Circle Spells$/.test(name));
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
  elementById("dataSummary").textContent =
    `${viewerState.allCharms.length} charms · ` +
    `${viewerState.categoryNames.length} categories`;
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
