"""
tests/test_flow.py
------------------
Automated test suite verifying the database setup, security systems, and prioritizing logic.
Can be executed via standard python CLI execution.
"""
import unittest
import os
import sys
import json

# Setup import path context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
# Explicitly force a separate test database to protect production/demo files
config.SQLITE_DB_PATH = "test_school_monitoring.db"

from database.models import initialize_database
from database.connection import execute_query, get_db_connection
from database.seed import seed_demo_data
from auth.authentication import hash_password, verify_password, authenticate_user, reset_user_password
from services.priority_engine import calculate_school_health, calculate_school_priority, calculate_school_decline_risk
from services.verification_service import submit_verification, recalculate_verification_confidence
from services.issue_service import create_issue, update_issue_status

class TestSchoolMonitoringSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """
        Runs once before any tests to initialize database and seed structure.
        """
        # Ensure test DB is fresh
        if os.path.exists(config.SQLITE_DB_PATH):
            os.remove(config.SQLITE_DB_PATH)
            
        initialize_database()
        seed_demo_data()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up test database file.
        """
        if os.path.exists(config.SQLITE_DB_PATH):
            os.remove(config.SQLITE_DB_PATH)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. DATABASE & SEED CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    def test_database_initialization(self):
        """
        Checks if the required tables are generated inside the DB file.
        """
        res = execute_query("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r["name"] for r in res]
        self.assertIn("schools", tables)
        self.assertIn("users", tables)
        self.assertIn("issues", tables)
        self.assertIn("issue_evidence", tables)
        self.assertIn("issue_verifications", tables)
        self.assertIn("student_feedback", tables)
        self.assertIn("inspections", tables)
        self.assertIn("audit_logs", tables)
        self.assertIn("notifications", tables)

    def test_seeded_counts(self):
        """
        Checks if the seeding successfully generated schools and users.
        """
        schools_count = execute_query("SELECT COUNT(*) as count FROM schools;", fetch="one")["count"]
        users_count = execute_query("SELECT COUNT(*) as count FROM users;", fetch="one")["count"]
        issues_count = execute_query("SELECT COUNT(*) as count FROM issues;", fetch="one")["count"]
        
        self.assertGreater(schools_count, 15)
        self.assertGreater(users_count, 5)
        self.assertGreater(issues_count, 3)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. SECURITY & AUTHENTICATION CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    def test_password_hashing_verification(self):
        """
        Checks if PBKDF2-HMAC-SHA256 password hashing works as designed.
        """
        pwd = "SecurityPassword123!"
        h, salt = hash_password(pwd)
        
        # Verify correct verification matching
        self.assertTrue(verify_password(pwd, h, salt))
        # Verify incorrect password returns false
        self.assertFalse(verify_password("wrong_password", h, salt))

    def test_user_authentication(self):
        """
        Checks authenticating pre-seeded accounts.
        """
        user = authenticate_user("headmaster_rampura", "Head@123")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "headmaster_rampura")
        self.assertEqual(user["role"], "Headmaster")
        
        invalid_user = authenticate_user("headmaster_rampura", "WrongPass")
        self.assertIsNone(invalid_user)

    def test_password_reset(self):
        """
        Checks the password reset flow.
        """
        username = "student_rampura"
        
        # Reset password
        reset_res = reset_user_password(username, "NewStudentPass123")
        self.assertTrue(reset_res)
        
        # Verify new password login
        auth_new = authenticate_user(username, "NewStudentPass123")
        self.assertIsNotNone(auth_new)
        
        # Verify old password fails
        auth_old = authenticate_user(username, "Stu@123")
        self.assertIsNone(auth_old)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. PRIORITY & HEALTH ENGINE CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    def test_school_priority_scoring(self):
        """
        Verifies priority evaluation logic.
        """
        school = execute_query("SELECT id FROM schools WHERE name = 'Government High School, Sagar';", fetch="one")
        school_id = school["id"]
        
        priority = calculate_school_priority(school_id)
        self.assertIn("score", priority)
        self.assertIn("level", priority)
        self.assertIn("breakdown", priority)
        
        # High School Sagar has pre-seeded teacher shortage and high issues, should be Critical or High
        self.assertIn(priority["level"], ["HIGH", "CRITICAL", "EMERGENCY"])

    def test_school_decline_risk(self):
        """
        Checks early warning decline risk evaluation.
        """
        school = execute_query("SELECT id FROM schools WHERE name = 'Government High School, Sagar';", fetch="one")
        school_id = school["id"]
        
        risk = calculate_school_decline_risk(school_id)
        self.assertGreater(risk["percentage"], 35.0)  # Sagar has strong enrollment decline (~40%)
        self.assertIn(risk["risk_level"], ["Moderate", "High"])  # Moderate risk is correct for ~40%

    # ─────────────────────────────────────────────────────────────────────────
    # 4. BUSINESS LOGIC & WORKFLOW CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    def test_verification_confidence_loop(self):
        """
        Verifies verification scoring and conflict flagging logic.
        """
        # Create a mock issue on schools
        school = execute_query("SELECT id FROM schools LIMIT 1;", fetch="one")
        school_id = school["id"]
        hm = execute_query("SELECT id, role FROM users WHERE role = 'Headmaster' LIMIT 1;", fetch="one")
        stu = execute_query("SELECT id, role FROM users WHERE role = 'Student Representative' LIMIT 1;", fetch="one")
        
        issue_res = create_issue(
            school_id=school_id,
            reporter_id=hm["id"],
            reporter_role=hm["role"],
            description="Mock electricity failure in class.",
            has_photo=True,
            has_gps=False,
            photo_name="electric_defect.jpg"
        )
        issue_id = issue_res["id"]
        
        # Test baseline confidence recalculation
        confidence, v_status, conflict = recalculate_verification_confidence(issue_id)
        self.assertEqual(confidence, 10.0) # Photo evidence weight (0.2 * 50% = 10.0)
        self.assertEqual(v_status, "Low Confidence")
        self.assertFalse(conflict)
        
        # Submit Headmaster verification (Confirms) -> Weight 30% * 100 = 30. Total = 40.
        c, s, conf = submit_verification(issue_id, hm["id"], hm["role"], confirms_issue=True)
        self.assertEqual(c, 40.0)
        self.assertEqual(s, "Review Required")
        self.assertFalse(conf)
        
        # Submit Student Representative verification (Denies -> Conflict!)
        c, s, conf = submit_verification(issue_id, stu["id"], stu["role"], confirms_issue=False)
        self.assertTrue(conf)
        # Confirms: HM (30), Denies: Stu (0), Photo: 10. Total confirmation = 40. Penalty: -30. Total confidence = 10.
        self.assertEqual(c, 10.0)
        self.assertEqual(s, "Review Required")

if __name__ == "__main__":
    unittest.main()
