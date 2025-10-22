from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

users_bp = Blueprint("users_bp", __name__)

USERS_FILE = "data/users.xlsx"
SECURITY_LOG = "data/security_log.csv"

os.makedirs("data", exist_ok=True)
_required_user_cols = ["username", "password", "role", "active", "created_at"]

# Initialize files if missing or fix columns
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=_required_user_cols).to_excel(USERS_FILE, index=False, engine="openpyxl")
else:
    try:
        df_check = pd.read_excel(USERS_FILE, engine="openpyxl")
        for c in _required_user_cols:
            if c not in df_check.columns:
                df_check[c] = None
        df_check.to_excel(USERS_FILE, index=False, engine="openpyxl")
    except Exception:
        pd.DataFrame(columns=_required_user_cols).to_excel(USERS_FILE, index=False, engine="openpyxl")

if not os.path.exists(SECURITY_LOG) or os.stat(SECURITY_LOG).st_size == 0:
    pd.DataFrame(columns=["username", "status", "timestamp"]).to_csv(SECURITY_LOG, index=False)


# ---------------- Helper Functions ----------------
def read_users_df():
    try:
        df = pd.read_excel(USERS_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=_required_user_cols)
    for c in _required_user_cols:
        if c not in df.columns:
            df[c] = None
    return df


def write_users_df(df):
    df.to_excel(USERS_FILE, index=False, engine="openpyxl")


def log_security(username, status):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = pd.DataFrame([[username, status, time]], columns=["username", "status", "timestamp"])
    if not os.path.exists(SECURITY_LOG) or os.stat(SECURITY_LOG).st_size == 0:
        entry.to_csv(SECURITY_LOG, index=False)
    else:
        try:
            log_df = pd.read_csv(SECURITY_LOG)
        except pd.errors.EmptyDataError:
            log_df = pd.DataFrame(columns=["username", "status", "timestamp"])
        log_df = pd.concat([log_df, entry], ignore_index=True)
        log_df.to_csv(SECURITY_LOG, index=False)


def admin_required():
    if "role" not in session or session.get("role") != "admin":
        abort(403)


# ---------------- Routes ----------------

@users_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form.get("role", "customer")

        if not username or not password:
            flash("Please enter both username and password.", "warning")
            return redirect(url_for("users_bp.register"))

        df = read_users_df()
        if username in df["username"].astype(str).values:
            flash("Username already exists. Try another one.", "warning")
            return redirect(url_for("users_bp.register"))

        hashed_password = generate_password_hash(password)
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_user = pd.DataFrame([[username, hashed_password, role, True, created]], columns=_required_user_cols)
        df = pd.concat([df, new_user], ignore_index=True)
        write_users_df(df)

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("users_bp.login"))

    return render_template("register.html")


@users_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        df = read_users_df()
        if username not in df["username"].astype(str).values:
            log_security(username, "Failed (No such user)")
            flash("Invalid username or password.", "danger")
            return redirect(url_for("users_bp.login"))

        user = df[df["username"] == username].iloc[0]

        if not bool(user.get("active", True)):
            log_security(username, "Failed (Inactive account)")
            flash("Account is deactivated.", "danger")
            return redirect(url_for("users_bp.login"))

        if check_password_hash(user["password"], password):
            session["username"] = username
            session["role"] = user["role"]
            log_security(username, "Success")
            flash("Login successful!", "success")

            # ✅ Correct redirection by role
            if user["role"] == "admin":
                return redirect(url_for("users_bp.admin_dashboard"))
            elif user["role"] == "seller":
                # ✅ Sellers now redirected to their product stock dashboard
                return redirect(url_for("products_bp.seller_products"))
            else:
                return redirect(url_for("users_bp.customer_dashboard"))
        else:
            log_security(username, "Failed (Wrong password)")
            flash("Invalid username or password.", "danger")
            return redirect(url_for("users_bp.login"))

    return render_template("login.html")


@users_bp.route("/dashboard")
def dashboard():
    if "username" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("users_bp.login"))

    role = session.get("role")
    if role == "admin":
        return redirect(url_for("users_bp.admin_dashboard"))
    elif role == "seller":
        return redirect(url_for("products_bp.seller_products"))
    else:
        return redirect(url_for("users_bp.customer_dashboard"))


@users_bp.route("/admin")
def admin_dashboard():
    if "username" not in session:
        return redirect(url_for("users_bp.login"))
    admin_required()
    df = read_users_df()
    total_users = len(df)
    total_sellers = len(df[df["role"] == "seller"])
    total_customers = len(df[df["role"] == "customer"])
    return render_template(
        "admin_dashboard.html",
        user=session["username"],
        total_users=total_users,
        total_sellers=total_sellers,
        total_customers=total_customers
    )


@users_bp.route("/seller")
def seller_dashboard():
    if "username" not in session:
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "seller":
        abort(403)
    return redirect(url_for("products_bp.seller_products"))  # ✅ Auto-redirect to seller products dashboard


@users_bp.route("/customer")
def customer_dashboard():
    if "username" not in session:
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "customer":
        abort(403)
    return render_template("customer_dashboard.html", user=session["username"])


@users_bp.route("/admin/users")
def admin_view_users():
    if "username" not in session:
        return redirect(url_for("users_bp.login"))
    admin_required()
    df = read_users_df()
    display_df = df.copy()
    if "password" in display_df.columns:
        display_df = display_df.drop(columns=["password"])
    users = display_df.to_dict(orient="records")
    return render_template("admin_users.html", users=users, user=session["username"])


@users_bp.route("/admin/toggle_active/<string:username>", methods=["POST"])
def admin_toggle_active(username):
    if "username" not in session:
        return redirect(url_for("users_bp.login"))
    admin_required()

    df = read_users_df()
    if username not in df["username"].astype(str).values:
        flash("User not found.", "warning")
        return redirect(url_for("users_bp.admin_view_users"))

    idx = df.index[df["username"] == username][0]
    current = bool(df.at[idx, "active"]) if pd.notna(df.at[idx, "active"]) else True
    df.at[idx, "active"] = not current
    write_users_df(df)

    action = "Reactivated" if df.at[idx, "active"] else "Deactivated"
    log_security(username, f"Admin {action} by {session.get('username')}")
    flash(f"User {action.lower()} successfully.", "success")
    return redirect(url_for("users_bp.admin_view_users"))


@users_bp.route("/admin/delete_user/<string:username>", methods=["POST"])
def admin_delete_user(username):
    if "username" not in session:
        return redirect(url_for("users_bp.login"))
    admin_required()

    df = read_users_df()
    if username not in df["username"].astype(str).values:
        flash("User not found.", "warning")
        return redirect(url_for("users_bp.admin_view_users"))

    if username == session.get("username"):
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("users_bp.admin_view_users"))

    df = df[df["username"] != username].reset_index(drop=True)
    write_users_df(df)
    log_security(username, f"Deleted by admin {session.get('username')}")
    flash("User deleted successfully.", "success")
    return redirect(url_for("users_bp.admin_view_users"))


@users_bp.route("/logout")
def logout():
    username = session.get("username", "unknown")
    session.clear()
    flash("You have been logged out successfully.", "info")
    log_security(username, "Logout")
    return redirect(url_for("users_bp.login"))
