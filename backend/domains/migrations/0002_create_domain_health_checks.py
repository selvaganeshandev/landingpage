# Generated manually to fix missing domain_health_checks table
# This migration creates the domain_health_checks table using raw SQL if it doesn't exist
# This is a workaround for when 0001_initial migration was partially applied

from django.db import migrations


def create_table_if_not_exists(apps, schema_editor):
    """
    Create domain_health_checks table if it doesn't exist.
    This uses raw SQL to avoid conflicts with the model definition in 0001_initial.
    """
    db_alias = schema_editor.connection.alias
    with schema_editor.connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'domain_health_checks'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            # Create the table
            cursor.execute("""
                CREATE TABLE domain_health_checks (
                    id BIGSERIAL PRIMARY KEY,
                    health_score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL DEFAULT 100,
                    percentage INTEGER NOT NULL,
                    grade VARCHAR(10) NOT NULL,
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
                        ON DELETE CASCADE,
                    CONSTRAINT domain_health_checks_grade_check 
                        CHECK (grade IN ('Excellent', 'Good', 'Fair', 'Poor'))
                );
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX domain_heal_domain__53961f_idx 
                ON domain_health_checks (domain_id, created_at DESC);
            """)
            
            cursor.execute("""
                CREATE INDEX domain_heal_domain__d0ae08_idx 
                ON domain_health_checks (domain_id, health_score DESC);
            """)
            
            cursor.execute("""
                CREATE INDEX domain_heal_grade_15dd57_idx 
                ON domain_health_checks (grade, created_at DESC);
            """)


def reverse_create_table(apps, schema_editor):
    """Drop the table if it exists (for migration rollback)"""
    db_alias = schema_editor.connection.alias
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS domain_health_checks CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ('domains', '0001_initial'),
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_table_if_not_exists,
            reverse_create_table,
        ),
    ]

