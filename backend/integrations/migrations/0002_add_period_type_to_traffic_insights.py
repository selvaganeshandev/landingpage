from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gatrafficinsight',
            name='period_type',
            field=models.CharField(
                choices=[
                    ('rolling_30d', 'Rolling 30 Days'),
                    ('current_month', 'Current Month'),
                    ('prev_month', 'Previous Month'),
                    ('yoy_month', 'YoY Month'),
                ],
                default='rolling_30d',
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='gsctrafficinsight',
            name='period_type',
            field=models.CharField(
                choices=[
                    ('rolling_30d', 'Rolling 30 Days'),
                    ('current_month', 'Current Month'),
                    ('prev_month', 'Previous Month'),
                    ('yoy_month', 'YoY Month'),
                ],
                default='rolling_30d',
                db_index=True,
                max_length=20,
            ),
        ),
    ]
