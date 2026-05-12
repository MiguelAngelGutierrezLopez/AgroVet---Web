from flask import Blueprint, jsonify, request

inventario_bp = Blueprint('inventario', __name__)


def placeholder_response():
    return jsonify({
        'success': False,
        'message': 'Proximamente podras usar estos datos'
    }), 200


@inventario_bp.route('/api/inventario', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def inventario_root():
    return placeholder_response()


@inventario_bp.route('/api/inventario/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def inventario_placeholder(path):
    return placeholder_response()
