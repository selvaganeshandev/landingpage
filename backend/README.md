# LLM Monitor Backend

Django 5.2 backend for the LLM Monitor application with PostgreSQL database and REST API.

## Setup

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   The `.env` file is already configured with the following database settings:
   - Host: localhost
   - Port: 5432
   - Database: llm_monitor
   - User: arun
   - Password: admin

4. **Database Setup:**
   Make sure PostgreSQL is running and create the database:
   ```sql
   CREATE DATABASE llm_monitor;
   ```

5. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server:**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

- **Test Endpoint:** `GET /api/test/`
- **Health Check:** `GET /api/health/`
- **Health Check (POST):** `POST /api/health/`
- **Admin Panel:** `http://localhost:8000/admin/`

## Project Structure

```
backend/
├── llm_monitor/          # Main Django project
│   ├── settings.py      # Django settings with PostgreSQL config
│   ├── urls.py          # Main URL configuration
│   └── wsgi.py          # WSGI configuration
├── api/                 # API app
│   ├── views.py         # API views
│   └── urls.py          # API URL patterns
├── requirements.txt     # Python dependencies
├── .env                # Environment variables
└── manage.py           # Django management script
```

## Dependencies

- Django 5.2
- Django REST Framework 3.15.2
- PostgreSQL adapter (psycopg2-binary)
- python-decouple (for environment variables)
- django-cors-headers (for CORS support)

## CORS Configuration

The backend is configured to allow requests from:
- http://localhost:3000
- http://127.0.0.1:3000
- http://localhost:5173
- http://127.0.0.1:5173
