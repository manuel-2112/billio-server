"""
Email service using AWS SES for sending notifications.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import config
from app.models.account import Account

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via AWS SES."""

    def __init__(self):
        self.ses_client = None
        self.sender = config.AWS_SES_SENDER

        # Initialize SES client if credentials are provided
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            try:
                self.ses_client = boto3.client(
                    "ses",
                    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                    region_name=config.AWS_REGION,
                )
                logger.info("AWS SES client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS SES client: {e}")
        else:
            logger.warning("AWS SES credentials not configured, email notifications disabled")

    def _format_currency(self, amount: int) -> str:
        """Format CLP amount as currency string."""
        return f"${amount:,}".replace(",", ".")

    def _build_payment_email_html(self, account: Account, payment_method: str) -> str:
        """Build HTML email content for payment notification."""
        payment_method_display = {
            "applePay": "Apple Pay",
            "googlePay": "Google Pay",
            "apple_pay": "Apple Pay",
            "google_pay": "Google Pay",
        }.get(payment_method.lower(), payment_method)

        items_html = ""
        for item in account.items:
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{item.name}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{self._format_currency(item.unit_price)}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{self._format_currency(item.total_price)}</td>
            </tr>
            """

        paid_time = account.paid_at.strftime("%H:%M:%S") if account.paid_at else "N/A"
        paid_date = account.paid_at.strftime("%d/%m/%Y") if account.paid_at else "N/A"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #ce2a2d; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background-color: #ce2a2d; color: white; padding: 12px; text-align: left; }}
                .total-row {{ font-weight: bold; background-color: #fff; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Pago Recibido - PayInTable</h1>
                </div>
                <div class="content">
                    <h2>Notificación de Pago</h2>
                    <p>Se ha recibido un pago exitoso:</p>
                    
                    <table>
                        <tr>
                            <th>Mesa</th>
                            <th>Total</th>
                            <th>Propina</th>
                            <th>Método</th>
                        </tr>
                        <tr>
                            <td style="padding: 8px;">Mesa {account.table.number}</td>
                            <td style="padding: 8px;">{self._format_currency(account.total)}</td>
                            <td style="padding: 8px;">{self._format_currency(account.tip)}</td>
                            <td style="padding: 8px;">{payment_method_display}</td>
                        </tr>
                    </table>

                    <h3>Detalle de Productos</h3>
                    <table>
                        <thead>
                            <tr>
                                <th style="text-align: left;">Producto</th>
                                <th style="text-align: center;">Cantidad</th>
                                <th style="text-align: right;">Precio Unit.</th>
                                <th style="text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>

                    <table>
                        <tr>
                            <td style="padding: 8px; text-align: right;">Subtotal:</td>
                            <td style="padding: 8px; text-align: right;">{self._format_currency(account.subtotal)}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; text-align: right;">IVA (19%):</td>
                            <td style="padding: 8px; text-align: right;">{self._format_currency(account.tax)}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; text-align: right;">Propina:</td>
                            <td style="padding: 8px; text-align: right;">{self._format_currency(account.tip)}</td>
                        </tr>
                        <tr class="total-row">
                            <td style="padding: 8px; text-align: right;">Total:</td>
                            <td style="padding: 8px; text-align: right;">{self._format_currency(account.total)}</td>
                        </tr>
                    </table>

                    <p><strong>Fecha y Hora:</strong> {paid_date} {paid_time}</p>
                </div>
                <div class="footer">
                    <p>Este es un mensaje automático de PayInTable</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_content

    def send_payment_notification(
        self,
        account: Account,
        payment_method: str,
    ) -> bool:
        """
        Send payment notification email to restaurant staff.

        Args:
            account: The paid account
            payment_method: Payment method used (applePay, googlePay, etc.)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.ses_client:
            logger.warning("AWS SES not configured, skipping email notification")
            return False

        if not self.sender:
            logger.warning("AWS SES sender not configured, skipping email notification")
            return False

        # Get restaurant email from account's table's location's restaurant
        # For MVP, we use the admin email configured in config
        restaurant_email = config.ADMIN_EMAIL

        try:
            # Build email content
            html_content = self._build_payment_email_html(account, payment_method)
            text_content = f"""
Pago Recibido - PayInTable

Se ha recibido un pago exitoso:

Mesa: {account.table.number}
Total: {self._format_currency(account.total)}
Propina: {self._format_currency(account.tip)}
Método de Pago: {payment_method}
Fecha: {account.paid_at.strftime('%d/%m/%Y %H:%M:%S') if account.paid_at else 'N/A'}

Este es un mensaje automático de PayInTable.
            """.strip()

            # Send email via SES
            response = self.ses_client.send_email(
                Source=self.sender,
                Destination={"ToAddresses": [restaurant_email]},
                Message={
                    "Subject": {
                        "Data": f"Pago Recibido - Mesa {account.table.number}",
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                        "Text": {"Data": text_content, "Charset": "UTF-8"},
                    },
                },
            )

            logger.info(
                f"Payment notification email sent: "
                f"account={account.id}, to={restaurant_email}, "
                f"message_id={response.get('MessageId')}"
            )

            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"AWS SES error sending email: {error_code} - {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            return False


# Singleton instance
email_service = EmailService()


async def send_payment_notification(
    account: Account,
    payment_method: str,
) -> bool:
    """
    Convenience function to send payment notification.

    This is called from webhooks after marking account as paid.
    Runs in executor since boto3 is synchronous.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        email_service.send_payment_notification,
        account,
        payment_method,
    )
