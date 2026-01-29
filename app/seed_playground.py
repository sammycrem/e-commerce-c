# seed_playground.py
"""
Seed script to create 4 products (p-1..p-4) with variants/colors/sizes and images.

Usage:
    export ENCRYPTION_KEY="your-key"
    python seed_playground.py

Place this file in the root directory.
"""

from decimal import Decimal, ROUND_HALF_UP
from math import ceil
import sys
import os
from datetime import datetime


# Adjust path to allow importing from app package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


from app import app
from extensions import db
from models import Product, Variant, ProductImage, VariantImage





# CONFIG
RECREATE_IF_EXISTS = True  # If True, existing products with same SKU will be deleted and recreated

BASE_URL = "http://localhost:5000/static/ec/products/img"

PRODUCT_COUNT = 4
PRODUCT_PREFIX = "p-"  # product SKUs: p-1, p-2, ...
COLORS = [
    {"name": "White", "code": "white", "prefix": "a", "price_modifier_pct": 0.0},
    {"name": "Red",   "code": "red",   "prefix": "b", "price_modifier_pct": 0.20},
    {"name": "Black", "code": "black", "prefix": "c", "price_modifier_pct": 0.10},
]
SIZES = ["S", "M", "L", "XL"]
DEFAULT_STOCK = 10
# Base prices (in dollars) for each product (choose arbitrary demo prices)
BASE_PRICES_USD = {
    "p-1": 12.00,
    "p-2": 18.50,
    "p-3": 22.00,
    "p-4": 15.75
}


# Helpers
def usd_to_cents(usd):
    d = Decimal(str(usd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def cents_to_usd_str(cents):
    return f"${(Decimal(cents) / 100):.2f}"


def create_product_data(product_key):
    """
    Build product dictionary for product_key like 'p-1'
    """
    sku = product_key
    name = f"T-Shirt {product_key.upper()}"
    category = "Graphic Tees"
    description = f"Comfortable cotton tee — design {product_key.upper()}."
    base_price_usd = BASE_PRICES_USD.get(product_key, 19.99)
    base_price_cents = usd_to_cents(base_price_usd)
    # product-level image base (first white image as main)
    product_image_url = f"{BASE_URL}/{product_key}/a-1.webp"
    # Build variant data
    variants = []
    for color in COLORS:
        color_prefix = color["prefix"]
        color_name = color["name"]
        modifier_pct = color["price_modifier_pct"]
        # three images per color (suffix 1..3)
        variant_images = [
            {"url": f"{BASE_URL}/{product_key}/{color_prefix}-1.webp", "alt_text": f"{color_name} image 1"},
            {"url": f"{BASE_URL}/{product_key}/{color_prefix}-2.webp", "alt_text": f"{color_name} image 2"},
            {"url": f"{BASE_URL}/{product_key}/{color_prefix}-3.webp", "alt_text": f"{color_name} image 3"},
        ]

        for size in SIZES:
            # create a unique SKU per variant — combine product key, color code and size
            variant_sku = f"{product_key.upper()}-{color['code'][0].upper()}-{size}"
            # price_modifier_cents is the extra cents added to base price
            price_modifier_cents = int(round(base_price_cents * modifier_pct))
            variants.append({
                "sku": variant_sku,
                "color_name": color_name,
                "size": size,
                "stock_quantity": DEFAULT_STOCK,
                "price_modifier_cents": price_modifier_cents,
                "images": variant_images
            })

    # product-level images: we'll include all first-of-color images as product images (optional)
    product_images = [
        {"url": f"{BASE_URL}/{product_key}/a-1.webp", "alt_text": f"{product_key} white 1", "display_order": 0},
        {"url": f"{BASE_URL}/{product_key}/a-2.webp", "alt_text": f"{product_key} white 2", "display_order": 1},
        {"url": f"{BASE_URL}/{product_key}/a-3.webp", "alt_text": f"{product_key} white 3", "display_order": 2},
        {"url": f"{BASE_URL}/{product_key}/b-1.webp", "alt_text": f"{product_key} red 1", "display_order": 3},
        {"url": f"{BASE_URL}/{product_key}/b-2.webp", "alt_text": f"{product_key} red 2", "display_order": 4},
        {"url": f"{BASE_URL}/{product_key}/b-3.webp", "alt_text": f"{product_key} red 3", "display_order": 5},
        {"url": f"{BASE_URL}/{product_key}/c-1.webp", "alt_text": f"{product_key} black 1", "display_order": 6},
        {"url": f"{BASE_URL}/{product_key}/c-2.webp", "alt_text": f"{product_key} black 2", "display_order": 7},
        {"url": f"{BASE_URL}/{product_key}/c-3.webp", "alt_text": f"{product_key} black 3", "display_order": 8},
    ]

    return {
        "product_sku": sku,
        "name": name,
        "category": category,
        "description": description,
        "base_price_cents": base_price_cents,
        "image_url": product_image_url,
        "images": product_images,
        "variants": variants
    }


def safe_delete_product_by_sku(session, sku):
    p = Product.query.filter_by(product_sku=sku).first()
    if p:
        print(f" - Deleting existing product {sku}")
        # Delete related images and variants explicitly if needed,
        # though SQLAlchemy cascade should handle it if configured.
        session.delete(p)
        session.flush()


def insert_product(session, pdata):
    sku = pdata["product_sku"]
    print(f"Creating product {sku} - {pdata['name']} - price {cents_to_usd_str(pdata['base_price_cents'])}")
    product = Product(
        product_sku=sku,
        name=pdata["name"],
        description=pdata.get("description"),
        category=pdata.get("category"),
        base_price_cents=int(pdata["base_price_cents"])
    )
    session.add(product)
    session.flush()  # get product.id

    # product images
    for idx, img in enumerate(pdata.get("images", [])):
        pi = ProductImage(
            product_id=product.id,
            url=img["url"],
            alt_text=img.get("alt_text", ""),
            display_order=int(img.get("display_order", idx))
        )
        session.add(pi)

    # variants + variant images
    for v in pdata.get("variants", []):
        variant = Variant(
            product_id=product.id,
            sku=v["sku"],
            color_name=v.get("color_name"),
            size=v.get("size"),
            stock_quantity=int(v.get("stock_quantity") or 0),
            price_modifier_cents=int(v.get("price_modifier_cents") or 0)
        )
        session.add(variant)
        session.flush()
        for idx, vi in enumerate(v.get("images", []) or []):
            vimg = VariantImage(
                variant_id=variant.id,
                url=vi.get("url"),
                alt_text=vi.get("alt_text", ""),
                display_order=idx
            )
            session.add(vimg)

    return product


def main():
    with app.app_context():
        print("Seeding playground data...")
        created = []
        try:
            for i in range(1, PRODUCT_COUNT + 1):
                key = f"p-{i}"
                pdata = create_product_data(key)
                if RECREATE_IF_EXISTS:
                    safe_delete_product_by_sku(db.session, pdata["product_sku"])

                prod = insert_product(db.session, pdata)
                created.append(prod.product_sku)

            db.session.commit()
            print("Seeding complete. Created products:", ", ".join(created))
            print("Seeding playground data...")
            created = []
            try:
                for i in range(1, PRODUCT_COUNT + 1):
                    key = f"p-{i}"
                    pdata = create_product_data(key)
                    if RECREATE_IF_EXISTS:
                        safe_delete_product_by_sku(db.session, pdata["product_sku"])

                    prod = insert_product(db.session, pdata)
                    created.append(prod.product_sku)

                db.session.commit()
                print("Seeding complete. Created products:", ", ".join(created))
            except Exception as exc:
                db.session.rollback()
                print("Error during seeding:", exc)
                raise
                
        except Exception as exc:
            db.session.rollback()
            print("Error during seeding:", exc)
            raise


if __name__ == "__main__":
    main()
