import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv
from datetime import datetime

# 1. KONFIGURASI HALAMAN (Wajib di bagian paling atas)
st.set_page_config(page_title="SIG-DOM POS INDONESIA", page_icon="🚚", layout="wide")

# 2. LOAD KONFIGURASI & DATABASE
load_dotenv()

def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url:
        return None
    try:
        # pool_pre_ping memastikan koneksi tidak "mati" saat idle
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.error(f"Koneksi Database Gagal: {e}")
        return None

engine = get_engine()

# 3. FUNGSI AUTHENTIKASI
def check_login(username, password):
    if not engine: return None
    query = text("""
        SELECT id_kantor, username, nama_kantor, status 
        FROM users_dc 
        WHERE username = :u AND password_hash = :p AND status = 'aktif'
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"u": username, "p": password}).fetchone()
            if result:
                # Mengembalikan dictionary agar data aman diakses di session_state
                return {
                    "id_kantor": result[0],
                    "username": result[1],
                    "nama_kantor": result[2],
                    "status": result[3]
                }
    except Exception as e:
        st.error(f"Database Error: {e}")
    return None

# --- MANAJEMEN SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# --- LOGIKA TAMPILAN ---

# A. JIKA BELUM LOGIN
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=120)
        st.title("SIG-DOM Login")
        st.info("Masukkan kredensial kantor DC Anda untuk melanjutkan.")
        
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
            
            if submitted:
                user_data = check_login(u, p)
                if user_data:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user_data
                    st.rerun()
                else:
                    st.error("Kombinasi Username/Password salah.")

# B. JIKA SUDAH LOGIN
else:
    user = st.session_state['user_info']

    # --- SIDEBAR NAVIGASI ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=70)
        st.title("Navigasi")
        st.write(f"👤 User: **{user['username']}**")
        st.write(f"🏢 Kantor: **{user['nama_kantor']}**")
        st.markdown("---")
        
        menu = st.radio(
            "Pilih Menu:",
            ["🗺️ Visualisasi Zona", "📦 History Antaran Per Petugas"]
        )
        
        st.markdown("<br>"*5, unsafe_allow_html=True)
        if st.button("🚪 Keluar Aplikasi", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['user_info'] = None
            st.rerun()

    # --- ISI KONTEN BERDASARKAN MENU ---
    
    # MENU 1: ZONA ANTARAN
    if menu == "🗺️ Visualisasi Zona":
        st.header(f"Peta Zona Antaran - {user['nama_kantor']}")
        
        if engine:
            with engine.connect() as conn:
                # Query zona (pilih yang sesuai id_kantor jika data sudah banyak)
                df_zona = pd.read_sql(text("""
                    SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson 
                    FROM zona_antaran
                """), conn)

            if not df_zona.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
                colors = ['red', 'blue', 'green', 'purple', 'orange', 'cadetblue', 'darkred']
                
                for i, row in df_zona.iterrows():
                    color = colors[i % len(colors)]
                    folium.GeoJson(
                        row['geojson'],
                        style_function=lambda x, c=color: {
                            'fillColor': c, 'color': 'black', 'weight': 2, 'fillOpacity': 0.3
                        },
                        tooltip=f"Kodepos: {row['kodepos']} ({row['nama_zona']})"
                    ).add_to(m)
                
                st_folium(m, width=1100, height=600)
            else:
                st.warning("Data zona belum tersedia di database.")

    # MENU 2: HISTORY ANTARAN
    elif menu == "📦 History Antaran Per Petugas":
        st.header("History Jalur Antaran Kurir")
        
        if engine:
            with engine.connect() as conn:
                df_petugas = pd.read_sql(text("SELECT id_petugas, nama_petugas FROM petugas_antaran"), conn)
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                p_list = df_petugas['nama_petugas'].tolist() if not df_petugas.empty else ["Data Petugas Kosong"]
                p_pilih = st.selectbox("Pilih Petugas:", p_list)
            with col_f2:
                t_pilih = st.date_input("Pilih Tanggal", datetime.now())

            # Query History berdasarkan waktu_kejadian
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
                st.success(f"Ditemukan {len(df_hist)} data antaran.")
                
                c_map, c_data = st.columns([2, 1])
                with c_map:
                    m_hist = folium.Map(location=[df_hist['lat'].mean(), df_hist['lon'].mean()], zoom_start=14)
                    points = []
                    for _, row in df_hist.iterrows():
                        loc = [row['lat'], row['lon']]
                        points.append(loc)
                        
                        ic = 'green' if row['status_antaran'] == 'DELIVERED' else 'orange'
                        folium.Marker(
                            loc,
                            popup=f"Resi: {row['connote']}<br>Jam: {row['waktu_kejadian'].strftime('%H:%M')}",
                            icon=folium.Icon(color=ic, icon='bicycle', prefix='fa')
                        ).add_to(m_hist)
                    
                    if len(points) > 1:
                        folium.PolyLine(points, color="blue", weight=3, opacity=0.6).add_to(m_hist)
                    
                    st_folium(m_hist, width="100%", height=500)
                
                with c_data:
                    st.write("📊 **Urutan Antaran**")
                    st.dataframe(df_hist[['waktu_kejadian', 'connote', 'status_antaran']], use_container_width=True)
            else:
                st.info(f"Tidak ada data antaran untuk {p_pilih} pada tanggal {t_pilih}")

# FOOTER
st.markdown("---")
st.caption(f"SIG-DOM v1.0 | PT Pos Indonesia | {datetime.now().year}")
