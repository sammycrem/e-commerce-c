import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set dummy env vars before any app code is imported to prevent initialization errors
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'
os.environ['ENCRYPTION_KEY'] = 'IaSmdjLwEg89FtIr6skf0jN2CJKMUnUuyIOa-8VGzhU='

from app.app import app as flask_app
from app.app import setup_database
from app.extensions import db
from app.models import Product, Variant, User

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        # Use a temporary in-memory SQLite DB for tests
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "testing-secret",
    })

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        # The setup_database function from app.py can be used to seed initial data
        setup_database(flask_app)

        # Seed one product with one variant for tests
        product = Product(
            product_sku='TEST-SHIRT',
            name='Test T-Shirt',
            description='A shirt for testing',
            category='Apparel',
            base_price_cents=2500,
            weight_grams=200, 
            dimensions_json={'length': 30, 'width': 25, 'height': 1}
        )
        db.session.add(product)
        db.session.flush()

        variant = Variant(
            product_id=product.id,
            sku='TEST-SHIRT-BLK-M',
            color_name='Black',
            size='M',
            stock_quantity=100,
            price_modifier_cents=0
        )
        db.session.add(variant)
        db.session.commit()

    yield flask_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def authenticated_client(app):
    """A test client that is authenticated."""
    with app.app_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                # Manually log in the user by setting the session
                # This is often more reliable than simulating a form post
                user = User.query.filter_by(email='admin@example.com').first()
                if user:
                    session['_user_id'] = user.id
                    session['_fresh'] = True
                else:
                    # If the admin user isn't found, you might want to fail the test
                    # or ensure your test DB seeding includes the admin user.
                    pytest.fail("Admin user not found in test database.")
            yield client
