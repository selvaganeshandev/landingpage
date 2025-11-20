from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shared_models', '0003_competitormetricsnapshot_platform_metrics'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompetitiveInsight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('insight_type', models.CharField(blank=True, max_length=100, null=True)),
                ('category', models.CharField(blank=True, max_length=100, null=True)),
                ('impact', models.CharField(choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium', max_length=20)),
                ('snapshot_version', models.CharField(max_length=255)),
                ('insight_data', models.JSONField(blank=True, default=dict)),
                ('model_name', models.CharField(blank=True, max_length=100, null=True)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitive_insights', to='shared_models.domain')),
            ],
            options={
                'db_table': 'competitive_insights',
                'ordering': ['-generated_at'],
                'indexes': [models.Index(fields=['domain', '-generated_at'], name='competitive_domain__03f183_idx'), models.Index(fields=['domain', 'snapshot_version'], name='competitive_domain__c96e1f_idx'), models.Index(fields=['impact'], name='competitive_impact_f5e03d_idx')],
                'unique_together': {('domain', 'snapshot_version', 'title')},
            },
        ),
    ]

