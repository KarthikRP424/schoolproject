"""
database/seed.py
----------------
Populates the database with realistic synthetic Karnataka school system data.
Implements secure PBKDF2 hashing for accounts and pre-configures demo scenarios (A to H).
"""
import json
import hashlib
import os
import sqlite3
from database.connection import get_db_connection

def hash_password(password: str) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Returns: (password_hash_hex, salt_hex)
    """
    salt = os.urandom(16)
    pwd_bytes = password.encode('utf-8')
    h = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt, 100000)
    return h.hex(), salt.hex()

def seed_demo_data():
    """
    Seeds the SQLite database with schools, users, issues, and audit records.
    Safe to execute multiple times (idempotent checking).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if already seeded
        cursor.execute("SELECT value FROM system_meta WHERE key = 'demo_seed_version';")
        row = cursor.fetchone()
        if row and row['value'] == '1':
            return # Already seeded

        # Clear existing tables just in case we are running a fresh reset
        cursor.execute("DELETE FROM system_meta;")
        cursor.execute("DELETE FROM audit_logs;")
        cursor.execute("DELETE FROM notifications;")
        cursor.execute("DELETE FROM inspections;")
        cursor.execute("DELETE FROM student_feedback;")
        cursor.execute("DELETE FROM issue_verifications;")
        cursor.execute("DELETE FROM issue_evidence;")
        cursor.execute("DELETE FROM issues;")
        cursor.execute("DELETE FROM users;")
        cursor.execute("DELETE FROM historical_scores;")
        cursor.execute("DELETE FROM attendance_records;")
        cursor.execute("DELETE FROM enrollment_records;")
        cursor.execute("DELETE FROM schools;")

        # ─────────────────────────────────────────────────────────────────────
        # SEED 1: SCHOOLS (20 Synthetic Karnataka Schools)
        # ─────────────────────────────────────────────────────────────────────
        # Geography: Shivamogga, Chikkamagaluru, Hassan
        schools_data = [
            # Shivamogga - Bhadravathi
            ("Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura", 13.8415, 75.7022, "Primary", 140, 4, 6, 4, 88.5, 76.5, 52.0, 35.0, "MEDIUM"),
            ("Government High School, Bhadravathi Town", "Shivamogga", "Bhadravathi", "Bhadravathi", 13.8400, 75.7011, "High School", 280, 8, 10, 8, 91.0, 82.0, 41.0, 22.0, "MODERATE"),
            ("Government Lower Primary School, Holehonnur", "Shivamogga", "Bhadravathi", "Holehonnur", 13.9212, 75.6980, "Primary", 65, 2, 3, 2, 85.0, 68.0, 45.0, 40.0, "MODERATE"),
            
            # Shivamogga - Sagar
            ("Government High School, Sagar", "Shivamogga", "Sagar", "Sagar", 14.1672, 75.0234, "High School", 310, 7, 12, 7, 72.0, 58.0, 74.0, 68.0, "CRITICAL"),
            ("Government Primary School, Anandapura", "Shivamogga", "Sagar", "Anandapura", 14.0722, 75.1233, "Primary", 110, 3, 4, 3, 89.0, 78.0, 35.0, 18.0, "LOW"),
            ("Government Primary School, Keladi", "Shivamogga", "Sagar", "Keladi", 14.2180, 75.0125, "Primary", 85, 2, 3, 2, 86.5, 71.0, 42.0, 28.0, "MODERATE"),
            
            # Shivamogga - Soraba
            ("Government School, Anavatti", "Shivamogga", "Soraba", "Anavatti", 14.4532, 75.1322, "High School", 185, 5, 8, 5, 84.0, 70.0, 55.0, 44.0, "HIGH"),
            ("Government Primary School, Soraba Rural", "Shivamogga", "Soraba", "Soraba Rural", 14.3800, 75.0900, "Primary", 95, 3, 4, 3, 90.0, 82.0, 30.0, 12.0, "LOW"),
            
            # Chikkamagaluru - Koppa
            ("Zilla Panchayat School, Koppa", "Chikkamagaluru", "Koppa", "Koppa", 13.5312, 75.3589, "High School", 220, 6, 9, 6, 89.5, 80.0, 48.0, 26.0, "MODERATE"),
            ("Government School, Hariharapura", "Chikkamagaluru", "Koppa", "Hariharapura", 13.5122, 75.2901, "Primary", 125, 4, 5, 4, 91.5, 84.0, 38.0, 15.0, "LOW"),
            
            # Chikkamagaluru - Mudigere
            ("Government High School, Mudigere", "Chikkamagaluru", "Mudigere", "Mudigere", 13.1368, 75.6372, "High School", 240, 5, 10, 5, 65.0, 49.0, 81.0, 82.0, "EMERGENCY"),
            ("Zilla Panchayat Primary School, Kalasa", "Chikkamagaluru", "Mudigere", "Kalasa", 13.2312, 75.3611, "Primary", 90, 2, 4, 2, 83.0, 65.0, 60.0, 55.0, "HIGH"),
            
            # Chikkamagaluru - Tarikere
            ("Government Primary School, Tarikere", "Chikkamagaluru", "Tarikere", "Tarikere", 13.7122, 75.8111, "Primary", 160, 5, 7, 5, 92.0, 86.0, 35.0, 10.0, "LOW"),
            ("Government High School, Ajjampura", "Chikkamagaluru", "Tarikere", "Ajjampura", 13.7299, 75.9877, "High School", 195, 6, 8, 6, 88.0, 79.0, 45.0, 24.0, "MODERATE"),
            
            # Hassan - Belur
            ("Government Middle School, Belur", "Hassan", "Belur", "Belur", 13.1624, 75.8598, "Primary", 135, 3, 6, 3, 81.0, 60.0, 68.0, 61.0, "HIGH"),
            ("Government High School, Halebidu", "Hassan", "Belur", "Halebidu", 13.2120, 75.9922, "High School", 205, 5, 8, 5, 87.0, 75.0, 50.0, 34.0, "MODERATE"),
            
            # Hassan - Arsikere
            ("Zilla Panchayat High School, Arsikere", "Hassan", "Arsikere", "Arsikere", 13.3129, 76.2567, "High School", 250, 6, 9, 6, 89.0, 81.0, 44.0, 23.0, "MODERATE"),
            ("Government Primary School, Banavara", "Hassan", "Arsikere", "Banavara", 13.4122, 76.1672, "Primary", 115, 3, 4, 3, 90.0, 83.0, 36.0, 14.0, "LOW"),
            
            # Hassan - Sakleshpur
            ("Government High School, Sakleshpur", "Hassan", "Sakleshpur", "Sakleshpur", 12.9431, 75.7854, "High School", 175, 4, 8, 4, 78.0, 62.0, 71.0, 64.0, "HIGH"),
            ("Government Primary School, Yeslur", "Hassan", "Sakleshpur", "Yeslur", 12.8122, 75.7122, "Primary", 80, 2, 3, 2, 85.0, 70.0, 48.0, 38.0, "MODERATE")
        ]

        inserted_schools = []
        for school in schools_data:
            # Default facility statuses
            facility_status = {
                "drinking_water": "Available",
                "boys_toilet": "Available",
                "girls_toilet": "Available",
                "electricity": "Available",
                "classrooms": "Available",
                "building_condition": "Available",
                "benches": "Available",
                "desks": "Available",
                "computer_lab": "Partially Available",
                "playground": "Available",
                "library": "Available",
                "internet": "Partially Available",
                "boundary_wall": "Available"
            }
            
            # Customize facilities to reflect scores (Emergency/Critical schools get poor/damaged facilities)
            level = school[15]
            if level in ["CRITICAL", "EMERGENCY"]:
                facility_status["drinking_water"] = "Not Available"
                facility_status["boys_toilet"] = "Damaged"
                facility_status["girls_toilet"] = "Damaged"
                facility_status["building_condition"] = "Damaged"
                facility_status["classrooms"] = "Requires Inspection"
            elif level == "HIGH":
                facility_status["girls_toilet"] = "Damaged"
                facility_status["electricity"] = "Not Available"
                facility_status["boundary_wall"] = "Damaged"
                
            facility_json = json.dumps(facility_status)

            # Generate synthetic enrollment trend
            base_enrollment = school[7]
            trend = {
                "2022": int(base_enrollment * 1.3),
                "2023": int(base_enrollment * 1.2),
                "2024": int(base_enrollment * 1.1),
                "2025": int(base_enrollment * 1.05),
                "2026": base_enrollment
            }
            # For Scenario D (High Decline Risk at Government High School, Sagar)
            if school[0] == "Government High School, Sagar":
                trend = {
                    "2022": 450,
                    "2023": 390,
                    "2024": 350,
                    "2025": 310,
                    "2026": 240
                }
            trend_json = json.dumps(trend)

            # Calculate expanded teacher metrics
            sanctioned = school[9]
            available = school[10]
            absent = 1 if school[0] in ["Government High School, Sagar", "Government High School, Mudigere", "Zilla Panchayat School, Koppa"] else 0
            present = max(0, available - absent)

            cursor.execute(
                """
                INSERT INTO schools (
                    name, district, taluk, village, latitude, longitude, school_type,
                    num_students, num_teachers, required_teachers, available_teachers,
                    sanctioned_teachers, present_teachers, absent_teachers,
                    attendance_pct, health_score, priority_score, decline_risk, priority_level,
                    facility_status_json, enrollment_trend_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    school[0], school[1], school[2], school[3], school[4], school[5], school[6],
                    school[7], school[8], school[9], school[10],
                    sanctioned, present, absent,
                    school[11], school[12], school[13], school[14], school[15], facility_json, trend_json
                )
            )
            school_id = cursor.lastrowid
            inserted_schools.append((school[0], school_id, school[1], school[2], school[3]))

            # Seed enrollment history records
            for year, count in trend.items():
                cursor.execute(
                    "INSERT INTO enrollment_records (school_id, year, num_students) VALUES (?, ?, ?);",
                    (school_id, int(year), count)
                )

            # Seed attendance history records
            months = [("June", school[11]), ("July", school[11]-2.0), ("August", school[11]-4.0), ("September", school[11]-6.0)]
            if school[0] == "Government High School, Sagar":
                # Scenario D: Drastic dropping attendance alert
                months = [("June", 85.0), ("July", 78.0), ("August", 72.0), ("September", 65.0)]
            for month, pct in months:
                cursor.execute(
                    "INSERT INTO attendance_records (school_id, month_name, attendance_pct) VALUES (?, ?, ?);",
                    (school_id, month, pct)
                )

            # Seed historical scores tracker
            histories = [
                ("2026-03-20 12:00:00", school[12]-10, school[13]+10),
                ("2026-06-20 12:00:00", school[12]-5, school[13]+5),
                ("2026-08-20 12:00:00", school[12], school[13])
            ]
            for ts, hs, ps in histories:
                cursor.execute(
                    "INSERT INTO historical_scores (school_id, timestamp, health_score, priority_score) VALUES (?, ?, ?, ?);",
                    (school_id, ts, hs, ps)
                )

        # Map school names to IDs for reference during user and issue seeding
        school_id_map = {name: sid for name, sid, _, _, _ in inserted_schools}

        # ─────────────────────────────────────────────────────────────────────
        # SEED 2: USERS (Demo Login Accounts)
        # ─────────────────────────────────────────────────────────────────────
        # Secure PBKDF2 hash initialization
        users_to_seed = [
            # Headmasters
            ("headmaster_rampura", "Head@123", "Headmaster", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura"),
            ("headmaster_sagar", "Head@456", "Headmaster", "Government High School, Sagar", "Shivamogga", "Sagar", "Sagar"),
            ("headmaster_mudigere", "Head@789", "Headmaster", "Government High School, Mudigere", "Chikkamagaluru", "Mudigere", "Mudigere"),
            
            # Student Representatives
            ("student_rampura", "Stu@123", "Student Representative", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura"),
            ("student_sagar", "Stu@456", "Student Representative", "Government High School, Sagar", "Shivamogga", "Sagar", "Sagar"),
            ("student_mudigere", "Stu@789", "Student Representative", "Government High School, Mudigere", "Chikkamagaluru", "Mudigere", "Mudigere"),
            
            # Village Volunteers
            ("volunteer_rampura", "Vol@123", "Village Volunteer", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura"),
            ("volunteer_sagar", "Vol@456", "Village Volunteer", "Government High School, Sagar", "Shivamogga", "Sagar", "Sagar"),
            
            # Officers
            ("officer_demo_district", "Off@123", "District Education Officer", None, "Shivamogga", None, None),
            ("officer_shivamogga", "Off@123", "District Education Officer", None, "Shivamogga", None, None),
            ("officer_state", "State@123", "State Education Department Official", None, "All", None, None),
            
            # Extra Student Representatives to simulate 5-user feedback consensus
            ("student_rep2", "Stu2@123", "Student Representative", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura"),
            ("student_rep3", "Stu3@123", "Student Representative", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura"),
            ("student_rep4", "Stu4@123", "Student Representative", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura"),
            ("student_rep5", "Stu5@123", "Student Representative", "Government Higher Primary School, Rampura", "Shivamogga", "Bhadravathi", "Rampura")
        ]

        user_id_map = {}
        for username, pwd, role, school_name, dist, tal, vil in users_to_seed:
            pwd_hash, salt = hash_password(pwd)
            sch_id = school_id_map.get(school_name) if school_name else None
            
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, salt, role, school_id, district, taluk, village)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (username, pwd_hash, salt, role, sch_id, dist, tal, vil)
            )
            user_id_map[username] = cursor.lastrowid

        # Dynamically seed 5 unique Student Representatives for every school
        for name, sid, dist, tal, vil in inserted_schools:
            for i in range(1, 6):
                username = f"student_rep_{sid}_{i}"
                pwd = "Stu@123"
                pwd_hash, salt = hash_password(pwd)
                
                cursor.execute("SELECT id FROM users WHERE username = ?;", (username,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO users (username, password_hash, salt, role, school_id, district, taluk, village)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (username, pwd_hash, salt, "Student Representative", sid, dist, tal, vil)
                    )

        # ─────────────────────────────────────────────────────────────────────
        # SEED 3: DEMO SCENARIOS (A to H)
        # ─────────────────────────────────────────────────────────────────────

        # Scenario A: Normal toilet issue -> verified -> resolved -> student approved
        # GHPS Rampura
        rampura_id = school_id_map["Government Higher Primary School, Rampura"]
        hm_rampura = user_id_map["headmaster_rampura"]
        stu_rampura = user_id_map["student_rampura"]
        
        cursor.execute(
            """
            INSERT INTO issues (
                report_id, school_id, reporter_id, reporter_role, category, description,
                submitted_time, latitude, longitude, status, verification_status,
                verification_confidence, dangerous_school_status, assignment, resolution_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "RPT-0001", rampura_id, hm_rampura, "Headmaster", "Sanitation",
                "The student boys toilet drainage is blocked and requires plumber repair.",
                "2026-08-01 10:00:00", "13.8415", "75.7022", "Closed", "Highly Verified",
                95.0, 0, "Bhadravathi Block Engineer", "2026-08-08 10:00:00"
            )
        )
        issue_a_id = cursor.lastrowid

        # Verification trail for Scenario A
        cursor.execute("INSERT INTO issue_verifications (issue_id, user_id, user_role, confidence_weight, confirms_issue, timestamp) VALUES (?, ?, ?, ?, ?, ?);",
                       (issue_a_id, stu_rampura, "Student Representative", 0.30, 1, "2026-08-01 11:30:00"))
        
        # Inspection entry
        cursor.execute("INSERT INTO inspections (school_id, issue_id, inspector_name, timestamp, findings, verified_status, recommendations) VALUES (?, ?, ?, ?, ?, ?, ?);",
                       (rampura_id, issue_a_id, "Bhadravathi BEO Officer", "2026-08-02 14:00:00", "Toilet blockage verified. Requires pipeline replacement.", "Verified", "Sanction local funds for replacement."))
        
        # Student feedback ratings (Appreciations / Approvals)
        for i in range(1, 6):
            uname = f"student_rep{i}" if i > 1 else "student_rampura"
            cursor.execute("INSERT INTO student_feedback (issue_id, rep_name, status_rating, feedback_text, timestamp) VALUES (?, ?, ?, ?, ?);",
                           (issue_a_id, uname, "Fully Solved", "Plumbing issue is fixed. Toilets are working now.", "2026-08-05 16:00:00"))

        # Scenario B: Headmaster and students disagree -> conflict -> inspection recommended
        # GHS Sagar
        sagar_id = school_id_map["Government High School, Sagar"]
        hm_sagar = user_id_map["headmaster_sagar"]
        stu_sagar = user_id_map["student_sagar"]
        vol_sagar = user_id_map["volunteer_sagar"]

        cursor.execute(
            """
            INSERT INTO issues (
                report_id, school_id, reporter_id, reporter_role, category, description,
                submitted_time, latitude, longitude, status, verification_status,
                verification_confidence, dangerous_school_status, assignment, resolution_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "RPT-0002", sagar_id, stu_sagar, "Student Representative", "Drinking Water",
                "The drinking water purification system has stopped working. Dirty mud water is coming from the pipe.",
                "2026-08-18 09:30:00", "14.1672", "75.0234", "Inspection Required", "Review Required",
                50.0, 0, "Sagar Taluk Health Officer", "2026-08-25 09:30:00"
            )
        )
        issue_b_id = cursor.lastrowid

        # Verification trail for Scenario B (disagree / conflict)
        cursor.execute("INSERT INTO issue_verifications (issue_id, user_id, user_role, confidence_weight, confirms_issue, timestamp) VALUES (?, ?, ?, ?, ?, ?);",
                       (issue_b_id, vol_sagar, "Village Volunteer", 0.20, 1, "2026-08-18 11:00:00"))
        cursor.execute("INSERT INTO issue_verifications (issue_id, user_id, user_role, confidence_weight, confirms_issue, timestamp) VALUES (?, ?, ?, ?, ?, ?);",
                       (issue_b_id, hm_sagar, "Headmaster", 0.30, 0, "2026-08-18 14:00:00"))  # Headmaster denies it, claims it works!

        # Raise Conflict Notification
        cursor.execute(
            """
            INSERT INTO notifications (user_id, role_target, message, timestamp, type, issue_id)
            VALUES (NULL, 'District Education Officer', 'Conflict detected on report RPT-0002. Headmaster claims drinking water is available, but Student Representative verifies it is unavailable.', '2026-08-18 14:05:00', 'Conflict', ?);
            """,
            (issue_b_id,)
        )

        # Scenario C: Unsafe building -> emergency -> officer alert -> inspection required
        # GHS Mudigere
        mudigere_id = school_id_map["Government High School, Mudigere"]
        stu_mudigere = user_id_map["student_mudigere"]

        cursor.execute(
            """
            INSERT INTO issues (
                report_id, school_id, reporter_id, reporter_role, category, description,
                submitted_time, latitude, longitude, status, verification_status,
                verification_confidence, dangerous_school_status, assignment, resolution_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "RPT-0003", mudigere_id, stu_mudigere, "Student Representative", "Infrastructure",
                "Cracks have opened in the ceiling of the Class 9 classroom. Small pieces of concrete are falling during study hours. Unsafe building.",
                "2026-08-19 15:45:00", "13.1368", "75.6372", "Pending", "Review Required",
                30.0, 1, None, "2026-08-21 15:45:00" # Emergency 48h SLA
            )
        )
        issue_c_id = cursor.lastrowid

        # Raise Emergency Notification
        cursor.execute(
            """
            INSERT INTO notifications (user_id, role_target, message, timestamp, type, issue_id)
            VALUES (NULL, 'District Education Officer', '🚨 EMERGENCY: Unsafe infrastructure reported at GHS Mudigere. Concrete slab falling from ceiling.', '2026-08-19 15:50:00', 'Emergency', ?);
            """,
            (issue_c_id,)
        )

        # Scenario F: Multiple users report the same issue -> duplicate detection
        # Create duplicate issues for Mudigere infrastructure crack
        cursor.execute(
            """
            INSERT INTO issues (
                report_id, school_id, reporter_id, reporter_role, category, description,
                submitted_time, latitude, longitude, status, verification_status,
                verification_confidence, dangerous_school_status, assignment, resolution_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "RPT-0004", mudigere_id, user_id_map["headmaster_mudigere"], "Headmaster", "Infrastructure",
                "Class 9 room roof structural cracks on ceiling plaster, requires civil engineer inspection.",
                "2026-08-19 17:00:00", "13.1368", "75.6372", "Pending", "Review Required",
                30.0, 1, None, "2026-08-21 17:00:00"
            )
        )

        # Scenario G: Issue remains unresolved -> SLA expires -> escalation
        # GHPS Rampura
        cursor.execute(
            """
            INSERT INTO issues (
                report_id, school_id, reporter_id, reporter_role, category, description,
                submitted_time, latitude, longitude, status, verification_status,
                verification_confidence, dangerous_school_status, assignment, resolution_deadline, is_escalated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "RPT-0005", rampura_id, user_id_map["volunteer_rampura"], "Village Volunteer", "Electricity",
                "Main power line is cut due to tree fall. No fans or lights working in school for over 2 weeks.",
                "2026-08-01 08:00:00", "13.8415", "75.7022", "Pending", "Verified",
                60.0, 0, "Bhadravathi Power Section", "2026-08-08 08:00:00", 1
            )
        )
        issue_g_id = cursor.lastrowid

        # Escalation Notification
        cursor.execute(
            """
            INSERT INTO notifications (user_id, role_target, message, timestamp, type, issue_id)
            VALUES (NULL, 'District Education Officer', '⚠️ SLA ESCALATION: Report RPT-0005 has been unresolved past the 7-day resolution window.', '2026-08-09 08:00:00', 'Escalation', ?);
            """,
            (issue_g_id,)
        )

        # Scenario H: Student representative rejects claimed resolution
        # Belur Primary
        belur_id = school_id_map["Government Middle School, Belur"]
        cursor.execute(
            """
            INSERT INTO issues (
                report_id, school_id, reporter_id, reporter_role, category, description,
                submitted_time, latitude, longitude, status, verification_status,
                verification_confidence, dangerous_school_status, assignment, resolution_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "RPT-0006", belur_id, user_id_map["officer_state"], "Education Officer", "Sanitation",
                "Plumbing blockage and overflowing toilets in girls section.",
                "2026-08-10 11:00:00", "13.1624", "75.8598", "Action Completed", "Verified",
                70.0, 0, "Belur Block Plumber", "2026-08-17 11:00:00"
            )
        )
        issue_h_id = cursor.lastrowid

        # Student feedback rejects the fix
        cursor.execute("INSERT INTO student_feedback (issue_id, rep_name, status_rating, feedback_text, timestamp) VALUES (?, ?, ?, ?, ?);",
                       (issue_h_id, "student_rampura", "Not Solved", "Toilets are still blocked. Work is incomplete.", "2026-08-16 15:00:00"))

        # Reopen notification
        cursor.execute(
            """
            INSERT INTO notifications (user_id, role_target, message, timestamp, type, issue_id)
            VALUES (NULL, 'Taluk Education Officer', '❌ RESOLUTION REJECTED: Students rejected completion status on report RPT-0006 at Belur School.', '2026-08-16 15:10:00', 'Resolution Rejected', ?);
            """,
            (issue_h_id,)
        )

        # Audit logs seed
        audit_events = [
            (user_id_map["officer_state"], "officer_state", "State Education Department Official", "INITIALIZE_DATABASE", "2026-08-20 10:45:00", "system", "0", None, "Version 1.0"),
            (user_id_map["headmaster_rampura"], "headmaster_rampura", "Headmaster", "SUBMIT_REPORT", "2026-08-01 10:00:00", "issue", "RPT-0001", None, "Pending"),
            (user_id_map["student_rampura"], "student_rampura", "Student Representative", "VERIFY_REPORT", "2026-08-01 11:30:00", "issue", "RPT-0001", "Pending", "Verified"),
            (user_id_map["officer_shivamogga"], "officer_shivamogga", "District Education Officer", "UPDATE_STATUS", "2026-08-05 16:30:00", "issue", "RPT-0001", "Action Completed", "Closed")
        ]
        for uid, uname, urole, action, ts, etype, eid, pval, nval in audit_events:
            cursor.execute(
                """
                INSERT INTO audit_logs (user_id, username, role, action, timestamp, entity_type, entity_id, prev_value, new_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (uid, uname, urole, action, ts, etype, eid, pval, nval)
            )

        # Mark seeding completed
        cursor.execute("INSERT INTO system_meta (key, value) VALUES ('demo_seed_version', '1');")
