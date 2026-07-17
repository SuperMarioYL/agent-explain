# Plan: Refactor API Endpoints

## Step 1: Read current API routes
Read `src/api/routes.py` to map out all existing endpoints and their handlers.

## Step 2: Create new route structure
Create `src/api/v2/routes.py` with the refactored route structure, grouping endpoints by resource.

## Step 3: Edit the main app
Edit `src/app.py` to register the new v2 routes and add a deprecation header to v1 endpoints.

## Step 4: Run tests and fix
Run `pytest tests/` to verify nothing broke. Fix any failing imports in `src/api/v1/handlers.py`.
