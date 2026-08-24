# Corrective migration for 0004.
#
# 0004 declared the four AI-detection fields with SeparateDatabaseAndState and
# database_operations=[] — "the columns already exist in the database (added
# outside migrations)". That was only true on the one database that had been
# hand-ALTERed: every FRESH database never gets the columns, and because
# Django's INSERT includes every model column, the whole content lane dies —
# GET /content/ 500s AND GeneratedContent.objects.create() fails, so plan,
# generate, rewrite, humanise and detect-ai are all unusable.
#
# This is the exact inverse of 0004: database_operations only, no state change
# (the state already carries the fields). ADD COLUMN IF NOT EXISTS makes it a
# no-op on databases where the hand-ALTER already happened, so it is safe to
# run everywhere — fresh installs gain the columns, production keeps its data.

from django.db import migrations

_SQL_ADD = """
ALTER TABLE generated_contents ADD COLUMN IF NOT EXISTS ai_detection_score numeric(5, 2) NULL;
ALTER TABLE generated_contents ADD COLUMN IF NOT EXISTS human_detection_score numeric(5, 2) NULL;
ALTER TABLE generated_contents ADD COLUMN IF NOT EXISTS ai_detection_label varchar(50) NULL;
ALTER TABLE generated_contents ADD COLUMN IF NOT EXISTS ai_detection_checked_at timestamp with time zone NULL;
"""

_SQL_DROP = """
ALTER TABLE generated_contents DROP COLUMN IF EXISTS ai_detection_score;
ALTER TABLE generated_contents DROP COLUMN IF EXISTS human_detection_score;
ALTER TABLE generated_contents DROP COLUMN IF EXISTS ai_detection_label;
ALTER TABLE generated_contents DROP COLUMN IF EXISTS ai_detection_checked_at;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0008_contentgenerationusage"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(_SQL_ADD, reverse_sql=_SQL_DROP)],
            state_operations=[],
        ),
    ]
