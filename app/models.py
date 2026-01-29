from .extensions import db
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import JSON as SA_JSON, asc, desc
from datetime import datetime, timezone
import uuid
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    encrypted_password = db.Column(db.String(128), nullable=False)
    validation = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    orders = db.relationship('Order', back_populates='user')
    addresses = db.relationship('Address', back_populates='user', cascade='all, delete-orphan')

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_sku = db.Column(db.Text, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.Text)
    base_price_cents = db.Column(db.BigInteger, nullable=False)
    weight_grams = db.Column(db.Integer, nullable=True)
    dimensions_json = db.Column(SA_JSON, nullable=True)
    variants = db.relationship('Variant', back_populates='product', cascade='all, delete-orphan')
    images = db.relationship('ProductImage', back_populates='product', cascade='all, delete-orphan', order_by='ProductImage.display_order')

class Variant(db.Model):
    __tablename__ = 'variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    sku = db.Column(db.Text, nullable=False, unique=True)
    color_name = db.Column(db.Text)
    size = db.Column(db.Text)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    price_modifier_cents = db.Column(db.BigInteger, nullable=False, default=0)
    product = db.relationship('Product', back_populates='variants')
    images = db.relationship('VariantImage', back_populates='variant', cascade='all, delete-orphan', order_by='VariantImage.display_order')

class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    alt_text = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    product = db.relationship('Product', back_populates='images')

class VariantImage(db.Model):
    __tablename__ = 'variant_images'
    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id', ondelete='CASCADE'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    alt_text = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    variant = db.relationship('Variant', back_populates='images')

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    public_order_id = db.Column(db.Text, nullable=False, unique=True, default=lambda: f"ORD-{str(uuid.uuid4())[:8].upper()}")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(30), nullable=False, default='PENDING')
    subtotal_cents = db.Column(db.BigInteger, nullable=False, default=0)
    discount_cents = db.Column(db.BigInteger, nullable=False, default=0)
    shipping_cost_cents = db.Column(db.BigInteger, nullable=False, default=0)
    vat_cents = db.Column(db.BigInteger, nullable=False, default=0)
    total_cents = db.Column(db.BigInteger, nullable=False, default=0)
    shipping_method = db.Column(db.String(50), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    shipping_provider = db.Column(db.Text, nullable=True)
    tracking_number = db.Column(db.Text, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    variant_sku = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_snapshot = db.Column(db.JSON, nullable=False)
    unit_price_cents = db.Column(db.BigInteger, nullable=False)
    order = db.relationship('Order', back_populates='items')

class Promotion(db.Model):
    __tablename__ = 'promotions'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    discount_type = db.Column(db.String(10), nullable=False)
    discount_value = db.Column(db.BigInteger, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    valid_to = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='promotions')

class Country(db.Model):
    __tablename__ = 'countries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    iso_code = db.Column(db.String(2), nullable=False, unique=True)
    default_vat_rate = db.Column(db.Numeric(5,4), nullable=False, default=0.0)
    currency_code = db.Column(db.String(3), nullable=False, default='USD')
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class VatRate(db.Model):
    __tablename__ = 'vat_rates'
    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.Text)
    vat_rate = db.Column(db.Numeric(5,4), nullable=False)
    country = db.relationship('Country', backref='vat_rates')

class ShippingZone(db.Model):
    __tablename__ = 'shipping_zones'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    countries_json = db.Column(SA_JSON, nullable=False)
    base_cost_cents = db.Column(db.BigInteger, nullable=False, default=0)
    cost_per_kg_cents = db.Column(db.BigInteger, nullable=False, default=0)
    volumetric_divisor = db.Column(db.Integer, nullable=False, default=5000)
    free_shipping_threshold_cents = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Address(db.Model):
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    address_type = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    address_line_1 = db.Column(db.String(255), nullable=False)
    address_line_2 = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20), nullable=False)
    country_iso_code = db.Column(db.String(2), nullable=False)
    phone_number = db.Column(db.String(20))
    is_default = db.Column(db.Boolean, default=False)
    user = db.relationship('User', back_populates='addresses')
