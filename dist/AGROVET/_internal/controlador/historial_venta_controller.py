from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import logging
import sys
import os

# Agregar ruta para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modelo.historial_venta_model import model  # Esto importa la instancia 'model'
    logger = logging.getLogger(__name__)
    logger.info("Modelo de historial de ventas importado correctamente")
except Exception as e:
    print(f"Error importando modelo: {e}")
    import traceback
    traceback.print_exc()
    # Crear un modelo dummy para evitar errores
    class DummyModel:
        @staticmethod
        def obtener_historial_completo():
            return {'success': False, 'error': 'Modelo no cargado', 'ventas': []}
        @staticmethod
        def filtrar_ventas(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'ventas': []}
        @staticmethod
        def obtener_estadisticas_periodo(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def obtener_detalle_venta(venta_id):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def obtener_clientes_para_filtro():
            return {'success': False, 'error': 'Modelo no cargado', 'usuarios': []}
        @staticmethod
        def obtener_productos_para_filtro():
            return {'success': False, 'error': 'Modelo no cargado', 'productos': []}
        @staticmethod
        def obtener_ventas_recientes(limit=10):
            return {'success': False, 'error': 'Modelo no cargado', 'ventas': []}
        @staticmethod
        def obtener_estadisticas_financieras(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def obtener_estadisticas_financieras_periodo_rapido(periodo):
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def eliminar_venta_completa(venta_id, recuperar_productos=False):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def eliminar_ventas_multiples(ventas_ids, recuperar_productos=False):
            return {'success': False, 'error': 'Modelo no cargado', 'eliminadas': 0}
        @staticmethod
        def verificar_venta_para_eliminar(venta_id):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def obtener_ingresos_por_categoria_pago(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'ingresos': []}
    
    model = DummyModel()

# Crear blueprint
historial_venta_bp = Blueprint('historial_venta', __name__)

@historial_venta_bp.route('/api/historial-ventas', methods=['GET'])
def obtener_historial():
    """Obtener historial completo de ventas"""
    try:
        logger.info("Solicitando historial completo de ventas")
        resultado = model.obtener_historial_completo()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_historial: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total': 0
        }), 500

@historial_venta_bp.route('/api/historial-ventas/filtrar', methods=['GET'])
def filtrar_historial():
    """Filtrar historial de ventas"""
    try:
        # Obtener parámetros de la consulta
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_pago = request.args.get('tipo_pago')
        tipo_usuario = request.args.get('tipo_usuario')
        cliente_cedula = request.args.get('cliente_cedula')
        producto_id = request.args.get('producto_id')
        
        logger.info(f"Filtrando ventas con parámetros: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, "
                   f"tipo_pago={tipo_pago}, tipo_usuario={tipo_usuario}, "
                   f"cliente_cedula={cliente_cedula}, producto_id={producto_id}")
        
        resultado = model.filtrar_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_pago=tipo_pago,
            tipo_usuario=tipo_usuario,
            cliente_cedula=cliente_cedula,
            producto_id=producto_id
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en filtrar_historial: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total': 0
        }), 500

@historial_venta_bp.route('/api/historial-ventas/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas del período"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        logger.info(f"Obteniendo estadísticas para período: {fecha_inicio} - {fecha_fin}")
        
        resultado = model.obtener_estadisticas_periodo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'estadisticas': {
                'total_ventas': 0,
                'ingresos_totales': 0,
                'promedio_venta': 0,
                'total_unidades': 0
            },
            'ventas_por_pago': [],
            'tendencia_ventas': []
        }), 500

@historial_venta_bp.route('/api/historial-ventas/<int:venta_id>', methods=['GET'])
def obtener_detalle_venta(venta_id):
    """Obtener detalle de una venta específica"""
    try:
        logger.info(f"Obteniendo detalle para venta ID: {venta_id}")
        
        resultado = model.obtener_detalle_venta(venta_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 404
            
    except Exception as e:
        logger.error(f"Error en obtener_detalle_venta: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@historial_venta_bp.route('/api/historial-ventas/filtros/clientes', methods=['GET'])
def obtener_clientes_filtro():
    """Obtener lista de clientes para filtros"""
    try:
        logger.info("Obteniendo lista de clientes para filtros")
        resultado = model.obtener_clientes_para_filtro()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_clientes_filtro: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'usuarios': []
        }), 500

@historial_venta_bp.route('/api/historial-ventas/filtros/productos', methods=['GET'])
def obtener_productos_filtro():
    """Obtener lista de productos para filtros"""
    try:
        logger.info("Obteniendo lista de productos para filtros")
        resultado = model.obtener_productos_para_filtro()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_productos_filtro: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'productos': []
        }), 500

@historial_venta_bp.route('/api/historial-ventas/recientes', methods=['GET'])
def obtener_ventas_recientes():
    """Obtener ventas recientes"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        logger.info(f"Obteniendo {limit} ventas recientes")
        
        resultado = model.obtener_ventas_recientes(limit=limit)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_ventas_recientes: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total': 0
        }), 500

@historial_venta_bp.route('/api/historial-ventas/periodo/rapido', methods=['GET'])
def obtener_periodo_rapido():
    """Obtener ventas para períodos rápidos (hoy, semana, mes, año)"""
    try:
        periodo = request.args.get('periodo', 'hoy')
        
        hoy = datetime.now()
        
        if periodo == 'hoy':
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        elif periodo == 'semana':
            fecha_inicio = (hoy - timedelta(days=hoy.weekday())).date()
            fecha_fin = hoy.date()
        elif periodo == 'mes':
            fecha_inicio = hoy.replace(day=1).date()
            fecha_fin = hoy.date()
        elif periodo == 'anio':
            fecha_inicio = hoy.replace(month=1, day=1).date()
            fecha_fin = hoy.date()
        else:
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        
        logger.info(f"Período rápido: {periodo} ({fecha_inicio} - {fecha_fin})")
        
        # Obtener ventas del período
        resultado_ventas = model.filtrar_ventas(
            fecha_inicio=str(fecha_inicio),
            fecha_fin=str(fecha_fin)
        )
        
        # Obtener estadísticas financieras del período
        resultado_financieras = model.obtener_estadisticas_financieras(
            fecha_inicio=str(fecha_inicio),
            fecha_fin=str(fecha_fin)
        )
        
        # Obtener estadísticas tradicionales (para compatibilidad)
        resultado_estadisticas = model.obtener_estadisticas_periodo(
            fecha_inicio=str(fecha_inicio),
            fecha_fin=str(fecha_fin)
        )
        
        # Asegurarse de que los datos sean serializables
        response_data = {
            'success': True,
            'periodo': periodo,
            'fecha_inicio': str(fecha_inicio),
            'fecha_fin': str(fecha_fin),
            'ventas': resultado_ventas.get('ventas', []) if resultado_ventas.get('success') else [],
            'total_ventas': resultado_ventas.get('total', 0) if resultado_ventas.get('success') else 0,
            
            # Estadísticas financieras (nuevo dashboard)
            'estadisticas_financieras': resultado_financieras.get('estadisticas', {}) if resultado_financieras.get('success') else {},
            
            # Estadísticas tradicionales (para compatibilidad con gráficos)
            'estadisticas': resultado_estadisticas.get('estadisticas', {}) if resultado_estadisticas.get('success') else {},
            'ventas_por_pago': resultado_estadisticas.get('ventas_por_pago', []) if resultado_estadisticas.get('success') else [],
            'ingresos_por_pago': resultado_estadisticas.get('ingresos_por_pago', []) if resultado_estadisticas.get('success') else [],
            'tendencia_ventas': resultado_estadisticas.get('tendencia_ventas', []) if resultado_estadisticas.get('success') else []
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error en obtener_periodo_rapido: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total_ventas': 0,
            'estadisticas_financieras': {},
            'estadisticas': {},
            'ventas_por_pago': [],
            'ingresos_por_pago': [],
            'tendencia_ventas': []
        }), 500
        
@historial_venta_bp.route('/api/historial-ventas/exportar/excel', methods=['GET'])
def exportar_excel():
    """Exportar historial de ventas a Excel/CSV"""
    try:
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_pago = request.args.get('tipo_pago')
        tipo_usuario = request.args.get('tipo_usuario')
        cliente_cedula = request.args.get('cliente_cedula')
        
        logger.info(f"Exportando a Excel con filtros: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        
        # Obtener datos filtrados
        resultado = model.filtrar_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_pago=tipo_pago,
            tipo_usuario=tipo_usuario,
            cliente_cedula=cliente_cedula
        )
        
        if not resultado.get('success') or not resultado.get('ventas'):
            return jsonify({
                'success': False,
                'error': 'No hay datos para exportar'
            }), 404
        
        ventas = resultado['ventas']
        
        # Crear contenido CSV (compatible con Excel)
        csv_lines = []
        
        # Encabezados
        headers = [
            "ID Venta", "Número Venta", "Fecha", "Hora", "Cliente", 
            "Cédula/NIT", "Tipo Cliente", "Teléfono", "Dirección",
            "Método Pago", "Subtotal", "Descuento", "Total", 
            "Productos Vendidos", "Total Unidades"
        ]
        csv_lines.append(";".join(headers))
        
        # Datos de cada venta
        for venta in ventas:
            # Formatear fecha y hora
            fecha = venta.get('fecha_dia', '')
            hora = venta.get('fecha_hora', '')
            if isinstance(fecha, str):
                fecha_formateada = fecha
            else:
                fecha_formateada = str(fecha)
            
            if isinstance(hora, str):
                hora_formateada = hora
            else:
                hora_formateada = str(hora)
            
            # Contar productos y unidades
            productos_list = venta.get('productos', [])
            total_productos = len(productos_list)
            total_unidades = sum(p.get('cantidad', 0) for p in productos_list)
            
            # Lista de productos (para columna de productos)
            productos_str = " | ".join([
                f"{p.get('nombre', '')} ({p.get('cantidad', 0)} x ${p.get('precio_unitario', 0):,.0f})"
                for p in productos_list[:5]  # Limitar a 5 productos para evitar línea muy larga
            ])
            if total_productos > 5:
                productos_str += f" ... y {total_productos - 5} más"
            
            # Crear línea CSV
            linea = [
                str(venta.get('id', '')),
                str(venta.get('numero_venta', '')),
                fecha_formateada,
                hora_formateada,
                venta.get('nombre_cliente', 'CLIENTE FINAL'),
                venta.get('cliente_cedula', ''),
                venta.get('usuario_tipo', 'cliente'),
                venta.get('telefono_cliente', ''),
                venta.get('direccion_cliente', '') or '',
                venta.get('tipo_pago', ''),
                f"{float(venta.get('subtotal', 0)):,.0f}",
                f"{float(venta.get('descuento', 0)):,.0f}",
                f"{float(venta.get('total', 0)):,.0f}",
                productos_str,
                str(total_unidades)
            ]
            
            # Escapar punto y coma dentro de celdas
            linea_escapada = [str(cell).replace(';', ',') for cell in linea]
            csv_lines.append(";".join(linea_escapada))
        
        csv_content = "\n".join(csv_lines)
        
        # Crear respuesta con archivo CSV
        from io import StringIO
        from flask import Response
        
        output = StringIO()
        output.write(csv_content)
        
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=historial_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        logger.info(f"Exportación a Excel completada: {len(ventas)} ventas")
        return response
        
    except Exception as e:
        logger.error(f"Error exportando a Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@historial_venta_bp.route('/api/historial-ventas/exportar/resumen-excel', methods=['GET'])
def exportar_resumen_excel():
    """Exportar resumen estadístico a Excel"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        logger.info(f"Exportando resumen a Excel: {fecha_inicio} - {fecha_fin}")
        
        # Obtener estadísticas
        resultado = model.obtener_estadisticas_periodo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        if not resultado.get('success'):
            return jsonify({
                'success': False,
                'error': 'No se pudieron obtener estadísticas'
            }), 500
        
        estadisticas = resultado.get('estadisticas', {})
        ventas_por_pago = resultado.get('ventas_por_pago', [])
        tendencia_ventas = resultado.get('tendencia_ventas', [])
        
        # Crear contenido CSV
        csv_lines = []
        
        # 1. Título y período
        csv_lines.append(f"RESUMEN DE VENTAS - AGROVET YACUANQUER")
        if fecha_inicio and fecha_fin:
            csv_lines.append(f"Período: {fecha_inicio} - {fecha_fin}")
        csv_lines.append("")  # Línea vacía
        
        # 2. Estadísticas generales
        csv_lines.append("ESTADÍSTICAS GENERALES")
        csv_lines.append("Métrica;Valor")
        csv_lines.append(f"Ventas Totales;{estadisticas.get('total_ventas', 0)}")
        csv_lines.append(f"Ingresos Totales;${float(estadisticas.get('ingresos_totales', 0)):,.0f}")
        csv_lines.append(f"Venta Promedio;${float(estadisticas.get('promedio_venta', 0)):,.0f}")
        csv_lines.append(f"Unidades Vendidas;{estadisticas.get('total_unidades', 0)}")
        csv_lines.append("")  # Línea vacía
        
        # 3. Ventas por tipo de pago
        csv_lines.append("VENTAS POR TIPO DE PAGO")
        csv_lines.append("Tipo de Pago;Cantidad;Monto Total;Porcentaje")
        
        total_ventas_pago = sum(v.get('cantidad', 0) for v in ventas_por_pago)
        total_monto_pago = sum(float(v.get('monto_total', 0)) for v in ventas_por_pago)
        
        for venta_pago in ventas_por_pago:
            cantidad = venta_pago.get('cantidad', 0)
            monto = float(venta_pago.get('monto_total', 0))
            porcentaje = (cantidad / total_ventas_pago * 100) if total_ventas_pago > 0 else 0
            
            csv_lines.append(
                f"{venta_pago.get('tipo_pago', '')};"
                f"{cantidad};"
                f"${monto:,.0f};"
                f"{porcentaje:.1f}%"
            )
        
        csv_lines.append("")  # Línea vacía
        
        # 4. Tendencia de ventas (últimos 7 días)
        if tendencia_ventas:
            csv_lines.append("TENDENCIA DE VENTAS (ÚLTIMOS 7 DÍAS)")
            csv_lines.append("Fecha;Ventas;Ingresos")
            
            for tendencia in tendencia_ventas:
                csv_lines.append(
                    f"{tendencia.get('fecha_dia', '')};"
                    f"{tendencia.get('cantidad_ventas', 0)};"
                    f"${float(tendencia.get('total_dia', 0)):,.0f}"
                )
        
        csv_lines.append("")  # Línea vacía
        
        # 5. Información de exportación
        csv_lines.append(f"Exportado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        csv_lines.append("Sistema POS - Agrovet Yacuanquer")
        
        csv_content = "\n".join(csv_lines)
        
        # Crear respuesta
        from io import StringIO
        from flask import Response
        
        output = StringIO()
        output.write(csv_content)
        
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=resumen_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        logger.info("Exportación de resumen a Excel completada")
        return response
        
    except Exception as e:
        logger.error(f"Error exportando resumen a Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@historial_venta_bp.route('/api/historial-ventas/test', methods=['GET'])
def test_conexion():
    """Endpoint de prueba para verificar que el historial funciona"""
    try:
        logger.info("Test endpoint de historial de ventas llamado")
        
        return jsonify({
            'success': True,
            'message': 'Historial de ventas funcionando correctamente',
            'endpoints': {
                'GET /api/historial-ventas': 'Obtener historial completo',
                'GET /api/historial-ventas/filtrar': 'Filtrar historial',
                'GET /api/historial-ventas/estadisticas': 'Obtener estadísticas',
                'GET /api/historial-ventas/{id}': 'Detalle de venta',
                'GET /api/historial-ventas/filtros/clientes': 'Clientes para filtro',
                'GET /api/historial-ventas/filtros/productos': 'Productos para filtro',
                'GET /api/historial-ventas/recientes': 'Ventas recientes',
                'GET /api/historial-ventas/periodo/rapido': 'Períodos rápidos'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en test_conexion: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@historial_venta_bp.route('/api/historial-ventas/estadisticas-financieras', methods=['GET'])
def obtener_estadisticas_financieras():
    """Obtener estadísticas financieras para el dashboard"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo = request.args.get('periodo')
        
        logger.info(f"Obteniendo estadísticas financieras: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, periodo={periodo}")
        
        if periodo and not fecha_inicio and not fecha_fin:
            # Usar período rápido
            resultado = model.obtener_estadisticas_financieras_periodo_rapido(periodo)
        else:
            # Usar fechas específicas
            resultado = model.obtener_estadisticas_financieras(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_financieras: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@historial_venta_bp.route('/api/historial-ventas/<int:venta_id>/eliminar', methods=['DELETE'])
def eliminar_venta(venta_id):
    """Eliminar una venta y todos sus registros relacionados"""
    try:
        logger.info(f"Solicitud para eliminar venta ID: {venta_id}")
        
        # Obtener parámetro de recuperación de productos
        recuperar_productos = request.args.get('recuperar_productos', 'false').lower() == 'true'
        logger.info(f"Recuperar productos: {recuperar_productos}")
        
        # Verificar si la venta existe
        resultado_existencia = model.obtener_detalle_venta(venta_id)
        
        if not resultado_existencia.get('success'):
            logger.warning(f"Venta {venta_id} no encontrada")
            return jsonify({
                'success': False,
                'error': 'Venta no encontrada'
            }), 404
        
        venta = resultado_existencia.get('venta', {})
        
        # Verificar si es una venta de crédito
        es_credito = venta.get('tipo_pago') == 'CRÉDITO'
        logger.info(f"Venta {venta_id} es de crédito: {es_credito}")
        
        # Eliminar la venta y sus registros relacionados
        resultado_eliminacion = model.eliminar_venta_completa(venta_id, recuperar_productos=recuperar_productos)
        
        if resultado_eliminacion.get('success'):
            logger.info(f"Venta {venta_id} eliminada exitosamente")
            
            # Mensaje específico para productos recuperados
            mensaje_respuesta = resultado_eliminacion.get('message', f'Venta #{venta_id} eliminada exitosamente')
            
            # Detalles para mostrar al usuario
            detalles = resultado_eliminacion.get('detalles', {})
            productos_recuperados = detalles.get('productos_recuperados', [])
            recuperados_exitosos = detalles.get('recuperados_exitosos', 0)
            
            respuesta = {
                'success': True,
                'message': mensaje_respuesta,
                'detalles': {
                    'venta_id': venta_id,
                    'cliente': venta.get('nombre_cliente', ''),
                    'total': venta.get('total', 0),
                    'fecha': venta.get('fecha_dia', ''),
                    'tipo_pago': venta.get('tipo_pago', ''),
                    'es_credito': es_credito,
                    'productos_recuperados': productos_recuperados,
                    'recuperados_exitosos': recuperados_exitosos,
                    'recuperados_fallidos': detalles.get('recuperados_fallidos', 0),
                    'recuperar_productos': recuperar_productos
                }
            }
            
            return jsonify(respuesta)
        else:
            error_msg = resultado_eliminacion.get('error', 'Error desconocido al eliminar')
            logger.error(f"Error eliminando venta {venta_id}: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
            
    except Exception as e:
        logger.error(f"Error en eliminar_venta: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error interno del servidor: {str(e)}'
        }), 500

@historial_venta_bp.route('/api/historial-ventas/multiple-eliminar', methods=['POST'])
def eliminar_ventas_multiples():
    """Eliminar múltiples ventas en una sola operación"""
    try:
        data = request.get_json()
        
        if not data or 'ventas_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'No se proporcionaron IDs de ventas'
            }), 400
        
        ventas_ids = data['ventas_ids']
        recuperar_productos = data.get('recuperar_productos', False)
        
        if not isinstance(ventas_ids, list) or len(ventas_ids) == 0:
            return jsonify({
                'success': False,
                'error': 'Se requiere una lista de IDs de ventas'
            }), 400
        
        logger.info(f"Solicitud para eliminar {len(ventas_ids)} ventas: {ventas_ids}, recuperar_productos={recuperar_productos}")
        
        # Verificar cada venta antes de proceder
        ventas_no_encontradas = []
        
        for venta_id in ventas_ids:
            resultado = model.obtener_detalle_venta(venta_id)
            if not resultado.get('success'):
                ventas_no_encontradas.append(venta_id)
        
        if ventas_no_encontradas:
            logger.warning(f"Ventas no encontradas: {ventas_no_encontradas}")
        
        # Eliminar las ventas
        resultados = model.eliminar_ventas_multiples(ventas_ids, recuperar_productos=recuperar_productos)
        
        if resultados.get('success'):
            logger.info(f"Eliminación múltiple completada: {resultados.get('eliminadas', 0)} ventas")
            
            response_data = {
                'success': True,
                'message': f'{resultados.get("eliminadas", 0)} ventas eliminadas exitosamente',
                'detalles': resultados.get('detalles', {
                    'eliminadas': resultados.get('eliminadas', 0),
                    'no_encontradas': ventas_no_encontradas,
                    'creditos_eliminados': resultados.get('creditos_eliminados', 0),
                    'detalles_eliminados': resultados.get('detalles_eliminados', 0),
                    'productos_recuperados': resultados.get('productos_recuperados', [])
                })
            }
            
            return jsonify(response_data)
        else:
            error_msg = resultados.get('error', 'Error desconocido en eliminación múltiple')
            logger.error(f"Error en eliminación múltiple: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
            
    except Exception as e:
        logger.error(f"Error en eliminar_ventas_multiples: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error interno del servidor: {str(e)}'
        }), 500

@historial_venta_bp.route('/api/historial-ventas/ingresos-por-categoria', methods=['GET'])
def obtener_ingresos_por_categoria():
    """Obtener ingresos por categoría de pago"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo = request.args.get('periodo')
        
        logger.info(f"Obteniendo ingresos por categoría: {fecha_inicio} - {fecha_fin}")
        
        resultado = model.obtener_ingresos_por_categoria_pago(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            periodo=periodo
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_ingresos_por_categoria: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ingresos': []
        }), 500

@historial_venta_bp.route('/api/historial-ventas/<int:venta_id>/verificar', methods=['GET'])
def verificar_venta(venta_id):
    """Verificar información de una venta antes de eliminarla"""
    try:
        logger.info(f"Verificando venta ID: {venta_id}")
        
        resultado = model.verificar_venta_para_eliminar(venta_id)
        
        if resultado.get('success'):
            return jsonify(resultado)
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Error en verificación'),
                'puede_eliminar': False
            }), 400
            
    except Exception as e:
        logger.error(f"Error en verificar_venta: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'puede_eliminar': False
        }), 500