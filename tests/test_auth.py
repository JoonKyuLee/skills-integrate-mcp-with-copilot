from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app, sessions, users


@pytest.fixture(autouse=True)
def restore_application_state():
    original_activities = deepcopy(activities)
    sessions.clear()
    yield
    activities.clear()
    activities.update(original_activities)
    sessions.clear()


@pytest.fixture
def client():
    return TestClient(app)


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_passwords_are_hashed():
    for user in users.values():
        assert set(user["password"]) == {"salt", "digest"}


def test_public_can_browse_activities(client: TestClient):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()


def test_invalid_password_is_rejected(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "student@mergington.edu", "password": "incorrect"},
    )

    assert response.status_code == 401


def test_enrollment_requires_authentication(client: TestClient):
    response = client.post("/activities/Chess Club/signup")

    assert response.status_code == 401


def test_student_can_manage_only_own_enrollment(client: TestClient):
    headers = login(client, "student@mergington.edu", "learn123")

    own_response = client.post("/activities/Chess Club/signup", headers=headers)
    other_response = client.delete(
        "/activities/Chess Club/unregister",
        params={"email": "michael@mergington.edu"},
        headers=headers,
    )

    assert own_response.status_code == 200
    assert "student@mergington.edu" in activities["Chess Club"]["participants"]
    assert other_response.status_code == 403
    assert "michael@mergington.edu" in activities["Chess Club"]["participants"]


def test_parent_can_manage_only_linked_students(client: TestClient):
    headers = login(client, "parent@mergington.edu", "family123")

    linked_response = client.delete(
        "/activities/Programming Class/unregister",
        params={"email": "emma@mergington.edu"},
        headers=headers,
    )
    unrelated_response = client.delete(
        "/activities/Chess Club/unregister",
        params={"email": "michael@mergington.edu"},
        headers=headers,
    )

    assert linked_response.status_code == 200
    assert unrelated_response.status_code == 403


def test_administrator_can_manage_any_enrollment(client: TestClient):
    headers = login(client, "admin@mergington.edu", "admin123")

    response = client.delete(
        "/activities/Chess Club/unregister",
        params={"email": "michael@mergington.edu"},
        headers=headers,
    )

    assert response.status_code == 200
    assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


def test_logout_invalidates_session(client: TestClient):
    headers = login(client, "student@mergington.edu", "learn123")

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401