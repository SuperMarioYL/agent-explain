# Plan: Add User Authentication

## Step 1: Read the auth module
Read `src/auth.py` to understand the current authentication flow and identify where password validation should be added.

## Step 2: Create the users migration
Create `migrations/001_add_users.py` with the user table schema, including columns for username, password_hash, and created_at.

## Step 3: Edit the auth module
Edit `src/auth.py` to add password validation logic using bcrypt, and update the login handler to check against the new users table.

## Step 4: Delete the old config and run migration
Delete `config/old_settings.json` — it's replaced by the database schema. Then run `python manage.py migrate` to apply the migration.

## Step 5: Add tests
Create `tests/test_auth.py` with unit tests for the new password validation and integration tests for the login flow.
