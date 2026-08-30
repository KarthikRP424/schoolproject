"""
Quick end-to-end smoke test to validate all core flows work correctly.
Run: python e2e_test.py
"""
from auth.authentication import authenticate_user
from services.issue_service import get_filtered_issues
from services.priority_engine import calculate_school_priority, calculate_school_health, calculate_school_decline_risk
from database.connection import execute_query

errors = []

# ── 1. Login tests ────────────────────────────────────────────────────────────
print("--- LOGIN TESTS ---")
test_accounts = [
    ("headmaster_rampura",  "Head@123",  "Headmaster"),
    ("student_rampura",     "Stu@123",   "Student Representative"),
    ("volunteer_rampura",   "Vol@123",   "Village Volunteer"),
    ("officer_shivamogga",  "Off@123",   "District Education Officer"),
    ("officer_state",       "State@123", "State Education Department Official"),
]
for uname, pwd, expected_role in test_accounts:
    u = authenticate_user(uname, pwd)
    if u and u["role"] == expected_role:
        print(f"  PASS  {uname:28s} -> {u['role']}")
    else:
        print(f"  FAIL  {uname}")
        errors.append(f"Login failed: {uname}")

# ── 2. Wrong password ────────────────────────────────────────────────────────
print()
print("--- WRONG PASSWORD TEST ---")
bad = authenticate_user("headmaster_rampura", "WrongPassword")
if bad is None:
    print("  PASS  Wrong password correctly rejected")
else:
    print("  FAIL  Wrong password was accepted!")
    errors.append("Wrong password accepted")

# ── 3. Issue filtering per role ───────────────────────────────────────────────
print()
print("--- ISSUE SCOPE FILTER TESTS ---")
dist_user  = authenticate_user("officer_shivamogga", "Off@123")
state_user = authenticate_user("officer_state",      "State@123")
hm_user    = authenticate_user("headmaster_rampura", "Head@123")

dist_issues  = get_filtered_issues(dist_user)
state_issues = get_filtered_issues(state_user)
hm_issues    = get_filtered_issues(hm_user)

print(f"  District officer (Shivamogga) sees: {len(dist_issues)} issues")
print(f"  State officer sees:                 {len(state_issues)} issues")
print(f"  Headmaster (Rampura) sees:          {len(hm_issues)} issues")

if len(state_issues) >= len(dist_issues):
    print("  PASS  State >= District scope")
else:
    print("  FAIL  State scope less than District scope!")
    errors.append("Scope filter incorrect")

if len(hm_issues) <= len(dist_issues):
    print("  PASS  Headmaster <= District scope")
else:
    print("  FAIL  Headmaster scope wider than District!")
    errors.append("Headmaster scope too wide")

# ── 4. Priority engine ────────────────────────────────────────────────────────
print()
print("--- PRIORITY ENGINE ---")
schools = execute_query(
    "SELECT id, name, priority_level FROM schools ORDER BY priority_score DESC LIMIT 5;"
)
for s in schools:
    h = calculate_school_health(s["id"])
    p = calculate_school_priority(s["id"])
    r = calculate_school_decline_risk(s["id"])
    name = s["name"][:42]
    print(f"  {name:42s} | {p['level']:9s} | Health:{h['score']:5.1f} | Risk:{r['percentage']:5.1f}%")

# ── 5. Seed integrity ─────────────────────────────────────────────────────────
print()
print("--- DATABASE INTEGRITY ---")
counts = {
    "schools":       execute_query("SELECT COUNT(*) as c FROM schools;",      fetch="one")["c"],
    "users":         execute_query("SELECT COUNT(*) as c FROM users;",         fetch="one")["c"],
    "issues":        execute_query("SELECT COUNT(*) as c FROM issues;",        fetch="one")["c"],
    "notifications": execute_query("SELECT COUNT(*) as c FROM notifications;", fetch="one")["c"],
    "audit_logs":    execute_query("SELECT COUNT(*) as c FROM audit_logs;",    fetch="one")["c"],
}
for table, count in counts.items():
    status = "PASS" if count > 0 else "FAIL"
    print(f"  {status}  {table:16s}: {count} rows")
    if count == 0:
        errors.append(f"Empty table: {table}")

# == Summary ===================================================================
print()
if errors:
    print(f"FAILED - {len(errors)} error(s):")
    for e in errors:
        print(f"  [X] {e}")
    exit(1)
else:
    print("ALL END-TO-END TESTS PASSED [OK]")
