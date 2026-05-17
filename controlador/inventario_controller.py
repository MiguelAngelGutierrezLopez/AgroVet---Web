from flask import Blueprint, jsonify, request
from modelo.inventario_model import InventarioModel
import logging

logger = logging.getLogger(__name__)
inventario_bp = Blueprint('inventario', __name__, url_prefix='/api/inventario')


def responder_error(mensaje, codigo=500):
    return jsonify({'success': False, 'message': mensaje}), codigo


def responder_exito(datos=None, mensaje='Éxito', codigo=200):
    respuesta = {'success': True, 'message': mensaje}
    if datos is not None:
        respuesta.update(datos)
    return jsonify(respuesta), codigo


@inventario_bp.route('/', methods=['GET'])
def listar_inventario():
    """Obtener productos con información de inventario y filtros"""
    try:
        # Construir filtros desde parámetros GET
        filtros = {}
        
        if request.args.get('categoria'):
            filtros['categoria'] = request.args.get('categoria')
        
        if request.args.get('proveedor'):
            filtros['proveedor'] = request.args.get('proveedor')
        
        if request.args.get('estado_stock'):
            filtros['estado_stock'] = request.args.get('estado_stock')
        
        if request.args.get('busqueda'):
            filtros['busqueda'] = request.args.get('busqueda')
        
        resultado = InventarioModel.obtener_productos_inventario(filtros if filtros else None)
        
        if not resultado.get('success'):
            return responder_error(resultado.get('error', 'Error al obtener inventario'), 500)
        
        return responder_exito({
            'productos': resultado.get('productos', []),
            'total': resultado.get('total', 0)
        })
    
    except Exception as e:
        logger.error(f"Error en listar_inventario: {str(e)}")
        return responder_error('Error al obtener inventario')


@inventario_bp.route('/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas generales del inventario"""
    try:
        resultado = InventarioModel.obtener_estadisticas_inventario()
        
        if not resultado.get('success'):
            return responder_error(resultado.get('error', 'Error al obtener estadísticas'), 500)
        
        return responder_exito({'estadisticas': resultado.get('estadisticas', {})})
    
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas: {str(e)}")
        return responder_error('Error al obtener estadísticas')


@inventario_bp.route('/movimientos', methods=['GET'])
def obtener_movimientos():
    """Obtener movimientos recientes del inventario"""
    try:
        limite = int(request.args.get('limite', 10))
        
        resultado = InventarioModel.obtener_movimientos_recientes(limite)
        
        if not resultado.get('success'):
            return responder_error(resultado.get('error', 'Error al obtener movimientos'), 500)
        
        return responder_exito({
            'movimientos': resultado.get('movimientos', []),
            'total': resultado.get('total', 0)
        })
    
    except ValueError:
        return responder_error('Parámetro límite inválido', 400)
    except Exception as e:
        logger.error(f"Error en obtener_movimientos: {str(e)}")
        return responder_error('Error al obtener movimientos')


@inventario_bp.route('/mas-vendidos', methods=['GET'])
def obtener_mas_vendidos():
    """Obtener productos más vendidos"""
    try:
        dias = int(request.args.get('dias', 30))
        limite = int(request.args.get('limite', 5))
        
        resultado = InventarioModel.obtener_productos_mas_vendidos(dias, limite)
        
        if not resultado.get('success'):
            return responder_error(resultado.get('error', 'Error al obtener más vendidos'), 500)
        
        return responder_exito({
            'productos': resultado.get('productos', []),
            'periodo_dias': resultado.get('periodo_dias', dias)
        })
    
    except ValueError:
        return responder_error('Parámetros inválidos', 400)
    except Exception as e:
        logger.error(f"Error en obtener_mas_vendidos: {str(e)}")
        return responder_error('Error al obtener productos más vendidos')


@inventario_bp.route('/ventas-mensuales', methods=['GET'])
def obtener_ventas_mensuales():
    """Obtener ventas mensuales por producto"""
    try:
        mes = int(request.args.get('mes'))
        anio = int(request.args.get('anio'))
        
        if mes < 1 or mes > 12:
            return responder_error('Mes debe estar entre 1 y 12', 400)
        
        if anio < 2000 or anio > 2100:
            return responder_error('Año fuera de rango válido', 400)
        
        resultado = InventarioModel.obtener_ventas_mensuales(mes, anio)
        
        if not resultado.get('success'):
            return responder_error(resultado.get('error', 'Error al obtener ventas mensuales'), 500)
        
        return responder_exito({
            'ventas_mensuales': resultado.get('ventas_mensuales', []),
            'mes': resultado.get('mes'),
            'anio': resultado.get('anio'),
            'total_registros': resultado.get('total_registros', 0)
        })
    
    except ValueError:
        return responder_error('Parámetros mes y anio requeridos y deben ser números', 400)
    except Exception as e:
        logger.error(f"Error en obtener_ventas_mensuales: {str(e)}")
        return responder_error('Error al obtener ventas mensuales')


@inventario_bp.route('/filtros', methods=['GET'])
def obtener_filtros():
    """Obtener filtros disponibles"""
    try:
        resultado = InventarioModel.obtener_filtros_disponibles()
        
        if not resultado.get('success'):
            return responder_error(resultado.get('error', 'Error al obtener filtros'), 500)
        
        return responder_exito(resultado)
    
    except Exception as e:
        logger.error(f"Error en obtener_filtros: {str(e)}")
        return responder_error('Error al obtener filtros')


@inventario_bp.route('/<int:producto_id>', methods=['GET'])
def obtener_producto_detalle(producto_id):
    """Obtener detalle de un producto específico"""
    try:
        resultado = InventarioModel.obtener_detalle_producto(producto_id)
        
        if not resultado or not resultado.get('success'):
            return responder_error('Producto no encontrado', 404)
        
        return responder_exito({'producto': resultado.get('producto')})
    
    except Exception as e:
        logger.error(f"Error en obtener_producto_detalle: {str(e)}")
        return responder_error('Error al obtener detalle del producto')
