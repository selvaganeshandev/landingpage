from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seo_rankings', '0007_alter_seoreportsheet_sheet_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seoreportsheet',
            name='sheet_type',
            field=models.CharField(
                choices=[
                    ('gsc_queries', 'GSC Queries'),
                    ('gsc_branded_queries', 'GSC Branded Queries'),
                    ('gsc_non_branded_queries', 'GSC Non-Branded Queries'),
                    ('gsc_pages', 'GSC Pages'),
                    ('ga_landing_pages', 'GA Landing Pages'),
                    ('ga_other_sources', 'GA Other Sources'),
                    ('ga_gsc_reconcile', 'GA vs GSC Reconciliation'),
                    ('ga_overview', 'GA Overview'),
                    ('keyword_ranking', 'Keyword Ranking'),
                    ('domain_metrics', 'Domain Metrics'),
                    ('gsc_overview', 'GSC Overview'),
                    ('keyword_ranking_overview', 'Keyword Ranking Overview'),
                    ('ga_organic_traffic_breakup', 'GA Organic Traffic Breakup'),
                ],
                help_text='Type of data in this report sheet',
                max_length=30,
            ),
        ),
    ]
