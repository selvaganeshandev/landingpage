from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the `sweep_guard_state` table that the
    BACKEND migration (prompts.0003_sweepguardstate) physically creates on the
    shared DB.

    The engine and backend point at the same database, so the table is created
    by the backend's real migration. Here we use SeparateDatabaseAndState with
    ONLY state_operations — Django records the model in the engine's state but
    issues NO DDL, avoiding "table already exists". This mirrors
    0004_geo_region_g1.

    The table holds the weekly-sweep cooldown and kill switch. It lives in the
    database rather than a JSON file so the guard is machine-independent: a
    sweep triggered from any host is visible to every other caller.
    """

    dependencies = [
        ('shared_models', '0006_remove_organisation_content_generation_token_limit'),
    ]

    _state_operations = [
        migrations.CreateModel(
            name='SweepGuardState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sweep', models.CharField(help_text="Sweep identifier: 'prompts' or 'competitors'", max_length=32, unique=True)),
                ('enabled', models.BooleanField(default=True, help_text='Kill switch. When False this sweep is refused even with force=True.')),
                ('disabled_reason', models.TextField(blank=True, default='', help_text='Why the sweep was disabled, shown in the refusal payload')),
                ('last_started_at', models.DateTimeField(blank=True, help_text='When this sweep last began (stamped before any work is enqueued)', null=True)),
                ('runs', models.PositiveIntegerField(default=0, help_text='How many times this sweep has been admitted')),
                ('last_started_by', models.CharField(blank=True, default='', help_text='host/pid that last started the sweep, for attribution', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Sweep Guard State',
                'verbose_name_plural': 'Sweep Guard States',
                'db_table': 'sweep_guard_state',
                'managed': True,
            },
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_state_operations),
    ]
