"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_state = {
        name: {"participants": details["participants"].copy(), **{k: v for k, v in details.items() if k != "participants"}}
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_state.items():
        activities[name]["participants"] = details["participants"].copy()


def test_root_redirect(client):
    """Test root endpoint redirects to static index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test getting all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert isinstance(data, dict)
    assert "Soccer Team" in data
    assert "Basketball Club" in data
    assert "Drama Club" in data
    
    # Verify activity details
    soccer = data["Soccer Team"]
    assert "description" in soccer
    assert "schedule" in soccer
    assert "max_participants" in soccer
    assert "participants" in soccer
    assert isinstance(soccer["participants"], list)


def test_signup_for_activity_success(client):
    """Test successful signup for an activity"""
    test_email = "test@mergington.edu"
    activity_name = "Soccer Team"
    
    # Get initial participant count
    initial_response = client.get("/activities")
    initial_count = len(initial_response.json()[activity_name]["participants"])
    
    # Sign up
    response = client.post(
        f"/activities/{activity_name}/signup?email={test_email}"
    )
    assert response.status_code == 200
    assert test_email in response.json()["message"]
    
    # Verify participant was added
    updated_response = client.get("/activities")
    updated_participants = updated_response.json()[activity_name]["participants"]
    assert test_email in updated_participants
    assert len(updated_participants) == initial_count + 1


def test_signup_duplicate_participant(client):
    """Test signing up a participant who is already registered"""
    test_email = "test@mergington.edu"
    activity_name = "Soccer Team"
    
    # First signup
    response1 = client.post(
        f"/activities/{activity_name}/signup?email={test_email}"
    )
    assert response1.status_code == 200
    
    # Second signup (should fail)
    response2 = client.post(
        f"/activities/{activity_name}/signup?email={test_email}"
    )
    assert response2.status_code == 400
    assert "already signed up" in response2.json()["detail"].lower()


def test_signup_nonexistent_activity(client):
    """Test signing up for an activity that doesn't exist"""
    response = client.post(
        "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_unregister_from_activity_success(client):
    """Test successful unregistration from an activity"""
    test_email = "test@mergington.edu"
    activity_name = "Soccer Team"
    
    # First sign up
    client.post(f"/activities/{activity_name}/signup?email={test_email}")
    
    # Get participant count after signup
    response = client.get("/activities")
    count_after_signup = len(response.json()[activity_name]["participants"])
    
    # Unregister
    response = client.delete(
        f"/activities/{activity_name}/unregister?email={test_email}"
    )
    assert response.status_code == 200
    assert "Unregistered" in response.json()["message"]
    assert test_email in response.json()["message"]
    
    # Verify participant was removed
    updated_response = client.get("/activities")
    updated_participants = updated_response.json()[activity_name]["participants"]
    assert test_email not in updated_participants
    assert len(updated_participants) == count_after_signup - 1


def test_unregister_not_registered_participant(client):
    """Test unregistering a participant who is not registered"""
    response = client.delete(
        "/activities/Soccer Team/unregister?email=notregistered@mergington.edu"
    )
    assert response.status_code == 400
    assert "not registered" in response.json()["detail"].lower()


def test_unregister_nonexistent_activity(client):
    """Test unregistering from an activity that doesn't exist"""
    response = client.delete(
        "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_unregister_existing_participant(client):
    """Test unregistering an existing participant"""
    activity_name = "Soccer Team"
    
    # Get initial state
    initial_response = client.get("/activities")
    initial_participants = initial_response.json()[activity_name]["participants"]
    
    # Ensure there's at least one participant
    assert len(initial_participants) > 0
    
    # Unregister the first participant
    email_to_remove = initial_participants[0]
    response = client.delete(
        f"/activities/{activity_name}/unregister?email={email_to_remove}"
    )
    assert response.status_code == 200
    
    # Verify removal
    updated_response = client.get("/activities")
    updated_participants = updated_response.json()[activity_name]["participants"]
    assert email_to_remove not in updated_participants
    assert len(updated_participants) == len(initial_participants) - 1


def test_activity_data_structure(client):
    """Test that all activities have the required data structure"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    
    required_fields = ["description", "schedule", "max_participants", "participants"]
    
    for activity_name, activity_data in data.items():
        for field in required_fields:
            assert field in activity_data, f"{activity_name} missing {field}"
        
        assert isinstance(activity_data["description"], str)
        assert isinstance(activity_data["schedule"], str)
        assert isinstance(activity_data["max_participants"], int)
        assert isinstance(activity_data["participants"], list)
        assert activity_data["max_participants"] > 0


def test_multiple_signups_different_activities(client):
    """Test that a student can sign up for multiple different activities"""
    test_email = "multisport@mergington.edu"
    
    # Sign up for Soccer
    response1 = client.post(
        f"/activities/Soccer Team/signup?email={test_email}"
    )
    assert response1.status_code == 200
    
    # Sign up for Basketball
    response2 = client.post(
        f"/activities/Basketball Club/signup?email={test_email}"
    )
    assert response2.status_code == 200
    
    # Verify both registrations
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert test_email in activities_data["Soccer Team"]["participants"]
    assert test_email in activities_data["Basketball Club"]["participants"]
