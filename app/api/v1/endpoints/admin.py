from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
import uuid
import io
import csv
import json
from datetime import datetime, timedelta
import re
import os
from datetime import datetime, timedelta
from app.middlewares.ip_whitelist import ip_access_attempts

from app.core.security import get_current_active_superuser
from app.schemas.auth import UserInDB
from app.services.payment_service import (
    get_pending_payments,
    verify_payment,
    decline_payment
)

from app.services.bank_statement_service import (
    process_bank_statement,
    get_bank_statements
)
from app.services.report_service import (
    get_payment_stats,
    get_merchant_reports,
    generate_payments_csv,
    get_merchant_commission_report
)
from app.services.admin_service import (
    get_users,
    create_user,
    update_user,
    get_merchants,
    create_merchant,
    update_merchant,
    regenerate_api_key,
    get_merchant_details
)

router = APIRouter()


# =================== Users Management ===================

@router.get("/users")
async def list_users(
        skip: int = 0,
        limit: int = 100,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    List all users
    """
    users = get_users(skip=skip, limit=limit)
    return users


@router.post("/users")
async def create_new_user(
        user_data: Dict[str, Any],
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Create a new user
    """
    try:
        user = create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/users/{user_id}")
async def update_existing_user(
        user_id: uuid.UUID,
        user_data: Dict[str, Any],
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Update an existing user
    """
    try:
        user = update_user(str(user_id), user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =================== Payment Management ===================

@router.get("/pending-payments")
async def list_pending_payments(
        merchant_id: Optional[uuid.UUID] = None,
        days: int = Query(7, description="Number of days to look back"),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Get all pending payments, optionally filtered by merchant
    """
    payments = get_pending_payments(
        merchant_id=str(merchant_id) if merchant_id else None,
        days=days
    )
    return payments


@router.post("/verify-payment/{payment_id}")
async def admin_verify_payment(
        payment_id: uuid.UUID,
        utr_number: str = Body(...),
        remarks: Optional[str] = Body(None),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Verify a payment (mark as CONFIRMED)
    """
    try:
        result = verify_payment(
            payment_id=str(payment_id),
            utr_number=utr_number,
            verified_by=str(current_user.id),
            verification_method="MANUAL",
            remarks=remarks
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/decline-payment/{payment_id}")
async def admin_decline_payment(
        payment_id: uuid.UUID,
        remarks: str = Body(...),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Decline a payment
    """
    try:
        result = decline_payment(
            payment_id=str(payment_id),
            declined_by=str(current_user.id),
            remarks=remarks
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/upload-bank-statement")
async def upload_bank_statement(
        file: UploadFile = File(...),
        bank_name: str = Form(...),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Upload a bank statement for automatic UTR matching
    """
    try:
        # Check file extension
        if not file.filename.endswith(('.csv', '.xlsx', '.xls', '.pdf')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload CSV, Excel, or PDF file."
            )

        # Process bank statement
        result = await process_bank_statement(
            file=file,
            bank_name=bank_name,
            uploaded_by=str(current_user.id)
        )

        return {
            "message": "Bank statement uploaded successfully",
            "filename": file.filename,
            "matched_transactions": result["matched_transactions"],
            "processed_transactions": result["processed_transactions"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing bank statement: {str(e)}"
        )


@router.get("/bank-statements")
async def list_bank_statements(
        skip: int = 0,
        limit: int = 100,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    List all bank statements
    """
    statements = get_bank_statements(skip=skip, limit=limit)
    return statements


@router.get("/export-payments")
async def export_payments_csv(
        merchant_id: Optional[uuid.UUID] = None,
        payment_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Export payments as CSV
    """
    # Generate CSV data
    csv_data = generate_payments_csv(
        merchant_id=str(merchant_id) if merchant_id else None,
        payment_type=payment_type,
        status=status,
        start_date=start_date,
        end_date=end_date
    )

    # Create in-memory file
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(csv_data["headers"])

    # Write data rows
    for row in csv_data["rows"]:
        writer.writerow(row)

    # Prepare response
    output.seek(0)

    # Format filename with current date
    filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/dashboard-stats")
async def get_dashboard_statistics(
        days: int = Query(30, description="Number of days to look back"),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Get dashboard statistics
    """
    stats = get_payment_stats(days=days)
    return stats


@router.get("/commission-dashboard")
async def get_commission_dashboard(
        days: int = Query(30, description="Number of days to look back"),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Get commission dashboard statistics
    """
    
    
    # Calculate start date
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()
    
    # Get report
    report = get_merchant_commission_report(
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "report": report,
        "days": days
    }

@router.get("/merchant-commission/{merchant_id}")
async def get_merchant_commission(
        merchant_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Get detailed commission report for a specific merchant
    """
    
    # Get report
    report = get_merchant_commission_report(
        merchant_id=str(merchant_id),
        start_date=start_date,
        end_date=end_date
    )
    
    return report


@router.get("/merchants/{merchant_id}/pending-ips")
async def get_pending_ips(
    merchant_id: uuid.UUID,
    current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Get pending IP addresses that need to be whitelisted for a merchant
    """
    from app.db.connection import execute_query
    from app.core.shared import ip_access_attempts  # Import the shared dictionary
    import re
    import os
    try:
        # Verify merchant exists
        merchant_query = """
        SELECT id FROM merchants WHERE id = %s
        """
        merchant = execute_query(merchant_query, (str(merchant_id),), single=True)
        
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )

        # Get current whitelisted IPs
        whitelist_query = """
        SELECT ip_address FROM ip_whitelist WHERE merchant_id = %s
        """
        whitelisted_ips = execute_query(whitelist_query, (str(merchant_id),))
        whitelisted_ip_set = {ip["ip_address"] for ip in whitelisted_ips}
        
        # Collect pending IPs from our in-memory storage
        pending_ips = []
        merchant_id_str = str(merchant_id)
        
        for ip_address, data in ip_access_attempts.items():
            if data.get("merchant_id") == merchant_id_str and ip_address not in whitelisted_ip_set:
                pending_ips.append({
                    "ip_address": ip_address,
                    "last_attempt": data.get("last_attempt", datetime.now().isoformat()),
                    "attempts": data.get("attempts", 1)
                })
        
        # Try to find additional IPs from log files
        log_files = [
            "app.log",  # Add your actual log files here
            "server.log",
            "/var/log/application.log"
        ]
        
        ip_pattern = r'IP (\d+\.\d+\.\d+\.\d+) not whitelisted for merchant ' + re.escape(merchant_id_str)
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if merchant_id_str in line and "not whitelisted" in line:
                                match = re.search(ip_pattern, line)
                                if match:
                                    ip_address = match.group(1)
                                    
                                    # Skip if already whitelisted or already in our results
                                    if ip_address in whitelisted_ip_set or any(item["ip_address"] == ip_address for item in pending_ips):
                                        continue
                                    
                                    # Extract timestamp if possible
                                    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                                    timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()
                                    
                                    pending_ips.append({
                                        "ip_address": ip_address,
                                        "last_attempt": timestamp,
                                        "attempts": 1
                                    })
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to get pending IPs: {str(e)}"
                    )
                    # logger.error(f"Error reading log file {log_file}: {e}")
        
        # Sort by most recent attempts
        pending_ips.sort(key=lambda x: x["last_attempt"], reverse=True)
        
        return pending_ips
        
    except Exception as e:
        # logger.error(f"Error getting pending IPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending IPs: {str(e)}"
        )

# @router.get("/export-commission-report")
# async def export_commission_report(
#         merchant_id: Optional[uuid.UUID] = None,
#         start_date: Optional[datetime] = None,
#         end_date: Optional[datetime] = None,
#         current_user: UserInDB = Depends(get_current_active_superuser)
# ):
#     """
#     Export commission report as CSV
#     """
#     if not start_date:
#         start_date = datetime.now() - timedelta(days=30)
#     if not end_date:
#         end_date = datetime.now()
    
#     # Build query conditions
#     conditions = ["p.status = 'CONFIRMED'", "p.created_at >= %s", "p.created_at <= %s"]
#     params = [start_date, end_date]
    
#     if merchant_id:
#         conditions.append("tf.merchant_id = %s")
#         params.append(str(merchant_id))
    
#     where_clause = " AND ".join(conditions)
    
#     # Get detailed transaction data
#     query = f"""
#     SELECT 
#         m.business_name,
#         p.reference, p.payment_type, 
#         tf.original_amount, tf.commission_rate, tf.fee_amount, tf.final_amount,
#         p.created_at, p.utr_number
#     FROM 
#         transaction_fees tf
#     JOIN
#         payments p ON tf.payment_id = p.id
#     JOIN
#         merchants m ON tf.merchant_id = m.id
#     WHERE 
#         {where_clause}
#     ORDER BY
#         p.created_at DESC
#     """
    
#     transactions = execute_query(query, tuple(params))
    
#     # Define CSV headers
#     headers = [
#         "Date", "Merchant", "Reference", "Type", "Original Amount", 
#         "Commission Rate (%)", "Commission Amount", "Final Amount",
#         "UTR Number"
#     ]
    
#     # Prepare rows
#     rows = []
#     for tx in transactions:
#         rows.append([
#             tx["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
#             tx["business_name"],
#             tx["reference"],
#             tx["payment_type"],
#             tx["original_amount"],
#             float(tx["commission_rate"]),
#             tx["fee_amount"],
#             tx["final_amount"],
#             tx["utr_number"] or ""
#         ])
    
#     # Generate CSV in memory
#     output = io.StringIO()
#     writer = csv.writer(output)
    
#     # Write header
#     writer.writerow(headers)
    
#     # Write data rows
#     for row in rows:
#         writer.writerow(row)
    
#     # Prepare output
#     output.seek(0)
    
#     # Format filename with current date
#     filename = f"commission_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
#     return StreamingResponse(
#         io.StringIO(output.getvalue()),
#         media_type="text/csv",
#         headers={"Content-Disposition": f"attachment; filename={filename}"}
#     )


# =================== Merchant Management ===================

@router.get("/merchants")
async def list_merchants(
        skip: int = 0,
        limit: int = 100,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    List all merchants
    """
    merchants = get_merchants(skip=skip, limit=limit)
    return merchants


@router.post("/merchants")
async def create_new_merchant(
        merchant_data: Dict[str, Any],
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Create a new merchant
    """
    try:
        merchant = create_merchant(merchant_data)
        return merchant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/merchants/{merchant_id}")
async def get_merchant(
        merchant_id: uuid.UUID,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Get merchant details
    """
    try:
        merchant = get_merchant_details(str(merchant_id))
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        return merchant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/merchants/{merchant_id}")
async def update_existing_merchant(
        merchant_id: uuid.UUID,
        merchant_data: Dict[str, Any],
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Update an existing merchant
    """
    try:
        merchant = update_merchant(str(merchant_id), merchant_data)
        return merchant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/merchants/{merchant_id}/regenerate-api-key")
async def regenerate_merchant_api_key(
        merchant_id: uuid.UUID,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Regenerate API key for a merchant
    """
    try:
        api_key = regenerate_api_key(str(merchant_id))
        return {
            "id": str(merchant_id),
            "api_key": api_key
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/merchants/{merchant_id}/add-ip-whitelist")
async def add_ip_to_whitelist(
        merchant_id: uuid.UUID,
        ip_address: str = Body(...),
        description: Optional[str] = Body(None),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Add IP address to merchant's whitelist
    """
    try:
        from app.db.connection import execute_query

        # Check if IP already exists
        check_query = """
        SELECT COUNT(*) as count
        FROM ip_whitelist
        WHERE merchant_id = %s AND ip_address = %s
        """

        result = execute_query(check_query, (str(merchant_id), ip_address), single=True)

        if result["count"] > 0:
            raise ValueError("IP address already whitelisted")

        # Add IP to whitelist
        insert_query = """
        INSERT INTO ip_whitelist (merchant_id, ip_address, description)
        VALUES (%s, %s, %s)
        RETURNING id
        """

        result = execute_query(
            insert_query,
            (str(merchant_id), ip_address, description),
            single=True
        )

        return {
            "id": result["id"],
            "merchant_id": str(merchant_id),
            "ip_address": ip_address,
            "description": description
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/merchants/{merchant_id}/remove-ip-whitelist/{ip_id}")
async def remove_ip_from_whitelist(
        merchant_id: uuid.UUID,
        ip_id: uuid.UUID,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Remove IP address from merchant's whitelist
    """
    try:
        from app.db.connection import execute_query

        # Delete IP from whitelist
        delete_query = """
        DELETE FROM ip_whitelist
        WHERE id = %s AND merchant_id = %s
        RETURNING ip_address
        """

        result = execute_query(
            delete_query,
            (str(ip_id), str(merchant_id)),
            single=True
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP not found in whitelist"
            )

        return {
            "message": "IP removed from whitelist",
            "ip_address": result["ip_address"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing IP: {str(e)}"
        )


@router.post("/merchants/{merchant_id}/update-rate-limit")
async def update_merchant_rate_limit(
        merchant_id: uuid.UUID,
        endpoint: str = Body(...),
        requests_per_minute: int = Body(...),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Update rate limit for a merchant endpoint
    """
    try:
        from app.db.connection import execute_query

        # Upsert rate limit
        upsert_query = """
        INSERT INTO rate_limits (merchant_id, endpoint, requests_per_minute)
        VALUES (%s, %s, %s)
        ON CONFLICT (merchant_id, endpoint) 
        DO UPDATE SET 
            requests_per_minute = EXCLUDED.requests_per_minute,
            updated_at = NOW()
        RETURNING id, endpoint, requests_per_minute
        """

        result = execute_query(
            upsert_query,
            (str(merchant_id), endpoint, requests_per_minute),
            single=True
        )

        return {
            "merchant_id": str(merchant_id),
            "endpoint": result["endpoint"],
            "requests_per_minute": result["requests_per_minute"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating rate limit: {str(e)}"
        )


@router.put("/merchants/{merchant_id}/update-commission")
async def update_merchant_commission(
        merchant_id: uuid.UUID,
        commission_rate: float = Body(..., ge=0, le=100),
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    """
    Update merchant commission rate
    """
    try:
        from app.db.connection import execute_query
        # Validate commission rate
        if commission_rate < 0 or commission_rate > 100:
            raise ValueError("Commission rate must be between 0 and 100")

        # Update merchant commission rate
        query = """
        UPDATE merchants
        SET commission_rate = %s
        WHERE id = %s
        RETURNING id, business_name, commission_rate
        """

        result = execute_query(query, (commission_rate, str(merchant_id)), single=True)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )

        return {
            "id": result["id"],
            "business_name": result["business_name"],
            "commission_rate": float(result["commission_rate"])
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/reports/commissions")
async def get_commission_reports(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        merchant_id: Optional[uuid.UUID] = None,
        current_user: UserInDB = Depends(get_current_active_superuser)
):
    try:
        from app.db.connection import execute_query
        """Get commission reports"""
        query_params = []
        filters = ""

        # Base query
        query = """
        SELECT 
            tf.id, tf.payment_id, tf.merchant_id, m.business_name,
            tf.original_amount, tf.commission_rate, tf.fee_amount, 
            tf.final_amount, tf.created_at,
            p.reference, p.payment_type
        FROM 
            transaction_fees tf
        JOIN
            merchants m ON tf.merchant_id = m.id
        JOIN
            payments p ON tf.payment_id = p.id
        WHERE 1=1
        """

        # Add filters
        if start_date:
            filters += " AND tf.created_at >= %s"
            query_params.append(start_date)

        if end_date:
            filters += " AND tf.created_at <= %s"
            query_params.append(end_date)

        if merchant_id:
            filters += " AND tf.merchant_id = %s"
            query_params.append(str(merchant_id))

        # Add filters and order by
        query += filters + " ORDER BY tf.created_at DESC"

        # Execute query
        commissions = execute_query(query, tuple(query_params) if query_params else None)

        # Calculate totals
        total_query = """
        SELECT 
            SUM(tf.original_amount) as total_amount,
            SUM(tf.fee_amount) as total_fees
        FROM 
            transaction_fees tf
        WHERE 1=1
        """ + filters

        totals = execute_query(total_query, tuple(query_params) if query_params else None, single=True)

        return {
            "commissions": commissions,
            "summary": {
                "total_original_amount": totals["total_amount"] or 0,
                "total_fees_collected": totals["total_fees"] or 0,
                "count": len(commissions)
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )