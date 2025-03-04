"""
SQL queries for authentication operations
"""

# Get user by email
GET_USER_BY_EMAIL = """
SELECT 
    id, email, hashed_password, full_name, is_active, is_superuser
FROM 
    users
WHERE 
    email = %s
"""

# Get user by ID
GET_USER_BY_ID = """
SELECT 
    id, email, full_name, is_active, is_superuser, created_at, updated_at
FROM 
    users
WHERE 
    id = %s
"""

# Create user
CREATE_USER = """
INSERT INTO users (
    email, hashed_password, full_name, is_active, is_superuser
) VALUES (
    %s, %s, %s, %s, %s
) RETURNING id, email, full_name, is_active, is_superuser, created_at, updated_at
"""

# Check if email exists
CHECK_EMAIL_EXISTS = """
SELECT id FROM users WHERE email = %s
"""

# Check if email exists for another user
CHECK_EMAIL_EXISTS_OTHER = """
SELECT id FROM users WHERE email = %s AND id != %s
"""

# Update user
UPDATE_USER = """
UPDATE users
SET {fields}, updated_at = NOW()
WHERE id = %s
RETURNING id, email, full_name, is_active, is_superuser, created_at, updated_at
"""

# Delete user
DELETE_USER = """
DELETE FROM users
WHERE id = %s
"""

# Check if user associated with merchant
CHECK_USER_MERCHANT = """
SELECT id FROM merchants WHERE user_id = %s
"""

# Get user password
GET_USER_PASSWORD = """
SELECT 
    hashed_password
FROM 
    users
WHERE 
    id = %s
"""

# Update user password
UPDATE_USER_PASSWORD = """
UPDATE users
SET 
    hashed_password = %s,
    updated_at = NOW()
WHERE 
    id = %s
"""

# Get all users
GET_USERS = """
SELECT 
    id, email, full_name, is_active, is_superuser, created_at, updated_at
FROM 
    users
ORDER BY 
    created_at DESC
LIMIT %s OFFSET %s
"""