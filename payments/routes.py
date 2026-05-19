"""
M-Pesa Payment Routes
"""
from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from database import db
from auth.models import User, Transaction
from payments.mpesa import mpesa
import json
from datetime import datetime

mpesa_bp = Blueprint("mpesa", __name__, url_prefix="/payments/mpesa")


@mpesa_bp.route("/deposit", methods=["GET", "POST"])
@login_required
def initiate_deposit():
    """Start an STK Push deposit"""
    if request.method == "GET":
        return render_template("payments/mpesa_deposit.html")

    try:
        phone = request.form.get("phone", "").strip()
        amount_str = request.form.get("amount", "0").strip()

        try:
            amount = float(amount_str)
        except ValueError:
            flash("Invalid amount entered", "danger")
            return redirect(url_for("mpesa.initiate_deposit"))

        # Validations
        if amount < 1:
            flash("Minimum deposit is KES 1", "danger")
            return redirect(url_for("mpesa.initiate_deposit"))

        if not phone:
            flash("Phone number is required", "danger")
            return redirect(url_for("mpesa.initiate_deposit"))

        # Create pending transaction
        reference = Transaction.generate_reference()
        txn = Transaction(
            user_id=current_user.id,
            transaction_type="DEPOSIT",
            amount=amount,
            payment_method="MPESA",
            mpesa_phone=phone,
            reference_id=reference,
            status="PENDING",
            notes=f"M-Pesa STK Push initiated for KES {amount}"
        )
        db.session.add(txn)
        db.session.commit()

        # Initiate STK Push
        result = mpesa.stk_push(
            phone=phone,
            amount=amount,
            account_reference=reference,
            description=f"Deposit {reference}"
        )

        if result.get("success"):
            txn.payment_details = json.dumps({
                "checkout_request_id": result.get("checkout_request_id"),
                "merchant_request_id": result.get("merchant_request_id")
            })
            txn.status = "PROCESSING"
            db.session.commit()

            flash(f"STK Push sent to {phone}. Enter your M-Pesa PIN to complete payment.", "success")
            return redirect(url_for("mpesa.check_status", reference=reference))
        else:
            txn.status = "FAILED"
            txn.notes = f"STK Push failed: {result.get('error')}"
            db.session.commit()
            flash(f"Payment failed: {result.get('error')}", "danger")
            return redirect(url_for("mpesa.initiate_deposit"))

    except Exception as e:
        print(f"[MPESA DEPOSIT] Error: {e}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("mpesa.initiate_deposit"))


@mpesa_bp.route("/status/<reference>")
@login_required
def check_status(reference):
    """Check the status of an STK Push transaction"""
    txn = Transaction.query.filter_by(
        reference_id=reference,
        user_id=current_user.id
    ).first_or_404()

    return render_template("payments/mpesa_status.html", transaction=txn)


@mpesa_bp.route("/check/<reference>")
@login_required
def check_ajax(reference):
    """AJAX endpoint to check transaction status"""
    txn = Transaction.query.filter_by(
        reference_id=reference,
        user_id=current_user.id
    ).first()

    if not txn:
        return jsonify({"status": "NOT_FOUND"}), 404

    # Query Safaricom if still processing
    if txn.status == "PROCESSING" and txn.payment_details:
        try:
            details = json.loads(txn.payment_details)
            checkout_id = details.get("checkout_request_id")

            if checkout_id:
                result = mpesa.query_transaction(checkout_id)
                result_code = result.get("ResultCode")

                if result_code == "0" or result_code == 0:
                    txn.status = "COMPLETED"
                    txn.completed_at = datetime.utcnow()
                    current_user.balance += txn.amount
                    current_user.total_deposited += txn.amount
                    current_user.has_deposited = True
                    db.session.commit()
                elif str(result_code) in ["1032", "1037", "1"]:
                    txn.status = "REJECTED"
                    txn.notes = result.get("ResultDesc", "Transaction cancelled")
                    db.session.commit()
        except Exception as e:
            print(f"[MPESA CHECK] Error: {e}")

    return jsonify({
        "status": txn.status,
        "amount": txn.amount,
        "reference": txn.reference_id,
        "balance": current_user.balance
    })


@mpesa_bp.route("/callback", methods=["POST"])
def callback():
    """M-Pesa callback URL - Safaricom calls this on payment completion"""
    try:
        data = request.get_json()
        print(f"[MPESA CALLBACK] Received: {json.dumps(data, indent=2)}")

        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})

        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        checkout_id = stk_callback.get("CheckoutRequestID")

        # Find transaction
        transactions = Transaction.query.filter_by(status="PROCESSING").all()
        txn = None
        for t in transactions:
            if t.payment_details:
                try:
                    details = json.loads(t.payment_details)
                    if details.get("checkout_request_id") == checkout_id:
                        txn = t
                        break
                except:
                    continue

        if not txn:
            print(f"[MPESA CALLBACK] Transaction not found for {checkout_id}")
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

        if result_code == 0:
            # Success - extract payment metadata
            metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            mpesa_code = ""

            for item in metadata:
                if item.get("Name") == "MpesaReceiptNumber":
                    mpesa_code = item.get("Value")

            txn.status = "COMPLETED"
            txn.mpesa_code = mpesa_code
            txn.completed_at = datetime.utcnow()
            txn.notes = f"Payment successful. M-Pesa code: {mpesa_code}"

            # Credit user balance
            user = User.query.get(txn.user_id)
            user.balance += txn.amount
            user.total_deposited += txn.amount
            user.has_deposited = True

            db.session.commit()
            print(f"[MPESA CALLBACK] SUCCESS - Credited {txn.amount} to user {user.email}")
        else:
            # Failed
            txn.status = "REJECTED"
            txn.notes = f"Failed: {result_desc}"
            db.session.commit()
            print(f"[MPESA CALLBACK] FAILED - {result_desc}")

        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        print(f"[MPESA CALLBACK] Error: {e}")
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})
