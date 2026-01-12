import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# Konfigurasi Halaman
st.set_page_config(page_title="SIG-DOM Neon", page_icon="🚚")

@st.cache_resource
def get_engine():
    # Mengambil URL dari Secrets Streamlit
    if "DB_URL" not in st.secrets:
        st.error("Gagal: DB_URL tidak ditemukan di Secrets!")
        return None
    return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)

engine = get_engine()

st.title("🚚 Dashboard SIG-DOM (Neon.tech)")

if engine:
    try:
        with engine.connect() as conn:
            # Tes koneksi sederhana
            conn.execute(text("SELECT 1"))
            st.success("✅ Terhubung ke Database Neon!")

            # Form Login
            st.markdown("### Silakan Login")
            u_input = st.text_input("Username")
            p_input = st.text_input("Password", type="password")
            
            if st.button("Masuk"):
                query = text("SELECT nama_kantor FROM users_dc WHERE username = :u AND password_hash = :p")
                user = conn.execute(query, {"u": u_input, "p": p_input}).fetchone()
                
                if user:
                    st.success(f"Selamat Datang di {user[0]}")
                    st.balloons()
                else:
                    st.error("Username atau Password salah.")

    except Exception as e:
        st.error(f"Kesalahan Koneksi: {e}")
