#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 TERMINAL SHARP: LIGA MX (CYBER-QUANT UI EDITION · V5.0)
 Dashboard web de predicción cuantitativa con Cartelera Grid:
 - Diccionario Oficial LOGOS_LIGA_MX (Wikimedia / ESPN CDN + Fallback)
 - Navegación SPA fluida mediante st.session_state.partido_activo
 - Vista A: Cartelera Interactiva en Cuadrícula (3 columnas estilo Flashscore)
 - Vista B: Análisis Profundo de Partido (Scoreboard 64px, 1X2, Asiáticos, Podio)
 - Motor Poisson + Corrección Dixon-Coles + Córners por Dominio
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
ESCUDO_GRID_PX = 32            # Tamaño de logo en Cartelera (Vista A)
ESCUDO_HEADER_PX = 64          # Tamaño de logo en Scoreboard TV (Vista B)
NUM_PARTIDOS = 9               # Total de partidos por jornada

FACTOR_LOCALIA_EQUIPOS = {
    "Toluca": 1.26, "Pumas": 1.24, "Pumas UNAM": 1.24, "Pachuca": 1.24,
    "América": 1.23, "Cruz Azul": 1.22, "Tigres": 1.23, "Tigres UANL": 1.23,
    "Monterrey": 1.22, "Guadalajara": 1.19, "Guadalajara (Chivas)": 1.19,
    "León": 1.20, "Santos": 1.18, "Santos Laguna": 1.18, "Atlas": 1.16,
    "San Luis": 1.17, "Atlético de San Luis": 1.17, "Necaxa": 1.16,
    "Tijuana": 1.21, "Tijuana (Xolos)": 1.21, "Puebla": 1.16,
    "Querétaro": 1.14, "Juárez": 1.13, "FC Juárez": 1.13,
    "Mazatlán": 1.12, "Mazatlán FC": 1.12, "Atlante": 1.18,
}

HORARIOS_JORNADA_DEFAULT = [
    "VIE · 19:00 HRS",
    "VIE · 21:05 HRS",
    "SÁB · 17:00 HRS",
    "SÁB · 19:00 HRS",
    "SÁB · 19:05 HRS",
    "SÁB · 21:10 HRS",
    "DOM · 12:00 HRS",
    "DOM · 18:00 HRS",
    "DOM · 20:05 HRS",
]

# ==============================================================
# 1. DICCIONARIO DE LOGOS OFICIALES (LIGA MX) Y FALLBACKS
# ==============================================================
LOGOS_LIGA_MX = {
    "América": "https://commons.wikimedia.org/wiki/Special:FilePath/Club%20Am%C3%A9rica%20flag.svg",
    "Atlas": "https://commons.wikimedia.org/wiki/Special:FilePath/F%C3%BAtbol%20Club%20Atlas.svg",
    "Atlético de San Luis": "https://commons.wikimedia.org/wiki/Special:FilePath/Atl%C3%A9tico%20San%20Luis%20Logo%20Proper.svg",
    "Cruz Azul": "https://commons.wikimedia.org/wiki/Special:FilePath/Club%20de%20Futbol%20Cruz%20Azul.svg",
    "FC Juárez": "https://commons.wikimedia.org/wiki/Special:FilePath/FC%20Ju%C3%A1rez%20logo.svg",
    "Guadalajara (Chivas)": "https://commons.wikimedia.org/wiki/Special:FilePath/Logo%20del%20Club%20Deportivo%20Guadalajara%20(M%C3%A9xico).svg",
    "León": "https://commons.wikimedia.org/wiki/Special:FilePath/Leon.svg",
    "Mazatlán FC": "https://commons.wikimedia.org/wiki/Special:FilePath/Mazatlan%20FC%20Flag.png",
    "Monterrey": "https://commons.wikimedia.org/wiki/Special:FilePath/Club%20de%20F%C3%BAtbol%20Monterrey%202019%20Logo.svg",
    "Necaxa": "https://commons.wikimedia.org/wiki/Special:FilePath/Club%20Necaxa%20Logo.svg",
    "Pachuca": "https://commons.wikimedia.org/wiki/Special:FilePath/Escudo%20del%20Club%20de%20F%C3%BAtbol%20Pachuca.png",
    "Puebla": "https://commons.wikimedia.org/wiki/Special:FilePath/Club%20Puebla%20logo.svg",
    "Pumas UNAM": "https://commons.wikimedia.org/wiki/Special:FilePath/Logo%20Pumas%20de%20la%20UNAM.jpg",
    "Querétaro": "https://commons.wikimedia.org/wiki/Special:FilePath/Gallosblancos.jpg",
    "Santos Laguna": "https://commons.wikimedia.org/wiki/Special:FilePath/Escudo%20del%20Club%20Santos%20Laguna.png",
    "Tigres UANL": "https://commons.wikimedia.org/wiki/Special:FilePath/Escudo%20del%20Club%20de%20F%C3%BAtbol%20Tigres%20UANL.svg",
    "Toluca": "https://commons.wikimedia.org/wiki/Special:FilePath/Club%20Toluca%20Logo.svg",
    "Tijuana (Xolos)": "https://commons.wikimedia.org/wiki/Special:FilePath/Club-Tijuana.jpg",
    # Soporte adicional en caso de que el CSV incluya a Atlante
    "Atlante": "https://commons.wikimedia.org/wiki/Special:FilePath/Atlante%20FC.png",
}

ALIAS_EQUIPOS = {
    "america": "América",
    "club america": "América",
    "aguilas": "América",
    "atlas": "Atlas",
    "san luis": "Atlético de San Luis",
    "atletico san luis": "Atlético de San Luis",
    "atletico de san luis": "Atlético de San Luis",
    "cruz azul": "Cruz Azul",
    "maquina": "Cruz Azul",
    "juarez": "FC Juárez",
    "fc juarez": "FC Juárez",
    "bravos": "FC Juárez",
    "guadalajara": "Guadalajara (Chivas)",
    "chivas": "Guadalajara (Chivas)",
    "guadalajara (chivas)": "Guadalajara (Chivas)",
    "leon": "León",
    "club leon": "León",
    "mazatlan": "Mazatlán FC",
    "mazatlan fc": "Mazatlán FC",
    "monterrey": "Monterrey",
    "rayados": "Monterrey",
    "necaxa": "Necaxa",
    "pachuca": "Pachuca",
    "tuzos": "Pachuca",
    "puebla": "Puebla",
    "club puebla": "Puebla",
    "pumas": "Pumas UNAM",
    "pumas unam": "Pumas UNAM",
    "unam": "Pumas UNAM",
    "queretaro": "Querétaro",
    "gallos": "Querétaro",
    "gallos blancos": "Querétaro",
    "santos": "Santos Laguna",
    "santos laguna": "Santos Laguna",
    "tigres": "Tigres UANL",
    "tigres uanl": "Tigres UANL",
    "toluca": "Toluca",
    "diablos": "Toluca",
    "tijuana": "Tijuana (Xolos)",
    "xolos": "Tijuana (Xolos)",
    "club tijuana": "Tijuana (Xolos)",
    "tijuana (xolos)": "Tijuana (Xolos)",
    "atlante": "Atlante",
}

FALLBACK_BADGE = {
    "América": ("AME", "#FFCC00", "#0b1f4d"),
    "Atlas": ("ATL", "#d91c24", "#111111"),
    "Atlético de San Luis": ("ASL", "#c8102e", "#ffffff"),
    "Cruz Azul": ("CAZ", "#0033a0", "#ffffff"),
    "FC Juárez": ("JUA", "#009639", "#ffffff"),
    "Guadalajara (Chivas)": ("GDL", "#e30613", "#ffffff"),
    "León": ("LEO", "#0a8a3f", "#ffffff"),
    "Mazatlán FC": ("MAZ", "#582c83", "#ffffff"),
    "Monterrey": ("MTY", "#0a2240", "#ffffff"),
    "Necaxa": ("NEC", "#e30613", "#ffffff"),
    "Pachuca": ("PAC", "#002855", "#ffffff"),
    "Puebla": ("PUE", "#1c3f94", "#ffffff"),
    "Pumas UNAM": ("PUM", "#00205b", "#cba052"),
    "Querétaro": ("QRO", "#0033a0", "#ffffff"),
    "Santos Laguna": ("SAN", "#007a33", "#ffffff"),
    "Tigres UANL": ("TIG", "#fbaa19", "#002d72"),
    "Toluca": ("TOL", "#c8102e", "#ffffff"),
    "Tijuana (Xolos)": ("TIJ", "#e2231a", "#111111"),
    "Atlante": ("ATN", "#0033a0", "#ffcc00"),
}

EMOJIS_LIGA = {
    "América": "🦅", "Guadalajara": "🐐", "Guadalajara (Chivas)": "🐐",
    "Cruz Azul": "🚂", "Pumas": "🐾", "Pumas UNAM": "🐾",
    "Tigres": "🐯", "Tigres UANL": "🐯", "Monterrey": "⛰️",
    "Toluca": "👿", "Pachuca": "🐹", "León": "🦁",
    "Santos": "😇", "Santos Laguna": "😇", "Atlas": "🦊",
    "Necaxa": "⚡", "Tijuana": "🐕", "Tijuana (Xolos)": "🐕",
    "Puebla": "🎽", "Juárez": "🐎", "FC Juárez": "🐎",
    "Mazatlán": "⚓", "Mazatlán FC": "⚓", "Querétaro": "🐓",
    "San Luis": "⛪", "Atlético de San Luis": "⛪", "Atlante": "🦈",
}


def _normalizar(texto):
    """Elimina acentos, convierte a minúsculas y limpia espacios."""
    texto = str(texto).strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


_LOGOS_NORMALIZADOS = {_normalizar(k): v for k, v in LOGOS_LIGA_MX.items()}
_FALLBACK_NORMALIZADO = {_normalizar(k): v for k, v in FALLBACK_BADGE.items()}
_LOCALIA_NORMALIZADA = {_normalizar(k): v for k, v in FACTOR_LOCALIA_EQUIPOS.items()}


def resolver_nombre_canonico(equipo):
    """
    Función auxiliar de resolución de nombres y desempate semántico.
    Convierte variantes del CSV ('San Luis', 'Guadalajara', 'Pumas', 'Mazatlán')
    a la clave oficial de LOGOS_LIGA_MX.
    """
    norm = _normalizar(equipo)
    if norm in ALIAS_EQUIPOS:
        return ALIAS_EQUIPOS[norm]
    for k_canon in LOGOS_LIGA_MX:
        if _normalizar(k_canon) == norm:
            return k_canon
    # Búsqueda parcial por subcadena en caso de nombres compuestos no previstos
    for alias_key, canon_val in ALIAS_EQUIPOS.items():
        if alias_key in norm or norm in alias_key:
            return canon_val
    return str(equipo).strip()


def obtener_logo_url(equipo, width_px=128):
    """Devuelve la URL oficial en alta resolución del club o None si requiere badge."""
    canon = resolver_nombre_canonico(equipo)
    base_url = LOGOS_LIGA_MX.get(canon) or _LOGOS_NORMALIZADOS.get(_normalizar(canon))
    if not base_url:
        return None
    if "commons.wikimedia.org" in base_url and "width=" not in base_url:
        return f"{base_url}?width={width_px}"
    return base_url


def obtener_iniciales_y_colores(equipo):
    """Devuelve (iniciales, color_fondo, color_texto) para el fallback visual."""
    canon = resolver_nombre_canonico(equipo)
    if canon in FALLBACK_BADGE:
        return FALLBACK_BADGE[canon]
    if _normalizar(canon) in _FALLBACK_NORMALIZADO:
        return _FALLBACK_NORMALIZADO[_normalizar(canon)]
    limpio = "".join(c for c in str(equipo).upper() if c.isalpha())
    return (limpio[:3] or "LMX", "#1e293b", "#00ff9d")


def escudo_html(equipo, size=ESCUDO_HEADER_PX):
    """
    Genera el HTML del escudo oficial con fallback automático en caso de error de red
    o empate/ausencia de nombre.
    """
    url = obtener_logo_url(equipo, width_px=max(size * 2, 128))
    iniciales, bg_col, txt_col = obtener_iniciales_y_colores(equipo)
    font_sz = max(10, int(size * 0.34))

    fallback_div = (
        f"<div style='width:{size}px;height:{size}px;min-width:{size}px;"
        f"border-radius:50%;background:{bg_col};color:{txt_col};"
        f"display:inline-flex;align-items:center;justify-content:center;"
        f"font-family:JetBrains Mono,monospace;font-weight:800;font-size:{font_sz}px;"
        f"border:1.5px solid rgba(255,255,255,0.28);box-shadow:0 3px 10px rgba(0,0,0,0.55);'>"
        f"{iniciales}</div>"
    )

    if not url:
        return fallback_div

    return (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;min-width:{size}px;">'
        f'<img src="{url}" alt="{equipo}" '
        f'style="width:{size}px;height:{size}px;object-fit:contain;'
        f'filter:drop-shadow(0 3px 8px rgba(0,0,0,0.65));" '
        f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'inline-flex\';">'
        f'<span style="display:none;width:{size}px;height:{size}px;min-width:{size}px;'
        f'border-radius:50%;background:{bg_col};color:{txt_col};'
        f'align-items:center;justify-content:center;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:800;font-size:{font_sz}px;border:1.5px solid rgba(255,255,255,0.28);'
        f'box-shadow:0 3px 10px rgba(0,0,0,0.55);">{iniciales}</span>'
        f'</span>'
    )


def generar_pastillas_forma(valor_forma, seed_offset=0):
    """
    Convierte el índice cuantitativo de Forma (0.0 a 1.0) en 5 pastillas visuales
    de últimos resultados (W / D / L) estilo Flashscore/SofaScore.
    """
    try:
        f_val = float(valor_forma)
    except (TypeError, ValueError):
        f_val = 0.50

    # Si el CSV trae Forma en escala 0-100 o 0-10, la normalizamos a 0.0-1.0
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
        "W": ("#10b981", "#03261b", "G"),
        "D": ("#64748b", "#f8fafc", "E"),
        "L": ("#ef4444", "#ffffff", "P"),
    }

    pills_html = []
    for res in secuencia:
        bg, fg, _ = colores[res]
        pills_html.append(
            f'<span class="form-pill" style="background:{bg};color:{fg};">{res}</span>'
        )
    return "".join(pills_html)


# ==============================================================
# 2. ESTÉTICA "CYBER-QUANT SPORTSBOOK TERMINAL" (CSS INYECTADO)
# ==============================================================
st.set_page_config(
    page_title="Terminal Sharp · Liga MX",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&family=Orbitron:wght@700;900&display=swap');

    [data-testid="stToolbar"] {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    .block-container {
        padding-top: 1.4rem !important;
        padding-bottom: 3rem !important;
        max-width: 1400px !important;
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
        background: linear-gradient(180deg, rgba(16, 24, 38, 0.88) 0%, rgba(8, 12, 20, 0.95) 100%);
        border: 1px solid rgba(255, 215, 0, 0.25);
        border-radius: 16px;
        padding: 20px 28px 16px 28px;
        margin-bottom: 1.25rem;
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

    /* Estilizado de Contenedores Glassmorphism */
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
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 1px;
        padding: 3px 9px;
        border-radius: 6px;
    }
    .grid-match-time {
        color: #94a3b8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.70rem;
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
        gap: 10px;
        min-width: 0;
    }
    .grid-team-name {
        font-size: 0.96rem;
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

    /* Botones Interactivos (Cartelera y Retorno) */
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

    /* Tarjetas del Radar Ejecutivo */
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
        gap: 18px;
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
        font-size: 0.84rem;
        font-weight: 800;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
        border-left: 3px solid #00ff9d;
        padding-left: 10px;
    }

    /* Botón de Submit Principal en el Configurador */
    div.stFormSubmitButton > button {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        font-size: 1.02rem !important;
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
# 3. CARGA DE DATOS (CON DATASET DE RESPALDO SI NO EXISTE CSV)
# ==============================================================
DATOS_DEFAULT_LIGA_MX = [
    {"Equipo": "América", "xG_favor": 1.88, "xGA_contra": 1.02, "Forma": 0.82, "Jerarquia": 9.5, "Corners_Favor": 5.8, "Corners_Contra": 4.1},
    {"Equipo": "Cruz Azul", "xG_favor": 1.82, "xGA_contra": 0.98, "Forma": 0.80, "Jerarquia": 9.0, "Corners_Favor": 5.9, "Corners_Contra": 3.9},
    {"Equipo": "Toluca", "xG_favor": 1.79, "xGA_contra": 1.15, "Forma": 0.76, "Jerarquia": 8.6, "Corners_Favor": 5.5, "Corners_Contra": 4.5},
    {"Equipo": "Tigres UANL", "xG_favor": 1.72, "xGA_contra": 1.05, "Forma": 0.72, "Jerarquia": 9.2, "Corners_Favor": 6.1, "Corners_Contra": 4.2},
    {"Equipo": "Monterrey", "xG_favor": 1.70, "xGA_contra": 1.08, "Forma": 0.70, "Jerarquia": 9.1, "Corners_Favor": 5.7, "Corners_Contra": 4.3},
    {"Equipo": "Guadalajara (Chivas)", "xG_favor": 1.56, "xGA_contra": 1.04, "Forma": 0.74, "Jerarquia": 8.7, "Corners_Favor": 5.4, "Corners_Contra": 4.4},
    {"Equipo": "Pumas UNAM", "xG_favor": 1.52, "xGA_contra": 1.18, "Forma": 0.62, "Jerarquia": 8.2, "Corners_Favor": 5.2, "Corners_Contra": 4.7},
    {"Equipo": "Pachuca", "xG_favor": 1.58, "xGA_contra": 1.26, "Forma": 0.60, "Jerarquia": 8.3, "Corners_Favor": 5.6, "Corners_Contra": 4.6},
    {"Equipo": "León", "xG_favor": 1.49, "xGA_contra": 1.28, "Forma": 0.64, "Jerarquia": 7.9, "Corners_Favor": 5.1, "Corners_Contra": 4.8},
    {"Equipo": "Atlético de San Luis", "xG_favor": 1.46, "xGA_contra": 1.32, "Forma": 0.58, "Jerarquia": 7.2, "Corners_Favor": 4.8, "Corners_Contra": 5.0},
    {"Equipo": "Atlas", "xG_favor": 1.28, "xGA_contra": 1.24, "Forma": 0.55, "Jerarquia": 7.4, "Corners_Favor": 4.6, "Corners_Contra": 4.9},
    {"Equipo": "Tijuana (Xolos)", "xG_favor": 1.42, "xGA_contra": 1.44, "Forma": 0.56, "Jerarquia": 7.1, "Corners_Favor": 4.9, "Corners_Contra": 5.2},
    {"Equipo": "Necaxa", "xG_favor": 1.34, "xGA_contra": 1.38, "Forma": 0.50, "Jerarquia": 6.9, "Corners_Favor": 4.5, "Corners_Contra": 5.3},
    {"Equipo": "Santos Laguna", "xG_favor": 1.31, "xGA_contra": 1.52, "Forma": 0.52, "Jerarquia": 7.3, "Corners_Favor": 4.7, "Corners_Contra": 5.4},
    {"Equipo": "Puebla", "xG_favor": 1.22, "xGA_contra": 1.58, "Forma": 0.42, "Jerarquia": 6.5, "Corners_Favor": 4.4, "Corners_Contra": 5.6},
    {"Equipo": "Querétaro", "xG_favor": 1.18, "xGA_contra": 1.55, "Forma": 0.44, "Jerarquia": 6.4, "Corners_Favor": 4.3, "Corners_Contra": 5.5},
    {"Equipo": "Mazatlán FC", "xG_favor": 1.20, "xGA_contra": 1.60, "Forma": 0.40, "Jerarquia": 6.3, "Corners_Favor": 4.2, "Corners_Contra": 5.7},
    {"Equipo": "FC Juárez", "xG_favor": 1.19, "xGA_contra": 1.64, "Forma": 0.38, "Jerarquia": 6.2, "Corners_Favor": 4.4, "Corners_Contra": 5.8},
]


@st.cache_data
def cargar_datos(path):
    columnas_requeridas = {
        "Equipo", "xG_favor", "xGA_contra", "Forma", "Jerarquia",
        "Corners_Favor", "Corners_Contra"
    }
    try:
        df = pd.read_csv(path)
        faltantes = columnas_requeridas - set(df.columns)
        if faltantes:
            raise ValueError(f"Faltan columnas en el CSV: {faltantes}")
        return df.set_index("Equipo"), True
    except FileNotFoundError:
        df_fallback = pd.DataFrame(DATOS_DEFAULT_LIGA_MX)
        return df_fallback.set_index("Equipo"), False


try:
    df_equipos, csv_cargado_ok = cargar_datos(CSV_PATH)
except ValueError as e:
    st.error(f"⚠ {e}")
    st.stop()


# ==============================================================
# 4. MOTOR MATEMÁTICO AVANZADO Y MOMIOS JUSTOS (FAIR ODDS)
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
    canon = resolver_nombre_canonico(eq_local)
    if canon in FACTOR_LOCALIA_EQUIPOS:
        return FACTOR_LOCALIA_EQUIPOS[canon]
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

    xg_local = (
        liga_gf_avg * fuerza_base_local * ventaja_local
        * forma_local * (1 + diff_jerarquia)
    )
    xg_visit = (
        liga_gf_avg * fuerza_base_visit
        * forma_visit * (1 - diff_jerarquia)
    )

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
    doble_12 = p_local + p_visit

    return {
        "local": p_local, "empate": p_empate, "visitante": p_visit,
        "btts": p_btts, "no_btts": 1.0 - p_btts,
        "over25": p_over25, "under25": p_under25, "under35": p_under35,
        "clean_sheet_local": p_clean_local, "clean_sheet_visitante": p_clean_visit,
        "dnb_local": dnb_local, "dnb_visit": dnb_visit,
        "doble_1x": doble_1x, "doble_x2": doble_x2, "doble_12": doble_12,
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


def analizar_partido(eq_local, eq_visitante, liga_gf_avg, liga_ga_avg, idx_partido=0, horario=None):
    row_local = df_equipos.loc[eq_local]
    row_visit = df_equipos.loc[eq_visitante]

    xg_l, xg_v, factor_loc = calcular_xg_esperado(eq_local, row_local, row_visit, liga_gf_avg, liga_ga_avg)
    matriz = generar_matriz_poisson(xg_l, xg_v)
    mercados = calcular_mercados(matriz)
    top3 = top_marcadores(matriz, top_n=3)
    xc_l, xc_v, total_corners, prob_over_c, prob_under_c = calcular_xcorners(row_local, row_visit, xg_l, xg_v)

    # Marcador proyectado coherente con el xG esperado y la cima de probabilidad Poisson
    gl_top, gv_top = top3[0][0]
    prob_marcador_top = top3[0][1]

    horario_str = horario or HORARIOS_JORNADA_DEFAULT[idx_partido % len(HORARIOS_JORNADA_DEFAULT)]

    return {
        "id": idx_partido,
        "local": eq_local,
        "visitante": eq_visitante,
        "horario": horario_str,
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
        "xgf_l": float(row_local["xG_favor"]),
        "xgf_v": float(row_visit["xG_favor"]),
        "matriz": matriz,
        "mercados": mercados,
        "top3": top3,
        "proy_gl": gl_top,
        "proy_gv": gv_top,
        "proy_prob": prob_marcador_top,
        "xc_l": xc_l,
        "xc_v": xc_v,
        "total_corners": total_corners,
        "prob_over_c": prob_over_c,
        "prob_under_c": prob_under_c,
    }


# ==============================================================
# 5. COMPONENTES VISUALES: RADAR, VISTA A (GRID) Y VISTA B (DETALLE)
# ==============================================================
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
        opacity=0.84,
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


def render_vista_cartelera_grid(resultados):
    """
    VISTA A: CARTELERA EN CUADRÍCULA (GRID 3 COLUMNAS ESTILO FLASHSCORE / SOFASCORE)
    """
    st.markdown(
        "<div class='sec-header'>🏟️ CARTELERA INTERACTIVA DE JORNADA · SELECCIONA UN ENCUENTRO PARA ANÁLISIS PROFUNDO</div>",
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
                        st.error(
                            f"⚠️ Partido #{idx_global + 1}: {r['local']} no puede enfrentarse a sí mismo. "
                            "Reconfigura este cruce arriba."
                        )
                        continue

                    local = r["local"]
                    visitante = r["visitante"]
                    mercados = r["mercados"]
                    logo_local_32 = escudo_html(local, size=ESCUDO_GRID_PX)
                    logo_visit_32 = escudo_html(visitante, size=ESCUDO_GRID_PX)

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

                    st.markdown(
                        f"""
                        <div class="grid-card-header">
                            <span class="grid-league-badge">⚽ LIGA MX · JORNADA</span>
                            <span class="grid-match-time">🕒 {r['horario']}</span>
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
                        key=f"btn_ver_partido_{idx_global}",
                        use_container_width=True,
                    ):
                        st.session_state.partido_activo = (local, visitante, idx_global)
                        st.rerun()


def render_vista_detalle_partido(r, idx_partido):
    """
    VISTA B: PANTALLA DETALLADA DE PARTIDO SELECCIONADO
    """
    # Botón prominente de retorno a la Cartelera Principal
    col_back, col_info = st.columns([3.5, 6.5])
    with col_back:
        if st.button("← Volver a la Cartelera de Jornada", key="btn_volver_cartelera", use_container_width=True):
            st.session_state.partido_activo = None
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:right; font-family:JetBrains Mono,monospace; font-size:0.80rem; "
            f"color:#94a3b8; padding-top:10px;'>"
            f"📍 EXPEDIENTE CUANTITATIVO · ENCUENTRO #{idx_partido + 1} · {r.get('horario', 'LIGA MX')}</div>",
            unsafe_allow_html=True,
        )

    st.write("")

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
        # 1. SCOREBOARD TV HEADER CON LOGOS OFICIALES EN GRANDE (64px)
        st.markdown(
            f"""
            <div class="scoreboard">
                <div class="sb-team">
                    {escudo_html(local, size=ESCUDO_HEADER_PX)}
                    <div>
                        <div class="sb-name">{EMOJIS_LIGA.get(local, '⚽')} {local}</div>
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
                        <div class="sb-name">{visitante} {EMOJIS_LIGA.get(visitante, '⚽')}</div>
                        <div class="sb-tag">VISITA · xG Proy: <b style="color:#ffd700;">{xg_v:.2f}</b> · xG Total: {xg_l + xg_v:.2f}</div>
                        <div style="margin-top:6px;display:flex;justify-content:flex-end;">{generar_pastillas_forma(r['forma_v'], seed_offset=idx_partido + 1)}</div>
                    </div>
                    {escudo_html(visitante, size=ESCUDO_HEADER_PX)}
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
            (col1, f"👑 {local} (1)" if pick_top == f"Gana {local}" else f"Gana {local} (1)", mercados["local"]),
            (col2, "👑 Empate (X)" if pick_top == "Empate" else "Empate (X)", mercados["empate"]),
            (col3, f"👑 {visitante} (2)" if pick_top == f"Gana {visitante}" else f"Gana {visitante} (2)", mercados["visitante"]),
        ]
        for col, label, prob in etiquetas_1x2:
            with col:
                st.metric(label, f"{prob*100:.1f}%", delta=f"Fair Odd: {formatear_momio_justo(prob)}", delta_color="off")

        st.write("")

        # 5. MERCADOS ASIÁTICOS, DOBLE OPORTUNIDAD Y DNB
        st.markdown("<div class='sec-header'>🛡️ Mercados Asiáticos, Doble Oportunidad y Draw No Bet (DNB)</div>", unsafe_allow_html=True)
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.metric(
                f"🛡️ {local} DNB (Sin Empate)",
                f"{mercados['dnb_local']*100:.1f}%",
                delta=f"Fair: {formatear_momio_justo(mercados['dnb_local'])}",
                delta_color="off",
            )
        with a2:
            st.metric(
                f"🛡️ {visitante} DNB (Sin Empate)",
                f"{mercados['dnb_visit']*100:.1f}%",
                delta=f"Fair: {formatear_momio_justo(mercados['dnb_visit'])}",
                delta_color="off",
            )
        with a3:
            if mercados["doble_1x"] >= mercados["doble_x2"]:
                lbl_dc, prob_dc = f"🔒 Doble Op: {local}/Emp (1X)", mercados["doble_1x"]
            else:
                lbl_dc, prob_dc = f"🔒 Doble Op: {visitante}/Emp (X2)", mercados["doble_x2"]
            st.metric(lbl_dc, f"{prob_dc*100:.1f}%", delta=f"Fair: {formatear_momio_justo(prob_dc)}", delta_color="off")
        with a4:
            if mercados["hc_local_15"] >= mercados["hc_visit_15"]:
                lbl_hc, prob_hc = f"⚡ Hándicap {local} (-1.5)", mercados["hc_local_15"]
            else:
                lbl_hc, prob_hc = f"⚡ Hándicap {visitante} (-1.5)", mercados["hc_visit_15"]
            st.metric(lbl_hc, f"{prob_hc*100:.1f}%", delta=f"Fair: {formatear_momio_justo(prob_hc)}", delta_color="off")

        st.write("")

        # 6. BLOQUE INFERIOR: PODIO DE MARCADORES, CÓRNERS Y GOLES
        col_izq, col_der = st.columns([5, 6])

        with col_izq:
            st.markdown("<div class='sec-header'>🎯 Podio de Marcadores Exactos (Oro / Plata / Bronce)</div>", unsafe_allow_html=True)
            cols_top = st.columns(3)
            clases_medalla = ["medal-gold", "medal-silver", "medal-bronze"]
            titulos_medalla = ["🥇 ORO (1º)", "🥈 PLATA (2º)", "🥉 BRONCE (3º)"]

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
            st.markdown("<div class='sec-header'>🚩 Línea de Córners Proyectada (Poisson + Dominio)</div>", unsafe_allow_html=True)
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.metric(f"🚩 {local}", f"{r['xc_l']}")
            with cc2:
                st.metric("🔥 TOTAL PROY.", f"{r['total_corners']}")
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
            st.markdown("<div class='sec-header'>📈 Over/Under de Goles, BTTS y Porterías Imbatidas</div>", unsafe_allow_html=True)
            goles_totales = xg_l + xg_v
            g1, g2, g3 = st.columns(3)
            with g1:
                st.metric("⚽ Goles Esp. (xG)", f"{goles_totales:.2f}", delta=f"Under 2.5: {mercados['under25']*100:.1f}%", delta_color="off")
            with g2:
                st.metric("🤝 Ambos Anotan (Sí)", f"{mercados['btts']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['btts'])}", delta_color="off")
            with g3:
                st.metric("🔥 Over 2.5 Goles", f"{mercados['over25']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['over25'])}", delta_color="off")

            st.write("")
            g4, g5, g6 = st.columns(3)
            with g4:
                st.metric("🧊 Under 3.5 Goles", f"{mercados['under35']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['under35'])}", delta_color="off")
            with g5:
                st.metric(f"🛡️ Cero {local}", f"{mercados['clean_sheet_local']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['clean_sheet_local'])}", delta_color="off")
            with g6:
                st.metric(f"🛡️ Cero {visitante}", f"{mercados['clean_sheet_visitante']*100:.1f}%", delta=f"Fair: {formatear_momio_justo(mercados['clean_sheet_visitante'])}", delta_color="off")

        st.write("")
        # 7. MATRIZ DE CALOR PLOTLY Y RADIOGRAFÍA DE PLANTILLAS
        st.markdown("<div class='sec-header'>📊 Matriz Interactiva de Probabilidad Exacta (0-0 a 6-6) y Comparativa</div>", unsafe_allow_html=True)
        m_col1, m_col2 = st.columns([6, 4])
        with m_col1:
            fig = crear_heatmap_plotly(r["matriz"], local, visitante)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"plotly_detail_{idx_partido}")
        with m_col2:
            st.markdown("<div class='sec-header'>📋 Radiografía de Plantillas</div>", unsafe_allow_html=True)
            st.metric(f"Forma Reciente ({local} vs {visitante})", f"{r['forma_l']*100:.0f}% vs {r['forma_v']*100:.0f}%")
            st.metric(f"Jerarquía de Plantel ({local} vs {visitante})", f"{r['jerarquia_l']:.1f}/10 vs {r['jerarquia_v']:.1f}/10")
            st.metric(f"xG a Favor Base ({local} vs {visitante})", f"{r['xgf_l']:.2f} vs {r['xgf_v']:.2f}")
            st.metric(f"xGA Defensivo ({local} vs {visitante})", f"{r['xga_l']:.2f} vs {r['xga_v']:.2f}")


# ==============================================================
# 6. ESTADO DE SESIÓN, SIMULACIÓN INICIAL Y NAVEGACIÓN PRINCIPAL
# ==============================================================
if "partido_activo" not in st.session_state:
    st.session_state.partido_activo = None

# Inicializamos automáticamente los 9 partidos en la primera carga para mostrar la Cartelera de inmediato
if "resultados_jornada" not in st.session_state:
    liga_gf_avg_init = df_equipos["xG_favor"].mean()
    liga_ga_avg_init = df_equipos["xGA_contra"].mean()
    equipos_lista = list(df_equipos.index)
    resultados_init = []
    for i in range(NUM_PARTIDOS):
        eq_l = equipos_lista[min(i * 2, len(equipos_lista) - 1)]
        eq_v = equipos_lista[min(i * 2 + 1, len(equipos_lista) - 1)]
        if eq_l == eq_v:
            resultados_init.append({"id": i, "local": eq_l, "visitante": eq_v, "error": True})
        else:
            resultados_init.append(
                analizar_partido(
                    eq_l, eq_v, liga_gf_avg_init, liga_ga_avg_init,
                    idx_partido=i, horario=HORARIOS_JORNADA_DEFAULT[i % len(HORARIOS_JORNADA_DEFAULT)]
                )
            )
    st.session_state["resultados_jornada"] = resultados_init

# HERO BANNER SUPERIOR
st.markdown("""
<div class="hero-box">
    <div class="status-pill"><span class="pulse-dot"></span> ENGINE ONLINE · DIXON-COLES + POISSON V5.0 · GRID EDITION</div>
    <h1 class="main-title">TERMINAL SHARP · LIGA MX</h1>
    <p class="subtitle">Cartelera Interactiva · Momios Justos (+EV) · Mercados Asiáticos</p>
</div>
""", unsafe_allow_html=True)

if not csv_cargado_ok:
    st.caption("ℹ️ Ejecutando con base de datos cuantitativa pre-integrada de los 18 clubes (coloca `ligamx_stats_completo.csv` en el directorio para usar tus métricas personalizadas).")

# ==============================================================
# ENRUTADOR DE VISTAS MEDIANTE st.session_state.partido_activo
# ==============================================================
resultados_guardados = st.session_state.get("resultados_jornada", [])

if st.session_state.partido_activo is None:
    # ----------------------------------------------------------
    # VISTA A: CONFIGURADOR + RADAR EJECUTIVO + CARTELERA EN CUADRÍCULA (3 COLUMNAS)
    # ----------------------------------------------------------
    with st.expander("⚙️ CONFIGURAR LOS 9 CRUCES DE LA JORNADA (CLIC PARA ABRIR / CERRAR)", expanded=False):
        with st.form("form_jornada"):
            partidos_jornada = []
            for i in range(1, NUM_PARTIDOS + 1):
                partido_prev = resultados_guardados[i - 1] if (i - 1) < len(resultados_guardados) else None
                idx_loc_default = (
                    list(df_equipos.index).index(partido_prev["local"])
                    if partido_prev and partido_prev["local"] in df_equipos.index
                    else min((i - 1) * 2, len(df_equipos.index) - 1)
                )
                idx_vis_default = (
                    list(df_equipos.index).index(partido_prev["visitante"])
                    if partido_prev and partido_prev["visitante"] in df_equipos.index
                    else min((i - 1) * 2 + 1, len(df_equipos.index) - 1)
                )

                c1, c2, c3 = st.columns([4.2, 1.6, 4.2])
                with c1:
                    local = st.selectbox(
                        f"Local {i}",
                        df_equipos.index,
                        index=idx_loc_default,
                        key=f"loc_{i}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"🏠 {EMOJIS_LIGA.get(x, '⚽')} {x}",
                    )
                with c2:
                    st.markdown(
                        f"<div style='text-align:center; font-family:Orbitron,sans-serif; font-size:0.78rem; "
                        f"font-weight:900; color:#ffd700; padding-top:8px;'>JUEGO {i}<br>"
                        f"<span style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:#94a3b8;'>"
                        f"{HORARIOS_JORNADA_DEFAULT[(i - 1) % len(HORARIOS_JORNADA_DEFAULT)]}</span></div>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    visitante = st.selectbox(
                        f"Visitante {i}",
                        df_equipos.index,
                        index=idx_vis_default,
                        key=f"vis_{i}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"✈️ {EMOJIS_LIGA.get(x, '⚽')} {x}",
                    )

                partidos_jornada.append({
                    "local": local,
                    "visitante": visitante,
                    "horario": HORARIOS_JORNADA_DEFAULT[(i - 1) % len(HORARIOS_JORNADA_DEFAULT)],
                })
                if i < NUM_PARTIDOS:
                    st.markdown("<hr style='margin: 0.35em 0px; border-color: rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

            st.write("")
            escanear = st.form_submit_button("⚡ ACTUALIZAR CARTELERA Y EJECUTAR SIMULACIÓN CUANTITATIVA ⚡", use_container_width=True)

        if escanear:
            liga_gf_avg = df_equipos["xG_favor"].mean()
            liga_ga_avg = df_equipos["xGA_contra"].mean()

            nuevos_resultados = []
            for idx_p, p in enumerate(partidos_jornada):
                if p["local"] == p["visitante"]:
                    nuevos_resultados.append({
                        "id": idx_p,
                        "local": p["local"],
                        "visitante": p["visitante"],
                        "horario": p["horario"],
                        "error": True,
                    })
                else:
                    nuevos_resultados.append(
                        analizar_partido(
                            p["local"], p["visitante"], liga_gf_avg, liga_ga_avg,
                            idx_partido=idx_p, horario=p["horario"]
                        )
                    )

            st.session_state["resultados_jornada"] = nuevos_resultados
            st.session_state.partido_activo = None
            st.rerun()

    validos = [r for r in resultados_guardados if not r.get("error")]
    render_radar_jornada(validos)
    render_vista_cartelera_grid(resultados_guardados)

else:
    # ----------------------------------------------------------
    # VISTA B: PANTALLA DETALLADA DEL PARTIDO SELECCIONADO
    # ----------------------------------------------------------
    seleccion = st.session_state.partido_activo
    partido_obj = None
    idx_sel = 0

    if isinstance(seleccion, tuple) and len(seleccion) == 3:
        loc_sel, vis_sel, idx_cand = seleccion
        if 0 <= idx_cand < len(resultados_guardados):
            cand = resultados_guardados[idx_cand]
            if not cand.get("error"):
                partido_obj = cand
                idx_sel = idx_cand
        if partido_obj is None:
            for i_r, r_item in enumerate(resultados_guardados):
                if not r_item.get("error") and r_item["local"] == loc_sel and r_item["visitante"] == vis_sel:
                    partido_obj = r_item
                    idx_sel = i_r
                    break
    elif isinstance(seleccion, int) and 0 <= seleccion < len(resultados_guardados):
        partido_obj = resultados_guardados[seleccion]
        idx_sel = seleccion

    if partido_obj is None or partido_obj.get("error"):
        st.warning("⚠️ El partido seleccionado ya no está disponible. Regresando a la cartelera...")
        st.session_state.partido_activo = None
        st.rerun()
    else:
        render_vista_detalle_partido(partido_obj, idx_sel)