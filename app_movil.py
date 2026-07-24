import streamlit as st
from supabase import create_client, Client
import pandas as pd
import io
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración de página optimizada para PC / Escritorio (Ancho completo)
st.set_page_config(page_title="MendoMedica - Gestión de Inventario", page_icon="🏥", layout="wide")

# Configuración de Supabase
SUPABASE_URL = "https://dsnjdrgtbhwkcxkfeipl.supabase.co"
SUPABASE_KEY = "sb_secret_H1879_2HEXiHBASrVbLauA_wGvHP6kK"

# Configuración de Servidor SMTP para envío de correos
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "f.monneretscg@gmail.com"

# Manejo seguro de la contraseña SMTP desde Secrets o Variable
try:
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except Exception:
    SMTP_PASSWORD = "lsmw ulmc efos muaj"  # Tu contraseña de aplicación de 16 caracteres sin espacios

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Error al conectar con Supabase: {e}")
    st.stop()

# Función para enviar correo de invitación
def enviar_email_invitacion(email_destino, nombre_usuario, password, rol):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = email_destino
        msg['Subject'] = "Invitación al Sistema de Inventario - MendoMedica"

        cuerpo = f"""
        Hola {nombre_usuario},

        Se ha creado tu cuenta con el rol de **{rol}** en el Sistema de Gestión de Inventario de MendoMedica.

        Tus credenciales de acceso son:
        -------------------------------------------
        Correo: {email_destino}
        Contraseña: {password}
        -------------------------------------------

        Puedes acceder al sistema a través de la plataforma web.

        Por razones de seguridad, te sugerimos cambiar tu contraseña al ingresar.

        Atentamente,
        Equipo MendoMedica
        """
        msg.attach(MIMEText(cuerpo, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado correctamente."
    except Exception as e:
        return False, str(e)

if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# ==========================================
# 1. PANTALLA DE INICIO DE SESIÓN (LOGIN)
# ==========================================
if not st.session_state["usuario"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏥 MendoMedica - Inventario")
        st.subheader("Acceso al Sistema")
        
        with st.form("form_login_pc"):
            email = st.text_input("Correo Electrónico").strip().lower()
            password = st.text_input("Contraseña", type="password").strip()
            btn_login = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            
            if btn_login:
                if not email or not password:
                    st.warning("Ingresa tu correo y contraseña.")
                else:
                    user_encontrado = None
                    
                    # 1. Buscar en Administradores
                    try:
                        res_admin = supabase.table("administradores").select("*").eq("email", email).eq("password", password).execute()
                        if res_admin.data:
                            user_encontrado = res_admin.data[0]
                            user_encontrado["rol"] = "Administrador"
                    except Exception:
                        pass

                    # 2. Buscar en Usuarios Móviles / Estándar
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
                        st.error("❌ Credenciales incorrectas. Verifica correo o contraseña.")
    st.stop()

# ==========================================
# 2. NAVEGACIÓN Y PANEL LATERAL (PC)
# ==========================================
user_actual = st.session_state["usuario"]
es_admin = user_actual.get("rol") == "Administrador"

st.sidebar.title("🏥 MendoMedica")
st.sidebar.write(f"👤 **{user_actual.get('nombre', 'Usuario')}**")
st.sidebar.caption(f"Rol: **{user_actual.get('rol')}**")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state["usuario"] = None
    st.rerun()

st.sidebar.markdown("---")

if es_admin:
    opciones_menu = [
        "📦 Control de Inventario", 
        "🔄 Movimientos (Entrada / Salida)", 
        "➕ Cargar Nuevo Producto", 
        "📄 Historial y Reporte Excel",
        "👥 Gestión de Usuarios"
    ]
else:
    opciones_menu = ["📦 Control de Inventario"]

opcion = st.sidebar.radio("Navegación:", opciones_menu)

# ==========================================
# 3. CONTROL DE INVENTARIO (TABLA COMPLETA / ADAPTADA POR ROL)
# ==========================================
if opcion == "📦 Control de Inventario":
    st.title("📦 Control de Inventario y Stock")
    
    col_busq, col_alm = st.columns([2, 1])
    with col_busq:
        busqueda = st.text_input("🔍 Buscar por Nombre, Código, Cód. Barras/Serie, Marca o Categoría:")
    with col_alm:
        almacen_sel = st.selectbox("🏬 Almacén / Unidad de Negocio:", ["Todos", "General", "Mendoza", "San Juan", "Endoscopia", "Quirófano"])
    
    try:
        prods = supabase.table("productos").select("*").execute().data
        if prods:
            df_prods = pd.DataFrame(prods)
            
            # 1. Filtrar por Almacén si no es 'Todos'
            if almacen_sel != "Todos" and "almacen" in df_prods.columns:
                df_prods = df_prods[df_prods['almacen'].astype(str).str.lower() == almacen_sel.lower()]

            # 2. Búsqueda combinada
            if busqueda:
                b = busqueda.lower()
                condicion = (
                    df_prods['nombre'].astype(str).str.lower().str.contains(b) |
                    df_prods['codigo'].astype(str).str.lower().str.contains(b) |
                    df_prods.get('codigo_barras', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b) |
                    df_prods.get('marca', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b) |
                    df_prods.get('categoria', pd.Series(['']*len(df_prods))).astype(str).str.lower().str.contains(b)
                )
                df_prods = df_prods[condicion]

            # 3. Definir columnas según el ROL (Ocultar Cliente y Proveedor para Usuarios Móviles)
            if es_admin:
                cols_deseadas = ["codigo", "codigo_barras", "nombre", "marca", "categoria", "stock_actual", "precio", "almacen", "ubicacion", "proveedor", "cliente"]
            else:
                cols_deseadas = ["codigo", "codigo_barras", "nombre", "marca", "categoria", "stock_actual", "precio", "almacen", "ubicacion"]

            cols_existentes = [c for c in cols_deseadas if c in df_prods.columns]
            df_prods = df_prods[cols_existentes]
            
            # Renombrar columnas para la interfaz visual
            nombres_cols = {
                "codigo": "Código",
                "codigo_barras": "Cód. Barras / N° Serie",
                "nombre": "Nombre / Descripción",
                "marca": "Marca",
                "categoria": "Categoría",
                "stock_actual": "Stock Actual",
                "precio": "Precio ($)",
                "almacen": "Almacén / Unidad",
                "ubicacion": "Ubicación",
                "proveedor": "Proveedor",
                "cliente": "Cliente / Resp."
            }
            df_prods = df_prods.rename(columns=nombres_cols)
            
            st.dataframe(df_prods, use_container_width=True, hide_index=True)
            st.caption(f"Mostrando {len(df_prods)} productos.")
        else:
            st.info("No hay productos registrados en la base de datos.")
    except Exception as e:
        st.error(f"Error al obtener el inventario: {e}")

# ==========================================
# 4. REGISTRAR MOVIMIENTOS (SOLO ADMIN)
# ==========================================
elif opcion == "🔄 Movimientos (Entrada / Salida)" and es_admin:
    st.title("🔄 Registro de Entradas y Salidas de Stock")
    
    try:
        prods = supabase.table("productos").select("codigo, nombre, stock_actual").execute().data
        if prods:
            dict_prods = {f"{p['codigo']} - {p['nombre']} (Stock: {p.get('stock_actual', 0)})": p for p in prods}
            
            with st.form("form_mov_pc"):
                c1, c2 = st.columns(2)
                with c1:
                    sel = st.selectbox("Seleccionar Producto:", list(dict_prods.keys()))
                    tipo = st.selectbox("Tipo de Movimiento:", ["SALIDA / VENTA", "INGRESO / COMPRA"])
                with c2:
                    cant = st.number_input("Cantidad:", min_value=1, value=1)
                    obs = st.text_input("Observación / Detalle / Remito")
                
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
                    st.success(f"✅ Movimiento guardado correctamente. Nuevo stock de {prod_sel['nombre']}: {nuevo_stock}")
    except Exception as e:
        st.error(f"Error al procesar el movimiento: {e}")

# ==========================================
# 5. CARGAR NUEVO PRODUCTO (SOLO ADMIN)
# ==========================================
elif opcion == "➕ Cargar Nuevo Producto" and es_admin:
    st.title("➕ Registrar Nuevo Producto")
    
    with st.form("form_alta_prod"):
        c1, c2 = st.columns(2)
        with c1:
            codigo = st.text_input("Código de Producto *")
            nombre = st.text_input("Nombre / Descripción *")
            cod_barras = st.text_input("Código de Barras / N° Serie (Alfanumérico)")
            marca = st.text_input("Marca")
            categoria = st.text_input("Categoría (Ej: Endoscopia, Insumos, etc.)")
            stock = st.number_input("Stock Inicial", min_value=0, value=0)
        with c2:
            precio = st.number_input("Precio ($)", min_value=0.0, value=0.0)
            almacen = st.selectbox("Almacén / Unidad de Negocio *", ["General", "Mendoza", "San Juan", "Endoscopia", "Quirófano"])
            ubicacion = st.text_input("Ubicación en Almacén")
            proveedor = st.text_input("Proveedor")
            cliente = st.text_input("Cliente / Responsable")
            
        btn_alta = st.form_submit_button("Guardar Producto", use_container_width=True)
        
        if btn_alta:
            if not codigo or not nombre:
                st.warning("El código y la descripción son campos obligatorios (*)")
            else:
                nuevo_prod = {
                    "codigo": codigo,
                    "nombre": nombre,
                    "codigo_barras": cod_barras,
                    "marca": marca,
                    "categoria": categoria,
                    "stock_actual": stock,
                    "precio": precio,
                    "almacen": almacen,
                    "ubicacion": ubicacion,
                    "proveedor": proveedor,
                    "cliente": cliente
                }
                try:
                    supabase.table("productos").insert(nuevo_prod).execute()
                    st.success(f"✅ Producto '{nombre}' registrado exitosamente.")
                except Exception as e:
                    st.error(f"Error al guardar producto: {e}")

# ==========================================
# 6. HISTORIAL Y REPORTE EXCEL (SOLO ADMIN)
# ==========================================
elif opcion == "📄 Historial y Reporte Excel" and es_admin:
    st.title("📄 Historial de Movimientos de Stock")
    
    try:
        historial = supabase.table("movimientos_stock").select("*").execute().data
        if historial:
            df_hist = pd.DataFrame(historial)
            
            cols_orden = [c for c in ["id", "created_at", "tipo", "producto_codigo", "producto_nombre", "cantidad", "stock_resultante", "responsable", "observacion"] if c in df_hist.columns]
            df_hist = df_hist[cols_orden]

            try:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_hist.to_excel(writer, index=False, sheet_name='Historial_Movimientos')
                excel_bytes = output.getvalue()

                st.download_button(
                    label="📥 Descargar Reporte en Excel (.xlsx)",
                    data=excel_bytes,
                    file_name=f"Reporte_Movimientos_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            except ModuleNotFoundError:
                st.warning("⚠️ Exportando en formato CSV alternativo:")
                csv_bytes = df_hist.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Reporte en CSV",
                    data=csv_bytes,
                    file_name=f"Reporte_Movimientos_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    type="primary"
                )

            st.markdown("---")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("No existen movimientos registrados aún.")
    except Exception as e:
        st.error(f"Error al consultar historial: {e}")

# ==========================================
# 7. GESTIÓN DE USUARIOS Y ENVÍO DE MAILS (SOLO ADMIN)
# ==========================================
elif opcion == "👥 Gestión de Usuarios" and es_admin:
    st.title("👥 Gestión de Usuarios y Administradores")
    
    tab1, tab2, tab3 = st.tabs(["➕ Registrar Nuevo Usuario", "👑 Administradores", "📱 Usuarios Móviles"])
    
    # --- PESTAÑA 1: CREAR USUARIO Y ENVIAR MAIL ---
    with tab1:
        st.subheader("Registrar Nuevo Administrador / Usuario Móvil")
        with st.form("form_alta_usuario"):
            c1, c2 = st.columns(2)
            with c1:
                nuevo_nombre = st.text_input("Nombre Completo *")
                nuevo_email = st.text_input("Correo Electrónico *").strip().lower()
                tipo_rol = st.selectbox("Rol del Usuario *", ["Administrador", "Usuario Móvil"])
            with c2:
                nueva_pass = st.text_input("Contraseña de Acceso *", type="password")
                sucursal = st.text_input("Sucursal / Sede (Opcional)")
                enviar_mail = st.checkbox("Enviar correo de invitación con datos de acceso", value=True)
                
            btn_crear_user = st.form_submit_button("Crear Usuario y Enviar Invitación", use_container_width=True)
            
            if btn_crear_user:
                if not nuevo_nombre or not nuevo_email or not nueva_pass:
                    st.warning("Completa los campos obligatorios (*)")
                else:
                    try:
                        tabla_destino = "administradores" if tipo_rol == "Administrador" else "usuarios_movil"
                        datos_user = {
                            "nombre": nuevo_nombre,
                            "email": nuevo_email,
                            "password": nueva_pass
                        }
                        if tipo_rol == "Usuario Móvil" and sucursal:
                            datos_user["sucursal"] = sucursal
                            
                        supabase.table(tabla_destino).insert(datos_user).execute()
                        st.success(f"✅ Usuario {nuevo_nombre} registrado exitosamente como {tipo_rol}.")
                        
                        if enviar_mail:
                            ok_mail, msg_mail = enviar_email_invitacion(nuevo_email, nuevo_nombre, nueva_pass, tipo_rol)
                            if ok_mail:
                                st.info("📧 Correo de invitación enviado correctamente.")
                            else:
                                st.warning(f"Usuario registrado, pero no se pudo enviar el correo: {msg_mail}")
                    except Exception as e:
                        st.error(f"Error al registrar usuario: {e}")

    # --- PESTAÑA 2: LISTA Y ELIMINACIÓN DE ADMINISTRADORES ---
    with tab2:
        st.subheader("Lista de Administradores")
        try:
            admins = supabase.table("administradores").select("*").execute().data
            if admins:
                df_admins = pd.DataFrame(admins)
                if "password" in df_admins.columns:
                    df_admins = df_admins.drop(columns=["password"])
                    
                st.dataframe(df_admins, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.caption("🗑️ **Eliminar Administrador**")
                
                dict_admins = {f"{a.get('nombre', 'Admin')} ({a.get('email', 'Sin Email')})": a['id'] for a in admins if 'id' in a}
                if dict_admins:
                    admin_a_borrar = st.selectbox("Seleccionar Administrador a borrar:", list(dict_admins.keys()))
                    
                    if st.button("❌ Borrar Administrador Seleccionado"):
                        id_borrar = dict_admins[admin_a_borrar]
                        supabase.table("administradores").delete().eq("id", id_borrar).execute()
                        st.success("✅ Administrador eliminado con éxito.")
                        st.rerun()
            else:
                st.info("No hay administradores registrados.")
        except Exception as e:
            st.error(f"Error al cargar administradores: {e}")

    # --- PESTAÑA 3: LISTA Y ELIMINACIÓN DE USUARIOS MÓVILES ---
    with tab3:
        st.subheader("Lista de Usuarios Móviles")
        try:
            moviles = supabase.table("usuarios_movil").select("*").execute().data
            if moviles:
                df_moviles = pd.DataFrame(moviles)
                if "password" in df_moviles.columns:
                    df_moviles = df_moviles.drop(columns=["password"])
                    
                st.dataframe(df_moviles, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.caption("🗑️ **Eliminar Usuario Móvil**")
                
                dict_moviles = {f"{m.get('nombre', 'Usuario')} ({m.get('email', 'Sin Email')})": m['id'] for m in moviles if 'id' in m}
                if dict_moviles:
                    user_a_borrar = st.selectbox("Seleccionar Usuario a borrar:", list(dict_moviles.keys()))
                    
                    if st.button("❌ Borrar Usuario Seleccionado"):
                        id_borrar_m = dict_moviles[user_a_borrar]
                        supabase.table("usuarios_movil").delete().eq("id", id_borrar_m).execute()
                        st.success("✅ Usuario eliminado con éxito.")
                        st.rerun()
            else:
                st.info("No hay usuarios móviles registrados.")
        except Exception as e:
            st.error(f"Error al cargar usuarios móviles: {e}")
