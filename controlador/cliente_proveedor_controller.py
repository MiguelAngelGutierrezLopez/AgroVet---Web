"""
Controlador para Clientes y Proveedores.
"""
from flask import Blueprint, request, jsonify
from modelo.cliente_proveedor_modelo import ClienteProveedorModel
import logging

logger = logging.getLogger(__name__)
cliente_proveedor_bp = Blueprint('cliente_proveedor', __name__)


def responder_error(mensaje, codigo=500):
    return jsonify({'success': False, 'message': mensaje}), codigo


def responder_exito(datos=None, mensaje='Éxito', codigo=200):
    respuesta = {'success': True, 'message': mensaje}
    if datos is not None:
        respuesta.update(datos)
    return jsonify(respuesta), codigo


@cliente_proveedor_bp.route('/clientes', methods=['GET'])
def listar_clientes():
    try:
        busqueda = request.args.get('busqueda', '')
        estado = request.args.get('estado')
        deuda = request.args.get('deuda')
        per_page = request.args.get('per_page')
        page = request.args.get('page')
        limit = int(request.args.get('limit', per_page or 10))
        if page is not None:
            page = int(page)
            offset = (max(page, 1) - 1) * limit
        else:
            offset = int(request.args.get('offset', 0))

        resultado = ClienteProveedorModel.obtener_clientes(
            busqueda=busqueda,
            estado=estado,
            deuda=deuda,
            limit=limit,
            offset=offset
        )

        return responder_exito({
            'clientes': resultado.get('clientes', []),
            'total': resultado.get('total', 0)
        })

    except ValueError:
        return responder_error('Parámetros limit u offset inválidos', 400)
    except Exception as e:
        logger.error(f"Error en listar_clientes: {str(e)}")
        return responder_error('Error al obtener clientes')


@cliente_proveedor_bp.route('/cliente/<cedula>', methods=['GET'])
def obtener_cliente(cedula):
    try:
        cliente = ClienteProveedorModel.obtener_cliente_por_cedula(cedula)
        if not cliente:
            return responder_error('Cliente no encontrado', 404)
        return responder_exito({'cliente': cliente})
    except Exception as e:
        logger.error(f"Error en obtener_cliente: {str(e)}")
        return responder_error('Error al obtener cliente')


@cliente_proveedor_bp.route('/cliente', methods=['POST'])
def crear_cliente():
    try:
        datos = request.get_json() or {}
        cedula = datos.get('cedula')
        nombre = datos.get('nombre')
        telefono = datos.get('telefono')
        correo = datos.get('correo')
        direccion = datos.get('direccion')

        if not cedula or not nombre:
            return responder_error('La cédula y el nombre son obligatorios', 400)

        exito, mensaje = ClienteProveedorModel.crear_cliente(
            cedula, nombre, telefono, correo, direccion
        )

        if not exito:
            return responder_error(mensaje, 400)

        return responder_exito(None, mensaje, 201)

    except Exception as e:
        logger.error(f"Error en crear_cliente: {str(e)}")
        return responder_error('Error al crear el cliente')


@cliente_proveedor_bp.route('/cliente/<cedula_original>', methods=['PUT'])
def actualizar_cliente(cedula_original):
    try:
        datos = request.get_json() or {}
        cedula = datos.get('cedula', cedula_original)
        nombre = datos.get('nombre')
        telefono = datos.get('telefono')
        correo = datos.get('correo')
        direccion = datos.get('direccion')
        fecha_creacion = datos.get('fecha_creacion')

        if not nombre:
            return responder_error('El nombre es obligatorio', 400)

        exito, mensaje = ClienteProveedorModel.actualizar_cliente(
            cedula_original,
            cedula,
            nombre,
            telefono,
            correo,
            direccion,
            fecha_creacion
        )

        if not exito:
            return responder_error(mensaje, 400)

        return responder_exito(None, mensaje)

    except Exception as e:
        logger.error(f"Error en actualizar_cliente: {str(e)}")
        return responder_error('Error al actualizar el cliente')


@cliente_proveedor_bp.route('/cliente/<cedula>', methods=['DELETE'])
def eliminar_cliente(cedula):
    try:
        exito, mensaje = ClienteProveedorModel.eliminar_cliente(cedula)
        if not exito:
            return responder_error(mensaje, 400)
        return responder_exito(None, mensaje)
    except Exception as e:
        logger.error(f"Error en eliminar_cliente: {str(e)}")
        return responder_error('Error al eliminar el cliente')


@cliente_proveedor_bp.route('/cliente/<cedula>/historial', methods=['GET'])
def historial_cliente(cedula):
    try:
        historial = ClienteProveedorModel.obtener_historial_cliente(cedula)
        if historial is None:
            return responder_error('Cliente no encontrado', 404)
        return responder_exito({'historial': historial})
    except Exception as e:
        logger.error(f"Error en historial_cliente: {str(e)}")
        return responder_error('Error al obtener el historial del cliente')


@cliente_proveedor_bp.route('/proveedores', methods=['GET'])
def listar_proveedores():
    try:
        busqueda = request.args.get('busqueda', '')
        estado = request.args.get('estado')
        per_page = request.args.get('per_page')
        page = request.args.get('page')
        limit = int(request.args.get('limit', per_page or 10))
        if page is not None:
            page = int(page)
            offset = (max(page, 1) - 1) * limit
        else:
            offset = int(request.args.get('offset', 0))

        resultado = ClienteProveedorModel.obtener_proveedores(
            busqueda=busqueda,
            estado=estado,
            limit=limit,
            offset=offset
        )

        return responder_exito({
            'proveedores': resultado.get('proveedores', []),
            'total': resultado.get('total', 0)
        })

    except ValueError:
        return responder_error('Parámetros limit u offset inválidos', 400)
    except Exception as e:
        logger.error(f"Error en listar_proveedores: {str(e)}")
        return responder_error('Error al obtener proveedores')


@cliente_proveedor_bp.route('/proveedor/<telefono>', methods=['GET'])
def obtener_proveedor(telefono):
    try:
        proveedor = ClienteProveedorModel.obtener_proveedor_por_telefono(telefono)
        if not proveedor:
            return responder_error('Proveedor no encontrado', 404)
        return responder_exito({'proveedor': proveedor})
    except Exception as e:
        logger.error(f"Error en obtener_proveedor: {str(e)}")
        return responder_error('Error al obtener proveedor')


@cliente_proveedor_bp.route('/proveedor', methods=['POST'])
def crear_proveedor():
    try:
        datos = request.get_json() or {}
        telefono = datos.get('telefono')
        nombre_empresa = datos.get('nombre_empresa')
        nombre_proveedor = datos.get('nombre_proveedor')
        correo = datos.get('correo')
        estado = datos.get('estado', 'activo')
        productos = datos.get('productos') or datos.get('producto')

        if not telefono or not nombre_empresa or not nombre_proveedor:
            return responder_error('Teléfono, nombre de empresa y nombre del proveedor son obligatorios', 400)

        if productos:
            exito, mensaje = ClienteProveedorModel.crear_proveedor_con_productos(
                telefono, nombre_empresa, nombre_proveedor, correo, estado, productos
            )
        else:
            exito, mensaje = ClienteProveedorModel.crear_proveedor(
                telefono, nombre_empresa, nombre_proveedor, correo, estado
            )

        if not exito:
            return responder_error(mensaje, 400)

        return responder_exito(None, mensaje, 201)

    except Exception as e:
        logger.error(f"Error en crear_proveedor: {str(e)}")
        return responder_error('Error al crear el proveedor')

@cliente_proveedor_bp.route('/proveedor/completo', methods=['POST'])
def crear_proveedor_completo():
    try:
        datos = request.get_json() or {}
        telefono = datos.get('telefono')
        nombre_empresa = datos.get('nombre_empresa')
        nombre_proveedor = datos.get('nombre_proveedor')
        correo = datos.get('correo')
        estado = datos.get('estado', 'activo')
        productos = datos.get('productos') or datos.get('producto')

        if not telefono or not nombre_empresa or not nombre_proveedor:
            return responder_error('Teléfono, nombre de empresa y nombre del proveedor son obligatorios', 400)

        exito, mensaje = ClienteProveedorModel.crear_proveedor_con_productos(
            telefono, nombre_empresa, nombre_proveedor, correo, estado, productos
        )

        if not exito:
            return responder_error(mensaje, 400)

        return responder_exito(None, 201)

    except Exception as e:
        logger.error(f"Error en crear_proveedor_completo: {str(e)}")
        return responder_error('Error al crear el proveedor completo')

@cliente_proveedor_bp.route('/proveedor/<telefono>', methods=['PUT'])
def actualizar_proveedor(telefono):
    try:
        datos = request.get_json() or {}
        nuevo_telefono = datos.get('telefono', telefono)
        nombre_empresa = datos.get('nombre_empresa')
        nombre_proveedor = datos.get('nombre_proveedor')
        correo = datos.get('correo')
        estado = datos.get('estado')
        producto = datos.get('producto')

        if not nombre_empresa or not nombre_proveedor or estado is None:
            return responder_error('Nombre de empresa, nombre de proveedor y estado son obligatorios', 400)

        exito, mensaje = ClienteProveedorModel.actualizar_proveedor(
            telefono,
            nuevo_telefono,
            nombre_empresa,
            nombre_proveedor,
            correo,
            estado,
            producto
        )

        if not exito:
            return responder_error(mensaje, 400)

        return responder_exito(None, mensaje)

    except Exception as e:
        logger.error(f"Error en actualizar_proveedor: {str(e)}")
        return responder_error('Error al actualizar el proveedor')


@cliente_proveedor_bp.route('/proveedor/<telefono>', methods=['DELETE'])
def eliminar_proveedor(telefono):
    try:
        exito, mensaje = ClienteProveedorModel.eliminar_proveedor(telefono)
        if not exito:
            return responder_error(mensaje, 400)
        return responder_exito(None, mensaje)
    except Exception as e:
        logger.error(f"Error en eliminar_proveedor: {str(e)}")
        return responder_error('Error al eliminar el proveedor')


@cliente_proveedor_bp.route('/proveedor/<telefono>/historial', methods=['GET'])
def historial_proveedor(telefono):
    try:
        historial = ClienteProveedorModel.obtener_historial_proveedor(telefono)
        if historial is None:
            return responder_error('Proveedor no encontrado', 404)
        return responder_exito({'historial': historial})
    except Exception as e:
        logger.error(f"Error en historial_proveedor: {str(e)}")
        return responder_error('Error al obtener el historial del proveedor')


@cliente_proveedor_bp.route('/productos/disponibles', methods=['GET'])
def productos_para_asignar():
    try:
        productos = ClienteProveedorModel.obtener_productos_para_asignar()
        return responder_exito({'productos': productos})
    except Exception as e:
        logger.error(f"Error en productos_para_asignar: {str(e)}")
        return responder_error('Error al obtener productos disponibles')


@cliente_proveedor_bp.route('/proveedor/<telefono>/asignar-productos', methods=['POST'])
def asignar_productos(telefono):
    try:
        datos = request.get_json() or {}
        ids_productos = datos.get('ids_productos') or datos.get('productos_ids') or datos.get('productos')

        if not ids_productos or not isinstance(ids_productos, list):
            return responder_error('Debes enviar una lista de IDs de productos', 400)

        exito, mensaje = ClienteProveedorModel.asignar_productos_a_proveedor(telefono, ids_productos)
        if not exito:
            return responder_error(mensaje, 400)

        return responder_exito(None, mensaje)

    except Exception as e:
        logger.error(f"Error en asignar_productos: {str(e)}")
        return responder_error('Error al asignar productos al proveedor')
