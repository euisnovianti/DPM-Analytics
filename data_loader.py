"""Pembacaan workbook DPM, tanpa ketergantungan pada antarmuka."""
from io import BytesIO
from pathlib import Path
import re

import pandas as pd

MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
ALIASES = {'MAY': 'MEI', 'AGU': 'AGS', 'AUG': 'AGS', 'OCT': 'OKT', 'DEC': 'DES'}
HEADER_ALIASES = {
    'KODERBM': 'KODE_RBM', 'JMLDATA': 'JMLDATA', 'JUMLAHDATA': 'JMLDATA',
    'PEMKWH': 'PEMKWH',
}


def normalize_header(value):
    return re.sub(r'[^A-Z0-9]', '', str(value).upper())


def infer_ulp(filename):
    name = Path(filename).stem.upper()
    if 'GK' in name or 'GARUT' in name:
        return 'ULP Garut Kota'
    if 'PMP' in name or 'PAMEUNGPEUK' in name:
        return 'ULP Pameungpeuk'
    return f'ULP {Path(filename).stem}'


def load_workbooks(files):
    """files adalah pasangan (nama, bytes); file gagal tidak membatalkan file lain."""
    records, issues = [], []
    for filename, contents in files:
        try:
            with pd.ExcelFile(BytesIO(contents)) as workbook:
                recognized = 0
                for sheet in workbook.sheet_names:
                    month = ALIASES.get(sheet.strip().upper(), sheet.strip().upper())
                    if month not in MONTHS:
                        continue
                    recognized += 1
                    try:
                        raw = pd.read_excel(workbook, sheet_name=sheet, header=None)
                        if raw.empty:
                            continue
                        header_row, positions = None, {}
                        # Mendukung header langsung maupun judul di atas header.
                        for idx, row in raw.head(30).iterrows():
                            mapped = {HEADER_ALIASES[normalize_header(v)]: i
                                      for i, v in enumerate(row)
                                      if normalize_header(v) in HEADER_ALIASES}
                            if len(mapped) == 3:
                                header_row, positions = idx, mapped
                                break
                        if header_row is None:
                            issues.append(f'{filename} / {sheet}: header KODERBM, JMLDATA, PEMKWH tidak ditemukan.')
                            continue
                        clean = raw.iloc[header_row + 1:, [positions[c] for c in ['KODE_RBM', 'JMLDATA', 'PEMKWH']]].copy()
                        clean.columns = ['KODE_RBM', 'JMLDATA', 'PEMKWH']
                        code = clean['KODE_RBM'].astype('string').str.strip().str.upper()
                        valid = code.notna() & code.ne('') & ~code.str.match(r'^(TOTAL|GRAND\s*TOTAL|JUMLAH|SUB\s*TOTAL)(\b|$)', na=False)
                        clean = clean.loc[valid].copy()
                        clean['KODE_RBM'] = code.loc[valid]
                        for column in ['JMLDATA', 'PEMKWH']:
                            number = pd.to_numeric(clean[column], errors='coerce')
                            bad = number.isna() | number.isin([float('inf'), float('-inf')])
                            if bad.any():
                                issues.append(f'{filename} / {sheet}: {int(bad.sum())} nilai {column} kosong/tidak valid dihitung sebagai 0.')
                            clean[column] = number.mask(bad, 0)
                        clean['BULAN'], clean['ULP'] = month, infer_ulp(filename)
                        records.append(clean)
                    except Exception:
                        issues.append(f'{filename} / {sheet}: lembar tidak dapat dibaca. Periksa format datanya.')
                if recognized == 0:
                    issues.append(f'{filename}: tidak ada sheet bulanan JAN sampai DES yang dikenali.')
        except Exception:
            issues.append(f'{filename}: file tidak dapat dibuka. Pastikan berupa Excel yang valid dan tidak diproteksi kata sandi.')
    if not records:
        return pd.DataFrame(), issues
    result = pd.concat(records, ignore_index=True)
    result['HARI_KODE'] = result['KODE_RBM'].str[-1]
    result['HARI_BACA'] = result['HARI_KODE'].map({c: f'Hari {i} ({c})' for i, c in enumerate('ABCDE', 1)}).fillna('Lainnya')
    result['WILAYAH'] = result['KODE_RBM'].str[2:5]
    result['PETUGAS'] = 'Petugas ' + result['WILAYAH']
    return result, issues
