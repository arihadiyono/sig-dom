import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv

load_dotenv()

# --- FUNGSI KONEKSI ---
def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url: return None
    try:
        return create_engine(db_url)
    except: return None

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SIG-DOM POS INDONESIA", layout="wide")
engine = get_engine()

# --- SIDEBAR MENU ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=100)
    st.title("Menu SIG-DOM")
    menu = st.radio("Pilih Tampilan:", ["🗺️ Zona Antaran", "history 📦 History Antaran"])
    st.markdown("---")
    st.caption("DC Asia Afrika - Bandung")

# --- 1. MENU ZONA ANTARAN ---
if menu == "🗺️ Zona Antaran":
    st.title("Peta Zona per Kodepos")
    st.write("Menampilkan pembagian wilayah berdasarkan kodepos dengan pewarnaan berbeda.")

    if engine:
        query = text("SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson FROM zona_antaran")
        with engine.connect() as conn:
            df_zona = pd.read_sql(query, conn)

        if not df_zona.empty:
            m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
            
            # Daftar warna untuk kodepos berbeda
            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue']
            
            for i, row in df_zona.iterrows():
                # Pilih warna berdasarkan index agar tiap kodepos beda warna
                color_index = i % len(colors)
                folium.GeoJson(
                    row['geojson'],
                    style_function=lambda x, color=colors[color_index]: {
                        'fillColor': color,
                        'color': 'black',
                        'weight': 2,
                        'fillOpacity': 0.4
                    },
                    tooltip=f"Kodepos: {row['kodepos']} - {row['nama_zona']}"
                ).add_to(m)
            
            st_folium(m, width=1200, height=600)
        else:
            st.warning("Data zona tidak ditemukan di database.")

# --- 2. MENU HISTORY ANTARAN ---
elif menu == "history 📦 History Antaran":
    st.title("History Antaran per Petugas")
    
    if engine:
        # Load daftar petugas untuk filter
        with engine.connect() as conn:
            df_petugas = pd.read_sql(text("SELECT * FROM petugas_antaran"), conn)
        
        # Filter di atas peta
        c1, c2 = st.columns(2)
        with c1:
            petugas_selected = st.selectbox("Pilih Petugas:", df_petugas['nama_petugas'].tolist() if not df_petugas.empty else ["Belum ada data"])
        with c2:
            tgl_selected = st.date_input("Pilih Tanggal:")

        # Query data antaran berdasarkan filter
        query_history = text("""
            SELECT t.*, ST_Y(t.geom) as lat, ST_X(t.geom) as lon 
            FROM titikan_antaran t
            JOIN petugas_antaran p ON t.id_petugas = p.id_petugas
            WHERE p.nama_petugas = :nama AND DATE(t.created_at) = :tgl
        """)
        
        with engine.connect() as conn:
            # Gunakan parameter binding untuk keamanan
            df_hist = pd.read_sql(query_history, conn, params={"nama": petugas_selected, "tgl": tgl_selected})

        if not df_hist.empty:
            st.success(f"Ditemukan {len(df_hist)} titik antaran untuk {petugas_selected}")
            
            m_hist = folium.Map(location=[df_hist['lat'].mean(), df_hist['lon'].mean()], zoom_start=14)
            
            # Tambahkan garis (Polyline) untuk menunjukkan urutan perjalanan
            points = []
            for _, row in df_hist.iterrows():
                loc = [row['lat'], row['lon']]
                points.append(loc)
                
                icon_color = 'green' if row['status_antaran'] == 'DELIVERED' else 'orange'
                folium.Marker(
                    loc,
                    popup=f"Resi: {row['connote']}<br>Status: {row['status_antaran']}",
                    icon=folium.Icon(color=icon_color, icon='bicycle', prefix='fa')
                ).add_to(m_hist)
            
            if len(points) > 1:
                folium.PolyLine(points, color="blue", weight=2.5, opacity=0.8).add_to(m_hist)
            
            st_folium(m_hist, width=1200, height=500)
            st.dataframe(df_hist[['connote', 'penerima', 'status_antaran', 'alamat_penerima']])
        else:
            st.info(f"Tidak ada record antaran untuk {petugas_selected} pada tanggal {tgl_selected}")
