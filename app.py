#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 TERMINAL SHARP: LIGA MX (CYBER-QUANT UI EDITION)
 Dashboard web de predicción cuantitativa:
 - Modelo Poisson + Corrección Dixon-Coles
 - Amortiguación de xG + Localía Dinámica por Altitud/Estadio
 - Modelo de Córners por Dominio (Game State) + Poisson PMF
 - Calculadora de Momios Justos (Fair Odds: Decimal y Americano)
 - Mercados Asiáticos (Draw No Bet, Doble Oportunidad, Hándicap -1.5)
 - UI PREMIUM: Glassmorphism, Scoreboard TV, Barra 1X2 y Podio
==============================================================
"""

import math
import unicodedata
from urllib.parse import quote
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ==============================================================
# PARÁMETROS GLOBALES DEL MODELO
# ==============================================================
CSV_PATH = "ligamx_stats_completo.csv"
HOME_ADVANTAGE_DEFAULT = 1.18  # Localía base si el equipo no está en el diccionario
DIXON_COLES_RHO = -0.13        # Correlación negativa para inflar empates bajos (0-0, 1-1)
LINEA_CORNERS = 9.5            # Línea asiática estándar para Over/Under de córners
MAX_GOLES_CALCULO = 10         # Rango de la matriz para mercados (precisión 100%)
MAX_GOLES_DISPLAY = 5          # Rango a mostrar en "marcadores exactos" (0-0 a 5-5)
MATRIZ_MAX_GOLES = 6           # Rango exacto de la matriz visual (0 a 6 goles)
ESCUDO_ANCHO_PX = 68           # Tamaño optimizado para el Scoreboard Header
NUM_PARTIDOS = 9               # Total de partidos por jornada

FACTOR_LOCALIA_EQUIPOS = {
    "Toluca": 1.26, "Pumas": 1.24, "Pachuca": 1.24, "América": 1.23,
    "Cruz Azul": 1.22, "Tigres": 1.23, "Monterrey": 1.22, "Guadalajara": 1.19,
    "León": 1.20, "Santos": 1.18, "Atlas": 1.16, "San Luis": 1.17,
    "Necaxa": 1.16, "Tijuana": 1.21, "Puebla": 1.16, "Querétaro": 1.14,
    "Juárez": 1.13, "Mazatlán": 1.12, "Atlante": 1.18,
}

# ==============================================================
# 0. DICCIONARIO DE ESCUDOS Y EMOJIS
# ==============================================================
WIKI_COMMONS_BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/"

ESCUDOS_EQUIPOS = {
    "América": "Club América flag.svg",
    "Cruz Azul": "Club de Futbol Cruz Azul.svg",
    "Guadalajara": "Logo del Club Deportivo Guadalajara (México).svg",
    "Tigres": "Escudo del Club de Fútbol Tigres UANL.svg",
    "Monterrey": "Club de Fútbol Monterrey 2019 Logo.svg",
    "Toluca": "Club Toluca Logo.svg",
    "Pumas": "Logo Pumas de la UNAM.jpg",
    "León": "Leon.svg",
    "Pachuca": "Escudo del Club de Fútbol Pachuca.png",
    "Santos": "Escudo del Club Santos Laguna.png",
    "Atlas": "Fútbol Club Atlas.svg",
    "Necaxa": "Club Necaxa Logo.svg",
    "Querétaro": "Gallosblancos.jpg",
    "Juárez": "FC Juárez logo.svg",
    "San Luis": "Atlético San Luis Logo Proper.svg",
    "Atlante": "Atlante FC.png",
    "Tijuana": "Club-Tijuana.jpg",
    "Puebla": "Club Puebla logo.svg",
}

FALLBACK_BADGE = {
    "América": ("AME", "#FFCC00", "#0b1f4d"),
    "León": ("LEON", "#0a8a3f", "#ffffff"),
    "San Luis": ("ASL", "#c8102e", "#ffffff"),
    "Atlante": ("ATL", "#0033a0", "#ffcc00"),
    "Tijuana": ("TIJ", "#000000", "#e2231a"),
    "Puebla": ("PUE", "#1c3f94", "#ffffff"),
    "Mazatlán": ("MAZ", "#582c83", "#ffffff"),
}

EMOJIS_LIGA = {
    "América": "🦅", "Guadalajara": "🐐", "Cruz Azul": "🚂", "Pumas": "🐾",
    "Tigres": "🐯", "Monterrey": "⛰️", "Toluca": "👿", "Pachuca": "🐹",
    "León": "🦁", "Santos": "😇", "Atlas": "🦊", "Necaxa": "⚡",
    "Tijuana": "🐕", "Puebla": "🎽", "Juárez": "🐎", "Mazatlán": "⚓",
    "Querétaro": "🐓", "San Luis": "⛪", "Atlante": "🦈"
}


def _normalizar(texto):
    texto = str(texto).strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


_ESCUDOS_NORMALIZADOS = {_normalizar(k): v for k, v in ESCUDOS_EQUIPOS.items()}
_FALLBACK_NORMALIZADO = {_normalizar(k): v for k, v in FALLBACK_BADGE.items()}
_LOCALIA_NORMALIZADA = {_normalizar(k): v for k, v in FACTOR_LOCALIA_EQUIPOS.items()}


def escudo_url(equipo):
    archivo = _ESCUDOS_NORMALIZADOS.get(_normalizar(equipo))
    if not archivo:
        return None
    return f"{WIKI_COMMONS_BASE}{quote(archivo)}?width={ESCUDO_ANCHO_PX * 2}"


def escudo_html(equipo, size=ESCUDO_ANCHO_PX):
    """Genera el HTML limpio del escudo con sombra de neón o su insignia fallback."""
    url = escudo_url(equipo)
    if url:
        return (
            f'<img src="{url}" style="width:{size}px; height:{size}px; '
            f'object-fit:contain; filter: drop-shadow(0 4px 10px rgba(0,0,0,0.65));" '
            f'alt="{equipo}">'
        )
    iniciales, color_fondo, color_texto = _FALLBACK_NORMALIZADO.get(
        _normalizar(equipo), (equipo[:3].upper(), "#1e293b", "#ffffff")
    )
    return (
        f'<div style="width:{size}px; height:{size}px; border-radius:50%; '
        f'background:{color_fondo}; color:{color_texto}; display:inline-flex; '
        f'align-items:center; justify-content:center; font-family:\'JetBrains Mono\', monospace; '
        f'font-weight:800; font-size:1.05rem; border:2px solid rgba(255,255,255,0.25); '
        f'box-shadow: 0 4px 12px rgba(0,0,0,0.5);">{iniciales}</div>'
    )


# ==============================================================
# 1. ESTÉTICA "CYBER-QUANT SPORTSBOOK TERMINAL"
# ==============================================================
st.set_page_config(
    page_title="Terminal Sharp · Liga MX",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700;800&family=Orbitron:wght@700;900&display=swap');

    [data-testid="stToolbar"] {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1380px !important;
    }

    /* Fondo oscuro multicapa con resplandor esmeralda y dorado sutil */
    .stApp {
        background-color: #06090e;
        background-image: 
            radial-gradient(at 15% 5%, rgba(0, 255, 157, 0.06) 0px, transparent 45%),
            radial-gradient(at 85% 10%, rgba(255, 215, 0, 0.05) 0px, transparent 45%),
            radial-gradient(at 50% 90%, rgba(0, 195, 255, 0.04) 0px, transparent 50%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* Banner Superior de la Terminal */
    .hero-box {
        background: linear-gradient(180deg, rgba(16, 24, 38, 0.85) 0%, rgba(8, 12, 20, 0.92) 100%);
        border: 1px solid rgba(255, 215, 0, 0.25);
        border-radius: 16px;
        padding: 22px 28px 18px 28px;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 35px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        text-align: center;
        position: relative;
        overflow: hidden;
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
        margin-bottom: 10px;
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
        font-size: 2.5rem;
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
        font-size: 0.82rem;
        margin-top: 6px;
        margin-bottom: 0;
        text-transform: uppercase;
        letter-spacing: 2.5px;
    }

    /* Estilizado de Contenedores de Partido (Glassmorphism) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(165deg, rgba(15, 22, 34, 0.88) 0%, rgba(9, 13, 21, 0.94) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 8px !important;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55) !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(0, 255, 157, 0.30) !important;
        box-shadow: 0 14px 38px rgba(0, 255, 157, 0.06) !important;
    }

    /* Métricas Nativas de Streamlit */
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
        font-size: 1.55rem !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.76rem !important;
    }

    /* Tarjetas del Radar Ejecutivo */
    .radar-card {
        background: linear-gradient(155deg, rgba(19, 28, 46, 0.95), rgba(10, 14, 23, 0.98));
        border: 1px solid rgba(255, 215, 0, 0.35);
        border-top: 3px solid #ffd700;
        border-radius: 14px;
        padding: 16px 16px;
        height: 100%;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .radar-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(255, 215, 0, 0.14);
        border-color: rgba(255, 215, 0, 0.7);
    }
    .radar-title {
        color: #ffd700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .radar-match {
        color: #f8fafc;
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .radar-pick {
        color: #00ff9d;
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.25rem;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .radar-odds {
        color: #94a3b8;
        font-size: 0.78rem;
        font-family: 'JetBrains Mono', monospace;
        background: rgba(0, 0, 0, 0.35);
        padding: 6px 10px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Scoreboard Header por Partido */
    .scoreboard {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, rgba(0,255,157,0.06) 0%, rgba(15,23,42,0.85) 50%, rgba(255,215,0,0.06) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px 24px;
        margin-bottom: 14px;
    }
    .sb-team {
        display: flex;
        align-items: center;
        gap: 16px;
        width: 38%;
    }
    .sb-team.right {
        justify-content: flex-end;
        text-align: right;
    }
    .sb-name {
        font-size: 1.35rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.5px;
        line-height: 1.15;
    }
    .sb-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 3px;
    }
    .sb-center {
        text-align: center;
        width: 24%;
    }
    .vs-circle {
        display: inline-block;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.95rem;
        font-weight: 900;
        color: #06090e;
        background: linear-gradient(135deg, #ffd700, #f59e0b);
        padding: 5px 14px;
        border-radius: 999px;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.4);
        margin-bottom: 6px;
    }
    .sb-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #cbd5e1;
    }

    /* Barra Tricolor 1X2 (Tug-of-War) */
    .prob-bar-wrapper {
        margin: 10px 0 16px 0;
    }
    .prob-bar-labels {
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .prob-bar-track {
        display: flex;
        height: 12px;
        width: 100%;
        border-radius: 999px;
        overflow: hidden;
        background: #0f172a;
        border: 1px solid rgba(255,255,255,0.1);
    }

    /* Banner del Pick Sugerido */
    .pick-banner {
        background: linear-gradient(90deg, rgba(255,215,0,0.16) 0%, rgba(0,255,157,0.10) 100%);
        border: 1px solid rgba(255,215,0,0.45);
        border-left: 5px solid #ffd700;
        border-radius: 10px;
        padding: 12px 18px;
        font-family: 'Inter', sans-serif;
        color: #fef08a;
        font-size: 1.02rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }

    /* Tarjetas de Podio para Marcador Exacto */
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
        font-size: 0.82rem;
        font-weight: 800;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 10px;
        border-left: 3px solid #00ff9d;
        padding-left: 8px;
    }

    /* Botón de Submit Principal */
    div.stFormSubmitButton > button {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        font-size: 1.05rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        background: linear-gradient(90deg, #00c853, #00e676, #00bfa5) !important;
        color: #04120b !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.2rem !important;
        box-shadow: 0 0 22px rgba(0, 255, 157, 0.35) !important;
        transition: all 0.25s ease !important;
    }
    div.stFormSubmitButton > button:hover {
        box-shadow: 0 0 32px rgba(0, 255, 157, 0.65) !important;
        transform: scale(1.01);
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================
# 2. CARGA DE DATOS
# ==============================================================
@st.cache_data
def cargar_datos(path):
    df = pd.read_csv(path)
    columnas_requeridas = {
        "Equipo", "xG_favor", "xGA_contra", "Forma", "Jerarquia",
        "Corners_Favor", "Corners_Contra"
    }
    faltantes = columnas_requeridas - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en el CSV: {faltantes}")
    return df.set_index("Equipo")


try:
    df_equipos = cargar_datos(CSV_PATH)
except FileNotFoundError:
    st.error(f"⚠ No se encontró el archivo `{CSV_PATH}`.")
    st.stop()
except ValueError as e:
    st.error(f"⚠ {e}")
    st.stop()


# ==============================================================
# 3. MOTOR MATEMÁTICO AVANZADO Y MOMIOS JUSTOS (FAIR ODDS)
# ==============================================================
def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def formatear_momio_justo(prob):
    if prob <= 0.005:
        return "99.0 (+9800)"
    if prob >= 0.995:
        return "1.01 (-10000)"

    decimal_odd = 1.0 / prob
    if prob >= 0.5:
        americano = -int(round((prob / (1.0 - prob)) * 100))
        str_amer = f"{americano}"
    else:
        americano = int(round(((1.0 - prob) / prob) * 100))
        str_amer = f"+{americano}"

    return f"{decimal_odd:.2f} ({str_amer})"


def obtener_factor_localia(eq_local, row_local):
    if "Localia" in row_local and pd.notna(row_local["Localia"]):
        return float(row_local["Localia"])
    return _LOCALIA_NORMALIZADA.get(_normalizar(eq_local), HOME_ADVANTAGE_DEFAULT)


def calcular_xg_esperado(eq_local, row_local, row_visit, liga_gf_avg, liga_ga_avg):
    ataque_local = row_local["xG_favor"] / liga_gf_avg
    defensa_visit = row_visit["xGA_contra"] / liga_ga_avg
    ataque_visit = row_visit["xG_favor"] / liga_gf_avg
    defensa_local = row_local["xGA_contra"] / liga_ga_avg

    fuerza_base_local = (ataque_local * defensa_visit) ** 0.85
    fuerza_base_visit = (ataque_visit * defensa_local) ** 0.85

    forma_local = 0.92 + (row_local["Forma"] * 0.16)
    forma_visit = 0.92 + (row_visit["Forma"] * 0.16)

    diff_jerarquia = (row_local["Jerarquia"] - row_visit["Jerarquia"]) * 0.01
    ventaja_local = obtener_factor_localia(eq_local, row_local)

    xg_local = (liga_gf_avg * fuerza_base_local * ventaja_local
                * forma_local * (1 + diff_jerarquia))
    xg_visit = (liga_gf_avg * fuerza_base_visit
                * forma_visit * (1 - diff_jerarquia))

    xg_local = max(0.25, min(xg_local, 3.80))
    xg_visit = max(0.20, min(xg_visit, 3.50))

    return round(xg_local, 3), round(xg_visit, 3), round(ventaja_local, 2)


def tau_dixon_coles(gl, gv, xg_local, xg_visit, rho=DIXON_COLES_RHO):
    if gl == 0 and gv == 0:
        return max(0.0, 1.0 - (xg_local * xg_visit * rho))
    elif gl == 0 and gv == 1:
        return max(0.0, 1.0 + (xg_local * rho))
    elif gl == 1 and gv == 0:
        return max(0.0, 1.0 + (xg_visit * rho))
    elif gl == 1 and gv == 1:
        return max(0.0, 1.0 - rho)
    return 1.0


def generar_matriz_poisson(xg_local, xg_visit, max_goles=MAX_GOLES_CALCULO):
    matriz = {}
    suma_total = 0.0

    for gl in range(max_goles + 1):
        p_l = poisson_pmf(gl, xg_local)
        for gv in range(max_goles + 1):
            p_v = poisson_pmf(gv, xg_visit)
            prob_final = (p_l * p_v) * tau_dixon_coles(gl, gv, xg_local, xg_visit)
            matriz[(gl, gv)] = prob_final
            suma_total += prob_final

    if suma_total > 0:
        for k in matriz:
            matriz[k] /= suma_total

    return matriz


def calcular_mercados(matriz):
    p_local = p_empate = p_visit = 0.0
    p_btts = p_over25 = p_under25 = p_under35 = 0.0
    p_clean_local = p_clean_visit = 0.0
    p_handicap_local_15 = p_handicap_visit_15 = 0.0

    for (gl, gv), p in matriz.items():
        if gl > gv:
            p_local += p
        elif gl == gv:
            p_empate += p
        else:
            p_visit += p

        if gl >= 1 and gv >= 1:
            p_btts += p
        if (gl + gv) >= 3:
            p_over25 += p
        else:
            p_under25 += p
        if (gl + gv) <= 3:
            p_under35 += p
        if gv == 0:
            p_clean_local += p
        if gl == 0:
            p_clean_visit += p

        if (gl - gv) >= 2:
            p_handicap_local_15 += p
        if (gv - gl) >= 2:
            p_handicap_visit_15 += p

    sin_empate = p_local + p_visit
    dnb_local = (p_local / sin_empate) if sin_empate > 0 else 0.5
    dnb_visit = (p_visit / sin_empate) if sin_empate > 0 else 0.5

    doble_1x = p_local + p_empate
    doble_x2 = p_visit + p_empate

    return {
        "local": p_local, "empate": p_empate, "visitante": p_visit,
        "btts": p_btts, "no_btts": 1.0 - p_btts,
        "over25": p_over25, "under25": p_under25, "under35": p_under35,
        "clean_sheet_local": p_clean_local, "clean_sheet_visitante": p_clean_visit,
        "dnb_local": dnb_local, "dnb_visit": dnb_visit,
        "doble_1x": doble_1x, "doble_x2": doble_x2,
        "hc_local_15": p_handicap_local_15, "hc_visit_15": p_handicap_visit_15,
    }


def top_marcadores(matriz, top_n=3, max_goles=MAX_GOLES_DISPLAY):
    filtrados = {k: v for k, v in matriz.items() if k[0] <= max_goles and k[1] <= max_goles}
    return sorted(filtrados.items(), key=lambda x: x[1], reverse=True)[:top_n]


def calcular_xcorners(row_local, row_visit, xg_local, xg_visit, linea=LINEA_CORNERS):
    base_local = (row_local["Corners_Favor"] + row_visit["Corners_Contra"]) / 2.0
    base_visit = (row_visit["Corners_Favor"] + row_local["Corners_Contra"]) / 2.0

    dominio_local = (xg_local / max(xg_visit, 0.3)) ** 0.12
    dominio_visit = (xg_visit / max(xg_local, 0.3)) ** 0.12

    corners_local = base_local * dominio_local
    corners_visit = base_visit * dominio_visit
    total_corners = corners_local + corners_visit

    k_max_under = int(math.floor(linea))
    prob_under = sum(poisson_pmf(k, total_corners) for k in range(k_max_under + 1))
    prob_over = max(0.0, min(1.0, 1.0 - prob_under))

    return (
        round(corners_local, 2),
        round(corners_visit, 2),
        round(total_corners, 2),
        round(prob_over, 3),
        round(prob_under, 3),
    )


# ==============================================================
# 4. LÓGICA DE ANÁLISIS, RADAR EJECUTIVO Y TARJETAS VISUALES
# ==============================================================
def analizar_partido(eq_local, eq_visitante, liga_gf_avg, liga_ga_avg):
    row_local = df_equipos.loc[eq_local]
    row_visit = df_equipos.loc[eq_visitante]

    xg_l, xg_v, factor_loc = calcular_xg_esperado(eq_local, row_local, row_visit, liga_gf_avg, liga_ga_avg)
    matriz = generar_matriz_poisson(xg_l, xg_v)
    mercados = calcular_mercados(matriz)
    top3 = top_marcadores(matriz, top_n=3)
    xc_l, xc_v, total_corners, prob_over_c, prob_under_c = calcular_xcorners(row_local, row_visit, xg_l, xg_v)

    return {
        "local": eq_local,
        "visitante": eq_visitante,
        "error": False,
        "xg_l": xg_l,
        "xg_v": xg_v,
        "factor_loc": factor_loc,
        "forma_l": float(row_local["Forma"]),
        "forma_v": float(row_visit["Forma"]),
        "jerarquia_l": float(row_local["Jerarquia"]),
        "jerarquia_v": float(row_visit["Jerarquia"]),
        "xga_l": float(row_local["xGA_contra"]),
        "xga_v": float(row_visit["xGA_contra"]),
        "matriz": matriz,
        "mercados": mercados,
        "top3": top3,
        "xc_l": xc_l,
        "xc_v": xc_v,
        "total_corners": total_corners,
        "prob_over_c": prob_over_c,
        "prob_under_c": prob_under_c,
    }


def render_radar_jornada(resultados_validos):
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
        if r["prob_over_c"] > max_prob_c:
            max_prob_c = r["prob_over_c"]
            mejor_corner = (r, f"Over {LINEA_CORNERS} Córners", r["prob_over_c"], f"Media Proy: {r['total_corners']} 🚩")
        if r["prob_under_c"] > max_prob_c:
            max_prob_c = r["prob_under_c"]
            mejor_corner = (r, f"Under {LINEA_CORNERS} Córners", r["prob_under_c"], f"Media Proy: {r['total_corners']} 🚩")

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
                    <div class="radar-match">{EMOJIS_LIGA.get(r_match['local'], '⚽')} {r_match['local']} vs {r_match['visitante']} {EMOJIS_LIGA.get(r_match['visitante'], '⚽')}</div>
                    <div class="radar-pick">{pick_str} · {prob_val*100:.1f}%</div>
                    <div class="radar-odds">💡 Fair Odd: <b style="color:#fff;">{momio_str}</b><br>{extra_info}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    st.write("")


def crear_heatmap_plotly(matriz, local, visitante):
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
            [0.0, '#090d16'],
            [0.15, '#112233'],
            [0.4, '#0f5257'],
            [0.7, '#00b4d8'],
            [1.0, '#00ff9d']
        ],
        showscale=False,
        opacity=0.82,
        xgap=4,
        ygap=4
    ))

    fig.update_layout(
        xaxis=dict(
            title=dict(text=f"{visitante.upper()} (GOLES) →", font=dict(family="JetBrains Mono", size=12, color="#ffd700")),
            side="top",
            tickfont=dict(family="JetBrains Mono", color="#ffd700")
        ),
        yaxis=dict(
            title=dict(text=f"← {local.upper()} (GOLES)", font=dict(family="JetBrains Mono", size=12, color="#00ff9d")),
            autorange="reversed",
            tickfont=dict(family="JetBrains Mono", color="#00ff9d")
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=55, b=20),
        height=420
    )
    return fig


def render_resultado(r, idx_partido):
    local = r["local"]
    visitante = r["visitante"]
    mercados = r["mercados"]
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
        # 1. SCOREBOARD TV HEADER (HTML PURO CON ESCUDOS ALINEADOS)
        st.markdown(
            f"""
            <div class="scoreboard">
                <div class="sb-team">
                    {escudo_html(local)}
                    <div>
                        <div class="sb-name">{EMOJIS_LIGA.get(local, '⚽')} {local}</div>
                        <div class="sb-tag">LOCAL · xG: <b style="color:#00ff9d;">{xg_l:.2f}</b> · Loc: x{r['factor_loc']}</div>
                    </div>
                </div>
                <div class="sb-center">
                    <div class="vs-circle">VS</div>
                    <div class="sb-meta">PARTIDO #{idx_partido + 1} · DIXON-COLES</div>
                </div>
                <div class="sb-team right">
                    <div>
                        <div class="sb-name">{visitante} {EMOJIS_LIGA.get(visitante, '⚽')}</div>
                        <div class="sb-tag">VISITA · xG: <b style="color:#ffd700;">{xg_v:.2f}</b> · Total: {xg_l + xg_v:.2f}</div>
                    </div>
                    {escudo_html(visitante)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. BARRA TRICOLOR 1X2 (TUG-OF-WAR VISUAL)
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
                <span style="font-family:'JetBrains Mono', monospace; background:rgba(0,0,0,0.4); padding:4px 10px; border-radius:6px; color:#00ff9d;">
                    💡 Cuota Justa Mínima: <b>{momio_top}</b>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4. FILA 1X2 DETALLADA
        col1, col2, col3 = st.columns(3)
        etiquetas_1x2 = [
            (col1, f"👑 {local} (1)" if pick_top == f"Gana {local}" else f"Gana {local} (1)", mercados["local"]),
            (col2, "👑 Empate (X)" if pick_top == "Empate" else "Empate (X)", mercados["empate"]),
            (col3, f"👑 {visitante} (2)" if pick_top == f"Gana {visitante}" else f"Gana {visitante} (2)", mercados["visitante"]),
        ]
        for col, label, prob in etiquetas_1x2:
            with col:
                st.metric(label, f"{prob*100:.1f}%", delta=f"Fair Odd: {formatear_momio_justo(prob)}", delta_color="off")

        st.write("")

        # 5. MERCADOS ASIÁTICOS Y DE PROTECCIÓN
        st.markdown("<div class='sec-header'>🛡️ Mercados Asiáticos y Protección de Bankroll</div>", unsafe_allow_html=True)
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.metric(
                f"🛡️ {local} DNB (Sin Empate)",
                f"{mercados['dnb_local']*100:.1f}%",
                delta=f"Fair: {formatear_momio_justo(mercados['dnb_local'])}",
                delta_color="off"
            )
        with a2:
            st.metric(
                f"🛡️ {visitante} DNB (Sin Empate)",
                f"{mercados['dnb_visit']*100:.1f}%",
                delta=f"Fair: {formatear_momio_justo(mercados['dnb_visit'])}",
                delta_color="off"
            )
        with a3:
            if mercados["doble_1x"] >= mercados["doble_x2"]:
                lbl_dc, prob_dc = f"🔒 Doble Op: {local}/Emp", mercados["doble_1x"]
            else:
                lbl_dc, prob_dc = f"🔒 Doble Op: {visitante}/Emp", mercados["doble_x2"]
            st.metric(lbl_dc, f"{prob_dc*100:.1f}%", delta=f"Fair: {formatear_momio_justo(prob_dc)}", delta_color="off")
        with a4:
            if mercados["hc_local_15"] >= mercados["hc_visit_15"]:
                lbl_hc, prob_hc = f"⚡ {local} (-1.5 Goles)", mercados["hc_local_15"]
            else:
                lbl_hc, prob_hc = f"⚡ {visitante} (-1.5 Goles)", mercados["hc_visit_15"]
            st.metric(lbl_hc, f"{prob_hc*100:.1f}%", delta=f"Fair: {formatear_momio_justo(prob_hc)}", delta_color="off")

        st.write("")

        # 6. BLOQUE INFERIOR: PODIO DE MARCADORES, CÓRNERS Y GOLES
        col_izq, col_der = st.columns([5, 6])

        with col_izq:
            st.markdown("<div class='sec-header'>🎯 Podio de Marcadores Exactos</div>", unsafe_allow_html=True)
            cols_top = st.columns(3)
            clases_medalla = ["medal-gold", "medal-silver", "medal-bronze"]
            titulos_medalla = ["🥇 1º LUGAR", "🥈 2º LUGAR", "🥉 3º LUGAR"]

            for idx, ((gl, gv), prob) in enumerate(r["top3"]):
                with cols_top[idx]:
                    st.markdown(
                        f"""
                        <div class="medal-card {clases_medalla[idx]}">
                            <div style="font-size:0.70rem; color:#cbd5e1; font-weight:700;">{titulos_medalla[idx]}</div>
                            <div class="medal-score">{gl} - {gv}</div>
                            <div class="medal-prob">{prob*100:.1f}% prob.</div>
                            <div style="font-size:0.68rem; color:#94a3b8; margin-top:2px;">{formatear_momio_justo(prob)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.write("")
            st.markdown("<div class='sec-header'>🚩 Córners (Poisson + Dominio)</div>", unsafe_allow_html=True)
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.metric(f"🚩 {local}", f"{r['xc_l']}")
            with cc2:
                st.metric("🔥 TOTAL", f"{r['total_corners']}")
            with cc3:
                st.metric(f"🚩 {visitante}", f"{r['xc_v']}")

            if r["prob_over_c"] >= r["prob_under_c"]:
                prob_c = r["prob_over_c"]
                pick_corners = f"🔥 OVER {LINEA_CORNERS} CÓRNERS ({prob_c*100:.1f}%) · Fair: {formatear_momio_justo(prob_c)}"
                color_pick = "#00ff9d"
            else:
                prob_c = r["prob_under_c"]
                pick_corners = f"🧊 UNDER {LINEA_CORNERS} CÓRNERS ({prob_c*100:.1f}%) · Fair: {formatear_momio_justo(prob_c)}"
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
            st.markdown("<div class='sec-header'>📈 Mercado de Goles y Porterías</div>", unsafe_allow_html=True)
            goles_totales = xg_l + xg_v
            g1, g2, g3 = st.columns(3)
            with g1:
                st.metric("⚽ Goles Esp.", f"{goles_totales:.2f}", delta=f"Under 2.5: {mercados['under25']*100:.1f}%", delta_color="off")
            with g2:
                st.metric("🤝 Ambos Anotan", f"{mercados['btts']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['btts'])}", delta_color="off")
            with g3:
                st.metric("🔥 Over 2.5", f"{mercados['over25']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['over25'])}", delta_color="off")

            st.write("")
            g4, g5, g6 = st.columns(3)
            with g4:
                st.metric("🧊 Under 3.5", f"{mercados['under35']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['under35'])}", delta_color="off")
            with g5:
                st.metric(f"🛡️ Cero {local}", f"{mercados['clean_sheet_local']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['clean_sheet_local'])}", delta_color="off")
            with g6:
                st.metric(f"🛡️ Cero {visitante}", f"{mercados['clean_sheet_visitante']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['clean_sheet_visitante'])}", delta_color="off")

        st.write("")
        # 7. EXPANDER DE MATRIZ DE CALOR Y RADIOGRAFÍA DE PLANTILLAS
        with st.expander("📊 ABRIR MATRIZ DE PROBABILIDAD EXACTA (PLOTLY) Y COMPARATIVA DE PLANTILLAS"):
            m_col1, m_col2 = st.columns([6, 4])
            with m_col1:
                fig = crear_heatmap_plotly(r["matriz"], local, visitante)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"plotly_{idx_partido}")
            with m_col2:
                st.markdown("<div class='sec-header'>📋 Radiografía de Plantillas</div>", unsafe_allow_html=True)
                st.metric(f"Forma Reciente ({local} vs {visitante})", f"{r['forma_l']*100:.0f}% vs {r['forma_v']*100:.0f}%")
                st.metric(f"Jerarquía ({local} vs {visitante})", f"{r['jerarquia_l']:.0f}/10 vs {r['jerarquia_v']:.0f}/10")
                st.metric(f"xGA Defensivo ({local} vs {visitante})", f"{r['xga_l']:.2f} vs {r['xga_v']:.2f}")


# ==============================================================
# 5. INTERFAZ PRINCIPAL: HERO BANNER + PANEL DE JORNADA
# ==============================================================
st.markdown("""
<div class="hero-box">
    <div class="status-pill"><span class="pulse-dot"></span> ENGINE ONLINE · DIXON-COLES + POISSON V4.0</div>
    <h1 class="main-title">TERMINAL SHARP · LIGA MX</h1>
    <p class="subtitle">Escáner Cuantitativo de Jornada · Momios Justos (+EV) · Mercados Asiáticos</p>
</div>
""", unsafe_allow_html=True)

# Si ya hay resultados calculados, colapsamos el configurador automáticamente para lucir el Radar
ya_calculado = "resultados_jornada" in st.session_state

with st.expander("⚙️ CONFIGURAR LOS 9 CRUCES DE LA JORNADA (CLIC PARA ABRIR / CERRAR)", expanded=not ya_calculado):
    with st.form("form_jornada"):
        partidos_jornada = []
        for i in range(1, NUM_PARTIDOS + 1):
            c1, c2, c3 = st.columns([4.2, 1.2, 4.2])
            with c1:
                local = st.selectbox(
                    f"Local {i}",
                    df_equipos.index,
                    index=min((i - 1) * 2, len(df_equipos.index) - 1),
                    key=f"loc_{i}",
                    label_visibility="collapsed",
                    format_func=lambda x: f"🏠 {EMOJIS_LIGA.get(x, '⚽')} {x}"
                )
            with c2:
                st.markdown(
                    f"<div style='text-align:center; font-family:Orbitron,sans-serif; font-size:0.8rem; "
                    f"font-weight:900; color:#ffd700; padding-top:8px;'>JUEGO {i}</div>",
                    unsafe_allow_html=True
                )
            with c3:
                visitante = st.selectbox(
                    f"Visitante {i}",
                    df_equipos.index,
                    index=min((i - 1) * 2 + 1, len(df_equipos.index) - 1),
                    key=f"vis_{i}",
                    label_visibility="collapsed",
                    format_func=lambda x: f"✈️ {EMOJIS_LIGA.get(x, '⚽')} {x}"
                )

            partidos_jornada.append({"local": local, "visitante": visitante})
            if i < NUM_PARTIDOS:
                st.markdown("<hr style='margin: 0.35em 0px; border-color: rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

        st.write("")
        escanear = st.form_submit_button("⚡ EJECUTAR SIMULACIÓN CUANTITATIVA DE JORNADA ⚡", use_container_width=True)

if escanear:
    liga_gf_avg = df_equipos["xG_favor"].mean()
    liga_ga_avg = df_equipos["xGA_contra"].mean()

    resultados = []
    for p in partidos_jornada:
        if p["local"] == p["visitante"]:
            resultados.append({"local": p["local"], "visitante": p["visitante"], "error": True})
        else:
            resultados.append(analizar_partido(p["local"], p["visitante"], liga_gf_avg, liga_ga_avg))

    st.session_state["resultados_jornada"] = resultados
    st.rerun()

resultados_guardados = st.session_state.get("resultados_jornada")
if resultados_guardados:
    validos = [r for r in resultados_guardados if not r["error"]]
    render_radar_jornada(validos)

    st.markdown("<div class='sec-header'>📋 ANÁLISIS PROFUNDO PARTIDO POR PARTIDO</div>", unsafe_allow_html=True)
    for idx_partido, r in enumerate(resultados_guardados):
        if r["error"]:
            st.error(f"⚠️ Error en el Partido {idx_partido + 1}: {r['local']} no puede jugar contra sí mismo.")
        else:
            render_resultado(r, idx_partido)
else:
    st.info("👆 Configura los 9 partidos en el panel superior y presiona **EJECUTAR SIMULACIÓN CUANTITATIVA DE JORNADA**.")
