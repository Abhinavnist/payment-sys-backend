from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, timedelta
import io
import csv

from app.core.security import get_api_key_merchant
from app.services.report_service import get_merchant_reports, generate_payments_csv

router = APIRouter()


@router.get("/payments")
async def get_merchant_payments(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_type: Optional[str] = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Get merchant payments with pagination and filtering
    """
    try:
        result = get_merchant_reports(
            merchant_id=merchant["id"],
            start_date=start_date,
            end_date=end_date,
            status=status,
            payment_type=payment_type,
            page=page,
            page_size=page_size
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving payments: {str(e)}"
        )


@router.get("/download-payments")
async def download_merchant_payments_csv(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_type: Optional[str] = None,
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Download merchant payments as CSV
    """
    try:
        # Generate CSV data
        csv_data = generate_payments_csv(
            merchant_id=merchant["id"],
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating CSV: {str(e)}"
        )


@router.get("/statistics")
async def get_merchant_statistics(
        days: int = Query(30, description="Number of days to look back"),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Get merchant payment statistics
    """
    try:
        from app.db.connection import execute_query

        # Calculate start date
        start_date = datetime.now() - timedelta(days=days)

        # Get total transactions
        total_transactions_query = """
        SELECT COUNT(*) as count 
        FROM payments 
        WHERE merchant_id = %s AND created_at >= %s
        """
        total_transactions = execute_query(
            total_transactions_query,
            (merchant["id"], start_date),
            single=True
        )["count"]

        # Get successful transactions
        successful_transactions_query = """
        SELECT COUNT(*) as count 
        FROM payments 
        WHERE merchant_id = %s AND status = 'CONFIRMED' AND created_at >= %s
        """
        successful_transactions = execute_query(
            successful_transactions_query,
            (merchant["id"], start_date),
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
        WHERE merchant_id = %s AND payment_type = 'DEPOSIT' 
        AND status = 'CONFIRMED' AND created_at >= %s
        """
        total_deposit = execute_query(
            total_deposit_query,
            (merchant["id"], start_date),
            single=True
        )["total"]

        # Get total withdrawal amount
        total_withdrawal_query = """
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM payments 
        WHERE merchant_id = %s AND payment_type = 'WITHDRAWAL' 
        AND status = 'CONFIRMED' AND created_at >= %s
        """
        total_withdrawal = execute_query(
            total_withdrawal_query,
            (merchant["id"], start_date),
            single=True
        )["total"]

        # Get pending verification count
        pending_verification_query = """
        SELECT COUNT(*) as count 
        FROM payments 
        WHERE merchant_id = %s AND status = 'PENDING'
        """
        pending_verification = execute_query(
            pending_verification_query,
            (merchant["id"],),
            single=True
        )["count"]

        return {
            "total_transactions": total_transactions,
            "successful_transactions": successful_transactions,
            "success_rate": success_rate,
            "total_deposit_amount": total_deposit,
            "total_withdrawal_amount": total_withdrawal,
            "pending_verification": pending_verification,
            "days": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving statistics: {str(e)}"
        )