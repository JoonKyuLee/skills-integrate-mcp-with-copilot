# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign in as a student, parent, provider, or administrator
- Sign up for and withdraw from activities according to account permissions
- Keep public activity browsing available without an account

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                     | Exchange an email and password for a bearer session                 |
| POST   | `/auth/logout`                                                    | Invalidate the current bearer session                               |
| GET    | `/auth/me`                                                        | Get the authenticated user's role and linked students               |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up an authorized student for an activity                       |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Withdraw an authorized student from an activity                  |

Enrollment changes require an `Authorization: Bearer <token>` header. Students
can change only their own enrollment, parents can change only linked students,
and provider or administrator accounts can act for a specified student.

### Demo Accounts

| Role          | Email                        | Password    |
| ------------- | ---------------------------- | ----------- |
| Student       | `student@mergington.edu`      | `learn123`  |
| Parent        | `parent@mergington.edu`       | `family123` |
| Provider      | `teacher@mergington.edu`      | `teach123`  |
| Administrator | `admin@mergington.edu`        | `admin123`  |

User records contain salted PBKDF2 password hashes rather than plaintext
passwords. These credentials are for local demonstration only.

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

All data and login sessions are stored in memory, which means they reset when
the server restarts.
