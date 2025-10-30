from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from authentication.models import Organisation, Account, UserPermission


class Command(BaseCommand):
    help = 'Create a super-admin account with email and password'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@pivotroots.com',
            help='Email for the admin account (default: admin@pivotroots.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Password for the admin account (default: admin123)'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='First name for the admin account (default: Admin)'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Last name for the admin account (default: User)'
        )
        parser.add_argument(
            '--organisation-name',
            type=str,
            default='PivotRoots Updated',
            help='Name of the organisation (default: PivotRoots Updated)'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        organisation_name = options['organisation_name']

        self.stdout.write(
            self.style.SUCCESS(f'Creating super-admin account: {email}')
        )

        try:
            with transaction.atomic():
                # Get or create organisation
                organisation, org_created = Organisation.objects.get_or_create(
                    name=organisation_name,
                    defaults={
                        'industry': 'Technology',
                        'team_count': 1
                    }
                )

                if org_created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created organisation: {organisation.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Using existing organisation: {organisation.name}')
                    )

                # Remove existing account if it exists
                existing_accounts = Account.objects.filter(email=email)
                if existing_accounts.exists():
                    self.stdout.write(
                        self.style.WARNING(f'Removing existing account with email {email}...')
                    )
                    # Delete user permissions first (due to foreign key constraints)
                    UserPermission.objects.filter(user__email=email).delete()
                    existing_accounts.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'Removed existing account')
                    )

                # Create super_admin account
                admin_user = Account.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role='super_admin',
                    organisation=organisation,
                    is_staff=True,
                    is_superuser=True,
                    is_active=True
                )

                # Create all user permissions for the admin
                self.create_all_permissions(admin_user)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created super_admin account with all permissions!\n'
                        f'Email: {admin_user.email}\n'
                        f'Password: {password}\n'
                        f'Organisation: {organisation.name}\n'
                        f'Role: {admin_user.role}\n'
                        f'Permissions: All modules with admin access'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating admin account: {str(e)}')

    def create_all_permissions(self, admin_user):
        """Create all module permissions for the admin user"""
        # Get all available modules from UserPermission model
        modules = [choice[0] for choice in UserPermission.MODULE_CHOICES]
        
        permissions_created = 0
        for module in modules:
            permission, created = UserPermission.objects.get_or_create(
                user=admin_user,
                module=module,
                defaults={
                    'permission_level': 'admin',
                    'granted_by': admin_user
                }
            )
            if created:
                permissions_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {permissions_created} permissions for admin user')
        )
