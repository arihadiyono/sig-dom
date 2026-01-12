import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from datetime import datetime

# 1. PAGE CONFIG
st.set_page_config(page_title="SIG-DOM POS", page_icon="🚚", layout="wide")

# 2. DATABASE ENGINE (DENGAN RE-TRY LOGIC)
@st.cache_resource
def get_engine():
    if "DB_URL" not in st.secrets:
        st.error("Secrets DB_URL belum diatur!")
        return None
    try:
        # Menggunakan pool_pre_ping agar jika koneksi drop, engine akan mencoba lagi
        return create_engine(
            st.secrets["DB_URL"],
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=0
        )
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return None

engine = get_engine()

# 3. FUNGSI AUTH
def check_login(u, p):
    if not engine: return None
    try:
        query = text("""
            SELECT id_kantor, username, nama_kantor 
            FROM users_dc 
            WHERE username = :u AND password_hash = :p AND status = 'aktif'
        """)
        with engine.connect() as conn:
            return conn.execute(query, {"u": u, "p": p}).fetchone()
    except Exception as e:
        st.error(f"Gagal Query Login: {e}")
        return None

# --- APP FLOW ---
if 'auth' not in st.session_state:
    st.session_state.auth = None

if not st.session_state.auth:
    # --- HALAMAN LOGIN ---
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=120)
        st.title("SIG-DOM Login")
        with st.form("login"):
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                user_data = check_login(u_in, p_in)
                if user_data:
                    st.session_state.auth = user_data
                    st.rerun()
                else:
                    st.error("❌ Username/Password salah atau akun tidak aktif.")
else:
    # --- DASHBOARD ---
    user = st.session_state.auth
    st.sidebar.title("🚚 SIG-DOM POS")
    st.sidebar.success(f"📍 {user[2]}") # nama_kantor
    
    menu = st.sidebar.radio("Navigasi", ["Peta Zona", "History Antaran"])
    
    if st.sidebar.button("Keluar"):
        st.session_state.auth = None
        st.rerun()

    if menu == "Peta Zona":
        st.header(f"Wilayah Antaran {user[2]}")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geo FROM zona_antaran"), conn)
            
            if not df.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
                for _, row in df.iterrows():
                    folium.GeoJson(row['geo'], tooltip=row['nama_zona']).add_to(m)
                st_folium(m, width="100%", height=500)
            else:
                st.warning("Belum ada data zona.")
        except Exception as e:
            st.error(f"Peta gagal dimuat: {e}")

st.markdown("---")
st.caption(f"SIG-DOM v1.6 | Mumbai Region | {datetime.now().year}")
