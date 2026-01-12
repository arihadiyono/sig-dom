import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv
from datetime import datetime

# 1. KONFIGURASI HALAMAN (Harus di baris pertama setelah import)
st.set_page_config(page_title="SIG-DOM POS INDONESIA", page_icon="🚚", layout="wide")

# 2. LOAD KONFIGURASI & KONEKSI DATABASE
load_dotenv()

@st.cache_resource
def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url:
        return None
    try:
        # pool_pre_ping=True sangat penting untuk aplikasi cloud agar koneksi tidak putus
        return create_engine(db_url, pool_pre_ping=True, disconnection_handling=True)
    except Exception as e:
        return None

engine = get_engine()

# 3. FUNGSI AUTHENTIKASI (DENGAN FEEDBACK ERROR)
def check_login(username, password):
    if engine is None:
        st.error("Koneksi Database Gagal. Periksa DB_URL di Secrets Streamlit.")
        return None
    
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
            else:
                return "AUTH_FAILED"
    except Exception as e:
        st.error(f"Error Database: {str(e)}")
        return None

# --- INISIALISASI SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# --- LOGIKA TAMPILAN ---

# A. HALAMAN LOGIN
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=120)
        st.title("SIG-DOM Login")
        st.info("Silakan login untuk mengakses dashboard DC.")
        
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
            
            if submitted:
                if not u or not p:
                    st.warning("Mohon isi username dan password.")
                else:
                    res = check_login(u, p)
                    if res == "AUTH_FAILED":
                        st.error("❌ Username atau Password salah/Akun nonaktif.")
                    elif res:
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = res
                        st.success("✅ Berhasil! Mengalihkan...")
                        st.rerun()

# B. HALAMAN DASHBOARD (JIKA SUDAH LOGIN)
else:
    user = st.session_state['user_info']

    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=80)
        st.title("SIG-DOM")
        st.success(f"📍 {user['nama_kantor']}")
        st.write(f"👤 User: {user['username']}")
        st.markdown("---")
        
        menu = st.radio(
            "Pilih Menu:",
            ["🗺️ Visualisasi Zona", "📦 History Antaran Per Petugas"]
        )
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['user_info'] = None
            st.rerun()

    # --- KONTEN MENU ---
    
    # MENU 1: ZONA
    if menu == "🗺️ Visualisasi Zona":
        st.header(f"Peta Zona Antaran")
        if engine:
            try:
                with engine.connect() as conn:
                    df_zona = pd.read_sql(text("SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson FROM zona_antaran"), conn)
                
                if not df_zona.empty:
                    m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
                    colors = ['red', 'blue', 'green', 'purple', 'orange', 'cadetblue', 'darkred']
                    for i, row in df_zona.iterrows():
                        folium.GeoJson(
                            row['geojson'],
                            style_function=lambda x, c=colors[i % len(colors)]: {
                                'fillColor': c, 'color': 'black', 'weight': 2, 'fillOpacity': 0.3
                            },
                            tooltip=f"{row['kodepos']} - {row['nama_zona']}"
                        ).add_to(m)
                    st_folium(m, width="100%", height=600)
                else:
                    st.info("Data zona belum tersedia.")
            except Exception as e:
                st.error(f"Gagal memuat peta: {e}")

    # MENU 2: HISTORY
    elif menu == "📦 History Antaran Per Petugas":
        st.header("History Jalur Antaran")
        if engine:
            try:
                with engine.connect() as conn:
                    df_petugas = pd.read_sql(text("SELECT id_petugas, nama_petugas FROM petugas_antaran"), conn)
                
                c1, c2 = st.columns(2)
                with c1:
                    p_pilih = st.selectbox("Pilih Petugas:", df_petugas['nama_petugas'].tolist() if not df_petugas.empty else ["Data Kosong"])
                with c2:
                    t_pilih = st.date_input("Tanggal", datetime.now())

                query_hist = text("""
                    SELECT t.connote, t.penerima, t.status_antaran, t.waktu_kejadian,
                           ST_Y(t.geom) as lat, ST_X(t.geom) as lon
                    FROM titikan_antaran t
                    JOIN petugas_antaran p ON t.id_petugas = p.id_petugas
                    WHERE p.nama_petugas = :n AND DATE(t.waktu_kejadian) = :d
                    ORDER BY t.waktu_kejadian ASC
                """)

                with engine.connect() as conn:
                    df_hist = pd.read_sql(query_hist, conn, params={"n": p_pilih, "d": t_pilih})

                if not df_hist.empty:
                    col_map, col_data = st.columns([2, 1])
                    with col_map:
                        m_hist = folium.Map(location=[df_hist['lat'].iloc[0], df_hist['lon'].iloc[0]], zoom_start=14)
                        points = []
                        for _, row in df_hist.iterrows():
                            points.append([row['lat'], row['lon']])
                            folium.Marker(
                                [row['lat'], row['lon']],
                                popup=f"{row['connote']} - {row['waktu_kejadian'].strftime('%H:%M')}",
                                icon=folium.Icon(color='green' if row['status_antaran'] == 'DELIVERED' else 'orange', icon='bicycle', prefix='fa')
                            ).add_to(m_hist)
                        if len(points) > 1:
                            folium.PolyLine(points, color="blue", weight=3).add_to(m_hist)
                        st_folium(m_hist, width="100%", height=500)
                    with col_data:
                        st.dataframe(df_hist[['waktu_kejadian', 'connote', 'status_antaran']], use_container_width=True)
                else:
                    st.info("Tidak ada data antaran.")
            except Exception as e:
                st.error(f"Gagal memuat history: {e}")

# FOOTER
st.markdown("---")
st.caption(f"SIG-DOM v1.1 | PT Pos Indonesia | {datetime.now().year}")
