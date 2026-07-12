import streamlit as st
import pandas as pd
import plotly.express as px
import os
from openpyxl import load_workbook

# ==========================================
# 1. PENGATURAN AWAL
# ==========================================
st.set_page_config(page_title="Dashboard Isotank", page_icon="🛢️", layout="wide")
st.title("🛢️ Sistem Monitoring Isotank")

# Pastikan nama file ini SAMA PERSIS dengan yang di-upload ke GitHub
FILE_EXCEL = 'WEEKLY STOCK TAKE ISOTANK 01 - 07 JULY 2026.xlsx'
NAMA_SHEET = 'ACID & ESCAID STATUS '

# ==========================================
# 2. FUNGSI AMBIL DATA DARI EXCEL
# ==========================================
@st.cache_data(ttl=2)
def ambil_data():
    # Cek apakah file excel ada di folder
    if not os.path.exists(FILE_EXCEL):
        st.error(f"❌ File Excel '{FILE_EXCEL}' tidak ditemukan di GitHub!")
        return pd.DataFrame()
    
    try:
        # Membaca excel. skiprows=3 berarti kita mengabaikan 3 baris teratas (judul)
        # dan mulai membaca dari baris ke-4 sebagai nama kolom.
        df = pd.read_excel(FILE_EXCEL, sheet_name=NAMA_SHEET, skiprows=3)
        
        # Hapus baris yang kosong (yang tidak punya TANK ID)
        df = df.dropna(subset=['TANK ID'])
        return df
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat membaca Excel: {e}")
        return pd.DataFrame()

df = ambil_data()

# ==========================================
# 3. MEMBUAT TAMPILAN DASHBOARD & FORM
# ==========================================
tab_dashboard, tab_input = st.tabs(["📊 Lihat Dashboard", "📝 Input Data Baru"])

# --- BAGIAN DASHBOARD ---
with tab_dashboard:
    if df.empty:
        st.warning("Data kosong atau belum terbaca.")
    else:
        st.subheader("Ringkasan Kondisi Tangki")
        
        # Membuat 4 Kotak Angka
        col1, col2, col3, col4 = st.columns(4)
        total_tangki = len(df)
        total_volume = df['QTY'].sum()
        jml_full = len(df[df['STATUS'].astype(str).str.upper() == 'FULL'])
        jml_empty = len(df[df['STATUS'].astype(str).str.upper() == 'EMPTY'])
        
        col1.metric("Total Unit Isotank", total_tangki)
        col2.metric("Total Volume (KG)", f"{total_volume:,.0f}")
        col3.metric("Status FULL", jml_full)
        col4.metric("Status EMPTY", jml_empty)
        
        st.divider()
        
        # Membuat Grafik
        kolom_grafik1, kolom_grafik2 = st.columns(2)
        with kolom_grafik1:
            st.markdown("**Perbandingan Status (FULL vs EMPTY)**")
            data_status = df['STATUS'].value_counts().reset_index()
            data_status.columns = ['Status', 'Jumlah']
            fig1 = px.pie(data_status, names='Status', values='Jumlah', hole=0.4, color='Status')
            st.plotly_chart(fig1, use_container_width=True)
            
        with kolom_grafik2:
            st.markdown("**Posisi Lokasi Tangki**")
            data_lokasi = df['LOCATION'].value_counts().reset_index()
            data_lokasi.columns = ['Lokasi', 'Jumlah']
            fig2 = px.bar(data_lokasi, x='Lokasi', y='Jumlah', color='Lokasi')
            st.plotly_chart(fig2, use_container_width=True)
            
        # Menampilkan Tabel Lengkap
        st.subheader("Data Detail")
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- BAGIAN INPUT DATA ---
with tab_input:
    st.subheader("Form Tambah Kedatangan/Status Tangki")
    
    with st.form("form_input", clear_on_submit=True):
        kolom_form1, kolom_form2 = st.columns(2)
        
        with kolom_form1:
            input_vendor = st.text_input("Nama Vendor")
            input_tank_id = st.text_input("TANK ID (Wajib Diisi)")
            input_qty = st.number_input("Jumlah Volume (QTY)", min_value=0.0)
            
        with kolom_form2:
            input_uom = st.selectbox("Satuan", ["KG", "LITER"])
            input_status = st.selectbox("Status", ["FULL", "EMPTY"])
            input_lokasi = st.selectbox("Lokasi", ["WAREHOUSE", "OUTBOUND", "INBOUND", "25KT"])
            
        tombol_simpan = st.form_submit_button("Simpan Data")
        
        if tombol_simpan:
            if input_tank_id.strip() == "":
                st.error("Gagal: TANK ID tidak boleh kosong!")
            else:
                try:
                    # Proses memasukkan data ke Excel
                    wb = load_workbook(FILE_EXCEL)
                    ws = wb[NAMA_SHEET]
                    
                    # Susunan kolom: Kolom A(Kosong), B(Kosong), C(Vendor), D(TankID), E(QTY), F(UoM), G(Status), H(Lokasi)
                    baris_baru = [None, None, input_vendor, input_tank_id, input_qty, input_uom, input_status, input_lokasi]
                    ws.append(baris_baru)
                    
                    wb.save(FILE_EXCEL)
                    st.cache_data.clear() # Refresh aplikasi
                    st.success(f"Data tangki {input_tank_id} berhasil disimpan!")
                except Exception as e:
                    st.error(f"Gagal menyimpan data: {e}")
