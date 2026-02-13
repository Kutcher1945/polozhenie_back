"""
Management command to fix superusers created without proper role and profile.
"""
from django.core.management.base import BaseCommand
from common.models import User, AdminProfile


class Command(BaseCommand):
    help = 'Fix superusers that were created without proper role and AdminProfile'

    def handle(self, *args, **options):
        self.stdout.write('Checking for superusers without proper configuration...\n')

        # Find all superusers
        superusers = User.objects.filter(is_superuser=True)

        fixed_count = 0
        for user in superusers:
            fixed = False

            # Fix role if not admin
            if user.role != 'admin':
                old_role = user.role
                user.role = 'admin'
                user.save(update_fields=['role'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Updated role for {user.email}: {old_role} → admin'
                    )
                )
                fixed = True

            # Create AdminProfile if it doesn't exist
            admin_profile, created = AdminProfile.objects.get_or_create(
                user=user,
                defaults={
                    'admin_type': 'super',  # Super administrator
                    'clinic': None,  # No clinic = super admin
                    'can_manage_staff': True,
                    'can_manage_patients': True,
                    'can_view_reports': True,
                    'can_manage_settings': True,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created AdminProfile for {user.email}'
                    )
                )
                fixed = True

            if fixed:
                fixed_count += 1

        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ All superusers are properly configured!'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Fixed {fixed_count} superuser(s) successfully!'
                )
            )
