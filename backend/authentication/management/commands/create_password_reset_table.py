from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Create password_reset_tokens table manually'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                        status VARCHAR(10) NOT NULL DEFAULT 'pending',
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW() + INTERVAL '1 hour',
                        used_at TIMESTAMP WITH TIME ZONE NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        modified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    );
                """)
                self.stdout.write(
                    self.style.SUCCESS('Successfully created password_reset_tokens table')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating table: {str(e)}')
                )
