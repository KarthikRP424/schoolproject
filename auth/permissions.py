"""
auth/permissions.py
-------------------
Role-Based Access Control (RBAC) permission scoping utilities.
Restricts database queries based on user scopes (School, Village, Taluk, District, State).
"""

def get_user_scope_filter(user_profile: dict, table_alias: str = "") -> tuple[str, list]:
    """
    Returns a SQL WHERE clause fragment and the corresponding parameter list 
    to enforce geographical and administrative permission boundaries.
    
    Parameters:
      - user_profile (dict): The logged-in user details.
      - table_alias (str): Optional table prefix (e.g. 's.' or 'i.') for SQL joins.
      
    Returns:
      - tuple: (where_clause_sql_string, parameters_list)
    """
    role = user_profile.get("role")
    prefix = f"{table_alias}." if table_alias else ""
    
    # State Officers and Admins have unrestricted access
    if role in ["State Education Department Official", "System Administrator"]:
        return "1=1", []
        
    # District Officers: filter by district (resides in schools table)
    elif role == "District Education Officer":
        district = user_profile.get("district")
        sch_prefix = "s." if table_alias == "i" else prefix
        return f"{sch_prefix}district = ?", [district]
        
    # Taluk Officers: filter by district and taluk (resides in schools table)
    elif role == "Taluk Education Officer":
        district = user_profile.get("district")
        taluk = user_profile.get("taluk")
        sch_prefix = "s." if table_alias == "i" else prefix
        return f"{sch_prefix}district = ? AND {sch_prefix}taluk = ?", [district, taluk]
        
    # Village Volunteers: filter by village (resides in schools table)
    elif role == "Village Volunteer":
        village = user_profile.get("village")
        sch_prefix = "s." if table_alias == "i" else prefix
        return f"{sch_prefix}village = ?", [village]
        
    # Headmasters and Student Representatives: filter by specific school ID
    elif role in ["Headmaster", "Student Representative"]:
        school_id = user_profile.get("school_id")
        # Handle schools table vs issues table columns
        col_name = "id" if table_alias in ["schools", "s"] or not table_alias else "school_id"
        return f"{prefix}{col_name} = ?", [school_id]
        
    # Unrecognized roles have no permissions
    return "1=0", []
