# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the application:

   ```
   export REGISTRATION_INVITE_CODE='provide-a-school-invitation-code'
   export ADMIN_EMAIL='administrator@mergington.edu'
   export ADMIN_PASSWORD='use-a-unique-password-of-at-least-12-characters'
   uvicorn app:app --app-dir src --reload
   ```

3. Open your browser and go to:
   - Activities: http://localhost:8000/
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Accounts and roles

- New accounts require a school invitation code and an email at `mergington.edu` (override with `SCHOOL_EMAIL_DOMAIN`).
- Passwords must contain at least 12 characters and are stored as salted scrypt hashes.
- Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` to create the initial administrator. Set both variables or neither.
- Administrators can promote users to `activity_manager` or `administrator` with `PATCH /users/{email}/role` using an administrator bearer token.
- Sign-in and registration return a one-hour bearer token. The browser keeps it in session storage and clears it on sign-out.
- Accounts, tokens, and activities are currently held in memory and reset when the server restarts. Use HTTPS and keep invitation/admin secrets out of source control.

Run the API tests with:

```sh
python -m unittest discover -s src -p 'test_*.py'
```

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
