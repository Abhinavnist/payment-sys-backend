import os
import re
import uuid
import logging
import pandas as pd
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from fastapi import UploadFile
import shutil
import csv
import openpyxl
import PyPDF2
import tabula

from app.core.config import settings
from app.db.connection import execute_query, execute_transaction
from app.services.payment_service import verify_payment

logger = logging.getLogger(__name__)

# UTR patterns for different banks
UTR_PATTERNS = {
    "hdfc": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    "icici": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    "sbi": r'(?:UTR|REF\.?|REFERENCE)\s*(?:NO\.?|NUMBER)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    "axis": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    "kotak": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    "yes": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    "indusind": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])',
    # Add more bank-specific patterns as needed
    "default": r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])'
}


async def process_bank_statement(
        file: UploadFile,
        bank_name: str,
        uploaded_by: str
) -> Dict[str, Any]:
    """
    Process a bank statement file and match UTR numbers with pending payments

    Parameters:
    - file: Uploaded bank statement file
    - bank_name: Name of the bank
    - uploaded_by: ID of user who uploaded the file

    Returns:
    - Processing result statistics
    """
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_FOLDER, "bank_statements")
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Insert record into database
    query = """
    INSERT INTO bank_statements (
        uploaded_by, file_name, file_path, processed, matched_transactions
    ) VALUES (
        %s, %s, %s, FALSE, 0
    ) RETURNING id
    """

    result = execute_query(
        query,
        (uploaded_by, file.filename, file_path),
        single=True
    )

    statement_id = result["id"]

    # Extract UTR numbers and amounts based on file type
    utr_data = []

    try:
        if file_ext.lower() in ['.csv']:
            utr_data = extract_utrs_from_csv(file_path, bank_name.lower())
        elif file_ext.lower() in ['.xlsx', '.xls']:
            utr_data = extract_utrs_from_excel(file_path, bank_name.lower())
        elif file_ext.lower() in ['.pdf']:
            utr_data = extract_utrs_from_pdf(file_path, bank_name.lower())
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        # Match UTRs with pending payments
        matched_count = match_utrs_with_payments(utr_data, uploaded_by)

        # Update bank statement record
        update_query = """
        UPDATE bank_statements
        SET 
            processed = TRUE,
            matched_transactions = %s
        WHERE 
            id = %s
        """

        execute_query(update_query, (matched_count, statement_id), fetch=False)

        return {
            "id": statement_id,
            "matched_transactions": matched_count,
            "processed_transactions": len(utr_data)
        }

    except Exception as e:
        logger.error(f"Error processing bank statement: {e}")

        # Update bank statement record with error
        update_query = """
        UPDATE bank_statements
        SET 
            processed = TRUE,
            matched_transactions = 0
        WHERE 
            id = %s
        """

        execute_query(update_query, (statement_id,), fetch=False)

        raise


def extract_utrs_from_csv(file_path: str, bank_name: str) -> List[Dict[str, Any]]:
    """
    Extract UTR numbers and amounts from CSV file

    Parameters:
    - file_path: Path to CSV file
    - bank_name: Name of the bank

    Returns:
    - List of UTR data (UTR number and amount)
    """
    utr_data = []

    try:
        # Read CSV file
        df = pd.read_csv(file_path)

        # Get UTR pattern for the bank
        utr_pattern = UTR_PATTERNS.get(bank_name, UTR_PATTERNS["default"])

        # Process each row
        for _, row in df.iterrows():
            # Convert row to string and search for UTR pattern
            row_str = ' '.join(str(val) for val in row.values)
            utr_match = re.search(utr_pattern, row_str)

            if utr_match:
                utr_number = utr_match.group(1)

                # Try to find amount in the row
                amount = extract_amount_from_row(row)

                if amount:
                    utr_data.append({
                        "utr_number": utr_number,
                        "amount": amount
                    })
    except Exception as e:
        logger.error(f"Error extracting UTRs from CSV: {e}")

    return utr_data


def validate_utr_number(utr_value):
    pass


def extract_utrs_from_excel(file_path: str, bank_name: str) -> List[Dict[str, Any]]:
    """
    Extract UTR numbers and amounts from Excel file

    Parameters:
    - file_path: Path to Excel file
    - bank_name: Name of the bank

    Returns:
    - List of UTR data (UTR number and amount)
    """
    utr_data = []

    try:
        # Read Excel file with specific data types
        df = pd.read_excel(
            file_path,
            dtype={'UTR': str, 'UTR No': str, 'Reference': str, 'Reference No': str}
        )

        # Get UTR pattern for the bank
        utr_pattern = UTR_PATTERNS.get(bank_name, UTR_PATTERNS["default"])

        # Process each row
        for _, row in df.iterrows():
            # First check if there's a column that might contain UTRs
            utr_columns = ['UTR', 'Reference', 'UTR No', 'Reference No', 'Transaction ID']
            found_utr = False

            for col in utr_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    utr_value = str(row[col])

                    # Check if value is in scientific notation
                    if 'E+' in utr_value:
                        try:
                            utr_value = '{:.0f}'.format(float(utr_value))
                        except ValueError:
                            pass

                    if validate_utr_number(utr_value):
                        # Try to find amount in other columns
                        amount = extract_amount_from_row(row)

                        if amount:
                            utr_data.append({
                                "utr_number": utr_value,
                                "amount": amount
                            })
                            found_utr = True
                            break

            # If no UTR found in specific columns, try the entire row
            if not found_utr:
                # Convert row to string and search for UTR pattern
                row_str = ' '.join(str(val) for val in row.values)
                utr_match = re.search(utr_pattern, row_str)

                if utr_match:
                    utr_number = utr_match.group(1)

                    # Check if value is in scientific notation
                    if 'E+' in utr_number:
                        try:
                            utr_number = '{:.0f}'.format(float(utr_number))
                        except ValueError:
                            pass

                    # Try to find amount in the row
                    amount = extract_amount_from_row(row)

                    if amount and validate_utr_number(utr_number):
                        utr_data.append({
                            "utr_number": utr_number,
                            "amount": amount
                        })
    except Exception as e:
        logger.error(f"Error extracting UTRs from Excel: {e}")

    return utr_data
# 
# def extract_utrs_from_excel(file_path: str, bank_name: str) -> List[Dict[str, Any]]:
#     """
#     Extract UTR numbers and amounts from Excel file
# 
#     Parameters:
#     - file_path: Path to Excel file
#     - bank_name: Name of the bank
# 
#     Returns:
#     - List of UTR data (UTR number and amount)
#     """
#     utr_data = []
# 
#     try:
#         # Read Excel file
#         df = pd.read_excel(file_path,
#                            dtype={'UTR': str, 'UTR No': str, 'Reference': str, 'Reference No': str}
#                            )
# 
#         # Get UTR pattern for the bank
#         utr_pattern = UTR_PATTERNS.get(bank_name, UTR_PATTERNS["default"])
# 
#         # Process each row
#         for _, row in df.iterrows():
#             # Convert row to string and search for UTR pattern
#             row_str = ' '.join(str(val) for val in row.values)
#             utr_match = re.search(utr_pattern, row_str)
# 
#             if utr_match:
#                 utr_number = utr_match.group(1)
# 
#                 # Try to find amount in the row
#                 amount = extract_amount_from_row(row)
# 
#                 if amount:
#                     utr_data.append({
#                         "utr_number": utr_number,
#                         "amount": amount
#                     })
#     except Exception as e:
#         logger.error(f"Error extracting UTRs from Excel: {e}")
# 
#     return utr_data


def extract_utrs_from_pdf(file_path: str, bank_name: str) -> List[Dict[str, Any]]:
    """
    Extract UTR numbers and amounts from PDF file

    Parameters:
    - file_path: Path to PDF file
    - bank_name: Name of the bank

    Returns:
    - List of UTR data (UTR number and amount)
    """
    utr_data = []

    try:
        # Get UTR pattern for the bank
        utr_pattern = UTR_PATTERNS.get(bank_name, UTR_PATTERNS["default"])

        # Extract tables from PDF
        tables = tabula.read_pdf(file_path, pages='all', multiple_tables=True)

        for table in tables:
            # Convert table to string and search for UTR pattern
            table_str = table.to_string()
            utr_matches = re.finditer(utr_pattern, table_str)

            for utr_match in utr_matches:
                utr_number = utr_match.group(1)

                # Try to find amount in the context
                context = table_str[max(0, utr_match.start() - 100):min(len(table_str), utr_match.end() + 100)]
                amount = extract_amount_from_text(context)

                if amount:
                    utr_data.append({
                        "utr_number": utr_number,
                        "amount": amount
                    })

        # If tabula didn't work well, extract text and try to find UTRs
        if not utr_data:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    utr_matches = re.finditer(utr_pattern, text)

                    for utr_match in utr_matches:
                        utr_number = utr_match.group(1)

                        # Try to find amount in the context
                        context = text[max(0, utr_match.start() - 100):min(len(text), utr_match.end() + 100)]
                        amount = extract_amount_from_text(context)

                        if amount:
                            utr_data.append({
                                "utr_number": utr_number,
                                "amount": amount
                            })

    except Exception as e:
        logger.error(f"Error extracting UTRs from PDF: {e}")

    return utr_data


def extract_amount_from_row(row) -> Optional[float]:
    """
    Extract amount from a pandas DataFrame row
    """
    # Look for columns that might contain amount
    amount_columns = ['amount', 'amt', 'total', 'credit', 'debit', 'value']

    for col in row.index:
        if any(keyword in str(col).lower() for keyword in amount_columns):
            try:
                # Try to convert to float
                amount_str = str(row[col])
                amount = float(re.sub(r'[^\d.]', '', amount_str))
                if amount > 0:
                    return amount
            except:
                continue

    # If no amount found in specific columns, search all values
    for val in row.values:
        amount = extract_amount_from_text(str(val))
        if amount:
            return amount

    return None


def extract_amount_from_text(text: str) -> Optional[float]:
    """
    Extract amount from text
    """
    # Look for common amount patterns (e.g., Rs. 1,234.56)
    amount_patterns = [
        r'(?:Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{2})?)',
        r'(?:Amount|Amt|Total)(?:[:\s])*([0-9,]+(?:\.[0-9]{2})?)',
        r'(?:₹|Rs)\s*([0-9,]+(?:\.[0-9]{2})?)',
        r'([0-9,]+(?:\.[0-9]{2})?)(?:\s*(?:Rs\.?|INR|/-|₹))'
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                amount_str = match.group(1)
                amount = float(re.sub(r'[^\d.]', '', amount_str))
                if amount > 0:
                    return amount
            except:
                continue

    return None


def match_utrs_with_payments(utr_data: List[Dict[str, Any]], verified_by: str) -> int:
    """
    Match extracted UTR numbers with pending payments

    Parameters:
    - utr_data: List of UTR data (UTR number and amount)
    - verified_by: ID of user who uploaded the file

    Returns:
    - Number of matched payments
    """
    matched_count = 0

    # Get all pending payments
    query = """
    SELECT 
        id, amount
    FROM 
        payments
    WHERE 
        status = 'PENDING'
        AND payment_type = 'DEPOSIT'
    """

    pending_payments = execute_query(query)

    # Create a lookup dictionary by amount
    payment_lookup = {}
    for payment in pending_payments:
        amount = payment["amount"]
        if amount not in payment_lookup:
            payment_lookup[amount] = []
        payment_lookup[amount].append(payment)

    # Match UTRs with payments
    for utr_item in utr_data:
        utr_number = utr_item["utr_number"]
        amount = utr_item["amount"]

        # Look for matching payment by amount
        if amount in payment_lookup and payment_lookup[amount]:
            payment = payment_lookup[amount].pop(0)

            try:
                # Verify payment
                verify_payment(
                    payment_id=payment["id"],
                    utr_number=utr_number,
                    verified_by=verified_by,
                    verification_method="AUTO",
                    remarks="Auto-verified via bank statement"
                )

                matched_count += 1
            except Exception as e:
                logger.error(f"Error verifying payment {payment['id']} with UTR {utr_number}: {e}")

    return matched_count


def get_bank_statements(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all bank statements

    Parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return

    Returns:
    - List of bank statements
    """
    query = """
    SELECT 
        bs.id, bs.file_name, bs.processed, bs.matched_transactions,
        bs.uploaded_at, u.full_name as uploaded_by_name
    FROM 
        bank_statements bs
    JOIN 
        users u ON bs.uploaded_by = u.id
    ORDER BY 
        bs.uploaded_at DESC
    LIMIT %s OFFSET %s
    """

    statements = execute_query(query, (limit, skip))

    return statements