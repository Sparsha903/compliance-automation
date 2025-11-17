import os
from io import BytesIO

from flask import Flask, render_template, request
from PyPDF2 import PdfReader

from b2sdk.v2 import InMemoryAccountInfo, B2Api

app = Flask(__name__)

# ---------- Backblaze B2 SETUP ----------

B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET = os.getenv("B2_BUCKET")  # should be "compliance-checker"

b2_api = None
b2_bucket = None


def init_b2():
    """
    Lazily initialize Backblaze so the app doesn't crash
    if keys are missing while you're still setting things up.
    """
    global b2_api, b2_bucket
    if not (B2_KEY_ID and B2_APP_KEY and B2_BUCKET):
        return None, None  # running without cloud until keys are set

    if b2_api is None:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
        b2_bucket = b2_api.get_bucket_by_name(B2_BUCKET)

    return b2_api, b2_bucket


def upload_to_b2(filename: str, data: bytes):
    """
    Uploads file bytes to Backblaze B2 and returns a public-ish URL.
    (Bucket can be private; URL is just for your report / testing.)
    """
    _, bucket = init_b2()
    if bucket is None:
        # No keys configured – just skip upload for now
        return None

    bucket.upload_bytes(data, filename)
    # Standard B2 download URL form (for simple demo use)
    return f"https://f000.backblazeb2.com/file/{B2_BUCKET}/{filename}"


# ---------- SIMPLE COMPLIANCE CHECKER ----------

GDPR_RULES = [
    "consent",
    "data retention",
    "right to access",
    "right to delete",
    "privacy policy",
]

HIPAA_RULES = [
    "PHI",
    "protected health information",
    "breach notification",
    "encryption",
    "access control",
]


def check_compliance(text: str):
    rules = GDPR_RULES + HIPAA_RULES
    found = []
    missing = []

    lower_text = text.lower()
    for rule in rules:
        if rule.lower() in lower_text:
            found.append(rule)
        else:
            missing.append(rule)

    score = round(len(found) / len(rules) * 100, 2)
    return score, found, missing


def extract_text_from_pdf(file_bytes: bytes) -> str:
    pdf = PdfReader(BytesIO(file_bytes))
    pages_text = []
    for page in pdf.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages_text)


# ---------- ROUTES ----------

@app.route("/", methods=["GET"])
def index():
    # First load – no result
    return render_template("index.html", result=None)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return render_template("index.html", error="No file uploaded", result=None)

    f = request.files["file"]
    if f.filename == "":
        return render_template("index.html", error="No file selected", result=None)

    data = f.read()

    # Upload original file to Backblaze
    b2_url = upload_to_b2(f.filename, data)

    # Extract text (PDF or TXT)
    content_type = f.content_type or ""
    if f.filename.lower().endswith(".pdf") or "pdf" in content_type:
        text = extract_text_from_pdf(data)
    else:
        # assume text file
        text = data.decode(errors="ignore")

    score, found, missing = check_compliance(text)

    result = {
        "filename": f.filename,
        "score": score,
        "found": found,
        "missing": missing,
        "b2_url": b2_url,
    }

    return render_template("index.html", result=result, error=None)


# For Render: 'gunicorn app:app' looks for this
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

