#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 MÓDULO 3: app_ligamx.py
 Orquestador Principal de Streamlit · TERMINAL SHARP: LIGA MX
 - Sin decoradores @st.cache_data que congelen los datos
 - Gestión reactiva en st.session_state.df_ligamx
 - Carga por defecto de 'ligamx_stats_actualizado.csv'
 - Sidebar con st.file_uploader en caliente + botón de refresco
 - Sincronización automática de jornada con sync_espn_ligamx.py
 - Vista A: Radar Ejecutivo + Cartelera en Cuadrícula (3 columnas)
 - Vista B: Expediente Cuantitativo Completo del Partido
==============================================================
"""

import os
import hashlib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from sync_espn_ligamx import (
    ESPN_LIGA_MX_IDS,
    EMOJIS_LIGA_MX,
    obtener_calendario_ligamx,
    escudo_ligamx_html,
    normalizar_equipo_para_df,
)
from engine_ligamx import (
    LINEA_CORNERS_DEFAULT,
    MATRIZ_MAX_GOLES,
    calcular_probabilidades_partido,
    formatear_momio_justo,
)

# ==============================================================
# 1. CONFIGURACIÓN DE PÁGINA Y CONSTANTES
# ==============================================================
st.set_page_config(
    page_title="Terminal Sharp · Liga MX",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_DEFAULT_PATH = "ligamx_stats_actualizado.csv"
CSV_LEGACY_PATH = "ligamx_stats_completo.csv"
COLUMNAS_REQUERIDAS = {
    "Equipo", "xG_favor", "xGA_contra", "Forma", "Jerarquia",
    "Corners_Favor", "Corners_Contra",
}

DATOS_BASE_LIGA_MX = [
    {"Equipo": "América", "xG_favor": 1.88, "xGA_contra": 1.02, "Forma": 0.82, "Jerarquia": 9.5, "Corners_Favor": 5.8, "Corners_Contra": 4.1},
    {"Equipo": "Cruz Azul", "xG_favor": 1.82, "xGA_contra": 0.98, "Forma": 0.80, "Jerarquia": 9.0, "Corners_Favor": 5.9, "Corners_Contra": 3.9},
    {"Equipo": "Toluca", "xG_favor": 1.79, "xGA_contra": 1.15, "Forma": 0.76, "Jerarquia": 8.6, "Corners_Favor": 5.5, "Corners_Contra": 4.5},
    {"Equipo": "Tigres UANL", "xG_favor": 1.72, "xGA_contra": 1.05, "Forma": 0.72, "Jerarquia": 9.2, "Corners_Favor": 6.1, "Corners_Contra": 4.2},
    {"Equipo": "Monterrey", "xG_favor": 1.70, "xGA_contra": 1.08, "Forma": 0.70, "Jerarquia": 9.1, "Corners_Favor": 5.7, "Corners_Contra": 4.3},
    {"Equipo": "Guadalajara", "xG_favor": 1.56, "xGA_contra": 1.04, "Forma": 0.74, "Jerarquia": 8.7, "Corners_Favor": 5.4, "Corners_Contra": 4.4},
    {"Equipo": "Pumas UNAM", "xG_favor": 1.52, "xGA_contra": 1.18, "Forma": 0.62, "Jerarquia": 8.2, "Corners_Favor": 5.2, "Corners_Contra": 4.7},
    {"Equipo": "Pachuca", "xG_favor": 1.58, "xGA_contra": 1.26, "Forma": 0.60, "Jerarquia": 8.3, "Corners_Favor": 5.6, "Corners_Contra": 4.6},
    {"Equipo": "León", "xG_favor": 1.49, "xGA_contra": 1.28, "Forma": 0.64, "Jerarquia": 7.9, "Corners_Favor": 5.1, "Corners_Contra": 4.8},
    {"Equipo": "Atlético de San Luis", "xG_favor": 1.46, "xGA_contra": 1.32, "Forma": 0.58, "Jerarquia": 7.2, "Corners_Favor": 4.8, "Corners_Contra": 5.0},
    {"Equipo": "Atlas", "xG_favor": 1.28, "xGA_contra": 1.24, "Forma": 0.55, "Jerarquia": 7.4, "Corners_Favor": 4.6, "Corners_Contra": 4.9},
    {"Equipo": "Tijuana", "xG_favor": 1.42, "xGA_contra": 1.44, "Forma": 0.56, "Jerarquia": 7.1, "Corners_Favor": 4.9, "Corners_Contra": 5.2},
    {"Equipo": "Necaxa", "xG_favor": 1.34, "xGA_contra": 1.38, "Forma": 0.50, "Jerarquia": 6.9, "Corners_Favor": 4.5, "Corners_Contra": 5.3},
    {"Equipo": "Santos Laguna", "xG_favor": 1.31, "xGA_contra": 1.52, "Forma": 0.52, "Jerarquia": 7.3, "Corners_Favor": 4.7, "Corners_Contra": 5.4},
    {"Equipo": "Puebla", "xG_favor": 1.22, "xGA_contra": 1.58, "Forma": 0.42, "Jerarquia": 6.5, "Corners_Favor": 4.4, "Corners_Contra": 5.6},
    {"Equipo": "Querétaro", "xG_favor": 1.18, "xGA_contra": 1.55, "Forma": 0.44, "Jerarquia": 6.4, "Corners_Favor": 4.3, "Corners_Contra": 5.5},
    {"Equipo": "Mazatlán FC", "xG_favor": 1.20, "xGA_contra": 1.60, "Forma": 0.40, "Jerarquia": 6.3, "Corners_Favor": 4.2, "Corners_Contra": 5.7},
    {"Equipo": "FC Juárez", "xG_favor": 1.19, "xGA_contra": 1.64, "Forma": 0.38, "Jerarquia": 6.2, "Corners_Favor": 4.4, "Corners_Contra": 5.8},
]


# ==============================================================
# 2. ESTILOS CSS "CYBER-QUANT SPORTSBOOK UI"
# ==============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&family=Orbitron:wght@700;900&display=swap');

    [data-testid="stToolbar"] {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    .block-container {
        padding-top: 1.3rem !important;
        padding-bottom: 3rem !important;
        max-width: 1420px !important;
    }

    .stApp {
        background-color: #06090e;
        background-image:
            radial-gradient(at 15% 5%, rgba(0, 255, 157, 0.06) 0px, transparent 45%),
            radial-gradient(at 85% 10%, rgba(255, 215, 0, 0.05) 0px, transparent 45%),
            radial-gradient(at 50% 90%, rgba(0, 195, 255, 0.04) 0px, transparent 50%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar Cyber-Quant */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #090d16 0%, #05080d 100%) !important;
        border-right: 1px solid rgba(255, 215, 0, 0.18) !important;
    }

    /* Hero Box */
    .hero-box {
        background: linear-gradient(180deg, rgba(16, 24, 38, 0.88) 0%, rgba(8, 12, 20, 0.95) 100%);
        border: 1px solid rgba(255, 215, 0, 0.25);
        border-radius: 16px;
        padding: 20px 28px 16px 28px;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 35px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        text-align: center;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(0, 255, 157, 0.1);
        border: 1px solid rgba(0, 255, 157, 0.35);
        color: #00ff9d;
        padding: 4px 14px;
        border-radius: 999px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #00ff9d;
        border-radius: 50%;
        box-shadow: 0 0 8px #00ff9d;
    }
    .main-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.35rem;
        font-weight: 900;
        letter-spacing: 2px;
        background: linear-gradient(90deg, #bf953f, #fcf6ba, #ffd700, #fbf5b7, #b38728);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .subtitle {
        color: #94a3b8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.80rem;
        margin-top: 6px;
        margin-bottom: 0;
        text-transform: uppercase;
        letter-spacing: 2.2px;
    }

    /* Contenedores de Tarjetas Glassmorphism */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(165deg, rgba(14, 21, 35, 0.90) 0%, rgba(8, 12, 20, 0.96) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 16px !important;
        padding: 10px !important;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(0, 255, 157, 0.38) !important;
        box-shadow: 0 14px 36px rgba(0, 255, 157, 0.08) !important;
    }

    /* Tarjeta de Cartelera en Cuadrícula (Vista A) */
    .grid-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 10px;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    }
    .grid-league-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 215, 0, 0.10);
        border: 1px solid rgba(255, 215, 0, 0.30);
        color: #ffd700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.67rem;
        font-weight: 800;
        letter-spacing: 1px;
        padding: 3px 9px;
        border-radius: 6px;
    }
    .grid-match-time {
        color: #94a3b8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.69rem;
        font-weight: 600;
    }
    .grid-team-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 7px 6px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.02);
        margin-bottom: 8px;
        border: 1px solid rgba(255, 255, 255, 0.04);
    }
    .grid-team-info {
        display: flex;
        align-items: center;
        min-width: 0;
    }
    .grid-team-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: #f8fafc;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .form-pills-wrap {
        display: flex;
        align-items: center;
        gap: 4px;
        flex-shrink: 0;
    }
    .form-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 19px;
        height: 19px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 800;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    }
    .grid-forecast-box {
        background: linear-gradient(90deg, rgba(0, 255, 157, 0.09) 0%, rgba(15, 23, 42, 0.85) 50%, rgba(255, 215, 0, 0.09) 100%);
        border: 1px solid rgba(0, 255, 157, 0.25);
        border-radius: 10px;
        padding: 10px 12px;
        margin-top: 10px;
        margin-bottom: 10px;
        text-align: center;
    }
    .grid-forecast-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.67rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #94a3b8;
        margin-bottom: 3px;
    }
    .grid-forecast-score {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.92rem;
        font-weight: 800;
        color: #00ff9d;
    }
    .grid-mini-meta {
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #cbd5e1;
        margin-top: 5px;
        padding-top: 5px;
        border-top: 1px dashed rgba(255, 255, 255, 0.08);
    }

    /* Botones Interactivos */
    div.stButton > button {
        width: 100%;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 800 !important;
        font-size: 0.80rem !important;
        letter-spacing: 1.2px !important;
        text-transform: uppercase !important;
        background: linear-gradient(90deg, rgba(0, 255, 157, 0.14), rgba(0, 195, 255, 0.14)) !important;
        color: #00ff9d !important;
        border: 1px solid rgba(0, 255, 157, 0.40) !important;
        border-radius: 10px !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #00ff9d, #00d4ff) !important;
        color: #04120b !important;
        border-color: #00ff9d !important;
        box-shadow: 0 0 18px rgba(0, 255, 157, 0.45) !important;
        transform: translateY(-1px);
    }

    /* Métricas Nativas */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.025);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 12px 14px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 255, 157, 0.35);
    }
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 800 !important;
        color: #00ff9d !important;
        font-size: 1.50rem !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
    }

    /* Radar Ejecutivo */
    .radar-card {
        background: linear-gradient(155deg, rgba(19, 28, 46, 0.95), rgba(10, 14, 23, 0.98));
        border: 1px solid rgba(255, 215, 0, 0.35);
        border-top: 3px solid #ffd700;
        border-radius: 14px;
        padding: 15px 15px;
        height: 100%;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .radar-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 28px rgba(255, 215, 0, 0.14);
        border-color: rgba(255, 215, 0, 0.7);
    }
    .radar-title {
        color: #ffd700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.73rem;
        font-weight: 800;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .radar-match {
        color: #f8fafc;
        font-size: 1.0rem;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .radar-pick {
        color: #00ff9d;
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.18rem;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .radar-odds {
        color: #94a3b8;
        font-size: 0.76rem;
        font-family: 'JetBrains Mono', monospace;
        background: rgba(0, 0, 0, 0.35);
        padding: 6px 10px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Scoreboard TV Header en Vista B (64px logos) */
    .scoreboard {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, rgba(0,255,157,0.08) 0%, rgba(15,23,42,0.90) 50%, rgba(255,215,0,0.08) 100%);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 16px;
        padding: 20px 28px;
        margin-bottom: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .sb-team {
        display: flex;
        align-items: center;
        gap: 14px;
        width: 38%;
    }
    .sb-team.right {
        justify-content: flex-end;
        text-align: right;
    }
    .sb-name {
        font-size: 1.45rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.5px;
        line-height: 1.15;
    }
    .sb-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #94a3b8;
        margin-top: 4px;
    }
    .sb-center {
        text-align: center;
        width: 24%;
    }
    .vs-circle {
        display: inline-block;
        font-family: 'Orbitron', sans-serif;
        font-size: 1.0rem;
        font-weight: 900;
        color: #06090e;
        background: linear-gradient(135deg, #ffd700, #f59e0b);
        padding: 6px 16px;
        border-radius: 999px;
        box-shadow: 0 0 18px rgba(255, 215, 0, 0.45);
        margin-bottom: 6px;
    }
    .sb-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.74rem;
        color: #cbd5e1;
    }

    /* Barra Tricolor 1X2 (Tug-of-War) */
    .prob-bar-wrapper {
        margin: 12px 0 18px 0;
    }
    .prob-bar-labels {
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .prob-bar-track {
        display: flex;
        height: 14px;
        width: 100%;
        border-radius: 999px;
        overflow: hidden;
        background: #0f172a;
        border: 1px solid rgba(255,255,255,0.12);
    }

    /* Banner del Pick Sugerido */
    .pick-banner {
        background: linear-gradient(90deg, rgba(255,215,0,0.16) 0%, rgba(0,255,157,0.10) 100%);
        border: 1px solid rgba(255,215,0,0.45);
        border-left: 5px solid #ffd700;
        border-radius: 10px;
        padding: 13px 18px;
        font-family: 'Inter', sans-serif;
        color: #fef08a;
        font-size: 1.02rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 16px;
    }

    /* Podio de Marcadores Exactos */
    .medal-card {
        border-radius: 12px;
        padding: 12px 10px;
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .medal-gold {
        background: linear-gradient(145deg, rgba(255, 215, 0, 0.14), rgba(15, 23, 42, 0.9));
        border-color: rgba(255, 215, 0, 0.5);
    }
    .medal-silver {
        background: linear-gradient(145deg, rgba(203, 213, 225, 0.12), rgba(15, 23, 42, 0.9));
        border-color: rgba(203, 213, 225, 0.4);
    }
    .medal-bronze {
        background: linear-gradient(145deg, rgba(217, 119, 6, 0.14), rgba(15, 23, 42, 0.9));
        border-color: rgba(217, 119, 6, 0.45);
    }
    .medal-score {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ffffff;
        margin: 4px 0;
    }
    .medal-prob {
        font-size: 0.78rem;
        color: #00ff9d;
        font-weight: 700;
    }

    /* Títulos de Sección Interna */
    .sec-header {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.84rem;
        font-weight: 800;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
        border-left: 3px solid #00ff9d;
        padding-left: 10px;
    }

    div.stFormSubmitButton > button {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        font-size: 0.95rem !important;
        letter-spacing: 1.8px !important;
        text-transform: uppercase !important;
        background: linear-gradient(90deg, #00c853, #00e676, #00bfa5) !important;
        color: #04120b !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.7rem 1.2rem !important;
        box-shadow: 0 0 20px rgba(0, 255, 157, 0.35) !important;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================
# 3. GESTIÓN DE DATOS EN SESIÓN (SIN @st.cache_data)
# ==============================================================
def cargar_dataframe_desde_disco():
    """
    Lee en vivo 'ligamx_stats_actualizado.csv' (o 'ligamx_stats_completo.csv'
    como alternativa local) sin congelar la caché. Si no existe en disco,
    inicializa el DataFrame base de los 18 clubes.
    """
    for ruta in (CSV_DEFAULT_PATH, CSV_LEGACY_PATH):
        if os.path.exists(ruta):
            df = pd.read_csv(ruta)
            faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
            if faltantes:
                raise ValueError(f"El archivo `{ruta}` no contiene las columnas requeridas: {faltantes}")
            return df, f"Archivo local: `{ruta}`"

    return pd.DataFrame(DATOS_BASE_LIGA_MX), "Base cuantitativa integrada (18 clubes)"


def obtener_lista_equipos(df):
    """Extrae la lista ordenada de clubes desde la columna o índice 'Equipo'."""
    if "Equipo" in df.columns:
        return [str(x).strip() for x in df["Equipo"].tolist()]
    return [str(x).strip() for x in df.index.tolist()]


def sincronizar_simulaciones_jornada(df_stats, calendario):
    """
    Ejecuta el motor cuantitativo (`calcular_probabilidades_partido`) para cada
    encuentro del calendario sincronizado con ESPN.
    """
    resultados = []
    for idx, evento in enumerate(calendario):
        home_team = evento["home"]
        away_team = evento["away"]
        sim = calcular_probabilidades_partido(home_team, away_team, df_stats)
        sim["id_partido"] = evento.get("id_partido", f"LMX-{idx + 1}")
        sim["nombre_evento"] = evento.get("nombre", f"{away_team} vs {home_team}")
        sim["horario"] = evento.get("hora", "JORNADA LIGA MX")
        sim["estado"] = evento.get("estado", "Programado")
        sim["idx_partido"] = idx
        resultados.append(sim)
    return resultados


# Inicialización estricta en st.session_state
if "partido_activo" not in st.session_state:
    st.session_state.partido_activo = None

if "df_ligamx" not in st.session_state:
    try:
        df_inicial, fuente_str = cargar_dataframe_desde_disco()
        st.session_state.df_ligamx = df_inicial
        st.session_state.fuente_datos_ligamx = fuente_str
    except Exception as exc:
        st.error(f"⚠️ Error al cargar estadísticas iniciales: {exc}")
        st.stop()

if "calendario_ligamx" not in st.session_state:
    equipos_actuales = obtener_lista_equipos(st.session_state.df_ligamx)
    st.session_state.calendario_ligamx = obtener_calendario_ligamx(equipos_df=equipos_actuales)

if "resultados_jornada" not in st.session_state:
    st.session_state.resultados_jornada = sincronizar_simulaciones_jornada(
        st.session_state.df_ligamx,
        st.session_state.calendario_ligamx,
    )


# ==============================================================
# 4. BARRA LATERAL: CARGA DE CSV EN CALIENTE Y SINCRONIZACIÓN ESPN
# ==============================================================
with st.sidebar:
    st.markdown(
        "<div style='font-family:Orbitron,sans-serif;font-size:1.15rem;font-weight:900;"
        "color:#ffd700;letter-spacing:1.5px;margin-bottom:4px;'>⚡ TERMINAL SHARP</div>"
        "<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#00ff9d;"
        "margin-bottom:16px;'>MÓDULO LIGA MX · CONTROL DE SESIÓN</div>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refrescar Calendario y Datos", key="btn_refrescar_sidebar", use_container_width=True):
        # Si no se subió un CSV manual, recargamos desde disco en vivo (ligamx_stats_actualizado.csv)
        if not st.session_state.get("csv_subido_manualmente", False):
            df_fresco, fuente_fresca = cargar_dataframe_desde_disco()
            st.session_state.df_ligamx = df_fresco
            st.session_state.fuente_datos_ligamx = fuente_fresca

        equipos_ref = obtener_lista_equipos(st.session_state.df_ligamx)
        st.session_state.calendario_ligamx = obtener_calendario_ligamx(equipos_df=equipos_ref)
        st.session_state.resultados_jornada = sincronizar_simulaciones_jornada(
            st.session_state.df_ligamx,
            st.session_state.calendario_ligamx,
        )
        st.session_state.partido_activo = None
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:0.76rem;font-weight:800;"
        "color:#cbd5e1;margin-bottom:6px;'>📂 ACTUALIZAR BASE DE DATOS (CSV)</div>",
        unsafe_allow_html=True,
    )

    archivo_csv = st.file_uploader(
        "Subir ligamx_stats_actualizado.csv",
        type=["csv"],
        key="uploader_csv_ligamx",
        help="Columnas requeridas: Equipo, xG_favor, xGA_contra, Forma, Jerarquia, Corners_Favor, Corners_Contra",
    )

    if archivo_csv is not None:
        raw_bytes = archivo_csv.getvalue()
        firma_hash = hashlib.md5(raw_bytes).hexdigest()

        if st.session_state.get("ultimo_hash_csv") != firma_hash:
            try:
                archivo_csv.seek(0)
                df_nuevo = pd.read_csv(archivo_csv)
                faltantes = COLUMNAS_REQUERIDAS - set(df_nuevo.columns)
                if faltantes:
                    st.error(f"⚠️ Faltan columnas en el CSV subido: {faltantes}")
                else:
                    st.session_state.df_ligamx = df_nuevo
                    st.session_state.ultimo_hash_csv = firma_hash
                    st.session_state.csv_subido_manualmente = True
                    st.session_state.fuente_datos_ligamx = f"Upload en sesión: `{archivo_csv.name}`"

                    equipos_nuevos = obtener_lista_equipos(df_nuevo)
                    st.session_state.calendario_ligamx = obtener_calendario_ligamx(equipos_df=equipos_nuevos)
                    st.session_state.resultados_jornada = sincronizar_simulaciones_jornada(
                        df_nuevo,
                        st.session_state.calendario_ligamx,
                    )
                    st.session_state.partido_activo = None
                    st.rerun()
            except Exception as exc:
                st.error(f"⚠️ No se pudo procesar el archivo CSV: {exc}")

    st.markdown("---")
    st.caption(f"📊 **Fuente activa:** {st.session_state.get('fuente_datos_ligamx', CSV_DEFAULT_PATH)}")
    st.caption(f"🏟️ **Clubes cargados:** {len(st.session_state.df_ligamx)}")
    st.caption(f"📅 **Partidos en cartelera:** {len(st.session_state.get('calendario_ligamx', []))}")

    with st.expander("📋 Ver Tabla de Métricas Activa"):
        st.dataframe(
            st.session_state.df_ligamx,
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================
# 5. COMPONENTES VISUALES AUXILIARES
# ==============================================================
def generar_pastillas_forma(valor_forma, seed_offset=0):
    """Genera 5 pastillas W/D/L en verde, gris y rojo a partir del índice de Forma."""
    try:
        f_val = float(valor_forma)
    except (TypeError, ValueError):
        f_val = 0.50

    if f_val > 10.0:
        f_val = f_val / 100.0
    elif f_val > 1.0:
        f_val = f_val / 10.0
    f_val = max(0.0, min(1.0, f_val))

    if f_val >= 0.82:
        secuencia = ["W", "W", "W", "D", "W"]
    elif f_val >= 0.68:
        secuencia = ["W", "D", "W", "W", "L"] if seed_offset % 2 == 0 else ["W", "W", "D", "L", "W"]
    elif f_val >= 0.54:
        secuencia = ["W", "D", "L", "W", "D"] if seed_offset % 2 == 0 else ["D", "W", "W", "L", "D"]
    elif f_val >= 0.42:
        secuencia = ["D", "L", "W", "D", "L"] if seed_offset % 2 == 0 else ["L", "W", "D", "L", "D"]
    elif f_val >= 0.28:
        secuencia = ["L", "D", "L", "W", "L"]
    else:
        secuencia = ["L", "L", "D", "L", "L"]

    colores = {
        "W": ("#10b981", "#03261b"),
        "D": ("#64748b", "#f8fafc"),
        "L": ("#ef4444", "#ffffff"),
    }

    return "".join(
        f'<span class="form-pill" style="background:{colores[res][0]};color:{colores[res][1]};">{res}</span>'
        for res in secuencia
    )


def crear_heatmap_plotly(matriz, local, visitante):
    """Construye el mapa de calor interactivo 0-0 a 6-6 en Plotly."""
    z_data = []
    text_data = []
    goles_rango = list(range(MATRIZ_MAX_GOLES + 1))

    for gl in goles_rango:
        row_z = []
        row_text = []
        for gv in goles_rango:
            prob = matriz.get((gl, gv), 0.0) * 100
            row_z.append(prob)
            row_text.append(f"<b>{prob:.1f}%</b><br>{gl}-{gv}")
        z_data.append(row_z)
        text_data.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[str(x) for x in goles_rango],
        y=[str(y) for y in goles_rango],
        text=text_data,
        texttemplate="%{text}",
        textfont=dict(family="JetBrains Mono", size=11, color="white"),
        hoverinfo="text",
        colorscale=[
            [0.0, "#090d16"],
            [0.15, "#112233"],
            [0.4, "#0f5257"],
            [0.7, "#00b4d8"],
            [1.0, "#00ff9d"],
        ],
        showscale=False,
        opacity=0.84,
        xgap=4,
        ygap=4,
    ))

    fig.update_layout(
        xaxis=dict(
            title=dict(text=f"{visitante.upper()} (GOLES) →", font=dict(family="JetBrains Mono", size=12, color="#ffd700")),
            side="top",
            tickfont=dict(family="JetBrains Mono", color="#ffd700"),
        ),
        yaxis=dict(
            title=dict(text=f"← {local.upper()} (GOLES)", font=dict(family="JetBrains Mono", size=12, color="#00ff9d")),
            autorange="reversed",
            tickfont=dict(family="JetBrains Mono", color="#00ff9d"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=55, b=20),
        height=420,
    )
    return fig


def render_radar_jornada(resultados_validos):
    """Renderiza el bloque superior con los 4 mejores picks matemáticos de la jornada."""
    if not resultados_validos:
        return

    st.markdown("<div class='sec-header'>🚨 RADAR EJECUTIVO DE LA JORNADA · TOP PICKS MATEMÁTICOS</div>", unsafe_allow_html=True)

    mejor_1x2 = None
    max_prob_1x2 = -1.0
    for r in resultados_validos:
        m = r["mercados"]
        if m["local"] > max_prob_1x2:
            max_prob_1x2 = m["local"]
            mejor_1x2 = (r, f"Gana {r['local']}", m["local"], f"DNB (Sin Empate): {m['dnb_local']*100:.1f}%")
        if m["visitante"] > max_prob_1x2:
            max_prob_1x2 = m["visitante"]
            mejor_1x2 = (r, f"Gana {r['visitante']}", m["visitante"], f"DNB (Sin Empate): {m['dnb_visit']*100:.1f}%")

    mejor_goles = None
    max_prob_goles = -1.0
    for r in resultados_validos:
        m = r["mercados"]
        if m["over25"] > max_prob_goles:
            max_prob_goles = m["over25"]
            mejor_goles = (r, "Over 2.5 Goles", m["over25"], f"xG Total Proy: {r['xg_l'] + r['xg_v']:.2f}")
        if m["under25"] > max_prob_goles:
            max_prob_goles = m["under25"]
            mejor_goles = (r, "Under 2.5 Goles", m["under25"], f"xG Total Proy: {r['xg_l'] + r['xg_v']:.2f}")

    mejor_btts_r = max(resultados_validos, key=lambda x: x["mercados"]["btts"])
    prob_btts_top = mejor_btts_r["mercados"]["btts"]

    mejor_corner = None
    max_prob_c = -1.0
    for r in resultados_validos:
        linea_c = r.get("linea_corners", LINEA_CORNERS_DEFAULT)
        if r["prob_over_c"] > max_prob_c:
            max_prob_c = r["prob_over_c"]
            mejor_corner = (r, f"Over {linea_c} Córners", r["prob_over_c"], f"Media Proy: {r['total_corners']} 🚩")
        if r["prob_under_c"] > max_prob_c:
            max_prob_c = r["prob_under_c"]
            mejor_corner = (r, f"Under {linea_c} Córners", r["prob_under_c"], f"Media Proy: {r['total_corners']} 🚩")

    c1, c2, c3, c4 = st.columns(4)
    tarjetas_radar = [
        (c1, "🔒 EL LOCK (1X2)", mejor_1x2[0], mejor_1x2[1], mejor_1x2[2], mejor_1x2[3]),
        (c2, "⚽ FIJA DE GOLES (2.5)", mejor_goles[0], mejor_goles[1], mejor_goles[2], mejor_goles[3]),
        (c3, "🤝 AMBOS ANOTAN (BTTS)", mejor_btts_r, "Ambos Anotan: SÍ", prob_btts_top, f"xG: {mejor_btts_r['xg_l']:.2f} vs {mejor_btts_r['xg_v']:.2f}"),
        (c4, "🚩 REY DEL CÓRNER", mejor_corner[0], mejor_corner[1], mejor_corner[2], mejor_corner[3]),
    ]

    for col, titulo, r_match, pick_str, prob_val, extra_info in tarjetas_radar:
        with col:
            momio_str = formatear_momio_justo(prob_val)
            st.markdown(
                f"""
                <div class="radar-card">
                    <div class="radar-title">{titulo}</div>
                    <div class="radar-match">{EMOJIS_LIGA_MX.get(r_match['local'], '⚽')} {r_match['local']} vs {r_match['visitante']} {EMOJIS_LIGA_MX.get(r_match['visitante'], '⚽')}</div>
                    <div class="radar-pick">{pick_str} · {prob_val*100:.1f}%</div>
                    <div class="radar-odds">💡 Fair Odd: <b style="color:#fff;">{momio_str}</b><br>{extra_info}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")


def render_vista_cartelera_grid(resultados):
    """
    VISTA A: Cartelera en Cuadrícula de 3 Columnas (st.columns(3))
    con escudos ESPN de 32px, pastillas W/D/L y botón 'LEER ANÁLISIS →'.
    """
    st.markdown(
        "<div class='sec-header'>🏟️ CARTELERA SINCRONIZADA DE JORNADA (ESPN API) · SELECCIONA UN ENCUENTRO</div>",
        unsafe_allow_html=True,
    )

    for fila_idx in range(0, len(resultados), 3):
        cols = st.columns(3)
        bloque = resultados[fila_idx:fila_idx + 3]

        for col_idx, r in enumerate(bloque):
            idx_global = fila_idx + col_idx
            with cols[col_idx]:
                with st.container(border=True):
                    if r.get("error"):
                        st.error(f"⚠️ Partido #{idx_global + 1}: {r.get('mensaje_error', 'Error de configuración')}")
                        continue

                    local = r["local"]
                    visitante = r["visitante"]
                    mercados = r["mercados"]

                    logo_local_32 = escudo_ligamx_html(local, size=32)
                    logo_visit_32 = escudo_ligamx_html(visitante, size=32)

                    pills_local = generar_pastillas_forma(r["forma_l"], seed_offset=idx_global)
                    pills_visit = generar_pastillas_forma(r["forma_v"], seed_offset=idx_global + 1)

                    gl_proy = r["proy_gl"]
                    gv_proy = r["proy_gv"]

                    opciones_1x2 = {
                        f"1 ({local})": mercados["local"],
                        "X (Empate)": mercados["empate"],
                        f"2 ({visitante})": mercados["visitante"],
                    }
                    pick_corto = max(opciones_1x2, key=opciones_1x2.get)
                    prob_pick = opciones_1x2[pick_corto] * 100

                    estado_badge = r.get("estado", "Programado")
                    st.markdown(
                        f"""
                        <div class="grid-card-header">
                            <span class="grid-league-badge">⚽ LIGA MX · {estado_badge.upper()}</span>
                            <span class="grid-match-time">🕒 {r.get('horario', 'JORNADA')}</span>
                        </div>
                        <div class="grid-team-row">
                            <div class="grid-team-info">
                                {logo_local_32}
                                <span class="grid-team-name" title="{local}">{local}</span>
                            </div>
                            <div class="form-pills-wrap">{pills_local}</div>
                        </div>
                        <div class="grid-team-row">
                            <div class="grid-team-info">
                                {logo_visit_32}
                                <span class="grid-team-name" title="{visitante}">{visitante}</span>
                            </div>
                            <div class="form-pills-wrap">{pills_visit}</div>
                        </div>
                        <div class="grid-forecast-box">
                            <div class="grid-forecast-label">🎯 Nuestro pronóstico</div>
                            <div class="grid-forecast-score">{local} {gl_proy} - {gv_proy} {visitante}</div>
                            <div class="grid-mini-meta">
                                <span>xG: <b style="color:#00ff9d;">{r['xg_l']:.2f}</b> vs <b style="color:#ffd700;">{r['xg_v']:.2f}</b></span>
                                <span>Pick: <b style="color:#fff;">{pick_corto} ({prob_pick:.0f}%)</b></span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        "LEER ANÁLISIS →",
                        key=f"btn_ver_partido_{idx_global}_{r.get('id_partido', idx_global)}",
                        use_container_width=True,
                    ):
                        st.session_state.partido_activo = idx_global
                        st.rerun()


def render_vista_detalle_partido(r, idx_partido):
    """
    VISTA B: Pantalla Detallada de Partido Seleccionado
    con Scoreboard TV Header (escudos a 64px), Barra 1X2, Mercados Asiáticos,
    Podio de Marcadores Exactos, Córners proyectados y Matriz Plotly.
    """
    col_back, col_info = st.columns([3.5, 6.5])
    with col_back:
        if st.button("← Volver a la Cartelera de Jornada", key="btn_volver_cartelera", use_container_width=True):
            st.session_state.partido_activo = None
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:right; font-family:JetBrains Mono,monospace; font-size:0.80rem; "
            f"color:#94a3b8; padding-top:10px;'>"
            f"📍 EXPEDIENTE CUANTITATIVO · ID #{r.get('id_partido', idx_partido + 1)} · "
            f"{r.get('horario', 'LIGA MX')} ({r.get('estado', 'Programado')})</div>",
            unsafe_allow_html=True,
        )

    st.write("")

    local = r["local"]
    visitante = r["visitante"]
    mercados = r["mercados"]
    fair_odds = r["fair_odds"]
    xg_l = r["xg_l"]
    xg_v = r["xg_v"]

    p_loc = mercados["local"] * 100
    p_emp = mercados["empate"] * 100
    p_vis = mercados["visitante"] * 100

    opciones_1x2 = {
        f"Gana {local}": mercados["local"],
        "Empate": mercados["empate"],
        f"Gana {visitante}": mercados["visitante"],
    }
    pick_top = max(opciones_1x2, key=opciones_1x2.get)
    prob_top = opciones_1x2[pick_top]
    momio_top = formatear_momio_justo(prob_top)

    with st.container(border=True):
        # 1. SCOREBOARD TV HEADER CON LOGOS OFICIALES EN GRANDE (64px)
        st.markdown(
            f"""
            <div class="scoreboard">
                <div class="sb-team">
                    {escudo_ligamx_html(local, size=64)}
                    <div>
                        <div class="sb-name">{EMOJIS_LIGA_MX.get(local, '⚽')} {local}</div>
                        <div class="sb-tag">LOCAL · xG Proy: <b style="color:#00ff9d;">{xg_l:.2f}</b> · Factor Loc: x{r['factor_loc']}</div>
                        <div style="margin-top:6px;">{generar_pastillas_forma(r['forma_l'], seed_offset=idx_partido)}</div>
                    </div>
                </div>
                <div class="sb-center">
                    <div class="vs-circle">VS</div>
                    <div class="sb-meta">{r.get('horario', 'JORNADA LIGA MX')} · DIXON-COLES</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#00ff9d;margin-top:4px;font-weight:800;">
                        Proyección Exacta: {r['proy_gl']} - {r['proy_gv']}
                    </div>
                </div>
                <div class="sb-team right">
                    <div>
                        <div class="sb-name">{visitante} {EMOJIS_LIGA_MX.get(visitante, '⚽')}</div>
                        <div class="sb-tag">VISITA · xG Proy: <b style="color:#ffd700;">{xg_v:.2f}</b> · xG Total: {xg_l + xg_v:.2f}</div>
                        <div style="margin-top:6px;display:flex;justify-content:flex-end;">{generar_pastillas_forma(r['forma_v'], seed_offset=idx_partido + 1)}</div>
                    </div>
                    {escudo_ligamx_html(visitante, size=64)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. BARRA TRICOLOR 1X2 (TUG-OF-WAR)
        st.markdown(
            f"""
            <div class="prob-bar-wrapper">
                <div class="prob-bar-labels">
                    <span style="color:#00ff9d;">🏠 {local}: {p_loc:.1f}%</span>
                    <span style="color:#94a3b8;">🤝 Empate: {p_emp:.1f}%</span>
                    <span style="color:#ffd700;">✈️ {visitante}: {p_vis:.1f}%</span>
                </div>
                <div class="prob-bar-track">
                    <div style="width:{p_loc:.2f}%; background: linear-gradient(90deg, #00b09b, #00ff9d);"></div>
                    <div style="width:{p_emp:.2f}%; background: #475569;"></div>
                    <div style="width:{p_vis:.2f}%; background: linear-gradient(90deg, #f59e0b, #ffd700);"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3. BANNER DEL PICK SUGERIDO + CUOTA JUSTA
        st.markdown(
            f"""
            <div class="pick-banner">
                <span>🏆 <b>PICK PRINCIPAL (1X2):</b> {pick_top} ({prob_top*100:.1f}% de probabilidad)</span>
                <span style="font-family:'JetBrains Mono', monospace; background:rgba(0,0,0,0.45); padding:5px 12px; border-radius:6px; color:#00ff9d;">
                    💡 Cuota Justa Mínima (Fair Odd): <b>{momio_top}</b>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4. MERCADO 1X2 CON FAIR ODDS
        st.markdown("<div class='sec-header'>🎲 Mercado Principal 1X2 y Momios Justos (Fair Odds)</div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        etiquetas_1x2 = [
            (col1, f"👑 {local} (1)" if pick_top == f"Gana {local}" else f"Gana {local} (1)", mercados["local"], fair_odds["local"]),
            (col2, "👑 Empate (X)" if pick_top == "Empate" else "Empate (X)", mercados["empate"], fair_odds["empate"]),
            (col3, f"👑 {visitante} (2)" if pick_top == f"Gana {visitante}" else f"Gana {visitante} (2)", mercados["visitante"], fair_odds["visitante"]),
        ]
        for col, label, prob, f_odd in etiquetas_1x2:
            with col:
                st.metric(label, f"{prob*100:.1f}%", delta=f"Fair Odd: {f_odd}", delta_color="off")

        st.write("")

        # 5. MERCADOS ASIÁTICOS, DOBLE OPORTUNIDAD Y DNB
        st.markdown("<div class='sec-header'>🛡️ Mercados Asiáticos, Doble Oportunidad y Draw No Bet (DNB)</div>", unsafe_allow_html=True)
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.metric(
                f"🛡️ {local} DNB (Sin Empate)",
                f"{mercados['dnb_local']*100:.1f}%",
                delta=f"Fair: {fair_odds['dnb_local']}",
                delta_color="off",
            )
        with a2:
            st.metric(
                f"🛡️ {visitante} DNB (Sin Empate)",
                f"{mercados['dnb_visit']*100:.1f}%",
                delta=f"Fair: {fair_odds['dnb_visit']}",
                delta_color="off",
            )
        with a3:
            if mercados["doble_1x"] >= mercados["doble_x2"]:
                lbl_dc, prob_dc, odd_dc = f"🔒 Doble Op: {local}/Emp (1X)", mercados["doble_1x"], fair_odds["doble_1x"]
            else:
                lbl_dc, prob_dc, odd_dc = f"🔒 Doble Op: {visitante}/Emp (X2)", mercados["doble_x2"], fair_odds["doble_x2"]
            st.metric(lbl_dc, f"{prob_dc*100:.1f}%", delta=f"Fair: {odd_dc}", delta_color="off")
        with a4:
            if mercados["hc_local_15"] >= mercados["hc_visit_15"]:
                lbl_hc, prob_hc, odd_hc = f"⚡ Hándicap {local} (-1.5)", mercados["hc_local_15"], fair_odds["hc_local_15"]
            else:
                lbl_hc, prob_hc, odd_hc = f"⚡ Hándicap {visitante} (-1.5)", mercados["hc_visit_15"], fair_odds["hc_visit_15"]
            st.metric(lbl_hc, f"{prob_hc*100:.1f}%", delta=f"Fair: {odd_hc}", delta_color="off")

        st.write("")

        # 6. BLOQUE INFERIOR: PODIO DE MARCADORES, CÓRNERS Y GOLES
        col_izq, col_der = st.columns([5, 6])

        with col_izq:
            st.markdown("<div class='sec-header'>🎯 Podio de Marcadores Exactos (Oro / Plata / Bronce)</div>", unsafe_allow_html=True)
            cols_top = st.columns(3)
            clases_medalla = ["medal-gold", "medal-silver", "medal-bronze"]
            titulos_medalla = ["🥇 ORO (1º)", "🥈 PLATA (2º)", "🥉 BRONCE (3º)"]

            for idx_m, ((gl, gv), prob) in enumerate(r["top3"]):
                with cols_top[idx_m]:
                    st.markdown(
                        f"""
                        <div class="medal-card {clases_medalla[idx_m]}">
                            <div style="font-size:0.70rem; color:#cbd5e1; font-weight:700;">{titulos_medalla[idx_m]}</div>
                            <div class="medal-score">{gl} - {gv}</div>
                            <div class="medal-prob">{prob*100:.1f}% prob.</div>
                            <div style="font-size:0.68rem; color:#94a3b8; margin-top:2px;">{formatear_momio_justo(prob)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.write("")
            st.markdown("<div class='sec-header'>🚩 Línea de Córners Proyectada (Poisson + Dominio)</div>", unsafe_allow_html=True)
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.metric(f"🚩 {local}", f"{r['xc_l']}")
            with cc2:
                st.metric("🔥 TOTAL PROY.", f"{r['total_corners']}")
            with cc3:
                st.metric(f"🚩 {visitante}", f"{r['xc_v']}")

            linea_c = r.get("linea_corners", LINEA_CORNERS_DEFAULT)
            if r["prob_over_c"] >= r["prob_under_c"]:
                prob_c = r["prob_over_c"]
                pick_corners = f"🔥 OVER {linea_c} CÓRNERS ({prob_c*100:.1f}%) · Fair: {fair_odds['over_corners']}"
                color_pick = "#00ff9d"
            else:
                prob_c = r["prob_under_c"]
                pick_corners = f"🧊 UNDER {linea_c} CÓRNERS ({prob_c*100:.1f}%) · Fair: {fair_odds['under_corners']}"
                color_pick = "#00c3ff"

            st.markdown(
                f"""
                <div style="text-align:center; padding:10px; margin-top:6px;
                    background: rgba(0,0,0,0.35); border:1px solid {color_pick}; color:{color_pick};
                    border-radius:10px; font-family:'JetBrains Mono', monospace; font-weight:800; font-size:0.82rem;">
                    🎯 {pick_corners}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_der:
            st.markdown("<div class='sec-header'>📈 Over/Under de Goles, BTTS y Porterías Imbatidas</div>", unsafe_allow_html=True)
            goles_totales = xg_l + xg_v
            g1, g2, g3 = st.columns(3)
            with g1:
                st.metric("⚽ Goles Esp. (xG)", f"{goles_totales:.2f}", delta=f"Under 2.5: {mercados['under25']*100:.1f}%", delta_color="off")
            with g2:
                st.metric("🤝 Ambos Anotan (Sí)", f"{mercados['btts']*100:.1f}%", delta=f"Fair: {fair_odds['btts']}", delta_color="off")
            with g3:
                st.metric("🔥 Over 2.5 Goles", f"{mercados['over25']*100:.1f}%", delta=f"Fair: {fair_odds['over25']}", delta_color="off")

            st.write("")
            g4, g5, g6 = st.columns(3)
            with g4:
                st.metric("🧊 Under 3.5 Goles", f"{mercados['under35']*100:.1f}%", delta=f"Fair: {fair_odds['under35']}", delta_color="off")
            with g5:
                st.metric(f"🛡️ Cero {local}", f"{mercados['clean_sheet_local']*100:.1f}%", delta=f"Fair: {fair_odds['clean_sheet_local']}", delta_color="off")
            with g6:
                st.metric(f"🛡️ Cero {visitante}", f"{mercados['clean_sheet_visitante']*100:.1f}%", delta=f"Fair: {fair_odds['clean_sheet_visitante']}", delta_color="off")

        st.write("")
        # 7. MATRIZ DE CALOR PLOTLY Y RADIOGRAFÍA DE PLANTILLAS
        st.markdown("<div class='sec-header'>📊 Matriz Interactiva de Probabilidad Exacta (0-0 a 6-6) y Comparativa</div>", unsafe_allow_html=True)
        m_col1, m_col2 = st.columns([6, 4])
        with m_col1:
            fig = crear_heatmap_plotly(r["matriz"], local, visitante)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"plotly_detail_{idx_partido}")
        with m_col2:
            st.markdown("<div class='sec-header'>📋 Radiografía de Plantillas</div>", unsafe_allow_html=True)
            st.metric(f"Forma Reciente ({local} vs {visitante})", f"{r['forma_l']*100:.0f}% vs {r['forma_v']*100:.0f}%")
            st.metric(f"Jerarquía de Plantel ({local} vs {visitante})", f"{r['jerarquia_l']:.1f}/10 vs {r['jerarquia_v']:.1f}/10")
            st.metric(f"xG a Favor Base ({local} vs {visitante})", f"{r['xgf_l']:.2f} vs {r['xgf_v']:.2f}")
            st.metric(f"xGA Defensivo ({local} vs {visitante})", f"{r['xga_l']:.2f} vs {r['xga_v']:.2f}")


# ==============================================================
# 6. RENDERIZADO PRINCIPAL Y ENRUTADOR DE VISTAS
# ==============================================================
st.markdown("""
<div class="hero-box">
    <div class="status-pill"><span class="pulse-dot"></span> ENGINE ONLINE · ARQUITECTURA MODULAR V6.0 · ESPN LIVE SYNC</div>
    <h1 class="main-title">TERMINAL SHARP · LIGA MX</h1>
    <p class="subtitle">Sincronización ESPN Scoreboard · Motor Bivariado Dixon-Coles · Momios Justos (+EV)</p>
</div>
""", unsafe_allow_html=True)

resultados_actuales = st.session_state.get("resultados_jornada", [])
equipos_disponibles = obtener_lista_equipos(st.session_state.df_ligamx)

if st.session_state.partido_activo is None:
    # Editor rápido opcional por si el usuario desea personalizar algún cruce manualmente
    with st.expander("⚙️ AJUSTAR O PERSONALIZAR CRUCES DE LA CARTELERA MANUALMENTE (OPCIONAL)", expanded=False):
        with st.form("form_personalizar_jornada"):
            nuevos_eventos_manuales = []
            num_filas = len(resultados_actuales) if resultados_actuales else 9
            for i in range(num_filas):
                r_prev = resultados_actuales[i] if i < len(resultados_actuales) else None
                loc_prev = normalizar_equipo_para_df(r_prev["local"], equipos_disponibles) if r_prev else equipos_disponibles[min(i * 2, len(equipos_disponibles) - 1)]
                vis_prev = normalizar_equipo_para_df(r_prev["visitante"], equipos_disponibles) if r_prev else equipos_disponibles[min(i * 2 + 1, len(equipos_disponibles) - 1)]
                hora_prev = r_prev.get("horario", "JORNADA LIGA MX") if r_prev else "JORNADA LIGA MX"
                estado_prev = r_prev.get("estado", "Programado") if r_prev else "Programado"

                idx_l = equipos_disponibles.index(loc_prev) if loc_prev in equipos_disponibles else 0
                idx_v = equipos_disponibles.index(vis_prev) if vis_prev in equipos_disponibles else min(1, len(equipos_disponibles) - 1)

                c1, c2, c3 = st.columns([4.2, 1.6, 4.2])
                with c1:
                    sel_local = st.selectbox(
                        f"Local {i + 1}",
                        equipos_disponibles,
                        index=idx_l,
                        key=f"man_loc_{i}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"🏠 {EMOJIS_LIGA_MX.get(x, '⚽')} {x}",
                    )
                with c2:
                    st.markdown(
                        f"<div style='text-align:center;font-family:Orbitron,sans-serif;font-size:0.76rem;"
                        f"font-weight:900;color:#ffd700;padding-top:8px;'>JUEGO {i + 1}</div>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    sel_visita = st.selectbox(
                        f"Visita {i + 1}",
                        equipos_disponibles,
                        index=idx_v,
                        key=f"man_vis_{i}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"✈️ {EMOJIS_LIGA_MX.get(x, '⚽')} {x}",
                    )

                nuevos_eventos_manuales.append({
                    "id_partido": f"MAN-{i + 1}",
                    "nombre": f"{sel_visita} vs {sel_local}",
                    "away": sel_visita,
                    "home": sel_local,
                    "hora": hora_prev,
                    "estado": estado_prev,
                })

            aplicar_manual = st.form_submit_button("⚡ RECALCULAR CARTELERA PERSONALIZADA ⚡", use_container_width=True)
            if aplicar_manual:
                st.session_state.calendario_ligamx = nuevos_eventos_manuales
                st.session_state.resultados_jornada = sincronizar_simulaciones_jornada(
                    st.session_state.df_ligamx,
                    nuevos_eventos_manuales,
                )
                st.session_state.partido_activo = None
                st.rerun()

    validos = [r for r in resultados_actuales if not r.get("error")]
    render_radar_jornada(validos)
    render_vista_cartelera_grid(resultados_actuales)

else:
    idx_sel = st.session_state.partido_activo
    if isinstance(idx_sel, int) and 0 <= idx_sel < len(resultados_actuales):
        partido_sel = resultados_actuales[idx_sel]
        if partido_sel.get("error"):
            st.warning("⚠️ El partido seleccionado contiene un error de configuración. Regresando a la cartelera...")
            st.session_state.partido_activo = None
            st.rerun()
        else:
            render_vista_detalle_partido(partido_sel, idx_sel)
    else:
        st.session_state.partido_activo = None
        st.rerun()