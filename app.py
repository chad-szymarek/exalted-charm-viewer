"""Web app: serve the charm viewer and parse uploaded PDFs in memory.

Deployment (e.g. Render): `gunicorn app:app`.

The uploaded PDF is read into memory, parsed with the existing parser, and
discarded when the request ends — nothing is written to disk or stored. The
browser holds the parsed charms only until the tab is closed.
"""
import os
import sys

from flask import Flask, jsonify, request, send_from_directory

# The parser modules import each other by bare name, so put parser/ on the path.
PARSER_DIR = os.path.join(os.path.dirname(__file__), "parser")
sys.path.insert(0, PARSER_DIR)
from parse import build_output, parse_charms_from_bytes  # noqa: E402

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
# Allow a full core-rulebook PDF (~50 MB) plus headroom; reject larger uploads.
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/parse", methods=["POST"])
def parse_uploaded_pdf():
    uploaded = request.files.get("pdf")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "No PDF uploaded."}), 400
    pdf_bytes = uploaded.read()  # in memory only; never saved
    try:
        charms, category_display_names = parse_charms_from_bytes(pdf_bytes)
    except Exception as error:  # malformed or non-Exalted PDF
        return jsonify({"error": f"Could not parse this PDF: {error}"}), 422
    if not charms:
        return jsonify({"error": "No charms found — is this the Exalted 3e "
                                 "core rulebook PDF?"}), 422
    return jsonify(build_output(charms, category_display_names))


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), debug=True)
