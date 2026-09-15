# Audit Engine Phase O — per-page technical-SEO details (add-only, safe to reverse).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audits', '0003_rival_positions'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditpageresult',
            name='details',
            field=models.JSONField(blank=True, default=dict, help_text='Technical / on-page signals: title and description lengths, H1 count, canonical, noindex, viewport, images, internal links, schema gaps, crawl depth, status code'),
        ),
    ]
