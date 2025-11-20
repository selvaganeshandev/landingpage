from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shared_models', '0002_competitormetricsnapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='competitormetricsnapshot',
            name='platform_metrics',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='competitormetricsnapshot',
            name='competitor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shared_metric_snapshots', to='shared_models.competitor'),
        ),
    ]

