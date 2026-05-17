from database import db
from datetime import datetime, timedelta, date
import logging
from decimal import Decimal
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

def convertir_para_json(data):
    """Función auxiliar para convertir tipos de datos no serializables a JSON
    ⭐ FORMATO CORREGIDO: muestra '25 abr 2026 07:25 PM' ⭐
    """
    if isinstance(data, dict):
        return {key: convertir_para_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convertir_para_json(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, timedelta):
        return data.days
    elif isinstance(data, datetime):
        # ⭐⭐⭐ FORMATO 12 HORAS: "25 abr 2026 07:25 PM" ⭐⭐⭐
        meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        
        # Convertir a formato 12 horas
        hora_12 = data.hour % 12
        if hora_12 == 0:
            hora_12 = 12
        ampm = "AM" if data.hour < 12 else "PM"
        
        fecha_formateada = f"{data.day:02d} {meses[data.month-1]} {data.year}"
        
        # Agregar hora si no es medianoche
        if data.hour != 0 or data.minute != 0 or data.second != 0:
            fecha_formateada += f" {hora_12:02d}:{data.minute:02d} {ampm}"
        
        return fecha_formateada
    elif isinstance(data, date):
        # ⭐⭐⭐ PARA FECHAS SIN HORA ⭐⭐⭐
        meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        return f"{data.day:02d} {meses[data.month-1]} {data.year}"
    elif isinstance(data, bytes):
        return data.decode('utf-8')
    elif hasattr(data, '__dict__'):
        return convertir_para_json(data.__dict__)
    else:
        return data

def format_sql_date(date_str):
    """Formatear fecha desde SQL"""
    if not date_str:
        return None
    try:
        # Intentar varios formatos comunes
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except ValueError:
                continue
        # Si no coincide ningún formato, devolver como está
        return date_str
    except Exception:
        return date_str

class HistorialVentaModel:
    
    @staticmethod
    def obtener_historial_completo():
        """Obtener el historial completo de ventas con detalles"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    v.id,
                    v.numero_venta,
                    DATE(v.fecha_dia) as fecha_dia,
                    TIME(v.fecha_hora) as fecha_hora,
                    v.nombre_cliente,
                    v.direccion_cliente,
                    v.telefono_cliente,
                    v.tipo_pago,
                    v.cliente_cedula,
                    v.subtotal,
                    v.descuento,
                    v.total,
                    v.dias_credito,
                    v.submetodo_banco,
                    v.usuario_id,
                    v.estado,
                    (SELECT COUNT(*) FROM ventas_mixtas vm WHERE vm.id_venta = v.id) as es_mixta
                FROM ventas v
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
            """
            
            cursor.execute(query)
            ventas = cursor.fetchall()
            
            # Para cada venta, obtener los productos
            for venta in ventas:
                # Combinar fecha y hora en un solo datetime para formatear correctamente
                if venta.get('fecha_dia') and venta.get('fecha_hora'):
                    try:
                        fecha_obj = venta['fecha_dia']
                        hora_str = str(venta['fecha_hora'])
                        # Crear datetime combinado
                        if isinstance(fecha_obj, date):
                            hora_partes = hora_str.split(':')
                            hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                            minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                            segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                            fecha_datetime = datetime(
                                fecha_obj.year, fecha_obj.month, fecha_obj.day,
                                hora, minuto, segundo
                            )
                            venta['fecha_completa'] = fecha_datetime
                    except Exception as e:
                        logger.warning(f"Error combinando fecha/hora: {e}")
                        venta['fecha_completa'] = venta['fecha_dia']
                else:
                    venta['fecha_completa'] = venta['fecha_dia']
                
                # Obtener información del crédito
                credito_query = """
                    SELECT 
                        c.estado as estado_credito,
                        c.anticipo as anticipo_credito,
                        c.abonos_realizados as abonos_credito,
                        c.saldo_pendiente as saldo_pendiente_credito,
                        c.deuda_inicial as deuda_inicial_credito,
                        c.fecha_vencimiento as fecha_vencimiento_credito
                    FROM creditos c
                    WHERE c.venta_id = %s
                    LIMIT 1
                """
                cursor.execute(credito_query, (venta['id'],))
                credito = cursor.fetchone()
                
                if credito:
                    venta.update(credito)
                else:
                    venta['estado_credito'] = None
                    venta['anticipo_credito'] = 0
                    venta['abonos_credito'] = 0
                    venta['saldo_pendiente_credito'] = 0
                    venta['deuda_inicial_credito'] = 0
                    venta['fecha_vencimiento_credito'] = None
                
                # Si es venta mixta, obtener detalles
                if venta['es_mixta']:
                    mixta_query = """
                        SELECT 
                            categoria,
                            metodo_pago,
                            submetodo,
                            SUM(monto) as monto_total
                        FROM ventas_mixtas
                        WHERE id_venta = %s
                        GROUP BY categoria, metodo_pago, submetodo
                        ORDER BY categoria, metodo_pago
                    """
                    cursor.execute(mixta_query, (venta['id'],))
                    detalles_mixtos = cursor.fetchall()
                    venta['detalles_mixtos'] = detalles_mixtos
                
                # Obtener productos con cálculo de utilidad
                producto_query = """
                    SELECT 
                        dv.id,
                        dv.id_producto,
                        p.nombre,
                        p.categoria,
                        p.presentacion,
                        dv.cantidad_vendida as cantidad,
                        dv.precio_unidad as precio_unitario,
                        dv.precio_neto as subtotal,
                        p.precio_costo,
                        p.precio_venta,
                        (dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida as utilidad_producto
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """
                cursor.execute(producto_query, (venta['id'],))
                productos = cursor.fetchall()
                
                # Calcular utilidad total y costo total
                utilidad_total = 0
                costo_total = 0
                
                for producto in productos:
                    precio_unidad = float(producto.get('precio_unitario', 0))
                    precio_costo = float(producto.get('precio_costo', 0))
                    cantidad = int(producto.get('cantidad', 0))
                    
                    utilidad_producto = (precio_unidad - precio_costo) * cantidad
                    producto['utilidad_producto'] = utilidad_producto
                    
                    utilidad_total += utilidad_producto
                    costo_total += precio_costo * cantidad
                
                venta['productos'] = productos
                venta['utilidad'] = utilidad_total
                venta['costo_total'] = costo_total
                
                # Contar productos y unidades
                total_productos = len(productos)
                total_unidades = sum(p.get('cantidad', 0) for p in productos)
                venta['total_productos'] = total_productos
                venta['total_unidades'] = total_unidades
                
                # Calcular utilidad realizada y proyectada según tipo de pago
                if venta['es_mixta']:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                    venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                elif venta['tipo_pago'] == 'CRÉDITO':
                    if venta['estado_credito'] == 'pagado':
                        venta['utilidad_realizada'] = utilidad_total
                        venta['utilidad_proyectada'] = 0
                        venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                    else:
                        venta['utilidad_realizada'] = 0
                        venta['utilidad_proyectada'] = utilidad_total
                        venta['etiqueta_utilidad'] = 'Utilidad Proyectada'
                else:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                    venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                
                # Calcular porcentajes de utilidad
                total_venta = float(venta['total']) if venta['total'] else 0
                if total_venta > 0:
                    venta['utilidad_porcentaje'] = (utilidad_total / total_venta) * 100
                    venta['margen_venta'] = (utilidad_total / total_venta) * 100
                else:
                    venta['utilidad_porcentaje'] = 0
                    venta['margen_venta'] = 0
                
                if costo_total > 0:
                    venta['rentabilidad_costo'] = (utilidad_total / costo_total) * 100
                else:
                    venta['rentabilidad_costo'] = 0
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            ventas = convertir_para_json(ventas)
            
            logger.info(f"Obtenidas {len(ventas)} ventas del historial")
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial completo: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }

    @staticmethod
    def obtener_ingresos_por_categoria_pago(fecha_inicio=None, fecha_fin=None, periodo=None):
        """Obtener ingresos por categoría de pago SIN ventas mixtas"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_conditions = []
            params_base = []
            
            if fecha_inicio and fecha_fin:
                where_conditions.append("v.fecha_dia BETWEEN %s AND %s")
                params_base.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_conditions.append("v.fecha_dia >= %s")
                params_base.append(fecha_inicio)
            elif fecha_fin:
                where_conditions.append("v.fecha_dia <= %s")
                params_base.append(fecha_fin)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
                SELECT 
                    CASE 
                        WHEN v.tipo_pago = 'CONTADO' THEN 'CONTADO'
                        WHEN v.tipo_pago = 'CRÉDITO' THEN 'CRÉDITO'
                        WHEN v.tipo_pago IN ('NEQUI', 'TRANSACCIÓN', 'TARJETA') THEN 'BANCO'
                        ELSE 'BANCO'
                    END as categoria_pago,
                    
                    COUNT(DISTINCT v.id) as cantidad_ventas,
                    
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CONTADO' THEN v.total
                            WHEN v.tipo_pago = 'NEQUI' THEN v.total
                            WHEN v.tipo_pago = 'TRANSACCIÓN' THEN v.total
                            WHEN v.tipo_pago = 'TARJETA' THEN v.total
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE v.total
                        END
                    ), 0) as ingresos_reales,
                    
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN v.total
                            ELSE 0
                        END
                    ), 0) as total_creditos,
                    
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.saldo_pendiente, 0)
                            ELSE 0
                        END
                    ), 0) as saldo_pendiente
                    
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id AND v.tipo_pago = 'CRÉDITO'
                WHERE v.id NOT IN (SELECT DISTINCT id_venta FROM ventas_mixtas)
                    AND {where_clause}
                GROUP BY 
                    CASE 
                        WHEN v.tipo_pago = 'CONTADO' THEN 'CONTADO'
                        WHEN v.tipo_pago = 'CRÉDITO' THEN 'CRÉDITO'
                        WHEN v.tipo_pago IN ('NEQUI', 'TRANSACCIÓN', 'TARJETA') THEN 'BANCO'
                        ELSE 'BANCO'
                    END
                ORDER BY ingresos_reales DESC
            """
            
            cursor.execute(query, params_base.copy())
            categorias = cursor.fetchall()
            
            bancos_query = f"""
                SELECT 
                    v.tipo_pago as metodo_pago,
                    COUNT(DISTINCT v.id) as cantidad_ventas,
                    COALESCE(SUM(v.total), 0) as monto_total
                FROM ventas v
                WHERE v.id NOT IN (SELECT DISTINCT id_venta FROM ventas_mixtas)
                    AND v.tipo_pago NOT IN ('CONTADO', 'CRÉDITO')
                    AND {where_clause}
                GROUP BY v.tipo_pago
                ORDER BY monto_total DESC
            """
            
            cursor.execute(bancos_query, params_base.copy())
            metodos_bancarios = cursor.fetchall()
            
            total_banco_query = f"""
                SELECT 
                    COALESCE(SUM(v.total), 0) as total_banco
                FROM ventas v
                WHERE v.id NOT IN (SELECT DISTINCT id_venta FROM ventas_mixtas)
                    AND v.tipo_pago NOT IN ('CONTADO', 'CRÉDITO')
                    AND {where_clause}
            """
            
            cursor.execute(total_banco_query, params_base.copy())
            total_banco = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            resultado = []
            for categoria in categorias:
                cat_data = convertir_para_json(categoria)
                
                if cat_data['cantidad_ventas'] > 0:
                    if cat_data['categoria_pago'] == 'BANCO':
                        cat_data['detalle_bancos'] = []
                        for metodo in metodos_bancarios:
                            metodo_data = convertir_para_json(metodo)
                            if metodo_data['monto_total'] > 0:
                                tipo_pago = str(metodo_data['metodo_pago']).upper().strip()
                                mapeo_tipos = {
                                    'NEQUI': 'NEQUI',
                                    'TRANSACCIÓN': 'TRANSACCIÓN',
                                    'TRANSFERENCIA': 'TRANSFERENCIA',
                                    'TARJETA': 'TARJETA',
                                    'BANCO': 'TRANSFERENCIA BANCARIA'
                                }
                                nombre_tipo = mapeo_tipos.get(tipo_pago, tipo_pago)
                                cat_data['detalle_bancos'].append({
                                    'metodo': nombre_tipo,
                                    'cantidad': int(metodo_data['cantidad_ventas']),
                                    'monto': float(metodo_data['monto_total'])
                                })
                    
                    resultado.append({
                        'categoria': cat_data['categoria_pago'],
                        'cantidad_ventas': int(cat_data['cantidad_ventas']),
                        'ingresos_reales': float(cat_data['ingresos_reales']),
                        'total_creditos': float(cat_data.get('total_creditos', 0)),
                        'saldo_pendiente': float(cat_data.get('saldo_pendiente', 0)),
                        'detalle_bancos': cat_data.get('detalle_bancos', [])
                    })
            
            logger.info(f"Ingresos por categoría: {len(resultado)} categorías")
            return {
                'success': True,
                'ingresos': resultado
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ingresos por categoría: {e}")
            return {
                'success': False,
                'error': str(e),
                'ingresos': []
            }
        
    @staticmethod
    def filtrar_ventas(fecha_inicio=None, fecha_fin=None, tipo_pago=None, 
                       tipo_usuario=None, cliente_cedula=None, producto_id=None):
        """Filtrar ventas según criterios"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            subquery = """
                SELECT v.id
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                WHERE 1=1
            """
            params = []
            
            if fecha_inicio and fecha_fin:
                subquery += " AND v.fecha_dia BETWEEN %s AND %s"
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                subquery += " AND v.fecha_dia >= %s"
                params.append(fecha_inicio)
            elif fecha_fin:
                subquery += " AND v.fecha_dia <= %s"
                params.append(fecha_fin)
            
            if tipo_pago:
                subquery += " AND v.tipo_pago = %s"
                params.append(tipo_pago)
            
            if cliente_cedula:
                subquery += " AND v.cliente_cedula = %s"
                params.append(cliente_cedula)
            
            if producto_id:
                subquery += " AND dv.id_producto = %s"
                params.append(producto_id)
            
            query = f"""
                SELECT 
                    v.id,
                    v.numero_venta,
                    DATE(v.fecha_dia) as fecha_dia,
                    TIME(v.fecha_hora) as fecha_hora,
                    v.nombre_cliente,
                    v.direccion_cliente,
                    v.telefono_cliente,
                    v.tipo_pago,
                    v.cliente_cedula,
                    v.subtotal,
                    v.descuento,
                    v.total,
                    v.dias_credito,
                    v.submetodo_banco,
                    v.usuario_id,
                    v.estado,
                    (SELECT COUNT(*) FROM ventas_mixtas vm WHERE vm.id_venta = v.id) as es_mixta
                FROM ventas v
                WHERE v.id IN ({subquery})
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
            """
            
            cursor.execute(query, params)
            ventas = cursor.fetchall()
            
            for venta in ventas:
                # Combinar fecha y hora
                if venta.get('fecha_dia') and venta.get('fecha_hora'):
                    try:
                        fecha_obj = venta['fecha_dia']
                        hora_str = str(venta['fecha_hora'])
                        if isinstance(fecha_obj, date):
                            hora_partes = hora_str.split(':')
                            hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                            minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                            segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                            fecha_datetime = datetime(
                                fecha_obj.year, fecha_obj.month, fecha_obj.day,
                                hora, minuto, segundo
                            )
                            venta['fecha_completa'] = fecha_datetime
                    except Exception:
                        venta['fecha_completa'] = venta['fecha_dia']
                else:
                    venta['fecha_completa'] = venta['fecha_dia']
                
                credito_query = """
                    SELECT 
                        c.estado as estado_credito,
                        c.anticipo as anticipo_credito,
                        c.abonos_realizados as abonos_credito,
                        c.saldo_pendiente as saldo_pendiente_credito,
                        c.deuda_inicial as deuda_inicial_credito
                    FROM creditos c
                    WHERE c.venta_id = %s
                    LIMIT 1
                """
                cursor.execute(credito_query, (venta['id'],))
                credito = cursor.fetchone()
                
                if credito:
                    venta.update(credito)
                else:
                    venta['estado_credito'] = None
                    venta['anticipo_credito'] = 0
                    venta['abonos_credito'] = 0
                    venta['saldo_pendiente_credito'] = 0
                    venta['deuda_inicial_credito'] = 0
                
                if venta['es_mixta']:
                    mixta_query = """
                        SELECT 
                            categoria,
                            metodo_pago,
                            submetodo,
                            SUM(monto) as monto_total
                        FROM ventas_mixtas
                        WHERE id_venta = %s
                        GROUP BY categoria, metodo_pago, submetodo
                        ORDER BY categoria, metodo_pago
                    """
                    cursor.execute(mixta_query, (venta['id'],))
                    detalles_mixtos = cursor.fetchall()
                    venta['detalles_mixtos'] = detalles_mixtos
                
                producto_query = """
                    SELECT 
                        dv.id,
                        dv.id_producto,
                        p.nombre,
                        p.categoria,
                        p.presentacion,
                        dv.cantidad_vendida as cantidad,
                        dv.precio_unidad as precio_unitario,
                        dv.precio_neto as subtotal,
                        p.precio_costo,
                        p.precio_venta,
                        (dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida as utilidad_producto
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """
                cursor.execute(producto_query, (venta['id'],))
                productos = cursor.fetchall()
                
                utilidad_total = 0
                costo_total = 0
                
                for producto in productos:
                    precio_unidad = float(producto.get('precio_unitario', 0))
                    precio_costo = float(producto.get('precio_costo', 0))
                    cantidad = int(producto.get('cantidad', 0))
                    
                    utilidad_producto = (precio_unidad - precio_costo) * cantidad
                    producto['utilidad_producto'] = utilidad_producto
                    
                    utilidad_total += utilidad_producto
                    costo_total += precio_costo * cantidad
                
                venta['productos'] = productos
                venta['utilidad'] = utilidad_total
                venta['costo_total'] = costo_total
                
                total_productos = len(productos)
                total_unidades = sum(p.get('cantidad', 0) for p in productos)
                venta['total_productos'] = total_productos
                venta['total_unidades'] = total_unidades
                
                if venta['es_mixta']:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                    venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                elif venta['tipo_pago'] == 'CRÉDITO':
                    if venta['estado_credito'] == 'pagado':
                        venta['utilidad_realizada'] = utilidad_total
                        venta['utilidad_proyectada'] = 0
                        venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                    else:
                        venta['utilidad_realizada'] = 0
                        venta['utilidad_proyectada'] = utilidad_total
                        venta['etiqueta_utilidad'] = 'Utilidad Proyectada'
                else:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                    venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                
                total_venta = float(venta['total']) if venta['total'] else 0
                venta['utilidad_porcentaje'] = (utilidad_total / total_venta * 100) if total_venta > 0 else 0
                
                if total_venta > 0:
                    venta['margen_venta'] = (utilidad_total / total_venta) * 100
                else:
                    venta['margen_venta'] = 0
                
                if costo_total > 0:
                    venta['rentabilidad_costo'] = (utilidad_total / costo_total) * 100
                else:
                    venta['rentabilidad_costo'] = 0
            
            cursor.close()
            conn.close()
            
            ventas = convertir_para_json(ventas)
            
            logger.info(f"Filtradas {len(ventas)} ventas")
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error filtrando ventas: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }
    
    @staticmethod
    def obtener_estadisticas_periodo(fecha_inicio=None, fecha_fin=None):
        """Obtener estadísticas del período considerando créditos correctamente"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE 1=1"
            params = []
            
            if fecha_inicio and fecha_fin:
                where_clause += " AND v.fecha_dia BETWEEN %s AND %s"
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_clause += " AND v.fecha_dia >= %s"
                params.append(fecha_inicio)
            elif fecha_fin:
                where_clause += " AND v.fecha_dia <= %s"
                params.append(fecha_fin)
            
            ingresos_query = f"""
                SELECT 
                    COUNT(DISTINCT v.id) as total_ventas,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago != 'CRÉDITO' THEN v.total
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE 0
                        END
                    ), 0) as ingresos_totales,
                    COALESCE(AVG(v.total), 0) as promedio_venta,
                    COALESCE(SUM(dv.cantidad_vendida), 0) as total_unidades_vendidas
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
            """
            
            cursor.execute(ingresos_query, params.copy())
            estadisticas = cursor.fetchone()
            
            utilidad_query = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago != 'CRÉDITO' THEN 
                                (SELECT SUM((dv2.precio_unidad - p2.precio_costo) * dv2.cantidad_vendida)
                                 FROM detalle_venta dv2
                                 JOIN productos p2 ON dv2.id_producto = p2.id
                                 WHERE dv2.id_venta = v.id)
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado = 'pagado' THEN 
                                (SELECT SUM((dv2.precio_unidad - p2.precio_costo) * dv2.cantidad_vendida)
                                 FROM detalle_venta dv2
                                 JOIN productos p2 ON dv2.id_producto = p2.id
                                 WHERE dv2.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as utilidad_total,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado != 'pagado' THEN 
                                (SELECT SUM((dv2.precio_unidad - p2.precio_costo) * dv2.cantidad_vendida)
                                 FROM detalle_venta dv2
                                 JOIN productos p2 ON dv2.id_producto = p2.id
                                 WHERE dv2.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as utilidad_pendiente_creditos
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
            """
            
            cursor.execute(utilidad_query, params.copy())
            utilidad_data = cursor.fetchone()
            
            pago_query = f"""
                SELECT 
                    v.tipo_pago,
                    COUNT(DISTINCT v.id) as cantidad,
                    COALESCE(SUM(v.total), 0) as monto_total,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE v.total
                        END
                    ), 0) as ingresos_reales,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.saldo_pendiente, 0)
                            ELSE 0
                        END
                    ), 0) as saldo_pendiente_total
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
                GROUP BY v.tipo_pago
            """
            
            cursor.execute(pago_query, params.copy())
            ventas_por_pago = cursor.fetchall()
            
            hoy = datetime.now()
            siete_dias_atras = hoy - timedelta(days=6)
            
            tendencia_query = """
                SELECT 
                    fecha_dia,
                    COUNT(*) as cantidad_ventas,
                    COALESCE(SUM(total), 0) as total_dia
                FROM ventas
                WHERE fecha_dia BETWEEN %s AND %s
                GROUP BY fecha_dia
                ORDER BY fecha_dia
            """
            
            cursor.execute(tendencia_query, (siete_dias_atras.date(), hoy.date()))
            tendencia_ventas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if estadisticas:
                estadisticas = convertir_para_json(estadisticas)
            if utilidad_data:
                utilidad_data = convertir_para_json(utilidad_data)
            if ventas_por_pago:
                ventas_por_pago = convertir_para_json(ventas_por_pago)
            if tendencia_ventas:
                tendencia_ventas = convertir_para_json(tendencia_ventas)
            
            resultado = {
                'success': True,
                'estadisticas': {
                    'total_ventas': int(estadisticas.get('total_ventas', 0)) if estadisticas else 0,
                    'ingresos_totales': float(estadisticas.get('ingresos_totales', 0)) if estadisticas else 0.0,
                    'promedio_venta': float(estadisticas.get('promedio_venta', 0)) if estadisticas else 0.0,
                    'total_unidades': int(estadisticas.get('total_unidades_vendidas', 0)) if estadisticas else 0,
                    'utilidad_total': float(utilidad_data.get('utilidad_total', 0)) if utilidad_data else 0.0,
                    'utilidad_pendiente_creditos': float(utilidad_data.get('utilidad_pendiente_creditos', 0)) if utilidad_data else 0.0
                },
                'ventas_por_pago': ventas_por_pago if ventas_por_pago else [],
                'tendencia_ventas': tendencia_ventas if tendencia_ventas else [],
                'ingresos_por_pago': []
            }
            
            if ventas_por_pago:
                resultado['ingresos_por_pago'] = [
                    {
                        'tipo_pago': item['tipo_pago'],
                        'monto_total': float(item['monto_total']),
                        'ingresos_reales': float(item['ingresos_reales']),
                        'cantidad_ventas': int(item['cantidad']),
                        'saldo_pendiente_total': float(item['saldo_pendiente_total'])
                    }
                    for item in ventas_por_pago
                ]
            
            logger.info(f"Estadísticas obtenidas")
            return resultado
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'estadisticas': {
                    'total_ventas': 0,
                    'ingresos_totales': 0.0,
                    'promedio_venta': 0.0,
                    'total_unidades': 0,
                    'utilidad_total': 0.0,
                    'utilidad_pendiente_creditos': 0.0
                },
                'ventas_por_pago': [],
                'tendencia_ventas': [],
                'ingresos_por_pago': []
            }
    
    @staticmethod
    def obtener_detalle_venta(venta_id):
        """Obtener detalle completo de una venta específica"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            venta_query = """
                SELECT 
                    v.*,
                    c.correo as cliente_correo,
                    c.direccion as cliente_direccion_completa
                FROM ventas v
                LEFT JOIN cliente c ON v.cliente_cedula = c.cedula
                WHERE v.id = %s
            """
            cursor.execute(venta_query, (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                return {
                    'success': False,
                    'error': 'Venta no encontrada'
                }
            
            # Combinar fecha y hora
            if venta.get('fecha_dia') and venta.get('fecha_hora'):
                try:
                    fecha_obj = venta['fecha_dia']
                    hora_str = str(venta['fecha_hora'])
                    if isinstance(fecha_obj, date):
                        hora_partes = hora_str.split(':')
                        hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                        minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                        segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                        fecha_datetime = datetime(
                            fecha_obj.year, fecha_obj.month, fecha_obj.day,
                            hora, minuto, segundo
                        )
                        venta['fecha_completa'] = fecha_datetime
                except Exception:
                    venta['fecha_completa'] = venta['fecha_dia']
            else:
                venta['fecha_completa'] = venta['fecha_dia']
            
            credito_query = """
                SELECT 
                    cr.estado as estado_credito,
                    cr.anticipo as anticipo_credito,
                    cr.abonos_realizados as abonos_credito,
                    cr.saldo_pendiente as saldo_pendiente_credito,
                    cr.deuda_inicial as deuda_inicial_credito,
                    cr.fecha_inicio as fecha_inicio_credito,
                    cr.fecha_vencimiento as fecha_vencimiento_credito,
                    cr.dias_credito as dias_credito_credito
                FROM creditos cr
                WHERE cr.venta_id = %s
                LIMIT 1
            """
            cursor.execute(credito_query, (venta_id,))
            credito = cursor.fetchone()
            
            if credito:
                venta.update(credito)
            
            venta_mixta_query = """
                SELECT 
                    COUNT(*) as total,
                    GROUP_CONCAT(CONCAT(categoria, ' - ', metodo_pago, ': $', FORMAT(monto, 0)) SEPARATOR ' | ') as resumen
                FROM ventas_mixtas 
                WHERE id_venta = %s
            """
            cursor.execute(venta_mixta_query, (venta_id,))
            venta_mixta = cursor.fetchone()
            
            venta['es_mixta'] = venta_mixta['total'] > 0 if venta_mixta else False
            
            if venta['es_mixta']:
                detalle_mixta_query = """
                    SELECT 
                        identificador,
                        categoria,
                        metodo_pago,
                        submetodo,
                        monto,
                        dinero_entregado,
                        cambio,
                        anticipo,
                        dias_credito,
                        cliente_cedula,
                        fecha_registro
                    FROM ventas_mixtas
                    WHERE id_venta = %s
                    ORDER BY categoria, metodo_pago
                """
                cursor.execute(detalle_mixta_query, (venta_id,))
                detalles_mixtos = cursor.fetchall()
                venta['venta_mixta_detalles'] = detalles_mixtos
                
                categorias_mixtas = {}
                for detalle in detalles_mixtos:
                    categoria = detalle['categoria']
                    if categoria not in categorias_mixtas:
                        categorias_mixtas[categoria] = {
                            'total': 0,
                            'metodos': []
                        }
                    categorias_mixtas[categoria]['total'] += float(detalle['monto'])
                    categorias_mixtas[categoria]['metodos'].append({
                        'metodo': detalle['metodo_pago'],
                        'submetodo': detalle['submetodo'],
                        'monto': detalle['monto'],
                        'dinero_entregado': detalle['dinero_entregado'],
                        'cambio': detalle['cambio'],
                        'anticipo': detalle['anticipo'],
                        'dias_credito': detalle['dias_credito']
                    })
                
                venta['categorias_mixtas'] = categorias_mixtas
            
            producto_query = """
                SELECT 
                    dv.id,
                    dv.id_producto,
                    p.nombre,
                    p.categoria,
                    p.presentacion,
                    dv.cantidad_vendida as cantidad,
                    dv.precio_unidad as precio_unitario,
                    dv.precio_neto as subtotal,
                    p.precio_costo,
                    p.precio_venta,
                    (dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida as utilidad_producto
                FROM detalle_venta dv
                JOIN productos p ON dv.id_producto = p.id
                WHERE dv.id_venta = %s
            """
            cursor.execute(producto_query, (venta_id,))
            productos = cursor.fetchall()
            
            utilidad_total = 0
            costo_total = 0
            
            for producto in productos:
                precio_unidad = float(producto.get('precio_unitario', 0))
                precio_costo = float(producto.get('precio_costo', 0))
                cantidad = int(producto.get('cantidad', 0))
                
                utilidad_producto = (precio_unidad - precio_costo) * cantidad
                producto['utilidad_producto'] = utilidad_producto
                
                utilidad_total += utilidad_producto
                costo_total += precio_costo * cantidad
            
            venta['productos'] = productos
            venta['utilidad'] = utilidad_total
            venta['costo_total'] = costo_total
            
            if venta['es_mixta']:
                venta['utilidad_realizada'] = utilidad_total
                venta['utilidad_proyectada'] = 0
                venta['etiqueta_utilidad'] = 'Utilidad Realizada'
            elif venta.get('tipo_pago') == 'CRÉDITO':
                if venta.get('estado_credito') == 'pagado':
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                    venta['etiqueta_utilidad'] = 'Utilidad Realizada'
                else:
                    venta['utilidad_realizada'] = 0
                    venta['utilidad_proyectada'] = utilidad_total
                    venta['etiqueta_utilidad'] = 'Utilidad Proyectada'
            else:
                venta['utilidad_realizada'] = utilidad_total
                venta['utilidad_proyectada'] = 0
                venta['etiqueta_utilidad'] = 'Utilidad Realizada'
            
            cursor.close()
            conn.close()
            
            venta = convertir_para_json(venta)
            
            return {
                'success': True,
                'venta': venta
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo detalle de venta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def obtener_clientes_para_filtro():
        """Obtener lista de clientes para el filtro"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    cedula as id,
                    nombre,
                    telefono,
                    'cliente' as tipo
                FROM cliente
                WHERE nombre IS NOT NULL AND nombre != ''
                ORDER BY nombre
            """
            
            cursor.execute(query)
            usuarios = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            usuarios = convertir_para_json(usuarios)
            
            return {
                'success': True,
                'usuarios': usuarios
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo clientes para filtro: {e}")
            return {
                'success': False,
                'error': str(e),
                'usuarios': []
            }
    
    @staticmethod
    def obtener_productos_para_filtro():
        """Obtener lista de productos para el filtro"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id,
                    nombre,
                    categoria,
                    presentacion,
                    precio_costo,
                    precio_venta
                FROM productos
                WHERE cantidad >= 0
                ORDER BY nombre
            """
            
            cursor.execute(query)
            productos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            productos = convertir_para_json(productos)
            
            return {
                'success': True,
                'productos': productos
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo productos para filtro: {e}")
            return {
                'success': False,
                'error': str(e),
                'productos': []
            }
    
    @staticmethod
    def obtener_ventas_recientes(limit=10):
        """Obtener las ventas más recientes"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    v.id,
                    v.numero_venta,
                    DATE(v.fecha_dia) as fecha_dia,
                    TIME(v.fecha_hora) as fecha_hora,
                    v.nombre_cliente,
                    v.tipo_pago,
                    v.total
                FROM ventas v
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            ventas = cursor.fetchall()
            
            for venta in ventas:
                if venta.get('fecha_dia') and venta.get('fecha_hora'):
                    try:
                        fecha_obj = venta['fecha_dia']
                        hora_str = str(venta['fecha_hora'])
                        if isinstance(fecha_obj, date):
                            hora_partes = hora_str.split(':')
                            hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                            minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                            segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                            fecha_datetime = datetime(
                                fecha_obj.year, fecha_obj.month, fecha_obj.day,
                                hora, minuto, segundo
                            )
                            venta['fecha_completa'] = fecha_datetime
                    except Exception:
                        venta['fecha_completa'] = venta['fecha_dia']
                else:
                    venta['fecha_completa'] = venta['fecha_dia']
            
            cursor.close()
            conn.close()
            
            ventas = convertir_para_json(ventas)
            
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ventas recientes: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }
        
    @staticmethod
    def obtener_estadisticas_financieras(fecha_inicio=None, fecha_fin=None):
        """Obtener estadísticas financieras según la nueva lógica del dashboard"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE 1=1"
            params = []
            
            if fecha_inicio and fecha_fin:
                where_clause += " AND v.fecha_dia BETWEEN %s AND %s"
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_clause += " AND v.fecha_dia >= %s"
                params.append(fecha_inicio)
            elif fecha_fin:
                where_clause += " AND v.fecha_dia <= %s"
                params.append(fecha_fin)
            
            ingresos_cobrados_query = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago != 'CRÉDITO' THEN v.total
                            ELSE 0
                        END
                    ), 0) as ventas_contado,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.anticipo, 0)
                            ELSE 0
                        END
                    ), 0) as anticipos_cobrados,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.abonos_realizados, 0)
                            ELSE 0
                        END
                    ), 0) as abonos_cobrados
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
            """
            
            cursor.execute(ingresos_cobrados_query, params.copy())
            ingresos_data = cursor.fetchone()
            
            ingresos_cobrados = (ingresos_data.get('ventas_contado', 0) + 
                               ingresos_data.get('anticipos_cobrados', 0) + 
                               ingresos_data.get('abonos_cobrados', 0))
            
            ventas_credito_query = f"""
                SELECT 
                    COUNT(DISTINCT v.id) as total_creditos,
                    COALESCE(SUM(v.total), 0) as total_credito_vendido,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE 0
                        END
                    ), 0) as credito_ya_pagado,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.saldo_pendiente, 0)
                            ELSE 0
                        END
                    ), 0) as credito_faltante
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
                AND v.tipo_pago = 'CRÉDITO'
            """
            
            cursor.execute(ventas_credito_query, params.copy())
            credito_data = cursor.fetchone()
            
            saldo_por_cobrar = credito_data.get('credito_faltante', 0) if credito_data else 0
            
            creditos_estado_query = f"""
                SELECT 
                    COUNT(DISTINCT c.id) as creditos_pendientes_count,
                    COALESCE(SUM(
                        CASE 
                            WHEN c.estado = 'vencido' THEN c.saldo_pendiente
                            ELSE 0
                        END
                    ), 0) as creditos_vencidos,
                    COALESCE(SUM(
                        CASE 
                            WHEN c.estado = 'pendiente' THEN c.saldo_pendiente
                            ELSE 0
                        END
                    ), 0) as creditos_en_fecha
                FROM creditos c
                JOIN ventas v ON c.venta_id = v.id
                {where_clause}
                AND c.estado IN ('pendiente', 'vencido')
            """
            
            cursor.execute(creditos_estado_query, params.copy())
            creditos_estado_data = cursor.fetchone()
            
            utilidad_realizada_query = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago != 'CRÉDITO' THEN 
                                (SELECT SUM((dv2.precio_unidad - p2.precio_costo) * dv2.cantidad_vendida)
                                 FROM detalle_venta dv2
                                 JOIN productos p2 ON dv2.id_producto = p2.id
                                 WHERE dv2.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as utilidad_contado,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado = 'pagado' THEN 
                                (SELECT SUM((dv2.precio_unidad - p2.precio_costo) * dv2.cantidad_vendida)
                                 FROM detalle_venta dv2
                                 JOIN productos p2 ON dv2.id_producto = p2.id
                                 WHERE dv2.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as utilidad_creditos_pagados
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
            """
            
            cursor.execute(utilidad_realizada_query, params.copy())
            utilidad_data = cursor.fetchone()
            
            utilidad_realizada = (utilidad_data.get('utilidad_contado', 0) + 
                                utilidad_data.get('utilidad_creditos_pagados', 0))
            
            utilidad_proyectada_query = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado != 'pagado' THEN v.total
                            ELSE 0
                        END
                    ), 0) as valor_ventas_pendientes,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado != 'pagado' THEN 
                                (SELECT SUM(p2.precio_costo * dv2.cantidad_vendida)
                                 FROM detalle_venta dv2
                                 JOIN productos p2 ON dv2.id_producto = p2.id
                                 WHERE dv2.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as costo_ventas_pendientes
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                {where_clause}
            """
            
            cursor.execute(utilidad_proyectada_query, params.copy())
            proyectada_data = cursor.fetchone()
            
            valor_ventas_pendientes = proyectada_data.get('valor_ventas_pendientes', 0)
            costo_ventas_pendientes = proyectada_data.get('costo_ventas_pendientes', 0)
            utilidad_proyectada = valor_ventas_pendientes - costo_ventas_pendientes
            
            ventas_totales_query = f"""
                SELECT COUNT(DISTINCT v.id) as total_ventas
                FROM ventas v
                {where_clause}
            """
            
            cursor.execute(ventas_totales_query, params.copy())
            ventas_totales_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            estadisticas = {
                'success': True,
                'estadisticas': {
                    'ingresos_cobrados': float(ingresos_cobrados),
                    'ventas_contado': float(ingresos_data.get('ventas_contado', 0)) if ingresos_data else 0.0,
                    'anticipos_cobrados': float(ingresos_data.get('anticipos_cobrados', 0)) if ingresos_data else 0.0,
                    'abonos_cobrados': float(ingresos_data.get('abonos_cobrados', 0)) if ingresos_data else 0.0,
                    'ventas_credito_pendientes': float(credito_data.get('credito_faltante', 0)) if credito_data else 0.0,
                    'total_credito_vendido': float(credito_data.get('total_credito_vendido', 0)) if credito_data else 0.0,
                    'credito_ya_pagado': float(credito_data.get('credito_ya_pagado', 0)) if credito_data else 0.0,
                    'credito_faltante': float(credito_data.get('credito_faltante', 0)) if credito_data else 0.0,
                    'saldo_por_cobrar': float(saldo_por_cobrar),
                    'creditos_pendientes_count': int(creditos_estado_data.get('creditos_pendientes_count', 0)) if creditos_estado_data else 0,
                    'creditos_vencidos': float(creditos_estado_data.get('creditos_vencidos', 0)) if creditos_estado_data else 0.0,
                    'creditos_en_fecha': float(creditos_estado_data.get('creditos_en_fecha', 0)) if creditos_estado_data else 0.0,
                    'utilidad_realizada': float(utilidad_realizada),
                    'utilidad_contado': float(utilidad_data.get('utilidad_contado', 0)) if utilidad_data else 0.0,
                    'utilidad_creditos_pagados': float(utilidad_data.get('utilidad_creditos_pagados', 0)) if utilidad_data else 0.0,
                    'utilidad_proyectada': float(utilidad_proyectada),
                    'valor_ventas_pendientes': float(valor_ventas_pendientes),
                    'costo_ventas_pendientes': float(costo_ventas_pendientes),
                    'total_ventas': int(ventas_totales_data.get('total_ventas', 0)) if ventas_totales_data else 0
                }
            }
            
            estadisticas = convertir_para_json(estadisticas)
            
            logger.info("Estadísticas financieras obtenidas exitosamente")
            return estadisticas
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas financieras: {e}")
            return {
                'success': False,
                'error': str(e),
                'estadisticas': {
                    'ingresos_cobrados': 0.0,
                    'ventas_contado': 0.0,
                    'anticipos_cobrados': 0.0,
                    'abonos_cobrados': 0.0,
                    'ventas_credito_pendientes': 0.0,
                    'total_credito_vendido': 0.0,
                    'credito_ya_pagado': 0.0,
                    'credito_faltante': 0.0,
                    'saldo_por_cobrar': 0.0,
                    'creditos_pendientes_count': 0,
                    'creditos_vencidos': 0.0,
                    'creditos_en_fecha': 0.0,
                    'utilidad_realizada': 0.0,
                    'utilidad_contado': 0.0,
                    'utilidad_creditos_pagados': 0.0,
                    'utilidad_proyectada': 0.0,
                    'valor_ventas_pendientes': 0.0,
                    'costo_ventas_pendientes': 0.0,
                    'total_ventas': 0
                }
            }
    
    @staticmethod
    def obtener_estadisticas_financieras_periodo_rapido(periodo):
        """Obtener estadísticas financieras para períodos rápidos"""
        try:
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
            
            return HistorialVentaModel.obtener_estadisticas_financieras(
                fecha_inicio=str(fecha_inicio),
                fecha_fin=str(fecha_fin)
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas financieras para período rápido: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def eliminar_venta_completa(venta_id, recuperar_productos=False):
        """Eliminar una venta con opción de recuperar productos AL INVENTARIO"""
        try:
            conn = db.get_connection()
            
            logger.info(f"Iniciando transacción para eliminar venta {venta_id}")
            conn.start_transaction()
            
            try:
                cursor = conn.cursor(dictionary=True)
                productos_recuperados = []
                
                check_query = """
                    SELECT 
                        v.id, 
                        v.tipo_pago, 
                        v.numero_venta, 
                        v.fecha_dia,
                        DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados,
                        c.id as credito_id
                    FROM ventas v
                    LEFT JOIN creditos c ON v.id = c.venta_id
                    WHERE v.id = %s
                """
                cursor.execute(check_query, (venta_id,))
                venta = cursor.fetchone()
                
                if not venta:
                    cursor.close()
                    conn.close()
                    return {
                        'success': False,
                        'error': f'Venta ID {venta_id} no encontrada'
                    }
                
                if recuperar_productos and venta.get('dias_pasados', 0) > 7:
                    cursor.close()
                    conn.close()
                    return {
                        'success': False,
                        'error': f'No se puede recuperar productos de una venta de hace más de 7 días',
                        'dias_pasados': venta['dias_pasados']
                    }
                
                if recuperar_productos:
                    productos_query = """
                        SELECT 
                            dv.id_producto,
                            dv.cantidad_vendida,
                            p.nombre,
                            p.cantidad as stock_actual,
                            p.categoria,
                            p.precio_costo,
                            p.precio_venta
                        FROM detalle_venta dv
                        JOIN productos p ON dv.id_producto = p.id
                        WHERE dv.id_venta = %s
                    """
                    cursor.execute(productos_query, (venta_id,))
                    productos = cursor.fetchall()
                    
                    logger.info(f"Recuperando {len(productos)} productos para venta {venta_id}")
                    
                    for producto in productos:
                        producto_id = producto['id_producto']
                        cantidad_recuperar = producto['cantidad_vendida']
                        nombre_producto = producto['nombre']
                        
                        update_stock_query = """
                            UPDATE productos 
                            SET cantidad = cantidad + %s
                            WHERE id = %s
                        """
                        cursor.execute(update_stock_query, (cantidad_recuperar, producto_id))
                        
                        if cursor.rowcount > 0:
                            cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (producto_id,))
                            stock_actualizado = cursor.fetchone()
                            nuevo_stock = stock_actualizado['cantidad'] if stock_actualizado else 'Desconocido'
                            
                            productos_recuperados.append({
                                'producto_id': producto_id,
                                'nombre': nombre_producto,
                                'categoria': producto['categoria'],
                                'cantidad_recuperada': cantidad_recuperar,
                                'stock_anterior': producto['stock_actual'],
                                'stock_nuevo': nuevo_stock,
                                'precio_costo': float(producto['precio_costo']) if producto['precio_costo'] else 0,
                                'precio_venta': float(producto['precio_venta']) if producto['precio_venta'] else 0,
                                'actualizado': True
                            })
                            
                            logger.info(f"✅ Producto recuperado: {nombre_producto} (ID: {producto_id})")
                            logger.info(f"   +{cantidad_recuperar} unidades, Stock: {producto['stock_actual']} → {nuevo_stock}")
                        else:
                            productos_recuperados.append({
                                'producto_id': producto_id,
                                'nombre': nombre_producto,
                                'cantidad_recuperada': cantidad_recuperar,
                                'error': 'No se pudo actualizar el stock - Producto no encontrado',
                                'actualizado': False
                            })
                            logger.error(f"❌ Error recuperando producto {producto_id}: No se pudo actualizar")
                
                detalles_eliminados = 0
                ventas_mixtas_eliminadas = 0
                credito_eliminado = False
                venta_eliminada = 0
                
                cursor.execute("DELETE FROM detalle_venta WHERE id_venta = %s", (venta_id,))
                detalles_eliminados = cursor.rowcount
                logger.info(f"Detalles de venta eliminados: {detalles_eliminados}")
                
                cursor.execute("DELETE FROM ventas_mixtas WHERE id_venta = %s", (venta_id,))
                ventas_mixtas_eliminadas = cursor.rowcount
                if ventas_mixtas_eliminadas > 0:
                    logger.info(f"Ventas mixtas eliminadas: {ventas_mixtas_eliminadas}")
                
                if venta['credito_id']:
                    cursor.execute("DELETE FROM creditos WHERE id = %s", (venta['credito_id'],))
                    if cursor.rowcount > 0:
                        credito_eliminado = True
                        logger.info(f"Crédito ID {venta['credito_id']} eliminado para venta {venta_id}")
                
                cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
                venta_eliminada = cursor.rowcount
                
                if venta_eliminada == 0:
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return {
                        'success': False,
                        'error': f'No se pudo eliminar la venta {venta_id}'
                    }
                
                conn.commit()
                logger.info(f"✅ Transacción COMPLETADA para venta {venta_id}")
                logger.info(f"   - Productos recuperados: {len([p for p in productos_recuperados if p.get('actualizado', False)])}")
                logger.info(f"   - Detalles eliminados: {detalles_eliminados}")
                logger.info(f"   - Venta eliminada: {venta_eliminada}")
                
                cursor.close()
                conn.close()
                
                mensaje = f'Venta #{venta["numero_venta"]} eliminada exitosamente'
                
                if recuperar_productos and productos_recuperados:
                    productos_exitosos = [p for p in productos_recuperados if p.get('actualizado', False)]
                    if productos_exitosos:
                        productos_texto = ', '.join([f"{p['nombre']} (+{p['cantidad_recuperada']})" for p in productos_exitosos])
                        mensaje += f'. {len(productos_exitosos)} producto(s) recuperado(s) al inventario: {productos_texto}'
                
                return {
                    'success': True,
                    'message': mensaje,
                    'detalles': {
                        'venta_id': venta_id,
                        'numero_venta': venta['numero_venta'],
                        'detalles_eliminados': detalles_eliminados,
                        'credito_eliminado': credito_eliminado,
                        'ventas_mixtas_eliminadas': ventas_mixtas_eliminadas,
                        'es_credito': venta['tipo_pago'] == 'CRÉDITO',
                        'venta_eliminada': venta_eliminada,
                        'productos_recuperados': productos_recuperados,
                        'recuperar_productos': recuperar_productos,
                        'recuperados_exitosos': len([p for p in productos_recuperados if p.get('actualizado', False)]),
                        'recuperados_fallidos': len([p for p in productos_recuperados if not p.get('actualizado', True)])
                    }
                }
                
            except Exception as e:
                conn.rollback()
                cursor.close()
                conn.close()
                
                logger.error(f"❌ ERROR en transacción al eliminar venta {venta_id}: {e}", exc_info=True)
                return {
                    'success': False,
                    'error': f'Error al eliminar la venta: {str(e)}',
                    'detalles': f'Venta ID: {venta_id}'
                }
                
        except Exception as e:
            logger.error(f"❌ Error eliminando venta completa {venta_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Error al eliminar la venta: {str(e)}',
                'detalles': f'Venta ID: {venta_id}'
            }    
    
    @staticmethod
    def eliminar_ventas_multiples(ventas_ids, recuperar_productos=False):
        """Eliminar múltiples ventas en una sola transacción con opción de recuperar productos"""
        try:
            conn = db.get_connection()
            
            logger.info(f"Iniciando transacción para eliminar {len(ventas_ids)} ventas")
            conn.start_transaction()
            
            try:
                cursor = conn.cursor(dictionary=True)
                
                resultados = {
                    'eliminadas': 0,
                    'detalles_eliminados': 0,
                    'creditos_eliminados': 0,
                    'ventas_mixtas_eliminadas': 0,
                    'productos_recuperados': [],
                    'errores': []
                }
                
                for venta_id in ventas_ids:
                    try:
                        cursor.execute("""
                            SELECT 
                                v.id, 
                                v.tipo_pago, 
                                v.numero_venta, 
                                v.fecha_dia,
                                DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados,
                                c.id as credito_id
                            FROM ventas v
                            LEFT JOIN creditos c ON v.id = c.venta_id
                            WHERE v.id = %s
                        """, (venta_id,))
                        venta = cursor.fetchone()
                        
                        if not venta:
                            resultados['errores'].append(f'Venta {venta_id} no encontrada')
                            continue
                        
                        if recuperar_productos and venta.get('dias_pasados', 0) > 7:
                            resultados['errores'].append(f'Venta {venta_id}: No se puede recuperar productos de una venta de hace más de 7 días')
                            continue
                        
                        if recuperar_productos:
                            cursor.execute("""
                                SELECT 
                                    dv.id_producto, 
                                    dv.cantidad_vendida, 
                                    p.nombre, 
                                    p.cantidad as stock_actual,
                                    p.categoria,
                                    p.precio_costo,
                                    p.precio_venta
                                FROM detalle_venta dv
                                JOIN productos p ON dv.id_producto = p.id
                                WHERE dv.id_venta = %s
                            """, (venta_id,))
                            productos = cursor.fetchall()
                            
                            for producto in productos:
                                cursor.execute("""
                                    UPDATE productos 
                                    SET cantidad = cantidad + %s 
                                    WHERE id = %s
                                """, (producto['cantidad_vendida'], producto['id_producto']))
                                
                                if cursor.rowcount > 0:
                                    cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (producto['id_producto'],))
                                    stock_actualizado = cursor.fetchone()
                                    nuevo_stock = stock_actualizado['cantidad'] if stock_actualizado else producto['stock_actual'] + producto['cantidad_vendida']
                                    
                                    resultados['productos_recuperados'].append({
                                        'venta_id': venta_id,
                                        'producto_id': producto['id_producto'],
                                        'nombre': producto['nombre'],
                                        'categoria': producto['categoria'],
                                        'cantidad': producto['cantidad_vendida'],
                                        'stock_anterior': producto['stock_actual'],
                                        'stock_nuevo': nuevo_stock,
                                        'precio_costo': float(producto['precio_costo']) if producto['precio_costo'] else 0,
                                        'precio_venta': float(producto['precio_venta']) if producto['precio_venta'] else 0,
                                        'actualizado': True
                                    })
                                    
                                    logger.info(f"✅ Producto {producto['nombre']} (ID: {producto['id_producto']}) recuperado de venta {venta_id}")
                                    logger.info(f"   +{producto['cantidad_vendida']} unidades, Stock: {producto['stock_actual']} → {nuevo_stock}")
                                else:
                                    resultados['productos_recuperados'].append({
                                        'venta_id': venta_id,
                                        'producto_id': producto['id_producto'],
                                        'nombre': producto['nombre'],
                                        'cantidad': producto['cantidad_vendida'],
                                        'error': 'No se pudo actualizar el stock',
                                        'actualizado': False
                                    })
                                    logger.error(f"❌ Error recuperando producto {producto['id_producto']} de venta {venta_id}")
                        
                        cursor.execute("DELETE FROM detalle_venta WHERE id_venta = %s", (venta_id,))
                        resultados['detalles_eliminados'] += cursor.rowcount
                        
                        cursor.execute("DELETE FROM ventas_mixtas WHERE id_venta = %s", (venta_id,))
                        if cursor.rowcount > 0:
                            resultados['ventas_mixtas_eliminadas'] += cursor.rowcount
                        
                        if venta['credito_id']:
                            cursor.execute("DELETE FROM creditos WHERE id = %s", (venta['credito_id'],))
                            if cursor.rowcount > 0:
                                resultados['creditos_eliminados'] += 1
                        
                        cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
                        if cursor.rowcount > 0:
                            resultados['eliminadas'] += 1
                            logger.info(f"✅ Venta {venta_id} eliminada exitosamente")
                        
                    except Exception as e:
                        error_msg = str(e)
                        resultados['errores'].append(f'Error eliminando venta {venta_id}: {error_msg}')
                        logger.error(f"❌ Error eliminando venta {venta_id}: {error_msg}")
                        continue
                
                conn.commit()
                logger.info(f"✅ Transacción MÚLTIPLE COMPLETADA")
                logger.info(f"   - Ventas eliminadas: {resultados['eliminadas']}/{len(ventas_ids)}")
                logger.info(f"   - Productos recuperados: {len([p for p in resultados['productos_recuperados'] if p.get('actualizado', False)])}")
                logger.info(f"   - Detalles eliminados: {resultados['detalles_eliminados']}")
                
                cursor.close()
                conn.close()
                
                productos_exitosos = [p for p in resultados['productos_recuperados'] if p.get('actualizado', False)]
                
                if resultados['errores']:
                    return {
                        'success': True,
                        'eliminadas': resultados['eliminadas'],
                        'detalles': {
                            'detalles_eliminados': resultados['detalles_eliminados'],
                            'creditos_eliminados': resultados['creditos_eliminados'],
                            'ventas_mixtas_eliminadas': resultados['ventas_mixtas_eliminadas'],
                            'productos_recuperados': resultados['productos_recuperados'],
                            'productos_exitosos': productos_exitosos,
                            'productos_fallidos': [p for p in resultados['productos_recuperados'] if not p.get('actualizado', False)],
                            'advertencias': resultados['errores']
                        },
                        'recuperar_productos': recuperar_productos,
                        'message': f'Se eliminaron {resultados["eliminadas"]} ventas con algunas advertencias'
                    }
                else:
                    mensaje = f'{resultados["eliminadas"]} ventas eliminadas exitosamente'
                    
                    if recuperar_productos and productos_exitosos:
                        productos_por_tipo = {}
                        for producto in productos_exitosos:
                            key = producto['nombre']
                            if key not in productos_por_tipo:
                                productos_por_tipo[key] = {
                                    'nombre': producto['nombre'],
                                    'categoria': producto['categoria'],
                                    'cantidad_total': 0,
                                    'stock_anterior': producto['stock_anterior'],
                                    'stock_nuevo': producto['stock_nuevo']
                                }
                            productos_por_tipo[key]['cantidad_total'] += producto['cantidad']
                        
                        resumen_productos = ', '.join([
                            f"{data['nombre']} (+{data['cantidad_total']})"
                            for data in productos_por_tipo.values()
                        ])
                        
                        mensaje += f'. {len(productos_exitosos)} producto(s) recuperado(s): {resumen_productos}'
                    
                    return {
                        'success': True,
                        'eliminadas': resultados['eliminadas'],
                        'detalles': {
                            'detalles_eliminados': resultados['detalles_eliminados'],
                            'creditos_eliminados': resultados['creditos_eliminados'],
                            'ventas_mixtas_eliminadas': resultados['ventas_mixtas_eliminadas'],
                            'productos_recuperados': resultados['productos_recuperados'],
                            'productos_exitosos': productos_exitosos,
                            'productos_fallidos': [p for p in resultados['productos_recuperados'] if not p.get('actualizado', False)]
                        },
                        'recuperar_productos': recuperar_productos,
                        'message': mensaje
                    }
                        
            except Exception as e:
                conn.rollback()
                cursor.close()
                conn.close()
                
                logger.error(f"❌ ERROR GENERAL en eliminación múltiple: {e}", exc_info=True)
                return {
                    'success': False,
                    'error': f'Error general en eliminación múltiple: {str(e)}',
                    'eliminadas': 0
                }
                    
        except Exception as e:
            logger.error(f"❌ Error en eliminación múltiple: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Error en eliminación múltiple: {str(e)}',
                'eliminadas': 0
            }
            
    @staticmethod
    def verificar_venta_para_eliminar(venta_id):
        """Verificar información básica de una venta antes de eliminarla"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    v.id,
                    v.numero_venta,
                    v.tipo_pago,
                    v.fecha_dia,
                    v.nombre_cliente,
                    v.total,
                    DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados,
                    COUNT(DISTINCT dv.id) as productos_count,
                    COALESCE(MAX(c.id), 0) as credito_id,
                    COUNT(DISTINCT c.id) as creditos_count,
                    COUNT(DISTINCT vm.id) as ventas_mixtas_count
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                LEFT JOIN creditos c ON v.id = c.venta_id
                LEFT JOIN ventas_mixtas vm ON v.id = vm.id_venta
                WHERE v.id = %s
                GROUP BY v.id
            """
            
            cursor.execute(query, (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'error': 'Venta no encontrada'
                }
            
            cursor.close()
            conn.close()
            
            venta = convertir_para_json(venta)
            
            puede_eliminar = True
            advertencias = []
            
            if venta.get('ventas_mixtas_count', 0) > 0:
                advertencias.append(f"Esta venta es MIXTA con {venta['ventas_mixtas_count']} métodos de pago")
            
            puede_recuperar_productos = venta.get('dias_pasados', 0) <= 7
            
            info_venta = {
                'id': venta_id,
                'numero_venta': venta.get('numero_venta'),
                'tipo_pago': venta.get('tipo_pago'),
                'fecha': venta.get('fecha_dia'),
                'dias_pasados': venta.get('dias_pasados', 0),
                'cliente': venta.get('nombre_cliente', 'CLIENTE FINAL'),
                'total': float(venta.get('total', 0)),
                'productos_count': venta.get('productos_count', 0),
                'es_credito': venta.get('tipo_pago') == 'CRÉDITO',
                'es_mixta': venta.get('ventas_mixtas_count', 0) > 0,
                'ventas_mixtas_count': venta.get('ventas_mixtas_count', 0),
                'tiene_credito': venta.get('credito_id') is not None,
                'creditos_count': venta.get('creditos_count', 0),
                'puede_recuperar_productos': puede_recuperar_productos
            }
            
            return {
                'success': True,
                'puede_eliminar': puede_eliminar,
                'puede_recuperar_productos': puede_recuperar_productos,
                'venta': info_venta,
                'advertencias': advertencias,
                'mensaje': 'Esta acción eliminará permanentemente la venta y todos sus registros relacionados.'
            }
            
        except Exception as e:
            logger.error(f"Error verificando venta {venta_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'puede_eliminar': False
            }

# Instancia global del modelo
model = HistorialVentaModel()