import logging
import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.security import generate_webhook_signature
from app.db.connection import execute_query

logger = logging.getLogger(__name__)


async def send_webhook(
        callback_url: str,
        payload: Dict[str, Any],
        webhook_secret: Optional[str],
        payment_id: Optional[str] = None,
        attempt: int = 1
) -> bool:
    """
    Send webhook callback to merchant

    Parameters:
    - callback_url: URL to send the webhook to
    - payload: Webhook payload
    - webhook_secret: Merchant's webhook secret
    - payment_id: ID of the payment being processed
    - attempt: Current attempt number

    Returns:
    - True if webhook was successfully sent, False otherwise
    """
    try:
        # Add signature to headers if webhook secret is provided
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if webhook_secret:
            signature = generate_webhook_signature(payload, webhook_secret)
            headers["X-Webhook-Signature"] = signature

        async with aiohttp.ClientSession() as session:
            # Send the webhook
            async with session.post(
                    callback_url,
                    json=payload,
                    headers=headers,
                    timeout=10
            ) as response:
                # Get response
                status_code = response.status
                response_text = await response.text()

                # Log response
                logger.info(f"Webhook sent to {callback_url}. Status: {status_code}")

                # Update payment record if payment_id is provided
                if payment_id:
                    update_query = """
                    UPDATE payments
                    SET 
                        callback_sent = TRUE,
                        callback_response = %s,
                        callback_attempts = %s
                    WHERE 
                        id = %s
                    """
                    execute_query(
                        update_query,
                        (response_text[:255], attempt, payment_id),
                        fetch=False
                    )

                # Return success if status code is 2xx
                return 200 <= status_code < 300

    except Exception as e:
        logger.error(f"Error sending webhook to {callback_url}: {e}")

        # Update payment record if payment_id is provided
        if payment_id:
            error_message = str(e)[:255]
            update_query = """
            UPDATE payments
            SET 
                callback_response = %s,
                callback_attempts = %s
            WHERE 
                id = %s
            """
            execute_query(
                update_query,
                (error_message, attempt, payment_id),
                fetch=False
            )

        # Retry if we haven't reached the max attempts
        if attempt < settings.WEBHOOK_RETRY_ATTEMPTS:
            # Schedule retry with exponential backoff
            delay = settings.WEBHOOK_RETRY_DELAY * (2 ** (attempt - 1))
            logger.info(f"Scheduling webhook retry in {delay} seconds (attempt {attempt + 1})")

            # Schedule the retry
            asyncio.create_task(
                retry_webhook(
                    callback_url,
                    payload,
                    webhook_secret,
                    payment_id,
                    attempt + 1,
                    delay
                )
            )

        return False


async def retry_webhook(
        callback_url: str,
        payload: Dict[str, Any],
        webhook_secret: Optional[str],
        payment_id: Optional[str],
        attempt: int,
        delay: int
) -> None:
    """
    Retry sending webhook after a delay

    Parameters:
    - callback_url: URL to send the webhook to
    - payload: Webhook payload
    - webhook_secret: Merchant's webhook secret
    - payment_id: ID of the payment being processed
    - attempt: Current attempt number
    - delay: Delay in seconds
    """
    # Wait for the specified delay
    await asyncio.sleep(delay)

    # Retry sending the webhook
    await send_webhook(
        callback_url,
        payload,
        webhook_secret,
        payment_id,
        attempt
    )


async def process_failed_webhooks() -> None:
    """
    Process failed webhooks
    Scheduled task to retry sending webhooks that failed
    """
    # Find payments with failed webhooks
    query = """
    SELECT 
        p.id, p.merchant_id, p.reference, p.amount, p.status,
        p.callback_attempts, m.callback_url, m.webhook_secret
    FROM 
        payments p
    JOIN 
        merchants m ON p.merchant_id = m.id
    WHERE 
        p.status IN ('CONFIRMED', 'DECLINED')
        AND (p.callback_sent = FALSE OR p.callback_attempts < %s)
        AND p.callback_attempts < %s
    LIMIT 50
    """

    failed_webhooks = execute_query(
        query,
        (settings.WEBHOOK_RETRY_ATTEMPTS, settings.WEBHOOK_RETRY_ATTEMPTS)
    )

    # Process each failed webhook
    for webhook in failed_webhooks:
        # Prepare callback data
        callback_data = {
            "reference_id": webhook["reference"],
            "status": 2 if webhook["status"] == "CONFIRMED" else 3,
            "remarks": "Payment processed",
            "amount": str(webhook["amount"])
        }

        # Send webhook
        await send_webhook(
            webhook["callback_url"],
            callback_data,
            webhook["webhook_secret"],
            webhook["id"],
            webhook["callback_attempts"] + 1
        )

        # Sleep briefly to avoid overwhelming the system
        await asyncio.sleep(1)