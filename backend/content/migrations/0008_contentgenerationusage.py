# Generated for ContentGenerationUsage token-tracking model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0007_generatedcontent_refurbished_from_and_more'),
        ('authentication', '0006_organisation_content_generation_key'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentGenerationUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature', models.CharField(help_text="Feature that produced the usage (e.g. 'outline', 'generate', 'humanise', 'refurbish')", max_length=50)),
                ('model_name', models.CharField(default='claude-sonnet-4-5', help_text='Claude model used for generation', max_length=50)),
                ('input_tokens', models.IntegerField(default=0, help_text='Prompt/input tokens consumed')),
                ('output_tokens', models.IntegerField(default=0, help_text='Completion/output tokens produced')),
                ('total_tokens', models.IntegerField(default=0, help_text='input_tokens + output_tokens (stored to avoid sum recalculations)')),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed')], default='success', help_text='Whether the generation succeeded or failed', max_length=20)),
                ('error_message', models.TextField(blank=True, help_text='Error message if the generation failed', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organisation', models.ForeignKey(help_text='Organisation this usage event belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='content_generation_usages', to='authentication.organisation')),
                ('user', models.ForeignKey(blank=True, help_text='User who triggered the generation (null for background jobs)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='content_generation_usages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Content Generation Usage',
                'verbose_name_plural': 'Content Generation Usages',
                'db_table': 'content_generation_usages',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['organisation', '-created_at'], name='content_gen_organis_fa85d3_idx'),
                    models.Index(fields=['organisation', 'status', '-created_at'], name='content_gen_organis_212835_idx'),
                ],
            },
        ),
    ]
