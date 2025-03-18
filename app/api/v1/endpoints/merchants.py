from fastapi import APIRouter, Depends, HTTPException, Request, status, Body, Query
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, timedelta

from app.core.security import get_api_key_merchant
from app.db.connection import execute_query

router = APIRouter()


@router.get("/profile")
async def get_merchant_profile(
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Get merchant profile
    """
    try:
        # Get merchant details
        query = """
        SELECT 
            m.id, m.business_name, m.business_type, m.contact_phone,
            m.callback_url, m.min_deposit, m.max_deposit,
            m.min_withdrawal, m.max_withdrawal, m.commission_rate,
            u.email, u.full_name
        FROM 
            merchants m
        JOIN 
            users u ON m.user_id = u.id
        WHERE 
            m.id = %s
        """

        merchant_details = execute_query(query, (merchant["id"],), single=True)

        # Get bank details
        bank_query = """
        SELECT 
            id, bank_name, account_name, account_number, ifsc_code, is_active
        FROM 
            merchant_bank_details
        WHERE 
            merchant_id = %s AND is_active = TRUE
        """

        bank_details = execute_query(bank_query, (merchant["id"],))

        # Get UPI details
        upi_query = """
        SELECT 
            id, upi_id, name, is_active
        FROM 
            merchant_upi_details
        WHERE 
            merchant_id = %s AND is_active = TRUE
        """

        upi_details = execute_query(upi_query, (merchant["id"],))

        # Format response
        result = {
            "id": merchant_details["id"],
            "business_name": merchant_details["business_name"],
            "business_type": merchant_details["business_type"],
            "contact_phone": merchant_details["contact_phone"],
            "email": merchant_details["email"],
            "full_name": merchant_details["full_name"],
            "callback_url": merchant_details["callback_url"],
            "min_deposit": merchant_details["min_deposit"],
            "max_deposit": merchant_details["max_deposit"],
            "min_withdrawal": merchant_details["min_withdrawal"],
            "max_withdrawal": merchant_details["max_withdrawal"],
            "commission_rate": float(merchant_details["commission_rate"]),
            "bank_details": bank_details,
            "upi_details": upi_details
        }

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving merchant profile: {str(e)}"
        )


@router.put("/update-profile")
async def update_merchant_profile(
        profile_data: Dict[str, Any] = Body(...),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Update merchant profile
    """
    try:
        # Fields that can be updated
        allowed_fields = [
            "business_name", "business_type", "contact_phone",
            "callback_url"
        ]

        # Build update fields
        fields = []
        params = []

        for field in allowed_fields:
            if field in profile_data:
                fields.append(f"{field} = %s")
                params.append(profile_data[field])

        # If no fields to update, return current profile
        if not fields:
            return await get_merchant_profile(merchant)

        # Build update query
        update_query = f"""
        UPDATE merchants
        SET {", ".join(fields)}, updated_at = NOW()
        WHERE id = %s
        """

        params.append(merchant["id"])

        # Execute update
        execute_query(update_query, tuple(params), fetch=False)

        # Return updated profile
        return await get_merchant_profile(merchant)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating merchant profile: {str(e)}"
        )


@router.post("/change-password")
async def change_merchant_password(
        current_password: str = Body(...),
        new_password: str = Body(...),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Change merchant user password
    """
    try:
        from app.core.security import get_password_hash, verify_password

        # Get user ID for this merchant
        query = """
        SELECT user_id FROM merchants WHERE id = %s
        """

        result = execute_query(query, (merchant["id"],), single=True)
        user_id = result["user_id"]

        # Verify current password
        check_query = """
        SELECT hashed_password FROM users WHERE id = %s
        """

        user = execute_query(check_query, (user_id,), single=True)

        if not verify_password(current_password, user["hashed_password"]):
            raise ValueError("Current password is incorrect")

        # Update password
        hashed_password = get_password_hash(new_password)

        update_query = """
        UPDATE users
        SET hashed_password = %s, updated_at = NOW()
        WHERE id = %s
        """

        execute_query(update_query, (hashed_password, user_id), fetch=False)

        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )


@router.get("/commission-report")
async def get_merchant_commission_report(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """Get merchant's commission report"""
    try:
        query_params = [merchant["id"]]
        filters = ""

        # Base query
        query = """
        SELECT 
            tf.id, tf.payment_id, p.reference, p.payment_type,
            tf.original_amount, tf.commission_rate, tf.fee_amount, 
            tf.final_amount, tf.created_at
        FROM 
            transaction_fees tf
        JOIN
            payments p ON tf.payment_id = p.id
        WHERE 
            tf.merchant_id = %s
        """

        # Add filters
        if start_date:
            filters += " AND tf.created_at >= %s"
            query_params.append(start_date)

        if end_date:
            filters += " AND tf.created_at <= %s"
            query_params.append(end_date)

        # Add filters and order by
        query += filters + " ORDER BY tf.created_at DESC"

        # Execute query
        commissions = execute_query(query, tuple(query_params))

        # Calculate totals
        total_query = """
        SELECT 
            SUM(tf.original_amount) as total_amount,
            SUM(tf.fee_amount) as total_fees,
            SUM(tf.final_amount) as total_final
        FROM 
            transaction_fees tf
        WHERE 
            tf.merchant_id = %s
        """ + filters

        totals = execute_query(total_query, tuple(query_params), single=True)

        # Get current commission rate
        rate_query = """
        SELECT commission_rate FROM merchants WHERE id = %s
        """
        rate_result = execute_query(rate_query, (merchant["id"],), single=True)

        return {
            "commission_rate": float(rate_result["commission_rate"]),
            "transactions": commissions,
            "summary": {
                "total_original_amount": totals["total_amount"] or 0,
                "total_fees_deducted": totals["total_fees"] or 0,
                "total_final_amount": totals["total_final"] or 0,
                "count": len(commissions)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving commission report: {str(e)}"
        )


@router.get("/all-upi-details")
async def get_all_merchant_upi_details(
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Get all UPI details for merchant (active and inactive)
    """
    try:
        # Get UPI details
        upi_query = """
        SELECT 
            id, upi_id, name, is_active
        FROM 
            merchant_upi_details
        WHERE 
            merchant_id = %s
        ORDER BY
            is_active DESC, created_at DESC
        """

        upi_details = execute_query(upi_query, (merchant["id"],))

        return {
            "upi_details": upi_details
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving UPI details: {str(e)}"
        )


@router.post("/update-upi-details")
async def update_merchant_upi_details(
        upi_details: List[Dict[str, Any]] = Body(...),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Update UPI details - only one can be active at a time
    """
    try:
        # First, deactivate all UPI details
        deactivate_query = """
        UPDATE merchant_upi_details
        SET is_active = FALSE
        WHERE merchant_id = %s
        """

        execute_query(deactivate_query, (merchant["id"],), fetch=False)

        # Then update or insert new UPI details
        for upi in upi_details:
            if "id" in upi and upi["id"]:
                # Update existing UPI detail
                update_query = """
                UPDATE merchant_upi_details
                SET 
                    upi_id = %s,
                    name = %s,
                    is_active = %s
                WHERE 
                    id = %s AND merchant_id = %s
                """

                update_params = (
                    upi.get("upi_id"),
                    upi.get("name"),
                    upi.get("is_active", False),
                    upi["id"],
                    merchant["id"]
                )

                execute_query(update_query, update_params, fetch=False)
            else:
                # Insert new UPI detail
                insert_query = """
                INSERT INTO merchant_upi_details (
                    merchant_id, upi_id, name, is_active
                ) VALUES (
                    %s, %s, %s, %s
                )
                """

                insert_params = (
                    merchant["id"],
                    upi.get("upi_id"),
                    upi.get("name"),
                    upi.get("is_active", False)
                )

                execute_query(insert_query, insert_params, fetch=False)

        # Get updated UPI details
        return await get_all_merchant_upi_details(merchant)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating UPI details: {str(e)}"
        )

# import logging
# from typing import Dict, Any, List, Optional
# import uuid
#
# from app.core.security import get_password_hash
# from app.db.connection import execute_query
# from app.services.merchant_service import get_merchants, get_merchant_details, create_merchant, update_merchant, \
#     regenerate_api_key
#
# logger = logging.getLogger(__name__)
#
#
# def get_users(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
#     """
#     Get all users
#
#     Parameters:
#     - skip: Number of records to skip
#     - limit: Maximum number of records to return
#
#     Returns:
#     - List of users
#     """
#     query = """
#     SELECT
#         id, email, full_name, is_active, is_superuser, created_at, updated_at
#     FROM
#         users
#     ORDER BY
#         created_at DESC
#     LIMIT %s OFFSET %s
#     """
#
#     users = execute_query(query, (limit, skip))
#
#     return users
#
#
# def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Create a new user
#
#     Parameters:
#     - user_data: User data
#
#     Returns:
#     - Created user
#     """
#     # Check if email already exists
#     check_query = """
#     SELECT id FROM users WHERE email = %s
#     """
#
#     existing_user = execute_query(check_query, (user_data.get("email"),), single=True)
#
#     if existing_user:
#         raise ValueError("Email already exists")
#
#     # Hash password
#     password = user_data.get("password")
#     if not password:
#         raise ValueError("Password is required")
#
#     hashed_password = get_password_hash(password)
#
#     # Build query
#     query = """
#     INSERT INTO users (
#         email, hashed_password, full_name, is_active, is_superuser
#     ) VALUES (
#         %s, %s, %s, %s, %s
#     ) RETURNING id, email, full_name, is_active, is_superuser, created_at, updated_at
#     """
#
#     params = (
#         user_data.get("email"),
#         hashed_password,
#         user_data.get("full_name"),
#         user_data.get("is_active", True),
#         user_data.get("is_superuser", False)
#     )
#
#     user = execute_query(query, params, single=True)
#
#     return user
#
#
# def update_user(user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Update an existing user
#
#     Parameters:
#     - user_id: User ID
#     - user_data: User data
#
#     Returns:
#     - Updated user
#     """
#     # Build update fields
#     fields = []
#     params = []
#
#     if "email" in user_data:
#         # Check if email already exists for another user
#         check_query = """
#         SELECT id FROM users WHERE email = %s AND id != %s
#         """
#
#         existing_user = execute_query(
#             check_query,
#             (user_data["email"], user_id),
#             single=True
#         )
#
#         if existing_user:
#             raise ValueError("Email already exists")
#
#         fields.append("email = %s")
#         params.append(user_data["email"])
#
#     if "full_name" in user_data:
#         fields.append("full_name = %s")
#         params.append(user_data["full_name"])
#
#     if "is_active" in user_data:
#         fields.append("is_active = %s")
#         params.append(user_data["is_active"])
#
#     if "is_superuser" in user_data:
#         fields.append("is_superuser = %s")
#         params.append(user_data["is_superuser"])
#
#     if "password" in user_data:
#         hashed_password = get_password_hash(user_data["password"])
#         fields.append("hashed_password = %s")
#         params.append(hashed_password)
#
#     # If no fields to update, return current user
#     if not fields:
#         query = """
#         SELECT
#             id, email, full_name, is_active, is_superuser, created_at, updated_at
#         FROM
#             users
#         WHERE
#             id = %s
#         """
#
#         user = execute_query(query, (user_id,), single=True)
#
#         if not user:
#             raise ValueError("User not found")
#
#         return user
#
#     # Build update query
#     update_query = f"""
#     UPDATE users
#     SET {", ".join(fields)}, updated_at = NOW()
#     WHERE id = %s
#     RETURNING id, email, full_name, is_active, is_superuser, created_at, updated_at
#     """
#
#     params.append(user_id)
#
#     # Execute update
#     user = execute_query(update_query, tuple(params), single=True)
#
#     if not user:
#         raise ValueError("User not found")
#
#     return user
#
#
# def delete_user(user_id: str) -> Dict[str, Any]:
#     """
#     Delete a user
#
#     Parameters:
#     - user_id: User ID
#
#     Returns:
#     - Deleted user
#     """
#     # Get user before deletion
#     query = """
#     SELECT
#         id, email, full_name, is_active, is_superuser, created_at, updated_at
#     FROM
#         users
#     WHERE
#         id = %s
#     """
#
#     user = execute_query(query, (user_id,), single=True)
#
#     if not user:
#         raise ValueError("User not found")
#
#     # Check if user is associated with a merchant
#     check_query = """
#     SELECT id FROM merchants WHERE user_id = %s
#     """
#
#     merchant = execute_query(check_query, (user_id,), single=True)
#
#     if merchant:
#         raise ValueError("Cannot delete user associated with a merchant")
#
#     # Delete user
#     delete_query = """
#     DELETE FROM users
#     WHERE id = %s
#     """
#
#     execute_query(delete_query, (user_id,), fetch=False)
#
#     return user
#
#
# # @router.get("/commission-report")
# # async def get_merchant_commission_report(
# #         start_date: Optional[datetime] = None,
# #         end_date: Optional[datetime] = None,
# #         merchant: Dict[str, Any] = Depends(get_api_key_merchant)
# # ):
# #     """Get merchant's commission report"""
# #     query_params = [merchant["id"]]
# #     filters = ""
# #
# #     # Base query
# #     query = """
# #     SELECT
# #         tf.id, tf.payment_id, p.reference, p.payment_type,
# #         tf.original_amount, tf.commission_rate, tf.fee_amount,
# #         tf.final_amount, tf.created_at
# #     FROM
# #         transaction_fees tf
# #     JOIN
# #         payments p ON tf.payment_id = p.id
# #     WHERE
# #         tf.merchant_id = %s
# #     """
# #
# #     # Add filters
# #     if start_date:
# #         filters += " AND tf.created_at >= %s"
# #         query_params.append(start_date)
# #
# #     if end_date:
# #         filters += " AND tf.created_at <= %s"
# #         query_params.append(end_date)
# #
# #     # Add filters and order by
# #     query += filters + " ORDER BY tf.created_at DESC"
# #
# #     # Execute query
# #     commissions = execute_query(query, tuple(query_params))
# #
# #     # Calculate totals
# #     total_query = """
# #     SELECT
# #         SUM(tf.original_amount) as total_amount,
# #         SUM(tf.fee_amount) as total_fees,
# #         SUM(tf.final_amount) as total_final
# #     FROM
# #         transaction_fees tf
# #     WHERE
# #         tf.merchant_id = %s
# #     """ + filters
# #
# #     totals = execute_query(total_query, tuple(query_params), single=True)
# #
# #     # Get current commission rate
# #     rate_query = """
# #     SELECT commission_rate FROM merchants WHERE id = %s
# #     """
# #     rate_result = execute_query(rate_query, (merchant["id"],), single=True)
# #
# #     return {
# #         "commission_rate": float(rate_result["commission_rate"]),
# #         "transactions": commissions,
# #         "summary": {
# #             "total_original_amount": totals["total_amount"] or 0,
# #             "total_fees_deducted": totals["total_fees"] or 0,
# #             "total_final_amount": totals["total_final"] or 0,
# #             "count": len(commissions)
# #         }
# #     }