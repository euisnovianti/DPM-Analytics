from pathlib import Path
from html import escape
import io
import base64

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import MONTHS, load_workbooks

st.set_page_config(page_title='DPM Analytics | PLN', page_icon=':material/electric_meter:', layout='wide', initial_sidebar_state='expanded')
BASE_DIR = Path(__file__).resolve().parent
css = BASE_DIR / 'assets' / 'style.css'
if css.exists():
    st.markdown(f'<style>{css.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)

COLORS = ['#007BB5', '#00A6B2', '#224D92', '#D39B12', '#5875B9', '#137477', '#8B60A2', '#BD6746']
MONTH_LABELS = dict(zip(MONTHS, ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']))
LABELS = {'BULAN': 'Bulan', 'PEMKWH': 'Pemakaian (kWh)', 'JMLDATA': 'Jumlah pelanggan', 'ULP': 'Unit layanan', 'WILAYAH': 'Wilayah', 'KODE_RBM': 'Kode RBM', 'HARI_BACA': 'Hari baca'}


def number(value, decimals=0):
    return f'{value:,.{decimals}f}'.translate(str.maketrans(',.', '.,'))


def section(kicker, title, caption):
    st.markdown(f'<div class="section-heading"><span class="eyebrow">{escape(kicker)}</span><h2>{escape(title)}</h2><p>{escape(caption)}</p></div>', unsafe_allow_html=True)


def chart_heading(title, caption):
    st.markdown(f'<div class="chart-heading"><h3>{escape(title)}</h3><p>{escape(caption)}</p></div>', unsafe_allow_html=True)


def draw(fig, key, height=340):
    fig.update_layout(
        template='plotly_white', height=height,
        font=dict(family='Arial, sans-serif', size=13, color='#35506B'),
        paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
        margin=dict(t=20, b=25, l=15, r=20),
        legend=dict(title_text='', orientation='h', yanchor='top', y=-0.24, x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor='#FFFFFF', font_size=13, font_color='#173957'),
        separators=',.', transition_duration=250,
    )
    if not any(trace.type == 'pie' for trace in fig.data):
        fig.update_xaxes(showgrid=False, zeroline=False, automargin=True, title_font_size=12)
        fig.update_yaxes(gridcolor='#EAF0F5', zeroline=False, automargin=True, title_font_size=12)
    st.plotly_chart(fig, width='stretch', theme=None, key=key,
                    config={'displaylogo': False, 'scrollZoom': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                            'toImageButtonOptions': {'format': 'png', 'scale': 2}})


@st.cache_data(show_spinner=False)
def load_and_prepare_data(files):
    return load_workbooks(files)


with st.sidebar:
    logo_path = BASE_DIR / 'assets' / 'Logo_PLN.png'
    try:
        logo_data = base64.b64encode(logo_path.read_bytes()).decode('ascii')
        brand_logo = (
            f'<img src="data:image/png;base64,{logo_data}" alt="Logo PLN" '
            'style="width:48px;height:68px;object-fit:contain;flex-shrink:0;display:block;">'
        )
    except OSError:
        brand_logo = '<div class="brand-word">PLN<span></span></div>'
    st.markdown(
        f'<div class="brand">{brand_logo}'
        '<div style="min-width:0;"><strong>DPM Analytics</strong>'
        '<small>Monitoring pembacaan meter</small></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-section">01 <span>Sumber data</span></div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader('Unggah file DPM', type=['xls', 'xlsx'], accept_multiple_files=True, help='Unggah satu atau beberapa file ULP dengan sheet bulanan JAN sampai DES.')
    st.caption('Excel .xls / .xlsx · Bisa unggah beberapa file')
    with st.expander('Panduan format data'):
        st.markdown('Gunakan sheet **JAN–DES** dengan kolom **KODERBM**, **JMLDATA**, dan **PEMKWH**. Header dapat berada di bawah judul lembar.')
        st.caption('Nama ULP mengikuti nama file. Gunakan file dari tahun yang sama agar bulan tidak tercampur.')

if not uploaded_files:
    st.markdown('''<div class="topline"><span>PLN <b>/</b> OPERASIONAL PEMBACAAN METER</span><span class="top-tag">DPM ANALYTICS</span></div>
    <div class="hero"><div class="hero-copy"><span class="hero-kicker">DATA PEMBACAAN METER</span><h1>Pantau pemakaian.<br>Pahami setiap wilayah.</h1><p>Ringkasan kWh, aktivitas pembacaan, dan distribusi RBM dalam satu tampilan.</p></div><div class="hero-art" aria-hidden="true"><div class="art-label">MONITORING DPM</div><div class="art-bars"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><div class="art-rule"></div><span>PEMAKAIAN &nbsp; / &nbsp; WILAYAH &nbsp; / &nbsp; RBM</span></div></div>''', unsafe_allow_html=True)

    st.markdown('''<div class="welcome"><span class="eyebrow">MULAI ANALISIS</span><h2>Data Anda, siap menjadi informasi.</h2><p>Unggah file DPM melalui panel kiri untuk melihat ringkasan dan enam grafik analisis secara otomatis.</p><div class="welcome-steps"><div><b>01</b><strong>Unggah Excel</strong><span>Gabungkan file dari beberapa ULP.</span></div><div><b>02</b><strong>Atur cakupan</strong><span>Pilih bulan, ULP, dan hari baca.</span></div><div><b>03</b><strong>Telusuri hasil</strong><span>Baca grafik dan ekspor rincian.</span></div></div></div>''', unsafe_allow_html=True)
    st.caption('Belum ada data yang ditampilkan. Grafik akan muncul setelah file berhasil dibaca.')
    st.stop()

with st.spinner('Menyiapkan data pembacaan meter...'):
    df_raw, issues = load_and_prepare_data(tuple((f.name, f.getvalue()) for f in uploaded_files))
if issues:
    with st.expander(f'Catatan pembacaan data ({len(issues)})', expanded=True):
        for issue in issues:
            st.warning(issue)
if df_raw.empty:
    st.info('Belum ada data yang dapat ditampilkan. Periksa nama sheet dan header kolom melalui panduan di panel kiri.')
    st.stop()

all_ulp = sorted(df_raw['ULP'].unique())
all_bulan = [m for m in MONTHS if m in df_raw['BULAN'].unique()]
all_hari = sorted(df_raw['HARI_BACA'].unique())
filter_spec = [('filter_ulp', all_ulp), ('filter_bulan', all_bulan), ('filter_hari', all_hari)]
# Menyelaraskan pilihan saat kumpulan file berubah, sebelum widget dibuat.
fingerprint = tuple((f.name, f.size) for f in uploaded_files)
if st.session_state.get('source_fingerprint') != fingerprint:
    for key, options in filter_spec:
        st.session_state[key] = options
    st.session_state['source_fingerprint'] = fingerprint
for key, options in filter_spec:
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in options]

with st.sidebar:
    st.markdown('<div class="sidebar-section">02 <span>Filter analisis</span></div>', unsafe_allow_html=True)
    if st.button('Reset filter', width='stretch'):
        for key, options in filter_spec:
            st.session_state[key] = options
    selected_ulp = st.multiselect('Unit layanan (ULP)', all_ulp, key='filter_ulp')
    selected_bulan = st.multiselect('Bulan', all_bulan, format_func=lambda m: MONTH_LABELS[m], key='filter_bulan')
    selected_hari = st.multiselect('Hari baca', all_hari, key='filter_hari')
    st.markdown('<div class="sidebar-note"><strong>Tampilan mengikuti filter</strong><p>Seluruh ringkasan, grafik, dan ekspor menyesuaikan pilihan Anda.</p></div>', unsafe_allow_html=True)

filtered = df_raw[df_raw['ULP'].isin(selected_ulp) & df_raw['BULAN'].isin(selected_bulan) & df_raw['HARI_BACA'].isin(selected_hari)]
st.sidebar.markdown(f'<div class="context-strip"><span><i></i> Data berhasil dimuat</span><span><b>{len(uploaded_files)}</b> file · <b>{len(selected_ulp)}</b> ULP · <b>{len(selected_bulan)}</b> bulan · <b>{number(len(filtered))}</b> baris terpilih</span></div>', unsafe_allow_html=True)
if filtered.empty:
    st.info('Tidak ada data untuk kombinasi filter ini. Pilih minimal satu ULP, bulan, dan hari baca, atau klik Reset filter.')
    st.stop()

color_map = {ulp: COLORS[i % len(COLORS)] for i, ulp in enumerate(all_ulp)}
plot_args = dict(color='ULP', color_discrete_map=color_map, labels=LABELS, category_orders={'BULAN': MONTHS})
tot_kwh, tot_pelanggan = filtered['PEMKWH'].sum(), filtered['JMLDATA'].sum()
avg_kwh = tot_kwh / tot_pelanggan if tot_pelanggan > 0 else 0
section('01 / RINGKASAN', 'Ringkasan pembacaan meter', 'Indikator utama sesuai cakupan data yang Anda pilih.')
kpis = [
    ('Total pemakaian', number(tot_kwh), 'kWh', 'Akumulasi pemakaian terpilih'),
    ('Pelanggan dibaca', number(tot_pelanggan), 'pembacaan', 'Akumulasi JMLDATA per periode'),
    ('Rata-rata pemakaian', number(avg_kwh, 2), 'kWh / pelanggan', 'Total kWh dibagi total pelanggan'),
    ('RBM aktif', number(filtered['KODE_RBM'].nunique()), 'RBM', 'Kode rute unik pada data terpilih'),
]
for i, (col, (title, value, unit, caption)) in enumerate(zip(st.columns(4), kpis)):
    with col:
        st.markdown(f'<div class="kpi kpi-{i}"><div class="kpi-label">{title}</div><div class="kpi-value">{value}</div><div class="kpi-unit">{unit}</div><div class="kpi-note">{caption}</div></div>', unsafe_allow_html=True)

section('02 / TREN BULANAN', 'Pergerakan dari bulan ke bulan', 'Bandingkan pemakaian energi dan jumlah pembacaan antar unit layanan.')
col_line1, col_line2 = st.columns(2)
with col_line1, st.container(border=True):
    chart_heading('Tren pemakaian kWh', 'Total pemakaian setiap bulan, berdasarkan ULP.')
    monthly_ulp = filtered.groupby(['BULAN', 'ULP'])['PEMKWH'].sum().reset_index()
    monthly_ulp['_order'] = monthly_ulp['BULAN'].map({m: i for i, m in enumerate(MONTHS)})
    fig_line1 = px.line(monthly_ulp.sort_values('_order'), x='BULAN', y='PEMKWH', markers=True, **plot_args)
    fig_line1.update_traces(line_width=3, marker_size=7)
    draw(fig_line1, 'trend_kwh')
with col_line2, st.container(border=True):
    chart_heading('Tren pelanggan dibaca', 'Jumlah pembacaan setiap bulan, berdasarkan ULP.')
    monthly_pel = filtered.groupby(['BULAN', 'ULP'])['JMLDATA'].sum().reset_index()
    monthly_pel['_order'] = monthly_pel['BULAN'].map({m: i for i, m in enumerate(MONTHS)})
    fig_line2 = px.line(monthly_pel.sort_values('_order'), x='BULAN', y='JMLDATA', markers=True, **plot_args)
    fig_line2.update_traces(line_width=3, marker_size=7)
    draw(fig_line2, 'trend_customers')

section('03 / SEBARAN WILAYAH', 'Kontribusi setiap unit layanan', 'Lihat wilayah dengan pemakaian tertinggi dan proporsi kWh antar ULP.')
col_bar1, col_pie = st.columns([1.2, 1])
with col_bar1, st.container(border=True):
    chart_heading('Perbandingan kWh per wilayah', '10 kombinasi wilayah dan ULP dengan pemakaian tertinggi.')
    wilayah_kwh = filtered.groupby(['WILAYAH', 'ULP'])['PEMKWH'].sum().reset_index().sort_values('PEMKWH', ascending=False).head(10)
    fig_wilayah = px.bar(wilayah_kwh, x='WILAYAH', y='PEMKWH', barmode='group', **plot_args)
    fig_wilayah.update_xaxes(type='category')
    draw(fig_wilayah, 'region_kwh', 365)
with col_pie, st.container(border=True):
    chart_heading('Proporsi kWh antar ULP', 'Persentase kontribusi terhadap total pemakaian terpilih.')
    ulp_pie = filtered.groupby('ULP')['PEMKWH'].sum().reset_index()
    if (ulp_pie['PEMKWH'] < 0).any() or ulp_pie['PEMKWH'].sum() <= 0:
        st.info('Proporsi tidak dapat ditampilkan karena total kWh nol atau terdapat total ULP negatif.')
    else:
        fig_pie = px.pie(ulp_pie, values='PEMKWH', names='ULP', **plot_args)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label', insidetextfont=dict(color='white', size=13), marker=dict(line=dict(color='white', width=3)), sort=False)
        draw(fig_pie, 'ulp_share', 365)

section('04 / AKTIVITAS PEMBACAAN', 'Telusuri hari baca dan rute', 'Distribusi pemakaian berdasarkan siklus hari baca dan kode RBM.')
col_hari, col_officer = st.columns([1, 1.2])
with col_hari, st.container(border=True):
    chart_heading('Pemakaian per siklus hari baca', 'Pengelompokan mengikuti karakter akhir kode RBM (A–E).')
    hari_agg = filtered.groupby('HARI_BACA')['PEMKWH'].sum().reset_index().sort_values('HARI_BACA')
    fig_hari = px.bar(hari_agg, x='HARI_BACA', y='PEMKWH', text='PEMKWH', color='PEMKWH', color_continuous_scale=['#76CFDF', '#007BB5', '#224D92'], labels=LABELS)
    fig_hari.update_traces(texttemplate='%{text:,.0f}', textposition='outside', cliponaxis=False)
    fig_hari.update_layout(coloraxis_showscale=False)
    draw(fig_hari, 'reading_cycle', 420)
with col_officer, st.container(border=True):
    chart_heading('Top pemakaian per RBM', '12 kombinasi RBM dan ULP dengan pemakaian tertinggi.')
    rbm_agg = filtered.groupby(['KODE_RBM', 'ULP'])['PEMKWH'].sum().reset_index().sort_values('PEMKWH', ascending=True).tail(12)
    fig_officer = px.bar(rbm_agg, x='PEMKWH', y='KODE_RBM', orientation='h', **plot_args)
    fig_officer.update_yaxes(type='category')
    draw(fig_officer, 'top_rbm', 420)

section('05 / RINCIAN DATA', 'Dari ringkasan ke setiap rute', 'Cari kode RBM atau wilayah, lalu unduh rincian sesuai hasil pencarian.')
with st.container(border=True):
    col_search, col_dl = st.columns([3, 1])
    with col_search:
        search_rbm = st.text_input('Cari kode RBM / wilayah', placeholder='Ketik kode RBM atau wilayah...', key='search_rbm')
    df_table = filtered[['BULAN', 'ULP', 'KODE_RBM', 'WILAYAH', 'HARI_BACA', 'JMLDATA', 'PEMKWH']].copy()
    df_table.columns = ['Bulan', 'ULP', 'Kode RBM', 'Wilayah', 'Hari Baca', 'Jml Pelanggan', 'Total kWh']
    if search_rbm.strip():
        query = search_rbm.strip()
        df_table = df_table[df_table['Kode RBM'].str.contains(query, case=False, na=False, regex=False) | df_table['Wilayah'].str.contains(query, case=False, na=False, regex=False)]
    with col_dl:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_formulas': False, 'strings_to_urls': False}}) as writer:
            df_table.to_excel(writer, sheet_name='Data_Billing', index=False)
            worksheet = writer.sheets['Data_Billing']
            header_format = writer.book.add_format({'bold': True, 'bg_color': '#007BB5', 'font_color': 'white'})
            for idx, column in enumerate(df_table.columns):
                worksheet.write(0, idx, column, header_format)
            worksheet.freeze_panes(1, 0)
            worksheet.set_column(0, 0, 12)
            worksheet.set_column(1, 1, 25)
            worksheet.set_column(2, 6, 20)
            worksheet.autofilter(0, 0, len(df_table), 6)
        st.markdown('<div class="download-spacer"></div>', unsafe_allow_html=True)
        st.download_button('Ekspor Excel', data=output.getvalue(), file_name='Laporan_Billing_DPM.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', width='stretch')
    st.caption(f'{number(len(df_table))} baris ditampilkan · Ekspor mengikuti filter dan pencarian aktif')
    st.dataframe(df_table.style.format({'Jml Pelanggan': lambda v: number(v), 'Total kWh': lambda v: number(v)}), width='stretch', hide_index=True, height=400)

st.markdown('<div class="footer"><strong>DPM Analytics</strong><span>Monitoring pembacaan meter · PLN</span></div>', unsafe_allow_html=True)
