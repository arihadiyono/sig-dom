import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv
from datetime import datetime

# 1. PAGE CONFIG
st.set_page_config(page_title="SIG-DOM POS", page_icon="🚚", layout="wide")

# 2. DATABASE ENGINE
load_dotenv()

@st.cache_resource
def get_engine():
    url = os.getenv("DB_URL")
    if not url:
        st.error("DB_URL tidak ditemukan di Secrets!")
        return None
    try:
        # Menambahkan timeout dan pool_pre_ping untuk stabilitas Cloud
        return create_engine(
            url, 
            pool_pre_ping=True, 
            connect_args={'connect_timeout': 10}
        )
    except Exception as e:
        st.error(f"Gagal inisialisasi Engine: {e}")
        return None

engine = get_engine()

# 3. AUTH FUNCTION
def check_login(username, password):
    if not engine: return None
    # Pastikan nama tabel dan kolom sesuai dengan di Supabase
    query = text("""
        SELECT id_kantor, username, nama_kantor, status 
        FROM users_dc 
        WHERE username = :u AND password_hash = :p AND status = 'aktif'
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"u": username, "p": password}).fetchone()
            if result:
                return {
                    "id_kantor": result[0],
                    "username": result[1],
                    "nama_kantor": result[2],
                    "status": result[3]
                }
            return "FAILED"
    except Exception as e:
        # Menampilkan detail error asli ke UI agar mudah didebug
        st.error(f"Koneksi Database Gagal: {str(e)}")
        return None

# --- APP LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # HALAMAN LOGIN
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=120)
        st.title("SIG-DOM Login")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                res = check_login(u, p)
                if res == "FAILED":
                    st.error("Username/Password salah.")
                elif res:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = res
                    st.rerun()
else:
    # HALAMAN UTAMA (DASHBOARD)
    user = st.session_state['user_info']
    
    with st.sidebar:
        st.title("SIG-DOM")
        st.success(f"📍 {user['nama_kantor']}")
        menu = st.radio("Menu:", ["🗺️ Zona Antaran", "📦 History Antaran"])
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    if menu == "🗺️ Zona Antaran":
        st.header("Visualisasi Zona Antaran")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson FROM zona_antaran"), conn)
            
            if not df.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
                for i, row in df.iterrows():
                    folium.GeoJson(row['geojson'], tooltip=row['kodepos']).add_to(m)
                st_folium(m, width="100%", height=600)
            else:
                st.info("Data zona belum tersedia.")
        except Exception as e:
            st.error(f"Gagal memuat data zona: {e}")

    elif menu == "📦 History Antaran":
        st.header("History Antaran Petugas")
        # Tambahkan filter tanggal dan petugas di sini (seperti versi sebelumnya)
        st.info("Pilih petugas dan tanggal untuk melihat rute.")

st.markdown("---")
st.caption(f"SIG-DOM v1.2 | {datetime.now().year}")
