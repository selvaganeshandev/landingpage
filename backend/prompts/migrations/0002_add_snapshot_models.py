# Generated migration for adding visibility_score, sentiment_score to PromptGroup and creating snapshot models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('domains', '0001_initial'),
        ('prompts', '0001_initial'),
    ]

    operations = [
        # Add visibility_score and sentiment_score to PromptGroup
        migrations.AddField(
            model_name='promptgroup',
            name='visibility_score',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Visibility score calculated from average position', max_digits=5),
        ),
        migrations.AddField(
            model_name='promptgroup',
            name='sentiment_score',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Average sentiment score (-1.00 to 1.00)', max_digits=3),
        ),
        # Create PromptMetricSnapshot
        migrations.CreateModel(
            name='PromptMetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(blank=True, help_text='AI platform (null = aggregated across all platforms)', max_length=100, null=True)),
                ('snapshot_date', models.DateField(help_text='Date of the snapshot (can be daily, weekly, monthly, quarterly)')),
                ('period_type', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly')], default='daily', help_text='Type of period this snapshot represents', max_length=20)),
                ('mentions', models.PositiveIntegerField(default=0, help_text='Total mentions')),
                ('citations', models.PositiveIntegerField(default=0, help_text='Total citations')),
                ('visibility_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Visibility score calculated from average position', max_digits=5)),
                ('sentiment_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Average sentiment score (-1.00 to 1.00)', max_digits=3)),
                ('average_position', models.DecimalField(decimal_places=2, default=0.0, help_text='Average position in search results', max_digits=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('prompt', models.ForeignKey(help_text='Prompt this snapshot belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='metric_snapshots', to='prompts.prompt')),
            ],
            options={
                'db_table': 'prompt_metric_snapshots',
                'ordering': ['-snapshot_date'],
            },
        ),
        # Create PromptGroupMetricSnapshot
        migrations.CreateModel(
            name='PromptGroupMetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(blank=True, help_text='AI platform (null = aggregated across all platforms)', max_length=100, null=True)),
                ('snapshot_date', models.DateField(help_text='Date of the snapshot (can be daily, weekly, monthly, quarterly)')),
                ('period_type', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly')], default='daily', help_text='Type of period this snapshot represents', max_length=20)),
                ('mentions', models.PositiveIntegerField(default=0, help_text='Total mentions')),
                ('citations', models.PositiveIntegerField(default=0, help_text='Total citations')),
                ('visibility_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Visibility score calculated from average position', max_digits=5)),
                ('sentiment_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Average sentiment score (-1.00 to 1.00)', max_digits=3)),
                ('average_position', models.DecimalField(decimal_places=2, default=0.0, help_text='Average position in search results', max_digits=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('prompt_group', models.ForeignKey(help_text='Prompt group this snapshot belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='metric_snapshots', to='prompts.promptgroup')),
            ],
            options={
                'db_table': 'prompt_group_metric_snapshots',
                'ordering': ['-snapshot_date'],
            },
        ),
        # Create DomainMetricSnapshot
        migrations.CreateModel(
            name='DomainMetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(blank=True, help_text='AI platform (null = aggregated across all platforms)', max_length=100, null=True)),
                ('snapshot_date', models.DateField(help_text='Date of the snapshot (can be daily, weekly, monthly, quarterly)')),
                ('period_type', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly')], default='daily', help_text='Type of period this snapshot represents', max_length=20)),
                ('mentions', models.PositiveIntegerField(default=0, help_text='Total mentions')),
                ('citations', models.PositiveIntegerField(default=0, help_text='Total citations')),
                ('visibility_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Visibility score calculated from average position', max_digits=5)),
                ('sentiment_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Average sentiment score (-1.00 to 1.00)', max_digits=3)),
                ('average_position', models.DecimalField(decimal_places=2, default=0.0, help_text='Average position in search results', max_digits=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('domain', models.ForeignKey(help_text='Domain this snapshot belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='metric_snapshots', to='domains.domain')),
            ],
            options={
                'db_table': 'domain_metric_snapshots',
                'ordering': ['-snapshot_date'],
            },
        ),
        # Add unique constraints and indexes
        migrations.AlterUniqueTogether(
            name='promptmetricsnapshot',
            unique_together={('prompt', 'platform', 'snapshot_date', 'period_type')},
        ),
        migrations.AlterUniqueTogether(
            name='promptgroupmetricsnapshot',
            unique_together={('prompt_group', 'platform', 'snapshot_date', 'period_type')},
        ),
        migrations.AlterUniqueTogether(
            name='domainmetricsnapshot',
            unique_together={('domain', 'platform', 'snapshot_date', 'period_type')},
        ),
        migrations.AddIndex(
            model_name='promptmetricsnapshot',
            index=models.Index(fields=['prompt', 'snapshot_date'], name='prompt_metr_prompt__snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='promptmetricsnapshot',
            index=models.Index(fields=['platform', 'snapshot_date'], name='prompt_metr_platform_snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='promptmetricsnapshot',
            index=models.Index(fields=['snapshot_date', '-visibility_score'], name='prompt_metr_snapshot_visibility_idx'),
        ),
        migrations.AddIndex(
            model_name='promptmetricsnapshot',
            index=models.Index(fields=['prompt', 'period_type', 'snapshot_date'], name='prompt_metr_prompt__period_idx'),
        ),
        migrations.AddIndex(
            model_name='promptgroupmetricsnapshot',
            index=models.Index(fields=['prompt_group', 'snapshot_date'], name='prompt_grou_prompt__snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='promptgroupmetricsnapshot',
            index=models.Index(fields=['platform', 'snapshot_date'], name='prompt_grou_platform_snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='promptgroupmetricsnapshot',
            index=models.Index(fields=['snapshot_date', '-visibility_score'], name='prompt_grou_snapshot_visibility_idx'),
        ),
        migrations.AddIndex(
            model_name='promptgroupmetricsnapshot',
            index=models.Index(fields=['prompt_group', 'period_type', 'snapshot_date'], name='prompt_grou_prompt__period_idx'),
        ),
        migrations.AddIndex(
            model_name='domainmetricsnapshot',
            index=models.Index(fields=['domain', 'snapshot_date'], name='domain_metr_domain__snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='domainmetricsnapshot',
            index=models.Index(fields=['platform', 'snapshot_date'], name='domain_metr_platform_snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='domainmetricsnapshot',
            index=models.Index(fields=['snapshot_date', '-visibility_score'], name='domain_metr_snapshot_visibility_idx'),
        ),
        migrations.AddIndex(
            model_name='domainmetricsnapshot',
            index=models.Index(fields=['domain', 'period_type', 'snapshot_date'], name='domain_metr_domain__period_idx'),
        ),
    ]

