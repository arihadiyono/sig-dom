import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Data contoh dari Anda (Silakan tambah sesuai kebutuhan)
data_antaran = [
    {
        "id_petugas": "560001308", "id_kantor": "4040E", "id_regional": "3",
        "connote": "P2510300003418", "produk": "PKH", "jenis_kiriman": "Dokumen",
        "is_cod": "NONCOD", "nominal_cod": 0, "berat_kg": 0.0,
        "penerima": "IRWAN DAVID HADINATA", "alamat_penerima": "JL LRE MARTADINATA 67",
        "kodepos_penerima": "40111", "waktu_kejadian": "2025-10-31 16:30:05",
        "status_antaran": "DELIVERED", "keterangan": "widi", 
        "lat": -6.90641, "lon": 107.61761
    },
    {
        "id_petugas": "560001308", "id_kantor": "4040E", "id_regional": "3",
        "connote": "P2510300003419", "produk": "PKH", "jenis_kiriman": "Dokumen",
        "is_cod": "NONCOD", "nominal_cod": 0, "berat_kg": 0.0,
        "penerima": "KOESBANDONO", "alamat_penerima": "JL LRE MARTADINATA 69",
        "kodepos_penerima": "40111", "waktu_kejadian": "2025-11-02 14:32:26",
        "status_antaran": "DELIVERED", "keterangan": "Mario", 
        "lat": -6.9060791, "lon": 107.6178093
    }
]

def upload_to_supabase():
    try:
        # Koneksi ke Supabase
        conn = psycopg2.connect(os.getenv("DB_URL"))
        cur = conn.cursor()

        for d in data_antaran:
            query = """
                INSERT INTO titikan_antaran (
                    id_petugas, id_kantor, id_regional, connote, produk, 
                    jenis_kiriman, is_cod, nominal_cod, berat_kg, penerima, 
                    alamat_penerima, kodepos_penerima, waktu_kejadian, 
                    status_antaran, keterangan, geom
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    ST_SetSRID(ST_Point(%s, %s), 4326)
                ) ON CONFLICT (connote) DO NOTHING;
            """
            cur.execute(query, (
                d['id_petugas'], d['id_kantor'], d['id_regional'], d['connote'], d['produk'],
                d['jenis_kiriman'], d['is_cod'], d['nominal_cod'], d['berat_kg'], d['penerima'],
                d['alamat_penerima'], d['kodepos_penerima'], d['waktu_kejadian'],
                d['status_antaran'], d['keterangan'], d['lon'], d['lat']
            ))
        
        conn.commit()
        print(f"✅ Berhasil mengunggah {len(data_antaran)} data ke Supabase!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Gagal: {e}")

if __name__ == "__main__":
    upload_to_supabase()