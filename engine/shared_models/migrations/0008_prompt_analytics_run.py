import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the `prompt_analytics_runs` table that
    the BACKEND migration (prompts.0005_prompt_analytics_run) physically creates
    on the shared DB.

    The engine and backend point at the same database, so the table is created
    once by the backend's real migration. Here we use SeparateDatabaseAndState
    with ONLY state_operations — Django records the model in the engine's state
    but issues NO DDL, avoiding "table already exists". This mirrors
    0007_sweep_guard_state.

    The table is the append-only run history the engine writes alongside each
    PromptAnalytics row: that row is update_or_create'd per
    (prompt, platform, region), so it holds only the latest run and overwrites
    everything before it.
    """

    dependencies = [
        ('shared_models', '0007_sweep_guard_state'),
    ]

    _state_operations = [
        migrations.CreateModel(
            name='PromptAnalyticsRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(help_text='Canonical platform label for this run', max_length=100)),
                ('region', models.CharField(db_index=True, default='GLOBAL', help_text="Geographic region: ISO 3166-1 alpha-2 country code, or 'GLOBAL' for unattributed.", max_length=8)),
                ('tracked_at', models.DateTimeField(db_index=True, help_text='When this run completed')),
                ('is_mention', models.BooleanField(default=False, help_text='Whether the brand was mentioned in this run')),
                ('total_mentions', models.PositiveIntegerField(default=0, help_text='Mentions recorded by this run')),
                ('total_citations', models.PositiveIntegerField(default=0, help_text='Domain-specific citations recorded by this run')),
                ('position', models.DecimalField(decimal_places=2, default=0.0, help_text="Position of the brand in this run's answer", max_digits=8)),
                ('sentiment_category', models.CharField(choices=[('positive', 'Positive'), ('neutral', 'Neutral'), ('negative', 'Negative')], default='neutral', help_text='Sentiment category for this run', max_length=10)),
                ('sentiment_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Sentiment score (-1.00 to 1.00) for this run', max_digits=3)),
                ('citation_list', models.JSONField(blank=True, default=list, help_text="Every URL cited in this run's answer")),
                ('competitor_mention_list', models.JSONField(blank=True, default=list, help_text="Competitors mentioned in this run's answer")),
                ('context_summary', models.TextField(blank=True, help_text="Summary of this run's answer")),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this history row was written')),
                ('prompt', models.ForeignKey(help_text='Prompt this run belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='analytics_runs', to='shared_models.prompt')),
            ],
            options={
                'verbose_name': 'Prompt Analytics Run',
                'verbose_name_plural': 'Prompt Analytics Runs',
                'db_table': 'prompt_analytics_runs',
                'ordering': ['-tracked_at'],
                'unique_together': {('prompt', 'platform', 'region', 'tracked_at')},
            },
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=_state_operations,
            database_operations=[],
        ),
    ]
