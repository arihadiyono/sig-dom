import streamlit as st
import pandas as pd
import psycopg2
import folium
from streamlit_folium import folium_static
import os
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi Database
def get_conn():
    return psycopg2.connect(os.getenv("DB_URL"))

st.set_page_config(page_title="SIG-DOM PT POS", layout="wide")
st.title("🚚 Dashboard Antaran PT Pos Indonesia")

# Ambil data dari Supabase
try:
    conn = get_conn()
    query = """
        SELECT connote, penerima, status_antaran, 
               ST_Y(geom) as lat, ST_X(geom) as lon 
        FROM titikan_antaran
    """
    df = pd.read_sql(query, conn)
    
    # Layout Kolom
    col1, col2 = st.columns([3, 1])

    with col1:
        # Inisialisasi Peta (Pusat Bandung)
        m = folium.Map(location=[-6.9175, 107.6191], zoom_start=13)
        
        # Tambahkan Titik Antaran ke Peta
        for _, row in df.iterrows():
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"{row['penerima']} - {row['connote']}",
                tooltip=row['status_antaran'],
                icon=folium.Icon(color="orange" if row['status_antaran'] == "DELIVERED" else "blue")
            ).add_to(m)
        
        folium_static(m, width=900)

    with col2:
        st.subheader("Ringkasan Data")
        st.write(f"Total Kiriman: {len(df)}")
        st.dataframe(df[['connote', 'penerima', 'status_antaran']])

except Exception as e:
    st.error(f"Error Koneksi: {e}")