#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MONSTERDOG_METRICS_ULTIMATE_TRIPLED
Pipeline autonome : fusion métriques → Z-score → QR → PDF → Dash.
"""

import os, glob, json, time, webbrowser
import numpy as np
import pandas as pd
from scipy import stats
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import qrcode
import dash, dash_table, dash_core_components as dcc, dash_html_components as html
from dash.dependencies import Input, Output

###############################################################################
# 0. CONFIGURATION GLOBALE
###############################################################################
THRESHOLD_Z = 3.0          # σ-cut
FREQ_SACREE = 11987.8589   # Hz pivot
TS = time.strftime('%Y%m%d_%H%M%S')
PDF_NAME = f"DECORTIFICUM_ANOMALIES_{TS}.pdf"

###############################################################################
# 1. INGESTION & FUSION
###############################################################################
def load_metrics(path='.', patterns=('*.csv', '*.xlsx')):
    frames = []
    for p in patterns:
        for file in glob.glob(os.path.join(path, p)):
            if file.endswith('.csv'):
                frames.append(pd.read_csv(file))
            else:
                frames.append(pd.read_excel(file))
    df = pd.concat(frames, ignore_index=True).infer_objects()
    df.columns = [c.strip().lower() for c in df.columns]
    df['timestamp'] = pd.Timestamp.utcnow()
    return df

###############################################################################
# 2. ANOMALIE Z-SCORE
###############################################################################
def extract_anomalies(df, z=THRESHOLD_Z):
    numeric = df.select_dtypes(include=np.number)
    z_scores = np.abs(stats.zscore(numeric, nan_policy='omit'))
    mask = (z_scores > z).any(axis=1)
    anomalies = df.loc[mask]
    anomalies.to_csv('anomalies.csv', index=False)
    return anomalies

###############################################################################
# 3. SIGIL QR
###############################################################################
def make_qr(text, out_dir='qr_sigils'):
    os.makedirs(out_dir, exist_ok=True)
    filename = os.path.join(out_dir, f"sigil_{hash(text)}.png")
    img = qrcode.make(text)
    img.save(filename)
    return filename

###############################################################################
# 4. EXPORT PDF RITUEL
###############################################################################
def build_pdf(anomalies, pdf_path=PDF_NAME):
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Page de garde
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height-72, "MONSTERDOG – Rapport Décortificum")
    c.setFont("Helvetica", 12)
    c.drawString(72, height-100, f"Généré : {TS} | Freq sacrée : {FREQ_SACREE} Hz")
    c.showPage()

    # Tableau simplifié
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height-72, "Anomalies détectées (Top 20)")
    c.setFont("Helvetica", 10)
    for i, row in anomalies.head(20).iterrows():
        y = height-100 - 12*i
        c.drawString(72, y, json.dumps(row.to_dict())[:95] + '…')
    c.showPage()

    # QR sigils
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height-72, "Sigils QR (limités à 6)")
    for i, row in anomalies.head(6).iterrows():
        qr_path = make_qr(json.dumps(row.to_dict()))
        c.drawImage(qr_path, 72 + (i%3)*160, height-200 - (i//3)*180, width=128, height=128)
    c.save()
    print(f"[PDF] {pdf_path} prêt.")

###############################################################################
# 5. DASH BLUEPRINT
###############################################################################
def run_dash(df):
    app = dash.Dash(__name__)
    app.layout = html.Div([
        html.H2("MONSTERDOG – Anomalies Décortificum"),
        dash_table.DataTable(
            id='table', data=df.to_dict('records'), page_size=15,
            style_cell={'textAlign': 'left'}
        ),
        dcc.Graph(id='zgraph'),
        dcc.Interval(id='refresh', interval=60_000, n_intervals=0)
    ])

    @app.callback(Output('zgraph', 'figure'), Input('refresh', 'n_intervals'))
    def update_graph(_):
        zn = np.abs(stats.zscore(df.select_dtypes(include=np.number), nan_policy='omit'))
        fig = {
            'data': [{'y': zn.flatten(), 'type': 'scatter', 'mode': 'markers'}],
            'layout': {'title': 'Distribution des |Z|'}
        }
        return fig

    webbrowser.open("http://127.0.0.1:8050")
    app.run_server(debug=False)

###############################################################################
# 6. BOUCLE « TRIPLE » & LANCEMENT
###############################################################################
def main():
    base = load_metrics()
    anomalies1 = extract_anomalies(base)
    anomalies2 = extract_anomalies(pd.concat([base, base]))
    anomalies3 = extract_anomalies(pd.concat([base]*3))

    all_anoms = pd.concat([anomalies1, anomalies2, anomalies3]).drop_duplicates()
    build_pdf(all_anoms)
    print(f"[CSV] anomalies.csv exporté – {len(all_anoms)} lignes.")
    run_dash(all_anoms)

if __name__ == "__main__":
    main()

