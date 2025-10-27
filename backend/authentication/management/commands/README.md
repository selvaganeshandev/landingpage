# Django Management Command: seed_admin

## Overview
This command creates a simple admin account with email and password. It automatically creates a default organisation if one doesn't exist.

## Usage

### Basic Usage (Default Values)
```bash
python manage.py seed_admin
```
This creates an admin account with:
- Email: `admin@pivotroots.com`
- Password: `admin123`
- Name: `Admin User`
- Organisation: `PivotRoots Updated`

### Custom Usage
```bash
python manage.py seed_admin --email "your@email.com" --password "yourpassword" --first-name "Your" --last-name "Name" --organisation-name "Your Company"
```

### Parameters
- `--email`: Email for the admin account (default: admin@pivotroots.com)
- `--password`: Password for the admin account (default: admin123)
- `--first-name`: First name for the admin account (default: Admin)
- `--last-name`: Last name for the admin account (default: User)
- `--organisation-name`: Name of the organisation (default: PivotRoots Updated)

### Examples

1. **Create admin with custom email and password:**
   ```bash
   python manage.py seed_admin --email "admin@mycompany.com" --password "securepass123"
   ```

2. **Create admin with full custom details:**
   ```bash
   python manage.py seed_admin --email "john@techcorp.com" --password "mypassword" --first-name "John" --last-name "Doe" --organisation-name "TechCorp Inc"
   ```

3. **Create admin for existing organisation:**
   ```bash
   python manage.py seed_admin --email "newadmin@company.com" --organisation-name "Existing Company"
   ```

## Features
- ✅ Automatically creates organisation if it doesn't exist
- ✅ Prevents duplicate admin accounts
- ✅ Uses database transactions for safety
- ✅ Provides clear success/error messages
- ✅ Supports custom parameters
- ✅ Follows Django best practices

## Notes
- The command will warn if an admin account with the same email already exists
- The organisation will be reused if it already exists
- All admin accounts are created with `is_staff=True` and `is_superuser=True`
- The command uses Django's built-in password hashing
