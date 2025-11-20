from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shared_models', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompetitorMetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('total_mentions', models.IntegerField(default=0)),
                ('total_citations', models.IntegerField(default=0)),
                ('visibility_score', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('sentiment_score', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('average_position', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('share_of_voice_percentage', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('trend_percentage', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)),
                ('track_status', models.CharField(blank=True, max_length=4, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('competitor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_metric_snapshots', to='shared_models.competitor')),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_metric_snapshots', to='shared_models.domain')),
            ],
            options={
                'db_table': 'competitor_metric_snapshots',
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['competitor', '-timestamp'], name='competitor__competit_cc2fe3_idx'), models.Index(fields=['domain', '-timestamp'], name='competitor__domain__4ef818_idx')],
            },
        ),
    ]

