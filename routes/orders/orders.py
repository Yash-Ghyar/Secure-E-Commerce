from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import pandas as pd
from datetime import datetime
import os

orders_bp = Blueprint("orders_bp", __name__)

ORDERS_FILE = "data/orders.xlsx"
PRODUCTS_FILE = "data/products.xlsx"

_required_order_cols = [
    "id", "product_id", "product_name", "price",
    "customer", "seller", "timestamp", "status"
]

os.makedirs("data", exist_ok=True)

if not os.path.exists(ORDERS_FILE):
    pd.DataFrame(columns=_required_order_cols).to_excel(ORDERS_FILE, index=False, engine="openpyxl")

if not os.path.exists(PRODUCTS_FILE):
    pd.DataFrame(columns=["id", "name", "description", "price", "stock", "image", "seller"]).to_excel(PRODUCTS_FILE, index=False, engine="openpyxl")


# ---------- Helper functions ----------
def read_orders_df():
    try:
        df = pd.read_excel(ORDERS_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=_required_order_cols)

    # Ensure all required columns exist
    for c in _required_order_cols:
        if c not in df.columns:
            df[c] = None

    # Drop completely blank rows (e.g., caused by Excel)
    df = df.dropna(subset=["product_name"], how="all")

    # Fix ID column: fill NaN and convert safely to int
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["id"] = df["id"].fillna(0).astype(int)

    # Reassign IDs if duplicates or zeros exist
    if df["id"].duplicated().any() or (df["id"] == 0).any():
        df = df.reset_index(drop=True)
        df["id"] = range(1, len(df) + 1)

    return df


def write_orders_df(df):
    df.to_excel(ORDERS_FILE, index=False, engine="openpyxl")


def read_products_df():
    try:
        df = pd.read_excel(PRODUCTS_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=["id", "name", "description", "price", "stock", "image", "seller"])
    return df


def write_products_df(df):
    df.to_excel(PRODUCTS_FILE, index=False, engine="openpyxl")


# ---------- Routes ----------
@orders_bp.route("/buy/<int:pid>", methods=["GET", "POST"])
def buy_product(pid):
    if "username" not in session:
        flash("Please login to buy products", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "customer":
        abort(403)

    products_df = read_products_df()
    product = products_df[products_df["id"] == pid]
    if product.empty:
        flash("Product not found", "danger")
        return redirect(url_for("products_bp.list_products"))

    p = product.iloc[0]
    stock = int(p["stock"]) if pd.notna(p["stock"]) else 0
    if stock <= 0:
        flash("Product out of stock!", "danger")
        return redirect(url_for("products_bp.list_products"))

    # Handle quantity
    quantity = 1
    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", 1))
        except ValueError:
            quantity = 1
        if quantity < 1 or quantity > stock:
            flash("Invalid quantity.", "warning")
            return redirect(url_for("orders_bp.buy_product", pid=pid))

    orders_df = read_orders_df()
    new_id = 1 if orders_df.empty else int(orders_df["id"].max()) + 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_order = pd.DataFrame(
        [[new_id, pid, p["name"], p["price"], session["username"], p["seller"], timestamp, "Pending"]],
        columns=_required_order_cols
    )

    orders_df = pd.concat([orders_df, new_order], ignore_index=True)
    write_orders_df(orders_df)

    # Decrease stock
    products_df.loc[products_df["id"] == pid, "stock"] = stock - quantity
    write_products_df(products_df)

    flash("Order placed successfully!", "success")
    return redirect(url_for("orders_bp.customer_orders"))


@orders_bp.route("/customer")
def customer_orders():
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "customer":
        abort(403)

    df = read_orders_df()
    user_orders = df[df["customer"] == session["username"]]
    orders = user_orders.sort_values("timestamp", ascending=False).to_dict(orient="records")
    return render_template("orders.html", orders=orders, user=session["username"], role="customer")


@orders_bp.route("/seller")
def seller_orders():
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "seller":
        abort(403)

    df = read_orders_df()
    seller_orders = df[df["seller"] == session["username"]]
    orders = seller_orders.sort_values("timestamp", ascending=False).to_dict(orient="records")
    return render_template("orders.html", orders=orders, user=session["username"], role="seller")


@orders_bp.route("/admin_orders")
def admin_orders():
    if "username" not in session or session.get("role") != "admin":
        flash("Unauthorized access", "danger")
        return redirect(url_for("users_bp.login"))

    df = read_orders_df()

    # 🧩 Ensure timestamp consistency
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    df = df.sort_values("timestamp", ascending=False, na_position="last")

    orders = df.to_dict(orient="records")
    return render_template("orders.html", orders=orders, role="admin")


@orders_bp.route("/update/<int:oid>", methods=["POST"])
def update_order_status(oid):
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") not in ["seller", "admin"]:
        abort(403)

    new_status = request.form.get("status")
    df = read_orders_df()

    if oid not in df["id"].values:
        flash("Order not found", "danger")
        return redirect(url_for("orders_bp.admin_orders"))

    df.loc[df["id"] == oid, "status"] = new_status
    write_orders_df(df)

    flash("Order status updated successfully!", "success")

    if session.get("role") == "seller":
        return redirect(url_for("orders_bp.seller_orders"))
    else:
        return redirect(url_for("orders_bp.admin_orders"))
