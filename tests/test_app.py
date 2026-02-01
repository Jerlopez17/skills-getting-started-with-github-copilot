"""Tests for the Mergington High School Activities API"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def clean_activities():
    """Store original activities and restore after each test"""
    original_activities = {}
    for activity_name, activity_data in activities.items():
        original_activities[activity_name] = {
            "description": activity_data["description"],
            "schedule": activity_data["schedule"],
            "max_participants": activity_data["max_participants"],
            "participants": activity_data["participants"].copy()
        }
    yield
    # Restore original activities after test
    for activity_name, activity_data in original_activities.items():
        activities[activity_name]["participants"] = activity_data["participants"]


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client, clean_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_duplicate_participant(self, client, clean_activities):
        """Test that duplicate signups are rejected"""
        email = "michael@mergington.edu"
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_signup_adds_to_participants_list(self, client, clean_activities):
        """Test that signup actually adds participant to the list"""
        activity_name = "Programming Class"
        email = "newprogrammer@mergington.edu"
        original_count = len(activities[activity_name]["participants"])
        
        response = client.post(
            f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}"
        )
        
        assert response.status_code == 200
        assert len(activities[activity_name]["participants"]) == original_count + 1


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client, clean_activities):
        """Test unregistering an existing participant"""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        
        response = client.delete(
            f"/activities/{activity_name.replace(' ', '%20')}/unregister?email={email}"
        )
        
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        assert email not in activities[activity_name]["participants"]

    def test_unregister_nonexistent_participant(self, client, clean_activities):
        """Test unregistering a participant who isn't registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]

    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_unregister_removes_from_participants_list(self, client, clean_activities):
        """Test that unregister actually removes participant from the list"""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        original_count = len(activities[activity_name]["participants"])
        
        response = client.delete(
            f"/activities/{activity_name.replace(' ', '%20')}/unregister?email={email}"
        )
        
        assert response.status_code == 200
        assert len(activities[activity_name]["participants"]) == original_count - 1


class TestRootEndpoint:
    """Tests for the root / endpoint"""

    def test_root_redirect(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestIntegration:
    """Integration tests"""

    def test_signup_then_unregister(self, client, clean_activities):
        """Test signing up and then unregistering"""
        activity_name = "Tennis Club"
        email = "tennis_player@mergington.edu"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        assert email in activities[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        assert email not in activities[activity_name]["participants"]

    def test_multiple_signups(self, client, clean_activities):
        """Test multiple participants signing up for the same activity"""
        activity_name = "Art Studio"
        emails = ["artist1@mergington.edu", "artist2@mergington.edu", "artist3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}"
            )
            assert response.status_code == 200
        
        for email in emails:
            assert email in activities[activity_name]["participants"]
