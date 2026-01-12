import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
from datetime import datetime

# --- CONFIG & ENGINE ---
st.set_page_config(page_title="SIG-DOM POS", layout="wide")

@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)

engine = get_engine()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- FUNGSI LOGIN ---
def login_ui():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.image("Logo Posind Biru.png", width=120)
        st.title("Login SIG-DOM")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                with engine.connect() as conn:
                    query = text("SELECT id_kantor, nama_kantor FROM users_dc WHERE username = :u AND password_hash = :p")
                    res = conn.execute(query, {"u": u, "p": p}).fetchone()
                    if res:
                        st.session_state.logged_in = True
                        st.session_state.user_info = {"id": res[0], "nama": res[1]}
                        st.rerun()
                    else:
                        st.error("Username atau Password salah!")

# --- MENU UTAMA ---
def main_app():
    user = st.session_state.user_info
    
    # SIDEBAR NAVIGASI
    st.sidebar.image("Logo Posind Biru.png", width=80)
    st.sidebar.title("SIG-DOM Dashboard")
    st.sidebar.info(f"📍 {user['nama']}")
    
    menu = st.sidebar.selectbox("Pilih Menu:", [
        "🏠 Dashboard & Statistik", 
        "🗺️ Peta Wilayah Antaran", 
        "📦 Data Titikan Paket", 
        "⚙️ Manajemen User"
    ])
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- KONTEN MENU ---
    if menu == "🏠 Dashboard & Statistik":
        st.header("Dashboard Utama")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Zona", "12 Zona")
        col2.metric("Titikan Hari Ini", "450 Paket")
        col3.metric("Kurir Aktif", "8 Petugas")
        
        st.markdown("---")
        st.subheader("Grafik Antaran Mingguan")
        # Placeholder grafik
        chart_data = pd.DataFrame([10, 25, 45, 30, 50], columns=["Paket"])
        st.line_chart(chart_data)

    elif menu == "🗺️ Peta Wilayah Antaran":
        st.header("Visualisasi Spasial Wilayah per Kodepos")
        
        # 1. Fungsi untuk menentukan warna unik berdasarkan kodepos
        def get_color(kodepos):
            # Daftar warna yang kontras
            colors = [
                'red', 'blue', 'green', 'purple', 'orange', 'darkred', 
                'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
                'darkpurple', 'pink', 'lightblue', 'lightgreen', 'black'
            ]
            # Logika sederhana: ambil indeks warna berdasarkan hash kodepos
            index = hash(str(kodepos)) % len(colors)
            return colors[index]

        # 2. Ambil data dari Neon
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("""
                    SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geo 
                    FROM zona_antaran
                """), conn)
            
            if not df.empty:
                # Koordinat default (Sesuaikan dengan wilayah operasional Anda)
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13, control_scale=True)
                
                # 3. Masukkan data ke peta dengan warna berbeda
                for _, row in df.iterrows():
                    color = get_color(row['kodepos'])
                    
                    folium.GeoJson(
                        row['geo'],
                        name=f"Kodepos {row['kodepos']}",
                        style_function=lambda x, color=color: {
                            'fillColor': color,
                            'color': 'black',     # Garis tepi hitam
                            'weight': 2,
                            'fillOpacity': 0.5,
                        },
                        tooltip=folium.Tooltip(f"<b>Zona:</b> {row['nama_zona']}<br><b>Kodepos:</b> {row['kodepos']}")
                    ).add_to(m)

                # Tambahkan kontrol layer
                folium.LayerControl().add_to(m)
                
                # Tampilkan peta
                st_folium(m, width="100%", height=600)
                
                # 4. Tampilkan Tabel Legenda di bawah peta
                st.markdown("### 📋 Keterangan Warna Kodepos")
                legend_df = df[['kodepos', 'nama_zona']].copy()
                legend_df['Warna'] = legend_df['kodepos'].apply(get_color)
                st.dataframe(legend_df, use_container_width=True)
                
            else:
                st.info("Belum ada data geometri zona (Polygon) di database Neon.")
                
        except Exception as e:
            st.error(f"Gagal memuat peta: {e}")

    elif menu == "📦 Data Titikan Paket":
        st.header("Data Riwayat Antaran")
        st.write("Daftar koordinat paket yang telah diantarkan oleh kurir.")
        # Contoh tabel data
        data_dummy = {
            'No Resi': ['P24001', 'P24002'],
            'Status': ['Selesai', 'Selesai'],
            'Waktu': [datetime.now(), datetime.now()]
        }
        st.table(pd.DataFrame(data_dummy))

    elif menu == "⚙️ Manajemen User":
        st.header("Pengaturan Pengguna")
        with engine.connect() as conn:
            df_users = pd.read_sql(text("SELECT username, nama_kantor, status FROM users_dc"), conn)
            st.dataframe(df_users, use_container_width=True)

# --- JALANKAN APLIKASI ---
if not st.session_state.logged_in:
    login_ui()
else:
    main_app()
