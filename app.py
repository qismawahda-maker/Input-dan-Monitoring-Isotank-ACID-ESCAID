import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. KONFIGURASI AWAL & GOOGLE SHEETS
# ==========================================
st.set_page_config(page_title="Dashboard Isotank", page_icon="🛢️", layout="wide")
st.title("🛢️ Sistem Monitoring Isotank")

# Masukkan Link Google Sheet Anda di sini
SPREADSHEET_URL = 'SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H9I0J/edit'' 
NAMA_SHEET = 'ACID & ESCAID STATUS' # Sesuaikan nama sheet-nya

# Fungsi untuk koneksi ke Google Sheets menggunakan secrets
def get_gsheets_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Mengambil kredensial dari Streamlit Secrets
    s = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(
        s,
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    return client

# ==========================================
# 2. FUNGSI AMBIL DATA
# ==========================================
@st.cache_data(ttl=5)
def ambil_data():
    try:
        client = get_gsheets_connection()
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
        # Mengambil semua data dan mengubahnya menjadi DataFrame Pandas
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Bersihkan baris jika TANK ID kosong
        if not df.empty and 'TANK ID' in df.columns:
            # Pastikan nama kolom sama persis, jika ada spasi, bersihkan
            df = df[df['TANK ID'].astype(str).str.strip() != '']
        return df, sheet
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat membaca Google Sheets: {e}")
        return pd.DataFrame(), None

df, worksheet = ambil_data()

# ==========================================
# 3. TAMPILAN APLIKASI
# ==========================================
tab_dashboard, tab_input = st.tabs(["📊 Lihat Dashboard", "📝 Input Data Baru"])

# --- BAGIAN DASHBOARD ---
with tab_dashboard:
    if df.empty:
        st.warning("Data kosong atau kolom tidak terbaca. Pastikan baris 1 di Google Sheets adalah header/judul kolom.")
    else:
        st.subheader("Ringkasan Kondisi Tangki")
        
        col1, col2, col3, col4 = st.columns(4)
        total_tangki = len(df)
        
        if 'QTY' in df.columns:
            df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0)
            total_volume = df['QTY'].sum()
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
        st.subheader("Data Detail")
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- BAGIAN INPUT DATA ---
with tab_input:
    st.subheader("Form Tambah Kedatangan/Status Tangki")
    
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
        tombol_simpan = st.form_submit_button("Simpan Data ke Google Sheets")
        
        if tombol_simpan:
            if input_tank_id.strip() == "":
                st.error("Gagal: TANK ID tidak boleh kosong!")
            else:
                try:
                    # Pastikan format tanggal diubah menjadi string sebelum dikirim ke Google Sheets
                    str_date_empty = input_date_empty.strftime("%Y-%m-%d") if input_date_empty else ""
                    str_date_in = input_date_in.strftime("%Y-%m-%d") if input_date_in else ""
                    str_date_out = input_date_out.strftime("%Y-%m-%d") if input_date_out else ""
                    
                    # Menyusun array sesuai urutan dari prompt Anda
                    baris_baru = [
                        input_vendor, input_tank_id, input_qty, input_uom, 
                        input_status, input_lokasi, input_qty_issued, str_date_empty, 
                        input_ps, input_cm_in, str_date_in, input_po_in, 
                        input_pr_po_out, input_qty_pr, input_cm_out, str_date_out
                    ]
                    
                    # Append baris baru langsung ke Google Sheets
                    worksheet.append_row(baris_baru)
                    
                    st.cache_data.clear() # Refresh agar data baru tampil di tabel
                    st.success(f"Data tangki {input_tank_id} berhasil disimpan ke Google Sheets!")
                except Exception as e:
                    st.error(f"Gagal menyimpan data: {e}")
