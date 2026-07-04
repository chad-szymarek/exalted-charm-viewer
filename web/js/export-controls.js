// Client-side JSON export — builds the file in the browser, no server needed.
import { viewerState } from "./state.js";

function downloadJsonFile(fileName, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)],
                        { type: "application/json" });
  const objectUrl = URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");
  downloadLink.href = objectUrl;
  downloadLink.download = fileName;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  URL.revokeObjectURL(objectUrl);
}

export function exportAllCharms() {
  downloadJsonFile("exalted-charms-all.json", {
    count: viewerState.allCharms.length,
    charms: viewerState.allCharms,
  });
}

export function exportSelectedCharms() {
  const selectedCharms = viewerState.allCharms.filter(
    (charm) => viewerState.selectedCharmIds.has(charm.id));
  downloadJsonFile("exalted-charms-selected.json", {
    count: selectedCharms.length,
    charms: selectedCharms,
  });
}
