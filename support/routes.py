from flask import render_template
from flask_login import login_required
from support import support_bp

@support_bp.route("/")
@login_required
def chat():
    return render_template("support/chat.html")
