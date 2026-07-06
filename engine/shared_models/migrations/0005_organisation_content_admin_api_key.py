from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the `content_admin_api_key` column
    that the backend migration (authentication.0007_*) physically adds to the
    shared `organisations` table.

    State-only (SeparateDatabaseAndState) — Django records the column in the
    engine's model state but issues NO DDL, avoiding "column already exists".
    Mirrors 0003_content_generation_key_and_usage.
    """

    dependencies = [
        ('shared_models', '0004_geo_region_g1'),
    ]

    _state_operations = [
        migrations.AddField(
            model_name='organisation',
            name='content_admin_api_key',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Encrypted Anthropic Admin API Key for live usage reporting',
            ),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_state_operations),
    ]
