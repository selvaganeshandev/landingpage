from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the BYOK API-key columns that the
    backend migration (authentication.0005_*) already added to the shared
    `organisations` table.

    The engine and backend point at the same database, so the columns physically
    exist already. We therefore use SeparateDatabaseAndState with only
    state_operations — Django records the fields in its model state but issues NO
    DDL, avoiding a "column already exists" error.
    """

    dependencies = [
        ('shared_models', '0001_initial'),
    ]

    _add_fields = [
        migrations.AddField(
            model_name='organisation',
            name='openai_api_key',
            field=models.TextField(blank=True, help_text='Encrypted OpenAI API Key', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='gemini_api_key',
            field=models.TextField(blank=True, help_text='Encrypted Gemini API Key', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='perplexity_api_key',
            field=models.TextField(blank=True, help_text='Encrypted Perplexity API Key', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='anthropic_api_key',
            field=models.TextField(blank=True, help_text='Encrypted Anthropic API Key', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='xai_api_key',
            field=models.TextField(blank=True, help_text='Encrypted xAI (Grok) API Key', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='deepseek_api_key',
            field=models.TextField(blank=True, help_text='Encrypted DeepSeek API Key', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='openai_enabled',
            field=models.BooleanField(default=True, help_text='Whether OpenAI is enabled'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='gemini_enabled',
            field=models.BooleanField(default=True, help_text='Whether Gemini is enabled'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='perplexity_enabled',
            field=models.BooleanField(default=True, help_text='Whether Perplexity is enabled'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='anthropic_enabled',
            field=models.BooleanField(default=True, help_text='Whether Anthropic is enabled'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='xai_enabled',
            field=models.BooleanField(default=True, help_text='Whether xAI (Grok) is enabled'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='deepseek_enabled',
            field=models.BooleanField(default=True, help_text='Whether DeepSeek is enabled'),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_add_fields),
    ]
