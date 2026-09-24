"""
app.py
------
Main entrypoint for the Karnataka Government School Monitoring and Early-Warning Platform.
Handles: database initialization, seeding, authentication routing, and dashboard rendering.
"""
import streamlit as st
from database.models import initialize_database
from database.seed import seed_demo_data
from auth.authentication import authenticate_user, reset_user_password
from dashboards.school import render_school_dashboard
from dashboards.district import render_district_dashboard
from dashboards.taluk import render_taluk_dashboard
from dashboards.state import render_state_dashboard
from dashboards.admin import render_admin_dashboard

# ─────────────────────────────────────────────────────────────────────────────
# APP CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Karnataka School Monitoring",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme CSS
st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    .main .block-container { padding-top: 2rem; }
    .stMetric label { color: #94a3b8 !important; }
    .stMetric [data-testid="stMetricValue"] { color: #f1f5f9 !important; }
    .stDataFrame, .stTable { background-color: #1e293b !important; }
    .stSelectbox label, .stTextInput label, .stTextArea label { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    .stButton > button { background-color: #1d4ed8; color: white; border: none; border-radius: 6px; }
    .stButton > button:hover { background-color: #2563eb; }
    h1, h2, h3, h4 { color: #f8fafc; }
    .stSuccess { background-color: #14532d !important; }
    .stError { background-color: #7f1d1d !important; }
    .stWarning { background-color: #78350f !important; }
    .stInfo { background-color: #1e3a5f !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# INITIALIZATION (runs once per cold start)
# ─────────────────────────────────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    initialize_database()
    seed_demo_data()
    st.session_state["db_initialized"] = True

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "user_profile" not in st.session_state:
    st.session_state["user_profile"] = None

if "page" not in st.session_state:
    st.session_state["page"] = "login"

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN / FORGOT PASSWORD PAGE
# ─────────────────────────────────────────────────────────────────────────────
def render_login_page():
    """Renders the login form and credentials reference panel."""
    col_empty, col_main, col_empty2 = st.columns([1, 2, 1])
    
    with col_main:
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0 1rem 0;'>
            <h1>🏫 Karnataka School Monitoring</h1>
            <p style='color: #94a3b8; font-size: 1.1rem;'>
                Smart Government School Monitoring and Early-Warning System
            </p>
            <p style='color: #64748b; font-size: 0.9rem;'>
                Better Schools. Smarter Decisions. Stronger Communities.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Toggle: Login vs. Forgot Password
        page_mode = st.radio("Select Action", ["Login", "Reset Password"], horizontal=True, label_visibility="collapsed")
        
        if page_mode == "Login":
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Sign In", use_container_width=True)
                
            if submit:
                if not username.strip() or not password.strip():
                    st.error("Please enter both username and password.")
                else:
                    user = authenticate_user(username.strip(), password.strip())
                    if user:
                        st.session_state["user_profile"] = user
                        st.session_state["page"] = "dashboard"
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")
        else:
            # Password Reset Form
            with st.form("reset_form"):
                r_username = st.text_input("Username")
                r_new_pass = st.text_input("New Password", type="password")
                r_confirm  = st.text_input("Confirm New Password", type="password")
                r_submit   = st.form_submit_button("Reset Password", use_container_width=True)
                
            if r_submit:
                if r_new_pass != r_confirm:
                    st.error("Passwords do not match.")
                elif len(r_new_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success = reset_user_password(r_username.strip(), r_new_pass)
                    if success:
                        st.success("Password reset successful! You can now log in with your new password.")
                    else:
                        st.error("Username not found. Please check and try again.")

        # Demo Credentials Panel
        st.markdown("---")
        with st.expander("📋 Demo Credentials (Click to expand)", expanded=False):
            st.markdown("""
| Role | Username | Password |
|------|----------|----------|
| **Headmaster** | `headmaster_rampura` | `Head@123` |
| **Headmaster** | `headmaster_sagar` | `Head@456` |
| **Headmaster** | `headmaster_mudigere` | `Head@789` |
| **Student Representative** | `student_rampura` | `Stu@123` |
| **Student Representative** | `student_sagar` | `Stu@456` |
| **Village Volunteer** | `volunteer_rampura` | `Vol@123` |
| **Village Volunteer** | `volunteer_sagar` | `Vol@456` |
| **District Officer** | `officer_shivamogga` | `Off@123` |
| **State Official** | `officer_state` | `State@123` |
""")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION (shown only when logged in)
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar(user_profile: dict):
    """Renders the navigation sidebar with user profile info and logout."""
    with st.sidebar:
        st.markdown(f"""
        <div style='padding: 1rem 0;'>
            <div style='font-size: 1.1rem; font-weight: bold; color: #f1f5f9;'>
                👤 {user_profile['username']}
            </div>
            <div style='color: #94a3b8; font-size: 0.85rem; margin-top: 0.25rem;'>
                🎭 {user_profile['role']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Contextual location info
        if user_profile.get("district"):
            st.markdown(f"📍 **District:** {user_profile['district']}")
        if user_profile.get("taluk"):
            st.markdown(f"📍 **Taluk:** {user_profile['taluk']}")
        if user_profile.get("village"):
            st.markdown(f"📍 **Village:** {user_profile['village']}")
            
        st.markdown("---")
        st.markdown("### 🗂️ Navigation")
        
        # Role-based navigation options
        role = user_profile["role"]
        if role in ["Headmaster", "Student Representative", "Village Volunteer"]:
            if st.button("🏫 School Dashboard", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()
        elif role == "Taluk Education Officer":
            if st.button("🏛️ Taluk Dashboard", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()
        elif role == "District Education Officer":
            if st.button("🏛️ District Dashboard", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()
        elif role in ["State Education Department Official", "System Administrator"]:
            if st.button("🏛️ State Dashboard", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["user_profile"] = None
            st.session_state["page"] = "login"
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style='color: #475569; font-size: 0.75rem; text-align: center;'>
            Karnataka School Monitor v1.0<br>
            Prototype · Demo Data Only
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTING CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────
def main():
    user_profile = st.session_state.get("user_profile")

    if not user_profile or st.session_state.get("page") == "login":
        render_login_page()
        return

    # Render sidebar navigation
    render_sidebar(user_profile)

    # Route to the appropriate dashboard based on role
    role = user_profile["role"]

    if role in ["Headmaster", "Student Representative", "Village Volunteer"]:
        render_school_dashboard(user_profile)

    elif role == "Taluk Education Officer":
        render_taluk_dashboard(user_profile)

    elif role == "District Education Officer":
        render_district_dashboard(user_profile)

    elif role == "State Education Department Official":
        render_state_dashboard(user_profile)

    elif role == "System Administrator":
        render_admin_dashboard(user_profile)

    else:
        st.error(f"No dashboard configured for role: **{role}**")
        st.info("Please contact the System Administrator.")


if __name__ == "__main__":
    main()
