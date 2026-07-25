import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0010_clientactivitylog'),
        ('domains', '0009_domainaccess_access_level_and_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teaminvitation',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Administrator'), ('user', 'User'), ('client', 'Client')],
                default='user',
                help_text='Role to be assigned to the invited user',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='teaminvitation',
            name='domain',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='client_invitations',
                to='domains.domain',
                help_text='Domain a client invitee is scoped to (client role only)',
            ),
        ),
    ]
