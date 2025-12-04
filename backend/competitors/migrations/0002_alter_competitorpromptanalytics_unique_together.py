# Generated migration to update unique_together constraint

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('competitors', '0001_initial'),
        ('prompts', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='competitorpromptanalytics',
            unique_together={('competitor', 'prompt', 'platform')},
        ),
    ]
