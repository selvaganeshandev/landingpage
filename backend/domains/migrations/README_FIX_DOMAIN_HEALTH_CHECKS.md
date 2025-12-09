# Fix for Missing domain_health_checks Table

## Problem
The error `django.db.utils.ProgrammingError: relation "domain_health_checks" does not exist` occurs because the `domain_health_checks` table was not created in the database, even though the model exists and the migration is defined.

## Solution

### Option 1: Run the Migration (Recommended)

1. Activate your virtual environment:
   ```bash
   cd backend
   source .venv/bin/activate  # or source venv/bin/activate
   ```

2. Run the migration:
   ```bash
   python3 manage.py migrate domains
   ```

   This will apply migration `0002_create_domain_health_checks.py` which safely creates the table if it doesn't exist.

### Option 2: Run All Migrations

If you want to ensure all migrations are applied:

```bash
cd backend
source .venv/bin/activate
python3 manage.py migrate
```

### Option 3: Manual SQL (If migrations fail)

If for some reason the migration doesn't work, you can run this SQL directly in your PostgreSQL database:

```sql
-- Check if table exists first
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'domain_health_checks'
);

-- If it doesn't exist, create it:
CREATE TABLE IF NOT EXISTS domain_health_checks (
    id BIGSERIAL PRIMARY KEY,
    health_score INTEGER NOT NULL,
    max_score INTEGER NOT NULL DEFAULT 100,
    percentage INTEGER NOT NULL,
    grade VARCHAR(10) NOT NULL CHECK (grade IN ('Excellent', 'Good', 'Fair', 'Poor')),
    grade_color VARCHAR(10) NOT NULL,
    checks JSONB NOT NULL,
    total_checks INTEGER NOT NULL,
    passed_checks INTEGER NOT NULL,
    warning_checks INTEGER NOT NULL,
    failed_checks INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    checked_by_id BIGINT,
    domain_id BIGINT NOT NULL,
    CONSTRAINT domain_health_checks_checked_by_id_fkey 
        FOREIGN KEY (checked_by_id) REFERENCES accounts(id) 
        ON DELETE SET NULL,
    CONSTRAINT domain_health_checks_domain_id_fkey 
        FOREIGN KEY (domain_id) REFERENCES domains(id) 
        ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS domain_heal_domain__53961f_idx 
    ON domain_health_checks (domain_id, created_at DESC);

CREATE INDEX IF NOT EXISTS domain_heal_domain__d0ae08_idx 
    ON domain_health_checks (domain_id, health_score DESC);

CREATE INDEX IF NOT EXISTS domain_heal_grade_15dd57_idx 
    ON domain_health_checks (grade, created_at DESC);
```

## Verification

After running the migration, verify the table exists:

```bash
python3 manage.py dbshell
```

Then in the PostgreSQL shell:
```sql
\dt domain_health_checks
\d domain_health_checks
```

Or check via Django:
```bash
python3 manage.py shell
```

```python
from domains.models import DomainHealthCheck
print(DomainHealthCheck.objects.count())  # Should work without error
```

