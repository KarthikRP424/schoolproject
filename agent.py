"""
agent.py
--------
This file contains the core AI agent logic for the School Issue Monitoring System.
It implements the rules specified for classifying, scoring, and verifying reports.
"""

def analyze_school_report(report_data: dict) -> dict:
    """
    Analyzes a school issue report based on structured rules.

    Input: report_data (dict) with:
      - school_name (str)
      - district (str)
      - taluk (str)
      - reporter_role (str)
      - issue_description (str)
      - has_photo (bool)
      - has_gps (bool)

    Returns: dict with:
      - category (str)
      - priority_level (str)
      - priority_score (int)
      - verification_status (str)
      - fake_risk (str)
      - recommended_action (str)
      - officer_summary (str)
    """
    school_name = report_data.get("school_name", "").strip()
    district = report_data.get("district", "").strip()
    taluk = report_data.get("taluk", "").strip()
    reporter_role = report_data.get("reporter_role", "").strip()
    issue_description = report_data.get("issue_description", "").strip()
    has_photo = report_data.get("has_photo", False)
    has_gps = report_data.get("has_gps", False)

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 1: Category Detection
    # ─────────────────────────────────────────────────────────────────────────────
    desc_lower = issue_description.lower()
    
    if "toilet" in desc_lower or "washroom" in desc_lower or "sanitation" in desc_lower:
        category = "Sanitation"
    elif "water" in desc_lower or "drinking water" in desc_lower:
        category = "Drinking Water"
    elif "teacher" in desc_lower or "staff" in desc_lower or "no teacher" in desc_lower:
        category = "Teacher Shortage"
    elif any(word in desc_lower for word in ["roof", "wall", "building", "classroom", "damage"]):
        category = "Infrastructure"
    elif any(word in desc_lower for word in ["electricity", "light", "fan", "power"]):
        category = "Electricity"
    else:
        category = "General Issue"

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 2: Priority Scoring
    # ─────────────────────────────────────────────────────────────────────────────
    priority_score = 40  # Start score at 40

    # Add points based on category
    if category in ["Sanitation", "Drinking Water"]:
        priority_score += 35
    elif category == "Teacher Shortage":
        priority_score += 30
    elif category == "Infrastructure":
        priority_score += 25
    elif category == "Electricity":
        priority_score += 20

    # Add points for urgency keywords
    urgency_keywords = ["urgent", "unsafe", "dangerous", "health", "students suffering"]
    if any(keyword in desc_lower for keyword in urgency_keywords):
        priority_score += 15

    # Add points for reporter role (Headmaster)
    if "headmaster" in reporter_role.lower():
        priority_score += 10

    # Add points for evidence
    if has_photo:
        priority_score += 10
    if has_gps:
        priority_score += 10

    # Limit score to maximum 100
    priority_score = min(priority_score, 100)

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 3: Priority Level
    # ─────────────────────────────────────────────────────────────────────────────
    if 80 <= priority_score <= 100:
        priority_level = "Urgent"
    elif 60 <= priority_score <= 79:
        priority_level = "High"
    elif 40 <= priority_score <= 59:
        priority_level = "Medium"
    else:
        priority_level = "Low"

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 4: Fake Risk Check
    # ─────────────────────────────────────────────────────────────────────────────
    if has_photo and has_gps:
        fake_risk = "Low"
    elif has_photo or has_gps:
        fake_risk = "Medium"
    else:
        fake_risk = "High"

    # Increase risk if issue description has fewer than 15 characters
    if len(issue_description) < 15:
        if fake_risk == "Low":
            fake_risk = "Medium"
        elif fake_risk == "Medium":
            fake_risk = "High"
        # if already High, stays High

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 5: Verification Status
    # ─────────────────────────────────────────────────────────────────────────────
    if fake_risk == "High":
        verification_status = "Manual verification or surprise visit recommended"
    else:
        verification_status = "Report has enough supporting details"

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 6: Recommended Action
    # ─────────────────────────────────────────────────────────────────────────────
    if category == "Sanitation":
        if priority_level in ["Urgent", "High"]:
            recommended_action = "Deploy sanitation crew for emergency repair and cleanup of school washrooms within 24 hours."
        else:
            recommended_action = "Schedule plumbing maintenance and hygiene audit with block officials."
    elif category == "Drinking Water":
        if priority_level in ["Urgent", "High"]:
            recommended_action = "Provide temporary water tanker supply immediately and dispatch pump technician within 24 hours."
        else:
            recommended_action = "Submit pipeline repair request under the school maintenance budget."
    elif category == "Teacher Shortage":
        if priority_level in ["Urgent", "High"]:
            recommended_action = "Escalate to District Education Officer (DEO) for immediate temporary teacher deputation."
        else:
            recommended_action = "Propose hiring guest teachers or adjusting local cluster staffing."
    elif category == "Infrastructure":
        if priority_level in ["Urgent", "High"]:
            recommended_action = "Secure structural safety fence. Dispatch junior engineer for building safety clearance."
        else:
            recommended_action = "Log repairs under Samagra Shiksha minor civil works fund."
    elif category == "Electricity":
        if priority_level in ["Urgent", "High"]:
            recommended_action = "Urgent notification to Electricity Board. Restrict access to any dangerous wiring."
        else:
            recommended_action = "Arrange electrician via School Management Committee (SMC) funds."
    else:  # General Issue
        if priority_level in ["Urgent", "High"]:
            recommended_action = "Forward report to the Block Development Officer for immediate review and action."
        else:
            recommended_action = "Log in the central monitoring dashboard for routine inspection."

    # ─────────────────────────────────────────────────────────────────────────────
    # Rule 7: Officer Summary
    # ─────────────────────────────────────────────────────────────────────────────
    officer_summary = (
        f"School: {school_name} in {taluk} Taluk, {district} District.\n"
        f"Issue Category: {category} (Urgency: {priority_level}, Priority Score: {priority_score}/100).\n"
        f"Verification Status: {fake_risk} Risk — {verification_status}.\n"
        f"Recommended Action: {recommended_action}"
    )

    return {
        "category": category,
        "priority_level": priority_level,
        "priority_score": priority_score,
        "verification_status": verification_status,
        "fake_risk": fake_risk,
        "recommended_action": recommended_action,
        "officer_summary": officer_summary
    }
