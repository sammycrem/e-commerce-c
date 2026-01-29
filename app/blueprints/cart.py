from flask import Blueprint, request, session, jsonify, render_template
from ..models import db, Variant, Product
from sqlalchemy.orm import joinedload

cart_bp = Blueprint('cart_bp', __name__)

@cart_bp.route('/api/cart', methods=['POST'])
def add_to_cart():
    data = request.get_json() or {}
    sku = data.get('sku')
    quantity = data.get('quantity', 1)

    if not sku or not isinstance(quantity, int) or quantity < 0:
        return jsonify({"error": "Invalid SKU or quantity"}), 400

    if 'cart' not in session:
        session['cart'] = {}

    variant = Variant.query.filter_by(sku=sku).first()
    if not variant:
        return jsonify({"error": f"Variant SKU {sku} not found"}), 404

    if quantity == 0:
        session['cart'].pop(sku, None)
    else:
        if quantity > variant.stock_quantity:
            return jsonify({"error": f"Not enough stock for {sku}. Only {variant.stock_quantity} available."}), 400
        session['cart'][sku] = quantity

    session.modified = True
    return get_cart()

@cart_bp.route('/api/cart', methods=['GET'])
def get_cart():
    cart_data = session.get('cart', {}) or {}
    if not cart_data:
        return jsonify({"items": [], "subtotal_cents": 0})

    variants = Variant.query.options(joinedload(Variant.product).joinedload(Product.images)).filter(Variant.sku.in_(list(cart_data.keys()))).all()

    items = []
    subtotal_cents = 0
    for variant in variants:
        quantity = cart_data.get(variant.sku, 0)
        final_price = int((variant.product.base_price_cents or 0) + (variant.price_modifier_cents or 0))
        line_total = final_price * quantity
        subtotal_cents += line_total

        image_url = None
        if variant.images:
            image_url = variant.images[0].url
        elif variant.product.images:
            image_url = variant.product.images[0].url

        items.append({
            "sku": variant.sku,
            "quantity": quantity,
            "product_name": variant.product.name,
            "color": variant.color_name,
            "size": variant.size,
            "unit_price_cents": final_price,
            "line_total_cents": line_total,
            "image_url": image_url
        })

    return jsonify({"items": items, "subtotal_cents": subtotal_cents})

@cart_bp.route('/cart')
def cart_page():
    return render_template('cart.html')

from flask import redirect, url_for

@cart_bp.route('/my-cart')
def my_cart_page():
    return redirect(url_for('cart_bp.cart_page'))
