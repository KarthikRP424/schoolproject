# 🏫 Smart Government School Monitoring and Early-Warning System for Karnataka

**Better Schools. Smarter Decisions. Stronger Communities.**

A production-quality prototype capstone project that digitises the end-to-end school issue lifecycle for the Karnataka State Education Department.

---

## 🗺️ System Overview

```
Report → Evidence → Verification → Priority → Assignment
       → Inspection → Action → Student Verification → Closure → Analytics
```

The platform connects **school-level reporters** (Headmasters, Students, Volunteers) with **district and state officers** through a single persistent monitoring dashboard backed by a local SQLite database.

---

## 👥 Demo Credentials

| Role | Username | Password | Scope |
|------|----------|----------|-------|
| **Headmaster** | `headmaster_rampura` | `Head@123` | GHPS Rampura, Shivamogga |
| **Headmaster** | `headmaster_sagar` | `Head@456` | GHS Sagar, Shivamogga |
| **Headmaster** | `headmaster_mudigere` | `Head@789` | GHS Mudigere, Chikkamagaluru |
| **Student Representative** | `student_rampura` | `Stu@123` | GHPS Rampura |
| **Student Representative** | `student_sagar` | `Stu@456` | GHS Sagar |
| **Village Volunteer** | `volunteer_rampura` | `Vol@123` | Rampura Village |
| **Village Volunteer** | `volunteer_sagar` | `Vol@456` | Sagar Village |
| **District Education Officer** | `officer_shivamogga` | `Off@123` | Shivamogga District |
| **State Official** | `officer_state` | `State@123` | All Karnataka |

> ⚠️ These are **synthetic demo credentials** for prototype use only. No real personal data is stored.

---

## 🚀 How to Run Locally

### Prerequisites

- Python 3.9+ (tested on Python 3.11)
- pip

### Setup

```bash
# Clone or download the project folder
cd schoolproject

# Install dependencies (no virtual environment required for demo)
pip install -r requirements.txt

# Run the app
python -m streamlit run app.py
```

The app will open automatically at **http://localhost:8501**

---

## 🌐 How to Share the App

### Method 1 — Share on the Same Wi-Fi Network

Run the server so it listens on all network interfaces:

```bash
python -m streamlit run app.py --server.address 0.0.0.0
```

Then find your laptop's local IP address:

```powershell
ipconfig
# Look for: IPv4 Address e.g. 192.168.1.5
```

Anyone on the **same Wi-Fi** can open:

```
http://YOUR-LAPTOP-IP:8501
```

Example: `http://192.168.1.5:8501`

> ⚠️ **Important:** `localhost` only works on the computer running the app.  
> Other devices must use your laptop's IP address.

---

### Method 2 — Public Deployment via Streamlit Community Cloud

1. Push this project to a **GitHub repository**
2. Go to [https://streamlit.io/cloud](https://streamlit.io/cloud)
3. Click **New App**
4. Select your **GitHub repository**
5. Set the **main file** to `app.py`
6. Click **Deploy**
7. Share the generated public `*.streamlit.app` link

> The SQLite database file (`school_monitoring.db`) will be created on first run and seeded automatically with all demo data.

---

## 🏗️ Project Architecture

```
schoolproject/
├── app.py                          # Main entrypoint & routing
├── config.py                       # Constants, SLA hours, weights
├── requirements.txt
│
├── database/
│   ├── connection.py               # SQLite context manager (row_factory)
│   ├── models.py                   # 13-table schema + initialize_database()
│   └── seed.py                     # Idempotent seeder with scenarios A–H
│
├── auth/
│   ├── authentication.py           # PBKDF2-HMAC-SHA256 login & reset
│   └── permissions.py              # RBAC scope filter SQL builders
│
├── services/
│   ├── issue_service.py            # CRUD, duplicate detection, workflow graph
│   ├── verification_service.py     # Confidence scoring, conflict detection
│   ├── priority_engine.py          # Health, Priority, Decline Risk scores
│   ├── notification_service.py     # In-app alert delivery
│   ├── inspection_service.py       # Inspection logs & Student 3/5 Consensus
│   ├── sla_service.py              # SLA tracking & auto-escalation engine
│   └── audit_service.py            # Immutable audit trail
│
├── components/
│   ├── charts.py                   # Enrollment, attendance, score trends
│   ├── maps.py                     # Priority RGBA coloured coordinate maps
│   └── timelines.py                # Issue lifecycle & audit visualisers
│
├── dashboards/
│   ├── school.py                   # Headmaster / Student Rep / Volunteer view
│   ├── district.py                 # District Education Officer view
│   ├── taluk.py                    # Taluk Education Officer view
│   ├── state.py                    # State-level analytics command centre
│   └── admin.py                    # System Administrator panel & safe DB reset
│
├── tests/
│   └── test_flow.py                # 12 automated tests (DB, auth, SLA, consensus)
│
└── data/
    └── sample_reports.csv          # Legacy sample data
```

---

## 🔐 Security Design

| Feature | Implementation |
|---------|---------------|
| Password hashing | PBKDF2-HMAC-SHA256, 100,000 iterations, unique 16-byte salt per user |
| Credential comparison | `hmac.compare_digest()` — timing-attack resistant |
| No external auth service | 100% Python stdlib (`hashlib`, `hmac`, `os.urandom`) |
| Role-Based Access Control | SQL `WHERE` clauses scoped per role at query time |
| Audit trail | Immutable `audit_logs` table — every status change logged |
| No API keys | Zero external credentials required |

---

## 📊 Scoring Engines

### Priority Score (0–100)
| Component | Weight |
|-----------|--------|
| Teacher Shortage | 25% |
| Infrastructure Condition | 25% |
| Basic Facilities (water/toilets) | 20% |
| Enrollment Decline | 15% |
| Unresolved Open Issues | 15% |

**Levels:** LOW → MODERATE → HIGH → CRITICAL → EMERGENCY

### Verification Confidence (0–100)
| Role | Weight |
|------|--------|
| Headmaster confirmation | 30% |
| Student Representative | 30% |
| Village Volunteer | 20% |
| Photo + GPS Evidence | 20% |

**Conflict detection:** If any role confirms while another denies → 30-point penalty + District Officer alert.

### School Decline Risk (0–100%)
| Indicator | Weight |
|-----------|--------|
| Multi-year enrollment drop | 40% |
| Attendance below 85% | 30% |
| Teacher vacancy | 20% |
| Unresolved complaints | 10% |

---

## 🗄️ Pre-Seeded Demo Scenarios

| ID | Scenario | Status |
|----|----------|--------|
| A | Toilet blockage → Verified → Repaired → **Student Approved** (Closed) | ✅ Closed |
| B | Drinking water dispute → **Conflict Detected** (HM vs. Students) | ⚠️ Inspection Required |
| C | Unsafe ceiling cracks → **Emergency** (24h SLA) | 🛑 Pending |
| D | GHS Sagar declining enrolment → **Early Warning Alert** | 📉 Monitoring |
| F | Duplicate infrastructure report detected | 🔁 Under Review |
| G | Electricity outage → **SLA Expired** → Escalated | ⏰ Escalated |
| H | Action marked complete → **Student rejects** closure | ❌ Reopened |

---

## 🔬 Running Tests

```bash
python -m unittest tests/test_flow.py -v
```

Expected output: **12/12 tests pass** covering database initialization, PBKDF2 hashing, authentication, password reset, priority scoring, decline risk, SLA escalation, 3/5 student consensus, duplicate merging, and workflow transition graphs.

---

## 📍 Karnataka Geography Covered

| District | Taluks | Schools |
|----------|--------|---------|
| Shivamogga | Bhadravathi, Sagar, Soraba | 8 schools |
| Chikkamagaluru | Koppa, Mudigere, Tarikere | 6 schools |
| Hassan | Belur, Arsikere, Sakleshpur | 6 schools |

**Total:** 20 schools · 15 demo users · 6 pre-seeded issue scenarios

---

## 🎓 Interview Discussion Points

This prototype demonstrates:

- **Database design** — normalised 13-table SQLite schema with FK constraints
- **RBAC** — role-scoped SQL queries dynamically built per login session
- **Service-layer architecture** — business logic cleanly separated from UI
- **Decision logic** — rule-based AI agent + weighted scoring engines
- **Auditability** — immutable audit log trail on every state change
- **Analytics** — health scores, decline risk, budget allocation calculator
- **Security** — PBKDF2-HMAC-SHA256 without external auth dependencies
