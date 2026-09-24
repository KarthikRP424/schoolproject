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

    # ─────────────────────────────────────────────────────────────────────────
    # 5. PHASE 2 FEATURE CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    def test_workflow_transitions(self):
        """
        Verifies workflow state transition validation rules.
        """
        from services.issue_service import is_valid_transition
        self.assertTrue(is_valid_transition("REPORTED", "VERIFIED"))
        self.assertFalse(is_valid_transition("REPORTED", "CLOSED"))
        self.assertTrue(is_valid_transition("ACTION_COMPLETED", "STUDENT_VERIFICATION"))
        self.assertTrue(is_valid_transition("STUDENT_VERIFICATION", "CLOSED"))
        self.assertTrue(is_valid_transition("CLOSED", "REOPENED"))
        self.assertFalse(is_valid_transition("MERGED", "VERIFIED"))

    def test_sla_escalation(self):
        """
        Verifies SLA calculation and escalation cascade.
        """
        from services.sla_service import check_and_escalate_sla, get_sla_status_for_issue
        
        # Test SLA calculation for issue
        issue = execute_query("SELECT * FROM issues LIMIT 1;", fetch="one")
        sla_info = get_sla_status_for_issue(issue)
        self.assertIn("status", sla_info)
        self.assertIn("label", sla_info)

        # Test SLA escalation runner
        res = check_and_escalate_sla()
        self.assertIn("total_breached", res)
        self.assertIn("escalated", res)

    def test_student_consensus_voting(self):
        """
        Verifies 3/5 student representative consensus voting rules.
        """
        from services.inspection_service import submit_student_consensus
        
        school = execute_query("SELECT id FROM schools LIMIT 1;", fetch="one")
        school_id = school["id"]
        
        # Create issue and transition to STUDENT_VERIFICATION
        issue_res = create_issue(
            school_id=school_id,
            reporter_id=1,
            reporter_role="Headmaster",
            description="Fix tap water pipeline.",
            has_photo=False,
            has_gps=False
        )
        issue_id = issue_res["id"]
        execute_query("UPDATE issues SET status = 'STUDENT_VERIFICATION' WHERE id = ?;", (issue_id,))

        # Fetch student reps for this school
        student_reps = execute_query("SELECT id FROM users WHERE school_id = ? AND role = 'Student Representative' LIMIT 3;", (school_id,))
        self.assertGreaterEqual(len(student_reps), 3)

        # Vote 1 (Approve) -> Pending
        res1 = submit_student_consensus(issue_id, student_reps[0]["id"], approves=True)
        self.assertEqual(res1["action"], "PENDING")

        # Vote 2 (Approve) -> Pending
        res2 = submit_student_consensus(issue_id, student_reps[1]["id"], approves=True)
        self.assertEqual(res2["action"], "PENDING")

        # Vote 3 (Approve) -> 3/5 Majority reached -> CLOSED
        res3 = submit_student_consensus(issue_id, student_reps[2]["id"], approves=True)
        self.assertEqual(res3["action"], "CLOSED")
        
        # Check DB state
        updated_issue = execute_query("SELECT status FROM issues WHERE id = ?;", (issue_id,), fetch="one")
        self.assertEqual(updated_issue["status"], "CLOSED")

    def test_duplicate_merging(self):
        """
        Verifies merging duplicate issues.
        """
        from services.issue_service import merge_duplicate_issues
        
        school = execute_query("SELECT id FROM schools LIMIT 1;", fetch="one")
        school_id = school["id"]
        
        master = create_issue(school_id, 1, "Headmaster", "Broken toilet door in block A", False, False)
        dup = create_issue(school_id, 2, "Student Representative", "Broken toilet door in block A", False, False)
        
        user_profile = {"id": 1, "role": "System Administrator", "district": "Shivamogga"}
        success = merge_duplicate_issues(dup["id"], master["id"], user_profile)
        self.assertTrue(success)

        dup_issue = execute_query("SELECT status, parent_issue_id FROM issues WHERE id = ?;", (dup["id"],), fetch="one")
        self.assertEqual(dup_issue["status"], "MERGED")
        self.assertEqual(dup_issue["parent_issue_id"], master["id"])

if __name__ == "__main__":
    unittest.main()

