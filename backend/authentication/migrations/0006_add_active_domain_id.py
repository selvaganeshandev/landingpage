# Generated manually for active_domain_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_alter_passwordresettoken_expires_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='active_domain_id',
            field=models.IntegerField(blank=True, help_text="ID of the currently active domain for this user", null=True),
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['active_domain_id'], name='accounts_active_d_idx'),
        ),
    ]

