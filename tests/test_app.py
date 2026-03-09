import pytest
from fastapi.testclient import TestClient
from urllib.parse import quote
from src.app import app

client = TestClient(app)


class TestRootEndpoint:
    """Test the root endpoint redirect"""

    def test_root_redirect(self):
        # Arrange: Create client that doesn't follow redirects
        test_client = TestClient(app, follow_redirects=False)

        # Act: Make GET request to root
        response = test_client.get("/")

        # Assert: Should redirect to static HTML
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test retrieving all activities"""

    def test_get_all_activities(self):
        # Arrange: No special setup needed

        # Act: Make GET request to activities
        response = client.get("/activities")

        # Assert: Should return 200 and contain all activities
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # Should have 9 activities

        # Check structure of one activity
        chess_club = data.get("Chess Club")
        assert chess_club is not None
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_activity_structure(self):
        # Arrange: Get activities data

        # Act: Make GET request
        response = client.get("/activities")
        data = response.json()

        # Assert: Each activity has correct structure and data types
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            assert activity_data["max_participants"] > 0
            # All participants should be strings (emails)
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation


class TestSignupEndpoint:
    """Test student signup for activities"""

    def test_successful_signup(self):
        # Arrange: Choose an activity and new email
        activity = "Programming Class"
        new_email = "test@mergington.edu"

        # Get initial participant count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity]["participants"])

        # Act: Sign up the student
        response = client.post(f"/activities/{activity}/signup?email={new_email}")

        # Assert: Should succeed and add participant
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert new_email in data["message"]
        assert activity in data["message"]

        # Verify participant was added
        final_response = client.get("/activities")
        final_data = final_response.json()
        final_count = len(final_data[activity]["participants"])
        assert final_count == initial_count + 1
        assert new_email in final_data[activity]["participants"]

    def test_duplicate_signup(self):
        # Arrange: Sign up a student first
        activity = "Gym Class"
        email = "duplicate@mergington.edu"
        client.post(f"/activities/{activity}/signup?email={email}")

        # Act: Try to sign up the same student again
        response = client.post(f"/activities/{activity}/signup?email={email}")

        # Assert: Should return 400 with error message
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self):
        # Arrange: Use a non-existent activity name
        fake_activity = "NonExistent Activity"
        email = "test@mergington.edu"

        # Act: Try to sign up for non-existent activity
        response = client.post(f"/activities/{fake_activity}/signup?email={email}")

        # Assert: Should return 404
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestRemoveParticipant:
    """Test removing participants from activities"""

    def test_successful_removal(self):
        # Arrange: Add a participant first, then remove them
        activity = "Tennis Club"
        email = "remove_me@mergington.edu"

        # Add participant
        client.post(f"/activities/{activity}/signup?email={email}")

        # Get initial count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity]["participants"])

        # Act: Remove the participant
        response = client.delete(f"/activities/{activity}/participants/{email}")

        # Assert: Should succeed and remove participant
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]

        # Verify participant was removed
        final_response = client.get("/activities")
        final_data = final_response.json()
        final_count = len(final_data[activity]["participants"])
        assert final_count == initial_count - 1
        assert email not in final_data[activity]["participants"]

    def test_remove_nonexistent_participant(self):
        # Arrange: Try to remove a participant who isn't signed up
        activity = "Art Studio"
        fake_email = "not_signed_up@mergington.edu"

        # Act: Try to remove non-existent participant
        response = client.delete(f"/activities/{activity}/participants/{fake_email}")

        # Assert: Should return 400
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_remove_from_nonexistent_activity(self):
        # Arrange: Use a non-existent activity
        fake_activity = "Fake Activity"
        email = "test@mergington.edu"

        # Act: Try to remove from non-existent activity
        response = client.delete(f"/activities/{fake_activity}/participants/{email}")

        # Assert: Should return 404
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_signup_with_special_characters(self):
        # Arrange: Use email with special characters
        activity = "Music Band"
        email = "test.user+tag@mergington.edu"
        encoded_email = quote(email)  # URL encode the email

        # Act: Sign up with special email
        response = client.post(f"/activities/{activity}/signup?email={encoded_email}")

        # Assert: Should succeed (backend doesn't validate email format)
        assert response.status_code == 200
        data = response.json()
        assert email in data["message"]  # Check for original email, not encoded

        # Verify in activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]

    def test_activity_name_with_spaces(self):
        # Arrange: Activity name with spaces (already tested, but confirm)
        activity = "Basketball Team"  # Has spaces
        email = "spaces_test@mergington.edu"

        # Act: Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")

        # Assert: Should work with URL encoding
        assert response.status_code == 200

    def test_case_sensitive_activity_names(self):
        # Arrange: Try different case for activity name
        activity_lower = "chess club"  # lowercase
        email = "case_test@mergington.edu"

        # Act: Try to sign up with different case
        response = client.post(f"/activities/{activity_lower}/signup?email={email}")

        # Assert: Should return 404 (activity names are case-sensitive)
        assert response.status_code == 404