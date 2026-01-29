from flask import Flask, abort, render_template, request, redirect, url_for, session, flash, jsonify,  send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, joinedload
from sqlalchemy import JSON as SA_JSON , and_
from sqlalchemy import asc, desc
from datetime import datetime, timedelta, timezone
import string
import random
import os
from .utils import check_string_number_inclusion, concatenate_text_files, create_directory, download_file, download_image, encrypt_password, generate_id, generate_key, get_folders_in_directory, get_json_image_id, is_valid_image, rename_image, resize_image, send_email, init_config, send_emailTls2, str_to_bool, process_image_data, translate
import logging
import json
from werkzeug.utils import secure_filename
import uuid
from openai import OpenAI
import requests
from flask_cors import CORS
import uuid
from math import ceil
from decimal import Decimal, ROUND_HALF_UP





SITE1= "_s1"
EXPORT_DIR = "export"

GEN_JSON1 = 'gen1.json'
GEN_JSON2 = 'gen2.json'


UPLOAD_FOLDER = 'export'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}



# -------------------------
# Logging
# -------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)




from .extensions import db

# -------------------------
# Flask app & config
# -------------------------
app = Flask(__name__, static_folder='static', template_folder='templates')


# Allow cross-origin requests — enable credentials for same-origin cookie sessions.
# In production replace origins for security: CORS(app, resources={r"/api/*": {"origins": "https://yourdomain.com"}}, supports_credentials=True)
#CORS(app, supports_credentials=True)
CORS(app, origins=["http://localhost:8000"])

# -----------------------------------------------------------End load configuration
encryption_key = os.environ.get('ENCRYPTION_KEY')
config = init_config("./config.txt","./encrypt_config_file.txt")



# Use the decrypted configuration values

ADMIN_USER = config['APP_ADMIN_USER']
ADMIN_EMAIL = config['APP_ADMIN_EMAIL']
ADMIN_PASSWORD = config['APP_ADMIN_PASSWORD']
WWW = config['APP_WWW']
HOST_WWW = config['APP_HOST_WWW']
CONVERT_DIR = config['APP_CONVERT_DIR']
CONVERT_DST_DIR= config['APP_CONVERT_DST_DIR']
SMTP_PASSWORD=config['APP_SMTP_PASSWORD']
SMTP_SERVER=config['APP_SMTP_SERVER']
SMTP_PORT=int(config['APP_SMTP_PORT'])
SENDER_EMAIL=config['APP_SENDER_EMAIL']
SERVER_URL=config['APP_SERVER_URL']
CONVERT_DST_IMG_DIR=config['APP_CONVERT_DST_IMG_DIR']
IMG_DIR=config['APP_IMG_DIR']
defautl_convert_file=config['APP_defautl_convert_file']
TRANSLATE_JSON=config['APP_TRANSLATE_JSON']
template_site_source = 'private/template/1/mfb/'
logger.info(config)






app.config['SECRET_KEY'] = config['APP_SECRET_KEY']  
app.config['SQLALCHEMY_DATABASE_URI'] = config['APP_SQLALCHEMY_DATABASE_URI']  # Replace with your desired database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = config['APP_SESSION_TYPE']
app.config['SESSION_PERMANENT'] = str_to_bool(config['APP_SESSION_PERMANENT'])
app.config['PERMANENT_SESSION_LIFETIME'] = int(config['APP_PERMANENT_SESSION_LIFETIME'])

logger.info('starting' )




# initialize the app with the extension
db.init_app(app)

Session(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"


@app.context_processor
def inject_now():
    return {'now': datetime.now(timezone.utc)}

from .models import User, Product, Variant, ProductImage, VariantImage, Order, OrderItem, Promotion, Country, VatRate, ShippingZone

# -------------------------
# Login loader
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None




def create_user(user_name, user_ID, user_email, user_pssword):
    encrypted_Password = encrypt_password(user_pssword, encryption_key)
    xuser = User(username=user_name.lower(), user_id=user_ID, password=generate_password_hash(user_pssword), encrypted_password= encrypted_Password, email=user_email.lower()) 
    db.session.add(xuser)
    db.session.commit()
    create_directory(WWW + xuser.user_id)
    logger.info('create: ' + xuser.username)
    logger.info('password: ' + user_pssword)
    logger.info('encrypted_password: ' + xuser.encrypted_password)
    logger.info('email: ' + xuser.email)
    logger.info('id: ' + xuser.user_id)
    return xuser


# -------------------------
# Seeding helpers & config
# -------------------------
RECREATE_IF_EXISTS = False
BASE_IMAGE_URL = "http://localhost:5000/static/ec/products/img"
PRODUCT_COUNT = 4
COLORS = [
    {"name": "White", "code": "white", "prefix": "a", "price_modifier_pct": 0.0},
    {"name": "Red",   "code": "red",   "prefix": "b", "price_modifier_pct": 0.20},
    {"name": "Black", "code": "black", "prefix": "c", "price_modifier_pct": 0.10},
]
SIZES = ["S", "M", "L", "XL"]
DEFAULT_STOCK = 10
BASE_PRICES_USD = {
    "p-1": 12.00,
    "p-2": 18.50,
    "p-3": 22.00,
    "p-4": 15.75
}

def usd_to_cents(usd):
    d = Decimal(str(usd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)

def create_product_data(product_key):
    sku = product_key
    name = f"T-Shirt {product_key.upper()}"
    category = "Graphic Tees"
    description = f"Comfortable cotton tee — design {product_key.upper()}."
    base_price_usd = BASE_PRICES_USD.get(product_key, 19.99)
    base_price_cents = usd_to_cents(base_price_usd)
    product_image_url = f"{BASE_IMAGE_URL}/{product_key}/a-1.webp"

    variants = []
    for color in COLORS:
        color_prefix = color["prefix"]
        color_name = color["name"]
        modifier_pct = color["price_modifier_pct"]
        variant_images = [
            {"url": f"{BASE_IMAGE_URL}/{product_key}/{color_prefix}-1.webp", "alt_text": f"{color_name} image 1"},
            {"url": f"{BASE_IMAGE_URL}/{product_key}/{color_prefix}-2.webp", "alt_text": f"{color_name} image 2"},
            {"url": f"{BASE_IMAGE_URL}/{product_key}/{color_prefix}-3.webp", "alt_text": f"{color_name} image 3"},
        ]

        for size in SIZES:
            variant_sku = f"{product_key.upper()}-{color['code'][0].upper()}-{size}"
            price_modifier_cents = int(round(base_price_cents * modifier_pct))
            variants.append({
                "sku": variant_sku,
                "color_name": color_name,
                "size": size,
                "stock_quantity": DEFAULT_STOCK,
                "price_modifier_cents": price_modifier_cents,
                "images": variant_images
            })

    product_images = [
        {"url": f"{BASE_IMAGE_URL}/{product_key}/a-1.webp", "alt_text": f"{product_key} white 1", "display_order": 0},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/a-2.webp", "alt_text": f"{product_key} white 2", "display_order": 1},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/a-3.webp", "alt_text": f"{product_key} white 3", "display_order": 2},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/b-1.webp", "alt_text": f"{product_key} red 1", "display_order": 3},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/b-2.webp", "alt_text": f"{product_key} red 2", "display_order": 4},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/b-3.webp", "alt_text": f"{product_key} red 3", "display_order": 5},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/c-1.webp", "alt_text": f"{product_key} black 1", "display_order": 6},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/c-2.webp", "alt_text": f"{product_key} black 2", "display_order": 7},
        {"url": f"{BASE_IMAGE_URL}/{product_key}/c-3.webp", "alt_text": f"{product_key} black 3", "display_order": 8},
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
        session.delete(p)
        session.flush()

def insert_product(session, pdata):
    sku = pdata["product_sku"]
    product = Product(
        product_sku=sku,
        name=pdata["name"],
        description=pdata.get("description"),
        category=pdata.get("category"),
        base_price_cents=int(pdata["base_price_cents"])
    )
    session.add(product)
    session.flush()

    for idx, img in enumerate(pdata.get("images", [])):
        pi = ProductImage(
            product_id=product.id,
            url=img["url"],
            alt_text=img.get("alt_text", ""),
            display_order=int(img.get("display_order", idx))
        )
        session.add(pi)

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

# -------------------------
# Serialization helpers
# -------------------------
def serialize_image(image):
    return {"url": image.url, "alt_text": image.alt_text, "display_order": image.display_order}

def serialize_variant(variant):
    return {
        "sku": variant.sku,
        "color_name": variant.color_name,
        "size": variant.size,
        "stock_quantity": variant.stock_quantity,
        "final_price_cents": int((variant.product.base_price_cents or 0) + (variant.price_modifier_cents or 0)),
        "images": [serialize_image(img) for img in variant.images]
    }

def serialize_product(product):
    return {
        "product_sku": product.product_sku,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "base_price_cents": product.base_price_cents,
        "images": [serialize_image(img) for img in product.images],
        "variants": [serialize_variant(var) for var in product.variants]
    }








# -------------------------
# DB setup + seeding
# -------------------------
def setup_database(app):
    with app.app_context():
        try:
            # This query checks if the database is accessible.
            # If not, the except block will create the tables.
            User.query.first()
        except Exception:
            logger.info('db.create_all()')
            db.create_all()

        # --- Seeding Logic ---
        # Create default user if it doesn't exist
        if not User.query.filter_by(username=ADMIN_USER).first():
            create_user(ADMIN_USER, generate_id(6) + '_1', ADMIN_EMAIL, ADMIN_PASSWORD)
            users = ["jimmy", "rami", "christophe","olivier","majed","clara","aline","oscar","jean"]
            for xuser_name in users:
                if not User.query.filter_by(username=xuser_name).first():
                    create_user(xuser_name, generate_id(6) + '_1', xuser_name+"@nomail.local", '123')

        if not Promotion.query.first():
            promo = Promotion(
                code='SAVE20',
                description='Get 20% off your entire order!',
                discount_type='PERCENT',
                discount_value=20,
                is_active=True,
                valid_to = datetime.now(timezone.utc) + timedelta(days=30)
            )
            db.session.add(promo)
            db.session.commit()
            logger.info("Seeded promotion SAVE20")

        # seed sample countries and shipping zone
        if not Country.query.first():
            c_us = Country(name='United States', iso_code='US', default_vat_rate=0.07, currency_code='USD')
            c_de = Country(name='Germany', iso_code='DE', default_vat_rate=0.19, currency_code='EUR')
            c_fr = Country(name='France', iso_code='FR', default_vat_rate=0.2, currency_code='EUR')
            db.session.add_all([c_us, c_de,c_fr])
            db.session.commit()

        if not ShippingZone.query.first():
            zone_na = ShippingZone(name='North America', countries_json=['US','CA'], base_cost_cents=500, cost_per_kg_cents=1000, volumetric_divisor=5000, free_shipping_threshold_cents=10000)
            zone_eu = ShippingZone(name='Europe', countries_json=['DE','FR','IT'], base_cost_cents=700, cost_per_kg_cents=2500, volumetric_divisor=5000, free_shipping_threshold_cents=15000)
            db.session.add_all([zone_na, zone_eu])
            db.session.commit()

        if not Product.query.filter_by(product_sku='SAMPLE-SKU').first():
            product = Product(
                product_sku='SAMPLE-SKU',
                name='Sample Product',
                description='This is a sample product.',
                category='Samples',
                base_price_cents=12345
            )
            db.session.add(product)
            db.session.flush()

            variant = Variant(
                product_id=product.id,
                sku='SAMPLE-SKU-VAR',
                color_name='Red',
                size='M',
                stock_quantity=10,
                price_modifier_cents=0
            )
            db.session.add(variant)
            db.session.commit()

        # --- Seeding playground data ---
        logger.info("Seeding playground data...")
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
            logger.info(f"Seeding complete. Created products: {', '.join(created)}")
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error during seeding: {exc}")
            # we don't want to crash the whole app startup if seeding fails







@app.route('/')
def home():
    return render_template('index.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
         

        if request.method == 'POST':
            
            password = request.form['password']
            email = request.form['email'].lower() 

            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                
                login_user(user) 
                

                session['logged_in'] = True
                session['time']  = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
                logger.info('Login: ' + email + ";"  + request.remote_addr)
                session_id=current_user.user_id
                
                client_id = session_id + SITE1
               
                
              
                next_page = request.form.get('next') or request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('home'))
                
                
                
                
            
            else:
                flash('Invalid username or password')
                logger.info('Invalid username or password;' + request.remote_addr)
                return render_template('login.html', message_text="Invalid username or password")
        else:
            if current_user.is_authenticated:
                return redirect(url_for('home'))
    except Exception as e:
        return render_template('login.html', message_text=e)
    return render_template('login.html', message_text="Please Login or Signup")



@app.route('/logout')
@login_required
def logout(): 

    session.pop('logged_in', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].lower() 
        password = request.form['password']
        email = request.form['email'].lower() 
        user_id=generate_id(3) + '_1'

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username already exists')
            logger.info('Username already exists;' + request.remote_addr)
            return render_template('signup.html', message_text='Username: ' + email +  ' already exists')
        #return redirect(url_for('signup'))
        else:
            try:
                new_user = User(username=username, user_id=user_id , password=generate_password_hash(password), email=email)
                db.session.add(new_user)
                db.session.commit()
                logger.info('add new user;' + email + ";" + request.remote_addr)
                html_validation= '''<html>
                <head>
                <title>Test Email</title>
                </head>
                <body>
                <h2>Hello sdfx_user,</h2>
                <p>Please click the link to validate your inscription :</p>
                <a rel="nofollow noopener noreferrer" target="_blank" href="sdfx_link" style="border-bottom:1px solid #34353a;text-decoration:none;color:#34353a;">sdfx_link</a><br><br>
                <b>Thank you!</b>
                </body>
                </html>'''
                html_validation=html_validation.replace('sdfx_user',username)
                html_validation=html_validation.replace('sdfx_link', SERVER_URL + url_for('validate_user') + '?id=' + user_id + '&username=' + username)
                message = send_emailTls2(SENDER_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, email,'Subscription Validation', html_validation)
                logger.info('send_email;' + message )
                create_directory(HOST_WWW + user.user_id)
                session.pop('logged_in', None)
                logout_user()

                flash('User created successfully. Please login.')
                return redirect(url_for('login'))
            except Exception as e: 
                print(f"An error occurred: signup  {str(e)}")         
                return render_template('signup.html', message_text=str(e))

    return render_template('signup.html')

@app.route('/validate')
def validate_user():
    user_id = request.args.get('id')
    username = request.args.get('username')

    if user_id is None or username is None:
        return jsonify({'error': 'Missing required parameters'}), 400

    user = User.query.filter_by(username=username,user_id=user_id).first()
    
    if user:
        user.validation = 1
        logger.info('validate_user;' + username + ";" + request.remote_addr)
        db.session.commit()
        return jsonify({'message': 'User validated successfully!'})
    else:
        return jsonify({'error': 'Invalid user ID or username'}), 401

#Crud
@app.route("/list")                 #admin only
@login_required
def user_list():
    #current_user = session.get('user_id')
    if current_user.is_authenticated and current_user.username==ADMIN_USER:
        users = db.session.execute(db.select(User).order_by(User.username)).scalars()
        logger.info('user_list: ' + current_user.username + ";"  + request.remote_addr)
        return render_template("list.html", users=users, message_text=current_user)
    else:
        logger.info('user_list: ' + ';You do not have admin permission' + ";"  + request.remote_addr)
        return render_template("list.html", message_text="You do not have admin permission to view users list " )


@app.route("/user/<int:id>")
@login_required
def user_detail(id):
    if current_user.is_authenticated and current_user.username==ADMIN_USER or current_user.id==id:
        user = db.get_or_404(User, id)
        logger.info('detail.html;'+user.email)
        return render_template("detail.html", user=user)
    else:
        logger.info('detail.html;You do not have permission;id='+str(id)+ ";"  + request.remote_addr)
        return render_template("login.html", message_text="You do not have permission to view user detail")
        


@app.route("/user/<int:id>/delete", methods=["GET", "POSTe"])
@login_required
def user_delete(id):
    if current_user.is_authenticated and (current_user.username==ADMIN_USER or current_user.id==id):
        user = db.get_or_404(User, id)

        if request.method == "POST":
            db.session.delete(user)
            db.session.commit()
            logger.info('user_delete;OK;id='+str(id)+ ";"  + request.remote_addr)
            return redirect(url_for("user_list"))
        else :
            logger.info('user_delete;Ko;id='+str(id)+ ";"  + request.remote_addr)
            return render_template("delete.html", user=user)

    if current_user.is_authenticated:
        logger.info('user_delete;You are not allowed to delete;id='+str(id)+ ";"  + request.remote_addr)
        return render_template("login.html", message_text="You are not allowed to delete this user, id=" + str(id))
    else:
        logger.info('user_delete;Please login')
        return render_template("login.html", message_text="Please login")





#@app.route('/static/path/<path:subpath>')
@app.route('/protected/<path:subpath>')
def protected_static(subpath):
    
    if "static" in subpath or "resource" in subpath:
        
        return send_from_directory('protected/' ,subpath )
    else:
        if current_user.is_authenticated:  # Check if the user is authenticated
            #return send_from_directory('static/' + path  ,filename)
            response = send_from_directory('protected/' ,subpath )
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
            response.headers['Pragma'] = 'no-cache'
            return response
        else:
            abort(403)  # Forbidden

@app.route('/export/<path:subpath>')
@login_required
def export_static(subpath):
    
    
    if subpath.startswith(current_user.user_id):  # Check if the user is authenticated
        #return send_from_directory('static/' + path  ,filename)
        response = send_from_directory(EXPORT_DIR+'/' ,subpath )
        # response.headers['Cache-Control'] = 'no-store'
        # response.headers['Expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        # response.headers['Pragma'] = 'no-cache'
        return response
    else:
        abort(403)  # Forbidden

@app.route("/authorized_keys" , methods=['GET', 'POST'])                 #admin only
#@login_required
def get_authorized_keys():
    #current_user = session.get('user_id')
    if current_user.is_authenticated :
        return jsonify({'key': "_authorized_keys", '_url': request.remote_addr}), 200 
    else:
        return jsonify({'error': "_not_authorized", 'url': request.remote_addr}), 400


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS





#---------------------------------------------------------------------------------shop
# -------------------------
# HTML Page routes
# -------------------------
@app.route('/index')
def index():

    return render_template('index.html')

@app.route('/shop')
def shop_page():
    products = Product.query.all()
    return render_template('shop.html', products=products)

@app.route('/product/<string:sku>')
def product_page(sku):
    return render_template('product_detail.html', sku=sku)


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


# -------------------------
# Admin product CRUD API
# -------------------------

# List all products (admin)
@app.route('/api/admin/products', methods=['GET'])
def admin_list_products():
    # returns all products (no pagination by default) — could add pagination/filters later
    products = Product.query.options(joinedload(Product.images), joinedload(Product.variants)).order_by(Product.name).all()
    return jsonify([serialize_product(p) for p in products]), 200

# Get single product for editing (admin)
@app.route('/api/admin/products/<string:sku>', methods=['GET'])
def admin_get_product(sku):
    product = Product.query.options(joinedload(Product.images), joinedload(Product.variants).joinedload(Variant.images)).filter_by(product_sku=sku).first_or_404()
    return jsonify(serialize_product(product)), 200

# Update an existing product (admin)
@app.route('/api/admin/products/<string:sku>', methods=['PUT'])
def admin_update_product(sku):
    data = request.get_json() or {}
    product = Product.query.filter_by(product_sku=sku).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    try:
        # Basic fields
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        product.category = data.get('category', product.category)
        product.base_price_cents = int(data.get('base_price_cents', product.base_price_cents or 0))

        # Replace product images if images provided
        if 'images' in data:
            ProductImage.query.filter_by(product_id=product.id).delete(synchronize_session=False)
            for idx, img in enumerate(data.get('images', [])):
                url = img.get('url') if isinstance(img, dict) else str(img)
                alt = img.get('alt_text') if isinstance(img, dict) else ''
                order = int(img.get('order', idx)) if isinstance(img, dict) else idx
                pimg = ProductImage(product_id=product.id, url=url, alt_text=alt, display_order=order)
                db.session.add(pimg)

        # Replace variants (delete existing and recreate) — use subquery to delete variant images safely
        # --- inside admin_update_product (replace previous variants delete/recreate block) ---
        if 'variants' in data:
            incoming_variants = data.get('variants', [])

            # 1) Load existing variants for this product into a dict by sku
            existing_variants = {v.sku: v for v in Variant.query.filter_by(product_id=product.id).all()}

            # 2) Validate incoming SKUs do not conflict with other products
            incoming_skus = [str(vd.get('sku')).strip() for vd in incoming_variants if vd.get('sku')]
            if any(not s for s in incoming_skus):
                return jsonify({"error": "Each variant must include a non-empty 'sku'"}), 400

            # Query for any variants in DB that use any of these SKUs but belong to other products
            conflict = Variant.query.filter(Variant.sku.in_(incoming_skus), Variant.product_id != product.id).first()
            if conflict:
                return jsonify({"error": f"SKU conflict: variant SKU '{conflict.sku}' already exists on another product."}), 400

            # 3) Track SKUs seen so we can delete the ones that were removed
            seen_skus = set()

            for v_data in incoming_variants:
                sku_v = str(v_data.get('sku')).strip()
                seen_skus.add(sku_v)

                # Normalize fields
                color_name = v_data.get('color_name')
                size = v_data.get('size')
                stock_quantity = int(v_data.get('stock_quantity') or 0)
                price_modifier_cents = int(v_data.get('price_modifier_cents') or 0)

                if sku_v in existing_variants:
                    # Update existing variant
                    variant = existing_variants[sku_v]
                    variant.color_name = color_name
                    variant.size = size
                    variant.stock_quantity = stock_quantity
                    variant.price_modifier_cents = price_modifier_cents
                    db.session.add(variant)
                    db.session.flush()  # ensure variant.id

                    # Replace variant images: delete existing, add new
                    VariantImage.query.filter_by(variant_id=variant.id).delete(synchronize_session=False)
                    for idx, vimg in enumerate(v_data.get('images', []) or []):
                        vurl = vimg.get('url') if isinstance(vimg, dict) else str(vimg)
                        valt = vimg.get('alt_text') if isinstance(vimg, dict) else ''
                        vorder = int(vimg.get('order', idx)) if isinstance(vimg, dict) else idx
                        vi = VariantImage(variant_id=variant.id, url=vurl, alt_text=valt, display_order=vorder)
                        db.session.add(vi)

                else:
                    # Create new variant (no global conflict because we checked earlier)
                    variant = Variant(
                        product_id=product.id,
                        sku=sku_v,
                        color_name=color_name,
                        size=size,
                        stock_quantity=stock_quantity,
                        price_modifier_cents=price_modifier_cents
                    )
                    db.session.add(variant)
                    db.session.flush()  # need variant.id for images

                    for idx, vimg in enumerate(v_data.get('images', []) or []):
                        vurl = vimg.get('url') if isinstance(vimg, dict) else str(vimg)
                        valt = vimg.get('alt_text') if isinstance(vimg, dict) else ''
                        vorder = int(vimg.get('order', idx)) if isinstance(vimg, dict) else idx
                        vi = VariantImage(variant_id=variant.id, url=vurl, alt_text=valt, display_order=vorder)
                        db.session.add(vi)

            # 4) Delete variants that existed previously but were not present in incoming payload
            skus_to_delete = [sku for sku in existing_variants.keys() if sku not in seen_skus]
            if skus_to_delete:
                # Delete variant images first
                variant_ids_subq = db.session.query(Variant.id).filter(Variant.sku.in_(skus_to_delete), Variant.product_id == product.id).subquery()
                VariantImage.query.filter(VariantImage.variant_id.in_(variant_ids_subq)).delete(synchronize_session=False)
                Variant.query.filter(Variant.sku.in_(skus_to_delete), Variant.product_id == product.id).delete(synchronize_session=False)


        db.session.commit()

        # return updated product
        full_product = Product.query.options(
            joinedload(Product.images),
            joinedload(Product.variants).joinedload(Variant.images)
        ).filter_by(id=product.id).one()
        return jsonify(serialize_product(full_product)), 200

    except Exception as e:
        db.session.rollback()
        logger.exception("Admin update failed")
        return jsonify({"error": "Failed to update product", "details": str(e)}), 500


    except Exception as e:
        db.session.rollback()
        logger.exception("Admin update failed")
        return jsonify({"error": "Failed to update product", "details": str(e)}), 500

# Delete a product (admin)
@app.route('/api/admin/products/<string:sku>', methods=['DELETE'])
def admin_delete_product(sku):
    product = Product.query.filter_by(product_sku=sku).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": f"Product {sku} deleted"}), 200
    except Exception as e:
        db.session.rollback()
        logger.exception("Admin delete failed")
        return jsonify({"error": "Failed to delete product", "details": str(e)}), 500


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

# -------------------------
# API: Products
# -------------------------
@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json() or {}
    required = ['product_sku', 'name', 'variants', 'base_price_cents']
    for key in required:
        if key not in data:
            return jsonify({"error": f"Missing required field: {key}"}), 400

    if Product.query.filter_by(product_sku=data['product_sku']).first():
        return jsonify({"error": f"Product SKU {data['product_sku']} already exists"}), 409

    try:
        product = Product(
            product_sku=data['product_sku'],
            name=data['name'],
            description=data.get('description'),
            category=data.get('category'),
            base_price_cents=int(data['base_price_cents'])
        )
        db.session.add(product)
        db.session.flush()  # get product.id

        # Product images (array of {url, alt_text, order})
        images = data.get('images') or []
        # Backwards-compatible single image_url field (if admin form used image_url)
        if data.get('image_url') and not images:
            images = [{"url": data['image_url'], "alt_text": data.get('name') or data.get('product_sku'), "order": 0}]

        for idx, img in enumerate(images):
            try:
                url = img.get('url') if isinstance(img, dict) else str(img)
                alt = img.get('alt_text') if isinstance(img, dict) else ''
                order = int(img.get('order', idx)) if isinstance(img, dict) else idx
                pimg = ProductImage(product_id=product.id, url=url, alt_text=alt, display_order=order)
                db.session.add(pimg)
            except Exception:
                logger.warning("Skipping invalid product image payload: %s", img)

        # Variants and variant images
        for v_data in data.get('variants', []):
            sku = v_data.get('sku')
            if not sku:
                db.session.rollback()
                return jsonify({"error": "Each variant must include a 'sku' field"}), 400

            variant = Variant(
                product_id=product.id,
                sku=sku,
                color_name=v_data.get('color_name'),
                size=v_data.get('size'),
                stock_quantity=int(v_data.get('stock_quantity') or 0),
                price_modifier_cents=int(v_data.get('price_modifier_cents') or 0)
            )
            db.session.add(variant)
            db.session.flush()  # get variant.id for images

            v_images = v_data.get('images') or []
            for idx, vimg in enumerate(v_images):
                try:
                    vurl = vimg.get('url') if isinstance(vimg, dict) else str(vimg)
                    valt = vimg.get('alt_text') if isinstance(vimg, dict) else ''
                    vorder = int(vimg.get('order', idx)) if isinstance(vimg, dict) else idx
                    vi = VariantImage(variant_id=variant.id, url=vurl, alt_text=valt, display_order=vorder)
                    db.session.add(vi)
                except Exception:
                    logger.warning("Skipping invalid variant image payload: %s", vimg)

        db.session.commit()

        # Return full serialized product
        full_product = Product.query.options(
            joinedload(Product.variants).joinedload(Variant.images),
            joinedload(Product.images)
        ).filter_by(id=product.id).one()

        logger.info("Product created: %s", full_product.product_sku)
        return jsonify(serialize_product(full_product)), 201

    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create product")
        return jsonify({"error": "Failed to create product", "details": str(e)}), 500

@app.route('/api/products', methods=['GET'])
def list_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', type=str)

    query = Product.query.options(joinedload(Product.images), joinedload(Product.variants))
    if category:
        query = query.filter_by(category=category)

    paginated = query.order_by(Product.name).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "products": [serialize_product(p) for p in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages
    }), 200

@app.route('/api/products/<string:sku>', methods=['GET'])
def get_product(sku):
    product = Product.query.options(
        joinedload(Product.images),
        joinedload(Product.variants).joinedload(Variant.images)
    ).filter_by(product_sku=sku).first_or_404()
    return jsonify(serialize_product(product)), 200





# Update product by SKU (PUT) - replace images/variants with payload
@app.route('/api/products/<string:product_sku>', methods=['PUT'])
def update_product(product_sku):
    data = request.get_json() or {}
    # Basic validation — require minimal fields
    required = ['product_sku', 'name', 'base_price_cents', 'variants']
    for key in required:
        if key not in data:
            return jsonify({"error": f"Missing required field: {key}"}), 400

    product = Product.query.filter_by(product_sku=product_sku).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    try:
        # Start a nested transaction
        with db.session.begin_nested():
            # Update product top-level fields
            product.product_sku = data['product_sku']
            product.name = data['name']
            product.description = data.get('description')
            product.category = data.get('category')
            product.base_price_cents = int(data['base_price_cents'])

            db.session.add(product)
            db.session.flush()  # ensure product.id is present

            # --- Delete existing variant images, variants and product images ---
            # Fetch existing variant ids
            existing_variant_ids = [v.id for v in Variant.query.filter_by(product_id=product.id).all()]

            if existing_variant_ids:
                # Delete variant images (avoid join().delete() which errors)
                VariantImage.query.filter(VariantImage.variant_id.in_(existing_variant_ids)).delete(synchronize_session=False)
                # Delete variants
                Variant.query.filter(Variant.product_id == product.id).delete(synchronize_session=False)

            # Delete product images
            ProductImage.query.filter(ProductImage.product_id == product.id).delete(synchronize_session=False)

            db.session.flush()

            # --- Recreate product images ---
            images = data.get('images') or []
            if data.get('image_url') and not images:  # backward-compatible single-image
                images = [{"url": data['image_url'], "alt_text": data.get('name') or data.get('product_sku'), "order": 0}]

            for idx, img in enumerate(images):
                try:
                    url = img.get('url') if isinstance(img, dict) else str(img)
                    alt = img.get('alt_text') if isinstance(img, dict) else ''
                    order = int(img.get('display_order', img.get('order', idx)) if isinstance(img, dict) else idx)
                    pimg = ProductImage(product_id=product.id, url=url, alt_text=alt, display_order=order)
                    db.session.add(pimg)
                except Exception:
                    logger.warning("Skipping invalid product image payload: %s", img)

            db.session.flush()

            # --- Recreate variants and their images ---
            for v_data in data.get('variants', []):
                sku = v_data.get('sku')
                if not sku:
                    raise ValueError("Each variant must include a 'sku' field")

                variant = Variant(
                    product_id=product.id,
                    sku=sku,
                    color_name=v_data.get('color_name'),
                    size=v_data.get('size'),
                    stock_quantity=int(v_data.get('stock_quantity') or 0),
                    price_modifier_cents=int(v_data.get('price_modifier_cents') or 0)
                )
                db.session.add(variant)
                db.session.flush()  # to get variant.id

                v_images = v_data.get('images') or []
                for idx, vimg in enumerate(v_images):
                    try:
                        vurl = vimg.get('url') if isinstance(vimg, dict) else str(vimg)
                        valt = vimg.get('alt_text') if isinstance(vimg, dict) else ''
                        vorder = int(vimg.get('display_order', vimg.get('order', idx)) if isinstance(vimg, dict) else idx)
                        vi = VariantImage(variant_id=variant.id, url=vurl, alt_text=valt, display_order=vorder)
                        db.session.add(vi)
                    except Exception:
                        logger.warning("Skipping invalid variant image payload: %s", vimg)

        db.session.commit()

        # Return full serialized product
        full_product = Product.query.options(
            joinedload(Product.variants).joinedload(Variant.images),
            joinedload(Product.images)
        ).filter_by(id=product.id).one()

        logger.info("Product updated: %s", full_product.product_sku)
        return jsonify(serialize_product(full_product)), 200

    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Product update failed")
        return jsonify({"error": "Failed to update product", "details": str(e)}), 500


# Delete product by SKU
@app.route('/api/products/<string:product_sku>', methods=['DELETE'])
def delete_product_by_sku(product_sku):
    product = Product.query.filter_by(product_sku=product_sku).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    try:
        db.session.delete(product)
        db.session.commit()
        logger.info("Product deleted: %s", product_sku)
        return jsonify({"message": "Product deleted", "product_sku": product_sku}), 200
    except Exception as e:
        db.session.rollback()
        logger.exception("Product delete failed")
        return jsonify({"error": "Failed to delete product", "details": str(e)}), 500










# ----------------------------
# Admin: Order management APIs
# ----------------------------




ORDER_WORKFLOW = ['PENDING','PAID','READY_FOR_SHIPPING','SHIPPED','DELIVERED','CANCELLED','RETURNED']

@app.route('/api/admin/orders', methods=['GET'])
def admin_list_orders():
    """
    List orders (paginated).
    Query params:
      - status (optional) : filter by order.status
      - page (optional, default=1)
      - per_page (optional, default=20)
      - q (optional) : substring search against public_order_id
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', type=str)
    q = request.args.get('q', type=str)

    query = Order.query.order_by(desc(Order.created_at))
    if status:
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(Order.public_order_id.ilike(like))

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    def serialize_order_summary(o):
        return {
            "id": o.id,
            "public_order_id": o.public_order_id,
            "status": o.status,
            "total_cents": o.total_cents,
            "created_at": o.created_at.isoformat(),
            "shipping_provider": o.shipping_provider,
            "tracking_number": o.tracking_number,
            "shipped_at": o.shipped_at.isoformat() if o.shipped_at else None,
            "item_count": sum(i.quantity for i in o.items)
        }

    return jsonify({
        "orders": [serialize_order_summary(o) for o in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages
    }), 200


@app.route('/api/admin/orders/<string:public_order_id>/status', methods=['PUT'])
def admin_update_order_status(public_order_id):
    """
    Body: { "status": "SHIPPED" }
    """
    order = Order.query.filter_by(public_order_id=public_order_id).first_or_404()
    data = request.get_json() or {}
    new_status = (data.get('status') or '').strip().upper()
    if not new_status or new_status not in ORDER_WORKFLOW:
        return jsonify({"error": "Invalid status", "allowed": ORDER_WORKFLOW}), 400

    # optionally implement workflow guards here
    if new_status == 'SHIPPED' and not order.shipped_at:
        order.shipped_at = datetime.now(timezone.utc)

    order.status = new_status
    db.session.add(order)
    db.session.commit()
    return jsonify({"message": "Status updated", "public_order_id": order.public_order_id, "status": order.status}), 200


@app.route('/api/admin/orders/<string:public_order_id>/shipment', methods=['PUT'])
def admin_update_order_shipment(public_order_id):
    """
    Body: { "shipping_provider": "UPS", "tracking_number": "1Z...", "mark_as_shipped": true }
    """
    order = Order.query.filter_by(public_order_id=public_order_id).first_or_404()
    data = request.get_json() or {}
    provider = data.get('shipping_provider')
    tracking = data.get('tracking_number')
    mark_as_shipped = bool(data.get('mark_as_shipped', False))

    if provider is not None:
        order.shipping_provider = str(provider).strip()
    if tracking is not None:
        order.tracking_number = str(tracking).strip()
    if mark_as_shipped:
        order.status = 'SHIPPED'
        order.shipped_at = order.shipped_at or datetime.now(timezone.utc)

    db.session.add(order)
    db.session.commit()
    return jsonify({
        "message": "Shipment updated",
        "public_order_id": order.public_order_id,
        "shipping_provider": order.shipping_provider,
        "tracking_number": order.tracking_number,
        "status": order.status,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None
    }), 200



@app.route('/api/admin/orders/<string:public_order_id>', methods=['GET'])
def admin_get_order(public_order_id):
    order = Order.query.filter_by(public_order_id=public_order_id).options(joinedload(Order.items)).first_or_404()
    def serialize_item(it):
        return {
            "variant_sku": it.variant_sku,
            "quantity": it.quantity,
            "unit_price_cents": it.unit_price_cents,
            "product_snapshot": it.product_snapshot
        }
    return jsonify({
        "public_order_id": order.public_order_id,
        "status": order.status,
        "subtotal_cents": order.subtotal_cents,
        "discount_cents": order.discount_cents,
        "shipping_cost_cents": order.shipping_cost_cents,
        "vat_cents": order.vat_cents,
        "total_cents": order.total_cents,
        "shipping_provider": order.shipping_provider,
        "tracking_number": order.tracking_number,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "created_at": order.created_at.isoformat(),
        "items": [serialize_item(i) for i in order.items]
    }), 200


# render order detail by public_order_id (string, e.g. ORD-6074C416)
@app.route("/admin/orders/<string:public_order_id>")
def admin_order_detail_by_public(public_order_id):
    """
    Render HTML order detail for the public order id.
    Frontend/links that point to /admin/orders/ORD-... will resolve here.
    """
    order = Order.query.filter_by(public_order_id=public_order_id).first_or_404()
    # Pass public_order_id so the template (or client-side JS) can fetch the API /api/admin/orders/<public_order_id>
    return render_template("admin_order_detail.html", public_order_id=order.public_order_id)


@app.route("/admin/orders")
def admin_orders():
    return render_template("admin_orders.html")

# keep numeric route if needed
@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin_order_detail.html", public_order_id=order.public_order_id)

from .blueprints.cart import cart_bp
from .blueprints.checkout import checkout_bp
from .blueprints.countries import countries_bp

app.register_blueprint(cart_bp)
app.register_blueprint(checkout_bp)
app.register_blueprint(countries_bp)
# -------------------------
# Start
# -------------------------
with app.app_context():
    setup_database(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
