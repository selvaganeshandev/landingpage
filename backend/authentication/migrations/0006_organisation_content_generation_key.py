# Generated for Content Generation API key (BYOK for Strategy pipeline)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_organisation_anthropic_api_key_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='content_generation_api_key',
            field=models.TextField(blank=True, help_text='Encrypted API Key for Content Generation', null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='content_generation_token_limit',
            field=models.BigIntegerField(blank=True, help_text='Optional monthly token limit for content generation (soft/informational only)', null=True),
        ),
    ]
