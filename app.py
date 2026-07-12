import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. KONFIGURASI AWAL
# ==========================================
st.set_page_config(page_title="MONITORING ISOTANK ACID & ESCAID", page_icon="🛢️", layout="wide")
st.title("🛢️ MONITORING ISOTANK ACID DAN ESCAID")

SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1eX12pN5sfohdIlEOWKNMv2Cj80lTRvxp0k8H-zcd4DI/edit?gid=0#gid=0'
NAMA_SHEET = 'ACID & ESCAID STATUS ' 

# ==========================================
# 2. FUNGSI KONEKSI
# ==========================================
@st.cache_resource
def get_gsheets_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    s = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(s, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

# ==========================================
# 3. FUNGSI AMBIL DATA
# ==========================================
@st.cache_data(ttl=5)
def ambil_data():
    try:
        client = get_gsheets_connection()
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
        
        data_mentah = sheet.get_all_values()
        
        if not data_mentah or len(data_mentah) < 2:
            return pd.DataFrame()
            
        df = pd.DataFrame(data_mentah[1:], columns=data_mentah[0])
        
        if 'TANK ID' in df.columns:
            df = df[df['TANK ID'].astype(str).str.strip() != '']
            df = df.drop_duplicates(subset=['TANK ID'], keep='last')
            
        return df
    except Exception as e:
        st.error(f"❌ Gagal membaca Google Sheets. Detail: {e}")
        return pd.DataFrame()

df = ambil_data()

# ==========================================
# 4. TAMPILAN DASHBOARD & FORM INPUT
# ==========================================
tab_dashboard, tab_input = st.tabs(["📊 Lihat Dashboard", "📝 Input Data Baru"])

# --- BAGIAN DASHBOARD ---
with tab_dashboard:
    if df.empty:
        st.warning("⚠️ Data kosong. Pastikan baris ke-1 di Spreadsheet Anda berisi judul kolom.")
    else:
        # ==========================================
        # FILTER PENCARIAN (Bertingkat)
        # ==========================================
        st.markdown("### 🔍 Filter Pencarian")
        
        # 1. Filter Utama: By Reagent (Satu kolom penuh di atas)
        # Kita cari nama kolom yang mengandung kata 'Reagent' (berjaga-jaga jika salah ketik)
        kolom_reagent = next((col for col in df.columns if 'REAGENT' in str(col).upper()), None)
        
        filter_reagent = "Semua Reagent"
        if kolom_reagent:
            list_reagent = ["Semua Reagent"] + sorted(df[kolom_reagent].astype(str).str.upper().unique().tolist())
            filter_reagent = st.selectbox(f"Filter Utama (Berdasarkan {kolom_reagent}):", list_reagent)
        else:
            st.info("💡 Kolom 'Jenis Reagent' belum terbaca. Pastikan Anda sudah memberi judul kolom tersebut di GSheets.")

        # 2. Filter Sekunder: Vendor, Status, Lokasi (3 Kolom sejajar di bawahnya)
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            list_vendor = ["Semua Vendor"] + sorted(df['Vendor'].astype(str).unique().tolist())
            filter_vendor = st.selectbox("Filter berdasarkan Vendor:", list_vendor)
            
        with col_filter2:
            list_status = ["Semua Status"] + sorted(df['STATUS'].astype(str).str.upper().unique().tolist())
            filter_status = st.selectbox("Filter berdasarkan Status:", list_status)
            
        with col_filter3:
            list_lokasi = ["Semua Lokasi"] + sorted(df['LOCATION'].astype(str).str.upper().unique().tolist())
            filter_lokasi = st.selectbox("Filter berdasarkan Lokasi:", list_lokasi)

        # Menerapkan Filter ke Data
        df_tampil = df.copy()
        
        # Eksekusi Filter Reagent
        if kolom_reagent and filter_reagent != "Semua Reagent":
            df_tampil = df_tampil[df_tampil[kolom_reagent].astype(str).str.upper() == filter_reagent]
            
        # Eksekusi Filter Lainnya
        if filter_vendor != "Semua Vendor":
            df_tampil = df_tampil[df_tampil['Vendor'].astype(str) == filter_vendor]
        if filter_status != "Semua Status":
            df_tampil = df_tampil[df_tampil['STATUS'].astype(str).str.upper() == filter_status]
        if filter_lokasi != "Semua Lokasi":
            df_tampil = df_tampil[df_tampil['LOCATION'].astype(str).str.upper() == filter_lokasi]

        st.divider()

        # ==========================================
        # RINGKASAN DATA & GRAFIK
        # ==========================================
        st.subheader("Ringkasan Kondisi Tangki")
        col1, col2, col3, col4 = st.columns(4)
        
        total_tangki = len(df_tampil)
        
        if 'QTY' in df_tampil.columns:
            df_tampil['QTY_NUM'] = pd.to_numeric(df_tampil['QTY'], errors='coerce').fillna(0)
            total_volume = df_tampil['QTY_NUM'].sum()
        else:
            total_volume = 0
            
        if 'STATUS' in df_tampil.columns:
            jml_full = len(df_tampil[df_tampil['STATUS'].astype(str).str.upper() == 'FULL'])
            jml_empty = len(df_tampil[df_tampil['STATUS'].astype(str).str.upper() == 'EMPTY'])
        else:
            jml_full, jml_empty = 0, 0
        
        col1.metric("Total Unit Isotank", total_tangki)
        col2.metric("Total Volume (QTY)", f"{total_volume:,.0f}")
        col3.metric("Status FULL", jml_full)
        col4.metric("Status EMPTY", jml_empty)
        
        st.divider()
        
        kolom_grafik1, kolom_grafik2 = st.columns(2)
        with kolom_grafik1:
            st.markdown("**Perbandingan Status Tangki**")
            if 'STATUS' in df_tampil.columns and total_tangki > 0:
                data_status = df_tampil['STATUS'].value_counts().reset_index()
                data_status.columns = ['Status', 'Jumlah']
                fig1 = px.pie(data_status, names='Status', values='Jumlah', hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Tidak ada data untuk grafik ini.")
                
        with kolom_grafik2:
            st.markdown("**Posisi Lokasi Tangki**")
            if 'LOCATION' in df_tampil.columns and total_tangki > 0:
                data_lokasi = df_tampil['LOCATION'].value_counts().reset_index()
                data_lokasi.columns = ['Lokasi', 'Jumlah']
                fig2 = px.bar(data_lokasi, x='Lokasi', y='Jumlah', color='Lokasi')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Tidak ada data untuk grafik ini.")
                
        st.subheader("Data Detail Keseluruhan")
        if 'QTY_NUM' in df_tampil.columns:
            df_tampil = df_tampil.drop(columns=['QTY_NUM'])
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)

# --- BAGIAN FORM INPUT ---
with tab_input:
    st.subheader("Form Kedatangan & Status Tangki Baru")
    
    with st.form("form_input", clear_on_submit=True):
        kolom_form1, kolom_form2, kolom_form3 = st.columns(3)
        
        with kolom_form1:
            st.markdown("**1. Info Utama**")
            input_vendor = st.text_input("Vendor")
            input_tank_id = st.text_input("TANK ID (Wajib Diisi)")
            # Input Baru: Jenis Reagent
            input_reagent = st.selectbox("Jenis Reagent", ["ACID", "ESCAID", "LAINNYA"])
            input_qty = st.number_input("QTY", min_value=0.0)
            input_uom = st.selectbox("UoM", ["KG", "LITER"])
            
        with kolom_form2:
            st.markdown("**2. Info Status & Masuk**")
            input_status = st.selectbox("STATUS", ["FULL", "EMPTY"])
            input_lokasi = st.selectbox("LOCATION", ["WAREHOUSE", "OUTBOUND", "INBOUND", "25KT"])
            input_qty_issued = st.number_input("QTY ISSUED", min_value=0.0)
            input_date_empty = st.date_input("Date Empty", value=None)
            input_ps = st.text_input("PS")
            input_cm_in = st.text_input("CM IN")
            
        with kolom_form3:
            st.markdown("**3. Info Detail Keluar**")
            input_date_in = st.date_input("DATE IN", value=None)
            input_po_in = st.text_input("PO IN")
            input_pr_po_out = st.text_input("PR/PO OUT")
            input_qty_pr = st.number_input("QTY PR", min_value=0.0)
            input_cm_out = st.text_input("CM OUT")
            input_date_out = st.date_input("DATE OUT", value=None)
            
        st.markdown("---")
        tombol_simpan = st.form_submit_button("Simpan ke Google Sheets")
        
        if tombol_simpan:
            if input_tank_id.strip() == "":
                st.error("Gagal: TANK ID tidak boleh kosong!")
            else:
                try:
                    client = get_gsheets_connection()
                    worksheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
                    
                    str_date_empty = input_date_empty.strftime("%Y-%m-%d") if input_date_empty else ""
                    str_date_in = input_date_in.strftime("%Y-%m-%d") if input_date_in else ""
                    str_date_out = input_date_out.strftime("%Y-%m-%d") if input_date_out else ""
                    
                    # Kolom Q (Index ke-16) adalah letak input_reagent
                    baris_baru = [
                        input_vendor, input_tank_id, input_qty, input_uom, 
                        input_status, input_lokasi, input_qty_issued, str_date_empty, 
                        input_ps, input_cm_in, str_date_in, input_po_in, 
                        input_pr_po_out, input_qty_pr, input_cm_out, str_date_out,
                        input_reagent  # <--- Ini akan otomatis masuk ke Kolom Q
                    ]
                    
                    worksheet.append_rows([baris_baru])
                    st.cache_data.clear() 
                    st.success(f"Berhasil! Data tangki {input_tank_id} beserta jenis reagent-nya telah tersimpan.")
                except Exception as e:
                    st.error(f"Gagal saat menyimpan data: {e}")
