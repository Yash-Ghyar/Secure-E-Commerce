import os
import pandas as pd

os.makedirs("data", exist_ok=True)

users_file = "data/users.xlsx"
if not os.path.exists(users_file):
    df_users = pd.DataFrame(columns=["username","password","role","active","created_at"])
    df_users.to_excel(users_file, index=False, engine="openpyxl")
    print("✅ users.xlsx created")
else:
    print("ℹ️ users.xlsx exists")

products_file = "data/products.xlsx"
if not os.path.exists(products_file):
    df_products = pd.DataFrame(columns=["id","name","description","price","stock","image","seller"])
    df_products.to_excel(products_file, index=False, engine="openpyxl")
    print("✅ products.xlsx created")
else:
    print("ℹ️ products.xlsx exists")

orders_file = "data/orders.xlsx"
if not os.path.exists(orders_file):
    df_orders = pd.DataFrame(columns=["id","product_id","product_name","price","customer","seller","timestamp","status"])
    df_orders.to_excel(orders_file, index=False, engine="openpyxl")
    print("✅ orders.xlsx created")
else:
    print("ℹ️ orders.xlsx exists")

sec_file = "data/security_log.csv"
if not os.path.exists(sec_file) or os.stat(sec_file).st_size==0:
    df_log = pd.DataFrame(columns=["username","status","timestamp"])
    df_log.to_csv(sec_file, index=False)
    print("✅ security_log.csv created")
else:
    print("ℹ️ security_log.csv exists")

os.makedirs("static/uploads", exist_ok=True)
print("🎉 Setup done.")
