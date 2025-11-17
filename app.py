import os
from io import BytesIO

from flask import Flask, render_template, request
from PyPDF2 import PdfReader
from b2sdk.v2 import InMemoryAccountInfo, B2Api

app = Flask(__name__)

# ---------- Backblaze B2 SETUP ----------

B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET = os.getenv("B2_BUCKET")  # "compliance-checker"

b2_api = None
b2_bucket = None


def init_b2():
    """
    Initialize Backblaze B2 safely.
    If keys are missing OR wrong, we just skip cloud upload
    instead of crashing the whole app.
    """
    global b2_api, b2_bucket

    if not (B2_KEY_ID and B2_APP_KEY and B2_BUCKET):
        print("B2 not configured – skipping upload.")
        return None, None

    if b2_api is not None and b2_bucket is not None:
        return b2_api, b2_bucket

    try:
        info = InMemoryAccountInfo()
        b2_api_local = B2Api(info)
        b2_api_local.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
        bucket_local = b2_api_local.get_bucket_by_name(B2_BUCKET)
    except Exception as e:
        # Avoid 500 error if auth fails
        print("Error initialising Backblaze B2:", e)
        return None, None

    b2_api = b2_api_local
    b2_bucket = bucket_local
    return b2_api, b2_bucket


def upload_to_b2(filename: str, data: bytes):
    """
    Uploads file bytes to Backblaze B2 and returns a URL.
    If B2 is not available, returns None.
    """
    _, bucket = init_b2()
    if bucket is None:
        return None

    bucket.upload_bytes(data, filename)
    # Simple demo URL; good enough for assignment
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
    # First load – no result yet
    return render_template(
        "index.html",
        filename=None,
        score=None,
        found_rules=[],
        missing_rules=[],
        b2_url=None,
        error=None,
    )


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return render_template(
            "index.html",
            filename=None,
            score=None,
            found_rules=[],
            missing_rules=[],
            b2_url=None,
            error="No file uploaded.",
        )

    f = request.files["file"]
    if f.filename == "":
        return render_template(
            "index.html",
            filename=None,
            score=None,
            found_rules=[],
            missing_rules=[],
            b2_url=None,
            error="No file selected.",
        )

    data = f.read()

    # Upload original file to Backblaze (safe – may return None)
    b2_url = upload_to_b2(f.filename, data)

    # Extract text (PDF or TXT)
    content_type = f.content_type or ""
    if f.filename.lower().endswith(".pdf") or "pdf" in content_type:
        text = extract_text_from_pdf(data)
    else:
        text = data.decode(errors="ignore")

    score, found, missing = check_compliance(text)

    return render_template(
        "index.html",
        filename=f.filename,
        score=score,
        found_rules=found,
        missing_rules=missing,
        b2_url=b2_url,
        error=None,
    )


# For Render: 'gunicorn app:app'
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
