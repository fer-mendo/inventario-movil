import streamlit as st
from supabase import create_client, Client
import pandas as pd
import io
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración de página
st.set_page_config(page_title="MendoMedica - Inventario", page_icon="🏥", layout="wide")

# ==============================================================================
# 🖼️ ARCHIVO DEL LOGO DE LA EMPRESA
# ==============================================================================
# Nombre del archivo guardado en el repositorio de GitHub
URL_LOGO = "logo.png" 

# ==============================================================================
# 🏬 LISTA MAESTRA DE ALMACENES
# ==============================================================================
LISTA_ALMACENES = [
    "General", 
    "Olympus", 
    "Pentax", 
    "Aohua", 
    "Aquilo", 
    "SportMedical"
]

# Configuración de Supabase
SUPABASE_URL = "https://dsnjdrgtbhwkcxkfeipl.supabase.co"
SUPABASE_KEY = "sb_secret_H1879_2HEXiHBASrVbLauA_wGvHP6kK"

# Configuración SMTP (Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "f.monneretscg@gmail.com"

try:
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except Exception:
    SMTP_PASSWORD = "uioqwteiodskteou"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Error al conectar con Supabase: {e}")
    st.stop()

def enviar_email_invitacion(email_destino, nombre_usuario, password, rol):
    if not SMTP_PASSWORD:
        return False, "Falta configurar SMTP_PASSWORD en los Secrets de Streamlit o código."
    try:
        URL_APP = "https://inventariomendoapp.streamlit.app/"

        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = email_destino
        msg['Subject'] = "Invitación al Sistema de Inventario - MendoMedica"

        cuerpo = f"""
        Hola {nombre_usuario},

        Se ha creado tu cuenta con el rol de {rol} en MendoMedica.

        Tus datos de acceso:
        -------------------------------------------
        Correo: {email_destino}
        Contraseña: {password}
        -------------------------------------------

        🔗 Accede al sistema aquí:
        {URL_APP}

        Atentamente,
        Equipo MendoMedica
        """
        msg.attach(MIMEText(cuerpo, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD.replace(" ", ""))
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado correctamente."
    except Exception as e:
        return False, str(e)

def generar_excel_seguro(df, nombre_hoja="Datos"):
    output = io.BytesIO()
    motor_usado = None
    
    try:
        import openpyxl
        motor_usado = 'openpyxl'
    except ImportError:
        try:
            import xlsxwriter
            motor_usado = 'xlsxwriter'
        except ImportError:
            motor_usado = None

    if motor_usado:
        with pd.ExcelWriter(output, engine=motor_usado) as writer:
            df.to_excel(writer, index=False, sheet_name=nombre_hoja)
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        csv_data = df.to_csv(index=False).encode('utf-8')
        return csv_data, "text/csv", "csv"

if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

if "items_remito" not in st.session_state:
    st.session_state["items_remito"] = []

# ==========================================
# 1. LOGIN CON LOGO
# ==========================================
if not st.session_state["usuario"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try:
            st.image(URL_LOGO, use_container_width=True)
        except Exception:
            st.title("🏥 MendoMedica")
            
        st.subheader("Sistema de Gestión e Inventario")
        st.caption("Portal Institucional de Control de Stock")
        
        with st.form("form_login"):
            email = st.text_input("Correo Electrónico").strip().lower()
            password = st.text_input("Contraseña", type="password").strip()
            btn_login = st.form_submit_button("Ingresar", use_container_width=True)
            
            if btn_login:
                user_encontrado = None
                try:
                    res_admin = supabase.table("administradores").select("*").eq("email", email).eq("password", password).execute()
                    if res_admin.data:
                        user_encontrado = res_admin.data[0]
                        user_encontrado["rol"] = "Administrador"
                except Exception:
                    pass

                if not user_encontrado:
                    try:
                        res_movil = supabase.table("usuarios_movil").select("*").eq("email", email).eq("password", password).execute()
                        if res_movil.data:
                            user_encontrado = res_movil.data[0]
                            user_encontrado["rol"] = "Usuario Móvil"
                    except Exception:
                        pass

                if user_encontrado:
                    st.session_state["usuario"] = user_encontrado
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")
    st.stop()

# ==========================================
# 2. NAVEGACIÓN Y PANEL LATERAL CON LOGO
# ==========================================
user_actual = st.session_state["usuario"]
es_admin = user_actual.get("rol") == "Administrador"

try:
    st.sidebar.image(URL_LOGO, use_container_width=True)
except Exception:
    st.sidebar.title("🏥 MendoMedica")

st.sidebar.write(f"👤 **{user_actual.get('nombre', 'Usuario')}**")
st.sidebar.caption(f"Rol: **{user_actual.get('rol')}**")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state["usuario"] = None
    st.session_state["items_remito"] = []
    st.rerun()

st.sidebar.markdown("---")

if es_admin:
    opciones_menu = [
        "📦 Control de Inventario", 
        "🧾 Generar Remito de Salida",
        "🔄 Movimientos (Entrada / Salida)", 
        "➕ Cargar Nuevo Producto", 
        "📄 Historial y Reporte Excel",
        "👥 Gestión de Usuarios"
    ]
else:
    opciones_menu = ["📦 Control de Inventario"]

opcion = st.sidebar.radio("Navegación:", opciones_menu)

# ==========================================
# 3. CONTROL DE INVENTARIO
# ==========================================
if opcion == "📦 Control de Inventario":
    st.title("📦 Control de Inventario y Stock")
    
    # Determinación de almacenes permitidos según rol
    raw_perm = user_actual.get("almacenes_permitidos", "")
    if es_admin:
        almacenes_disponibles = ["Todos"] + LISTA_ALMACENES
        permitidos_lista = LISTA_ALMACENES
    else:
        if raw_perm:
            permitidos_lista = [a.strip() for a in str(raw_perm).split(",") if a.strip()]
        else:
            permitidos_lista = []
            
        if permitidos_lista:
            almacenes_disponibles = ["Todos los permitidos"] + permitidos_lista
        else:
            almacenes_disponibles = ["Sin almacenes asignados"]

    col_busq, col_alm = st.columns([2, 1])
    with col_busq:
        busqueda = st.text_input("🔍 Buscar por Nombre, Código, Cód. Barras, Marca, Categoría o Estado:")
    with col_alm:
        almacen_sel = st.selectbox("🏬 Almacén / Unidad:", almacenes_disponibles)
    
    try:
        res_prods = supabase.table("productos").select("*").execute()
        prods = res_prods.data if res_prods else []
        
        if prods:
            df_prods = pd.DataFrame(prods)
            
            # Limpiar comillas o formato en columnas de texto
            for col_str in ["moneda_costo", "estado", "almacen"]:
                if col_str in df_prods.columns:
                    df_prods[col_str] = df_prods[col_str].astype(str).str.replace("'", "").str.strip()

            # -----------------------------------------------------------------
            # FILTRADO SEGÚN ALMACÉN Y PERMISOS DE USUARIO
            # -----------------------------------------------------------------
            if "almacen" in df_prods.columns:
                if es_admin:
                    if almacen_sel != "Todos":
                        df_prods = df_prods[df_prods['almacen'].str.lower() == almacen_sel.lower()]
                else:
                    if not permitidos_lista:
                        df_prods = df_prods.iloc[0:0]
                    else:
                        permitidos_lower = [a.lower() for a in permitidos_lista]
                        if almacen_sel == "Todos los permitidos":
                            df_prods = df_prods[df_prods['almacen'].str.lower().isin(permitidos_lower)]
                        else:
                            if almacen_sel.lower() in permitidos_lower:
                                df_prods = df_prods[df_prods['almacen'].str.lower() == almacen_sel.lower()]
                            else:
                                df_prods = df_prods.iloc[0:0]

            # Búsqueda por texto
            if busqueda and not df_prods.empty:
                b = busqueda.lower()
                condicion = (
                    df_prods['nombre'].astype(str).str.lower().str.contains(b) |
                    df_prods['codigo'].astype(str).str.lower().str.contains(b) |
                    df_prods.get('codigo_barras', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b) |
                    df_prods.get('marca', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b) |
                    df_prods.get('categoria', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b) |
                    df_prods.get('estado', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b)
                )
                df_prods = df_prods[condicion]

            # Selección y orden de columnas visibles según Rol
            if es_admin:
                cols_prioritarias = [
                    "codigo", "codigo_barras", "nombre", "marca", "categoria", 
                    "stock_actual", "precio", "moneda", "costo", "moneda_costo", 
                    "estado", "almacen", "ubicacion", "proveedor", "cliente"
                ]
                cols_existentes = [c for c in cols_prioritarias if c in df_prods.columns]
                otras_cols = [c for c in df_prods.columns if c not in cols_existentes and c != 'id']
                df_prods_mostrar = df_prods[cols_existentes + otras_cols]
            else:
                cols_excluidas = ["costo", "moneda_costo", "estado", "proveedor", "cliente", "id"]
                df_prods_mostrar = df_prods.drop(columns=[c for c in cols_excluidas if c in df_prods.columns], errors='ignore')

            st.dataframe(df_prods_mostrar, use_container_width=True, hide_index=True)
            st.caption(f"Mostrando {len(df_prods_mostrar)} productos.")

            if es_admin:
                st.markdown("---")
                try:
                    file_data, mime_type, ext = generar_excel_seguro(pd.DataFrame(prods), nombre_hoja="Inventario")
                    st.download_button(
                        label=f"💾 Descargar Respaldo Completo de Inventario (.{ext.upper()})",
                        data=file_data,
                        file_name=f"Backup_Inventario_MendoMedica_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.{ext}",
                        mime=mime_type
                    )
                except Exception as e:
                    st.warning(f"No se pudo generar el archivo de respaldo: {e}")
        else:
            st.info("No hay productos registrados.")
    except Exception as e:
        st.error(f"Error al obtener el inventario: {e}")

# ==========================================
# 4. GENERAR REMITO DE SALIDA
# ==========================================
elif opcion == "🧾 Generar Remito de Salida" and es_admin:
    st.title("🧾 Generar Remito de Entrega / Salida")
    
    st.subheader("1. Datos del Destinatario / Cliente")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        rem_cliente = st.text_input("Nombre del Cliente / Institución *")
    with col_c2:
        rem_localidad = st.text_input("Localidad / Dirección *")
    with col_c3:
        rem_contacto = st.text_input("Teléfono / Email de Contacto")
        
    st.markdown("---")
    st.subheader("2. Agregar Productos al Remito")
    
    try:
        prods_rem = supabase.table("productos").select("codigo, nombre, stock_actual, precio, moneda").execute().data
        if prods_rem:
            dict_prods_rem = {f"{p['codigo']} - {p['nombre']} (Stock: {p.get('stock_actual', 0)})": p for p in prods_rem}
            
            col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
            with col_p1:
                p_sel = st.selectbox("Seleccionar Producto:", list(dict_prods_rem.keys()))
            with col_p2:
                p_cant = st.number_input("Cantidad:", min_value=1, value=1, key="cant_rem")
            with col_p3:
                st.write(" ")
                st.write(" ")
                btn_add_item = st.button("➕ Agregar Item", use_container_width=True)
                
            if btn_add_item:
                prod_obj = dict_prods_rem[p_sel]
                if p_cant > prod_obj.get("stock_actual", 0):
                    st.error(f"Stock insuficiente para {prod_obj['nombre']}. Disponible: {prod_obj.get('stock_actual', 0)}")
                else:
                    existente = False
                    for item in st.session_state["items_remito"]:
                        if item["codigo"] == prod_obj["codigo"]:
                            item["cantidad"] += p_cant
                            existente = True
                            break
                    if not existente:
                        st.session_state["items_remito"].append({
                            "codigo": prod_obj["codigo"],
                            "nombre": prod_obj["nombre"],
                            "cantidad": p_cant,
                            "stock_actual": prod_obj.get("stock_actual", 0),
                            "precio": prod_obj.get("precio", 0.0),
                            "moneda": prod_obj.get("moneda", "ARS")
                        })
                    st.success(f"Item {prod_obj['nombre']} agregado al remito.")
                    st.rerun()

            if st.session_state["items_remito"]:
                st.markdown("### 📋 Items en el Remito:")
                df_rem_temp = pd.DataFrame(st.session_state["items_remito"])[["codigo", "nombre", "cantidad", "precio", "moneda"]]
                st.dataframe(df_rem_temp, use_container_width=True, hide_index=True)
                
                c_del, c_proc = st.columns([1, 2])
                with c_del:
                    if st.button("🗑️ Limpiar Lista de Items"):
                        st.session_state["items_remito"] = []
                        st.rerun()
                with c_proc:
                    btn_confirmar_remito = st.button("✅ Confirmar Remito y Descontar Stock", type="primary", use_container_width=True)
                    
                if btn_confirmar_remito:
                    if not rem_cliente or not rem_localidad:
                        st.warning("Por favor completa el Nombre del Cliente y la Localidad.")
                    else:
                        nro_remito_gen = f"REM-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                        
                        for item in st.session_state["items_remito"]:
                            nuevo_stock = item["stock_actual"] - item["cantidad"]
                            supabase.table("productos").update({"stock_actual": nuevo_stock}).eq("codigo", item["codigo"]).execute()
                            
                            reg_mov = {
                                "producto_codigo": item["codigo"],
                                "producto_nombre": item["nombre"],
                                "tipo": "SALIDA / REMITO",
                                "cantidad": item["cantidad"],
                                "stock_resultante": nuevo_stock,
                                "responsable": user_actual.get("nombre"),
                                "observacion": f"Remito {nro_remito_gen} - Destino: {rem_localidad} ({rem_contacto})"
                            }
                            supabase.table("movimientos_stock").insert(reg_mov).execute()

                        st.success(f"🎉 Remito {nro_remito_gen} procesado con éxito. Stock actualizado.")
                        
                        resumen_remito = f"""
                        ==================================================
                        🏥 MENDOMEDICA - REMITO DE ENTREGA: {nro_remito_gen}
                        ==================================================
                        Fecha: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}
                        Cliente: {rem_cliente}
                        Localidad: {rem_localidad}
                        Contacto: {rem_contacto}
                        Emitido por: {user_actual.get('nombre')}
                        --------------------------------------------------
                        DETALLE DE PRODUCTOS:
                        """
                        for it in st.session_state["items_remito"]:
                            resumen_remito += f"\n• [{it['codigo']}] {it['nombre']} - Cantidad: {it['cantidad']}"
                            
                        resumen_remito += "\n\n--------------------------------------------------"
                        resumen_remito += "\nFirma Conformidad Cliente: _______________________"
                        
                        st.text_area("📄 Copia de Remito para Imprimir / Enviar:", resumen_remito, height=250)
                        
                        st.session_state["items_remito"] = []
    except Exception as e:
        st.error(f"Error en remitos: {e}")

# ==========================================
# 5. MOVIMIENTOS
# ==========================================
elif opcion == "🔄 Movimientos (Entrada / Salida)" and es_admin:
    st.title("🔄 Registro de Entradas y Salidas")
    try:
        prods_mov = supabase.table("productos").select("codigo, nombre, stock_actual").execute().data
        if prods_mov:
            dict_prods = {f"{p['codigo']} - {p['nombre']} (Stock: {p.get('stock_actual', 0)})": p for p in prods_mov}
            
            with st.form("form_mov"):
                c1, c2 = st.columns(2)
                with c1:
                    sel = st.selectbox("Seleccionar Producto:", list(dict_prods.keys()))
                    tipo = st.selectbox("Tipo de Movimiento:", ["SALIDA / VENTA", "INGRESO / COMPRA"])
                with c2:
                    cant = st.number_input("Cantidad:", min_value=1, value=1)
                    obs = st.text_input("Observación / Detalle")
                
                btn_mov = st.form_submit_button("Guardar Movimiento", use_container_width=True)
                
                if btn_mov:
                    prod_sel = dict_prods[sel]
                    stock_act = prod_sel.get("stock_actual", 0)
                    
                    if "SALIDA" in tipo:
                        if cant > stock_act:
                            st.error(f"Stock insuficiente. Disponible: {stock_act}")
                            st.stop()
                        nuevo_stock = stock_act - cant
                    else:
                        nuevo_stock = stock_act + cant
                        
                    supabase.table("productos").update({"stock_actual": nuevo_stock}).eq("codigo", prod_sel["codigo"]).execute()
                    
                    reg = {
                        "producto_codigo": prod_sel["codigo"],
                        "producto_nombre": prod_sel["nombre"],
                        "tipo": tipo,
                        "cantidad": cant,
                        "stock_resultante": nuevo_stock,
                        "responsable": user_actual.get("nombre"),
                        "observacion": obs
                    }
                    supabase.table("movimientos_stock").insert(reg).execute()
                    st.success(f"✅ Movimiento registrado. Nuevo stock: {nuevo_stock}")
    except Exception as e:
        st.error(f"Error al procesar movimiento: {e}")

# ==========================================
# 6. CARGAR PRODUCTO (CON COSTO Y ESTADO INDEPENDIENTES)
# ==========================================
elif opcion == "➕ Cargar Nuevo Producto" and es_admin:
    st.title("➕ Registrar Nuevo Producto")
    with st.form("form_alta_prod"):
        c1, c2 = st.columns(2)
        with c1:
            codigo = st.text_input("Código *")
            nombre = st.text_input("Nombre / Descripción *")
            cod_barras = st.text_input("Código de Barras / N° Serie")
            marca = st.text_input("Marca")
            categoria = st.text_input("Categoría")
            stock = st.number_input("Stock Inicial", min_value=0, value=0)
            estado = st.selectbox("Estado del Producto *", ["Stock disponible", "Servicio técnico", "Préstamo"])
            
        with c2:
            st.markdown("**Precios y Monedas Independientes:**")
            col_prec, col_mon_p = st.columns([2, 1])
            with col_prec:
                precio = st.number_input("Precio de Venta", min_value=0.0, value=0.0)
            with col_mon_p:
                moneda_precio = st.selectbox("Moneda Venta", ["ARS", "USD"])
                
            col_cost, col_mon_c = st.columns([2, 1])
            with col_cost:
                costo = st.number_input("Costo", min_value=0.0, value=0.0)
            with col_mon_c:
                moneda_costo = st.selectbox("Moneda Costo", ["ARS", "USD"])
                
            almacen = st.selectbox("Almacén / Unidad *", LISTA_ALMACENES)
            ubicacion = st.text_input("Ubicación")
            proveedor = st.text_input("Proveedor")
            cliente = st.text_input("Cliente / Responsable")
            
        btn_alta = st.form_submit_button("Guardar Producto", use_container_width=True)
        
        if btn_alta:
            if not codigo or not nombre:
                st.warning("Completa los campos obligatorios (*)")
            else:
                nuevo_prod = {
                    "codigo": codigo, 
                    "nombre": nombre, 
                    "codigo_barras": cod_barras,
                    "marca": marca, 
                    "categoria": categoria, 
                    "stock_actual": stock,
                    "precio": precio, 
                    "moneda": moneda_precio,
                    "costo": costo,
                    "moneda_costo": moneda_costo,
                    "estado": estado, 
                    "almacen": almacen, 
                    "ubicacion": ubicacion, 
                    "proveedor": proveedor, 
                    "cliente": cliente
                }
                try:
                    supabase.table("productos").insert(nuevo_prod).execute()
                    st.success(f"✅ Producto '{nombre}' registrado correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==========================================
# 7. HISTORIAL Y EXCEL
# ==========================================
elif opcion == "📄 Historial y Reporte Excel" and es_admin:
    st.title("📄 Historial de Movimientos")
    try:
        historial = supabase.table("movimientos_stock").select("*").execute().data
        if historial:
            df_hist = pd.DataFrame(historial)
            file_data, mime_type, ext = generar_excel_seguro(df_hist, nombre_hoja="Movimientos")
            
            st.download_button(
                label=f"📥 Descargar Reporte de Movimientos (.{ext.upper()})",
                data=file_data,
                file_name=f"Reporte_Movimientos_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.{ext}",
                mime=mime_type,
                type="primary"
            )
            st.markdown("---")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("No hay movimientos registrados.")
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

# ==========================================
# 8. GESTIÓN DE USUARIOS
# ==========================================
elif opcion == "👥 Gestión de Usuarios" and es_admin:
    st.title("👥 Gestión de Usuarios")
    tab1, tab2, tab3 = st.tabs(["➕ Nuevo Usuario", "👑 Administradores", "📱 Usuarios Móviles"])
    
    with tab1:
        with st.form("form_user"):
            c1, c2 = st.columns(2)
            with c1:
                nuevo_nombre = st.text_input("Nombre Completo *")
                nuevo_email = st.text_input("Correo Electrónico *").strip().lower()
                tipo_rol = st.selectbox("Rol *", ["Administrador", "Usuario Móvil"])
            with c2:
                nueva_pass = st.text_input("Contraseña *", type="password")
                sucursal = st.text_input("Sucursal / Referencia")
                
                almacenes_seleccionados = st.multiselect(
                    "🏬 Almacenes Permitidos (solo para Usuario Móvil):",
                    options=LISTA_ALMACENES,
                    default=[LISTA_ALMACENES[0]] if LISTA_ALMACENES else []
                )
                enviar_mail = st.checkbox("Enviar invitación por correo", value=True)
                
            if st.form_submit_button("Crear Usuario", use_container_width=True):
                if not nuevo_nombre or not nuevo_email or not nueva_pass:
                    st.warning("Completa todos los campos obligatorios.")
                else:
                    try:
                        tabla = "administradores" if tipo_rol == "Administrador" else "usuarios_movil"
                        datos = {"nombre": nuevo_nombre, "email": nuevo_email, "password": nueva_pass}
                        
                        if tipo_rol == "Usuario Móvil":
                            if sucursal:
                                datos["sucursal"] = sucursal
                            datos["almacenes_permitidos"] = ", ".join(almacenes_seleccionados)
                            
                        supabase.table(tabla).insert(datos).execute()
                        st.success(f"✅ Usuario registrado como {tipo_rol}.")
                        
                        if enviar_mail:
                            ok_mail, msg_mail = enviar_email_invitacion(nuevo_email, nuevo_nombre, nueva_pass, tipo_rol)
                            if ok_mail:
                                st.info("📧 Invitación enviada con éxito.")
                            else:
                                st.warning(f"Usuario guardado pero falló el correo: {msg_mail}")
                    except Exception as e:
                        if "duplicate key" in str(e) or "already exists" in str(e):
                            st.error(f"⚠️ El correo '{nuevo_email}' ya se encuentra registrado.")
                        else:
                            st.error(f"Error al registrar: {e}")

    with tab2:
        try:
            admins = supabase.table("administradores").select("*").execute().data
            if admins:
                df_a = pd.DataFrame(admins)
                if "password" in df_a.columns: df_a = df_a.drop(columns=["password"])
                st.dataframe(df_a, use_container_width=True, hide_index=True)
                
                dict_a = {f"{a.get('nombre')} ({a.get('email')})": a['id'] for a in admins if 'id' in a}
                admin_del = st.selectbox("Borrar Administrador:", list(dict_a.keys()))
                if st.button("❌ Borrar Seleccionado"):
                    supabase.table("administradores").delete().eq("id", dict_a[admin_del]).execute()
                    st.success("Administrador eliminado.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    with tab3:
        try:
            moviles = supabase.table("usuarios_movil").select("*").execute().data
            if moviles:
                df_m = pd.DataFrame(moviles)
                if "password" in df_m.columns: df_m = df_m.drop(columns=["password"])
                st.dataframe(df_m, use_container_width=True, hide_index=True)
                
                dict_m = {f"{m.get('nombre')} ({m.get('email')})": m['id'] for m in moviles if 'id' in m}
                user_del = st.selectbox("Borrar Usuario Móvil:", list(dict_m.keys()))
                if st.button("❌ Borrar Usuario Seleccionado"):
                    supabase.table("usuarios_movil").delete().eq("id", dict_m[user_del]).execute()
                    st.success("Usuario eliminado.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
