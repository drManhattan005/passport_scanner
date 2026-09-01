# MRZ Passport Batch Extractor

> Use Python 3.12.

## Setup

### 1. Clone the repository

git clone <your-repo-url>
cd MRZ-passport-scan

### 2. Create and activate a virtual environment

macOS / Linux:

python3 -m venv .venv
source .venv/bin/activate

Windows PowerShell:

python -m venv .venv
.venv\Scripts\Activate.ps1

### 3. Install dependencies

pip install --upgrade pip
pip install -r requirements.txt

The OmniMRZ source is included under `vendor/OmniMRZ-source` because the
published package currently installs metadata without the importable package.
The backend loads this vendored source automatically.

### 4. Run the app

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

### 5. Open in browser

http://127.0.0.1:8000
