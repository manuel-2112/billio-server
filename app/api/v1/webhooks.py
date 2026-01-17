"""
Webhook handlers for Klap payment notifications.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.database.dependencies import sessDep
from app.models.account import AccountStatus
from app.models.table import Table
from app.models.location import Location
from app.models.webhook_log import WebhookLog
from app.services import account_service
from app.services.klap_service import klap_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    """Base webhook payload structure."""
    reference_id: str
    order_id: str
    amount: int
    currency: str = "CLP"
    status: str
    transaction_data: dict | None = None


@router.post(
    "/klap-confirm",
    status_code=status.HTTP_200_OK,
    summary="Webhook for confirmed payment",
    description="Receives notification when Klap confirms a payment. Validates signature and marks account as paid.",
)
async def webhook_confirm(
    request: Request,
    async_session: sessDep,
    payload: dict,
    Apikey: str | None = Header(None, alias="Apikey"),
):
    """
    Handle webhook notification for confirmed payment.

    Validates the webhook signature and marks the account as paid.
    Must return 200 OK within 10 seconds or Klap will retry.
    """
    start_time = datetime.now(UTC)

    try:
        # Extract webhook data
        reference_id = payload.get("reference_id")
        order_id = payload.get("order_id")
        amount = payload.get("amount")
        status_value = payload.get("status")

        if not all([reference_id, order_id, Apikey]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campos requeridos faltantes en webhook",
            )

        # Validate webhook signature
        is_valid = klap_service.validate_webhook(
            header_apikey=Apikey,
            reference_id=reference_id,
            order_id=order_id,
        )

        if not is_valid:
            logger.error(
                f"Invalid webhook signature: reference_id={reference_id}, "
                f"order_id={order_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firma de webhook inválida",
            )

        # Find account by Klap order_id with all relationships
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        stmt = (
            select(Account)
            .where(Account.klap_order_id == order_id)
            .options(
                joinedload(Account.table).joinedload(Table.location).joinedload(Location.restaurant),
                joinedload(Account.items),
            )
        )
        result = await async_session.execute(stmt)
        account = result.unique().scalar_one_or_none()

        if not account:
            logger.error(f"Account not found for order_id: {order_id}")
            # Still return 200 to prevent Klap retries
            return {"status": "ok", "message": "Account not found, already processed"}

        if account.status != AccountStatus.OPEN:
            logger.warning(
                f"Account {account.id} already processed: status={account.status}"
            )
            return {"status": "ok", "message": "Account already processed"}

        # Verify amount matches
        if account.total != amount:
            logger.warning(
                f"Amount mismatch: account.total={account.total}, "
                f"webhook.amount={amount}"
            )

        # Mark account as paid
        payment_method = "applePay" if "apple" in str(payload).lower() else "googlePay"
        payment_method = payload.get("payment_method", payment_method)

        await account_service.mark_account_paid(
            session=async_session,
            account_id=account.id,
            payment_method=payment_method,
            klap_order_id=order_id,
            transaction_data=payload,
        )

        # Log webhook
        webhook_log = WebhookLog(
            account_id=account.id,
            event_type="confirm",
            payload=payload,
            response_status=200,
        )
        async_session.add(webhook_log)
        await async_session.commit()

        # Send email notification (async, don't wait)
        try:
            from app.services.email_service import send_payment_notification

            await send_payment_notification(
                account=account,
                payment_method=payment_method,
            )
        except Exception as e:
            logger.error(f"Failed to send payment notification email: {e}")
            # Don't fail webhook if email fails

        elapsed_time = (datetime.now(UTC) - start_time).total_seconds()
        logger.info(
            f"Payment confirmed: account={account.id}, order_id={order_id}, "
            f"amount={amount}, elapsed={elapsed_time:.2f}s"
        )

        # Ensure we return within 10 seconds
        if elapsed_time > 9:
            logger.warning(f"Webhook took {elapsed_time:.2f}s, close to 10s limit")

        return {"status": "ok", "message": "Payment confirmed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing confirm webhook: {e}", exc_info=True)
        # Return 200 to prevent retries for unexpected errors
        # Log the error for manual review
        return {"status": "error", "message": "Internal error logged"}


@router.post(
    "/klap-reject",
    status_code=status.HTTP_200_OK,
    summary="Webhook for rejected payment",
    description="Receives notification when Klap rejects a payment. Logs the error.",
)
async def webhook_reject(
    request: Request,
    async_session: sessDep,
    payload: dict,
    Apikey: str | None = Header(None, alias="Apikey"),
):
    """
    Handle webhook notification for rejected payment.

    Logs the rejection but keeps the account open so customer can retry.
    """
    try:
        # Extract webhook data
        reference_id = payload.get("reference_id")
        order_id = payload.get("order_id")
        status_value = payload.get("status")
        error_message = payload.get("error_message", "Pago rechazado")

        if not all([reference_id, order_id]):
            logger.warning("Incomplete webhook reject payload")
            return {"status": "ok", "message": "Incomplete payload"}

        # Validate webhook signature (optional for reject, but recommended)
        if Apikey:
            is_valid = klap_service.validate_webhook(
                header_apikey=Apikey,
                reference_id=reference_id,
                order_id=order_id,
            )
            if not is_valid:
                logger.error(f"Invalid webhook signature for reject: order_id={order_id}")

        # Find account by Klap order_id
        from sqlalchemy import select

        stmt = select(Account).where(Account.klap_order_id == order_id)
        result = await async_session.execute(stmt)
        account = result.unique().scalar_one_or_none()

        # Log webhook
        if account:
            webhook_log = WebhookLog(
                account_id=account.id,
                event_type="reject",
                payload=payload,
                response_status=200,
            )
            async_session.add(webhook_log)
            await async_session.commit()

            logger.warning(
                f"Payment rejected: account={account.id}, order_id={order_id}, "
                f"error={error_message}"
            )
        else:
            logger.warning(f"Payment rejected but account not found: order_id={order_id}")

        return {"status": "ok", "message": "Rejection logged"}

    except Exception as e:
        logger.error(f"Error processing reject webhook: {e}", exc_info=True)
        # Return 200 to prevent retries
        return {"status": "error", "message": "Internal error logged"}
