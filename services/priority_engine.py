"""
services/priority_engine.py
---------------------------
Implements the prioritization algorithms for schools.
Calculates the Priority Score, Health Score, Improvement Score, and Decline Risk.
"""
import json
from database.connection import execute_query

def calculate_school_priority(school_id: int) -> dict:
    """
    Computes a school's Priority Score (0-100) and priority level.
    Score is based on:
      - Teacher Shortage: 25%
      - Infrastructure Damage: 25%
      - Basic Facilities: 20%
      - Enrollment Decline: 15%
      - Unresolved Issues: 15%
    """
    # 1. Fetch School Data
    school = execute_query(
        """
        SELECT required_teachers, available_teachers, facility_status_json, 
               enrollment_trend_json FROM schools WHERE id = ?;
        """,
        (school_id,),
        fetch="one"
    )
    if not school:
        return {"score": 0.0, "level": "LOW", "breakdown": {}}

    # 2. Fetch Unresolved Issues Count (canonical statuses)
    issues_row = execute_query(
        "SELECT COUNT(*) as count FROM issues WHERE school_id = ? AND status NOT IN ('CLOSED','MERGED','Closed');",
        (school_id,),
        fetch="one"
    )
    unresolved_count = issues_row["count"] if issues_row else 0

    # 3. Fetch teacher absence metrics (Phase 2G: use sanctioned/present if available)
    teacher_metrics = execute_query(
        "SELECT sanctioned_teachers, present_teachers, absent_teachers FROM schools WHERE id = ?;",
        (school_id,), fetch="one"
    )
    has_precise_teacher_data = (
        teacher_metrics and
        teacher_metrics.get("sanctioned_teachers") is not None and
        teacher_metrics["sanctioned_teachers"] > 0
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CALCULATE COMPONENT SCORES
    # ─────────────────────────────────────────────────────────────────────────
    
    # A. Teacher Shortage (25%) — prefer sanctioned/present data when available
    if has_precise_teacher_data:
        sanctioned = teacher_metrics["sanctioned_teachers"]
        present    = teacher_metrics["present_teachers"]
        absent     = teacher_metrics["absent_teachers"] or (sanctioned - present)
        shortage_ratio = max(0.0, absent / sanctioned)
    else:
        req_t = max(school["required_teachers"], 1)
        avail_t = school["available_teachers"]
        shortage_ratio = max(0.0, (req_t - avail_t) / req_t)
    teacher_shortage_score = shortage_ratio * 100.0

    # B. Infrastructure Condition (25%)
    # Evaluate classroom and building condition from JSON
    fac_json = school["facility_status_json"]
    facilities = json.loads(fac_json) if fac_json else {}
    
    infra_points = 0.0
    building_cond = facilities.get("building_condition", "Available")
    classrooms = facilities.get("classrooms", "Available")
    
    if building_cond == "Damaged":
        infra_points += 50.0
    elif building_cond in ["Partially Available", "Requires Inspection"]:
        infra_points += 30.0
        
    if classrooms == "Damaged":
        infra_points += 50.0
    elif classrooms in ["Partially Available", "Requires Inspection"]:
        infra_points += 30.0
    infra_score = min(infra_points, 100.0)

    # C. Basic Facilities (20%)
    # Evaluate drinking water and toilet statuses
    water = facilities.get("drinking_water", "Available")
    b_toilet = facilities.get("boys_toilet", "Available")
    g_toilet = facilities.get("girls_toilet", "Available")
    
    fac_points = 0.0
    if water == "Not Available" or water == "Damaged":
        fac_points += 40.0
    elif water == "Partially Available":
        fac_points += 20.0
        
    if b_toilet == "Not Available" or b_toilet == "Damaged":
        fac_points += 30.0
    elif b_toilet == "Partially Available":
        fac_points += 15.0
        
    if g_toilet == "Not Available" or g_toilet == "Damaged":
        fac_points += 30.0
    elif g_toilet == "Partially Available":
        fac_points += 15.0
    fac_score = min(fac_points, 100.0)

    # D. Enrollment Decline (15%)
    trend_json = school["enrollment_trend_json"]
    trend = json.loads(trend_json) if trend_json else {}
    
    decline_score = 0.0
    years = sorted(trend.keys())
    if len(years) >= 2:
        oldest_count = max(trend[years[0]], 1)
        newest_count = trend[years[-1]]
        if newest_count < oldest_count:
            decline_ratio = (oldest_count - newest_count) / oldest_count
            decline_score = min(decline_ratio * 100.0, 100.0)

    # E. Unresolved Issues (15%)
    unresolved_score = min(unresolved_count * 20.0, 100.0) # Caps at 5 unresolved issues for full points

    # ─────────────────────────────────────────────────────────────────────────
    # ASSEMBLE FINAL PRIORITY SCORE
    # ─────────────────────────────────────────────────────────────────────────
    from config import PRIORITY_WEIGHTS
    
    final_score = (
        (teacher_shortage_score * PRIORITY_WEIGHTS["teacher_shortage"]) +
        (infra_score * PRIORITY_WEIGHTS["infrastructure_condition"]) +
        (fac_score * PRIORITY_WEIGHTS["basic_facilities"]) +
        (decline_score * PRIORITY_WEIGHTS["enrollment_decline"]) +
        (unresolved_score * PRIORITY_WEIGHTS["unresolved_issues"])
    )

    # Map to priority levels
    if final_score >= 86.0:
        level = "EMERGENCY"
    elif final_score >= 71.0:
        level = "CRITICAL"
    elif final_score >= 51.0:
        level = "HIGH"
    elif final_score >= 31.0:
        level = "MODERATE"
    else:
        level = "LOW"

    breakdown = {
        "teacher_shortage": round(teacher_shortage_score, 1),
        "infrastructure": round(infra_score, 1),
        "basic_facilities": round(fac_score, 1),
        "enrollment_decline": round(decline_score, 1),
        "unresolved_issues": round(unresolved_score, 1)
    }

    return {
        "score": round(final_score, 1),
        "level": level,
        "breakdown": breakdown
    }

def calculate_school_health(school_id: int) -> dict:
    """
    Computes a School Health Score (0-100) representing current physical & operational condition.
    - Teacher Availability: 20%
    - Infrastructure status: 20%
    - Basic facilities: 20%
    - Attendance level: 20%
    - Safety & Security: 20%
    """
    school = execute_query(
        "SELECT available_teachers, required_teachers, attendance_pct, facility_status_json FROM schools WHERE id = ?;",
        (school_id,),
        fetch="one"
    )
    if not school:
        return {"score": 100.0, "level": "Excellent"}

    fac_json = school["facility_status_json"]
    facilities = json.loads(fac_json) if fac_json else {}

    # 1. Teacher Availability (Max 20)
    req = max(school["required_teachers"], 1)
    avail = school["available_teachers"]
    teacher_pct = min(avail / req, 1.0)
    teacher_pts = teacher_pct * 20.0

    # 2. Infrastructure Status (Max 20)
    infra_pct = 1.0
    if facilities.get("building_condition") == "Damaged":
        infra_pct -= 0.5
    if facilities.get("classrooms") == "Damaged":
        infra_pct -= 0.5
    infra_pts = max(0.0, infra_pct) * 20.0

    # 3. Basic Facilities (Max 20)
    fac_pct = 1.0
    if facilities.get("drinking_water") in ["Not Available", "Damaged"]:
        fac_pct -= 0.4
    if facilities.get("boys_toilet") in ["Not Available", "Damaged"]:
        fac_pct -= 0.3
    if facilities.get("girls_toilet") in ["Not Available", "Damaged"]:
        fac_pct -= 0.3
    fac_pts = max(0.0, fac_pct) * 20.0

    # 4. Attendance Percentage (Max 20)
    att_pct = school["attendance_pct"] / 100.0
    att_pts = att_pct * 20.0

    # 5. Safety & Support Systems (Max 20)
    safety_pct = 1.0
    if facilities.get("boundary_wall") in ["Not Available", "Damaged"]:
        safety_pct -= 0.5
    if facilities.get("electricity") in ["Not Available", "Damaged"]:
        safety_pct -= 0.5
    safety_pts = max(0.0, safety_pct) * 20.0

    health_score = teacher_pts + infra_pts + fac_pts + att_pts + safety_pts

    if health_score >= 86.0:
        level = "Excellent"
    elif health_score >= 71.0:
        level = "Good"
    elif health_score >= 51.0:
        level = "Needs Improvement"
    elif health_score >= 31.0:
        level = "Poor"
    else:
        level = "Critical"

    return {
        "score": round(health_score, 1),
        "level": level
    }

def calculate_school_decline_risk(school_id: int) -> dict:
    """
    Evaluates School Decline Risk (0-100%) indicating closure/drop-out warning indicators.
    Indicators:
      - Multi-year enrollment drop (40%)
      - Low or dropping student attendance (30%)
      - Severe teacher shortage (20%)
      - Cumulative unresolved open complaints (10%)
    """
    school = execute_query(
        "SELECT required_teachers, available_teachers, attendance_pct, enrollment_trend_json FROM schools WHERE id = ?;",
        (school_id,),
        fetch="one"
    )
    if not school:
        return {"percentage": 0.0, "risk_level": "Low"}

    # 1. Enrollment Decline Factor (40%)
    trend_json = school["enrollment_trend_json"]
    trend = json.loads(trend_json) if trend_json else {}
    enroll_decline_factor = 0.0
    
    years = sorted(trend.keys())
    if len(years) >= 2:
        oldest = max(trend[years[0]], 1)
        newest = trend[years[-1]]
        if newest < oldest:
            decline_ratio = (oldest - newest) / oldest
            enroll_decline_factor = min(decline_ratio, 1.0) * 40.0

    # 2. Attendance Factor (30%)
    # Threshold warning starts when attendance drops below 85%
    att_pct = school["attendance_pct"]
    att_factor = 0.0
    if att_pct < 85.0:
        att_factor = ((85.0 - att_pct) / 35.0) * 30.0  # Caps out at 50% attendance
        att_factor = min(att_factor, 30.0)

    # 3. Teacher Shortage Factor (20%)
    req = max(school["required_teachers"], 1)
    avail = school["available_teachers"]
    teacher_factor = max(0.0, (req - avail) / req) * 20.0

    # 4. Open Complaints Factor (10%)
    issues_row = execute_query(
        "SELECT COUNT(*) as count FROM issues WHERE school_id = ? AND status NOT IN ('CLOSED','MERGED','Closed');",
        (school_id,), fetch="one"
    )
    unresolved_count = issues_row["count"] if issues_row else 0
    open_factor = min(unresolved_count * 2.0, 10.0)  # Maxes out at 5 open issues

    risk_pct = enroll_decline_factor + att_factor + teacher_factor + open_factor
    
    if risk_pct >= 75.0:
        level = "Critical"
    elif risk_pct >= 50.0:
        level = "High"
    elif risk_pct >= 25.0:
        level = "Moderate"
    else:
        level = "Low"

    return {
        "percentage": round(risk_pct, 1),
        "risk_level": level,
        "factors": {
            "enrollment_drop": round(enroll_decline_factor, 1),
            "low_attendance": round(att_factor, 1),
            "teacher_vacancy": round(teacher_factor, 1),
            "unresolved_complaints": round(open_factor, 1)
        }
    }

def get_school_improvement_score(school_id: int) -> float:
    """
    Compares latest health score with oldest recorded health score to measure net change.
    """
    scores = execute_query(
        "SELECT health_score FROM historical_scores WHERE school_id = ? ORDER BY timestamp ASC;",
        (school_id,)
    )
    if len(scores) < 2:
        return 0.0
    
    oldest = scores[0]["health_score"]
    latest = scores[-1]["health_score"]
    return round(latest - oldest, 1)

def update_all_school_scores():
    """
    Re-calculates priority, health, and risk parameters for all schools in the DB.
    Phase 2G: Also saves a historical_scores snapshot on every recalculation
    so trend charts always have up-to-date data.
    """
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    schools = execute_query("SELECT id FROM schools;")
    for s in schools:
        sid = s["id"]
        priority = calculate_school_priority(sid)
        health   = calculate_school_health(sid)
        risk     = calculate_school_decline_risk(sid)

        # Update live scores in schools table
        execute_query(
            """
            UPDATE schools
            SET health_score = ?, priority_score = ?, decline_risk = ?, priority_level = ?
            WHERE id = ?;
            """,
            (health["score"], priority["score"], risk["percentage"], priority["level"], sid),
            fetch="rowcount"
        )

        # Snapshot into historical_scores (Phase 2G)
        execute_query(
            """
            INSERT INTO historical_scores (school_id, timestamp, health_score, priority_score)
            VALUES (?, ?, ?, ?);
            """,
            (sid, now, health["score"], priority["score"]),
            fetch="rowcount"
        )
