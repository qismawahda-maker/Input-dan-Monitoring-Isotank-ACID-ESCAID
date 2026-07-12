import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import io
from datetime import datetime

# ==========================================
# 1. KONFIGURASI AWAL & CUSTOM CSS FONT
# ==========================================
st.set_page_config(page_title="MONITORING ISOTANK ACID & ESCAID", page_icon="🛢️", layout="wide")

st.markdown("""
    <style>
        .main-title {
            font-size: 42px !important;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .stMarkdown h3, .stMarkdown h5 {
            font-size: 26px !important;
            font-weight: bold !important;
        }
        .stSelectbox label, .stTextInput label, .stNumberInput label, .stDateInput label {
            font-size: 20px !important;
            font-weight: 500 !important;
        }
        .stSelectbox div, .stTextInput div, .stNumberInput div, .stDateInput div {
            font-size: 18px !important;
        }
        .stTabs button {
            font-size: 22px !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 36px !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 18px !important;
        }
        .stDataFrame div {
            font-size: 16px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🛢️ MONITORING ISOTANK</div>', unsafe_allow_html=True)

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
@st.cache_data(ttl=2)
def ambil_data():
    try:
        client = get_gsheets_connection()
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
        data_mentah = sheet.get_all_values()
        
        if not data_mentah or len(data_mentah) < 2:
            return pd.DataFrame()
            
        df = pd.DataFrame(data_mentah[1:], columns=data_mentah[0])
        return df
    except Exception as e:
        st.error(f"❌ Gagal membaca Google Sheets. Detail: {e}")
        return pd.DataFrame()

# Kita ambil data mentah penuh untuk fungsi pencarian riwayat
df_mentah = ambil_data()

# Untuk visualisasi Dashboard, tetap gunakan data unik terbaru per TANK ID
if not df_mentah.empty and 'TANK ID' in df_mentah.columns:
    df = df_mentah[df_mentah['TANK ID'].astype(str).str.strip() != ''].copy()
    df = df.drop_duplicates(subset=['TANK ID'], keep='last')
else:
    df = df_mentah.copy()

# Helper untuk mengubah string tanggal ke objek date Python
def konversi_ke_date(tgl_str):
    if not tgl_str or tgl_str.strip() == "":
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(tgl_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

# FUNGSI PENYELAMAT: Mengubah string dari Sheets ke float secara aman
def safe_float(val, default=0.0):
    if val is None:
        return default
    # Bersihkan spasi dan hapus tanda koma ribuan jika ada (misal: "25,000" -> "25000")
    val_str = str(val).strip().replace(',', '')
    if not val_str or val_str == "":
        return default
    try:
        return float(val_str)
    except ValueError:
        return default

# ==========================================
# 4. TAMPILAN DASHBOARD & FORM INPUT
# ==========================================
tab_dashboard, tab_input = st.tabs(["📊 Lihat Dashboard", "📝 Input Data Baru / Update"])

# --- BAGIAN DASHBOARD ---
with tab_dashboard:
    if df.empty:
        st.warning("⚠️ Data kosong. Pastikan baris ke-1 di Spreadsheet Anda berisi judul kolom.")
    else:
        # FILTER PENCARIAN
        st.markdown("### 🔍 Filter Pencarian")
        kolom_reagent = next((col for col in df.columns if 'REAGENT' in str(col).upper()), None)
        
        filter_reagent = "Semua Reagent"
        if kolom_reagent:
            list_reagent = ["Semua Reagent"] + sorted(df[kolom_reagent].astype(str).str.upper().unique().tolist())
            filter_reagent = st.selectbox(f"Filter Utama (Berdasarkan {kolom_reagent}):", list_reagent)

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

        df_tampil = df.copy()
        if kolom_reagent and filter_reagent != "Semua Reagent":
            df_tampil = df_tampil[df_tampil[kolom_reagent].astype(str).str.upper() == filter_reagent]
        if filter_vendor != "Semua Vendor":
            df_tampil = df_tampil[df_tampil['Vendor'].astype(str) == filter_vendor]
        if filter_status != "Semua Status":
            df_tampil = df_tampil[df_tampil['STATUS'].astype(str).str.upper() == filter_status]
        if filter_lokasi != "Semua Lokasi":
            df_tampil = df_tampil[df_tampil['LOCATION'].astype(str).str.upper() == filter_lokasi]

        st.divider()

        # RINGKASAN DATA
        st.subheader("Ringkasan Kondisi Tangki")
        col_tot1, col_tot2 = st.columns(2)
        total_tangki = len(df_tampil)
        
        if 'QTY' in df_tampil.columns:
            df_tampil['QTY_NUM'] = pd.to_numeric(df_tampil['QTY'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            total_volume = df_tampil['QTY_NUM'].sum()
        else:
            total_volume = 0
            
        col_tot1.metric("Total Keseluruhan Unit Isotank", total_tangki)
        col_tot2.metric("Total Keseluruhan Volume (QTY)", f"{total_volume:,.0f}")
        
        st.markdown("##### Rincian Status Tangki")
        c1, c2, c3, c4 = st.columns(4)
        if 'STATUS' in df_tampil.columns:
            status_series = df_tampil['STATUS'].astype(str).str.upper()
            jml_full = len(status_series[status_series == 'FULL'])
            jml_empty = len(status_series[status_series == 'EMPTY'])
            jml_install = len(status_series[status_series == 'INSTALL'])
            jml_vendor = len(status_series[status_series == 'VENDOR'])
        else:
            jml_full = jml_empty = jml_install = jml_vendor = 0
            
        c1.metric("Status FULL", jml_full)
        c2.metric("Status EMPTY", jml_empty)
        c3.metric("Status INSTALL", jml_install)
        c4.metric("Status VENDOR", jml_vendor)
        
        st.divider()

        # GRAFIK VISUAL
        kolom_grafik1, kolom_grafik2 = st.columns(2)
        with kolom_grafik1:
            st.markdown("**Perbandingan Status Tangki**")
            if 'STATUS' in df_tampil.columns and total_tangki > 0:
                data_status = df_tampil['STATUS'].value_counts().reset_index()
                data_status.columns = ['Status', 'Jumlah']
                fig1 = px.pie(data_status, names='Status', values='Jumlah', hole=0.4)
                fig1.update_traces(textposition='inside', textinfo='value+percent')
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Tidak ada data untuk grafik ini.")
                
        with kolom_grafik2:
            st.markdown("**Posisi Lokasi Tangki**")
            if 'LOCATION' in df_tampil.columns and total_tangki > 0:
                data_lokasi = df_tampil['LOCATION'].value_counts().reset_index()
                data_lokasi.columns = ['Lokasi', 'Jumlah']
                fig2 = px.bar(data_lokasi, x='Lokasi', y='Jumlah', color='Lokasi', text='Jumlah')
                fig2.update_traces(textposition='inside')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Tidak ada data untuk grafik ini.")
                
        st.divider()

        # DATA DETAIL & EXPORT XLSX
        st.subheader("Data Detail Keseluruhan")
        if 'QTY_NUM' in df_tampil.columns:
            df_tampil = df_tampil.drop(columns=['QTY_NUM'])
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_tampil.to_excel(writer, index=False, sheet_name='Monitoring Isotank')
        st.download_button(
            label="📥 Download Data Detail (Format Excel .xlsx)",
            data=buffer.getvalue(),
            file_name="Data_Detail_Isotank.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- BAGIAN FORM INPUT (AUTOFILL & UPDATE) ---
with tab_input:
    st.subheader("Form Input / Update Status Tangki")
    st.info("💡 Caranya: Ketik TANK ID terlebih dahulu. Jika data tangki sudah pernah ada, semua kolom di bawah akan otomatis terisi dengan data terakhirnya.")

    # TANK ID ditaruh di luar form agar memicu deteksi real-time
    input_tank_id = st.text_input("👉 Masukkan TANK ID Anda:", key="input_tank_id_main").strip()

    # Inisialisasi data default kosong
    exist_data = {}
    ditemukan = False

    if input_tank_id:
        # Cari data terakhir (paling bawah di sheet) berdasarkan TANK ID tersebut
        df_match = df_mentah[df_mentah['TANK ID'].astype(str).str.strip() == input_tank_id]
        if not df_match.empty:
            exist_data = df_match.iloc[-1].to_dict()
            ditemukan = True
            st.success(f"🔍 Tangki **{input_tank_id}** ditemukan! Mengisi form otomatis dengan data terakhir. Silakan ganti bagian yang perlu diperbarui.")
        else:
            st.info(f"✨ Tangki **{input_tank_id}** baru belum terdaftar. Silakan isi data dari awal.")

    # Pilihan Dropdown Dinamis
    opsi_vendor = ["ROLIMEX", "DWIJAYA", "ENERGI JAYA INOVASI PT", "ADIMITRA"]
    if not df_mentah.empty and 'Vendor' in df_mentah.columns:
        opsi_vendor = sorted(list(set(opsi_vendor + df_mentah['Vendor'].astype(str).unique().tolist())))
    if "-- Pilih Vendor --" not in opsi_vendor:
        opsi_vendor = ["-- Pilih Vendor --"] + opsi_vendor

    opsi_lokasi = ["WAREHOUSE", "OUTBOUND", "INBOUND", "25KT", "INBOUND- KOE WTR", "INBOUND - SUB KOE"]
    if not df_mentah.empty and 'LOCATION' in df_mentah.columns:
        opsi_lokasi = sorted(list(set(opsi_lokasi + df_mentah['LOCATION'].astype(str).unique().tolist())))
    if "-- Pilih Lokasi --" not in opsi_lokasi:
        opsi_lokasi = ["-- Pilih Lokasi --"] + opsi_lokasi

    # Index Finder untuk Dropdown Autofill
    def get_index(opsi_list, target_val):
        if target_val:
            target_str = str(target_val).strip().upper()
            for idx, opsi in enumerate(opsi_list):
                if str(opsi).strip().upper() == target_str:
                    return idx
        return 0

    # Menyusun layout Form Pengisian
    kolom_form1, kolom_form2, kolom_form3 = st.columns(3)
    
    with kolom_form1:
        st.markdown("**1. Info Utama**")
        
        idx_reagent = get_index(["-- Pilih Reagent --", "ACID", "ESCAID", "LAINNYA"], exist_data.get('Jenis Reagent', exist_data.get('REAGENT', '')))
        input_reagent = st.selectbox("Jenis Reagent / Acid (Wajib)", ["-- Pilih Reagent --", "ACID", "ESCAID", "LAINNYA"], index=idx_reagent)
        
        idx_vendor = get_index(opsi_vendor, exist_data.get('Vendor', ''))
        input_vendor = st.selectbox("Vendor (Wajib)", opsi_vendor, index=idx_vendor)
        
        # Konversi QTY dengan safe_float agar bebas error string/kosong
        qty_awal = safe_float(exist_data.get('QTY', 0.0)) if ditemukan else 0.0
        input_qty = st.number_input("QTY (dalam KG)", min_value=0.0, value=qty_awal, step=1.0, format="%.2f")
        
    with kolom_form2:
        st.markdown("**2. Info Status**")
        
        idx_status = get_index(["-- Pilih Status --", "FULL", "EMPTY", "INSTALL", "VENDOR"], exist_data.get('STATUS', ''))
        input_status = st.selectbox("STATUS (Wajib)", ["-- Pilih Status --", "FULL", "EMPTY", "INSTALL", "VENDOR"], index=idx_status)
        
        idx_lokasi = get_index(opsi_lokasi, exist_data.get('LOCATION', ''))
        input_lokasi = st.selectbox("LOCATION (Wajib)", opsi_lokasi, index=idx_lokasi)
        
        # Konversi QTY ISSUED dengan aman
        qty_issued_awal = safe_float(exist_data.get('QTY ISSUED', 0.0)) if ditemukan else 0.0
        input_qty_issued = st.number_input("QTY ISSUED (KG)", min_value=0.0, value=qty_issued_awal, step=1.0, format="%.2f")
        
        input_date_empty = st.date_input("Date Empty", value=konversi_ke_date(exist_data.get('Date Empty', '')))
        input_ps = st.text_input("PS", value=str(exist_data.get('PS', '')) if ditemukan else "")
        input_cm_in = st.text_input("CM IN", value=str(exist_data.get('CM IN', '')) if ditemukan else "")
        
    with kolom_form3:
        st.markdown("**3. Info Keluar**")
        input_date_in = st.date_input("DATE IN", value=konversi_ke_date(exist_data.get('DATE IN', '')))
        input_po_in = st.text_input("PO IN", value=str(exist_data.get('PO IN', '')) if ditemukan else "")
        input_pr_po_out = st.text_input("PR/PO OUT", value=str(exist_data.get('PR/PO OUT', '')) if ditemukan else "")
        
        # Konversi QTY PR dengan aman
        qty_pr_awal = safe_float(exist_data.get('QTY PR', 0.0)) if ditemukan else 0.0
        input_qty_pr = st.number_input("QTY PR (KG)", min_value=0.0, value=qty_pr_awal, step=1.0, format="%.2f")
        
        input_cm_out = st.text_input("CM OUT", value=str(exist_data.get('CM OUT', '')) if ditemukan else "")
        input_date_out = st.date_input("DATE OUT", value=konversi_ke_date(exist_data.get('DATE OUT', '')))
        
    st.markdown("---")
    tombol_simpan = st.button("💾 Simpan Perubahan ke Google Sheets", type="primary")
    
    if tombol_simpan:
        if input_tank_id == "":
            st.error("❌ Gagal: Masukkan TANK ID terlebih dahulu di kotak atas!")
        elif input_vendor == "-- Pilih Vendor --":
            st.error("❌ Gagal: Kolom 'Vendor' harus dipilih!")
        elif input_reagent == "-- Pilih Reagent --":
            st.error("❌ Gagal: Kolom 'Jenis Reagent / Acid' harus dipilih!")
        elif input_status == "-- Pilih Status --":
            st.error("❌ Gagal: Kolom 'STATUS' harus dipilih!")
        elif input_lokasi == "-- Pilih Lokasi --":
            st.error("❌ Gagal: Kolom 'LOCATION' harus dipilih!")
        else:
            try:
                client = get_gsheets_connection()
                worksheet = client.open_by_url(SPREADSHEET_URL).worksheet(NAMA_SHEET)
                
                str_date_empty = input_date_empty.strftime("%Y-%m-%d") if input_date_empty else ""
                str_date_in = input_date_in.strftime("%Y-%m-%d") if input_date_in else ""
                str_date_out = input_date_out.strftime("%Y-%m-%d") if input_date_out else ""
                
                baris_baru = [
                    input_vendor, input_tank_id, input_qty, "KG", 
                    input_status, input_lokasi, input_qty_issued, str_date_empty, 
                    input_ps, input_cm_in, str_date_in, input_po_in, 
                    input_pr_po_out, input_qty_pr, input_cm_out, str_date_out,
                    input_reagent
                ]
                
                worksheet.append_rows([baris_baru])
                st.cache_data.clear() 
                st.success(f"🎉 Sukses! Data terbaru tangki {input_tank_id} berhasil disimpan ke database Google Sheets.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal saat menyimpan data: {e}")
