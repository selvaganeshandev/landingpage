from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0008_remove_organisation_content_generation_token_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Administrator'),
                    ('admin', 'Administrator'),
                    ('user', 'User'),
                    ('client', 'Client'),
                ],
                default='user',
                help_text='Role of the account (super-admin, admin, user or client)',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='account',
            name='account_status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('suspended', 'Suspended'),
                    ('pending', 'Pending'),
                    ('disabled', 'Disabled'),
                ],
                default='active',
                help_text='Lifecycle status; non-active accounts are denied access even with a valid token',
                max_length=15,
            ),
        ),
    ]
