from flask import Blueprint, jsonify, request

historial_venta_bp = Blueprint('historial_venta', __name__)


def placeholder_response():
    return jsonify({
        'success': False,
        'message': 'Proximamente podras usar estos datos'
    }), 200


@historial_venta_bp.route('/api/historial-ventas', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def historial_ventas_root():
    return placeholder_response()


@historial_venta_bp.route('/api/historial-ventas/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def historial_ventas_placeholder(path):
    return placeholder_response()
