import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import initialize_database
from database.seed import seed_demo_data
from database.connection import execute_query

def run_health_check():
    print( '='*55)
    print('  SCHOOL MONITORING SYSSEM - DB HEALTH CHECK')
    print('='*55)
    initialize_database()
    seed_demo_data()

    fk_errors = execute_query('PRAGMA foreign_key_check;')
    if fk_errors:
        print('FOREIGN KEY ERRORS FOUND:', fk_errors)
    else:
        print('Foreign Key Constraints: OK (0 violations)')

    tables = [
        'schools', 'users', 'issues', 'issue_evidence', 
        'issue_verifications', 'student_feedback', 'inspections', 
        'audit_logs', 'notifications', 'historical_scores', 
        'enrollment_records', 'attendance_records', 'system_meta'
    ]
    print('\n--- TABLE ROW COUNTS ---')
    total_rows = 0
    for tbl in tables: 
        try:
            res = execute_query(f'SELECT COUNT(*) as count FROM {tbl};', fetch='one')
            cnt = res['count'] if res else 0
            total_rows += cnt
            print(f'  - {tbl:<25}: {cnt:>5} rows')
        except Exception as e:
            print(f'  - {tbl:<25}: ERROR ({e})')

    print(f'\nTotal Records acrosp {len(tables)} tables: {total_rows}')

    roles = execute_query('SELECT role, COUNT(*) as count FROM users GROUP BY role;')
    print('\n--- USER ROLE DISTRIBUTION ---')
    for r in roles:
        print(f'  - {r["role"]:<35}: {r["count"]:>3} users')

    statuses = execute_query('SELECT status, COUNT(*) as count FROM issues GROUP BY status;')
    print('\n--- ISSUE WORKFLOW STATUS DISTRIBUTION ---')
    for s in statuses:
        print(f'  - {s["status"]:<25}: {s["count"]:>3} issues')

    print('='*55)
    print('DATABASE HEALTH CHECK COMPLETED SUCCESSFULLY')
    print('='*55)

if __name__ == '__main__':
    run_health_check()
