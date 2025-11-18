Compliance Automation System (GDPR & HIPAA)

A cloud-based mini-project using Flask, Render, and Backblaze B2 to analyze PDF/TXT documents for basic GDPR and HIPAA compliance.

🚀 Features

Upload PDF or TXT files

Extract text using PyPDF2

Keyword-based compliance checking

Calculates compliance score

Stores files in Backblaze B2

Cloud deployment via Render

Simple, clean UI

🛠 Tech Stack

Flask (Python)

Backblaze B2 Cloud Storage

Render Cloud Hosting

Bootstrap (Frontend)

PyPDF2, b2sdk

GitHub (Version Control)

📁 Project Structure
app.py
requirements.txt
templates/
   index.html

⚙️ Run Locally
git clone https://github.com/Sparsha903/compliance-automation
cd compliance-automation
pip install -r requirements.txt
python app.py


Set environment variables:

B2_KEY_ID=
B2_APP_KEY=
B2_BUCKET=compliance-checker

☁️ Deploy on Render

Build:

pip install -r requirements.txt


Start:

gunicorn app:app


Add environment variables:

B2_KEY_ID

B2_APP_KEY

B2_BUCKET

📊 Compliance Rules Checked

GDPR: consent, data retention, right to access, right to delete, privacy policy
HIPAA: PHI, breach notification, encryption, access control
