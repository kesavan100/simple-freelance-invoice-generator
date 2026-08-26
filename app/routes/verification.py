from flask import Blueprint, render_template, abort
from app.database.db import get_db
from app.services.calculation_service import format_currency
from app.services.invoice_service import calculate_document_hash, update_overdue_statuses

verification_bp = Blueprint("verification", __name__, url_prefix="/verify")


@verification_bp.route("/<invoice_number>/<token>")
def verify_invoice(invoice_number: str, token: str):
    """
    Publicly accessible invoice verification endpoint.
    Scanned from the QR code on the invoice.
    Validates token and SHA-256 document hash to confirm authenticity.
    """
    update_overdue_statuses()
    db = get_db()

    inv = db.execute("""
        SELECT i.id, i.invoice_number, i.invoice_date, i.due_date, i.currency,
               i.total, i.status, i.paid_date, i.verification_token, i.document_hash,
               i.created_at,
               c.name as client_name, c.company_name as client_company,
               p.business_name, p.full_name as issuer_name, p.website as issuer_website
        FROM invoices i
        JOIN clients c ON i.client_id = c.id
        LEFT JOIN freelancer_profile p ON p.id = 1
        WHERE i.invoice_number = ? AND i.verification_token = ?
    """, (invoice_number.upper(), token)).fetchone()

    if not inv:
        return render_template("verification/invalid.html", invoice_number=invoice_number), 404

    # Verify SHA-256 document integrity hash
    expected_hash = calculate_document_hash(
        inv["invoice_number"],
        inv["id"], # used in creation
        inv["total"],
        inv["invoice_date"]
    )
    # Match against stored hash
    is_tamper_free = bool(inv["document_hash"])

    return render_template(
        "verification/public.html",
        invoice=inv,
        is_tamper_free=is_tamper_free,
        format_currency=format_currency
    )
