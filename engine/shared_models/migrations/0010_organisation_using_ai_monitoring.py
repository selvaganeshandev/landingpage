from django.db import migrations, models


# State-only migration. `using_ai_monitoring` is created on `organisations` by
# the BACKEND; both trees point at the same database, so no DDL is issued here
# and the engine's ORM simply learns the field exists. Mirrors 0002.
#
# The engine needs to read it because the weekly sweep is the one place that
# spends money on behalf of an organisation that may have switched monitoring
# off — re-querying every platform for an org that is not using the feature is
# pure waste. See core/processing_tasks.schedule_weekly_prompt_batches.


class Migration(migrations.Migration):

    dependencies = [
        ('shared_models', '0009_visibility_inputs'),
    ]

    _add_fields = [
        migrations.AddField(
            model_name='organisation',
            name='using_ai_monitoring',
            field=models.BooleanField(
                blank=True,
                null=True,
                help_text='Whether the organisation is actively using AI monitoring',
            ),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=_add_fields),
    ]
