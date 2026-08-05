"""Commercial profile fields used by the AI prompt-generation wizard.

All additive and nullable — two thirds of existing domains predate them and
must keep working untouched.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domains', '0009_domainaccess_access_level_and_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='domain',
            name='business_model',
            field=models.CharField(
                blank=True, default='', max_length=64,
                help_text='B2C ecommerce, B2B SaaS, Local services, ... — selects the prompt intent taxonomy',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='offering_categories',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Product/service categories the brand sells',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='regions_served',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Cities/regions served — country alone is too coarse for local queries',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='price_positioning',
            field=models.CharField(
                blank=True, default='', max_length=32,
                help_text='Budget | Mid-market | Premium | Mixed',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='use_cases',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Use cases and occasions that drive purchases',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='buying_criteria',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Decision factors, e.g. same-day delivery, price, compliance',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='common_objections',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Pre-purchase concerns — feeds trust prompts',
            ),
        ),
        migrations.AddField(
            model_name='domain',
            name='differentiators',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Why customers choose this brand — feeds comparison prompts',
            ),
        ),
    ]
