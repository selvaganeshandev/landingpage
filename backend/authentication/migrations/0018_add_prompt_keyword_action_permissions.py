"""Add the six fine-grained prompt/keyword action permissions.

The backfill preserves what each role could already do, which is NOT symmetric
between the two modules:

  * Prompts had no role check at all — any member with the ``prompts`` module
    could add, edit and delete. So every such member is granted all three
    prompt rights; without this they would silently lose access on deploy.

  * Keywords were hardcoded admin-only in the views. Nobody below admin could
    write them, so nothing is granted — admins keep their bypass, and an admin
    hands out ``keywords_*`` deliberately from the team-member page.
"""

from django.db import migrations, models

PROMPT_ACTIONS = ['prompts_add', 'prompts_edit', 'prompts_delete']


def grant_prompt_actions(apps, schema_editor):
    Account = apps.get_model('authentication', 'Account')
    UserPermission = apps.get_model('authentication', 'UserPermission')

    # Admins bypass the grid in code; rows for them would be noise.
    holders = Account.objects.filter(
        permissions__module='prompts',
    ).exclude(role__in=['admin', 'super_admin']).distinct()

    new_rows = []
    for user in holders:
        # granted_by is NOT NULL. Attribute the backfill to an admin of the
        # same organisation where one exists, else to the user themselves —
        # the column records provenance and is not read for access decisions.
        grantor = Account.objects.filter(
            organisation_id=user.organisation_id,
            role__in=['super_admin', 'admin'],
        ).order_by('id').first() or user

        existing = set(
            UserPermission.objects.filter(
                user=user, module__in=PROMPT_ACTIONS,
            ).values_list('module', flat=True)
        )
        for module in PROMPT_ACTIONS:
            if module in existing:
                continue
            new_rows.append(UserPermission(
                user=user,
                module=module,
                permission_level='write',
                granted_by=grantor,
            ))

    UserPermission.objects.bulk_create(new_rows, batch_size=500)


def revoke_prompt_actions(apps, schema_editor):
    UserPermission = apps.get_model('authentication', 'UserPermission')
    UserPermission.objects.filter(
        module__in=PROMPT_ACTIONS + ['keywords_add', 'keywords_edit', 'keywords_delete'],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0017_organisation_subscription_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpermission',
            name='module',
            field=models.CharField(
                choices=[
                    ('dashboard', 'Dashboard'),
                    ('mentions', 'Mentions'),
                    ('prompts', 'Prompts'),
                    ('prompts_add', 'Add Prompts'),
                    ('prompts_edit', 'Edit Prompts'),
                    ('prompts_delete', 'Delete Prompts'),
                    ('alerts', 'Alerts'),
                    ('sentiment_analysis', 'Sentiment Analysis'),
                    ('topics', 'Topics'),
                    ('share_of_voice', 'Share of Voice'),
                    ('historical_trends', 'Historical Trends'),
                    ('content_gaps', 'Content Gaps'),
                    ('competitors', 'Competitors'),
                    ('multilingual', 'Multilingual'),
                    ('ai_copilot', 'AI Copilot'),
                    ('prompt_insights', 'Prompt Insights'),
                    ('agent_analytics', 'Agent Analytics'),
                    ('ai_crawler', 'AI Crawler'),
                    ('traffic_attribution', 'Traffic Attribution'),
                    ('misinformation_alerts', 'Misinformation Alerts'),
                    ('keyword_rankings', 'Keyword Rankings'),
                    ('keywords_add', 'Add Keywords'),
                    ('keywords_edit', 'Edit Keywords'),
                    ('keywords_delete', 'Delete Keywords'),
                    ('seo_competitors', 'SEO Competitors'),
                    ('organic_reports', 'Organic Reports'),
                    ('backlinks', 'Backlinks'),
                    ('reports', 'Reports'),
                    ('organization_settings', 'Organization Settings'),
                    ('team_management', 'Team Management'),
                ],
                help_text='Module the permission applies to',
                max_length=30,
            ),
        ),
        migrations.RunPython(grant_prompt_actions, revoke_prompt_actions),
    ]
