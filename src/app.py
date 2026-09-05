"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
from pathlib import Path
import secrets
from typing import Literal, TypedDict

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


class PasswordRecord(TypedDict):
    salt: str
    digest: str


class UserRecord(TypedDict):
    email: str
    password: PasswordRecord
    role: Literal["student", "parent", "provider", "admin"]
    managed_students: tuple[str, ...]


app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

password_iterations = 200_000
bearer_scheme = HTTPBearer(auto_error=False)
sessions: dict[str, str] = {}


def hash_password(password: str, salt: bytes | None = None) -> PasswordRecord:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, password_iterations
    )
    return {
        "salt": base64.b64encode(salt).decode(),
        "digest": base64.b64encode(digest).decode(),
    }


def verify_password(password: str, record: PasswordRecord) -> bool:
    salt = base64.b64decode(record["salt"])
    candidate = hash_password(password, salt)["digest"]
    return hmac.compare_digest(candidate, record["digest"])


def create_user(
    email: str,
    password: str,
    role: Literal["student", "parent", "provider", "admin"],
    managed_students: tuple[str, ...] = (),
) -> UserRecord:
    return {
        "email": email,
        "password": hash_password(password),
        "role": role,
        "managed_students": managed_students,
    }


users = {
    user["email"]: user
    for user in (
        create_user("student@mergington.edu", "learn123", "student"),
        create_user(
            "parent@mergington.edu",
            "family123",
            "parent",
            ("emma@mergington.edu", "sophia@mergington.edu"),
        ),
        create_user("teacher@mergington.edu", "teach123", "provider"),
        create_user("admin@mergington.edu", "admin123", "admin"),
    )
}

activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


class LoginRequest(BaseModel):
    email: str
    password: str


def public_user(user: UserRecord) -> dict[str, str | tuple[str, ...]]:
    return {
        "email": user["email"],
        "role": user["role"],
        "managed_students": user["managed_students"],
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")

    email = sessions.get(credentials.credentials)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return users[email]


def enrollment_email(user: UserRecord, requested_email: str | None) -> str:
    if user["role"] == "student":
        if requested_email is not None and requested_email != user["email"]:
            raise HTTPException(
                status_code=403, detail="Students can manage only their own enrollments"
            )
        return user["email"]

    if user["role"] == "parent":
        if requested_email not in user["managed_students"]:
            raise HTTPException(
                status_code=403, detail="Parents can manage only their linked students"
            )
        return str(requested_email)

    if requested_email is None:
        raise HTTPException(
            status_code=400, detail="A student email is required for staff actions"
        )
    return requested_email


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def login(login_request: LoginRequest):
    email = login_request.email.strip().lower()
    user = users.get(email)
    if user is None or not verify_password(login_request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = email
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@app.post("/auth/logout", status_code=204)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    current_user: UserRecord = Depends(get_current_user),
):
    del current_user
    assert credentials is not None
    sessions.pop(credentials.credentials, None)
    return Response(status_code=204)


@app.get("/auth/me")
def get_authenticated_user(current_user: UserRecord = Depends(get_current_user)):
    return public_user(current_user)


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str | None = None,
    current_user: UserRecord = Depends(get_current_user),
):
    """Sign up an authorized student for an activity."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    authorized_email = enrollment_email(current_user, email)
    activity = activities[activity_name]
    if authorized_email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    activity["participants"].append(authorized_email)
    return {"message": f"Signed up {authorized_email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str | None = None,
    current_user: UserRecord = Depends(get_current_user),
):
    """Unregister an authorized student from an activity."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    authorized_email = enrollment_email(current_user, email)
    activity = activities[activity_name]
    if authorized_email not in activity["participants"]:
        raise HTTPException(
            status_code=400, detail="Student is not signed up for this activity"
        )

    activity["participants"].remove(authorized_email)
    return {"message": f"Unregistered {authorized_email} from {activity_name}"}