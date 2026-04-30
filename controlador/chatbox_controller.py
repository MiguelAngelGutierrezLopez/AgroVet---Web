from flask import Blueprint, request, jsonify, session
from database import Database
import json
import logging
import traceback
from datetime import date, timedelta

logger = logging.getLogger(__name__)

chatbox_bp = Blueprint('chatbox', __name__, url_prefix='/api/chat')

def obtener_usuario_actual():
    """Obtener el ID del usuario logueado"""
    return 1


@chatbox_bp.route('/send', methods=['POST'])
def enviar_mensaje():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'mensaje': 'No se recibieron datos',
                'botones': [{'label': 'Volver al menu', 'payload': 'menu_principal'}],
                'solicitar_texto': False
            }), 400
            
        payload = data.get('payload', 'menu_principal')
        usuario_id = obtener_usuario_actual()
        db = Database()
        
        sesion = db.fetch_one(
            "SELECT id, estado_actual FROM chat_sesiones WHERE usuario_id = %s ORDER BY id DESC LIMIT 1",
            (usuario_id,)
        )
        
        if not sesion:
            session_id = db.execute(
                "INSERT INTO chat_sesiones (usuario_id, session_token, estado_actual) VALUES (%s, %s, 'menu_principal')",
                (usuario_id, f"chat_{usuario_id}_{__import__('time').time()}"),
                return_lastrowid=True
            )
            estado_actual = 'menu_principal'
        else:
            session_id = sesion['id']
            estado_actual = sesion['estado_actual']
        
        respuesta = procesar_payload(payload, estado_actual, db, usuario_id)
        
        db.execute(
            """INSERT INTO chat_logs (session_id, usuario_payload, bot_respuesta, botones_json) 
               VALUES (%s, %s, %s, %s)""",
            (session_id, payload, respuesta.get('mensaje', ''), json.dumps(respuesta.get('botones', [])))
        )
        
        nuevo_estado = respuesta.get('nuevo_estado', estado_actual)
        db.execute(
            "UPDATE chat_sesiones SET estado_actual = %s, ultima_interaccion = NOW() WHERE id = %s",
            (nuevo_estado, session_id)
        )
        
        return jsonify({
            'mensaje': respuesta.get('mensaje', 'Error en la respuesta'),
            'botones': respuesta.get('botones', [{'label': 'Menu principal', 'payload': 'menu_principal'}]),
            'solicitar_texto': respuesta.get('solicitar_texto', False),
            'texto_instruccion': respuesta.get('texto_instruccion', '')
        })
        
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'mensaje': f'Error: {str(e)}',
            'botones': [{'label': 'Volver al menu', 'payload': 'menu_principal'}],
            'solicitar_texto': False
        }), 500


def procesar_payload(payload, estado_actual, db, usuario_id):
    
    # ========== MENU PRINCIPAL ==========
    if payload == 'menu_principal':
        return {
            'mensaje': 'SISTEMA DE GESTION AGROVET\n\nSeleccione una opcion:',
            'botones': [
                {'label': 'Productos', 'payload': 'menu_productos'},
                {'label': 'Clientes', 'payload': 'menu_clientes'},
                {'label': 'Ventas', 'payload': 'menu_ventas'},
                {'label': 'Creditos', 'payload': 'menu_creditos'},
                {'label': 'Reporte Caja', 'payload': 'reporte_caja'},
                {'label': 'Alertas', 'payload': 'alertas'}
            ],
            'nuevo_estado': 'menu_principal'
        }
    
    # ========== PRODUCTOS ==========
    if payload == 'menu_productos':
        return {
            'mensaje': 'MODULO DE PRODUCTOS\n\nSeleccione una opcion:',
            'botones': [
                {'label': 'Buscar por nombre', 'payload': 'buscar_producto_nombre'},
                {'label': 'Buscar por categoria', 'payload': 'buscar_producto_categoria'},
                {'label': 'Ver stock bajo', 'payload': 'ver_stock_bajo'},
                {'label': 'Listar productos', 'payload': 'listar_todos_productos'},
                {'label': 'Volver', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_productos',
            'solicitar_texto': False
        }
    
    if payload == 'buscar_producto_nombre':
        return {
            'mensaje': 'BUSCAR PRODUCTO POR NOMBRE\n\nEscriba el nombre del producto:',
            'botones': [{'label': 'Cancelar', 'payload': 'menu_productos'}],
            'nuevo_estado': 'buscando_producto_por_nombre',
            'solicitar_texto': True,
            'texto_instruccion': 'Nombre del producto:'
        }
    
    if payload == 'buscar_producto_categoria':
        try:
            categorias = db.fetch_all("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
            botones_cat = []
            if categorias and len(categorias) > 0:
                for cat in categorias:
                    if cat and cat.get('categoria'):
                        botones_cat.append({'label': f'{cat["categoria"]}', 'payload': f'categoria_{cat["categoria"]}'})
            botones_cat.append({'label': 'Volver', 'payload': 'menu_productos'})
        except Exception as e:
            logger.error(f"Error obteniendo categorias: {e}")
            botones_cat = [{'label': 'Volver', 'payload': 'menu_productos'}]
        
        return {
            'mensaje': 'BUSCAR POR CATEGORIA\n\nSeleccione o escriba una categoria:',
            'botones': botones_cat,
            'nuevo_estado': 'menu_productos',
            'solicitar_texto': True,
            'texto_instruccion': 'Escriba la categoria:'
        }
    
    if payload == 'ver_stock_bajo':
        try:
            productos = db.fetch_all(
                """SELECT p.nombre, p.categoria, p.cantidad,
                          COALESCE(pr.nombre_proveedor, 'SIN PROVEEDOR') as proveedor_nombre,
                          COALESCE(pr.telefono, 'N/D') as proveedor_telefono
                   FROM productos p
                   LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                   WHERE p.cantidad < 5
                   ORDER BY p.cantidad ASC
                   LIMIT 30"""
            )
            
            if productos and len(productos) > 0:
                texto = "PRODUCTOS CON STOCK BAJO (menos de 5 unidades)\n"
                texto += "-" * 50 + "\n\n"
                texto += "{:<30} {:<15} {:<10} {:<20}\n".format("PRODUCTO", "CATEGORIA", "STOCK", "PROVEEDOR")
                texto += "-" * 75 + "\n"
                for p in productos:
                    nombre = p.get('nombre', 'N/A')[:28]
                    categoria = p.get('categoria', 'N/A')[:13]
                    cantidad = p.get('cantidad', 0)
                    proveedor = p.get('proveedor_nombre', 'SIN PROVEEDOR')[:18]
                    texto += "{:<30} {:<15} {:<10} {:<20}\n".format(nombre, categoria, str(cantidad), proveedor)
                texto += "\n" + "-" * 50
            else:
                texto = "No hay productos con stock bajo. Todos los productos tienen 5 o mas unidades."
        except Exception as e:
            logger.error(f"Error en ver_stock_bajo: {e}")
            texto = "Error al consultar productos con stock bajo."
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Volver a productos', 'payload': 'menu_productos'},
                {'label': 'Menu principal', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_productos'
        }
    
    if payload == 'listar_todos_productos':
        try:
            productos = db.fetch_all(
                """SELECT p.nombre, p.categoria, p.cantidad, p.precio_venta,
                          COALESCE(pr.nombre_proveedor, 'SIN PROVEEDOR') as proveedor_nombre
                   FROM productos p
                   LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                   ORDER BY p.nombre
                   LIMIT 50"""
            )
            
            if productos and len(productos) > 0:
                texto = "LISTA DE PRODUCTOS\n"
                texto += "-" * 70 + "\n\n"
                texto += "{:<35} {:<15} {:<8} {:<12} {:<20}\n".format("PRODUCTO", "CATEGORIA", "STOCK", "PRECIO", "PROVEEDOR")
                texto += "-" * 90 + "\n"
                for p in productos:
                    nombre = p.get('nombre', 'N/A')[:33]
                    categoria = p.get('categoria', 'N/A')[:13]
                    cantidad = p.get('cantidad', 0)
                    precio = float(p.get('precio_venta', 0))
                    proveedor = p.get('proveedor_nombre', 'SIN PROVEEDOR')[:18]
                    texto += "{:<35} {:<15} {:<8} ${:<11,.0f} {:<20}\n".format(nombre, categoria, str(cantidad), precio, proveedor)
                texto += "\n" + "-" * 70
                if len(productos) == 50:
                    texto += "\n\n*Mostrando primeros 50 productos. Use la busqueda para mas especificos.*"
            else:
                texto = "No hay productos registrados."
        except Exception as e:
            logger.error(f"Error en listar_todos_productos: {e}")
            texto = "Error al consultar productos."
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Buscar producto', 'payload': 'buscar_producto_nombre'},
                {'label': 'Buscar por categoria', 'payload': 'buscar_producto_categoria'},
                {'label': 'Volver', 'payload': 'menu_productos'}
            ],
            'nuevo_estado': 'menu_productos'
        }
    
    # Busqueda por nombre (texto libre)
    if estado_actual == 'buscando_producto_por_nombre' and not payload.startswith('menu_'):
        nombre_busqueda = payload
        try:
            productos = db.fetch_all(
                """SELECT p.*, 
                          COALESCE(pr.nombre_proveedor, 'SIN PROVEEDOR') as proveedor_nombre,
                          COALESCE(pr.telefono, 'N/D') as proveedor_telefono,
                          COALESCE(pr.correo, 'N/D') as proveedor_correo
                   FROM productos p
                   LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                   WHERE p.nombre LIKE %s
                   ORDER BY p.nombre
                   LIMIT 20""",
                (f"%{nombre_busqueda}%",)
            )
            
            if productos and len(productos) > 0:
                texto = f"RESULTADOS PARA '{nombre_busqueda}'\n"
                texto += "=" * 60 + "\n\n"
                for p in productos:
                    nombre = p.get('nombre', 'N/A')
                    categoria = p.get('categoria', 'N/A')
                    precio_venta = float(p.get('precio_venta', 0))
                    precio_costo = float(p.get('precio_costo', 0))
                    ganancia = precio_venta - precio_costo
                    ganancia_porcentaje = (ganancia / precio_costo * 100) if precio_costo > 0 else 0
                    cantidad = p.get('cantidad', 0)
                    presentacion = p.get('presentacion', 'N/A')
                    proveedor_nombre = p.get('proveedor_nombre', 'SIN PROVEEDOR')
                    proveedor_telefono = p.get('proveedor_telefono', 'N/D')
                    proveedor_correo = p.get('proveedor_correo', 'N/D')
                    descripcion = p.get('descripcion', 'Sin descripcion')
                    if descripcion and len(descripcion) > 80:
                        descripcion = descripcion[:80] + "..."
                    
                    texto += f"PRODUCTO: {nombre}\n"
                    texto += f"  Categoria: {categoria}\n"
                    texto += f"  Precio Venta: ${precio_venta:,.0f}\n"
                    texto += f"  Precio Costo: ${precio_costo:,.0f}\n"
                    
                    if ganancia >= 0:
                        texto += f"  Ganancia: ${ganancia:,.0f} (+{ganancia_porcentaje:.1f}%)\n"
                    else:
                        texto += f"  Perdida: ${abs(ganancia):,.0f} ({ganancia_porcentaje:.1f}%)\n"
                    
                    texto += f"  Stock: {cantidad} unidades\n"
                    texto += f"  Presentacion: {presentacion}\n"
                    texto += f"  Proveedor: {proveedor_nombre}\n"
                    texto += f"  Telefono Proveedor: {proveedor_telefono}\n"
                    if proveedor_correo and proveedor_correo != 'N/D':
                        texto += f"  Email Proveedor: {proveedor_correo}\n"
                    texto += f"  Descripcion: {descripcion}\n"
                    texto += "-" * 40 + "\n"
            else:
                texto = f"No se encontraron productos con nombre que contenga '{nombre_busqueda}'"
        except Exception as e:
            logger.error(f"Error en busqueda por nombre: {e}")
            texto = f"Error al buscar productos con '{nombre_busqueda}'"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Nueva busqueda', 'payload': 'buscar_producto_nombre'},
                {'label': 'Buscar por categoria', 'payload': 'buscar_producto_categoria'},
                {'label': 'Listar todos', 'payload': 'listar_todos_productos'},
                {'label': 'Volver', 'payload': 'menu_productos'}
            ],
            'nuevo_estado': 'menu_productos'
        }
    
    # Busqueda por categoria (seleccion)
    if payload.startswith('categoria_'):
        categoria = payload.replace('categoria_', '')
        try:
            productos = db.fetch_all(
                """SELECT p.*, COALESCE(pr.nombre_proveedor, 'SIN PROVEEDOR') as proveedor_nombre
                   FROM productos p
                   LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                   WHERE p.categoria = %s
                   ORDER BY p.nombre""",
                (categoria,)
            )
            
            if productos and len(productos) > 0:
                texto = f"PRODUCTOS EN CATEGORIA '{categoria}'\n"
                texto += "-" * 60 + "\n\n"
                texto += "{:<35} {:<10} {:<12} {:<20}\n".format("PRODUCTO", "STOCK", "PRECIO", "PROVEEDOR")
                texto += "-" * 80 + "\n"
                for p in productos:
                    nombre = p.get('nombre', 'N/A')[:33]
                    cantidad = p.get('cantidad', 0)
                    precio = float(p.get('precio_venta', 0))
                    proveedor = p.get('proveedor_nombre', 'SIN PROVEEDOR')[:18]
                    texto += "{:<35} {:<10} ${:<11,.0f} {:<20}\n".format(nombre, str(cantidad), precio, proveedor)
                texto += "\n" + "-" * 60
            else:
                texto = f"No hay productos en la categoria '{categoria}'"
        except Exception as e:
            logger.error(f"Error en busqueda por categoria: {e}")
            texto = f"Error al buscar productos en categoria '{categoria}'"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Otra categoria', 'payload': 'buscar_producto_categoria'},
                {'label': 'Buscar por nombre', 'payload': 'buscar_producto_nombre'},
                {'label': 'Volver', 'payload': 'menu_productos'}
            ],
            'nuevo_estado': 'menu_productos'
        }
    
    # ========== CLIENTES ==========
    if payload == 'menu_clientes':
        return {
            'mensaje': 'MODULO DE CLIENTES\n\nSeleccione una opcion:',
            'botones': [
                {'label': 'Buscar por cedula', 'payload': 'buscar_cliente_cedula'},
                {'label': 'Buscar por nombre', 'payload': 'buscar_cliente_nombre'},
                {'label': 'Listar todos los clientes', 'payload': 'listar_todos_clientes'},
                {'label': 'Clientes con creditos', 'payload': 'clientes_creditos'},
                {'label': 'Volver', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_clientes'
        }
    
    if payload == 'buscar_cliente_cedula':
        return {
            'mensaje': 'BUSCAR CLIENTE POR CEDULA\n\nEscriba el numero de cedula:',
            'botones': [{'label': 'Cancelar', 'payload': 'menu_clientes'}],
            'nuevo_estado': 'buscando_cliente_por_cedula',
            'solicitar_texto': True,
            'texto_instruccion': 'Cedula del cliente:'
        }
    
    if payload == 'buscar_cliente_nombre':
        return {
            'mensaje': 'BUSCAR CLIENTE POR NOMBRE\n\nEscriba el nombre del cliente:',
            'botones': [{'label': 'Cancelar', 'payload': 'menu_clientes'}],
            'nuevo_estado': 'buscando_cliente_por_nombre',
            'solicitar_texto': True,
            'texto_instruccion': 'Nombre del cliente:'
        }
    
    if payload == 'listar_todos_clientes':
        try:
            clientes = db.fetch_all(
                "SELECT cedula, nombre, telefono, correo, direccion, fecha_creacion FROM cliente ORDER BY nombre LIMIT 30"
            )
            
            if clientes and len(clientes) > 0:
                texto = "LISTA DE CLIENTES\n"
                texto += "-" * 80 + "\n\n"
                texto += "{:<20} {:<15} {:<15} {:<25}\n".format("NOMBRE", "CEDULA", "TELEFONO", "CORREO")
                texto += "-" * 80 + "\n"
                for c in clientes:
                    nombre = c.get('nombre', 'N/A')[:18]
                    cedula = c.get('cedula', 'N/A')[:13]
                    telefono = (c.get('telefono') or 'N/A')[:13]
                    correo = (c.get('correo') or 'N/A')[:23]
                    texto += "{:<20} {:<15} {:<15} {:<25}\n".format(nombre, cedula, telefono, correo)
                texto += "\n" + "-" * 80
                if len(clientes) == 30:
                    texto += "\n\n*Mostrando primeros 30 clientes. Use la busqueda para mas especificos.*"
            else:
                texto = "No hay clientes registrados."
        except Exception as e:
            logger.error(f"Error en listar_todos_clientes: {e}")
            texto = "Error al consultar clientes."
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Buscar cliente', 'payload': 'menu_clientes'},
                {'label': 'Clientes con creditos', 'payload': 'clientes_creditos'},
                {'label': 'Volver', 'payload': 'menu_clientes'}
            ],
            'nuevo_estado': 'menu_clientes'
        }
    
    if payload == 'clientes_creditos':
        try:
            clientes_credito = db.fetch_all(
                """SELECT 
                    cl.cedula,
                    cl.nombre,
                    cl.telefono,
                    SUM(c.deuda_inicial) as total_credito_inicial,
                    SUM(c.saldo_pendiente) as total_credito_actual,
                    MAX(c.fecha_vencimiento) as ultima_fecha_vencimiento
                   FROM cliente cl
                   JOIN creditos c ON cl.cedula = c.cliente_cedula
                   WHERE c.estado IN ('pendiente', 'vencido')
                   GROUP BY cl.cedula, cl.nombre, cl.telefono
                   ORDER BY total_credito_actual DESC
                   LIMIT 30"""
            )
            
            if clientes_credito and len(clientes_credito) > 0:
                texto = "CLIENTES CON CREDITOS ACTIVOS\n"
                texto += "=" * 80 + "\n\n"
                texto += "{:<25} {:<15} {:<15} {:<15} {:<15}\n".format("NOMBRE", "CEDULA", "TELEFONO", "CRED.INICIAL", "SALDO")
                texto += "-" * 85 + "\n"
                for c in clientes_credito:
                    nombre = c.get('nombre', 'N/A')[:23]
                    cedula = c.get('cedula', 'N/A')[:13]
                    telefono = (c.get('telefono') or 'N/A')[:13]
                    credito_inicial = float(c.get('total_credito_inicial', 0))
                    credito_actual = float(c.get('total_credito_actual', 0))
                    texto += "{:<25} {:<15} {:<15} ${:<14,.0f} ${:<14,.0f}\n".format(nombre, cedula, telefono, credito_inicial, credito_actual)
                texto += "\n" + "=" * 80
            else:
                texto = "No hay clientes con creditos activos pendientes."
        except Exception as e:
            logger.error(f"Error en clientes_creditos: {e}")
            texto = "Error al consultar clientes con creditos."
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Volver a clientes', 'payload': 'menu_clientes'},
                {'label': 'Ver todos los creditos', 'payload': 'creditos_pendientes'},
                {'label': 'Menu principal', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_clientes'
        }
    
    # Busqueda de cliente por cedula
    if estado_actual == 'buscando_cliente_por_cedula' and not payload.startswith('menu_'):
        cedula = payload
        try:
            cliente = db.fetch_one(
                "SELECT * FROM cliente WHERE cedula = %s",
                (cedula,)
            )
            
            if cliente and len(cliente) > 0:
                creditos = db.fetch_all(
                    "SELECT * FROM creditos WHERE cliente_cedula = %s AND estado != 'pagado'",
                    (cedula,)
                )
                nombre = cliente.get('nombre', 'N/A')
                cedula_val = cliente.get('cedula', 'N/A')
                telefono = cliente.get('telefono') or 'N/A'
                correo = cliente.get('correo') or 'N/A'
                direccion = cliente.get('direccion') or 'N/A'
                fecha_reg = cliente.get('fecha_creacion')
                fecha_str = fecha_reg.strftime('%d/%m/%Y') if fecha_reg else 'N/A'
                creditos_count = len(creditos) if creditos else 0
                
                texto = f"INFORMACION DEL CLIENTE\n"
                texto += "=" * 50 + "\n\n"
                texto += f"Nombre: {nombre}\n"
                texto += f"Cedula: {cedula_val}\n"
                texto += f"Telefono: {telefono}\n"
                texto += f"Correo: {correo}\n"
                texto += f"Direccion: {direccion}\n"
                texto += f"Fecha Registro: {fecha_str}\n"
                texto += f"Creditos Activos: {creditos_count}"
            else:
                texto = f"No se encontro cliente con cedula {cedula}"
        except Exception as e:
            logger.error(f"Error en busqueda por cedula: {e}")
            texto = f"Error al buscar cliente con cedula {cedula}"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Buscar otro cliente', 'payload': 'menu_clientes'},
                {'label': 'Volver', 'payload': 'menu_clientes'}
            ],
            'nuevo_estado': 'menu_clientes'
        }
    
    # Busqueda de cliente por nombre
    if estado_actual == 'buscando_cliente_por_nombre' and not payload.startswith('menu_'):
        nombre_busqueda = payload
        try:
            clientes = db.fetch_all(
                "SELECT * FROM cliente WHERE nombre LIKE %s ORDER BY nombre LIMIT 10",
                (f"%{nombre_busqueda}%",)
            )
            
            if clientes and len(clientes) > 0:
                texto = f"RESULTADOS PARA '{nombre_busqueda}'\n"
                texto += "-" * 60 + "\n\n"
                texto += "{:<30} {:<15} {:<15}\n".format("NOMBRE", "CEDULA", "TELEFONO")
                texto += "-" * 60 + "\n"
                for c in clientes:
                    nombre = c.get('nombre', 'N/A')[:28]
                    cedula = c.get('cedula', 'N/A')[:13]
                    telefono = (c.get('telefono') or 'N/A')[:13]
                    texto += "{:<30} {:<15} {:<15}\n".format(nombre, cedula, telefono)
                texto += "\n" + "-" * 60
            else:
                texto = f"No se encontraron clientes con nombre que contenga '{nombre_busqueda}'"
        except Exception as e:
            logger.error(f"Error en busqueda por nombre: {e}")
            texto = f"Error al buscar clientes con '{nombre_busqueda}'"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Nueva busqueda', 'payload': 'menu_clientes'},
                {'label': 'Listar todos', 'payload': 'listar_todos_clientes'},
                {'label': 'Volver', 'payload': 'menu_clientes'}
            ],
            'nuevo_estado': 'menu_clientes'
        }
    
    # ========== VENTAS ==========
    if payload == 'menu_ventas':
        try:
            hoy = date.today()
            ventas_hoy = db.fetch_scalar("SELECT COUNT(*) FROM ventas WHERE fecha_dia = %s", (hoy,))
            total_hoy = db.fetch_scalar("SELECT COALESCE(SUM(total), 0) FROM ventas WHERE fecha_dia = %s", (hoy,))
            if ventas_hoy is None:
                ventas_hoy = 0
            if total_hoy is None:
                total_hoy = 0
        except:
            ventas_hoy = 0
            total_hoy = 0
        
        return {
            'mensaje': f"MODULO DE VENTAS\n\nResumen rapido:\n  Ventas hoy: {ventas_hoy}\n  Total hoy: ${float(total_hoy):,.2f}\n\nSeleccione una opcion:",
            'botones': [
                {'label': 'Ventas de hoy', 'payload': 'ventas_hoy'},
                {'label': 'Ventas de ayer', 'payload': 'ventas_ayer'},
                {'label': 'Top productos vendidos', 'payload': 'top_productos'},
                {'label': 'Ultimas 10 ventas', 'payload': 'ultimas_ventas'},
                {'label': 'Volver', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_ventas'
        }
    
    if payload == 'ventas_hoy':
        try:
            hoy = date.today()
            ventas = db.fetch_all(
                """SELECT v.id, v.numero_venta, v.nombre_cliente, v.total, v.tipo_pago
                   FROM ventas v
                   WHERE v.fecha_dia = %s
                   ORDER BY v.id DESC LIMIT 15""",
                (hoy,)
            )
            
            if ventas and len(ventas) > 0:
                total_dia = sum(float(v.get('total', 0)) for v in ventas)
                texto = f"VENTAS DE HOY ({hoy.strftime('%d/%m/%Y')})\n"
                texto += "=" * 70 + "\n\n"
                texto += "{:<12} {:<25} {:<12} {:<15}\n".format("TICKET", "CLIENTE", "TOTAL", "FORMA PAGO")
                texto += "-" * 70 + "\n"
                for v in ventas:
                    ticket = str(v.get('numero_venta', 'N/A'))[:10]
                    cliente = v.get('nombre_cliente', 'N/A')[:23]
                    total = float(v.get('total', 0))
                    tipo_pago = v.get('tipo_pago', 'N/A')[:13]
                    texto += "{:<12} {:<25} ${:<11,.0f} {:<15}\n".format(ticket, cliente, total, tipo_pago)
                texto += "\n" + "-" * 70
                texto += f"\nTOTAL DEL DIA: ${total_dia:,.2f}"
            else:
                texto = f"No hay ventas registradas hoy ({hoy.strftime('%d/%m/%Y')})"
        except Exception as e:
            logger.error(f"Error en ventas_hoy: {e}")
            texto = "Error al consultar ventas de hoy"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ventas de ayer', 'payload': 'ventas_ayer'},
                {'label': 'Volver a ventas', 'payload': 'menu_ventas'}
            ],
            'nuevo_estado': 'menu_ventas'
        }
    
    if payload == 'ventas_ayer':
        try:
            ayer = date.today() - timedelta(days=1)
            ventas = db.fetch_all(
                """SELECT v.id, v.numero_venta, v.nombre_cliente, v.total, v.tipo_pago
                   FROM ventas v
                   WHERE v.fecha_dia = %s
                   ORDER BY v.id DESC LIMIT 15""",
                (ayer,)
            )
            
            if ventas and len(ventas) > 0:
                total_dia = sum(float(v.get('total', 0)) for v in ventas)
                texto = f"VENTAS DE AYER ({ayer.strftime('%d/%m/%Y')})\n"
                texto += "=" * 70 + "\n\n"
                texto += "{:<12} {:<25} {:<12} {:<15}\n".format("TICKET", "CLIENTE", "TOTAL", "FORMA PAGO")
                texto += "-" * 70 + "\n"
                for v in ventas:
                    ticket = str(v.get('numero_venta', 'N/A'))[:10]
                    cliente = v.get('nombre_cliente', 'N/A')[:23]
                    total = float(v.get('total', 0))
                    tipo_pago = v.get('tipo_pago', 'N/A')[:13]
                    texto += "{:<12} {:<25} ${:<11,.0f} {:<15}\n".format(ticket, cliente, total, tipo_pago)
                texto += "\n" + "-" * 70
                texto += f"\nTOTAL DEL DIA: ${total_dia:,.2f}"
            else:
                texto = f"No hay ventas registradas el {ayer.strftime('%d/%m/%Y')}"
        except Exception as e:
            logger.error(f"Error en ventas_ayer: {e}")
            texto = "Error al consultar ventas de ayer"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ventas de hoy', 'payload': 'ventas_hoy'},
                {'label': 'Volver a ventas', 'payload': 'menu_ventas'}
            ],
            'nuevo_estado': 'menu_ventas'
        }
    
    if payload == 'top_productos':
        try:
            productos = db.fetch_all(
                """SELECT p.nombre, SUM(dv.cantidad_vendida) as total_vendido
                   FROM detalle_venta dv
                   JOIN productos p ON dv.id_producto = p.id
                   GROUP BY p.id, p.nombre
                   ORDER BY total_vendido DESC
                   LIMIT 10"""
            )
            
            if productos and len(productos) > 0:
                texto = "TOP 10 PRODUCTOS MAS VENDIDOS\n"
                texto += "-" * 50 + "\n\n"
                texto += "{:<5} {:<35} {:<10}\n".format("POS", "PRODUCTO", "UNIDADES")
                texto += "-" * 50 + "\n"
                for i, p in enumerate(productos, 1):
                    nombre = p.get('nombre', 'N/A')[:33]
                    total = p.get('total_vendido', 0)
                    texto += "{:<5} {:<35} {:<10}\n".format(str(i), nombre, str(total))
                texto += "\n" + "-" * 50
            else:
                texto = "No hay datos de ventas suficientes."
        except Exception as e:
            logger.error(f"Error en top_productos: {e}")
            texto = "Error al consultar top productos"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ventas de hoy', 'payload': 'ventas_hoy'},
                {'label': 'Volver a ventas', 'payload': 'menu_ventas'}
            ],
            'nuevo_estado': 'menu_ventas'
        }
    
    if payload == 'ultimas_ventas':
        try:
            ventas = db.fetch_all(
                """SELECT v.id, v.numero_venta, v.nombre_cliente, v.total, v.fecha_dia, v.tipo_pago
                   FROM ventas v
                   ORDER BY v.id DESC
                   LIMIT 10"""
            )
            
            if ventas and len(ventas) > 0:
                texto = "ULTIMAS 10 VENTAS\n"
                texto += "=" * 75 + "\n\n"
                texto += "{:<12} {:<25} {:<12} {:<12} {:<15}\n".format("TICKET", "CLIENTE", "TOTAL", "FECHA", "FORMA PAGO")
                texto += "-" * 80 + "\n"
                for v in ventas:
                    ticket = str(v.get('numero_venta', 'N/A'))[:10]
                    cliente = v.get('nombre_cliente', 'N/A')[:23]
                    total = float(v.get('total', 0))
                    fecha = v.get('fecha_dia')
                    fecha_str = fecha.strftime('%d/%m/%Y') if fecha else 'N/A'
                    tipo_pago = v.get('tipo_pago', 'N/A')[:13]
                    texto += "{:<12} {:<25} ${:<11,.0f} {:<12} {:<15}\n".format(ticket, cliente, total, fecha_str, tipo_pago)
                texto += "\n" + "=" * 75
            else:
                texto = "No hay ventas registradas."
        except Exception as e:
            logger.error(f"Error en ultimas_ventas: {e}")
            texto = "Error al consultar ultimas ventas"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ventas de hoy', 'payload': 'ventas_hoy'},
                {'label': 'Volver a ventas', 'payload': 'menu_ventas'}
            ],
            'nuevo_estado': 'menu_ventas'
        }
    
    # ========== CREDITOS ==========
    if payload == 'menu_creditos':
        try:
            pendientes = db.fetch_scalar("SELECT COUNT(*) FROM creditos WHERE estado IN ('pendiente', 'vencido')")
            monto_pendiente = db.fetch_scalar("SELECT COALESCE(SUM(saldo_pendiente), 0) FROM creditos WHERE estado IN ('pendiente', 'vencido')")
            if pendientes is None:
                pendientes = 0
            if monto_pendiente is None:
                monto_pendiente = 0
        except:
            pendientes = 0
            monto_pendiente = 0
        
        return {
            'mensaje': f"GESTION DE CREDITOS\n\nResumen actual:\n  Creditos activos: {pendientes}\n  Monto total pendiente: ${float(monto_pendiente):,.2f}\n\nSeleccione una opcion:",
            'botones': [
                {'label': 'Listar creditos pendientes', 'payload': 'creditos_pendientes'},
                {'label': 'Creditos vencidos', 'payload': 'creditos_vencidos'},
                {'label': 'Abonos recientes', 'payload': 'abonos_recientes'},
                {'label': 'Volver', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_creditos'
        }
    
    if payload == 'creditos_pendientes':
        try:
            creditos = db.fetch_all(
                """SELECT c.id, cl.nombre, cl.cedula, c.deuda_inicial, c.saldo_pendiente, 
                          c.fecha_vencimiento, c.estado,
                          DATEDIFF(CURDATE(), c.fecha_vencimiento) as dias_vencido
                   FROM creditos c
                   JOIN cliente cl ON c.cliente_cedula = cl.cedula
                   WHERE c.estado IN ('pendiente', 'vencido')
                   ORDER BY c.fecha_vencimiento ASC
                   LIMIT 20"""
            )
            
            if creditos and len(creditos) > 0:
                texto = "CREDITOS PENDIENTES\n"
                texto += "=" * 80 + "\n\n"
                texto += "{:<25} {:<12} {:<15} {:<12} {:<15}\n".format("CLIENTE", "CEDULA", "DEUDA ACTUAL", "VENCE", "ESTADO")
                texto += "-" * 85 + "\n"
                for c in creditos:
                    nombre = c.get('nombre', 'N/A')[:23]
                    cedula = c.get('cedula', 'N/A')[:10]
                    saldo = float(c.get('saldo_pendiente', 0))
                    fecha = c.get('fecha_vencimiento', 'N/A')
                    if hasattr(fecha, 'strftime'):
                        fecha = fecha.strftime('%d/%m/%Y')
                    estado = c.get('estado', 'N/A')
                    if estado == 'vencido':
                        estado = "VENCIDO"
                    else:
                        estado = "PENDIENTE"
                    texto += "{:<25} {:<12} ${:<14,.0f} {:<12} {:<15}\n".format(nombre, cedula, saldo, fecha, estado)
                texto += "\n" + "=" * 80
            else:
                texto = "No hay creditos pendientes. Todos los creditos estan al dia."
        except Exception as e:
            logger.error(f"Error en creditos_pendientes: {e}")
            texto = "Error al consultar creditos pendientes"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Abonos recientes', 'payload': 'abonos_recientes'},
                {'label': 'Ver vencidos', 'payload': 'creditos_vencidos'},
                {'label': 'Volver a creditos', 'payload': 'menu_creditos'}
            ],
            'nuevo_estado': 'menu_creditos'
        }
    
    if payload == 'creditos_vencidos':
        try:
            creditos = db.fetch_all(
                """SELECT c.id, cl.nombre, cl.cedula, c.saldo_pendiente, c.fecha_vencimiento,
                          DATEDIFF(CURDATE(), c.fecha_vencimiento) as dias_vencido
                   FROM creditos c
                   JOIN cliente cl ON c.cliente_cedula = cl.cedula
                   WHERE c.estado = 'vencido' OR (c.estado = 'pendiente' AND c.fecha_vencimiento < CURDATE())
                   ORDER BY c.fecha_vencimiento ASC
                   LIMIT 20"""
            )
            
            if creditos and len(creditos) > 0:
                total = sum(float(c.get('saldo_pendiente', 0)) for c in creditos)
                texto = f"CREDITOS VENCIDOS\n"
                texto += "=" * 70 + "\n\n"
                texto += f"Total en mora: ${total:,.2f}\n"
                texto += f"Numero de clientes: {len(creditos)}\n\n"
                texto += "{:<25} {:<12} {:<15} {:<15}\n".format("CLIENTE", "CEDULA", "SALDO", "DIAS VENCIDO")
                texto += "-" * 70 + "\n"
                for c in creditos:
                    nombre = c.get('nombre', 'N/A')[:23]
                    cedula = c.get('cedula', 'N/A')[:10]
                    saldo = float(c.get('saldo_pendiente', 0))
                    dias = c.get('dias_vencido', 0)
                    texto += "{:<25} {:<12} ${:<14,.0f} {:<15}\n".format(nombre, cedula, saldo, f"{dias} dias")
                texto += "\n" + "=" * 70
            else:
                texto = "No hay creditos vencidos."
        except Exception as e:
            logger.error(f"Error en creditos_vencidos: {e}")
            texto = "Error al consultar creditos vencidos"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ver todos los pendientes', 'payload': 'creditos_pendientes'},
                {'label': 'Volver a creditos', 'payload': 'menu_creditos'}
            ],
            'nuevo_estado': 'menu_creditos'
        }
    
    if payload == 'abonos_recientes':
        try:
            abonos = db.fetch_all(
                """SELECT a.monto, a.fecha, a.metodo_pago, cl.nombre as cliente_nombre, cl.cedula
                   FROM abonos a
                   JOIN creditos c ON a.credito_id = c.id
                   JOIN cliente cl ON c.cliente_cedula = cl.cedula
                   ORDER BY a.fecha DESC
                   LIMIT 15"""
            )
            
            if abonos and len(abonos) > 0:
                texto = "ABONOS RECIENTES\n"
                texto += "=" * 70 + "\n\n"
                texto += "{:<25} {:<12} {:<12} {:<15} {:<15}\n".format("CLIENTE", "CEDULA", "MONTO", "METODO", "FECHA")
                texto += "-" * 85 + "\n"
                for a in abonos:
                    nombre = a.get('cliente_nombre', 'N/A')[:23]
                    cedula = a.get('cedula', 'N/A')[:10]
                    monto = float(a.get('monto', 0))
                    metodo = a.get('metodo_pago', 'N/A')[:13]
                    fecha = a.get('fecha')
                    fecha_str = fecha.strftime('%d/%m/%Y') if fecha else 'N/A'
                    texto += "{:<25} {:<12} ${:<11,.0f} {:<15} {:<15}\n".format(nombre, cedula, monto, metodo, fecha_str)
                texto += "\n" + "=" * 70
            else:
                texto = "No hay abonos registrados."
        except Exception as e:
            logger.error(f"Error en abonos_recientes: {e}")
            texto = "Error al consultar abonos recientes"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ver creditos pendientes', 'payload': 'creditos_pendientes'},
                {'label': 'Volver a creditos', 'payload': 'menu_creditos'}
            ],
            'nuevo_estado': 'menu_creditos'
        }
    
    # ========== REPORTE DE CAJA ==========
    if payload == 'reporte_caja':
        try:
            hoy = date.today()
            ventas_hoy_total = db.fetch_scalar(
                "SELECT COALESCE(SUM(total), 0) FROM ventas WHERE fecha_dia = %s AND estado = 'completada'",
                (hoy,)
            )
            if ventas_hoy_total is None:
                ventas_hoy_total = 0
            
            abonos_hoy = db.fetch_scalar(
                "SELECT COALESCE(SUM(monto), 0) FROM abonos WHERE DATE(fecha) = CURDATE()"
            )
            if abonos_hoy is None:
                abonos_hoy = 0
            
            ventas_mes = db.fetch_scalar(
                "SELECT COALESCE(SUM(total), 0) FROM ventas WHERE MONTH(fecha_dia) = MONTH(CURDATE()) AND YEAR(fecha_dia) = YEAR(CURDATE())"
            )
            if ventas_mes is None:
                ventas_mes = 0
            
            abonos_mes = db.fetch_scalar(
                "SELECT COALESCE(SUM(monto), 0) FROM abonos WHERE MONTH(fecha) = MONTH(CURDATE()) AND YEAR(fecha) = YEAR(CURDATE())"
            )
            if abonos_mes is None:
                abonos_mes = 0
            
            total_creditos_pendientes = db.fetch_scalar(
                "SELECT COALESCE(SUM(saldo_pendiente), 0) FROM creditos WHERE estado IN ('pendiente', 'vencido')"
            )
            if total_creditos_pendientes is None:
                total_creditos_pendientes = 0
            
            total_productos = db.fetch_scalar("SELECT COUNT(*) FROM productos")
            if total_productos is None:
                total_productos = 0
            
            valor_inventario = db.fetch_scalar("SELECT COALESCE(SUM(precio_costo * cantidad), 0) FROM productos")
            if valor_inventario is None:
                valor_inventario = 0
            
            texto = f"REPORTE FINANCIERO COMPLETO\n"
            texto += "=" * 60 + "\n\n"
            texto += f"RESUMEN DEL DIA ({hoy.strftime('%d/%m/%Y')})\n"
            texto += "-" * 40 + "\n"
            texto += f"  Ventas del dia: ${float(ventas_hoy_total):,.2f}\n"
            texto += f"  Abonos recibidos: ${float(abonos_hoy):,.2f}\n"
            texto += f"  Ingreso total dia: ${float(ventas_hoy_total + abonos_hoy):,.2f}\n\n"
            texto += f"RESUMEN DEL MES\n"
            texto += "-" * 40 + "\n"
            texto += f"  Ventas del mes: ${float(ventas_mes):,.2f}\n"
            texto += f"  Abonos del mes: ${float(abonos_mes):,.2f}\n"
            texto += f"  Ingreso total mes: ${float(ventas_mes + abonos_mes):,.2f}\n\n"
            texto += f"CARTERA DE CREDITOS\n"
            texto += "-" * 40 + "\n"
            texto += f"  Total por cobrar: ${float(total_creditos_pendientes):,.2f}\n\n"
            texto += f"INVENTARIO\n"
            texto += "-" * 40 + "\n"
            texto += f"  Total productos: {total_productos}\n"
            texto += f"  Valor inventario: ${float(valor_inventario):,.2f}\n"
            texto += "=" * 60
        except Exception as e:
            logger.error(f"Error en reporte_caja: {e}")
            texto = "Error al generar reporte financiero"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ver ventas de hoy', 'payload': 'ventas_hoy'},
                {'label': 'Ver abonos del dia', 'payload': 'abonos_recientes'},
                {'label': 'Ver creditos pendientes', 'payload': 'creditos_pendientes'},
                {'label': 'Menu principal', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_principal'
        }
    
    # ========== ALERTAS ==========
    if payload == 'alertas':
        try:
            stock_bajo = db.fetch_all(
                """SELECT p.nombre, p.cantidad, COALESCE(pr.nombre_proveedor, 'SIN PROVEEDOR') as proveedor_nombre
                   FROM productos p
                   LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                   WHERE p.cantidad < 5
                   ORDER BY p.cantidad ASC
                   LIMIT 10"""
            )
            
            creditos_proximos = db.fetch_all(
                """SELECT c.id, cl.nombre, c.saldo_pendiente, c.fecha_vencimiento
                   FROM creditos c
                   JOIN cliente cl ON c.cliente_cedula = cl.cedula
                   WHERE c.estado = 'pendiente' 
                     AND c.fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                   ORDER BY c.fecha_vencimiento ASC
                   LIMIT 10"""
            )
            
            texto = "ALERTAS DEL SISTEMA\n"
            texto += "=" * 50 + "\n\n"
            
            if stock_bajo and len(stock_bajo) > 0:
                texto += "STOCK BAJO (menos de 5 unidades)\n"
                texto += "-" * 40 + "\n"
                for p in stock_bajo:
                    texto += f"  - {p.get('nombre', 'N/A')}: {p.get('cantidad', 0)} unidades (Prov: {p.get('proveedor_nombre', 'N/A')})\n"
                texto += "\n"
            else:
                texto += "STOCK: Todos los productos con inventario suficiente.\n\n"
            
            if creditos_proximos and len(creditos_proximos) > 0:
                texto += "CREDITOS POR VENCER (proximos 7 dias)\n"
                texto += "-" * 40 + "\n"
                for c in creditos_proximos:
                    fecha = c.get('fecha_vencimiento')
                    fecha_str = fecha.strftime('%d/%m/%Y') if fecha else 'N/A'
                    texto += f"  - {c.get('nombre', 'N/A')}: ${float(c.get('saldo_pendiente', 0)):,.2f} (vence {fecha_str})\n"
            else:
                texto += "CREDITOS: No hay creditos por vencer proximamente."
            
            texto += "\n" + "=" * 50
        except Exception as e:
            logger.error(f"Error en alertas: {e}")
            texto = "Error al consultar alertas"
        
        return {
            'mensaje': texto,
            'botones': [
                {'label': 'Ver stock bajo', 'payload': 'ver_stock_bajo'},
                {'label': 'Ver creditos pendientes', 'payload': 'creditos_pendientes'},
                {'label': 'Volver', 'payload': 'menu_principal'}
            ],
            'nuevo_estado': 'menu_principal'
        }
    
    # ========== DEFAULT ==========
    return {
        'mensaje': 'Opcion no reconocida. Volviendo al menu principal.',
        'botones': [{'label': 'Menu principal', 'payload': 'menu_principal'}],
        'nuevo_estado': 'menu_principal'
    }