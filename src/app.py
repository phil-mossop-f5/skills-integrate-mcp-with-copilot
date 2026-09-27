"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import Literal, Optional

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SCHOOL_EMAIL_DOMAIN = os.getenv("SCHOOL_EMAIL_DOMAIN", "mergington.edu").lower()
REGISTRATION_INVITE_CODE = os.getenv("REGISTRATION_INVITE_CODE")
SESSION_DURATION = timedelta(hours=1)
PASSWORD_HASH_OPTIONS = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
bearer_scheme = HTTPBearer(auto_error=False)
users = {}
sessions = {}


class RegistrationRequest(BaseModel):
    email: str
    name: str = Field(min_length=1, max_length=100)
    grade: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(min_length=12, max_length=128)
    invite_code: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    grade: Optional[str] = Field(default=None, max_length=30)


class RoleUpdate(BaseModel):
    role: Literal["student", "activity_manager", "administrator"]


def normalize_school_email(email: str) -> str:
    normalized_email = email.strip().lower()
    local_part, separator, domain = normalized_email.partition("@")
    if (not separator or not local_part or "@" in domain
            or domain != SCHOOL_EMAIL_DOMAIN
            or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+", local_part)):
        raise HTTPException(
            status_code=400,
            detail=f"Use a valid email address at {SCHOOL_EMAIL_DOMAIN}",
        )
    return normalized_email


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                                   **PASSWORD_HASH_OPTIONS)
    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, expected_hash = stored_hash.split(":", 1)
    actual_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        **PASSWORD_HASH_OPTIONS,
    ).hex()
    return hmac.compare_digest(actual_hash, expected_hash)


def public_profile(user: dict) -> dict:
    return {key: user[key] for key in ("email", "name", "grade", "role")}


def issue_session(email: str) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + SESSION_DURATION
    sessions[token] = {"email": email, "expires_at": expires_at}
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(SESSION_DURATION.total_seconds()),
    }


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    session = sessions.get(credentials.credentials) if credentials else None
    now = datetime.now(timezone.utc)
    if not session or session["expires_at"] <= now:
        if credentials:
            sessions.pop(credentials.credentials, None)
        raise HTTPException(
            status_code=401,
            detail="Sign in is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = users.get(session["email"])
    if not user:
        raise HTTPException(status_code=401, detail="Sign in is required")
    return user


def require_role(*roles: str):
    def role_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_dependency


admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
admin_password = os.getenv("ADMIN_PASSWORD", "")
if bool(admin_email) != bool(admin_password):
    raise RuntimeError("Set both ADMIN_EMAIL and ADMIN_PASSWORD to bootstrap an administrator")
if admin_email:
    admin_email = normalize_school_email(admin_email)
    if len(admin_password) < 12:
        raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters")
    users[admin_email] = {
        "email": admin_email,
        "name": os.getenv("ADMIN_NAME", "School Administrator"),
        "grade": None,
        "password_hash": hash_password(admin_password),
        "role": "administrator",
    }

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/register", status_code=201)
def register(request: RegistrationRequest):
    if not REGISTRATION_INVITE_CODE:
        raise HTTPException(status_code=503, detail="Account registration is not configured")
    if not hmac.compare_digest(request.invite_code, REGISTRATION_INVITE_CODE):
        raise HTTPException(status_code=403, detail="Invalid registration invitation")

    email = normalize_school_email(request.email)
    if email in users:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    user = {
        "email": email,
        "name": request.name.strip(),
        "grade": request.grade,
        "password_hash": hash_password(request.password),
        "role": "student",
    }
    if not user["name"]:
        raise HTTPException(status_code=400, detail="Name cannot be blank")
    users[email] = user
    return {**issue_session(email), "user": public_profile(user)}


@app.post("/auth/login")
def login(request: LoginRequest):
    email = request.email.strip().lower()
    user = users.get(email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {**issue_session(email), "user": public_profile(user)}


@app.post("/auth/logout")
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    current_user: dict = Depends(get_current_user),
):
    if credentials:
        sessions.pop(credentials.credentials, None)
    return {"message": "Signed out"}


@app.get("/auth/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return public_profile(current_user)


@app.get("/users/{email}")
def get_user_profile(email: str, current_user: dict = Depends(get_current_user)):
    target_email = email.strip().lower()
    if target_email != current_user["email"] and current_user["role"] != "administrator":
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    user = users.get(target_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return public_profile(user)


@app.patch("/users/{email}")
def update_user_profile(
    email: str,
    request: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    target_email = email.strip().lower()
    if target_email != current_user["email"] and current_user["role"] != "administrator":
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    user = users.get(target_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updates = request.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = updates["name"].strip()
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="Name cannot be blank")
    user.update(updates)
    return public_profile(user)


@app.patch("/users/{email}/role")
def update_user_role(
    email: str,
    request: RoleUpdate,
    current_user: dict = Depends(require_role("administrator")),
):
    user = users.get(email.strip().lower())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["role"] = request.role
    return public_profile(user)


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    current_user: dict = Depends(get_current_user),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    email = current_user["email"]
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    target_email = (email or current_user["email"]).strip().lower()
    if (target_email != current_user["email"]
            and current_user["role"] not in ("activity_manager", "administrator")):
        raise HTTPException(status_code=403, detail="You can only unregister yourself")

    # Validate student is signed up
    if target_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(target_email)
    return {"message": f"Unregistered {target_email} from {activity_name}"}
