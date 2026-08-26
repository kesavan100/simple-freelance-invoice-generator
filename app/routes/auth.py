from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import check_password_hash
from app.database.db import get_db, log_activity

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    """Decorator to require authenticated session on protected routes."""
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access your financial dashboard.", "info")
            return redirect(url_for("auth.login", next=request.url))
        return view_func(*args, **kwargs)
    return decorated_view


@auth_bp.before_app_request
def load_logged_in_user():
    """Loads user from session into flask global g before each request."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute("SELECT id, email, full_name, role FROM users WHERE id = ?", (user_id,)).fetchone()


@auth_bp.app_context_processor
def inject_current_user():
    """Injects current_user into all Jinja2 templates."""
    return {"current_user": g.user if hasattr(g, "user") else None}


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User Login Page."""
    if session.get("user_id"):
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "1"

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("auth/login.html", email=email)

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            session["user_name"] = user["full_name"]
            
            if remember:
                session.permanent = True

            log_activity("LOGIN", "USER", user["id"], f"User {user['email']} logged in successfully")
            flash(f"Welcome back, {user['full_name']}!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.home"))
        else:
            flash("Invalid email address or password. Please try again.", "error")
            return render_template("auth/login.html", email=email)

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """User Logout Endpoint."""
    user_id = session.get("user_id")
    if user_id:
        log_activity("LOGOUT", "USER", user_id, "User logged out")
    session.clear()
    flash("You have been signed out safely.", "success")
    return redirect(url_for("auth.login"))
