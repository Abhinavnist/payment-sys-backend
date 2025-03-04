import qrcode
import io
import base64
from typing import Optional
from app.core.config import settings


def generate_qr_code(data: str, box_size: Optional[int] = None, border: Optional[int] = None) -> str:
    """
    Generate a QR code as a base64 encoded image

    Parameters:
    - data: Data to encode in the QR code
    - box_size: Size of each box in the QR code
    - border: Border size around the QR code

    Returns:
    - Base64 encoded QR code image
    """
    # Set default values if not provided
    box_size = box_size or settings.QR_CODE_BOX_SIZE
    border = border or settings.QR_CODE_BORDER

    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )

    # Add data to the QR code
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image to a bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    # Get the bytes value from the buffer
    img_bytes = buffer.getvalue()

    # Encode the bytes as base64
    img_base64 = base64.b64encode(img_bytes).decode()

    # Return data URI
    return f"data:image/png;base64,{img_base64}"