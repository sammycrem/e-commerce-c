from flask import Blueprint, jsonify
from ..models import Country

countries_bp = Blueprint('countries_bp', __name__)

@countries_bp.route('/api/countries', methods=['GET'])
def list_countries():
    countries = Country.query.order_by(Country.name).all()
    result = [{"iso_code": c.iso_code, "name": c.name, "default_vat_rate": str(c.default_vat_rate), "currency": c.currency_code} for c in countries]
    return jsonify(result), 200
