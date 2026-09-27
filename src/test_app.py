import os
import unittest

os.environ["REGISTRATION_INVITE_CODE"] = "test-invite-code"
os.environ["SCHOOL_EMAIL_DOMAIN"] = "mergington.edu"

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app import LoginRequest, ProfileUpdate, RegistrationRequest, RoleUpdate

import app as app_module


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        app_module.users.clear()
        app_module.sessions.clear()
        self.original_participants = list(app_module.activities["Chess Club"]["participants"])

    def tearDown(self):
        app_module.activities["Chess Club"]["participants"] = self.original_participants

    def register(self, email="student@mergington.edu", invite_code="test-invite-code"):
        return app_module.register(RegistrationRequest(
            email=email,
            name="Test Student",
            grade="11",
            password="a-strong-password-123",
            invite_code=invite_code,
        ))

    def test_registration_requires_invitation_and_hashes_password(self):
        with self.assertRaises(HTTPException) as rejected:
            self.register(invite_code="wrong-code")
        self.assertEqual(rejected.exception.status_code, 403)

        accepted = self.register()
        self.assertEqual(accepted["user"]["role"], "student")
        self.assertNotIn("password_hash", accepted["user"])
        self.assertNotEqual(
            app_module.users["student@mergington.edu"]["password_hash"],
            "a-strong-password-123",
        )

    def test_login_and_profile_access_are_scoped_to_authenticated_user(self):
        self.register()
        self.register("other@mergington.edu")
        login = app_module.login(LoginRequest(
            email="student@mergington.edu",
            password="a-strong-password-123",
        ))
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=login["access_token"]
        )
        current_user = app_module.get_current_user(credentials)

        self.assertEqual(app_module.get_my_profile(current_user)["email"],
                         "student@mergington.edu")
        with self.assertRaises(HTTPException) as denied:
            app_module.get_user_profile("other@mergington.edu", current_user)
        self.assertEqual(denied.exception.status_code, 403)

        updated = app_module.update_user_profile(
            "student@mergington.edu",
            ProfileUpdate(name="Updated Student"),
            current_user,
        )
        self.assertEqual(updated["name"], "Updated Student")

    def test_activity_changes_require_auth_and_use_authenticated_identity(self):
        with self.assertRaises(HTTPException) as denied:
            app_module.get_current_user(None)
        self.assertEqual(denied.exception.status_code, 401)

        registered = self.register()
        student = app_module.users["student@mergington.edu"]
        response = app_module.signup_for_activity("Chess Club", student)
        self.assertIn("student@mergington.edu", response["message"])
        participants = app_module.activities["Chess Club"]["participants"]
        self.assertIn("student@mergington.edu", participants)
        self.assertNotIn("other@mergington.edu", participants)

        with self.assertRaises(HTTPException) as remove_other:
            app_module.unregister_from_activity(
                "Chess Club", "michael@mergington.edu", student
            )
        self.assertEqual(remove_other.exception.status_code, 403)
        self.assertTrue(registered["access_token"])

    def test_only_administrators_can_assign_roles_or_view_other_profiles(self):
        self.register()
        app_module.users["admin@mergington.edu"] = {
            "email": "admin@mergington.edu",
            "name": "Administrator",
            "grade": None,
            "password_hash": app_module.hash_password("admin-password-123"),
            "role": "administrator",
        }
        student = app_module.users["student@mergington.edu"]
        admin = app_module.users["admin@mergington.edu"]
        role_dependency = app_module.require_role("administrator")
        with self.assertRaises(HTTPException) as denied:
            role_dependency(student)
        self.assertEqual(denied.exception.status_code, 403)

        role_update = app_module.update_user_role(
            "student@mergington.edu",
            RoleUpdate(role="activity_manager"),
            admin,
        )
        self.assertEqual(role_update["role"], "activity_manager")
        self.assertEqual(
            app_module.get_user_profile("student@mergington.edu", admin)["role"],
            "activity_manager",
        )


if __name__ == "__main__":
    unittest.main()