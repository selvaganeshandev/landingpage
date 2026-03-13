from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('domains', '0001_initial'),
        ('seo_rankings', '0004_add_seo_competitor_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeoReportSheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sheet_name', models.CharField(help_text='Report display name', max_length=255)),
                ('category', models.CharField(
                    choices=[
                        ('gsc', 'Google Search Console'),
                        ('ga', 'Google Analytics'),
                        ('rank', 'Keyword Ranking'),
                        ('base', 'Domain Metrics'),
                        ('overview', 'Summary'),
                    ],
                    default='gsc',
                    help_text='Report category tab',
                    max_length=20,
                )),
                ('sheet_type', models.CharField(
                    choices=[
                        ('gsc_queries', 'GSC Queries'),
                        ('gsc_branded_queries', 'GSC Branded Queries'),
                        ('gsc_non_branded_queries', 'GSC Non-Branded Queries'),
                        ('gsc_pages', 'GSC Pages'),
                        ('ga_landing_pages', 'GA Landing Pages'),
                        ('ga_other_sources', 'GA Other Sources'),
                        ('ga_overview', 'GA Overview'),
                        ('keyword_ranking', 'Keyword Ranking'),
                        ('domain_metrics', 'Domain Metrics'),
                        ('gsc_overview', 'GSC Overview'),
                        ('keyword_ranking_overview', 'Keyword Ranking Overview'),
                    ],
                    help_text='Type of data in this report sheet',
                    max_length=30,
                )),
                ('metrics', models.JSONField(blank=True, default=list, help_text='Selected metrics for the report')),
                ('change_units', models.JSONField(blank=True, default=list, help_text='Comparison units: number, percentage')),
                ('schedule', models.CharField(
                    choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')],
                    default='weekly',
                    max_length=10,
                )),
                ('duration', models.IntegerField(default=2, help_text='Number of intervals to include')),
                ('order_by', models.CharField(default='Ascending', help_text='Date sort order', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seo_report_sheets',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('domain', models.ForeignKey(
                    help_text='Domain this report belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seo_report_sheets',
                    to='domains.domain',
                )),
            ],
            options={
                'verbose_name': 'SEO Report Sheet',
                'verbose_name_plural': 'SEO Report Sheets',
                'db_table': 'seo_report_sheets',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['domain', '-created_at'], name='seo_report_sh_domain__6e9a3c_idx'),
                    models.Index(fields=['domain', 'category'], name='seo_report_sh_domain__8f2b1a_idx'),
                ],
            },
        ),
    ]
