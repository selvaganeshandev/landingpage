import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync the engine's migration STATE with the Content-Generation columns and
    the ContentGenerationUsage table that the backend migrations
    (authentication.0006_* and content.0008_*) already created on the shared
    database.

    The engine and backend point at the same database, so these objects
    physically exist already. We use SeparateDatabaseAndState with only
    state_operations — Django records them in its model state but issues NO DDL,
    avoiding "column/table already exists" errors.
    """

    dependencies = [
        ('shared_models', '0002_organisation_byok_api_keys'),
    ]

    _state_operations = [
        migrations.AddField(
            model_name='organisation',
            name='content_generation_api_key',
            field=models.TextField(blank=True, help_text='Encrypted API Key for Content Generation', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='content_generation_token_limit',
            field=models.BigIntegerField(blank=True, help_text='Optional monthly token limit for content generation', null=True),
        ),
        migrations.CreateModel(
            name='ContentGenerationUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature', models.CharField(max_length=50)),
                ('model_name', models.CharField(default='claude-sonnet-4-5', max_length=50)),
                ('input_tokens', models.IntegerField(default=0)),
                ('output_tokens', models.IntegerField(default=0)),
                ('total_tokens', models.IntegerField(default=0)),
                ('status', models.CharField(default='success', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_generation_usages', to='shared_models.organisation')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='content_generation_usages', to='shared_models.account')),
            ],
            options={
                'db_table': 'content_generation_usages',
                'managed': True,
                'ordering': ['-created_at'],
            },
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_state_operations),
    ]
