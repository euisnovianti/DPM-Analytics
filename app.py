import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# 1. Konfigurasi Halaman Penuh
st.set_page_config(
    page_title="Dashboard Billing & Monitoring kWh",
    page_icon="bar-chart",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load local CSS untuk gaya SIPERTI
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    pass

# Palet Warna PLN / Visual Identity
PALETTE = {
    "primary": "#00288e",
    "secondary": "#0284c7",
    "accent": "#f59e0b",
    "danger": "#ef4444",
    "success": "#10b981",
    "bg_light": "#f8fafc"
}

# 2. Fungsi Ekstraksi & Parsing Data DPM
@st.cache_data
def load_and_prepare_data(uploaded_files):
    """
    Membaca dan menstandarisasi file DPM dari berbagai ULP
    Mengekstrak ULP, Wilayah, Hari Baca dari KODERBM
    """
    records = []
    
    def parse_sheet(file_obj, ulp_name):
        excel_obj = pd.ExcelFile(file_obj)
        month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
        
        for m in month_names:
            if m in excel_obj.sheet_names:
                df = pd.read_excel(excel_obj, sheet_name=m)
                # Standarisasi header sheet bulanan
                if len(df) > 0 and 'Unnamed: 0' in df.columns:
                    # Ambil baris data setelah header koderbm, dan hanya 3 kolom pertama
                    df_clean = df.iloc[1:, :3].copy()
                    df_clean.columns = ['KODE_RBM', 'JMLDATA', 'PEMKWH']
                    df_clean['BULAN'] = m
                    df_clean['ULP'] = ulp_name
                    records.append(df_clean)

    if not uploaded_files:
        return pd.DataFrame()

    for f in uploaded_files:
        # Menentukan nama ULP dari nama file (format penamaan sama)
        fname = f.name.upper()
        if "GK" in fname or "GARUT" in fname:
            ulp = "ULP Garut Kota"
        elif "PMP" in fname or "PAMEUNGPEUK" in fname:
            ulp = "ULP Pameungpeuk"
        else:
            ulp = f"ULP {f.name.split('.')[0]}"
        parse_sheet(f, ulp)

    if not records:
        return pd.DataFrame()

    df_all = pd.concat(records, ignore_index=True)
    
    # Pembersihan tipe data numerik
    df_all['PEMKWH'] = pd.to_numeric(df_all['PEMKWH'], errors='coerce').fillna(0)
    df_all['JMLDATA'] = pd.to_numeric(df_all['JMLDATA'], errors='coerce').fillna(0)
    df_all['KODE_RBM'] = df_all['KODE_RBM'].astype(str).str.strip().str.upper()

    # Ekstraksi dimensi PLN dari KODERBM:
    # 1. Hari Baca (Karakter terakhir: A-E -> Hari 1 - 5)
    hari_map = {'A': 'Hari 1 (A)', 'B': 'Hari 2 (B)', 'C': 'Hari 3 (C)', 'D': 'Hari 4 (D)', 'E': 'Hari 5 (E)'}
    df_all['HARI_KODE'] = df_all['KODE_RBM'].str[-1]
    df_all['HARI_BACA'] = df_all['HARI_KODE'].map(hari_map).fillna("Lainnya")
    
    # 2. Wilayah / Posko (Karakter ke 3-5 KODERBM)
    df_all['WILAYAH'] = df_all['KODE_RBM'].str[2:5]
    
    # 3. Estimasi Penugasan Petugas
    df_all['PETUGAS'] = "Petugas " + df_all['WILAYAH']

    return df_all

# 3. Sidebar: Upload & Filter Global
st.sidebar.markdown("### <span class='material-icons' style='vertical-align: bottom;'>analytics</span> Billing Analytics Control", unsafe_allow_html=True)
uploaded_files = st.sidebar.file_uploader("Upload File DPM (.xls/.xlsx)", type=["xls", "xlsx"], accept_multiple_files=True)

# Gunakan data dari file yang diunggah
if uploaded_files:
    df_raw = load_and_prepare_data(uploaded_files)
else:
    st.info("Silakan unggah satu atau beberapa file DPM melalui sidebar untuk memulai analisis.")
    st.stop()

if df_raw.empty:
    st.warning("Data tidak dapat dibaca atau struktur kosong.")
    st.stop()

# --- FILTER SECTION ---
st.sidebar.markdown("---")
st.sidebar.markdown("### <span class='material-icons' style='vertical-align: bottom;'>filter_alt</span> Filter Global", unsafe_allow_html=True)

all_ulp = sorted(df_raw['ULP'].unique())
selected_ulp = st.sidebar.multiselect("Pilih ULP", options=all_ulp, default=all_ulp)

all_bulan = list(df_raw['BULAN'].unique())
selected_bulan = st.sidebar.multiselect("Pilih Bulan", options=all_bulan, default=all_bulan)

all_hari = sorted(df_raw['HARI_BACA'].unique())
selected_hari = st.sidebar.multiselect("Pilih Hari Baca", options=all_hari, default=all_hari)

# Filter dataframe
df_filtered = df_raw[
    (df_raw['ULP'].isin(selected_ulp)) &
    (df_raw['BULAN'].isin(selected_bulan)) &
    (df_raw['HARI_BACA'].isin(selected_hari))
]

# 4. KPI Calculations
tot_kwh = df_filtered['PEMKWH'].sum()
tot_pelanggan = df_filtered['JMLDATA'].sum()
avg_kwh = (tot_kwh / tot_pelanggan) if tot_pelanggan > 0 else 0
tot_rbm = df_filtered['KODE_RBM'].nunique()

# 5. KPI Summary Cards (Horizontal)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class='bento-card'>
        <div class='bento-title'>Total Pemakaian kWh</div>
        <div class='bento-value'>{tot_kwh:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi2:
    st.markdown(f"""
    <div class='bento-card'>
        <div class='bento-title'>Total Pelanggan Dibaca</div>
        <div class='bento-value'>{tot_pelanggan:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi3:
    st.markdown(f"""
    <div class='bento-card'>
        <div class='bento-title'>Rata-rata kWh/Pelanggan</div>
        <div class='bento-value'>{avg_kwh:.2f}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi4:
    st.markdown(f"""
    <div class='bento-card'>
        <div class='bento-title'>Jumlah RBM Aktif</div>
        <div class='bento-value'>{tot_rbm:,}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 6. Row 1: Tren Garis (kWh & Pelanggan)
col_line1, col_line2 = st.columns(2)

with col_line1:
    st.markdown("<h4 style='color: #4b5563; font-size: 16px;'>Tren Pemakaian kWh per Bulan</h4>", unsafe_allow_html=True)
    monthly_ulp = df_filtered.groupby(['BULAN', 'ULP'])['PEMKWH'].sum().reset_index()
    fig_line1 = px.line(monthly_ulp, x='BULAN', y='PEMKWH', color='ULP', markers=True, color_discrete_sequence=[PALETTE['primary'], PALETTE['accent']])
    fig_line1.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_line1, use_container_width=True)

with col_line2:
    st.markdown("<h4 style='color: #4b5563; font-size: 16px;'>Tren Pelanggan Dibaca per Bulan</h4>", unsafe_allow_html=True)
    monthly_pel = df_filtered.groupby(['BULAN', 'ULP'])['JMLDATA'].sum().reset_index()
    fig_line2 = px.line(monthly_pel, x='BULAN', y='JMLDATA', color='ULP', markers=True, color_discrete_sequence=[PALETTE['secondary'], PALETTE['success']])
    fig_line2.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_line2, use_container_width=True)

st.markdown("---")

# 7. Row 2: Perbandingan Wilayah & Proporsi ULP
col_bar1, col_pie = st.columns([1.2, 1])

with col_bar1:
    st.markdown("<h4 style='color: #4b5563; font-size: 16px;'>Perbandingan kWh per Wilayah</h4>", unsafe_allow_html=True)
    wilayah_kwh = df_filtered.groupby(['WILAYAH', 'ULP'])['PEMKWH'].sum().reset_index().sort_values(by='PEMKWH', ascending=False).head(10)
    fig_wilayah = px.bar(wilayah_kwh, x='WILAYAH', y='PEMKWH', color='ULP', barmode='group', color_discrete_sequence=[PALETTE['secondary'], PALETTE['accent']])
    fig_wilayah.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_wilayah, use_container_width=True)

with col_pie:
    st.markdown("<h4 style='color: #4b5563; font-size: 16px;'>Proporsi kWh antar ULP</h4>", unsafe_allow_html=True)
    ulp_pie = df_filtered.groupby('ULP')['PEMKWH'].sum().reset_index()
    fig_pie = px.pie(ulp_pie, values='PEMKWH', names='ULP', color_discrete_sequence=[PALETTE['primary'], PALETTE['secondary'], PALETTE['success']])
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# 8. Row 3: Distribusi Hari Baca & Top Petugas
col_hari, col_officer = st.columns([1, 1.2])

with col_hari:
    st.markdown("<h4 style='color: #4b5563; font-size: 16px;'>Distribusi Pemakaian per Siklus Hari Baca</h4>", unsafe_allow_html=True)
    hari_agg = df_filtered.groupby('HARI_BACA')['PEMKWH'].sum().reset_index().sort_values(by='HARI_BACA')
    fig_hari = px.bar(hari_agg, x='HARI_BACA', y='PEMKWH', text='PEMKWH', color='PEMKWH', color_continuous_scale="Blues")
    fig_hari.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_hari.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
    st.plotly_chart(fig_hari, use_container_width=True)

with col_officer:
    st.markdown("<h4 style='color: #4b5563; font-size: 16px;'>Top Pemakaian per Petugas / RBM</h4>", unsafe_allow_html=True)
    rbm_agg = df_filtered.groupby(['KODE_RBM', 'ULP'])['PEMKWH'].sum().reset_index().sort_values(by='PEMKWH', ascending=True).tail(12)
    fig_officer = px.bar(rbm_agg, x='PEMKWH', y='KODE_RBM', orientation='h', color='ULP', color_discrete_sequence=[PALETTE['primary'], PALETTE['accent']])
    fig_officer.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_officer, use_container_width=True)

st.markdown("---")

# 9. Bottom Table & Export
col_search, col_dl = st.columns([3, 1])
with col_search:
    search_rbm = st.text_input("Cari Kode RBM / Wilayah:", placeholder="Ketik kode RBM...")

df_table = df_filtered[['BULAN', 'ULP', 'KODE_RBM', 'WILAYAH', 'HARI_BACA', 'JMLDATA', 'PEMKWH']].copy()
df_table.columns = ['Bulan', 'ULP', 'Kode RBM', 'Wilayah', 'Hari Baca', 'Jml Pelanggan', 'Total kWh']

if search_rbm:
    df_table = df_table[df_table['Kode RBM'].str.contains(search_rbm, case=False, na=False)]

# Pandas Styler
def style_table(styler):
    styler.set_table_styles([
        {'selector': 'thead th', 'props': [('background-color', '#0f766e'), ('color', 'white'), ('font-weight', 'bold')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f8fafc')]}
    ])
    return styler

styled_df = df_table.style.pipe(style_table).format({'Jml Pelanggan': "{:,.0f}", 'Total kWh': "{:,.0f}"})
st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)

with col_dl:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_table.to_excel(writer, sheet_name='Data_Billing', index=False)
    
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    st.download_button(
        label="Ekspor Excel",
        icon=":material/download:",
        data=output.getvalue(),
        file_name="Laporan_Billing_DPM.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
