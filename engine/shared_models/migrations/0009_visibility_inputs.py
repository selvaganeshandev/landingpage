from django.db import migrations, models


# State-only migration. The columns are created on `domain_metric_snapshots` by
# the BACKEND migration (prompts.0006_visibility_inputs); both trees point at the
# same database, so no DDL is issued here (database_operations is empty) and the
# engine's ORM simply learns the fields exist. Mirrors 0008_prompt_analytics_run.
#
# These are the inputs to the visibility formula. Storing only the finished score
# meant a snapshot could never be rescored when the formula changed, so the
# Insights trend line mixed the old MAX-normalised scores with newly computed
# ones. With the inputs recorded, the gauge and the line are computed from the
# same numbers by the same function.


class Migration(migrations.Migration):

    dependencies = [
        ('shared_models', '0008_prompt_analytics_run'),
    ]

    _state_operations = [
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='period_responses',
            field=models.PositiveIntegerField(default=0, help_text='AI answers checked in this period (visibility denominator)'),
        ),
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='period_mentioned_responses',
            field=models.PositiveIntegerField(default=0, help_text='Answers in this period that mentioned the brand'),
        ),
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='period_own_cited_responses',
            field=models.PositiveIntegerField(default=0, help_text="Answers in this period that cited the brand's own domain"),
        ),
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='period_avg_sentiment',
            field=models.DecimalField(decimal_places=3, default=0.0, help_text="Mean sentiment (-1..1) over this period's mention rows", max_digits=4),
        ),
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='period_avg_position',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text="Mean position over this period's mention rows (0 = unknown)", max_digits=8),
        ),
        migrations.AddField(
            model_name='domainmetricsnapshot',
            name='visibility_formula_version',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, help_text='Which formula produced visibility_score. 0 = legacy MAX-normalised score with no recorded inputs; 1 = rate-based score with the period_* inputs above. Readers must never compare across versions.'),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=_state_operations,
            database_operations=[],
        ),
    ]
