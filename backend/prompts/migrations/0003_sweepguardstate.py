from django.db import migrations, models


def _seed(apps, schema_editor):
    """Create the two known sweep rows so the guard always has a row to read."""
    SweepGuardState = apps.get_model('prompts', 'SweepGuardState')
    for sweep in ('prompts', 'competitors'):
        SweepGuardState.objects.get_or_create(sweep=sweep)


def _unseed(apps, schema_editor):
    SweepGuardState = apps.get_model('prompts', 'SweepGuardState')
    SweepGuardState.objects.filter(sweep__in=('prompts', 'competitors')).delete()


class Migration(migrations.Migration):
    """Create `sweep_guard_state`, the cross-machine control table for the
    weekly full-corpus reprocess sweeps.

    The engine's cost guard previously kept its cooldown in a JSON file under
    BASE_DIR, which made it per-machine — a sweep run from a laptop against this
    database never saw the server's cooldown and vice versa. This table moves
    that state into the one place every caller must reach.

    Seeds the two known sweeps so the row exists before the first check; both
    start enabled, matching today's behaviour (the kill switch is opt-in).
    """

    dependencies = [
        ('prompts', '0002_alter_domainmetricsnapshot_unique_together_and_more'),
    ]

    operations = [
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
            },
        ),
        migrations.RunPython(_seed, _unseed),
    ]
