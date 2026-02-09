"""
Migration script to migrate from CustomToken to standard DRF Token
Run this script BEFORE running makemigrations/migrate after switching to standard Token authentication

Usage: python manage.py shell < migrate_tokens.py
"""

from django.db import connection
from rest_framework.authtoken.models import Token

print("=" * 80)
print("TOKEN MIGRATION SCRIPT")
print("=" * 80)

# Check if custom token table exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'common_authtoken'
        );
    """)
    custom_token_exists = cursor.fetchone()[0]

if not custom_token_exists:
    print("✅ Custom token table does not exist. No migration needed.")
    exit(0)

print(f"📋 Custom token table exists: {custom_token_exists}")

# Get all tokens from custom table
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT key, user_id, created_at
        FROM common_authtoken
    """)
    custom_tokens = cursor.fetchall()

print(f"📊 Found {len(custom_tokens)} custom tokens to migrate")

if len(custom_tokens) == 0:
    print("✅ No tokens to migrate.")
    exit(0)

# Check if standard token table exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'authtoken_token'
        );
    """)
    standard_token_exists = cursor.fetchone()[0]

if not standard_token_exists:
    print("❌ Standard token table does not exist. Please run migrations first:")
    print("   python manage.py migrate")
    exit(1)

print(f"✅ Standard token table exists")

# Migrate tokens
migrated = 0
skipped = 0
errors = 0

for key, user_id, created_at in custom_tokens:
    try:
        # Check if token already exists for this user
        existing = Token.objects.filter(user_id=user_id).first()
        if existing:
            print(f"⚠️  Token already exists for user {user_id}, skipping...")
            skipped += 1
            continue

        # Create new token with same key
        Token.objects.create(
            key=key,
            user_id=user_id,
            created=created_at
        )
        print(f"✅ Migrated token for user {user_id}")
        migrated += 1
    except Exception as e:
        print(f"❌ Error migrating token for user {user_id}: {e}")
        errors += 1

print("\n" + "=" * 80)
print("MIGRATION SUMMARY")
print("=" * 80)
print(f"✅ Migrated: {migrated}")
print(f"⚠️  Skipped: {skipped}")
print(f"❌ Errors: {errors}")
print(f"📊 Total: {len(custom_tokens)}")
print("=" * 80)

if errors == 0:
    print("\n✅ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Test the authentication with standard Token")
    print("2. If everything works, you can drop the custom token table:")
    print("   python manage.py dbshell")
    print("   DROP TABLE common_authtoken;")
else:
    print("\n⚠️  Migration completed with errors. Please review the errors above.")
