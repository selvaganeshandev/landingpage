from django.db import migrations


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the removal of the
    `content_generation_token_limit` column from the shared `organisations`
    table (physically dropped by backend authentication.0008_*).

    State-only (SeparateDatabaseAndState) — issues NO DDL. Mirrors the
    0003/0004/0005 pattern.
    """

    dependencies = [
        ('shared_models', '0005_organisation_content_admin_api_key'),
    ]

    _state_operations = [
        migrations.RemoveField(
            model_name='organisation',
            name='content_generation_token_limit',
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_state_operations),
    ]
