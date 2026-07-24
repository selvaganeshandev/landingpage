import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_account_client_role_and_status'),
        ('domains', '0009_domainaccess_access_level_and_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('login', 'Login'), ('logout', 'Logout'), ('export_report', 'Export Report')], help_text='What the client did', max_length=50)),
                ('details', models.JSONField(blank=True, default=dict, help_text='Optional structured context for the action')),
                ('ip_address', models.GenericIPAddressField(blank=True, help_text='Client IP address at the time of the action', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(blank=True, help_text='Domain in context when the action occurred, if any', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_activity_logs', to='domains.domain')),
                ('user', models.ForeignKey(help_text='Account the activity belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='activity_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Client Activity Log',
                'verbose_name_plural': 'Client Activity Logs',
                'db_table': 'client_activity_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='clientactivitylog',
            index=models.Index(fields=['user', '-created_at'], name='client_acti_user_id_c93507_idx'),
        ),
    ]
