"""
Controlador placeholder para Clientes y Proveedores.
"""
from flask import Blueprint, jsonify, request

cliente_proveedor_bp = Blueprint('cliente_proveedor', __name__)


def placeholder_response():
    return jsonify({
        'success': False,
        'message': 'Proximamente podras usar estos datos'
    }), 200


@cliente_proveedor_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def cliente_proveedor_placeholder(path):
    allowed_prefixes = [
        'debug/tablas',
        'venta',
        'clientes',
        'estadisticas',
        'cliente',
        'proveedores',
        'proveedor',
    ]

    if any(path == prefix or path.startswith(prefix + '/') for prefix in allowed_prefixes):
        return placeholder_response()

    return jsonify({
        'success': False,
        'message': 'Ruta no encontrada'
    }), 404
