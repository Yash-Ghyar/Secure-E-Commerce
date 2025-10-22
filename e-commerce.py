from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from routes.users.users import users_bp
from routes.products.products import products_bp
from routes.orders.orders import orders_bp
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
# change SECRET_KEY before production
app.secret_key = "supersecurekey123"

# CSRF protection
csrf = CSRFProtect(app)
csrf.init_app(app)

# upload & session config
app.config['UPLOAD_FOLDER'] = os.path.join('static','uploads')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# register blueprints
app.register_blueprint(users_bp, url_prefix="/users")
app.register_blueprint(products_bp, url_prefix="/products")
app.register_blueprint(orders_bp, url_prefix="/orders")

@app.route("/")
def home():
    return render_template("home.html")

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", message="403 Forbidden: Access Denied"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", message="404 Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", message="500 Internal Server Error"), 500

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("static/uploads", exist_ok=True)
    app.run(debug=True)
