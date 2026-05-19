from flask import Blueprint
support_bp = Blueprint("support", __name__, template_folder="../templates/support")
from support import routes
