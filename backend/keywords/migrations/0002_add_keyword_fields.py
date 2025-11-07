# Generated migration for adding keyword auto-generation fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keywords', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='keyword',
            name='auto_generate_prompts',
            field=models.BooleanField(default=True, help_text='If True, this keyword will be used to auto-generate prompt groups'),
        ),
        migrations.AddField(
            model_name='keyword',
            name='priority',
            field=models.IntegerField(default=0, help_text='Priority for prompt generation (higher = more important)'),
        ),
        migrations.AddField(
            model_name='keyword',
            name='last_used_for_generation',
            field=models.DateTimeField(blank=True, help_text='When this keyword was last used to generate prompts', null=True),
        ),
        migrations.AddIndex(
            model_name='keyword',
            index=models.Index(fields=['domain', 'auto_generate_prompts', 'priority'], name='keywords_domain__auto_gen_idx'),
        ),
        migrations.AddIndex(
            model_name='keyword',
            index=models.Index(fields=['domain', 'last_used_for_generation'], name='keywords_domain__last_use_idx'),
        ),
    ]

