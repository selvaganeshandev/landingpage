import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the geographic AI-mention tracking
    (G1) schema that the BACKEND migrations physically apply on the shared DB:

      - a `region` column on `prompt_analytics` and `domain_metric_snapshots`,
        widening their unique keys to include `region`, and
      - the new `domain_regions` table (backend app: domains.DomainRegion).

    The engine and backend point at the same database, so these objects are
    created by the backend's real migrations. Here we use
    SeparateDatabaseAndState with ONLY state_operations — Django records them in
    the engine's model state but issues NO DDL, avoiding
    "column/table already exists" errors. This mirrors
    0003_content_generation_key_and_usage.

    See docs/GEO_AI_MENTION_TRACKING_DESIGN.md.
    """

    dependencies = [
        ('shared_models', '0003_content_generation_key_and_usage'),
    ]

    _region_field = dict(
        max_length=8,
        default='GLOBAL',
        db_index=True,
        help_text=(
            "Geographic region: ISO 3166-1 alpha-2 country code, or 'GLOBAL' "
            "for unattributed. See docs/GEO_AI_MENTION_TRACKING_DESIGN.md."
        ),
    )

    _state_operations = [
        migrations.AddField(
            model_name='promptanalytics',
            name='region',
            field=models.CharField(**_region_field),
        ),
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='region',
            field=models.CharField(**_region_field),
        ),
        migrations.AlterUniqueTogether(
            name='promptanalytics',
            unique_together={('prompt', 'platform', 'region')},
        ),
        migrations.AlterUniqueTogether(
            name='domainmetricsnapshot',
            unique_together={('domain', 'platform', 'snapshot_date', 'period_type', 'region')},
        ),
        migrations.CreateModel(
            name='DomainRegion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country_code', models.CharField(help_text="ISO 3166-1 alpha-2 country code, e.g. 'IN', 'US'", max_length=2)),
                ('country_name', models.CharField(help_text="Human-readable country name for display, e.g. 'India'", max_length=100)),
                ('locale', models.CharField(blank=True, help_text="Optional locale hint for prompt localization, e.g. 'en-IN'", max_length=10)),
                ('is_active', models.BooleanField(default=True, help_text='Whether the engine should query this region on the next run')),
                ('is_primary', models.BooleanField(default=False, help_text='Primary region for the domain (seeded from Domain.country)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('domain', models.ForeignKey(help_text='Domain this tracked region belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='regions', to='shared_models.domain')),
            ],
            options={
                'verbose_name': 'Domain Region',
                'verbose_name_plural': 'Domain Regions',
                'db_table': 'domain_regions',
                'ordering': ['-is_primary', 'country_name'],
                'managed': True,
                'unique_together': {('domain', 'country_code')},
            },
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_state_operations),
    ]
