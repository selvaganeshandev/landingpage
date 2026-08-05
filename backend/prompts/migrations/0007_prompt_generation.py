"""Prompt generation runs and their candidates.

Candidates are kept out of the `prompts` table on purpose: nothing generated is
trackable, billable, or visible in analytics until a user accepts it.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0006_visibility_inputs'),
        ('domains', '0010_domain_commercial_profile'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptGenerationRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[
                    ('INIT', 'Queued'), ('PROC', 'Processing'), ('DONE', 'Ready for review'),
                    ('FAIL', 'Failed'), ('ACPT', 'Accepted'), ('DISC', 'Discarded'),
                ], default='INIT', max_length=4)),
                ('stage', models.CharField(blank=True, choices=[
                    ('ground', 'Reading your site'),
                    ('entities', 'Understanding what you offer'),
                    ('expand', 'Writing prompts'),
                    ('dedup', 'Removing duplicates'),
                    ('score', 'Checking which ones surface brands'),
                    ('assemble', 'Grouping by theme'),
                ], default='', max_length=16)),
                ('progress', models.PositiveSmallIntegerField(default=0, help_text='0-100')),
                ('config', models.JSONField(blank=True, default=dict)),
                ('grounding', models.JSONField(blank=True, default=dict)),
                ('error', models.TextField(blank=True, default='')),
                ('tokens_used', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('domain', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='prompt_generation_runs', to='domains.domain')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='prompt_generation_runs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Prompt Generation Run',
                'verbose_name_plural': 'Prompt Generation Runs',
                'db_table': 'prompt_generation_runs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromptCandidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('intent', models.CharField(blank=True, choices=[
                    ('discovery', 'Discovery'), ('comparison', 'Comparison'),
                    ('evaluation', 'Evaluation'), ('use_case', 'Use case'),
                    ('problem', 'Problem'), ('brand', 'Brand'), ('trust', 'Trust'),
                ], default='', max_length=16)),
                ('entity', models.CharField(blank=True, default='', max_length=255)),
                ('is_branded', models.BooleanField(default=False)),
                ('cluster_key', models.CharField(blank=True, default='', max_length=255)),
                ('cluster_title', models.CharField(blank=True, default='', max_length=255)),
                ('score_realism', models.FloatField(default=0)),
                ('score_elicits_brands', models.FloatField(default=0)),
                ('brands_seen', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[
                    ('pending', 'Pending review'), ('accepted', 'Accepted'), ('rejected', 'Rejected'),
                ], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('run', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='candidates', to='prompts.promptgenerationrun')),
            ],
            options={
                'verbose_name': 'Prompt Candidate',
                'verbose_name_plural': 'Prompt Candidates',
                'db_table': 'prompt_candidates',
                'ordering': ['cluster_key', '-score_elicits_brands'],
            },
        ),
        migrations.AddIndex(
            model_name='promptgenerationrun',
            index=models.Index(fields=['domain', 'status'], name='pgr_domain_status_idx'),
        ),
        migrations.AddIndex(
            model_name='promptgenerationrun',
            index=models.Index(fields=['status'], name='pgr_status_idx'),
        ),
        migrations.AddIndex(
            model_name='promptcandidate',
            index=models.Index(fields=['run', 'status'], name='pc_run_status_idx'),
        ),
    ]
