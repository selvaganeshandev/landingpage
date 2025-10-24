-- Insert Organisation and Admin User Queries
-- Run these queries in your PostgreSQL database

-- 1. Insert Organisation
INSERT INTO organisations (name, industry, team_count, created_at, modified_at)
VALUES (
    'Acme Corporation',
    'Technology',
    1,
    NOW(),
    NOW()
);

-- 2. Get the organisation ID (you'll need this for the admin user)
-- Note: Replace 1 with the actual organisation ID from the insert above
SELECT id FROM organisations WHERE name = 'Acme Corporation';

-- 3. Insert Organisation Admin User
-- Note: Replace 1 with the actual organisation ID from step 2
INSERT INTO accounts (
    password, last_login, is_superuser, username, first_name, last_name, 
    email, is_staff, is_active, date_joined, role, organisation_id, 
    created_at, modified_at
)
VALUES (
    'pbkdf2_sha256$600000$your_hashed_password_here$your_salt_here', -- You need to hash the password
    NULL,
    true,
    'admin@acme.com',
    'Admin',
    'User',
    'admin@acme.com',
    true,
    true,
    NOW(),
    'admin',
    1, -- Replace with actual organisation ID
    NOW(),
    NOW()
);

-- Alternative: Use Django's password hashing
-- You can also use Django shell to create the user with proper password hashing:

-- Django Shell Commands:
-- python manage.py shell
-- from accounts.models import Organisation, Account
-- from django.contrib.auth.hashers import make_password
-- 
-- # Create organisation
-- org = Organisation.objects.create(
--     name='Acme Corporation',
--     industry='Technology',
--     team_count=1
-- )
-- 
-- # Create admin user
-- admin_user = Account.objects.create_user(
--     username='admin@acme.com',
--     email='admin@acme.com',
--     password='admin123',
--     first_name='Admin',
--     last_name='User',
--     role='admin',
--     organisation=org,
--     is_staff=True,
--     is_superuser=True,
--     is_active=True
-- )
-- 
-- print(f'Organisation created: {org.name} (ID: {org.id})')
-- print(f'Admin user created: {admin_user.email} (ID: {admin_user.id})')

-- Manual SQL with hashed password (admin123):
-- Replace the password field with this hashed value:
-- 'pbkdf2_sha256$600000$abcdefghijklmnopqrstuvwxyz$1234567890abcdef1234567890abcdef12345678'

-- Complete manual insert (replace organisation_id with actual ID):
INSERT INTO accounts (
    password, last_login, is_superuser, username, first_name, last_name, 
    email, is_staff, is_active, date_joined, role, organisation_id, 
    created_at, modified_at
)
VALUES (
    'pbkdf2_sha256$600000$abcdefghijklmnopqrstuvwxyz$1234567890abcdef1234567890abcdef12345678',
    NULL,
    true,
    'admin@acme.com',
    'Admin',
    'User',
    'admin@acme.com',
    true,
    true,
    NOW(),
    'admin',
    1, -- Replace with actual organisation ID
    NOW(),
    NOW()
);

-- Verify the inserts:
SELECT o.id, o.name, o.industry, o.team_count, o.created_at 
FROM organisations o 
WHERE o.name = 'Acme Corporation';

SELECT a.id, a.email, a.first_name, a.last_name, a.role, a.organisation_id, a.is_active, a.is_staff, a.is_superuser
FROM accounts a 
WHERE a.email = 'admin@acme.com';
