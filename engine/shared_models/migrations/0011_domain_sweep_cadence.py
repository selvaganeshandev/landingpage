from django.db import migrations, models


# State-only migration. `sweep_cadence` and `last_swept_at` are created on
# `domains` by the BACKEND (domains.0012); both trees point at the same
# database, so no DDL is issued here and the engine's ORM simply learns the
# fields exist. Mirrors 0010.
#
# The engine needs them because the weekly sweep is what acts on the cadence:
# it reads `sweep_cadence` to decide which domains a run covers, and writes
# `last_swept_at` so a cadence longer than the weekly cron has something to
# measure "is this domain due yet?" against.
# See core/processing_tasks.schedule_weekly_prompt_batches.


class Migration(migrations.Migration):

    dependencies = [
        ('shared_models', '0010_organisation_using_ai_monitoring'),
    ]

    _add_fields = [
        migrations.AddField(
            model_name='domain',
            name='sweep_cadence',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('weekly', 'Weekly'),
                    ('biweekly', 'Every 15 days'),
                    ('monthly', 'Every 30 days'),
                    ('off', 'Off - no sweep'),
                ],
                default='weekly',
                help_text='How often the full prompt sweep re-runs this domain',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='last_swept_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the full prompt sweep last covered this domain',
            ),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_add_fields),
    ]
