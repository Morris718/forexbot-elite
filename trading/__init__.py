from flask import Blueprint
trading_bp = Blueprint("trading", __name__, template_folder="../templates/trading")
from trading import routes
