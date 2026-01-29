from flask import Blueprint, request, jsonify, session, render_template
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Promotion, Order, OrderItem, Variant
from ..utils import calculate_totals_internal
from datetime import datetime, timezone
from math import ceil
import logging

logger = logging.getLogger(__name__)

checkout_bp = Blueprint('checkout_bp', __name__)

@checkout_bp.route('/api/apply-promo', methods=['POST'])
def apply_promo():
    data = request.get_json() or {}
    code = data.get('code')
    cart_subtotal = data.get('cart_subtotal_cents')
    user_id = current_user.id if current_user.is_authenticated else None

    if not code or cart_subtotal is None:
        return jsonify({"error": "Promo code and cart subtotal are required"}), 400

    promo = Promotion.query.filter_by(code=code, is_active=True).first()
    if not promo:
        return jsonify({"error": "Invalid promotion code"}), 404

    promo_valid_to = promo.valid_to
    if promo_valid_to and promo_valid_to.tzinfo is None:
        promo_valid_to = promo_valid_to.replace(tzinfo=timezone.utc)

    if promo_valid_to and promo_valid_to < datetime.now(timezone.utc):
        return jsonify({"error": "Promotion code has expired"}), 404

    if promo.user_id is not None and promo.user_id != user_id:
        return jsonify({"error": "This promotion code is not valid for your account"}), 403

    discount_cents = 0
    if promo.discount_type == 'PERCENT':
        discount_cents = int(ceil(cart_subtotal * (promo.discount_value / 100)))
    elif promo.discount_type == 'FIXED':
        discount_cents = int(promo.discount_value)

    session['promo_code'] = promo.code
    return jsonify({"code": promo.code, "discount_cents": discount_cents, "new_total_cents": cart_subtotal - discount_cents}), 200

@checkout_bp.route('/api/checkout', methods=['POST'])
def checkout():
    body = request.get_json() or {}
    shipping_country_iso = body.get('shipping_country_iso') or body.get('country_iso')
    user_id = current_user.id if current_user.is_authenticated else None

    # get cart from session
    cart_info = session.get('cart', {})
    if not cart_info:
        return jsonify({"error": "Cannot checkout with an empty cart"}), 400

    # create simple items list for calculation
    items = [{"sku": sku, "quantity": qty} for sku, qty in cart_info.items()]

    # calculate totals using helper
    calc_res = calculate_totals_internal(items, shipping_country_iso=shipping_country_iso, promo_code=body.get('promo_code'), user_id=user_id)

    subtotal = calc_res['subtotal_cents']
    discount = calc_res['discount_cents']
    vat = calc_res['vat_cents']
    shipping_cost = calc_res['shipping_cost_cents']
    total = calc_res['total_cents']

    try:
        with db.session.begin_nested():
            new_order = Order(
                status='PENDING',
                subtotal_cents=subtotal,
                discount_cents=discount,
                vat_cents=vat,
                shipping_cost_cents=shipping_cost,
                total_cents=total
            )
            # optionally store shipping country or address fields here
            db.session.add(new_order)
            db.session.flush()

            for item_data in items:
                variant = Variant.query.filter_by(sku=item_data['sku']).with_for_update().first()
                if not variant:
                    raise ValueError(f"Variant not found: {item_data['sku']}")
                if variant.stock_quantity < item_data['quantity']:
                    raise ValueError(f"Insufficient stock for {item_data['sku']}")
                variant.stock_quantity -= item_data['quantity']

                product_snapshot = {
                    "name": variant.product.name,
                    "product_sku": variant.product.product_sku,
                    "category": variant.product.category,
                    "weight_grams": variant.product.weight_grams,
                    "dimensions_json": variant.product.dimensions_json
                }
                unit_price = int((variant.product.base_price_cents or 0) + (variant.price_modifier_cents or 0))
                order_item = OrderItem(
                    order_id=new_order.id,
                    variant_sku=item_data['sku'],
                    quantity=item_data['quantity'],
                    unit_price_cents=unit_price,
                    product_snapshot=product_snapshot
                )
                db.session.add(order_item)

        db.session.commit()
        session.pop('cart', None)
        return jsonify({
            "message": "Order created successfully",
            "order_id": new_order.public_order_id,
            "subtotal_cents": subtotal,
            "discount_cents": discount,
            "vat_cents": vat,
            "shipping_cost_cents": shipping_cost,
            "total_cents": total
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Checkout failed")
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500

@checkout_bp.route('/webhooks/payment', methods=['POST'])
def handle_payment_webhook():
    data = request.get_json() or {}
    order_id = data.get('metadata', {}).get('public_order_id')
    event_type = data.get('type')
    if event_type == 'charge.succeeded' and order_id:
        order = Order.query.filter_by(public_order_id=order_id).first()
        if order and order.status == 'PENDING':
            order.status = 'PAID'
            db.session.commit()
            logger.info("Webhook: Order %s set to PAID", order.public_order_id)
            return jsonify({"status": "success"}), 200
        elif order:
            return jsonify({"status": "already_processed"}), 200
    return jsonify({"status": "ignored"}), 200

@checkout_bp.route('/api/calculate-totals', methods=['POST'])
def api_calculate_totals():
    data = request.get_json() or {}
    items = data.get('items', [])
    country_iso = data.get('shipping_country_iso')
    promo_code = data.get('promo_code')
    user_id = current_user.id if current_user.is_authenticated else None

    result = calculate_totals_internal(items, shipping_country_iso=country_iso, promo_code=promo_code, user_id=user_id)
    return jsonify(result), 200

@checkout_bp.route('/checkout/login', methods=['GET'])
def checkout_login():
    return render_template('checkout_login.html')

from flask import flash, redirect, url_for
from ..models import Address, Country
from flask_login import current_user

@checkout_bp.route('/checkout/shipping-address', methods=['GET', 'POST'])
@login_required
def shipping_address():
    if request.method == 'POST':
        # Check if the request is for deleting an address
        if 'delete_address' in request.form:
            address_id = request.form.get('address_id')
            address_to_delete = Address.query.get_or_404(address_id)
            if address_to_delete.user_id == current_user.id:
                db.session.delete(address_to_delete)
                db.session.commit()
                flash('Address deleted successfully!', 'success')
            else:
                flash('You are not authorized to delete this address.', 'danger')
            return redirect(url_for('checkout_bp.shipping_address'))

        # Handle adding a new address
        address = Address(
            user_id=current_user.id,
            address_type=request.form.get('address_type'),
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            address_line_1=request.form.get('address_line_1'),
            address_line_2=request.form.get('address_line_2'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            postal_code=request.form.get('postal_code'),
            country_iso_code=request.form.get('country'),
            phone_number=request.form.get('phone_number')
        )
        db.session.add(address)
        db.session.commit()
        flash('Address added successfully!', 'success')
        return redirect(url_for('checkout_bp.shipping_address'))

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    countries = Country.query.all()
    cart_info = session.get('cart', {})
    items = [{"sku": sku, "quantity": qty} for sku, qty in cart_info.items()]
    promo_code = session.get('promo_code')
    user_id = current_user.id if current_user.is_authenticated else None
    cart_summary = calculate_totals_internal(items, promo_code=promo_code, user_id=user_id)
    return render_template('shipping_address.html', addresses=addresses, cart_summary=cart_summary, countries=countries)

@checkout_bp.route('/checkout/edit-address/<int:address_id>', methods=['GET', 'POST'])
@login_required
def edit_address(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != current_user.id:
        flash('You are not authorized to edit this address.', 'danger')
        return redirect(url_for('checkout_bp.shipping_address'))

    if request.method == 'POST':
        address.address_type = request.form.get('address_type')
        address.first_name = request.form.get('first_name')
        address.last_name = request.form.get('last_name')
        address.address_line_1 = request.form.get('address_line_1')
        address.address_line_2 = request.form.get('address_line_2')
        address.city = request.form.get('city')
        address.state = request.form.get('state')
        address.postal_code = request.form.get('postal_code')
        address.country_iso_code = request.form.get('country')
        address.phone_number = request.form.get('phone_number')
        db.session.commit()
        flash('Address updated successfully!', 'success')
        return redirect(url_for('checkout_bp.shipping_address'))

    countries = Country.query.all()
    return render_template('edit_address.html', address=address, countries=countries)

@checkout_bp.route('/checkout/shipping-methods', methods=['GET'])
@login_required
def shipping_methods():
    cart_info = session.get('cart', {})
    items = [{"sku": sku, "quantity": qty} for sku, qty in cart_info.items()]

    # Get the user's shipping address
    shipping_address = Address.query.filter_by(user_id=current_user.id, address_type='shipping').first()
    country_iso = shipping_address.country_iso_code if shipping_address else None

    selected_shipping = session.get('shipping_method', 'standard')
    promo_code = session.get('promo_code')
    user_id = current_user.id if current_user.is_authenticated else None
    cart_summary = calculate_totals_internal(items, shipping_country_iso=country_iso, shipping_method=selected_shipping, promo_code=promo_code, user_id=user_id)
    return render_template('shipping_methods.html', cart_summary=cart_summary, selected_shipping=selected_shipping)

@checkout_bp.route('/checkout/shipping-methods-save', methods=['POST'])
@login_required
def shipping_methods_save():
    shipping_method = request.form.get('shipping_method')
    if shipping_method:
        session['shipping_method'] = shipping_method
        return redirect(url_for('checkout_bp.payment_methods'))
    flash('Please select a shipping method.', 'danger')
    return redirect(url_for('checkout_bp.shipping_methods'))

@checkout_bp.route('/checkout/payment-methods', methods=['GET', 'POST'])
@login_required
def payment_methods():
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        if payment_method:
            session['payment_method'] = payment_method
            return redirect(url_for('checkout_bp.summary'))
        flash('Please select a payment method.', 'danger')

    cart_info = session.get('cart', {})
    items = [{"sku": sku, "quantity": qty} for sku, qty in cart_info.items()]

    # Get the user's shipping address for calculation
    shipping_address = Address.query.filter_by(user_id=current_user.id, address_type='shipping').first()
    country_iso = shipping_address.country_iso_code if shipping_address else None

    # We also need the shipping cost from the previous step
    # For now, we'll just recalculate based on standard or get from session if stored
    # Ideally, we should have the selected shipping method in session
    selected_shipping = session.get('shipping_method', 'standard')
    promo_code = session.get('promo_code')
    user_id = current_user.id if current_user.is_authenticated else None

    cart_summary = calculate_totals_internal(items, shipping_country_iso=country_iso, shipping_method=selected_shipping, promo_code=promo_code, user_id=user_id)

    return render_template('payment_methods.html', cart_summary=cart_summary)

@checkout_bp.route('/checkout/summary', methods=['GET', 'POST'])
@login_required
def summary():
    cart_info = session.get('cart', {})
    if not cart_info:
        return redirect(url_for('shop_page'))

    items_list = [{"sku": sku, "quantity": qty} for sku, qty in cart_info.items()]

    shipping_address = Address.query.filter_by(user_id=current_user.id, address_type='shipping').first()
    country_iso = shipping_address.country_iso_code if shipping_address else None

    selected_shipping = session.get('shipping_method', 'standard')
    selected_payment = session.get('payment_method', 'card')
    promo_code = session.get('promo_code') # Assuming promo_code might be in session
    user_id = current_user.id if current_user.is_authenticated else None

    cart_summary = calculate_totals_internal(items_list, shipping_country_iso=country_iso, shipping_method=selected_shipping, promo_code=promo_code, user_id=user_id)

    if request.method == 'POST':
        comment = request.form.get('comment')

        # Resolve variants for order items
        skus = [it.get('sku') for it in items_list]
        variants = Variant.query.filter(Variant.sku.in_(skus)).all()
        variant_map = {v.sku: v for v in variants}

        try:
            with db.session.begin_nested():
                new_order = Order(
                    user_id=current_user.id,
                    status='PENDING',
                    subtotal_cents=cart_summary['subtotal_cents'],
                    discount_cents=cart_summary['discount_cents'],
                    vat_cents=cart_summary['vat_cents'],
                    shipping_cost_cents=cart_summary['shipping_cost_cents'],
                    total_cents=cart_summary['total_cents'],
                    shipping_method=selected_shipping,
                    payment_method=selected_payment,
                    comment=comment
                )
                db.session.add(new_order)
                db.session.flush()

                for it in items_list:
                    v = variant_map.get(it['sku'])
                    if not v: continue

                    product_snapshot = {
                        "name": v.product.name,
                        "product_sku": v.product.product_sku,
                        "category": v.product.category,
                        "weight_grams": v.product.weight_grams,
                        "dimensions_json": v.product.dimensions_json
                    }
                    unit_price = int((v.product.base_price_cents or 0) + (v.price_modifier_cents or 0))
                    order_item = OrderItem(
                        order_id=new_order.id,
                        variant_sku=it['sku'],
                        quantity=it['quantity'],
                        unit_price_cents=unit_price,
                        product_snapshot=product_snapshot
                    )
                    db.session.add(order_item)

                    # Update stock
                    if v.stock_quantity < it['quantity']:
                        raise ValueError(f"Insufficient stock for {v.sku}")
                    v.stock_quantity -= it['quantity']

            db.session.commit()
            session.pop('cart', None)
            session.pop('shipping_method', None)
            session.pop('payment_method', None)
            flash('Order placed successfully!', 'success')
            return redirect(url_for('checkout_bp.order_success', order_id=new_order.public_order_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    # Get actual objects for display
    display_items = []
    for sku, qty in cart_info.items():
        v = Variant.query.filter_by(sku=sku).first()
        if v:
            display_items.append({'variant': v, 'quantity': qty})

    return render_template('summary.html',
                           cart_summary=cart_summary,
                           shipping_address=shipping_address,
                           display_items=display_items,
                           selected_shipping=selected_shipping,
                           selected_payment=selected_payment)

@checkout_bp.route('/checkout/success/<order_id>')
@login_required
def order_success(order_id):
    order = Order.query.filter_by(public_order_id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_success.html', order=order, order_id=order_id)
