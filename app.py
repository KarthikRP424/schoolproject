"""
app.py
------
Main Streamlit application for the "AI School Issue Monitoring and Priority Agent" project.
Features a role-based login system, session-based password reset, auto-filled reporter profiles,
and a government officer dashboard with district-specific filters, urgent alerts, and status updates.

To run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Import the local rule-based agent function
from agent import analyze_school_report

# ─────────────────────────────────────────────────────────────────────────────
# 1. PAGE TITLE & SETUP
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI School Issue Monitoring and Priority Agent",
    page_icon="🏫",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

# Initialize user accounts dictionary
if "users" not in st.session_state:
    st.session_state["users"] = {
        # Headmasters
        "headmaster_rampura": {
            "password": "Head@123",
            "role": "Headmaster",
            "school_name": "Government Higher Primary School, Rampura",
            "district": "Shivamogga",
            "taluk": "Bhadravathi",
            "village": "Rampura"
        },
        "headmaster_sagar": {
            "password": "Head@456",
            "role": "Headmaster",
            "school_name": "Government High School, Sagar",
            "district": "Shivamogga",
            "taluk": "Sagar",
            "village": "Sagar"
        },
        # Student Representatives
        "student_rampura": {
            "password": "Stu@123",
            "role": "Student Representative",
            "school_name": "Government Higher Primary School, Rampura",
            "district": "Shivamogga",
            "taluk": "Bhadravathi",
            "village": "Rampura"
        },
        "student_sagar": {
            "password": "Stu@456",
            "role": "Student Representative",
            "school_name": "Government High School, Sagar",
            "district": "Shivamogga",
            "taluk": "Sagar",
            "village": "Sagar"
        },
        # Village Volunteers
        "volunteer_rampura": {
            "password": "Vol@123",
            "role": "Village Volunteer",
            "school_name": "Government Higher Primary School, Rampura",
            "district": "Shivamogga",
            "taluk": "Bhadravathi",
            "village": "Rampura"
        },
        "volunteer_sagar": {
            "password": "Vol@456",
            "role": "Village Volunteer",
            "school_name": "Government High School, Sagar",
            "district": "Shivamogga",
            "taluk": "Sagar",
            "village": "Sagar"
        },
        # Government Officers
        "officer_shivamogga": {
            "password": "Off@123",
            "role": "Government Officer",
            "district": "Shivamogga"
        },
        "officer_state": {
            "password": "State@123",
            "role": "Government Officer",
            "district": "All"
        }
    }

# Initialize reports list
if "reports" not in st.session_state:
    st.session_state["reports"] = []

# Initialize sample reports from CSV exactly once
if "sample_reports_loaded" not in st.session_state:
    csv_path = os.path.join("data", "sample_reports.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for idx, row in df.iterrows():
                desc = str(row.get("issue_description", ""))
                
                # Analyze using core local agent to generate categories and scores
                result = analyze_school_report({
                    "school_name": str(row.get("school_name", "")),
                    "district": str(row.get("district", "")),
                    "taluk": str(row.get("taluk", "")),
                    "reporter_role": str(row.get("reporter_role", "")),
                    "issue_description": desc,
                    "has_photo": bool(row.get("has_photo", False)),
                    "has_gps": bool(row.get("has_gps", False))
                })
                
                dangerous_school = (result["priority_level"] == "Urgent")
                rpt_id = f"RPT-{str(idx + 1).zfill(4)}"
                
                # Default mock coordinate generation for sample database
                lat = "13.9299" if str(row.get("district", "")).strip() == "Shivamogga" else "13.3379"
                lon = "75.7224" if str(row.get("district", "")).strip() == "Shivamogga" else "77.1009"
                
                st.session_state["reports"].append({
                    "report_id": rpt_id,
                    "submitted_time": "2026-06-20 12:00:00",
                    "school_name": str(row.get("school_name", "")),
                    "district": str(row.get("district", "")),
                    "taluk": str(row.get("taluk", "")),
                    "village_name": str(row.get("taluk", "")) + " Village",
                    "reporter_name": "System Sample Loader",
                    "reporter_role": str(row.get("reporter_role", "")),
                    "issue_description": desc,
                    "latitude": lat,
                    "longitude": lon,
                    "photo_evidence_available": bool(row.get("has_photo", False)),
                    "gps_location_available": bool(row.get("has_gps", False)),
                    "uploaded_image_name": "sample_photo.jpg" if row.get("has_photo") else "None",
                    "category": result["category"],
                    "priority_level": result["priority_level"],
                    "priority_score": result["priority_score"],
                    "fake_risk": result["fake_risk"],
                    "verification_status": result["verification_status"],
                    "recommended_action": result["recommended_action"],
                    "officer_summary": result["officer_summary"],
                    "dangerous_school_status": dangerous_school,
                    "status": "Pending"
                })
        except Exception as e:
            st.error(f"Error loading sample CSV records: {e}")
    st.session_state["sample_reports_loaded"] = True

# Initialize login status tracking
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

# Initialize password reset mode toggle
if "reset_mode" not in st.session_state:
    st.session_state["reset_mode"] = False


# ─────────────────────────────────────────────────────────────────────────────
# 3. AUTHENTICATION & LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def handle_logout():
    st.session_state["logged_in_user"] = None
    st.success("Successfully logged out.")

if st.session_state["logged_in_user"] is None:
    st.title("🏫 AI School Issue Monitoring and Priority Agent")
    st.write("Welcome! Please log in with your credentials to access the agent portal.")

    # Two columns layout: Login box and Reset/Credentials details
    left_col, right_col = st.columns(2)

    with left_col:
        # Checkbox to toggle between Login screen and Reset Password screen
        reset_checkbox = st.checkbox("Forgot / Reset Password", value=st.session_state["reset_mode"])
        st.session_state["reset_mode"] = reset_checkbox

        if st.session_state["reset_mode"]:
            st.subheader("🔑 Reset Password")
            st.info("💡 Note: This is a demo reset system. Password changes are temporary and will reset when the app restarts.")

            reset_username = st.text_input("Username", key="reset_user").strip()
            new_password = st.text_input("New Password", type="password", key="reset_pass1")
            confirm_password = st.text_input("Confirm New Password", type="password", key="reset_pass2")

            if st.button("Reset Password"):
                if not reset_username or not new_password or not confirm_password:
                    st.error("Please fill in all the reset fields.")
                elif reset_username not in st.session_state["users"]:
                    st.error("Username does not exist in the database.")
                elif len(new_password) < 6:
                    st.error("New password must be at least 6 characters long.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    # Update password in session state users map
                    st.session_state["users"][reset_username]["password"] = new_password
                    st.success("Password reset successful. Please login with your new password.")
                    st.session_state["reset_mode"] = False
        else:
            st.subheader("👤 User Login")
            login_username = st.text_input("Username", key="login_user").strip()
            login_password = st.text_input("Password", type="password", key="login_pass")

            if st.button("Login"):
                if login_username in st.session_state["users"]:
                    expected_password = st.session_state["users"][login_username]["password"]
                    if login_password == expected_password:
                        # Success: save user detail and username key in session state
                        user_info = st.session_state["users"][login_username].copy()
                        user_info["username"] = login_username
                        st.session_state["logged_in_user"] = user_info
                        st.rerun()
                    else:
                        st.error("Incorrect password. Please try again.")
                else:
                    st.error("Username not found.")

    with right_col:
        # Expandable helper to show prototype credentials
        with st.expander("View Demo Login Credentials", expanded=True):
            st.write("Use the credentials below to test the different user views and filter scopes:")
            
            # Format user dictionary for visual display in a dataframe
            cred_rows = []
            for username, data in st.session_state["users"].items():
                access = "All Districts" if data.get("district") == "All" else f"{data.get('district')} District Only" if "district" in data and data.get("role") == "Government Officer" else f"{data.get('school_name', '')} ({data.get('taluk', '')})"
                cred_rows.append({
                    "Role": data.get("role"),
                    "Username": username,
                    "Password": data.get("password"),
                    "Scope / Access Level": access
                })
            st.dataframe(pd.DataFrame(cred_rows), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-style: italic;'>"
        "Better Schools. Smarter Decisions. Stronger Communities."
        "</div>",
        unsafe_allow_html=True
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 4. LOGGED-IN SYSTEM GATEWAY
# ─────────────────────────────────────────────────────────────────────────────

user = st.session_state["logged_in_user"]

# Sidebar information
st.sidebar.title("🏫 AI School Monitor")
st.sidebar.markdown(f"**Logged in as:** `{user['username']}`")
st.sidebar.markdown(f"**Role:** {user['role']}")

if "school_name" in user:
    st.sidebar.markdown(f"**School:** {user['school_name']}")
if "district" in user and user["role"] != "Government Officer":
    st.sidebar.markdown(f"**District:** {user['district']}")

# Logout button
if st.sidebar.button("Logout", type="secondary"):
    handle_logout()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Capstone Track:** Agents for Good")
st.sidebar.markdown("**Security:** No API key used")
st.sidebar.markdown("**Built With:** Python and Streamlit")


# ═════════════════════════════════════════════════════════════════════════════
# 5. GOVERNMENT OFFICER VIEW
# ═════════════════════════════════════════════════════════════════════════════

if user["role"] == "Government Officer":
    st.title("🏛️ Government Officer Dashboard")
    st.write(
        "Reviewing real-time school issue submissions in your database. "
        "Any updates made to status logs will take effect instantly."
    )

    # Load reports from session state
    reports_data = st.session_state["reports"]
    
    if not reports_data:
        st.info("No school issue reports are currently logged in the system.")
    else:
        df_reports = pd.DataFrame(reports_data)
        
        # Strip trailing whitespaces for district filters
        df_reports["district_clean"] = df_reports["district"].astype(str).str.strip()

        # Apply geographical jurisdiction filtering
        officer_district = user.get("district")
        if officer_district == "All":
            jurisdiction_reports = df_reports
            st.success("🌍 State-wide access level: displaying all school reports.")
        else:
            jurisdiction_reports = df_reports[df_reports["district_clean"].str.lower() == officer_district.lower()]
            st.success(f"📍 District access level: showing reports for **{officer_district}** only.")

        # ─────────────────────────────────────────────────────────────────────
        # 8. URGENT ALERT SECTION
        # ─────────────────────────────────────────────────────────────────────
        st.subheader("🚨 New Urgent Reports")
        urgent_df = jurisdiction_reports[jurisdiction_reports["priority_level"] == "Urgent"]
        
        if urgent_df.empty:
            st.info("No active Urgent-level reports inside your jurisdiction.")
        else:
            for idx, row in urgent_df.iterrows():
                with st.warning(f"⚠️ Report ID: {row['report_id']} — Submitted: {row['submitted_time']}"):
                    st.markdown(f"**School:** {row['school_name']} ({row['village_name']}, {row['taluk']} Taluk, {row['district']} District)")
                    st.markdown(f"**Reporter:** {row['reporter_role']}")
                    st.markdown(f"**Issue:** {row['issue_description']}")
                    st.markdown(f"**Score:** `{row['priority_score']}/100` | **Action Plan:** {row['recommended_action']}")

        # ─────────────────────────────────────────────────────────────────────
        # 9. DANGEROUS SCHOOL ALERT SECTION
        # ─────────────────────────────────────────────────────────────────────
        st.subheader("🔥 Dangerous School Alerts")
        danger_df = jurisdiction_reports[jurisdiction_reports["dangerous_school_status"] == True]
        
        if danger_df.empty:
            st.info("No schools in your jurisdiction are currently flagged under Dangerous Status.")
        else:
            danger_cols = st.columns(min(len(danger_df), 3))
            for i, (_, row) in enumerate(danger_df.iterrows()):
                col_to_use = danger_cols[i % len(danger_cols)]
                with col_to_use:
                    st.error(f"🛑 DANGER: {row['school_name']}")
                    st.markdown(f"**Location:** {row['village_name']}, {row['taluk']}, {row['district']}")
                    st.markdown(f"**Problem:** {row['issue_description'][:100]}...")
                    st.markdown(f"**Score:** `{row['priority_score']}/100`")
                    st.markdown(f"**Briefing:** *{row['officer_summary'][:150]}...*")
                    st.markdown(f"**Recommended action:** {row['recommended_action']}")

        st.markdown("---")

        # ─────────────────────────────────────────────────────────────────────
        # 12. OFFICER FILTERS
        # ─────────────────────────────────────────────────────────────────────
        st.subheader("🔍 Filters & Search")
        
        f1, f2, f3, f4, f5 = st.columns(5)
        
        with f1:
            # District filter (dependent on jurisdiction)
            dist_options = ["All"] + sorted(jurisdiction_reports["district"].dropna().unique().tolist())
            sel_dist = st.selectbox("District", dist_options)
            
        with f2:
            taluk_options = ["All"] + sorted(jurisdiction_reports["taluk"].dropna().unique().tolist())
            sel_taluk = st.selectbox("Taluk", taluk_options)
            
        with f3:
            role_options = ["All"] + sorted(jurisdiction_reports["reporter_role"].dropna().unique().tolist())
            sel_role = st.selectbox("Reporter Role", role_options)
            
        with f4:
            priority_options = ["All"] + sorted(jurisdiction_reports["priority_level"].dropna().unique().tolist())
            sel_priority = st.selectbox("Priority Level", priority_options)
            
        with f5:
            status_options = ["All"] + sorted(jurisdiction_reports["status"].dropna().unique().tolist())
            sel_status = st.selectbox("Status", status_options)

        # Apply user filters
        filtered_df = jurisdiction_reports.copy()
        if sel_dist != "All":
            filtered_df = filtered_df[filtered_df["district"] == sel_dist]
        if sel_taluk != "All":
            filtered_df = filtered_df[filtered_df["taluk"] == sel_taluk]
        if sel_role != "All":
            filtered_df = filtered_df[filtered_df["reporter_role"] == sel_role]
        if sel_priority != "All":
            filtered_df = filtered_df[filtered_df["priority_level"] == sel_priority]
        if sel_status != "All":
            filtered_df = filtered_df[filtered_df["status"] == sel_status]

        # ─────────────────────────────────────────────────────────────────────
        # 7. MAIN REPORTS TABLE
        # ─────────────────────────────────────────────────────────────────────
        st.subheader("📋 Active Reports Register")
        
        if filtered_df.empty:
            st.info("No records match the current filter selection.")
        else:
            display_cols = [
                "report_id", "submitted_time", "school_name", "district", "taluk", 
                "reporter_role", "category", "priority_level", "priority_score", "fake_risk", "status"
            ]
            renamed_df = filtered_df[display_cols].rename(columns={
                "report_id": "Report ID",
                "submitted_time": "Submitted Time",
                "school_name": "School Name",
                "district": "District",
                "taluk": "Taluk",
                "reporter_role": "Reporter Role",
                "category": "Category",
                "priority_level": "Priority Level",
                "priority_score": "Score",
                "fake_risk": "Risk Level",
                "status": "Current Status"
            })
            st.dataframe(renamed_df, use_container_width=True, hide_index=True)

            # ─────────────────────────────────────────────────────────────────────
            # 10. STATUS UPDATE UTILITY
            # ─────────────────────────────────────────────────────────────────────
            st.subheader("🔧 Manage Report Status & Verification Details")
            
            selected_report_id = st.selectbox(
                "Select Report ID to update status or view full brief:",
                options=filtered_df["report_id"].tolist()
            )
            
            # Find the corresponding report object in session state list
            original_idx = next((i for i, r in enumerate(st.session_state["reports"]) if r["report_id"] == selected_report_id), None)
            
            if original_idx is not None:
                selected_report = st.session_state["reports"][original_idx]
                
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.markdown(f"**Selected Report:** `{selected_report_id}` ({selected_report['school_name']})")
                    # Update status
                    new_status = st.selectbox(
                        "Update Status",
                        options=["Pending", "Under Review", "Inspection Scheduled", "Resolved"],
                        index=["Pending", "Under Review", "Inspection Scheduled", "Resolved"].index(selected_report["status"]),
                        key=f"status_{selected_report_id}"
                    )
                    
                    if new_status != selected_report["status"]:
                        st.session_state["reports"][original_idx]["status"] = new_status
                        st.success(f"Status for {selected_report_id} updated successfully to: {new_status}!")
                        st.rerun()
                
                with sc2:
                    st.markdown(f"📍 **Coordinates:** Latitude `{selected_report.get('latitude')}`, Longitude `{selected_report.get('longitude')}`")
                    st.markdown(f"🖼️ **Evidence File:** `{selected_report.get('uploaded_image_name')}`")
                    st.markdown(f"🔍 **Verification:** {selected_report.get('verification_status')}")
                
                st.markdown("**Officer Summary Brief:**")
                st.code(selected_report["officer_summary"], language="markdown")


# ═════════════════════════════════════════════════════════════════════════════
# 6. REPORTER VIEW (Headmaster, Student, Village Volunteer)
# ═════════════════════════════════════════════════════════════════════════════

else:
    st.title("📝 Submit School Issue Report")
    st.write(
        "Create a new issue submission report. Details matching your user profile "
        "have been automatically filled."
    )

    # Wrap inputs inside a Streamlit form
    with st.form("school_report_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            school_name = st.text_input("School Name", value=user.get("school_name", ""))
            district = st.text_input("District", value=user.get("district", ""))
            village_name = st.text_input("Village Name", value=user.get("village", ""))
            
        with col2:
            taluk = st.text_input("Taluk", value=user.get("taluk", ""))
            # Reporter role auto-selected based on user profile role
            reporter_role = st.selectbox(
                "Reporter Role",
                options=["Headmaster", "Student Representative", "Village Volunteer", "Education Officer"],
                index=["Headmaster", "Student Representative", "Village Volunteer", "Education Officer"].index(user.get("role")) if user.get("role") in ["Headmaster", "Student Representative", "Village Volunteer", "Education Officer"] else 0
            )
            
        issue_description = st.text_area(
            "Issue Description", 
            placeholder="Describe the issue clearly (e.g., The toilet washroom ceiling is leaking and needs urgent repair)."
        )
        
        st.write("**Supporting Evidence**")
        col_photo, col_gps = st.columns(2)
        with col_photo:
            uploaded_file = st.file_uploader("📷 Upload Photo Evidence", type=["jpg", "png", "jpeg"])
            has_photo = uploaded_file is not None
        with col_gps:
            gps_coordinates = st.text_input("📡 GPS Coordinates (Latitude, Longitude)", placeholder="e.g., 12.9716, 77.5946")
            has_gps = len(gps_coordinates.strip()) > 0
            
        submit_button = st.form_submit_button("🔍 Analyze and Submit Report")

    # Submission logic execution
    if submit_button:
        if not school_name.strip() or not district.strip() or not taluk.strip() or not issue_description.strip():
            st.error("⚠️ Please fill out all the fields in the form before analyzing.")
        else:
            report_data = {
                "school_name": school_name.strip(),
                "district": district.strip(),
                "taluk": taluk.strip(),
                "reporter_role": reporter_role,
                "issue_description": issue_description.strip(),
                "has_photo": has_photo,
                "has_gps": has_gps
            }
            
            # Process using rule agent
            result = analyze_school_report(report_data)
            
            # Parse latitude and longitude from input coordinate string
            lat, lon = "None", "None"
            if has_gps and "," in gps_coordinates:
                try:
                    parts = gps_coordinates.split(",")
                    lat, lon = parts[0].strip(), parts[1].strip()
                except Exception:
                    pass
            
            # Generate automatic report_id and submitted_time
            report_id = "RPT-" + str(len(st.session_state["reports"]) + 1).zfill(4)
            submitted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dangerous_status = (result["priority_level"] == "Urgent")
            uploaded_name = uploaded_file.name if has_photo else "None"

            # 3. Assemble report dictionary (User Input + Agent Output)
            new_record = {
                "report_id": report_id,
                "submitted_time": submitted_time,
                "school_name": school_name.strip(),
                "district": district.strip(),
                "taluk": taluk.strip(),
                "village_name": village_name.strip(),
                "reporter_name": user["username"],
                "reporter_role": reporter_role,
                "issue_description": issue_description.strip(),
                "latitude": lat,
                "longitude": lon,
                "photo_evidence_available": has_photo,
                "gps_location_available": has_gps,
                "uploaded_image_name": uploaded_name,
                "category": result["category"],
                "priority_level": result["priority_level"],
                "priority_score": result["priority_score"],
                "fake_risk": result["fake_risk"],
                "verification_status": result["verification_status"],
                "recommended_action": result["recommended_action"],
                "officer_summary": result["officer_summary"],
                "dangerous_school_status": dangerous_status,
                "status": "Pending"
            }
            
            # Save into session state array
            st.session_state["reports"].append(new_record)
            
            # 6. Success and dashboard insertion message
            st.success("Report submitted successfully and sent to Government Officer dashboard.")
            
            # 11. Simple proof display
            st.info(f"📋 **Your Report ID:** `{report_id}`")
            st.info(f"📊 **Current total reports in officer dashboard:** `{len(st.session_state['reports'])}`")
            
            st.subheader("📊 Submitted Report AI Analysis Results")
            
            # Visual display cards
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric(label="📂 Category", value=result["category"])
            with m_col2:
                st.metric(label="🎯 Priority Level", value=result["priority_level"])
            with m_col3:
                st.metric(label="📊 Priority Score", value=f"{result['priority_score']}/100")
                
            st.subheader("🕵️ Verification & Risk Assessment")
            st.metric(label="🕵️ Fake Risk", value=f"{result['fake_risk']} Risk")
            st.info(f"🔍 **Verification Status:** {result['verification_status']}")
            
            if has_photo:
                st.subheader("📷 Uploaded Evidence Photo Preview")
                st.image(uploaded_file, caption=f"Uploaded File: {uploaded_name}", use_container_width=True)

            st.subheader("✅ Recommended Action")
            st.success(result["recommended_action"])
            
            st.subheader("📄 Officer Briefing Summary")
            st.code(result["officer_summary"], language="markdown")


# ─────────────────────────────────────────────────────────────────────────────
# 7. FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-style: italic;'>"
    "Better Schools. Smarter Decisions. Stronger Communities."
    "</div>",
    unsafe_allow_html=True
)
