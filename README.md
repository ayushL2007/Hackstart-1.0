# Hackstart-1.0

## Flask registration API

This branch contains only the JSON API. The website, registration form, dashboard, roadmap, and event assets stay on `main`. Python 3.10 or newer is required.

The API exposes `POST /api/participants` for registration and `GET /api/participants` for authorized review. POST uses `HACKSTART_REGISTRATION_TOKEN`; GET uses the separate `HACKSTART_ADMIN_TOKEN`. Both are bearer tokens of at least 32 bytes. Requests are limited to 16 KB and validated before being atomically written to `participants.json`.

### Local development

In PowerShell, install the dependency and configure separate tokens:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$registrationBytes = New-Object byte[] 32
$adminBytes = New-Object byte[] 32
$rng.GetBytes($registrationBytes)
$rng.GetBytes($adminBytes)
$rng.Dispose()
$env:HACKSTART_REGISTRATION_TOKEN = [Convert]::ToBase64String($registrationBytes)
$env:HACKSTART_ADMIN_TOKEN = [Convert]::ToBase64String($adminBytes)
Write-Output "Registration token: $env:HACKSTART_REGISTRATION_TOKEN"
Write-Output "Admin token: $env:HACKSTART_ADMIN_TOKEN"
.\.venv\Scripts\python.exe app.py
```

### Deploy on PythonAnywhere

PythonAnywhere's free Beginner account supports one web app and persistent home-directory storage. Keep a separate backup of `participants.json`; for heavier use, move records to a database.

1. Clone this branch and install Flask in a virtual environment:

   ```bash
   git clone --branch server https://github.com/ayushL2007/Hackstart-1.0.git ~/hackstart-api
   mkvirtualenv --python=/usr/bin/python3.13 hackstart-api
   workon hackstart-api
   pip install -r ~/hackstart-api/requirements.txt
   ```

2. In the Web tab, add a web app with **Manual configuration**, choose the same Python version, and set its virtualenv to `/home/<username>/.virtualenvs/hackstart-api`.
3. In the WSGI configuration file, set the project path, separate tokens, and persistent data path before importing the app:

   ```python
   import os
   import sys

   project_home = "/home/<username>/hackstart-api"
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   os.environ["HACKSTART_REGISTRATION_TOKEN"] = "<registration-token>"
   os.environ["HACKSTART_ADMIN_TOKEN"] = "<admin-token>"
   os.environ["PARTICIPANTS_FILE"] = "/home/<username>/.local/share/hackstart/participants.json"

   from app import app as application
   ```

   Generate each token with `openssl rand -hex 32`. Do not commit tokens.
4. Save the WSGI file and click **Reload**. The API will be at `https://<username>.pythonanywhere.com/api/participants`.

The frontend is on `main`. When hosting it separately from the API, configure its API URL and allow only its origin; same-origin relative API paths will not work across separate domains. See PythonAnywhere's [Flask guide](https://help.pythonanywhere.com/pages/Flask/). Render's [free services use ephemeral filesystems](https://render.com/docs/free), so they are unsuitable for `participants.json` without changing to a persistent database.