import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# 2. Fungsi Koneksi Database (Optimalkan untuk Supabase Pooler)
def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url:
        st.error("DB_URL tidak ditemukan! Pastikan sudah diisi di Secrets Streamlit.")
        return None
    try:
        # Menggunakan SQLAlchemy Engine
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        st.error(f"Gagal membuat engine koneksi: {e}")
        return None

# Konfigurasi Halaman
st.set_page_config(
    page_title="SIG-DOM PT POS INDONESIA",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 Delivery Operation Management (SIG-DOM)")
st.subheader("Monitoring Antaran DC Asia Afrika - Bandung")
st.markdown("---")

engine = get_engine()

if engine:
    try:
        # --- QUERY DATA ---
        # Query Poligon Zona
        query_zona = text("""
            SELECT kodepos, nama_zona, 
            ST_AsGeoJSON(geom)::json as geojson 
            FROM zona_antaran
        """)
        
        # Query Titik Antaran
        query_titik = text("""
            SELECT connote, penerima, status_antaran, alamat_penerima,
                   ST_Y(geom) as lat, ST_X(geom) as lon
            FROM titikan_antaran
        """)

        with engine.connect() as conn:
            df_zona = pd.read_sql(query_zona, conn)
            df_titik = pd.read_sql(query_titik, conn)

        # --- LAYOUT DASHBOARD ---
        col_map, col_stats = st.columns([3, 1])

        with col_map:
            st.markdown("#### Peta Sebaran Antaran")
            # Inisialisasi Peta (Pusat di Bandung)
            m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13, tiles="OpenStreetMap")

            # Layer 1: Poligon Zona (Kodepos)
            if not df_zona.empty:
                for _, row in df_zona.iterrows():
                    folium.GeoJson(
                        row['geojson'],
                        style_function=lambda x: {
                            'fillColor': '#ffcc00',
                            'color': '#ff6600',
                            'weight': 1.5,
                            'fillOpacity': 0.1
                        },
                        tooltip=f"Kodepos: {row['kodepos']} ({row['nama_zona']})"
                    ).add_to(m)

            # Layer 2: Titik Antaran (Markers)
            if not df_titik.empty:
                for _, row in df_titik.iterrows():
                    color = "green" if row['status_antaran'] == "DELIVERED" else "orange"
                    folium.Marker(
                        location=[row['lat'], row['lon']],
                        popup=f"Resi: {row['connote']}<br>Penerima: {row['penerima']}",
                        tooltip=f"{row['penerima']} ({row['status_antaran']})",
                        icon=folium.Icon(color=color, icon="info-sign")
                    ).add_to(m)
            else:
                st.info("Belum ada data titik antaran di database.")

            # Tampilkan Peta menggunakan st_folium
            st_folium(m, width=900, height=550, returned_objects=[])

        with col_stats:
            st.markdown("#### Statistik")
            st.metric("Total Kiriman", len(df_titik))
            
            if not df_titik.empty:
                status_counts = df_titik['status_antaran'].value_counts()
                st.bar_chart(status_counts)
                
                st.markdown("---")
                st.markdown("#### Daftar Resi")
                st.dataframe(df_titik[['connote', 'status_antaran']], height=300)

    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil data: {e}")
        st.info("Pastikan tabel 'zona_antaran' dan 'titikan_antaran' sudah ada di database.")

else:
    st.warning("Menunggu koneksi database...")

# Footer
st.markdown("---")
st.caption("Aplikasi SIG-DOM PT Pos Indonesia © 2026")
