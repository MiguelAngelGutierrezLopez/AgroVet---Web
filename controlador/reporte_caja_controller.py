from flask import Blueprint, jsonify, request

reporte_caja_bp = Blueprint('reporte_caja', __name__)


def placeholder_response():
    return jsonify({
        'success': False,
        'message': 'Proximamente podras usar estos datos'
    }), 200


@reporte_caja_bp.route('/api/reporte-caja', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def reporte_caja_root():
    return placeholder_response()


@reporte_caja_bp.route('/api/reporte-caja/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def reporte_caja_placeholder(path):
    return placeholder_response()
