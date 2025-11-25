# Python Environment Setup

This document describes the Python environment configuration for the LLM Monitor project.

## Environment Overview

The project uses a **virtual environment** located at `backend/.venv/`, but due to the way it was created, it uses the **system Python 3.9** from Xcode as the interpreter while installing packages to the **user site-packages**.

## Key Paths

| Component | Path |
|-----------|------|
| Virtual Environment | `backend/.venv/` |
| Python Interpreter | `/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9` |
| User Site-Packages | `/Users/arun/Library/Python/3.9/lib/python/site-packages` |
| Venv Python Binary | `backend/.venv/bin/python3` |

## Installing Python Packages

### Correct Method

When installing new Python packages for the backend or engine, use the venv Python with `-m pip`:

```bash
# From the project root directory
"/Users/arun/My Products/AI Project/LLM Monitor/Dev/llm-monitor/backend/.venv/bin/python3" -m pip install <package-name>
```

Or using the shorthand from within the backend directory:

```bash
cd backend
.venv/bin/python3 -m pip install <package-name>
```

### Why This Method?

The venv's `pip` binary installs to the venv's site-packages (Python 3.14), but the venv's Python interpreter actually uses Python 3.9 system paths. Using `python3 -m pip` ensures packages are installed where the interpreter can find them (user site-packages for Python 3.9).

### DO NOT Use

- `pip install <package>` - Uses system pip, may fail due to externally-managed-environment
- `pip3 install <package>` - Same issue
- `.venv/bin/pip install <package>` - Installs to wrong location (venv site-packages for Python 3.14)

## Running the Backend

The backend is started using the venv Python:

```bash
cd backend
.venv/bin/python3 manage.py runserver 8000
```

Or using the full path:

```bash
"/Users/arun/My Products/AI Project/LLM Monitor/Dev/llm-monitor/backend/.venv/bin/python3" manage.py runserver 8000
```

## Startup Script

The `start-all.sh` script handles starting all services correctly. It uses:

```bash
VENV_PYTHON="$PROJECT_DIR/backend/.venv/bin/python3"
```

## Requirements File

All dependencies are listed in `backend/requirements.txt`. After adding new packages:

1. Install the package using the correct method above
2. Update `requirements.txt` to include the new package

## Current Installed Packages (Key Dependencies)

- Django 5.2
- djangorestframework 3.15.2
- psycopg (PostgreSQL adapter)
- python-decouple (environment variables)
- django-cors-headers
- djangorestframework-simplejwt (JWT auth)
- openai (OpenAI API)
- google-auth, google-auth-oauthlib, google-api-python-client (Google APIs)

## Troubleshooting

### "ModuleNotFoundError" after installing a package

The package was likely installed to the wrong location. Reinstall using:

```bash
.venv/bin/python3 -m pip install <package-name>
```

### "externally-managed-environment" error

Don't use system pip. Always use the venv Python with `-m pip`.

### Checking where packages are installed

```bash
.venv/bin/python3 -m pip show <package-name>
```

### Listing installed packages

```bash
.venv/bin/python3 -m pip list
```
