import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

# 1. Inisialisasi Halaman
st.set_page_config(page_title="SIG-DOM POS", layout="wide")

# 2. Fungsi Engine dengan pool_pre_ping
@st.cache_resource
def get_engine():
    # Pastikan mengambil dari st.secrets agar sinkron dengan Streamlit Cloud
    if "DB_URL" not in st.secrets:
        st.error("Konfigurasi DB_URL hilang di Secrets!")
        return None
    
    db_url = st.secrets["DB_URL"]
    try:
        # pool_pre_ping=True akan mengetes koneksi sebelum digunakan
        # Sangat krusial untuk mencegah 'OperationalError' di server Cloud
        return create_engine(
            db_url, 
            pool_pre_ping=True,
            pool_recycle=300
        )
    except Exception as e:
        st.error(f"Gagal Inisialisasi Engine: {e}")
        return None

engine = get_engine()

# 3. UI Utama
st.title("🚚 SIG-DOM PT POS INDONESIA")

if engine:
    try:
        # Tes koneksi sederhana
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            st.success("✅ Koneksi Berhasil! Database Terhubung.")
            
            # Tampilkan menu setelah sukses login/koneksi
            st.info("Sistem siap digunakan. Silakan akses menu di sidebar.")
            
    except Exception as e:
        st.error("❌ Gagal Terhubung ke Database.")
        st.warning(f"Detail Error: {str(e)}")
        st.info("Tips: Pastikan Project ID di username sudah benar (postgres.vlsyyhlsvwjavfrzruyd)")
