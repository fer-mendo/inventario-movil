import streamlit as st
from supabase import create_client, Client

# Configuración de la página para celulares
st.set_page_config(page_title="Consulta de Stock", page_icon="📦", layout="centered")

SUPABASE_URL = "https://dsnjdrgtbhwkcxkfeipl.supabase.co"
SUPABASE_KEY = "sb_secret_w1UfLTj-U7oyzedV1Jy0OQ_OybCcdSy"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📦 Consulta de Stock Remota")
st.write("Busca productos en tiempo real desde tu celular.")

# Sistema de Login Simple en la Web
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    with st.form("login_form"):
        email = st.text_input("Correo Electrónico")
        password = st.text_input("Contraseña", type="password")
        boton_login = st.form_submit_button("Iniciar Sesión")
        
        if boton_login:
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    # Verificar que el usuario exista en perfiles
                    query = supabase.table("perfiles").select("rol").eq("id", res.user.id).execute()
                    if query.data:
                        st.session_state['autenticado'] = True
                        st.session_state['user_email'] = email
                        st.rerun()
            except Exception:
                st.error("❌ Credenciales incorrectas.")
else:
    st.success(f"Conectado como: {st.session_state['user_email']}")
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

    # --- BUSCADOR EN TIEMPO REAL ---
    criterio = st.text_input("🔍 Busca por Nombre o Código de Barras:")
    
    try:
        # Traer los productos de Supabase
        query = supabase.table("productos").select("codigo, codigo_barras, nombre, precio, stock_actual, ubicacion, responsable").execute()
        productos = query.data
        
        if productos:
            # Filtrar según lo que escriba el usuario en el celular
            filtrados = [
                p for p in productos 
                if criterio.lower() in str(p.get('nombre', '')).lower() 
                or criterio in str(p.get('codigo_barras', ''))
                or criterio in str(p.get('codigo', ''))
            ]
            
            if filtrados:
                for prod in filtrados:
                    # Crear una tarjeta visual para cada producto (Ideal para celulares)
                    with st.container(border=True):
                        st.subheader(f"🔹 {prod.get('nombre')}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(label="Stock Actual", value=prod.get('stock_actual'))
                            st.write(f"**Ubicación:** {prod.get('ubicacion') or 'Sin asignar'}")
                        with col2:
                            st.metric(label="Precio", value=f"${prod.get('precio'):.2f}")
                            st.write(f"**Responsable:** {prod.get('responsable') or 'Sin asignar'}")
            else:
                st.info("No se encontraron productos que coincidan con la búsqueda.")
        else:
            st.warning("No hay productos registrados en el inventario.")
            
    except Exception as e:
        st.error(f"Error de conexión: {e}")
