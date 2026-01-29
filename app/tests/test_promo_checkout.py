import pytest
from flask import session
from app.models import Promotion, Country, ShippingZone, Product, Variant, Address
from app.extensions import db

def test_set_promo_code(client, app):
    # Add a promotion
    with app.app_context():
        promo = Promotion(code='TESTPROMO', discount_type='PERCENT', discount_value=10, is_active=True)
        db.session.add(promo)
        db.session.commit()

    # Test setting promo code
    resp = client.post('/api/set-promo-code', json={'promo_code': 'TESTPROMO'})
    assert resp.status_code == 200
    assert resp.get_json()['code'] == 'TESTPROMO'

    with client.session_transaction() as sess:
        assert sess['promo_code'] == 'TESTPROMO'

    # Test removing promo code
    resp = client.post('/api/set-promo-code', json={'promo_code': ''})
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert 'promo_code' not in sess

def test_promo_applied_in_checkout_flow(client, app):
    with app.app_context():
        # Setup data
        promo = Promotion(code='SAVE50', discount_type='PERCENT', discount_value=50, is_active=True)
        db.session.add(promo)

        country = Country(name='TestLand', iso_code='TL', default_vat_rate=0.20)
        db.session.add(country)

        zone = ShippingZone(name='TestZone', countries_json=['TL'], base_cost_cents=1000)
        db.session.add(zone)

        product = Product(product_sku='P1', name='Product 1', base_price_cents=10000)
        db.session.add(product)
        db.session.flush()

        variant = Variant(product_id=product.id, sku='V1', stock_quantity=100)
        db.session.add(variant)
        db.session.commit()

    # Add to cart
    client.post('/api/cart', json={'sku': 'V1', 'quantity': 1})

    # Set promo code
    client.post('/api/set-promo-code', json={'promo_code': 'SAVE50'})

    # Calculate totals via API
    resp = client.post('/api/calculate-totals', json={
        'items': [{'sku': 'V1', 'quantity': 1}],
        'shipping_country_iso': 'TL',
        'shipping_method': 'standard'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['subtotal_cents'] == 10000
    assert data['discount_cents'] == 5000
    assert data['subtotal_after_discount_cents'] == 5000

    # Check VAT: (5000 * 0.20) + (1000 * 0.20) = 1000 + 200 = 1200
    assert data['vat_cents'] == 1200
    assert data['shipping_cost_cents'] == 1000
    assert data['total_cents'] == 5000 + 1200 + 1000 # 7200
