from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domains', '0008_domainregion'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainaccess',
            name='access_level',
            field=models.CharField(
                choices=[
                    ('viewer', 'Viewer'),
                    ('analyst', 'Analyst'),
                    ('manager', 'Manager'),
                ],
                default='viewer',
                help_text='Granular access level (reserved; unused in Phase 1)',
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name='domainaccess',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='Soft-delete flag; False revokes access while preserving history',
            ),
        ),
    ]
