from django.db import migrations, models


# State-only migration. The `period_type` column already exists on
# ga_traffic_insights / gsc_traffic_insights (created by the backend app's
# migration 0002_add_period_type_to_traffic_insights). The engine only needs
# Django's migration state to know about the field so its ORM can read/write
# it — no DDL is issued here (database_operations is empty).
PERIOD_TYPE_FIELD = models.CharField(
    max_length=20,
    choices=[
        ('rolling_30d', 'Rolling 30 Days'),
        ('current_month', 'Current Month'),
        ('prev_month', 'Previous Month'),
        ('yoy_month', 'YoY Month'),
    ],
    default='rolling_30d',
    db_index=True,
)


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='gatrafficinsight',
                    name='period_type',
                    field=PERIOD_TYPE_FIELD,
                ),
                migrations.AddField(
                    model_name='gsctrafficinsight',
                    name='period_type',
                    field=PERIOD_TYPE_FIELD,
                ),
            ],
            database_operations=[],
        ),
    ]
