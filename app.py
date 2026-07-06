"""Web app: serve the charm viewer and parse uploaded PDFs in memory.

Deployment (e.g. Render): `gunicorn app:app`.

The uploaded PDF is read into memory, parsed with the existing parser, and
discarded when the request ends — nothing is written to disk or stored. The
browser holds the parsed charms only until the tab is closed.
"""
import json
import os
import queue
import sys
import threading

import fitz  # PyMuPDF
from flask import Flask, Response, jsonify, request, send_from_directory

# The parser modules import each other by bare name, so put parser/ on the path.
PARSER_DIR = os.path.join(os.path.dirname(__file__), "parser")
sys.path.insert(0, PARSER_DIR)
from parse import build_output, parse_charms_from_document  # noqa: E402

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
# Allow a full core-rulebook PDF (~50 MB) plus headroom; reject larger uploads.
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/parse", methods=["POST"])
def parse_uploaded_pdf():
    """Parse an uploaded PDF, streaming progress as newline-delimited JSON.

    Each line is one of {"progress": 0..1}, {"result": {...}}, or {"error": ...}.
    Parsing runs in a worker thread; progress flows back through a queue so the
    response can stream it as the parse advances. The PDF bytes live only in
    memory for the duration of the request.
    """
    uploaded = request.files.get("pdf")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "No PDF uploaded."}), 400
    pdf_bytes = uploaded.read()  # in memory only; never saved

    def generate():
        progress_queue = queue.Queue()

        def worker():
            try:
                document = fitz.open(stream=pdf_bytes, filetype="pdf")
                charms, categories = parse_charms_from_document(
                    document,
                    progress_callback=lambda f: progress_queue.put(("progress", f)))
                if not charms:
                    progress_queue.put(("error", "No charms found — is this the "
                                        "Exalted 3e core rulebook PDF?"))
                else:
                    progress_queue.put(("result", build_output(charms, categories)))
            except Exception as error:  # malformed or non-Exalted PDF
                progress_queue.put(("error", f"Could not parse this PDF: {error}"))

        threading.Thread(target=worker, daemon=True).start()
        while True:
            kind, payload = progress_queue.get()
            if kind == "progress":
                yield json.dumps({"progress": payload}) + "\n"
            elif kind == "result":
                yield json.dumps({"result": payload}) + "\n"
                return
            else:  # error
                yield json.dumps({"error": payload}) + "\n"
                return

    return Response(generate(), mimetype="application/x-ndjson",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), debug=True)
