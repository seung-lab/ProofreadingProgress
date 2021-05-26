from flask import Blueprint
from flask import request
from flask_cors import cross_origin
from middle_auth_client import auth_required
from proofreadertraining.app import common
from proofreadertraining import __version__

bp = Blueprint('proofreadertraining_v1', __name__, url_prefix="/api/v1")

# -------------------------------
# ------ Access control and index
# -------------------------------


@bp.route('/', methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    return common.index()

@bp.route("/simple", methods=["GET"])
def simple():
    return common.simple()

@bp.route("/query", methods=["GET"])
def query():
    return common.query()

@bp.route("/user", methods=["GET"])
def user():
    return common.user()

@bp.route('/<name>.js', methods=['GET'])
def scripts(name):
    return common.getScripts(name+".js")

@bp.route('/<name>.css', methods=['GET'])
def style(name):
    return common.getStyles(name+".css")

@bp.route
def home():
    return common.home()

# -------------------------------
# ------ Measurements and Logging
# -------------------------------

@bp.before_request
#@auth_required
def before_request():
    return common.before_request()


@bp.after_request
#@auth_required
def after_request(response):
    return common.after_request(response)


@bp.errorhandler(Exception)
def internal_server_error(e):
    return common.internal_server_error(e)


@bp.errorhandler(Exception)
def unhandled_exception(e):
    return common.unhandled_exception(e)

# -------------------
# ------ Applications
# -------------------

@bp.route('/json/', methods=['GET'])
#@auth_required
def get_json_link():
    return common.get_json_link(request.args)

@bp.route('/full/', methods=['GET'])
def get_state_link():
    return common.get_state_link(request.args)

@bp.route('/cord/', methods=['GET'])
def get_root_ids():
    return common.get_rootids(request.args)

@bp.route('/version', methods=['GET'])
def get_version():
    return __version__

@bp.route('/qry/', methods=['GET'])
def pass_through():
    return common.apiRequest(request.args)