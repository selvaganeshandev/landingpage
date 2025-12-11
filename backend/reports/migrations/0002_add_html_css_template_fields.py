# Generated manually for adding HTML and CSS template fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporttemplate',
            name='html_template',
            field=models.TextField(blank=True, help_text='Rendered HTML template with placeholders for data injection', null=True),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='css_template',
            field=models.TextField(blank=True, help_text='Compiled CSS styles (Tailwind) for the template', null=True),
        ),
    ]
