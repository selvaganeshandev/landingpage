"""
Free the organisation slot held by domain-scoped alert configurations.

AlertConfiguration carries two partial unique constraints — one per domain, one
per organisation — so a row is meant to be scoped to exactly one of them. Both
existing rows had `domain` AND `organisation` set, which made each one occupy
its organisation's single slot. The consequence was that the second domain in an
organisation could never save an email configuration: the insert failed with
`unique_org_config` and the endpoint returned a 500.

Clearing `organisation` on domain-scoped rows restores the intended shape. No
information is lost — the organisation is reachable through `domain.organisation`
— and org-scoped rows (domain NULL) are untouched.
"""
from django.db import migrations


def release_org_slot(apps, schema_editor):
    AlertConfiguration = apps.get_model('alerts', 'AlertConfiguration')
    AlertConfiguration.objects.filter(
        domain__isnull=False, organisation__isnull=False
    ).update(organisation=None)


def restore_org(apps, schema_editor):
    """Re-point organisation at the domain's org.

    Only reversible while at most one domain per organisation holds a config —
    beyond that the constraint this migration exists to relieve would reject the
    write, which is the original bug.
    """
    AlertConfiguration = apps.get_model('alerts', 'AlertConfiguration')
    for config in AlertConfiguration.objects.filter(domain__isnull=False, organisation__isnull=True).select_related('domain'):
        config.organisation_id = config.domain.organisation_id
        config.save(update_fields=['organisation'])


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0003_alter_alertconfiguration_email_address'),
    ]

    operations = [
        migrations.RunPython(release_org_slot, restore_org),
    ]
