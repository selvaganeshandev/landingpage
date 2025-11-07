# Generated migration for updating SentimentAnalytics to snapshot pattern

from django.db import migrations, models


def migrate_timestamp_to_snapshot_date(apps, schema_editor):
    """Migrate existing timestamp data to snapshot_date and set period_type to daily"""
    SentimentAnalytics = apps.get_model('analytics', 'SentimentAnalytics')
    for record in SentimentAnalytics.objects.all():
        record.snapshot_date = record.timestamp
        record.period_type = 'daily'
        # Set default values for new fields
        record.mentions = record.mention_count
        record.citations = 0  # Default, will be calculated later
        record.visibility_score = 0.00
        record.sentiment_score = 0.00
        record.average_position = 0.00
        record.save()


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_initial'),
    ]

    operations = [
        # Add new fields first (nullable initially)
        migrations.AddField(
            model_name='sentimentanalytics',
            name='snapshot_date',
            field=models.DateField(help_text='Date of the snapshot (can be daily, weekly, monthly, quarterly)', null=True),
        ),
        migrations.AddField(
            model_name='sentimentanalytics',
            name='period_type',
            field=models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly')], default='daily', help_text='Type of period this snapshot represents', max_length=20),
        ),
        migrations.AddField(
            model_name='sentimentanalytics',
            name='mentions',
            field=models.PositiveIntegerField(default=0, help_text='Total mentions'),
        ),
        migrations.AddField(
            model_name='sentimentanalytics',
            name='citations',
            field=models.PositiveIntegerField(default=0, help_text='Total citations'),
        ),
        migrations.AddField(
            model_name='sentimentanalytics',
            name='visibility_score',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
        ),
        migrations.AddField(
            model_name='sentimentanalytics',
            name='sentiment_score',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=3),
        ),
        migrations.AddField(
            model_name='sentimentanalytics',
            name='average_position',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Average position in search results', max_digits=8),
        ),
        # Migrate data from timestamp to snapshot_date
        migrations.RunPython(migrate_timestamp_to_snapshot_date, migrations.RunPython.noop),
        # Make snapshot_date non-nullable
        migrations.AlterField(
            model_name='sentimentanalytics',
            name='snapshot_date',
            field=models.DateField(help_text='Date of the snapshot (can be daily, weekly, monthly, quarterly)'),
        ),
        # Remove old timestamp field
        migrations.RemoveField(
            model_name='sentimentanalytics',
            name='timestamp',
        ),
        # Update unique_together
        migrations.AlterUniqueTogether(
            name='sentimentanalytics',
            unique_together={('domain', 'theme', 'platform', 'snapshot_date', 'period_type')},
        ),
        # Update indexes
        migrations.RemoveIndex(
            model_name='sentimentanalytics',
            name='sentiment_a_domain__760a5b_idx',
        ),
        migrations.RemoveIndex(
            model_name='sentimentanalytics',
            name='sentiment_a_theme_d98b66_idx',
        ),
        migrations.RemoveIndex(
            model_name='sentimentanalytics',
            name='sentiment_a_domain__508f7c_idx',
        ),
        migrations.RemoveIndex(
            model_name='sentimentanalytics',
            name='sentiment_a_domain__ff51e2_idx',
        ),
        migrations.RemoveIndex(
            model_name='sentimentanalytics',
            name='sentiment_a_timesta_b59eac_idx',
        ),
        migrations.AddIndex(
            model_name='sentimentanalytics',
            index=models.Index(fields=['domain', 'snapshot_date'], name='sentiment_a_domain__snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='sentimentanalytics',
            index=models.Index(fields=['theme', 'snapshot_date'], name='sentiment_a_theme_snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='sentimentanalytics',
            index=models.Index(fields=['domain', 'platform', 'snapshot_date'], name='sentiment_a_domain__platform_snapshot_idx'),
        ),
        migrations.AddIndex(
            model_name='sentimentanalytics',
            index=models.Index(fields=['domain', 'theme', '-sentiment_score'], name='sentiment_a_domain__theme_sentiment_idx'),
        ),
        migrations.AddIndex(
            model_name='sentimentanalytics',
            index=models.Index(fields=['snapshot_date', '-mention_count'], name='sentiment_a_snapshot_mention_idx'),
        ),
        migrations.AddIndex(
            model_name='sentimentanalytics',
            index=models.Index(fields=['domain', 'period_type', 'snapshot_date'], name='sentiment_a_domain__period_snapshot_idx'),
        ),
        # Update ordering
        migrations.AlterModelOptions(
            name='sentimentanalytics',
            options={'ordering': ['-snapshot_date']},
        ),
    ]

