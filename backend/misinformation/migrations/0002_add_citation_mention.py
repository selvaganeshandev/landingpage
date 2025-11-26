# Generated manually for CitationMention model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('domains', '0005_add_misinformation_scan_status'),
        ('prompts', '0001_initial'),
        ('misinformation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CitationMention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('context_snippet', models.TextField(blank=True, help_text='Extracted context where this citation appeared in the response', null=True)),
                ('position_in_response', models.PositiveIntegerField(default=1, help_text='Position of this citation in the response (1st, 2nd, 3rd, etc.)')),
                ('is_primary_source', models.BooleanField(default=False, help_text='Whether this is the primary/main source cited for the claim')),
                ('mentioned_at', models.DateTimeField(auto_now_add=True, help_text='When this citation was mentioned')),
                ('citation_url', models.ForeignKey(help_text='The citation URL being mentioned', on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='misinformation.citationurl')),
                ('domain', models.ForeignKey(help_text='Associated domain (denormalized for query efficiency)', on_delete=django.db.models.deletion.CASCADE, related_name='citation_mentions', to='domains.domain')),
                ('prompt_analytics', models.ForeignKey(help_text='The prompt analytics record containing this citation', on_delete=django.db.models.deletion.CASCADE, related_name='citation_mentions', to='prompts.promptanalytics')),
            ],
            options={
                'verbose_name': 'Citation Mention',
                'verbose_name_plural': 'Citation Mentions',
                'db_table': 'citation_mentions',
                'ordering': ['-mentioned_at'],
            },
        ),
        migrations.AddIndex(
            model_name='citationmention',
            index=models.Index(fields=['domain', '-mentioned_at'], name='citation_me_domain__5c1f7b_idx'),
        ),
        migrations.AddIndex(
            model_name='citationmention',
            index=models.Index(fields=['citation_url', '-mentioned_at'], name='citation_me_citatio_a27e3d_idx'),
        ),
        migrations.AddIndex(
            model_name='citationmention',
            index=models.Index(fields=['prompt_analytics', 'position_in_response'], name='citation_me_prompt__c8d4e1_idx'),
        ),
        migrations.AddIndex(
            model_name='citationmention',
            index=models.Index(fields=['domain', 'citation_url'], name='citation_me_domain__9f8c2a_idx'),
        ),
    ]
