# Starting Local Development Services

This guide provides the exact commands to start all three services for the LLM Monitor project.

## Prerequisites

- Python 3.x installed
- Node.js and npm installed
- PostgreSQL running at 64.227.190.42:5432
- Backend virtual environment already set up at `backend/.venv`
- Engine linked to backend's virtual environment

## Quick Start (All Services)

Run these commands in separate terminal windows or as background processes:

### 1. Backend (Django REST API) - Port 8000

```bash
cd backend && source .venv/bin/activate && python3 manage.py runserver
```

**URL:** http://localhost:8000/
**Admin:** http://localhost:8000/admin/

### 2. Engine (Processing Engine) - Port 8001

```bash
cd engine && source .venv/bin/activate && python3 manage.py runserver 8001
```

**URL:** http://localhost:8001/

### 3. Frontend (React + Vite) - Port 8080

```bash
cd frontend && npm run dev
```

**URL:** http://localhost:8080/

## Running as Background Processes

To run all services in the background (useful for development):

```bash
# Start backend
cd backend && source .venv/bin/activate && python3 manage.py runserver &

# Start engine
cd engine && source .venv/bin/activate && python3 manage.py runserver 8001 &

# Start frontend
cd frontend && npm run dev &
```

## Verify Services Are Running

```bash
# Check which processes are using the ports
lsof -i :8000 -i :8001 -i :8080

# Or test each endpoint
curl http://localhost:8080        # Frontend
curl http://localhost:8000/admin/ # Backend
curl http://localhost:8001/       # Engine
```

## Important Notes

### Virtual Environment Setup

- **Backend:** Uses `backend/.venv/` (already created)
- **Engine:** Uses a symlink to `backend/.venv/` (shared dependencies)
  - Created with: `cd engine && ln -s ../backend/.venv .venv`
- **Frontend:** Uses npm (no virtual environment needed)

### Why Engine Shares Backend's venv

Both backend and engine:
- Share the same PostgreSQL database
- Use the same Django version and dependencies
- This avoids duplicate dependency installations and version conflicts

### Common Issues

**Issue:** `no such file or directory: venv/bin/activate`
- **Solution:** Use `.venv` not `venv` (note the dot)
- **Correct:** `source .venv/bin/activate`
- **Wrong:** `source venv/bin/activate`

**Issue:** `command not found: python`
- **Solution:** Use `python3` instead of `python`

**Issue:** `ModuleNotFoundError: No module named 'django'`
- **Solution:** Make sure you activated the virtual environment first
- Run: `source .venv/bin/activate` before running Django commands

**Issue:** Engine won't install dependencies (psycopg2-binary error)
- **Solution:** Use backend's .venv (already resolved by symlinking)

## Stopping All Services

```bash
# Find and kill all Python Django servers
pkill -f "python3 manage.py runserver"

# Kill the frontend dev server
pkill -f "npm run dev"

# Or kill specific ports
lsof -ti:8000 | xargs kill
lsof -ti:8001 | xargs kill
lsof -ti:8080 | xargs kill
```

## Service Dependencies

```
Frontend (8080) → Backend (8000) → PostgreSQL (64.227.190.42:5432)
                ↘ Engine (8001)  ↗
```

- Frontend makes API calls to Backend
- Both Backend and Engine connect to the same PostgreSQL database
- Engine processes domains scheduled through Backend

## Logs and Debugging

### Backend Logs
- Console output shows all requests
- Django debug toolbar available in DEBUG mode

### Engine Logs
- `engine/engine.log` - General engine logs
- `engine/processor.log` - Processor-specific logs
- `engine/processor_engine.log` - Detailed processing logs

### Frontend Logs
- Browser console for client-side errors
- Terminal shows Vite build warnings/errors

## Development Workflow

1. Start all three services using the quick start commands
2. Make code changes
3. Services auto-reload on file changes:
   - Backend: Django's StatReloader watches Python files
   - Engine: Django's StatReloader watches Python files
   - Frontend: Vite's HMR watches React/TypeScript files
4. No need to restart unless you:
   - Change Django settings
   - Add new dependencies
   - Modify database models (requires migrations)

## Additional Engine Processes

The engine can also be started with the processor daemon:

```bash
cd engine
source .venv/bin/activate
python manage.py start_processor --daemon
```

Or use the standalone script:

```bash
cd engine
source .venv/bin/activate
python start_engine.py
```

## Environment Variables

Make sure these files exist:
- `backend/.env` - Backend environment variables
- `engine/.env` - Engine environment variables (includes API keys)

Required in `engine/.env`:
```
DATAFORSEO_USERNAME=<your-username>
DATAFORSEO_PASSWORD=<your-password>
OPENAI_API_KEY=<your-api-key>
```
