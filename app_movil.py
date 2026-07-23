import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="MendoMedica Móvil", page_icon="📱", layout="centered")

SUPABASE_URL = "https://dsnjdrgtbhwkcxkfeipl.supabase.co"
SUPABASE_KEY = "sb_secret_H1879_2HEXiHBASrVbLauA_wGvHP6kK"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# Inicializar estado de sesión
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# ==========================================
# PANTALLA DE LOGIN
# ==========================================
if not st.session_state["usuario"]:
    st.title("📱 MendoMedica Stock")
    st.subheader("Iniciar Sesión")
    
    with st.form("login_form"):
        email = st.text_input("Correo Electrónico").strip().lower()
        password = st.text_input("Contraseña", type="password").strip()
        btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if btn_login:
            if not email or not password:
                st.warning("Ingresa tu correo y contraseña.")
            else:
                try:
                    # 1. Buscar en la tabla de Usuarios Móviles
                    res_movil = supabase.table("usuarios_movil").select("*").eq("email", email).eq("password", password).execute()
                    
                    if res_movil.data:
                        user = res_movil.data[0]
                        user["rol"] = "Usuario Móvil"
                        st.session_state["usuario"] = user
                        st.rerun()
                    else:
                        # 2. Si no está en movil, buscar en Administradores
                        res_admin = supabase.table("administradores").select("*").eq("email", email).eq("password", password).execute()
                        if res_admin.data:
                            user = res_admin.data[0]
                            user["rol"] = "Administrador"
                            st.session_state["usuario"] = user
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas.")
                except Exception as err:
                    st.error(f"Error al verificar cuenta: {err}")
    st.stop()

# ==========================================
# MENÚ PRINCIPAL POST-LOGIN
# ==========================================
user_actual = st.session_state["usuario"]

st.title(f"👋 Hola, {user_actual.get('nombre', 'Usuario')}")
st.caption(f"Rol: {user_actual.get('rol', 'Usuario')} | Cuenta: {user_actual.get('email', '')}")

if st.button("🚪 Cerrar Sesión"):
    st.session_state["usuario"] = None
    st.rerun()

st.markdown("---")

# Opción de consultar / registrar movimientos desde el celular
st.subheader("📦 Consultar Inventario")
busqueda = st.text_input("🔍 Buscar producto por nombre o código:")

try:
    prods = supabase.table("productos").select("*").execute().data
    if prods:
        if busqueda:
            prods = [p for p in prods if busqueda.lower() in str(p.get("nombre", "")).lower() or busqueda.lower() in str(p.get("codigo", "")).lower()]
        
        for p in prods:
            with st.container():
                st.markdown(f"**{p.get('nombre')}** (Cód: `{p.get('codigo')}`)")
                st.write(f"Stock actual: **{p.get('stock_actual', 0)}** | Ubicación: {p.get('ubicacion', 'N/A')}")
                st.markdown("---")
    else:
        st.info("No hay productos registrados.")
except Exception as e:
    st.error(f"Error al cargar productos: {e}")
