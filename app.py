#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 TERMINAL SHARP: LIGA MX
 Dashboard web de predicción cuantitativa basado en Poisson.
 Datos leídos 100% desde ligamx_stats_completo.csv (pandas).
 Incluye Matriz de Calor Interactiva (Plotly).
==============================================================
"""

import html
import math
import unicodedata
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CSV_PATH = "ligamx_stats_completo.csv"
HOME_ADVANTAGE = 1.20      # Ventaja de localía (+20% al xG del local)
MAX_GOLES_CALCULO = 10     # Rango de la matriz para mercados (precisión)
MAX_GOLES_DISPLAY = 5      # Rango a mostrar en "marcadores exactos" (0-0 a 5-5)
MATRIZ_MAX_GOLES = 6       # Rango exacto de la matriz visual (0 a 6 goles)
ESCUDO_ANCHO_PX = 110       # Ancho uniforme de los escudos
ESCUDO_CARD_PX = 80          # Ancho de los escudos en el encabezado de cada partido
LINEA_CORNERS = 9.5         # Línea de casino para el mercado de córners


# ==============================================================
# 0. DICCIONARIO DE ESCUDOS
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
}

def _normalizar(texto):
    """minúsculas + sin acentos + sin espacios extra, para que el match de
    escudos no dependa de que el CSV tenga los acentos/mayúsculas exactos."""
    texto = texto.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


# Índice normalizado -> nombre de archivo, construido una sola vez a partir
# de ESCUDOS_EQUIPOS (la fuente de verdad sigue siendo ese diccionario).
_ESCUDOS_NORMALIZADOS = {_normalizar(k): v for k, v in ESCUDOS_EQUIPOS.items()}
_FALLBACK_NORMALIZADO = {_normalizar(k): v for k, v in FALLBACK_BADGE.items()}


def escudo_url(equipo):
    archivo = _ESCUDOS_NORMALIZADOS.get(_normalizar(equipo))
    if not archivo:
        return None
    return f"{WIKI_COMMONS_BASE}{quote(archivo)}?width={ESCUDO_ANCHO_PX * 2}"

def render_escudo(equipo, nombre_display, ancho=ESCUDO_ANCHO_PX):
    url = escudo_url(equipo)
    if url:
        st.image(url, width=ancho)
    else:
        iniciales, color_fondo, color_texto = _FALLBACK_NORMALIZADO.get(
            _normalizar(equipo), (nombre_display[:3].upper(), "#333333", "#ffffff")
        )
        iniciales = html.escape(iniciales)
        st.markdown(
            f"""
            <div style="
                width:{ancho}px; height:{ancho}px; margin:0 auto;
                border-radius:50%; background:{color_fondo}; color:{color_texto};
                display:flex; align-items:center; justify-content:center;
                font-family:'Courier New', monospace; font-weight:800; font-size:{max(0.9, ancho / 85):.2f}rem;
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
    page_title=" Liga MX-Predictor Avanzado",
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
        /* 👇 Estas 3 líneas son las que crean la magia del degradado dorado 👇 */
        background: linear-gradient(90deg, #bf953f, #fcf6ba, #b38728, #fbf5b7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        /* 👆 -------------------------------------------------------------- 👆 */
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #7d8b99;
        font-family: 'Arial', sans-serif;
        font-size: 0.95rem;
        margin-top: 0;
        margin-bottom: 2.5rem;
        text-transform: uppercase;
        letter-spacing: 3px;
    }
    .vs-badge {
        text-align: center;
        font-family: 'Arial', sans-serif;
        font-size: 2.2rem;
        font-weight: 900;
        color: #ffd700;
        padding-top: 1.8rem;
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
        background: linear-gradient(90deg, rgba(255,215,0,0.12), rgba(255,215,0,0.02));
        border: 1px solid rgba(255,215,0,0.4);
        border-radius: 10px;
        padding: 14px 20px;
        font-family: 'Arial', sans-serif;
        color: #ffd700;
        font-size: 1.2rem;
        text-align: center;
        margin: 1.5rem 0;
    }
    div.stButton > button {
       font-family: 'Arial', sans-serif;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        border-radius: 8px;
        border: 1px solid #00ff9d;
    }
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================
# 2. CARGA DE DATOS
# ==============================================================
@st.cache_data
def cargar_datos(path):
    df = pd.read_csv(path)
    columnas_requeridas = {"Equipo", "xG_favor", "xGA_contra", "Forma", "Jerarquia",
                            "Corners_Favor", "Corners_Contra"}
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
# 3. MOTOR MATEMÁTICO (Poisson)
# ==============================================================
def poisson_pmf(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def calcular_xg_esperado(row_local, row_visit, liga_gf_avg, liga_ga_avg):
    ataque_local = row_local["xG_favor"] / liga_gf_avg
    defensa_visit = row_visit["xGA_contra"] / liga_ga_avg
    ataque_visit = row_visit["xG_favor"] / liga_gf_avg
    defensa_local = row_local["xGA_contra"] / liga_ga_avg

    forma_local = 0.85 + (row_local["Forma"] * 0.30)
    forma_visit = 0.85 + (row_visit["Forma"] * 0.30)
    diff_jerarquia = (row_local["Jerarquia"] - row_visit["Jerarquia"]) * 0.02

    xg_local = (liga_gf_avg * ataque_local * defensa_visit * HOME_ADVANTAGE
                * forma_local * (1 + diff_jerarquia))
    xg_visit = (liga_gf_avg * ataque_visit * defensa_local
                * forma_visit * (1 - diff_jerarquia))

    return round(xg_local, 3), round(xg_visit, 3)

def generar_matriz_poisson(xg_local, xg_visit, max_goles=MAX_GOLES_CALCULO):
    matriz = {}
    for gl in range(max_goles + 1):
        p_l = poisson_pmf(gl, xg_local)
        for gv in range(max_goles + 1):
            p_v = poisson_pmf(gv, xg_visit)
            matriz[(gl, gv)] = p_l * p_v
    return matriz

def calcular_mercados(matriz):
    p_local = p_empate = p_visit = 0.0
    p_btts = p_over25 = 0.0
    p_under35 = 0.0  # <--- NUEVA VARIABLE
    p_clean_local = p_clean_visit = 0.0

    for (gl, gv), p in matriz.items():
        if gl > gv: p_local += p
        elif gl == gv: p_empate += p
        else: p_visit += p

        if gl >= 1 and gv >= 1: p_btts += p
        if (gl + gv) >= 3: p_over25 += p
        if (gl + gv) <= 3: p_under35 += p  # <--- NUEVO CÁLCULO (0, 1, 2 o 3 goles totales)
        if gv == 0: p_clean_local += p
        if gl == 0: p_clean_visit += p

    return {
        "local": p_local, "empate": p_empate, "visitante": p_visit,
        "btts": p_btts, "over25": p_over25,
        "under35": p_under35, # <--- LO AGREGAMOS AL RESULTADO
        "clean_sheet_local": p_clean_local, "clean_sheet_visitante": p_clean_visit,
    }

def top_marcadores(matriz, top_n=3, max_goles=MAX_GOLES_DISPLAY):
    filtrados = {k: v for k, v in matriz.items() if k[0] <= max_goles and k[1] <= max_goles}
    return sorted(filtrados.items(), key=lambda x: x[1], reverse=True)[:top_n]

def calcular_xcorners(row_local, row_visit):
    """Calcula los tiros de esquina esperados cruzando el ataque y defensa de ambos."""
    corners_local = (row_local["Corners_Favor"] + row_visit["Corners_Contra"]) / 2
    corners_visit = (row_visit["Corners_Favor"] + row_local["Corners_Contra"]) / 2
    
    # Sumamos ambos para obtener el total del partido (Línea asiática típica)
    total_corners = corners_local + corners_visit
    return round(corners_local, 2), round(corners_visit, 2), round(total_corners, 2)

# --- SECCIÓN 4: PANEL MAESTRO DE JORNADA ---
NUM_PARTIDOS = 9


def analizar_partido(eq_local, eq_visitante, liga_gf_avg, liga_ga_avg):
    """Devuelve solo datos simples (dict/listas/tuplas) para guardarlos en session_state."""
    row_local = df_equipos.loc[eq_local]
    row_visit = df_equipos.loc[eq_visitante]

    xg_l, xg_v = calcular_xg_esperado(row_local, row_visit, liga_gf_avg, liga_ga_avg)
    matriz = generar_matriz_poisson(xg_l, xg_v)
    xc_l, xc_v, xc_total = calcular_xcorners(row_local, row_visit)

    # Submatriz 0..MATRIZ_MAX_GOLES para el mapa de calor (listas simples, no dict con tuplas)
    n = MATRIZ_MAX_GOLES
    matriz_visual = [[matriz[(gl, gv)] for gv in range(n + 1)] for gl in range(n + 1)]

    return {
        "local": eq_local,
        "visitante": eq_visitante,
        "error": False,
        "mercados": calcular_mercados(matriz),
        "top3": top_marcadores(matriz, top_n=3),
        "xc_local": xc_l,
        "xc_visitante": xc_v,
        "xc_total": xc_total,
        "matriz_visual": matriz_visual,
        "cobertura_matriz": sum(sum(fila) for fila in matriz_visual),
    }


def recomendacion_corners(total, linea=LINEA_CORNERS):
    """Compara el total proyectado contra la línea. Devuelve (texto, diferencia)."""
    dif = total - linea
    if dif > 0:
        return f"OVER {linea}", dif
    if dif < 0:
        return f"UNDER {linea}", dif
    return "SIN VENTAJA (empata la línea)", dif


def construir_matriz_plotly(r):
    """Mapa de calor: filas = goles del local, columnas = goles del visitante."""
    etiquetas = list(range(MATRIZ_MAX_GOLES + 1))
    z = [[p * 100 for p in fila] for fila in r["matriz_visual"]]

    fig = go.Figure(go.Heatmap(
        z=z, x=etiquetas, y=etiquetas,
        colorscale=[[0.0, "#0b1118"], [0.5, "#0d5c4a"], [1.0, "#00ff9d"]],
        showscale=False,
        xgap=2, ygap=2,
        texttemplate="%{z:.1f}%",
        textfont=dict(family="Arial", size=12),
        hovertemplate=(f"{r['local']} %{{y}} - %{{x}} {r['visitante']}"
                       "<br>Probabilidad: %{z:.2f}%<extra></extra>"),
    ))
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color="#b8c4cf"),
        xaxis=dict(title=f"Goles {r['visitante']} (visitante)", dtick=1),
        yaxis=dict(title=f"Goles {r['local']} (local)", dtick=1, autorange="reversed"),
    )
    return fig


def render_resultado(r, idx):
    mercados = r["mercados"]
    with st.container(border=True):
        # --- Encabezado: escudo local | nombres | escudo visitante ---
        c_esc_l, c_centro, c_esc_v = st.columns([1, 3, 1], vertical_alignment="center")
        with c_esc_l:
            render_escudo(r["local"], r["local"], ancho=ESCUDO_CARD_PX)
        with c_centro:
            st.markdown(
                f"<h3 style='text-align:center; margin:0;'>🏟️ {html.escape(r['local'])} "
                f"<span style='color:#ffd700;'>vs</span> {html.escape(r['visitante'])}</h3>",
                unsafe_allow_html=True,
            )
        with c_esc_v:
            render_escudo(r["visitante"], r["visitante"], ancho=ESCUDO_CARD_PX)

        # --- 1X2 ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Gana {r['local']}", f"{mercados['local']*100:.1f}%")
        with col2:
            st.metric("Empate", f"{mercados['empate']*100:.1f}%")
        with col3:
            st.metric(f"Gana {r['visitante']}", f"{mercados['visitante']*100:.1f}%")

        st.divider()

        # --- Top 3 marcadores exactos ---
        st.markdown("**🎯 Top 3 Marcadores Exactos**")
        columnas = st.columns(3)
        medallas = ["🥇 1er", "🥈 2do", "🥉 3er"]
        for i, ((gl, gv), prob) in enumerate(r["top3"]):
            with columnas[i]:
                st.metric(medallas[i], f"{gl} - {gv}", delta=f"{prob*100:.1f}% prob.", delta_color="off")

        st.divider()

        # --- Mercados de goles ---
        st.markdown("**⚽ Mercados de Goles**")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.metric("Over 2.5", f"{mercados['over25']*100:.1f}%")
        with g2:
            st.metric("Under 3.5", f"{mercados['under35']*100:.1f}%")
        with g3:
            st.metric("Ambos Anotan (BTTS)", f"{mercados['btts']*100:.1f}%")

        st.divider()

        # --- Mercado de córners ---
        st.markdown("**🚩 Mercado de Córners (xCorners)**")
        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric(f"xC {r['local']}", f"{r['xc_local']:.2f}")
        with k2:
            st.metric(f"xC {r['visitante']}", f"{r['xc_visitante']:.2f}")
        with k3:
            st.metric("Total proyectado", f"{r['xc_total']:.2f}")

        pick, dif = recomendacion_corners(r["xc_total"])
        st.markdown(
            f"<div class='pick-banner' style='margin:0.8rem 0 0.4rem 0;'>"
            f"🚩 Línea {LINEA_CORNERS} · Proyección {r['xc_total']:.2f} "
            f"({dif:+.2f}) → <b>{pick}</b></div>",
            unsafe_allow_html=True,
        )

        # --- Matriz de probabilidad (colapsable) ---
        with st.expander("📊 Ver Matriz de Probabilidad Exacta"):
            st.plotly_chart(construir_matriz_plotly(r), theme=None, key=f"matriz_{idx}")
            st.caption(
                f"Cubre marcadores de 0 a {MATRIZ_MAX_GOLES} goles por equipo "
                f"({r['cobertura_matriz']*100:.1f}% de la probabilidad total)."
            )


st.markdown("<h2 class='main-title'>LIGA MX - ESCÁNER DE JORNADA</h2>", unsafe_allow_html=True)
st.write("")

with st.expander("⚙️ CONFIGURAR LOS 9 CRUCES", expanded=True):
    # El form agrupa los 18 selectores: no se re-ejecuta el script hasta pulsar el botón.
    with st.form("form_jornada"):
        partidos_jornada = []
        for i in range(1, NUM_PARTIDOS + 1):
            c1, c2, c3 = st.columns([4, 1, 4])
            with c1:
                local = st.selectbox(f"Local {i}", df_equipos.index, key=f"loc_{i}", label_visibility="collapsed")
            with c2:
                st.markdown("<div style='text-align: center; font-weight: bold;'>VS</div>", unsafe_allow_html=True)
            with c3:
                visitante = st.selectbox(
                    f"Visitante {i}", df_equipos.index,
                    index=min(i, len(df_equipos.index) - 1),
                    key=f"vis_{i}", label_visibility="collapsed",
                )

            partidos_jornada.append({"local": local, "visitante": visitante})
            if i < NUM_PARTIDOS:
                st.markdown("<hr style='margin: 0.5em 0px; border-color: #2b3a4a;'>", unsafe_allow_html=True)

        escanear = st.form_submit_button("🔥 ESCANEAR JORNADA COMPLETA 🔥", use_container_width=True, type="primary")

st.write("")

# Al enviar el form: calcular y GUARDAR en session_state.
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
    st.success("¡Probabilidades calculadas con distribución de Poisson para toda la jornada!")

# Render SIEMPRE desde session_state: los resultados sobreviven a cualquier re-ejecución.
resultados_guardados = st.session_state.get("resultados_jornada")
if resultados_guardados:
    for idx, r in enumerate(resultados_guardados):
        if r["error"]:
            st.error(f"⚠️ Error: {r['local']} no puede jugar contra sí mismo.")
        else:
            render_resultado(r, idx)
