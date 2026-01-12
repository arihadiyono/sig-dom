import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="SIG-DOM POS", layout="wide")

# Fungsi koneksi yang lebih robust
@st.cache_resource
def get_engine():
    if "DB_URL" not in st.secrets:
        st.error("DB_URL tidak ditemukan!")
        return None
    
    url = st.secrets["DB_URL"]
    try:
        # Menambahkan argument 'options' secara manual untuk membantu Supavisor menemukan Tenant
        # Ganti [PROJECT_REF] dengan vlsyyhlsvwjavfrzruyd
        return create_engine(
            url,
            connect_args={
                "options": "-c search_path=public",
                "connect_timeout": 10
            },
            pool_pre_ping=True
        )
    except Exception as e:
        st.error(f"Inisialisasi Gagal: {e}")
        return None

engine = get_engine()

st.title("🚚 SIG-DOM POS Login")

# FORM LOGIN SEDERHANA UNTUK TES
with st.form("login"):
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.form_submit_button("Masuk"):
        if engine:
            try:
                with engine.connect() as conn:
                    # Query menggunakan parameter bind untuk keamanan
                    query = text("SELECT username, nama_kantor FROM users_dc WHERE username = :u AND password_hash = :p")
                    result = conn.execute(query, {"u": u, "p": p}).fetchone()
                    
                    if result:
                        st.success(f"Selamat Datang, {result[1]}!")
                        st.session_state.auth = True
                    else:
                        st.error("User tidak ditemukan di database.")
            except Exception as e:
                st.error(f"Error Koneksi: {e}")
                st.info("Jika muncul 'Tenant not found', pastikan Username di Secrets adalah: postgres.vlsyyhlsvwjavfrzruyd")
