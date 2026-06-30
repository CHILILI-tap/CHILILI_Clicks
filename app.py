from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database import db
from models import User, WalletFunding, Transaction, Notification
import uuid
import csv
from io import StringIO
from flask import Response


def create_notification(user_id, title, message):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=False
    )

    db.session.add(notification)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def generate_reference(prefix="CHL"):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        not_robot = request.form.get("not_robot")

        if not not_robot:
            flash("Please confirm that you are not a robot.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists. Please login.", "danger")
            return redirect(url_for("login"))

        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password=generate_password_hash(password),
            wallet_balance=0.0
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        not_robot = request.form.get("not_robot")

        if not not_robot:
            flash("Please confirm that you are not a robot.", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        login_user(user)
        flash("Login successful.", "success")

        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    total_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).count()

    successful_payments = Transaction.query.filter_by(
        user_id=current_user.id,
        status="successful"
    ).count()

    pending_transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        status="pending"
    ).count()

    failed_transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        status="failed"
    ).count()

    all_successful = Transaction.query.filter_by(
        user_id=current_user.id,
        status="successful"
    ).all()

    total_amount_spent = sum(txn.amount for txn in all_successful)

    latest_transaction = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.created_at.desc()).first()

    recent_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.created_at.desc()).limit(5).all()

    # -------- Chart Data --------

    chart_data = {
        "Wallet Funding": 0,
        "Airtime Purchase": 0,
        "Data Purchase": 0,
        "Electricity Payment": 0,
        "TV Subscription": 0
    }

    for txn in all_successful:
        if txn.service_type in chart_data:
            chart_data[txn.service_type] += 1

    chart_labels = list(chart_data.keys())
    chart_values = list(chart_data.values())

    return render_template(
        "user_dashboard.html",
        user=current_user,
        total_transactions=total_transactions,
        successful_payments=successful_payments,
        pending_transactions=pending_transactions,
        failed_transactions=failed_transactions,
        total_amount_spent=total_amount_spent,
        latest_transaction=latest_transaction,
        recent_transactions=recent_transactions,
        chart_labels=chart_labels,
        chart_values=chart_values
    )

@app.route("/fund-wallet", methods=["GET", "POST"])
@login_required
def fund_wallet():
    if request.method == "POST":
        amount = request.form.get("amount")
        proof_text = request.form.get("proof_text")

        try:
            amount = float(amount)
        except ValueError:
            flash("Invalid amount.", "danger")
            return redirect(url_for("fund_wallet"))

        if amount <= 0:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for("fund_wallet"))

        funding_request = WalletFunding(
            user_id=current_user.id,
            amount=amount,
            proof_text=proof_text,
            status="pending"
        )

        transaction = Transaction(
            user_id=current_user.id,
            service_type="Wallet Funding",
            provider="Manual Transfer",
            phone_or_meter=proof_text,
            amount=amount,
            status="pending",
            reference=generate_reference("FUND")
        )

        db.session.add(funding_request)
        db.session.add(transaction)
        db.session.commit()

        flash("Wallet funding request submitted. Waiting for admin approval.", "success")
        return redirect(url_for("transactions"))

    return render_template("fund_wallet.html", user=current_user)


@app.route("/buy-airtime", methods=["GET", "POST"])
@login_required
def buy_airtime():
    if request.method == "POST":
        provider = request.form.get("provider")
        phone_number = request.form.get("phone_number")
        amount = request.form.get("amount")

        try:
            amount = float(amount)
        except ValueError:
            flash("Invalid amount.", "danger")
            return redirect(url_for("buy_airtime"))

        if amount <= 0:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for("buy_airtime"))

        if current_user.wallet_balance < amount:
            flash("Insufficient wallet balance. Please fund your wallet.", "danger")
            return redirect(url_for("buy_airtime"))

        current_user.wallet_balance -= amount

        transaction = Transaction(
            user_id=current_user.id,
            service_type="Airtime Purchase",
            provider=provider,
            phone_or_meter=phone_number,
            amount=amount,
            status="successful",
            reference=generate_reference("AIR")
        )

        db.session.add(transaction)

        create_notification(
            current_user.id,
            "Airtime Purchase Successful",
            f"Your ₦{amount:.2f} airtime purchase for {phone_number} on {provider} was successful."
        )

        db.session.commit()

        flash("Airtime purchase successful.", "success")
        return redirect(url_for("transactions"))

    return render_template("buy_airtime.html", user=current_user)


@app.route("/buy-data", methods=["GET", "POST"])
@login_required
def buy_data():
    plan_prices = {
        "500MB - ₦200": 200.0,
        "1GB - ₦350": 350.0,
        "2GB - ₦700": 700.0,
        "5GB - ₦1500": 1500.0
    }

    if request.method == "POST":
        provider = request.form.get("provider")
        plan = request.form.get("plan")
        phone_number = request.form.get("phone_number")

        if not provider or not plan or not phone_number:
            flash("Please complete all fields.", "danger")
            return redirect(url_for("buy_data"))

        amount = plan_prices.get(plan)

        if amount is None:
            flash("Invalid data plan selected.", "danger")
            return redirect(url_for("buy_data"))

        if current_user.wallet_balance < amount:
            flash("Insufficient wallet balance. Please fund your wallet.", "danger")
            return redirect(url_for("buy_data"))

        current_user.wallet_balance -= amount

        transaction = Transaction(
            user_id=current_user.id,
            service_type="Data Purchase",
            provider=provider,
            phone_or_meter=f"{phone_number} ({plan})",
            amount=amount,
            status="successful",
            reference=generate_reference("DATA")
        )

        db.session.add(transaction)

        create_notification(
            current_user.id,
            "Data Purchase Successful",
            f"Your {plan} subscription for {phone_number} on {provider} was successful. ₦{amount:.2f} has been deducted from your wallet."
        )

        db.session.commit()

        flash("Data purchase successful.", "success")
        return redirect(url_for("transactions"))

    return render_template("buy_data.html", user=current_user)


@app.route("/pay-electricity", methods=["GET", "POST"])
@login_required
def pay_electricity():
    if request.method == "POST":
        provider = request.form.get("provider")
        meter_number = request.form.get("meter_number")
        amount = request.form.get("amount")

        try:
            amount = float(amount)
        except ValueError:
            flash("Invalid amount.", "danger")
            return redirect(url_for("pay_electricity"))

        if amount <= 0:
            flash("Enter a valid amount.", "danger")
            return redirect(url_for("pay_electricity"))

        if current_user.wallet_balance < amount:
            flash("Insufficient wallet balance. Please fund your wallet.", "danger")
            return redirect(url_for("pay_electricity"))

        current_user.wallet_balance -= amount

        demo_token = str(uuid.uuid4()).replace("-", "")[:20].upper()

        transaction = Transaction(
            user_id=current_user.id,
            service_type="Electricity Payment",
            provider=provider,
            phone_or_meter=f"{meter_number} | Token: {demo_token}",
            amount=amount,
            status="successful",
            reference=generate_reference("ELEC")
        )

        db.session.add(transaction)
        create_notification(
            current_user.id,
            "Electricity Payment Successful",
            f"Your electricity payment for {meter_number} on {provider} was successful. ₦{amount:.2f} has been deducted from your wallet."
        )
        db.session.commit()

        flash(f"Electricity payment successful. Demo Token: {demo_token}", "success")
        return redirect(url_for("transactions"))

    return render_template("pay_electricity.html", user=current_user)


@app.route("/pay-tv", methods=["GET", "POST"])
@login_required
def pay_tv():
    plan_prices = {
        "DSTV Padi - ₦2500": 2500.0,
        "DSTV Yanga - ₦3500": 3500.0,
        "GOtv Jolli - ₦3300": 3300.0,
        "GOtv Max - ₦4850": 4850.0,
        "StarTimes Basic - ₦2200": 2200.0,
        "StarTimes Classic - ₦3200": 3200.0
    }

    if request.method == "POST":
        provider = request.form.get("provider")
        plan = request.form.get("plan")
        smartcard_number = request.form.get("smartcard_number")

        if not provider or not plan or not smartcard_number:
            flash("Please complete all fields.", "danger")
            return redirect(url_for("pay_tv"))

        amount = plan_prices.get(plan)

        if amount is None:
            flash("Invalid TV subscription plan selected.", "danger")
            return redirect(url_for("pay_tv"))

        if current_user.wallet_balance < amount:
            flash("Insufficient wallet balance. Please fund your wallet.", "danger")
            return redirect(url_for("pay_tv"))

        current_user.wallet_balance -= amount

        transaction = Transaction(
            user_id=current_user.id,
            service_type="TV Subscription",
            provider=provider,
            phone_or_meter=f"{smartcard_number} ({plan})",
            amount=amount,
            status="successful",
            reference=generate_reference("TV")
        )

        db.session.add(transaction)
        create_notification(
            current_user.id,
            "TV Subscription Payment Successful",
            f"Your TV subscription payment for {smartcard_number} on {provider} was successful. ₦{amount:.2f} has been deducted from your wallet."
        )
        db.session.commit()

        flash("TV subscription payment successful.", "success")
        return redirect(url_for("transactions"))

    return render_template("pay_tv.html", user=current_user)


@app.route("/transactions")
@login_required
def transactions():

    page = request.args.get("page", 1, type=int)

    search = request.args.get("search", "")
    service = request.args.get("service", "")
    status = request.args.get("status", "")

    # Admin sees every transaction.
    # Normal users only see their own.
    if current_user.role == "admin":
        query = Transaction.query
    else:
        query = Transaction.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            db.or_(
                Transaction.reference.ilike(f"%{search}%"),
                Transaction.provider.ilike(f"%{search}%"),
                Transaction.phone_or_meter.ilike(f"%{search}%"),
                Transaction.service_type.ilike(f"%{search}%")
            )
        )

    if service:
        query = query.filter(
            Transaction.service_type == service
        )

    if status:
        query = query.filter(
            Transaction.status == status
        )

    transactions = query.order_by(
        Transaction.created_at.desc()
    ).paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    return render_template(
        "transaction_history.html",
        user=current_user,
        transactions=transactions,
        search=search,
        service=service,
        status=status
    )


@app.route("/export-transactions")
@login_required
def export_transactions():
    if current_user.role == "admin":
        transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    else:
        transactions = Transaction.query.filter_by(
            user_id=current_user.id
        ).order_by(Transaction.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Reference",
        "User",
        "Service",
        "Provider",
        "Receiver/Meter/Card",
        "Amount",
        "Status",
        "Date"
    ])

    for txn in transactions:
        writer.writerow([
            txn.reference,
            txn.user.full_name if txn.user else "N/A",
            txn.service_type,
            txn.provider,
            txn.phone_or_meter,
            txn.amount,
            txn.status,
            txn.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=chilili_transactions.csv"

    return response

@app.route("/notifications")
@login_required
def notifications():

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()

    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()

    return render_template(
        "notifications.html",
        user=current_user,
        notifications=notifications,
        unread_count=unread_count
    )
@app.route("/notification/read/<int:id>")
@login_required
def read_notification(id):

    notification = Notification.query.get_or_404(id)

    if notification.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("notifications"))

    notification.is_read = True

    db.session.commit()

    return redirect(url_for("notifications"))
@app.route("/notification/delete/<int:id>")
@login_required
def delete_notification(id):

    notification = Notification.query.get_or_404(id)

    if notification.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("notifications"))

    db.session.delete(notification)

    db.session.commit()

    flash("Notification deleted.", "success")

    return redirect(url_for("notifications"))

@app.route("/ai-assistant", methods=["POST"])
@login_required
def ai_assistant():
    question = request.json.get("question", "").lower().strip()

    if not question:
        return jsonify({
            "reply": "Please type a question first."
        })

    user_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.created_at.desc()).all()

    total_spent = sum(
        txn.amount for txn in user_transactions
        if txn.status == "successful" and txn.service_type != "Wallet Funding"
    )

    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()

    if "balance" in question or "wallet" in question:
        reply = f"Your current wallet balance is ₦{current_user.wallet_balance:.2f}."

    elif "spent" in question or "spending" in question:
        reply = f"You have spent ₦{total_spent:.2f} on successful bill and service payments."

    elif "recent" in question or "transaction" in question or "history" in question:
        recent = user_transactions[:5]

        if not recent:
            reply = "You do not have any transactions yet."
        else:
            reply = "Here are your last 5 transactions:\n"
            for txn in recent:
                reply += f"- {txn.service_type}: ₦{txn.amount:.2f} ({txn.status})\n"

    elif "notification" in question or "alert" in question:
        reply = f"You have {unread_notifications} unread notification(s)."

    elif "fund" in question:
        reply = "To fund your wallet, click Fund Wallet, enter the amount and payment proof/reference, then submit for admin approval."

    elif "airtime" in question:
        reply = "To buy airtime, open Airtime, select your network, enter phone number and amount, then submit."

    elif "data" in question:
        reply = "To buy data, open Data, select network, choose a data plan, enter phone number and submit."

    elif "electricity" in question or "meter" in question:
        reply = "To pay electricity, open Electricity, select provider, enter meter number and amount, then submit."

    elif "tv" in question or "dstv" in question or "gotv" in question or "startimes" in question:
        reply = "To pay TV subscription, open TV Bills, select provider, plan, smartcard/IUC number and submit."

    elif "receipt" in question:
        reply = "To view a receipt, open Transactions and click View Receipt beside the transaction."

    else:
        reply = (
            "I can help with wallet balance, spending, recent transactions, "
            "notifications, funding, airtime, data, electricity, TV bills and receipts."
        )

    return jsonify({
        "reply": reply
    })



@app.route("/receipt/<int:transaction_id>")
@login_required
def receipt(transaction_id):
    txn = Transaction.query.get_or_404(transaction_id)

    if txn.user_id != current_user.id and current_user.role != "admin":
        flash("You are not authorized to view this receipt.", "danger")
        return redirect(url_for("transactions"))

    return render_template("receipt.html", user=current_user, txn=txn)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")

        if not full_name or not phone:
            flash("Please complete all fields.", "danger")
            return redirect(url_for("profile"))

        current_user.full_name = full_name
        current_user.phone = phone

        db.session.commit()

        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=current_user)


@app.route("/admin-dashboard")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("You are not authorized to access the admin dashboard.", "danger")
        return redirect(url_for("dashboard"))

    pending_count = WalletFunding.query.filter_by(status="pending").count()
    approved_count = WalletFunding.query.filter_by(status="approved").count()
    rejected_count = WalletFunding.query.filter_by(status="rejected").count()

    total_users = User.query.count()
    total_transactions = Transaction.query.count()

    successful_transactions = Transaction.query.filter_by(status="successful").count()
    pending_transactions = Transaction.query.filter_by(status="pending").count()
    failed_transactions = Transaction.query.filter_by(status="failed").count()

    total_wallet_balance = db.session.query(
        db.func.coalesce(db.func.sum(User.wallet_balance), 0)
    ).scalar()

    total_approved_funding = db.session.query(
        db.func.coalesce(db.func.sum(WalletFunding.amount), 0)
    ).filter(WalletFunding.status == "approved").scalar()

    total_successful_amount = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0)
    ).filter(Transaction.status == "successful").scalar()

    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    recent_transactions = Transaction.query.order_by(
        Transaction.created_at.desc()
    ).limit(6).all()

    recent_funding_requests = WalletFunding.query.order_by(
        WalletFunding.created_at.desc()
    ).limit(6).all()

    funding_chart_labels = ["Pending", "Approved", "Rejected"]
    funding_chart_values = [pending_count, approved_count, rejected_count]

    transaction_chart_labels = ["Successful", "Pending", "Failed"]
    transaction_chart_values = [
        successful_transactions,
        pending_transactions,
        failed_transactions
    ]

    service_labels = [
        "Wallet Funding",
        "Airtime Purchase",
        "Data Purchase",
        "Electricity Payment",
        "TV Subscription"
    ]

    service_values = []
    for service in service_labels:
        count = Transaction.query.filter_by(service_type=service).count()
        service_values.append(count)

    return render_template(
        "admin_dashboard.html",
        user=current_user,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        total_users=total_users,
        total_transactions=total_transactions,
        total_wallet_balance=total_wallet_balance,
        total_approved_funding=total_approved_funding,
        total_successful_amount=total_successful_amount,
        recent_users=recent_users,
        recent_transactions=recent_transactions,
        recent_funding_requests=recent_funding_requests,
        funding_chart_labels=funding_chart_labels,
        funding_chart_values=funding_chart_values,
        transaction_chart_labels=transaction_chart_labels,
        transaction_chart_values=transaction_chart_values,
        service_labels=service_labels,
        service_values=service_values
    )


@app.route("/admin-funding")
@login_required
def admin_funding():
    if current_user.role != "admin":
        flash("You are not authorized.", "danger")
        return redirect(url_for("dashboard"))

    requests = WalletFunding.query.order_by(WalletFunding.created_at.desc()).all()

    return render_template("admin_funding.html", user=current_user, requests=requests)


@app.route("/approve-funding/<int:request_id>")
@login_required
def approve_funding(request_id):
    if current_user.role != "admin":
        flash("You are not authorized.", "danger")
        return redirect(url_for("dashboard"))

    funding_request = WalletFunding.query.get_or_404(request_id)

    if funding_request.status != "pending":
        flash("This request has already been processed.", "danger")
        return redirect(url_for("admin_funding"))

    user = User.query.get(funding_request.user_id)
    user.wallet_balance += funding_request.amount
    funding_request.status = "approved"

    transaction = Transaction.query.filter_by(
        user_id=funding_request.user_id,
        amount=funding_request.amount,
        service_type="Wallet Funding",
        status="pending"
    ).first()

    if transaction:
        transaction.status = "successful"

    create_notification(
        user_id=funding_request.user_id,
        title="Funding Approved",
        message=f"Your funding request of ₦{funding_request.amount} has been approved."
    )

    db.session.commit()

    flash("Funding approved and wallet updated.", "success")
    return redirect(url_for("admin_funding"))


@app.route("/reject-funding/<int:request_id>")
@login_required
def reject_funding(request_id):
    if current_user.role != "admin":
        flash("You are not authorized.", "danger")
        return redirect(url_for("dashboard"))

    funding_request = WalletFunding.query.get_or_404(request_id)

    if funding_request.status != "pending":
        flash("This request has already been processed.", "danger")
        return redirect(url_for("admin_funding"))

    funding_request.status = "rejected"

    transaction = Transaction.query.filter_by(
        user_id=funding_request.user_id,
        amount=funding_request.amount,
        service_type="Wallet Funding",
        status="pending"
    ).first()

    if transaction:
        transaction.status = "failed"

    create_notification(
        user_id=funding_request.user_id,
        title="Funding Rejected",
        message=f"Your funding request of ₦{funding_request.amount} has been rejected."
    )

    db.session.commit()

    flash("Funding request rejected.", "success")
    return redirect(url_for("admin_funding"))





@app.route("/admin-transactions")
@login_required
def admin_transactions():
    if current_user.role != "admin":
        flash("You are not authorized.", "danger")
        return redirect(url_for("dashboard"))

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    service = request.args.get("service", "")
    status = request.args.get("status", "")

    query = Transaction.query

    if search:
        query = query.filter(
            db.or_(
                Transaction.reference.ilike(f"%{search}%"),
                Transaction.provider.ilike(f"%{search}%"),
                Transaction.phone_or_meter.ilike(f"%{search}%"),
                Transaction.service_type.ilike(f"%{search}%")
            )
        )

    if service:
        query = query.filter(Transaction.service_type == service)

    if status:
        query = query.filter(Transaction.status == status)

    transactions = query.order_by(
        Transaction.created_at.desc()
    ).paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    return render_template(
        "admin_transactions.html",
        user=current_user,
        transactions=transactions,
        search=search,
        service=service,
        status=status
    )


@app.route("/admin-users")
@login_required
def admin_users():
    if current_user.role != "admin":
        flash("You are not authorized.", "danger")
        return redirect(url_for("dashboard"))

    search = request.args.get("search", "").strip()

    query = User.query

    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"),
                User.role.ilike(f"%{search}%")
            )
        )

    users = query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin_users.html",
        user=current_user,
        users=users,
        search=search
    )


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        if len(new_password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("change_password"))

        current_user.password = generate_password_hash(new_password)

        create_notification(
    current_user.id,
    "Password Changed",
    "Your account password was changed successfully. If you did not perform this action, contact the administrator immediately."
)
        db.session.commit()

        flash("Password changed successfully.", "success")
        return redirect(url_for("profile"))

    return render_template(
        "change_password.html",
        user=current_user
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

@app.route("/setup-admin")
def setup_admin():
    existing_admin = User.query.filter_by(email="admin@chilili.com").first()

    if existing_admin:
        return "Admin already exists."

    admin = User(
        full_name="CHILILI Admin",
        email="admin@chilili.com",
        phone="08000000000",
        password=generate_password_hash("admin123"),
        wallet_balance=0.0,
        role="admin"
    )

    db.session.add(admin)
    db.session.commit()

    return "Admin created successfully."    
@app.route("/setup-users")
def setup_users():
    admin = User.query.filter_by(email="admin@chilili.com").first()

    if not admin:
        admin = User(
            full_name="CHILILI Admin",
            email="admin@chilili.com",
            phone="08000000000",
            password=generate_password_hash("admin123"),
            wallet_balance=0.0,
            role="admin"
        )
        db.session.add(admin)

    test_user = User.query.filter_by(email="test@gmail.com").first()

    if not test_user:
        test_user = User(
            full_name="Test User",
            email="test@gmail.com",
            phone="08012345678",
            password=generate_password_hash("test123"),
            wallet_balance=200000.0,
            role="user"
        )
        db.session.add(test_user)

    db.session.commit()

    return "Admin and test user created successfully."