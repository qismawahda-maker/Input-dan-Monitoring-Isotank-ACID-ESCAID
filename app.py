import streamlit as st
import pandas as pd
import plotly.express as px
import os
from openpyxl import load_workbook

# -------------------------------------------------------------
# 1. KONFIGURASI HALAMAN DAN VARIABEL UTAMA
# -------------------------------------------------------------
st.set_page_config(page_title="Dashboard Isotank", page_icon="🛢️", layout="wide")
st.title("🛢️ Dashboard & Input Data Isotank")

# NAMA FILE HARUS SAMA PERSIS dengan yang ada di GitHub Anda
FILE_NAME = 'WEEKLY STOCK TAKE ISOTANK 01 - 07 JULY 2026.xlsx'
SHEET_NAME = 'ACID & ESCAID STATUS '

# -------------------------------------------------------------
# 2. FUNGSI UNTUK MEMBACA DATA (VIEW)
# -------------------------------------------------------------
# Menggunakan @st.cache_data agar aplikasi tidak melambat saat membaca Excel berulang kali,
# tetapi akan mengambil data terbaru (ttl=5 detik) jika ada perubahan.
@st.cache_data(ttl=5)
def get_data():
    if not os.path.exists(FILE_NAME):
        st.error(f"File {FILE_NAME} tidak ditemukan di repository!")
        return pd.DataFrame()
    
    # Membaca data. skiprows=3 karena berdasarkan screenshot, baris header ada di baris ke-4
    df = pd.read_excel(FILE_NAME, sheet_name=SHEET_NAME, skiprows=3)
    
    # Mengambil kolom yang penting saja (B = TANK ID, C = QTY, D = UoM, E = STATUS, F = LOCATION)
    # Sesuaikan nama kolom ini jika berbeda di file Excel Anda yang sebenarnya
    try:
        df_clean = df[['Vendor', 'TANK ID', 'QTY', 'UoM', 'STATUS', 'LOCATION']].copy()
        df_clean = df_clean.dropna(subset=['TANK ID']) # Hapus baris kosong yang tidak ada ID tangkinya
        return df_clean
    except KeyError:
        st.error("Format header/kolom di Excel tidak sesuai dengan yang diharapkan kode. Pastikan header ada di baris ke-4 dan namanya persis 'Vendor', 'TANK ID', dll.")
        return df

df = get_data()

# -------------------------------------------------------------
# 3. MEMBUAT DUA HALAMAN (TABS)
# -------------------------------------------------------------
tab1, tab2 = st.tabs(["📊 Dashboard Monitoring", "📝 Form Input Data Baru"])

# =============================================================
# TAB 1: DASHBOARD (VIEW DATA)
# =============================================================
with tab1:
    if not df.empty:
        # A. Bagian Kartu KPI (Ringkasan Angka)
        st.subheader("Ringkasan Data Saat Ini")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        total_tangki = len(df)
        total_qty = df['QTY'].sum()
        tangki_full = len(df[df['STATUS'].astype(str).str.upper() == 'FULL'])
        tangki_empty = len(df[df['STATUS'].astype(str).str.upper() == 'EMPTY'])
        
        kpi1.metric("Total Isotank", total_tangki)
        kpi2.metric("Total Volume (KG)", f"{total_qty:,.0f}")
        kpi3.metric("Status FULL", tangki_full)
        kpi4.metric("Status EMPTY", tangki_empty)
        
        st.markdown("---")
        
        # B. Bagian Grafik Interaktif
        col_grafik1, col_grafik2 = st.columns(2)
        
        with col_grafik1:
            st.markdown("**Persentase Status Tangki**")
            status_df = df['STATUS'].value_counts().reset_index()
            status_df.columns = ['Status', 'Jumlah']
            fig_pie = px.pie(status_df, names='Status', values='Jumlah', hole=0.3, color='Status')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_grafik2:
            st.markdown("**Sebaran Lokasi Tangki**")
            loc_df = df['LOCATION'].value_counts().reset_index()
            loc_df.columns = ['Lokasi', 'Jumlah']
            fig_bar = px.bar(loc_df, x='Lokasi', y='Jumlah', color='Lokasi')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # C. Tabel Data Detail
        st.subheader("Tabel Detail Isotank")
        # Menambahkan fitur pencarian/filter bawaan dataframe
        st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================
# TAB 2: INPUT DATA BARU (SUBMIT DATA)
# =============================================================
with tab2:
    st.subheader("Masukkan Data Kedatangan/Keberangkatan Tangki Baru")
    
    # st.form memastikan data dikirim serentak saat tombol diklik (tidak reload per kolom isian)
    with st.form("form_tambah_tangki", clear_on_submit=True):
        col_input1, col_input2 = st.columns(2)
        
        with col_input1:
            input_vendor = st.text_input("Nama Vendor")
            input_tank = st.text_input("TANK ID (Nomor Isotank)")
            input_qty = st.number_input("Jumlah QTY", min_value=0.0)
            
        with col_input2:
            input_uom = st.selectbox("Satuan", ["KG", "L"])
            input_status = st.selectbox("Status Tangki", ["FULL", "EMPTY"])
            input_loc = st.selectbox("Lokasi", ["WAREHOUSE", "OUTBOUND", "INBOUND", "25KT"])
            
        btn_submit = st.form_submit_button("Simpan Data ke Excel")
        
        # Logika ketika tombol submit ditekan
        if btn_submit:
            if input_tank == "":
                st.error("Tolong isi Nomor TANK ID terlebih dahulu!")
            else:
                try:
                    # 1. Buka file excel tanpa merusak isinya (openpyxl)
                    wb = load_workbook(FILE_NAME)
                    ws = wb[SHEET_NAME]
                    
                    # 2. Data baru yang akan dimasukkan
                    # CATATAN: Urutan ini (Kolom A, B, C, dst) harus pas dengan posisi di Excel.
                    # Asumsi berdasarkan gambar: A=Kosong, B=Kosong, C=Vendor, D=TankID, E=QTY, F=UoM, G=Status, H=Lokasi
                    baris_baru = [None, None, input_vendor, input_tank, input_qty, input_uom, input_status, input_loc]
                    
                    # 3. Tambahkan ke baris paling bawah
                    ws.append(baris_baru)
                    
                    # 4. Simpan kembali file Excel-nya
                    wb.save(FILE_NAME)
                    
                    # 5. Refresh cache agar data baru langsung muncul di Dashboard
                    st.cache_data.clear()
                    st.success(f"Berhasil! Tangki {input_tank} telah ditambahkan ke data.")
                
                except Exception as error_msg:
                    st.error(f"Gagal menyimpan data. Detail error: {error_msg}")
