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
    SMTP_PASSWORD = "lsmwulmcefosmuaj"

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
        return False, "Falta configurar SMTP_PASSWORD en los Secrets de Streamlit."
    try:
        URL_APP = "https://inventario-movil-keqyrhd8mr25qkng7tdajx.streamlit.app"

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

if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# ==========================================
# 1. LOGIN
# ==========================================
if not st.session_state["usuario"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏥 MendoMedica")
        st.subheader("Acceso al Sistema")
        
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
# 2. NAVEGACIÓN Y PANEL LATERAL
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
# 3. CONTROL DE INVENTARIO
# ==========================================
if opcion == "📦 Control de Inventario":
    st.title("📦 Control de Inventario y Stock")
    
    col_busq, col_alm = st.columns([2, 1])
    with col_busq:
        busqueda = st.text_input("🔍 Buscar por Nombre, Código, Cód. Barras, Marca o Categoría:")
    with col_alm:
        almacen_sel = st.selectbox("🏬 Almacén / Unidad:", ["Todos", "General", "Mendoza", "San Juan", "Endoscopia", "Quirófano"])
    
    try:
        prods = supabase.table("productos").select("*").execute().data
        if prods:
            df_prods = pd.DataFrame(prods)
            
            if almacen_sel != "Todos" and "almacen" in df_prods.columns:
                df_prods = df_prods[df_prods['almacen'].astype(str).str.lower() == almacen_sel.lower()]

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

            # Seleccionar columnas a mostrar según rol
            if es_admin:
                cols_deseadas = ["codigo", "codigo_barras", "nombre", "marca", "categoria", "stock_actual", "precio", "almacen", "ubicacion", "proveedor", "cliente"]
            else:
                cols_deseadas = ["codigo", "codigo_barras", "nombre", "marca", "categoria", "stock_actual", "precio", "almacen", "ubicacion"]

            cols_existentes = [c for c in cols_deseadas if c in df_prods.columns]
            df_prods = df_prods[cols_existentes]
            
            st.dataframe(df_prods, use_container_width=True, hide_index=True)
            st.caption(f"Mostrando {len(df_prods)} productos.")

            # BOTÓN DE RESPALDO DE INVENTARIO PARA ADMIN
            if es_admin:
                st.markdown("---")
                try:
                    df_backup = pd.DataFrame(prods)
                    output_backup = io.BytesIO()
                    with pd.ExcelWriter(output_backup, engine='openpyxl') as writer:
                        df_backup.to_excel(writer, index=False, sheet_name='Inventario_Completo')
                        
                    st.download_button(
                        label="💾 Descargar Respaldo Completo de Inventario (.xlsx)",
                        data=output_backup.getvalue(),
                        file_name=f"Backup_Inventario_MendoMedica_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.warning(f"No se pudo generar el archivo Excel de respaldo: {e}")
        else:
            st.info("No hay productos registrados.")
    except Exception as e:
        st.error(f"Error al obtener el inventario: {e}")

# ==========================================
# 4. MOVIMIENTOS
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
# 5. CARGAR PRODUCTO
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
        with c2:
            precio = st.number_input("Precio ($)", min_value=0.0, value=0.0)
            almacen = st.selectbox("Almacén / Unidad *", ["General", "Mendoza", "San Juan", "Endoscopia", "Quirófano"])
            ubicacion = st.text_input("Ubicación")
            proveedor = st.text_input("Proveedor")
            cliente = st.text_input("Cliente / Responsable")
            
        btn_alta = st.form_submit_button("Guardar Producto", use_container_width=True)
        
        if btn_alta:
            if not codigo or not nombre:
                st.warning("Completa los campos obligatorios (*)")
            else:
                nuevo_prod = {
                    "codigo": codigo, "nombre": nombre, "codigo_barras": cod_barras,
                    "marca": marca, "categoria": categoria, "stock_actual": stock,
                    "precio": precio, "almacen": almacen, "ubicacion": ubicacion,
                    "proveedor": proveedor, "cliente": cliente
                }
                try:
                    supabase.table("productos").insert(nuevo_prod).execute()
                    st.success(f"✅ Producto '{nombre}' registrado.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==========================================
# 6. HISTORIAL Y EXCEL
# ==========================================
elif opcion == "📄 Historial y Reporte Excel" and es_admin:
    st.title("📄 Historial de Movimientos")
    try:
        historial = supabase.table("movimientos_stock").select("*").execute().data
        if historial:
            df_hist = pd.DataFrame(historial)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_hist.to_excel(writer, index=False, sheet_name='Movimientos')
            
            st.download_button(
                label="📥 Descargar Reporte de Movimientos en Excel (.xlsx)",
                data=output.getvalue(),
                file_name=f"Reporte_Movimientos_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            st.markdown("---")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("No hay movimientos registrados.")
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

# ==========================================
# 7. GESTIÓN DE USUARIOS
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
                sucursal = st.text_input("Sucursal")
                enviar_mail = st.checkbox("Enviar invitación por correo", value=True)
                
            if st.form_submit_button("Crear Usuario", use_container_width=True):
                if not nuevo_nombre or not nuevo_email or not nueva_pass:
                    st.warning("Completa todos los campos obligatorios.")
                else:
                    try:
                        tabla = "administradores" if tipo_rol == "Administrador" else "usuarios_movil"
                        datos = {"nombre": nuevo_nombre, "email": nuevo_email, "password": nueva_pass}
                        if tipo_rol == "Usuario Móvil" and sucursal:
                            datos["sucursal"] = sucursal
                            
                        supabase.table(tabla).insert(datos).execute()
                        st.success(f"✅ Usuario registrado como {tipo_rol}.")
                        
                        if enviar_mail:
                            ok_mail, msg_mail = enviar_email_invitacion(nuevo_email, nuevo_nombre, nueva_pass, tipo_rol)
                            if ok_mail:
                                st.info("📧 Invitación enviada con éxito.")
                            else:
                                st.warning(f"Usuario guardado pero falló el correo: {msg_mail}")
                    except Exception as e:
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
