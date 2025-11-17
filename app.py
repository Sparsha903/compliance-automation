import os
import io

from flask import Flask, render_template, request, redirect, url_for, flash
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from PyPDF2 import PdfReader

# ----- Flask setup -----
app = Flask(__name__)
app.secret_key = "some-secret-key"  # just for flash messages

# ----- Backblaze B2 setup -----
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET")

info = InMemoryAccountInfo()
b2_api = B2Api(info)

# authorize with Backblaze using environment vars
b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)


# ----- Simple rule-based compliance engine -----
GDPR_RULES = [
    "consent",
    "data retention",
    "right to access",
    "right to delete",
    "privacy policy",
]

HIPAA_RULES = [
    "protected health information",
    "PHI",
    "breach notification",
    "encryption",
    "access control",
]


def check_compliance(text: str):
    rules = GDPR_RULES + HIPAA_RULES
    passed = []
    missing = []

    lower_text = text.lower()

    for rule in rules:
        if rule.lower() in lower_text:
            passed.append(rule)
        else:
            missing.append(rule)

    score = round(len(passed) / len(rules) * 100, 2)
    return score, passed, missing


def extract_text_from_file(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text
    else:
        # treat as plain text file
        return data.decode("utf-8", errors="ignore")


# ----- Routes -----

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file part")
        return redirect(url_for("index"))

    file = request.files["file"]

    if file.filename == "":
        flash("No selected file")
        return redirect(url_for("index"))

    file_bytes = file.read()
    filename = file.filename

    # 1) Upload original file to Backblaze
    bucket.upload_bytes(file_bytes, filename)

    # 2) Extract text and run compliance check
    text = extract_text_from_file(filename, file_bytes)
    score, passed, missing = check_compliance(text)

    # 3) Create a simple text report and upload it
    report_content = (
        f"Compliance Report for {filename}\n"
        f"Score: {score}%\n\n"
        f"Passed rules:\n- " + "\n- ".join(passed) +
        "\n\nMissing rules:\n- " + ("\n- ".join(missing) if missing else "None")
    )
    report_name = filename + "_report.txt"
    bucket.upload_bytes(report_content.encode("utf-8"), report_name)

    # Render result page
    return render_template(
        "result.html",
        filename=filename,
        score=score,
        passed=passed,
        missing=missing,
        report_name=report_name,
    )


# For Render with gunicorn: entry point "app:app"
if __name__ == "__main__":
    app.run(debug=True)
