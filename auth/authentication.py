"""
auth/authentication.py
----------------------
Handles secure user authentication and session password hashing.
Implements PBKDF2-HMAC-SHA256 with 100,000 iterations to protect passwords.
"""
import hashlib
import hmac
import os
from database.connection import execute_query

def hash_password(password: str) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Returns: (password_hash_hex, salt_hex)
    """
    salt = os.urandom(16)
    pwd_bytes = password.encode('utf-8')
    h = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt, 100000)
    return h.hex(), salt.hex()

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verifies a password against a stored PBKDF2 hash and salt.
    """
    pwd_bytes = password.encode('utf-8')
    salt_bytes = bytes.fromhex(salt)
    h = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
    return hmac.compare_digest(h.hex(), password_hash)

def authenticate_user(username: str, password: str) -> dict or None:
    """
    Checks the username and password in the database.
    Returns the user data dictionary if successful, or None.
    """
    user = execute_query(
        """
        SELECT id, username, password_hash, salt, role, school_id, district, taluk, village 
        FROM users WHERE username = ?;
        """,
        (username,),
        fetch="one"
    )
    if not user:
        return None
    
    if verify_password(password, user["password_hash"], user["salt"]):
        # Clean dictionary representation of user profile (excluding hash and salt)
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "school_id": user["school_id"],
            "district": user["district"],
            "taluk": user["taluk"],
            "village": user["village"]
        }
    return None

def reset_user_password(username: str, new_password: str) -> bool:
    """
    Resets the password of the specified user.
    """
    user = execute_query("SELECT id FROM users WHERE username = ?;", (username,), fetch="one")
    if not user:
        return False
    
    new_hash, new_salt = hash_password(new_password)
    rows_affected = execute_query(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?;",
        (new_hash, new_salt, username),
        fetch="rowcount"
    )
    return rows_affected > 0
