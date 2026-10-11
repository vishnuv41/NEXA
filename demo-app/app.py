from flask import Flask, request, jsonify
import json
import time
import random

app = Flask(__name__)

# Demo data
PRODUCTS = [
    {"id": 1, "name": "Laptop Pro 15", "price": 1299.99, "category": "electronics"},
    {"id": 2, "name": "Wireless Headphones", "price": 199.99, "category": "electronics"},
    {"id": 3, "name": "Mechanical Keyboard", "price": 149.99, "category": "electronics"},
    {"id": 4, "name": "4K Monitor 27\"", "price": 449.99, "category": "electronics"},
    {"id": 5, "name": "USB-C Hub", "price": 79.99, "category": "accessories"},
]

USERS = {
    "admin": {"id": 1, "username": "admin", "role": "admin"},
    "user1": {"id": 2, "username": "user1", "role": "user"},
    "demo": {"id": 3, "username": "demo", "role": "user"},
}

CARTS = {}

@app.route("/")
def index():
    return jsonify({
        "service": "NEXA Demo Application",
        "version": "1.0",
        "endpoints": [
            "GET /",
            "GET /products",
            "GET /products/{id}",
            "GET /search",
            "POST /login",
            "GET /dashboard",
            "GET /users/{id}",
            "POST /cart",
            "POST /checkout",
            "POST /payment",
        ]
    })

@app.route("/products")
def get_products():
    category = request.args.get("category")
    products = PRODUCTS
    if category:
        products = [p for p in PRODUCTS if p["category"] == category]
    return jsonify({"products": products, "count": len(products)})

@app.route("/products/<int:product_id>")
def get_product(product_id):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)

@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = [p for p in PRODUCTS if q.lower() in p["name"].lower() or q.lower() in p["category"].lower()]
    return jsonify({"query": q, "results": results, "count": len(results)})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    
    if username in USERS and password == "password123":
        user = USERS[username]
        return jsonify({
            "success": True,
            "token": f"demo-token-{user['id']}-{int(time.time())}",
            "user": user,
        })
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route("/dashboard")
def dashboard():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401
    
    token = auth[7:]
    user_id = None
    for u, info in USERS.items():
        if f"demo-token-{info['id']}-" in token:
            user_id = info['id']
            break
    
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401
    
    return jsonify({
        "user_id": user_id,
        "stats": {
            "orders": random.randint(1, 20),
            "total_spent": round(random.uniform(50, 5000), 2),
            "wishlist_items": random.randint(0, 10),
        },
        "recent_activity": [
            {"action": "login", "timestamp": time.time() - 3600},
            {"action": "view_product", "product_id": 1, "timestamp": time.time() - 1800},
        ]
    })

@app.route("/users/<int:user_id>")
def get_user(user_id):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401
    
    user = next((u for u in USERS.values() if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(user)

@app.route("/cart", methods=["POST"])
def add_to_cart():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    token = auth[7:]
    user_id = None
    for u, info in USERS.items():
        if f"demo-token-{info['id']}-" in token:
            user_id = info['id']
            break
    
    if user_id not in CARTS:
        CARTS[user_id] = []
    
    CARTS[user_id].append({"product_id": product_id, "quantity": quantity, "product": product})
    
    return jsonify({"success": True, "cart": CARTS[user_id]})

@app.route("/checkout", methods=["POST"])
def checkout():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401
    
    token = auth[7:]
    user_id = None
    for u, info in USERS.items():
        if f"demo-token-{info['id']}-" in token:
            user_id = info['id']
            break
    
    cart = CARTS.get(user_id, [])
    if not cart:
        return jsonify({"error": "Cart is empty"}), 400
    
    total = sum(item["product"]["price"] * item["quantity"] for item in cart)
    
    order = {
        "id": random.randint(1000, 9999),
        "user_id": user_id,
        "items": cart,
        "total": total,
        "status": "pending_payment",
    }
    
    CARTS[user_id] = []
    
    return jsonify({"success": True, "order": order})

@app.route("/payment", methods=["POST"])
def payment():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json() or {}
    order_id = data.get("order_id")
    payment_method = data.get("payment_method", "card")
    
    return jsonify({
        "success": True,
        "transaction_id": f"txn_{random.randint(100000, 999999)}",
        "order_id": order_id,
        "amount": data.get("amount", 0),
        "method": payment_method,
        "status": "completed",
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)