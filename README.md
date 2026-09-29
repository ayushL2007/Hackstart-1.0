# Hackstart-1.0

## Flask registration server

This branch serves the website, registration form, and dashboard through Flask. Python 3.10 or newer is required.

For local development in PowerShell:

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

Visit `http://localhost:3000/registration.html` or `http://localhost:3000/dashboard.html`. Share only the registration token; keep the admin token private. The API is `POST /api/participants` for registration and `GET /api/participants` for the dashboard. Both use bearer-token authentication, but require separate tokens. Request bodies are limited to 16 KB and validated. Records are atomically written to `participants.json`, which is excluded from Git.

## Free deployment: PythonAnywhere

PythonAnywhere is the simplest free option for this file-backed app: its free Beginner account includes one web app and persistent home-directory storage. The JSON file survives app restarts there. Keep a separate backup of `participants.json`; for heavier use, move records to a database.

1. Commit and push the `server` branch from this workspace:

	```powershell
	git add .gitignore README.md index.html app.py dashboard.html registration.html requirements.txt
	git commit -m "Add Flask team registration server"
	git push -u origin server
	```

	The branch currently has no commit containing these files, so run these commands before cloning it on PythonAnywhere.
2. Create a free Beginner account at [PythonAnywhere](https://www.pythonanywhere.com/).
3. Open a Bash console and clone the branch, replacing the URL if your repository differs:

	```bash
	git clone --branch server https://github.com/ayushL2007/Hackstart-1.0.git ~/hackstart
	mkvirtualenv --python=/usr/bin/python3.13 hackstart-env
	workon hackstart-env
	pip install -r ~/hackstart/requirements.txt
	```

4. In the Web tab, add a web app with **Manual configuration** and the same Python version. Set its virtualenv to `/home/<username>/.virtualenvs/hackstart-env`.
5. Open the WSGI configuration file linked on the Web tab. Add this before the Flask import, replacing `<username>` and both token placeholders with separate random secrets:

	```python
	import os
	import sys

	project_home = "/home/<username>/hackstart"
	if project_home not in sys.path:
		 sys.path.insert(0, project_home)

	os.environ["HACKSTART_REGISTRATION_TOKEN"] = "<registration-token>"
	os.environ["HACKSTART_ADMIN_TOKEN"] = "<admin-token>"
	os.environ["PARTICIPANTS_FILE"] = "/home/<username>/.local/share/hackstart/participants.json"

	from app import app as application
	```

	Generate each token with `openssl rand -hex 32` in the Bash console. Do not put these secrets in Git.
6. Save the WSGI file, then click **Reload** on the Web tab. Your site will be at `https://<username>.pythonanywhere.com/`; use `/registration.html` and `/dashboard.html` on that domain.

PythonAnywhere's [Flask guide](https://help.pythonanywhere.com/pages/Flask/) covers the WSGI setup. Render is another free host, but its [free web services have ephemeral filesystems](https://render.com/docs/free), so they will lose this app's JSON registrations on restart or redeploy. Render persistent disks are paid.