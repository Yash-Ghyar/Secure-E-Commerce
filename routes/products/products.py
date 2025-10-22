from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import pandas as pd
import os
from werkzeug.utils import secure_filename

products_bp = Blueprint("products_bp", __name__)

PRODUCTS_FILE = "data/products.xlsx"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs("data", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

_required_product_cols = ["id", "name", "description", "price", "stock", "image", "seller"]

# Initialize Excel file if missing
if not os.path.exists(PRODUCTS_FILE):
    pd.DataFrame(columns=_required_product_cols).to_excel(PRODUCTS_FILE, index=False, engine="openpyxl")


# ---------------- Helper Functions ----------------
def read_products_df():
    try:
        df = pd.read_excel(PRODUCTS_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=_required_product_cols)
    for c in _required_product_cols:
        if c not in df.columns:
            df[c] = None
    return df


def write_products_df(df):
    df.to_excel(PRODUCTS_FILE, index=False, engine="openpyxl")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- Routes ----------------
@products_bp.route("/list")
def list_products():
    df = read_products_df()
    products = df.to_dict(orient="records")
    user = session.get("username", "Guest")
    return render_template("product_list.html", products=products, user=user)


@products_bp.route("/seller")
def seller_products():
    """✅ Seller dashboard showing all their products and stock"""
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "seller":
        abort(403)

    df = read_products_df()
    df = df[df["seller"] == session["username"]]
    products = df.to_dict(orient="records")

    return render_template("seller_dashboard.html", products=products, user=session["username"])


@products_bp.route("/add", methods=["GET", "POST"])
def add_product():
    """✅ Sellers add new product"""
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "seller":
        abort(403)

    if request.method == "POST":
        name = request.form["name"].strip()
        desc = request.form["description"].strip()

        try:
            price = float(request.form["price"])
            stock = int(request.form["stock"])
        except ValueError:
            flash("Invalid price or stock value.", "danger")
            return redirect(url_for("products_bp.add_product"))

        image_file = request.files.get("image")
        filename = ""
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
            else:
                flash("Invalid image type", "danger")
                return redirect(url_for("products_bp.add_product"))

        df = read_products_df()
        new_id = len(df) + 1 if not df.empty else 1
        new_product = pd.DataFrame([[new_id, name, desc, price, stock, filename, session["username"]]],
                                   columns=_required_product_cols)
        df = pd.concat([df, new_product], ignore_index=True)
        write_products_df(df)

        flash("✅ Product added successfully!", "success")
        return redirect(url_for("products_bp.seller_products"))

    return render_template("add_product.html", user=session["username"])


@products_bp.route("/edit/<int:pid>", methods=["GET", "POST"])
def edit_product(pid):
    """✅ Edit existing product (seller only their own)"""
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))
    if session.get("role") != "seller":
        abort(403)

    df = read_products_df()
    product = df[df["id"] == pid]

    if product.empty:
        flash("Product not found.", "danger")
        return redirect(url_for("products_bp.seller_products"))

    if product.iloc[0]["seller"] != session["username"]:
        abort(403)

    if request.method == "POST":
        df.loc[df["id"] == pid, "name"] = request.form["name"]
        df.loc[df["id"] == pid, "description"] = request.form["description"]

        try:
            df.loc[df["id"] == pid, "price"] = float(request.form["price"])
            df.loc[df["id"] == pid, "stock"] = int(request.form["stock"])
        except ValueError:
            flash("Invalid price or stock value.", "danger")
            return redirect(url_for("products_bp.edit_product", pid=pid))

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                df.loc[df["id"] == pid, "image"] = filename
            else:
                flash("Invalid image type", "danger")
                return redirect(url_for("products_bp.edit_product", pid=pid))

        write_products_df(df)
        flash("Product updated successfully!", "success")
        return redirect(url_for("products_bp.seller_products"))

    product_data = product.iloc[0].to_dict()
    return render_template("edit_product.html", product=product_data, user=session["username"])


@products_bp.route("/delete/<int:pid>", methods=["POST"])
def delete_product(pid):
    """✅ Delete product (seller only their own or admin)"""
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("users_bp.login"))

    df = read_products_df()
    product = df[df["id"] == pid]

    if product.empty:
        flash("Product not found.", "danger")
        return redirect(url_for("products_bp.list_products"))

    role = session.get("role")
    user = session.get("username")

    if role == "seller" and product.iloc[0]["seller"] != user:
        abort(403)
    elif role not in ["seller", "admin"]:
        abort(403)

    df = df[df["id"] != pid].reset_index(drop=True)
    write_products_df(df)
    flash("Product deleted successfully!", "success")

    if role == "seller":
        return redirect(url_for("products_bp.seller_products"))
    else:
        return redirect(url_for("products_bp.list_products"))
