"""
Klap payment gateway service.

Handles communication with Klap Checkout Flex API for creating orders
and validating webhooks.
"""

import hashlib
import logging
from typing import Any
from uuid import UUID

import httpx

from app.config import config
from app.functions.exceptions import bad_request

logger = logging.getLogger(__name__)


class KlapService:
    """Service for interacting with Klap Checkout Flex API."""

    def __init__(self):
        self.api_key = config.KLAP_API_KEY
        self.api_url = config.KLAP_API_URL
        self.webhook_secret = config.KLAP_WEBHOOK_SECRET
        self.frontend_url = config.FRONTEND_URL

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Klap API requests."""
        return {
            "Content-Type": "application/json",
            "Apikey": self.api_key,
        }

    async def create_order(
        self,
        reference_id: str,
        amount: int,
        description: str,
    ) -> dict[str, Any]:
        """
        Create a payment order in Klap.

        Args:
            reference_id: Unique identifier for the order (format: TABLE-{table_number}-{timestamp})
            amount: Amount in CLP (no decimals)
            description: Description of the order

        Returns:
            Order data including order_id from Klap

        Raises:
            HTTPException: If order creation fails
        """
        if not self.api_key:
            raise bad_request("Klap API key no configurada")

        url = f"{self.api_url}/payment-gateway/v1/orders"

        # Build webhook URLs
        webhook_confirm_url = f"{self.frontend_url}/api/v1/webhooks/klap-confirm"
        webhook_reject_url = f"{self.frontend_url}/api/v1/webhooks/klap-reject"

        payload = {
            "reference_id": reference_id,
            "amount": amount,
            "currency": "CLP",
            "description": description,
            "webhook_confirm": webhook_confirm_url,
            "webhook_reject": webhook_reject_url,
        }

        logger.info(f"Creating Klap order: reference_id={reference_id}, amount={amount}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                order_data = response.json()

                logger.info(
                    f"Klap order created successfully: "
                    f"order_id={order_data.get('order_id')}, reference_id={reference_id}"
                )

                return order_data

        except httpx.HTTPStatusError as e:
            error_msg = f"Error creating Klap order: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                logger.error(f"{error_msg} - {error_detail}")
            except Exception:
                logger.error(f"{error_msg} - {e.response.text}")

            raise bad_request(f"Error al crear orden de pago: {e.response.status_code}")

        except httpx.TimeoutException:
            logger.error(f"Timeout creating Klap order: reference_id={reference_id}")
            raise bad_request("Timeout al comunicarse con Klap")

        except Exception as e:
            logger.error(f"Unexpected error creating Klap order: {e}")
            raise bad_request(f"Error inesperado al crear orden de pago: {str(e)}")

    def validate_webhook(
        self,
        header_apikey: str,
        reference_id: str,
        order_id: str,
    ) -> bool:
        """
        Validate webhook signature from Klap.

        Klap validates webhooks using SHA256(reference_id + order_id + api_key).

        Args:
            header_apikey: Apikey header sent by Klap in the webhook
            reference_id: Reference ID from the webhook payload
            order_id: Order ID from Klap
            api_key: API key to use for validation (defaults to configured key)

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping validation")
            return True  # Allow in dev if not configured

        # Calculate expected signature
        message = f"{reference_id}{order_id}{self.webhook_secret}"
        expected_signature = hashlib.sha256(message.encode()).hexdigest()

        is_valid = expected_signature.lower() == header_apikey.lower()

        if not is_valid:
            logger.warning(
                f"Invalid webhook signature: "
                f"expected={expected_signature}, received={header_apikey}"
            )

        return is_valid

    def generate_reference_id(self, table_id: UUID, timestamp: int | None = None) -> str:
        """
        Generate a unique reference_id for Klap orders.

        Format: TABLE-{table_number}-{timestamp}
        """
        import time

        if timestamp is None:
            timestamp = int(time.time() * 1000)  # milliseconds

        return f"TABLE-{table_id.hex[:8]}-{timestamp}"


# Singleton instance
klap_service = KlapService()
