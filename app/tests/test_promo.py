import pytest
from app.models import Promotion, User
from app.utils import calculate_totals_internal
from app.extensions import db
from datetime import datetime, timedelta, timezone

def test_global_promo_code(app, client):
    with app.app_context():
        promo = Promotion(
            code='GLOBAL10',
            discount_type='PERCENT',
            discount_value=10,
            is_active=True
        )
        db.session.add(promo)
        db.session.commit()

        items = [{'sku': 'SAMPLE-SKU-VAR', 'quantity': 1}]
        # Subtotal for SAMPLE-SKU is 12345 cents
        result = calculate_totals_internal(items, promo_code='GLOBAL10')
        assert result['discount_cents'] == 1235 # ceil(12345 * 0.1)
        assert result['subtotal_after_discount_cents'] == 12345 - 1235

def test_user_specific_promo_code(app, client):
    with app.app_context():
        user1 = User.query.filter_by(username='admin').first()
        user2 = User.query.filter_by(username='jimmy').first()

        promo = Promotion(
            code='USER1_ONLY',
            discount_type='FIXED',
            discount_value=1000,
            is_active=True,
            user_id=user1.id
        )
        db.session.add(promo)
        db.session.commit()

        items = [{'sku': 'SAMPLE-SKU-VAR', 'quantity': 1}]

        # Test with correct user
        result = calculate_totals_internal(items, promo_code='USER1_ONLY', user_id=user1.id)
        assert result['discount_cents'] == 1000

        # Test with wrong user
        result = calculate_totals_internal(items, promo_code='USER1_ONLY', user_id=user2.id)
        assert result['discount_cents'] == 0

        # Test with no user
        result = calculate_totals_internal(items, promo_code='USER1_ONLY', user_id=None)
        assert result['discount_cents'] == 0

def test_expired_promo_code(app, client):
    with app.app_context():
        promo = Promotion(
            code='EXPIRED',
            discount_type='PERCENT',
            discount_value=50,
            is_active=True,
            valid_to=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.session.add(promo)
        db.session.commit()

        items = [{'sku': 'SAMPLE-SKU-VAR', 'quantity': 1}]
        result = calculate_totals_internal(items, promo_code='EXPIRED')
        assert result['discount_cents'] == 0
