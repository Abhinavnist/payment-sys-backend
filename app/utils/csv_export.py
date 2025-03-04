import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime


def format_csv_value(value: Any) -> str:
    """Format a value for CSV export"""
    if value is None:
        return ""
    elif isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, bool):
        return "Yes" if value else "No"
    else:
        return str(value)


def generate_csv_file(headers: List[str], rows: List[List[Any]]) -> str:
    """
    Generate a CSV file as a string

    Parameters:
    - headers: List of column headers
    - rows: List of rows, each containing values for each column

    Returns:
    - CSV content as a string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(headers)

    # Write data rows
    for row in rows:
        formatted_row = [format_csv_value(value) for value in row]
        writer.writerow(formatted_row)

    return output.getvalue()


def dict_to_csv(data: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> str:
    """
    Convert a list of dictionaries to CSV

    Parameters:
    - data: List of dictionaries containing the data
    - fields: List of field names to include (all fields if None)

    Returns:
    - CSV content as a string
    """
    if not data:
        return ""

    # Determine fields if not provided
    if fields is None:
        fields = list(data[0].keys())

    # Generate rows
    rows = []
    for item in data:
        row = []
        for field in fields:
            row.append(item.get(field))
        rows.append(row)

    return generate_csv_file(fields, rows)