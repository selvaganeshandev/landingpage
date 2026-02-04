"""
Management command to grant domain access to all existing users who don't have it.
This is a one-time fix for users who accepted invitations before the auto-grant feature was added.

Usage:
    python manage.py grant_domain_access
    python manage.py grant_domain_access --dry-run  # Preview changes without applying
"""

from django.core.management.base import BaseCommand
from authentication.models import Account
from domains.models import Domain, DomainAccess


class Command(BaseCommand):
    help = 'Grant domain access to all users in their organization who do not have access yet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made\n'))

        # Get all non-super_admin users with an organization
        users = Account.objects.filter(
            organisation__isnull=False,
            is_active=True
        ).exclude(role='super_admin')

        total_grants = 0

        for user in users:
            # Get all domains in the user's organization
            org_domains = Domain.objects.filter(organisation=user.organisation)

            for domain in org_domains:
                # Check if user already has access
                exists = DomainAccess.objects.filter(user=user, domain=domain).exists()

                if not exists:
                    if dry_run:
                        self.stdout.write(
                            f"  Would grant: {user.email} -> {domain.name}"
                        )
                    else:
                        # Find an admin in the organization to be the granter
                        admin = Account.objects.filter(
                            organisation=user.organisation,
                            role__in=['admin', 'super_admin']
                        ).first()

                        DomainAccess.objects.create(
                            user=user,
                            domain=domain,
                            granted_by=admin
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f"  Granted: {user.email} -> {domain.name}")
                        )
                    total_grants += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nWould grant {total_grants} domain access records'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nGranted {total_grants} domain access records'))
