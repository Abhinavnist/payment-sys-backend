import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import csv
import io

from app.db.connection import execute_query

logger = logging.getLogger(__name__)


def get_payment_stats(days: int = 30) -> Dict[str, Any]:
    """
    Get payment statistics for dashboard

    Parameters:
    - days: Number of days to look back

    Returns:
    - Statistics dictionary
    """
    # Calculate start date
    start_date = datetime.now() - timedelta(days=days)

    # Get total merchants
    total_merchants_query = """
    SELECT COUNT(*) as count FROM merchants
    """
    total_merchants = execute_query(total_merchants_query, single=True)["count"]

    # Get active merchants
    active_merchants_query = """
    SELECT COUNT(*) as count FROM merchants WHERE is_active = TRUE
    """
    active_merchants = execute_query(active_merchants_query, single=True)["count"]

    # Get total transactions
    total_transactions_query = """
    SELECT COUNT(*) as count 
    FROM payments 
    WHERE created_at >= %s
    """
    total_transactions = execute_query(
        total_transactions_query,
        (start_date,),
        single=True
    )["count"]

    # Get successful transactions
    successful_transactions_query = """
    SELECT COUNT(*) as count 
    FROM payments 
    WHERE status = 'CONFIRMED' AND created_at >= %s
    """
    successful_transactions = execute_query(
        successful_transactions_query,
        (start_date,),
        single=True
    )["count"]

    # Calculate success rate
    success_rate = 0
    if total_transactions > 0:
        success_rate = round((successful_transactions / total_transactions) * 100, 2)

    # Get total deposit amount
    total_deposit_query = """
    SELECT COALESCE(SUM(amount), 0) as total 
    FROM payments 
    WHERE payment_type = 'DEPOSIT' 
    AND status = 'CONFIRMED' 
    AND created_at >= %s
    """
    total_deposit = execute_query(
        total_deposit_query,
        (start_date,),
        single=True
    )["total"]

    # Get total withdrawal amount
    total_withdrawal_query = """
    SELECT COALESCE(SUM(amount), 0) as total 
    FROM payments 
    WHERE payment_type = 'WITHDRAWAL' 
    AND status = 'CONFIRMED' 
    AND created_at >= %s
    """
    total_withdrawal = execute_query(
        total_withdrawal_query,
        (start_date,),
        single=True
    )["total"]

    # Get pending verification count
    pending_verification_query = """
    SELECT COUNT(*) as count 
    FROM payments 
    WHERE status = 'PENDING'
    """
    pending_verification = execute_query(
        pending_verification_query,
        single=True
    )["count"]

    # Get daily transaction counts for chart
    daily_transactions_query = """
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as count,
        SUM(CASE WHEN status = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed
    FROM 
        payments
    WHERE 
        created_at >= %s
    GROUP BY 
        DATE(created_at)
    ORDER BY 
        date
    """
    daily_transactions = execute_query(daily_transactions_query, (start_date,))

    # Format daily transaction data for chart
    daily_chart_data = []
    for day in daily_transactions:
        daily_chart_data.append({
            "date": day["date"].strftime("%Y-%m-%d"),
            "total": day["count"],
            "confirmed": day["confirmed"]
        })

    # Get merchant transaction counts
    merchant_transactions_query = """
    SELECT 
        m.business_name,
        COUNT(p.id) as count,
        SUM(CASE WHEN p.status = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed
    FROM 
        merchants m
    LEFT JOIN 
        payments p ON m.id = p.merchant_id AND p.created_at >= %s
    GROUP BY 
        m.id, m.business_name
    ORDER BY 
        count DESC
    LIMIT 10
    """
    merchant_transactions = execute_query(merchant_transactions_query, (start_date,))

    # Format merchant transaction data
    merchant_chart_data = []
    for merchant in merchant_transactions:
        merchant_chart_data.append({
            "merchant": merchant["business_name"],
            "total": merchant["count"],
            "confirmed": merchant["confirmed"]
        })

    # Return stats
    return {
        "total_merchants": total_merchants,
        "active_merchants": active_merchants,
        "total_transactions": total_transactions,
        "successful_transactions": successful_transactions,
        "success_rate": success_rate,
        "total_deposit_amount": total_deposit,
        "total_withdrawal_amount": total_withdrawal,
        "pending_verification": pending_verification,
        "days": days,
        "daily_chart_data": daily_chart_data,
        "merchant_chart_data": merchant_chart_data
    }


def get_merchant_reports(
        merchant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
) -> Dict[str, Any]:
    """
    Get payment reports for a merchant

    Parameters:
    - merchant_id: Merchant ID
    - start_date: Start date filter
    - end_date: End date filter
    - status: Payment status filter
    - payment_type: Payment type filter
    - page: Page number
    - page_size: Page size

    Returns:
    - Paginated payment reports
    """
    # Calculate offset
    offset = (page - 1) * page_size

    # Base query
    query = """
    SELECT 
        p.id, p.reference, p.trxn_hash_key, p.payment_type,
        p.payment_method, p.amount, p.currency, p.status,
        p.utr_number, p.created_at, p.updated_at
    FROM 
        payments p
    WHERE 
        p.merchant_id = %s
    """

    # Count query
    count_query = """
    SELECT 
        COUNT(*) as count
    FROM 
        payments p
    WHERE 
        p.merchant_id = %s
    """

    # Build query parameters
    query_params = [merchant_id]
    count_params = [merchant_id]

    # Add filters
    if start_date:
        query += " AND p.created_at >= %s"
        count_query += " AND p.created_at >= %s"
        query_params.append(start_date)
        count_params.append(start_date)

    if end_date:
        query += " AND p.created_at <= %s"
        count_query += " AND p.created_at <= %s"
        query_params.append(end_date)
        count_params.append(end_date)

    if status:
        query += " AND p.status = %s"
        count_query += " AND p.status = %s"
        query_params.append(status)
        count_params.append(status)

    if payment_type:
        query += " AND p.payment_type = %s"
        count_query += " AND p.payment_type = %s"
        query_params.append(payment_type)
        count_params.append(payment_type)

    # Add order by
    query += " ORDER BY p.created_at DESC"

    # Add pagination
    query += " LIMIT %s OFFSET %s"
    query_params.extend([page_size, offset])

    # Execute queries
    payments = execute_query(query, tuple(query_params))
    count_result = execute_query(count_query, tuple(count_params), single=True)

    # Calculate total pages
    total = count_result["count"]
    pages = (total + page_size - 1) // page_size

    # Return results
    return {
        "items": payments,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


def generate_payments_csv(
        merchant_id: Optional[str] = None,
        payment_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate CSV data for payments export

    Parameters:
    - merchant_id: Filter by merchant ID
    - payment_type: Filter by payment type
    - status: Filter by status
    - start_date: Start date filter
    - end_date: End date filter

    Returns:
    - CSV data dictionary with headers and rows
    """
    # Base query
    query = """
    SELECT 
        p.id, p.reference, p.trxn_hash_key, 
        p.payment_type, p.payment_method, p.amount, 
        p.currency, p.status, p.utr_number,
        p.account_name, p.account_number, p.bank, p.bank_ifsc,
        p.created_at, p.updated_at, 
        p.remarks, m.business_name as merchant_name
    FROM 
        payments p
    JOIN 
        merchants m ON p.merchant_id = m.id
    WHERE 
        1=1
    """

    # Build query parameters
    query_params = []

    # Add filters
    if merchant_id:
        query += " AND p.merchant_id = %s"
        query_params.append(merchant_id)

    if payment_type:
        query += " AND p.payment_type = %s"
        query_params.append(payment_type)

    if status:
        query += " AND p.status = %s"
        query_params.append(status)

    if start_date:
        query += " AND p.created_at >= %s"
        query_params.append(start_date)

    if end_date:
        query += " AND p.created_at <= %s"
        query_params.append(end_date)

    # Add order by
    query += " ORDER BY p.created_at DESC"

    # Execute query
    payments = execute_query(query, tuple(query_params) if query_params else None)

    # Define CSV headers
    headers = [
        "ID", "Reference", "Transaction Hash", "Type", "Method",
        "Amount", "Currency", "Status", "UTR Number",
        "Account Name", "Account Number", "Bank", "IFSC Code",
        "Created At", "Updated At", "Remarks", "Merchant"
    ]

    # Prepare rows
    rows = []
    for payment in payments:
        rows.append([
            payment["id"],
            payment["reference"],
            payment["trxn_hash_key"],
            payment["payment_type"],
            payment["payment_method"],
            payment["amount"],
            payment["currency"],
            payment["status"],
            payment["utr_number"] or "",
            payment["account_name"] or "",
            payment["account_number"] or "",
            payment["bank"] or "",
            payment["bank_ifsc"] or "",
            payment["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            payment["updated_at"].strftime("%Y-%m-%d %H:%M:%S"),
            payment["remarks"] or "",
            payment["merchant_name"]
        ])

    return {
        "headers": headers,
        "rows": rows
    }