#!/usr/bin/env python
"""
Initialize database with default admin user and test data
"""

import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import get_password_hash, generate_api_key
from app.db.connection import execute_query, execute_transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user():
    """Create default admin user if none exists"""
    logger.info("Checking for existing admin user...")

    # Check if admin user exists
    check_query = """
    SELECT id FROM users WHERE is_superuser = TRUE LIMIT 1
    """
    admin = execute_query(check_query, single=True)

    if admin:
        logger.info(f"Admin user already exists with ID: {admin['id']}")
        return

    logger.info("Creating admin user...")

    # Create admin user
    hashed_password = get_password_hash("admin123")

    query = """
    INSERT INTO users (
        email, hashed_password, full_name, is_active, is_superuser
    ) VALUES (
        'admin@example.com', %s, 'System Administrator', TRUE, TRUE
    ) RETURNING id
    """

    admin = execute_query(query, (hashed_password,), single=True)

    logger.info(f"Admin user created with ID: {admin['id']}")


def create_test_merchant():
    """Create a test merchant if none exists"""
    logger.info("Checking for existing merchants...")

    # Check if any merchant exists
    check_query = """
    SELECT id FROM merchants LIMIT 1
    """
    merchant = execute_query(check_query, single=True)

    if merchant:
        logger.info(f"Test merchant already exists with ID: {merchant['id']}")
        return

    logger.info("Creating test merchant...")

    # Create test merchant user
    hashed_password = get_password_hash("merchant123")

    user_query = """
    INSERT INTO users (
        email, hashed_password, full_name, is_active, is_superuser
    ) VALUES (
        'merchant@example.com', %s, 'Test Merchant', TRUE, FALSE
    ) RETURNING id
    """

    user = execute_query(user_query, (hashed_password,), single=True)

    # Generate API key
    api_key = generate_api_key()

    # Create merchant
    merchant_query = """
    INSERT INTO merchants (
        user_id, business_name, business_type, contact_phone, address,
        api_key, callback_url, is_active, min_deposit, max_deposit,
        min_withdrawal, max_withdrawal
    ) VALUES (
        %s, 'Test Merchant', 'E-commerce', '1234567890', '123 Test St, Test City',
        %s, 'https://example.com/callback', TRUE, 500, 300000, 1000, 1000000
    ) RETURNING id
    """

    merchant = execute_query(merchant_query, (user["id"], api_key), single=True)

    # Create bank detail
    bank_query = """
    INSERT INTO merchant_bank_details (
        merchant_id, bank_name, account_name, account_number, ifsc_code, is_active
    ) VALUES (
        %s, 'Test Bank', 'Test Merchant', '1234567890', 'TEST0001234', TRUE
    )
    """

    execute_query(bank_query, (merchant["id"],), fetch=False)

    # Create UPI detail
    upi_query = """
    INSERT INTO merchant_upi_details (
        merchant_id, upi_id, name, is_active
    ) VALUES (
        %s, 'test@upi', 'Test Merchant', TRUE
    )
    """

    execute_query(upi_query, (merchant["id"],), fetch=False)

    # Add IP to whitelist
    ip_query = """
    INSERT INTO ip_whitelist (
        merchant_id, ip_address, description
    ) VALUES (
        %s, '0.0.0.0', 'All IPs (for testing)'
    )
    """

    execute_query(ip_query, (merchant["id"],), fetch=False)

    logger.info(f"Test merchant created with ID: {merchant['id']}")
    logger.info(f"API Key: {api_key}")


def main():
    """Main function to initialize the database"""
    logger.info("Initializing database...")

    try:
        create_admin_user()
        create_test_merchant()

        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()