#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 TERMINAL SHARP: LIGA MX (PRO QUANT EDITION)
 Dashboard web de predicción cuantitativa:
 - Modelo Poisson + Corrección Dixon-Coles
 - Amortiguación de xG + Localía Dinámica por Altitud/Estadio
 - Modelo de Córners por Dominio (Game State) + Poisson PMF
 - Escáner de Jornada Completa (9 Partidos) con st.form
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
ESCUDO_ANCHO_PX = 75           # Ancho uniforme de los escudos en las tarjetas de jornada
NUM_PARTIDOS = 9               # Total de partidos por jornada

# Factor de localía específico por cancha / altitud / fortaleza histórica
FACTOR_LOCALIA_EQUIPOS = {
    "Toluca": 1.26,       # 2,660m de altitud (Bombonera)
    "Pumas": 1.24,        # CDMX + factor horario/altitud
    "Pachuca": 1.24,      # 2,400m de altitud + ritmo dinámico
    "América": 1.23,      # Altitud CDMX + peso específico
    "Cruz Azul": 1.22,    # Altitud CDMX
    "Tigres": 1.23,       # El Volcán (fortaleza de local)
    "Monterrey": 1.22,    # Gigante de Acero
    "Guadalajara": 1.19,  # Estadio Akron
    "León": 1.20,         # Nou Camp
    "Santos": 1.18,       # TSM (calor/comarca)
    "Atlas": 1.16,
    "San Luis": 1.17,
    "Necaxa": 1.16,
    "Tijuana": 1.21,      # Pasto sintético (ventaja única)
    "Puebla": 1.16,
    "Querétaro": 1.14,
    "Juárez": 1.13,
    "Mazatlán": 1.12,
    "Atlante": 1.18,
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


def render_escudo(equipo, nombre_display):
    url = escudo_url(equipo)
    if url:
        st.image(url, width=ESCUDO_ANCHO_PX)
    else:
        iniciales, color_fondo, color_texto = _FALLBACK_NORMALIZADO.get(
            _normalizar(equipo), (nombre_display[:3].upper(), "#333333", "#ffffff")
        )
        st.markdown(
            f"""
            <div style="
                width:{ESCUDO_ANCHO_PX}px; height:{ESCUDO_ANCHO_PX}px;
                border-radius:50%; background:{color_fondo}; color:{color_texto};
                display:flex; align-items:center; justify-content:center;
                font-family:'Courier New', monospace; font-weight:800; font-size:1.1rem;
                border:2px solid rgba(255,255,255,0.25); margin-bottom:4px;">
                {iniciales}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================
# 1. ESTÉTICA "CASINO TERMINAL"
# ==============================================================
st.set_page_config(
    page_title="Liga MX - Predictor Cuantitativo",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stToolbar"] {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    .stApp {
        background: radial-gradient(circle at top, #10151c 0%, #05070a 100%);
    }
    h1, h2, h3 {
        font-family: 'Arial', sans-serif !important;
        letter-spacing: 1px;
    }
    .main-title {
        font-family: 'Arial', sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(90deg, #bf953f, #fcf6ba, #b38728, #fbf5b7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #7d8b99;
        font-family: 'Arial', sans-serif;
        font-size: 0.90rem;
        margin-top: 4px;
        margin-bottom: 2rem;
        text-transform: uppercase;
        letter-spacing: 3px;
    }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 255, 157, 0.15);
        border-radius: 10px;
        padding: 10px 14px;
        box-shadow: 0 0 18px rgba(0, 255, 157, 0.04);
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Arial', sans-serif;
        color: #00ff9d;
    }
    div[data-testid="stMetricLabel"] {
        color: #b8c4cf;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(90deg, #00c3ff, #00ff9d);
    }
    .pick-banner {
        background: linear-gradient(90deg, rgba(255,215,0,0.14), rgba(255,215,0,0.03));
        border: 1px solid rgba(255,215,0,0.45);
        border-radius: 10px;
        padding: 12px 18px;
        font-family: 'Arial', sans-serif;
        color: #ffd700;
        font-size: 1.1rem;
        text-align: center;
        margin: 0.8rem 0 1.2rem 0;
    }
    div.stButton > button {
        font-family: 'Arial', sans-serif;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        border-radius: 8px;
        border: 1px solid #00ff9d;
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
# 3. MOTOR MATEMÁTICO AVANZADO (Poisson + Dixon-Coles + Amortiguación)
# ==============================================================
def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def obtener_factor_localia(eq_local, row_local):
    """Obtiene la localía del CSV si existe la columna 'Localia', si no usa el diccionario por estadio."""
    if "Localia" in row_local and pd.notna(row_local["Localia"]):
        return float(row_local["Localia"])
    return _LOCALIA_NORMALIZADA.get(_normalizar(eq_local), HOME_ADVANTAGE_DEFAULT)


def calcular_xg_esperado(eq_local, row_local, row_visit, liga_gf_avg, liga_ga_avg):
    """
    Calcula el xG esperado con amortiguación para evitar doble conteo
    entre el xG base de la temporada, la Forma y la Jerarquía.
    """
    ataque_local = row_local["xG_favor"] / liga_gf_avg
    defensa_visit = row_visit["xGA_contra"] / liga_ga_avg
    ataque_visit = row_visit["xG_favor"] / liga_gf_avg
    defensa_local = row_local["xGA_contra"] / liga_ga_avg

    # Suavizamos la interacción ataque vs defensa (exponente 0.85 evita picos irreales)
    fuerza_base_local = (ataque_local * defensa_visit) ** 0.85
    fuerza_base_visit = (ataque_visit * defensa_local) ** 0.85

    # Amortiguación de Forma: impacto máximo de ±8% (0.92 a 1.08) en vez de ±15%
    forma_local = 0.92 + (row_local["Forma"] * 0.16)
    forma_visit = 0.92 + (row_visit["Forma"] * 0.16)

    # Amortiguación de Jerarquía: 1% por punto de diferencia (máx ±9%)
    diff_jerarquia = (row_local["Jerarquia"] - row_visit["Jerarquia"]) * 0.01

    # Localía específica por cancha/altitud
    ventaja_local = obtener_factor_localia(eq_local, row_local)

    xg_local = (liga_gf_avg * fuerza_base_local * ventaja_local
                * forma_local * (1 + diff_jerarquia))
    xg_visit = (liga_gf_avg * fuerza_base_visit
                * forma_visit * (1 - diff_jerarquia))

    # Límites de seguridad estadísticos (clamp)
    xg_local = max(0.25, min(xg_local, 3.80))
    xg_visit = max(0.20, min(xg_visit, 3.50))

    return round(xg_local, 3), round(xg_visit, 3), round(ventaja_local, 2)


def tau_dixon_coles(gl, gv, xg_local, xg_visit, rho=DIXON_COLES_RHO):
    """Factor de ajuste Tau de Dixon-Coles para corregir la subestimación de empates bajos."""
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
    """Genera la matriz de probabilidad de goles aplicando la corrección de Dixon-Coles y normalizando."""
    matriz = {}
    suma_total = 0.0

    for gl in range(max_goles + 1):
        p_l = poisson_pmf(gl, xg_local)
        for gv in range(max_goles + 1):
            p_v = poisson_pmf(gv, xg_visit)
            prob_base = p_l * p_v
            ajuste_dc = tau_dixon_coles(gl, gv, xg_local, xg_visit)
            prob_final = prob_base * ajuste_dc
            matriz[(gl, gv)] = prob_final
            suma_total += prob_final

    # Re-normalizar para garantizar que la suma de toda la matriz sea exactamente 1.0 (100%)
    if suma_total > 0:
        for k in matriz:
            matriz[k] /= suma_total

    return matriz


def calcular_mercados(matriz):
    p_local = p_empate = p_visit = 0.0
    p_btts = p_over25 = p_under35 = 0.0
    p_clean_local = p_clean_visit = 0.0

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
        if (gl + gv) <= 3:
            p_under35 += p
        if gv == 0:
            p_clean_local += p
        if gl == 0:
            p_clean_visit += p

    return {
        "local": p_local, "empate": p_empate, "visitante": p_visit,
        "btts": p_btts, "over25": p_over25, "under35": p_under35,
        "clean_sheet_local": p_clean_local, "clean_sheet_visitante": p_clean_visit,
    }


def top_marcadores(matriz, top_n=3, max_goles=MAX_GOLES_DISPLAY):
    filtrados = {k: v for k, v in matriz.items() if k[0] <= max_goles and k[1] <= max_goles}
    return sorted(filtrados.items(), key=lambda x: x[1], reverse=True)[:top_n]


def calcular_xcorners(row_local, row_visit, xg_local, xg_visit, linea=LINEA_CORNERS):
    """
    Calcula córners esperados ajustando por Dominio Territorial (xG Ratio)
    y obtiene la probabilidad exacta del Over/Under mediante distribución de Poisson.
    """
    base_local = (row_local["Corners_Favor"] + row_visit["Corners_Contra"]) / 2.0
    base_visit = (row_visit["Corners_Favor"] + row_local["Corners_Contra"]) / 2.0

    # Ajuste por dominio (Game State): quien proyecta más ataque genera más córners
    dominio_local = (xg_local / max(xg_visit, 0.3)) ** 0.12
    dominio_visit = (xg_visit / max(xg_local, 0.3)) ** 0.12

    corners_local = base_local * dominio_local
    corners_visit = base_visit * dominio_visit
    total_corners = corners_local + corners_visit

    # Probabilidad acumulada de Poisson para superar la línea (ej. 9.5 -> 10 o más córners)
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
# 4. LÓGICA DE ANÁLISIS Y RENDERIZADO DE TARJETAS
# ==============================================================
def analizar_partido(eq_local, eq_visitante, liga_gf_avg, liga_ga_avg):
    """Ejecuta todos los cálculos del partido y empaqueta los resultados para session_state."""
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


def crear_heatmap_plotly(matriz, local, visitante):
    """Genera el gráfico interactivo de Plotly para los marcadores exactos."""
    z_data = []
    text_data = []
    goles_rango = list(range(MATRIZ_MAX_GOLES + 1))

    for gl in goles_rango:
        row_z = []
        row_text = []
        for gv in goles_rango:
            prob = matriz.get((gl, gv), 0.0) * 100
            row_z.append(prob)
            row_text.append(f"{prob:.2f}%<br>{gl}-{gv}")
        z_data.append(row_z)
        text_data.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[str(x) for x in goles_rango],
        y=[str(y) for y in goles_rango],
        text=text_data,
        texttemplate="%{text}",
        textfont=dict(family="Arial", size=11, color="white"),
        hoverinfo="text",
        colorscale=[[0, '#0e1520'], [0.1, '#1d2a44'], [0.4, '#23607a'], [0.7, '#8b2516'], [1, '#c83219']],
        showscale=False,
        opacity=0.70,
        xgap=3,
        ygap=3
    ))

    fig.update_layout(
        xaxis=dict(
            title=dict(text=f"{visitante.upper()} (GOLES) →", font=dict(family="Arial", color="#ffd700")),
            side="top",
            tickfont=dict(family="Courier New", color="#ffd700")
        ),
        yaxis=dict(
            title=dict(text=f"← {local.upper()} (GOLES)", font=dict(family="Arial", color="#00ff9d")),
            autorange="reversed",
            tickfont=dict(family="Courier New", color="#00ff9d")
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=55, b=30),
        height=440
    )
    return fig


def render_resultado(r, idx_partido):
    """Dibuja la tarjeta ejecutiva completa para cada partido."""
    local = r["local"]
    visitante = r["visitante"]
    mercados = r["mercados"]
    xg_l = r["xg_l"]
    xg_v = r["xg_v"]

    opciones_1x2 = {
        f"Gana {local}": mercados["local"],
        "Empate": mercados["empate"],
        f"Gana {visitante}": mercados["visitante"],
    }
    pick_top = max(opciones_1x2, key=opciones_1x2.get)

    with st.container(border=True):
        # 1. ENCABEZADO CON ESCUDOS Y XG ESPERADO
        c_esc_l, c_tit, c_esc_v = st.columns([1.2, 6, 1.2])
        with c_esc_l:
            render_escudo(local, local)
        with c_tit:
            st.markdown(
                f"<h3 style='text-align:center; margin-bottom:2px;'>"
                f"{EMOJIS_LIGA.get(local, '⚽')} {local} &nbsp;vs&nbsp; {visitante} {EMOJIS_LIGA.get(visitante, '⚽')}"
                f"</h3>"
                f"<p style='text-align:center; color:#7d8b99; font-size:0.88rem; margin-top:0;'>"
                f"xG Proyectado: <b>{xg_l:.2f}</b> vs <b>{xg_v:.2f}</b> &nbsp;|&nbsp; "
                f"Factor Localía: <b>x{r['factor_loc']}</b> &nbsp;|&nbsp; Ajuste: <b>Dixon-Coles</b></p>",
                unsafe_allow_html=True,
            )
        with c_esc_v:
            render_escudo(visitante, visitante)

        # 2. BANNER DEL PICK PRINCIPAL
        st.markdown(
            f'<div class="pick-banner">🏆 PICK SUGERIDO (1X2): <b>{pick_top}</b> '
            f'&nbsp;·&nbsp; {opciones_1x2[pick_top]*100:.1f}% de probabilidad</div>',
            unsafe_allow_html=True,
        )

        # 3. MERCADO 1X2 (MONEYLINE)
        col1, col2, col3 = st.columns(3)
        etiquetas_1x2 = [
            (col1, f"👑 {local}" if pick_top == f"Gana {local}" else f"Gana {local}", mercados["local"]),
            (col2, "👑 Empate" if pick_top == "Empate" else "Empate", mercados["empate"]),
            (col3, f"👑 {visitante}" if pick_top == f"Gana {visitante}" else f"Gana {visitante}", mercados["visitante"]),
        ]
        for col, label, prob in etiquetas_1x2:
            with col:
                st.metric(label, f"{prob*100:.1f}%")
                st.progress(min(prob, 1.0))

        st.divider()

        # 4. TOP 3 MARCADORES Y MERCADOS DE GOLES
        col_izq, col_der = st.columns([5, 6])

        with col_izq:
            st.markdown("**🎯 Top 3 Marcadores Exactos (Dixon-Coles)**")
            cols_top = st.columns(3)
            medallas = ["🥇 1er", "🥈 2do", "🥉 3er"]
            for idx, ((gl, gv), prob) in enumerate(r["top3"]):
                with cols_top[idx]:
                    st.metric(medallas[idx], f"{gl} - {gv}", delta=f"{prob*100:.1f}%", delta_color="off")

            st.write("")
            st.markdown("**🚩 Mercado de Tiros de Esquina (Poisson + Dominio)**")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.metric(f"🚩 {local}", f"{r['xc_l']}")
            with cc2:
                st.metric("🔥 TOTAL", f"{r['total_corners']}")
            with cc3:
                st.metric(f"🚩 {visitante}", f"{r['xc_v']}")

            if r["prob_over_c"] >= r["prob_under_c"]:
                pick_corners = f"🔥 OVER {LINEA_CORNERS} CÓRNERS ({r['prob_over_c']*100:.1f}% prob.)"
                color_pick = "#00ff9d"
            else:
                pick_corners = f"🧊 UNDER {LINEA_CORNERS} CÓRNERS ({r['prob_under_c']*100:.1f}% prob.)"
                color_pick = "#00c3ff"

            st.markdown(
                f"""
                <div style="text-align:center; padding:8px; margin-top:6px; 
                    border:1px dashed {color_pick}; color:{color_pick}; 
                    border-radius:8px; font-weight:800; font-size:0.9rem; letter-spacing:1px;">
                    🎯 {pick_corners}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_der:
            st.markdown("**📈 Mercado de Goles y Porterías**")
            goles_totales = xg_l + xg_v
            g1, g2, g3 = st.columns(3)
            with g1:
                st.metric("⚽ Goles Esp.", f"{goles_totales:.2f}")
            with g2:
                st.metric("🤝 Ambos Anotan", f"{mercados['btts']*100:.1f}%")
            with g3:
                st.metric("🔥 Over 2.5", f"{mercados['over25']*100:.1f}%")

            st.write("")
            g4, g5, g6 = st.columns(3)
            with g4:
                st.metric("🧊 Under 3.5", f"{mercados['under35']*100:.1f}%")
            with g5:
                st.metric(f"🛡️ Cero {local}", f"{mercados['clean_sheet_local']*100:.1f}%")
            with g6:
                st.metric(f"🛡️ Cero {visitante}", f"{mercados['clean_sheet_visitante']*100:.1f}%")

        # 5. EXPANDERS PARA MATRIZ DE CALOR Y STATS BASE
        with st.expander("📊 Ver Matriz de Calor (Plotly) y Desglose de Plantillas"):
            m_col1, m_col2 = st.columns([6, 4])
            with m_col1:
                fig = crear_heatmap_plotly(r["matriz"], local, visitante)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"plotly_{idx_partido}")
            with m_col2:
                st.markdown("**📋 Comparativa de Métricas Base**")
                st.write("")
                st.metric(f"Forma {local} vs {visitante}", f"{r['forma_l']*100:.0f}% vs {r['forma_v']*100:.0f}%")
                st.metric(f"Jerarquía {local} vs {visitante}", f"{r['jerarquia_l']:.0f}/10 vs {r['jerarquia_v']:.0f}/10")
                st.metric(f"xGA en Contra ({local} / {visitante})", f"{r['xga_l']:.2f} / {r['xga_v']:.2f}")


# ==============================================================
# 5. INTERFAZ PRINCIPAL: PANEL MAESTRO DE JORNADA
# ==============================================================
st.markdown("<h2 class='main-title'>LIGA MX - ESCÁNER DE JORNADA</h2>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Motor Poisson + Corrección Dixon-Coles · Inteligencia Cuantitativa</p>", unsafe_allow_html=True)

with st.expander("⚙️ CONFIGURAR LOS 9 CRUCES DE LA JORNADA", expanded=True):
    with st.form("form_jornada"):
        partidos_jornada = []
        for i in range(1, NUM_PARTIDOS + 1):
            c1, c2, c3 = st.columns([4, 1, 4])
            with c1:
                local = st.selectbox(
                    f"Local {i}",
                    df_equipos.index,
                    index=min((i - 1) * 2, len(df_equipos.index) - 1),
                    key=f"loc_{i}",
                    label_visibility="collapsed",
                    format_func=lambda x: f"{EMOJIS_LIGA.get(x, '⚽')} {x} (Local)"
                )
            with c2:
                st.markdown("<div style='text-align: center; font-weight: 900; color: #ffd700; padding-top: 6px;'>VS</div>", unsafe_allow_html=True)
            with c3:
                visitante = st.selectbox(
                    f"Visitante {i}",
                    df_equipos.index,
                    index=min((i - 1) * 2 + 1, len(df_equipos.index) - 1),
                    key=f"vis_{i}",
                    label_visibility="collapsed",
                    format_func=lambda x: f"{EMOJIS_LIGA.get(x, '⚽')} {x} (Visita)"
                )

            partidos_jornada.append({"local": local, "visitante": visitante})
            if i < NUM_PARTIDOS:
                st.markdown("<hr style='margin: 0.4em 0px; border-color: #1f2a36;'>", unsafe_allow_html=True)

        st.write("")
        escanear = st.form_submit_button("🔥 ESCANEAR JORNADA COMPLETA 🔥", use_container_width=True, type="primary")

st.write("")

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
    st.success("✅ ¡Simulación cuantitativa completada con ajuste Dixon-Coles para los 9 partidos!")

resultados_guardados = st.session_state.get("resultados_jornada")
if resultados_guardados:
    for idx_partido, r in enumerate(resultados_guardados):
        if r["error"]:
            st.error(f"⚠️ Error en el Partido {idx_partido + 1}: {r['local']} no puede jugar contra sí mismo.")
        else:
            render_resultado(r, idx_partido)
else:
    st.info("👆 Configura los 9 cruces arriba y presiona **ESCANEAR JORNADA COMPLETA** para correr el modelo.")
