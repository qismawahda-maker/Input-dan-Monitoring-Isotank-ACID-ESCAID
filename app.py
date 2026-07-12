import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. KONFIGURASI AWAL
# ==========================================
st.set_page_config(page_title="Dashboard Isotank", page_icon="🛢️", layout="wide")
st.title("🛢️ Sistem Monitoring Isotank (Google Sheets)")

SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1eX12pN5sfohdIlEOWKNMv2Cj80lTRvxp0k8H-zcd4DI/edit?gid=0#gid=0'
NAMA_SHEET = 'ACID & ESCAID STATUS' 

# ==========================================
# 2. FUNGSI KONEKSI (Menggunakan Cache Resource)
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
# 3. FUNGSI AMBIL DATA (Hanya Data, bukan Koneksi)
# ==========================================
@st.cache_data(ttl=5)
def ambil_data():
    try:
        client = get_gsheets_connection()
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
        
        data_mentah = sheet.get_all_values()
        
        if not data_mentah or len(data_mentah) < 2:
            return pd.DataFrame()
            
        # Asumsi: Baris pertama di Spreadsheet (Baris 1) adalah judul kolom
        df = pd.DataFrame(data_mentah[1:], columns=data_mentah[0])
        
        # Hapus baris yang kosong pada TANK ID
        if 'TANK ID' in df.columns:
            df = df[df['TANK ID'].astype(str).str.strip() != '']
            
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
        st.warning("⚠️ Data kosong. Pastikan baris ke-1 di Spreadsheet Anda berisi judul kolom (Vendor, TANK ID, dll).")
    else:
        st.subheader("Ringkasan Kondisi Tangki")
        col1, col2, col3, col4 = st.columns(4)
        
        total_tangki = len(df)
        
        # Konversi QTY jadi angka agar bisa dijumlahkan
        if 'QTY' in df.columns:
            df['QTY_NUM'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0)
            total_volume = df['QTY_NUM'].sum()
        else:
            total_volume = 0
            
        if 'STATUS' in df.columns:
            jml_full = len(df[df['STATUS'].astype(str).str.upper() == 'FULL'])
            jml_empty = len(df[df['STATUS'].astype(str).str.upper() == 'EMPTY'])
        else:
            jml_full, jml_empty = 0, 0
        
        col1.metric("Total Unit Isotank", total_tangki)
        col2.metric("Total Volume (QTY)", f"{total_volume:,.0f}")
        col3.metric("Status FULL", jml_full)
        col4.metric("Status EMPTY", jml_empty)
        
        st.divider()
        
        kolom_grafik1, kolom_grafik2 = st.columns(2)
        with kolom_grafik1:
            st.markdown("**Perbandingan Status (FULL vs EMPTY)**")
            if 'STATUS' in df.columns:
                data_status = df['STATUS'].value_counts().reset_index()
                data_status.columns = ['Status', 'Jumlah']
                fig1 = px.pie(data_status, names='Status', values='Jumlah', hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
                
        with kolom_grafik2:
            st.markdown("**Posisi Lokasi Tangki**")
            if 'LOCATION' in df.columns:
                data_lokasi = df['LOCATION'].value_counts().reset_index()
                data_lokasi.columns = ['Lokasi', 'Jumlah']
                fig2 = px.bar(data_lokasi, x='Lokasi', y='Jumlah', color='Lokasi')
                st.plotly_chart(fig2, use_container_width=True)
                
        st.subheader("Data Detail")
        if 'QTY_NUM' in df.columns:
            df = df.drop(columns=['QTY_NUM'])
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- BAGIAN FORM INPUT ---
with tab_input:
    st.subheader("Form Kedatangan & Status Tangki Baru")
    
    with st.form("form_input", clear_on_submit=True):
        kolom_form1, kolom_form2, kolom_form3 = st.columns(3)
        
        with kolom_form1:
            st.markdown("**1. Info Utama**")
            input_vendor = st.text_input("Vendor")
            input_tank_id = st.text_input("TANK ID (Wajib Diisi)")
            input_qty = st.number_input("QTY", min_value=0.0)
            input_uom = st.selectbox("UoM", ["KG", "LITER"])
            input_status = st.selectbox("STATUS", ["FULL", "EMPTY"])
            input_lokasi = st.selectbox("LOCATION", ["WAREHOUSE", "OUTBOUND", "INBOUND", "25KT"])
            
        with kolom_form2:
            st.markdown("**2. Info Detail Masuk**")
            input_qty_issued = st.number_input("QTY ISSUED", min_value=0.0)
            input_date_empty = st.date_input("Date Empty", value=None)
            input_ps = st.text_input("PS")
            input_cm_in = st.text_input("CM IN")
            input_date_in = st.date_input("DATE IN", value=None)
            input_po_in = st.text_input("PO IN")
            
        with kolom_form3:
            st.markdown("**3. Info Detail Keluar**")
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
                    # Membuka koneksi baru HANYA saat mau input data
                    client = get_gsheets_connection()
                    worksheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
                    
                    # Mengubah format tanggal menjadi teks
                    str_date_empty = input_date_empty.strftime("%Y-%m-%d") if input_date_empty else ""
                    str_date_in = input_date_in.strftime("%Y-%m-%d") if input_date_in else ""
                    str_date_out = input_date_out.strftime("%Y-%m-%d") if input_date_out else ""
                    
                    # Susunan kolom yang akan dikirim
                    baris_baru = [
                        input_vendor, input_tank_id, input_qty, input_uom, 
                        input_status, input_lokasi, input_qty_issued, str_date_empty, 
                        input_ps, input_cm_in, str_date_in, input_po_in, 
                        input_pr_po_out, input_qty_pr, input_cm_out, str_date_out
                    ]
                    
                    # Menggunakan append_rows untuk menghindari bug versi lama
                    worksheet.append_rows([baris_baru])
                    
                    # Refresh aplikasi agar tabel di Dashboard langsung ter-update
                    st.cache_data.clear() 
                    st.success(f"Berhasil! Data tangki {input_tank_id} telah meluncur ke Google Sheets.")
                except Exception as e:
                    st.error(f"Gagal saat menyimpan data: {e}")
