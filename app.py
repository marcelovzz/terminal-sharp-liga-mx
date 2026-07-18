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

import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

CSV_PATH = "ligamx_stats_completo.csv"
HOME_ADVANTAGE = 1.20      # Ventaja de localía (+20% al xG del local)
MAX_GOLES_CALCULO = 10     # Rango de la matriz para mercados (precisión)
MAX_GOLES_DISPLAY = 5      # Rango a mostrar en "marcadores exactos" (0-0 a 5-5)
MATRIZ_MAX_GOLES = 6       # Rango exacto de la matriz visual (0 a 6 goles)
ESCUDO_ANCHO_PX = 110       # Ancho uniforme de los escudos


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

def escudo_url(equipo):
    archivo = ESCUDOS_EQUIPOS.get(equipo)
    if not archivo:
        return None
    from urllib.parse import quote
    return f"{WIKI_COMMONS_BASE}{quote(archivo)}?width={ESCUDO_ANCHO_PX * 2}"

def render_escudo(equipo, nombre_display):
    url = escudo_url(equipo)
    if url:
        st.image(url, width=ESCUDO_ANCHO_PX)
    else:
        iniciales, color_fondo, color_texto = FALLBACK_BADGE.get(
            equipo, (nombre_display[:3].upper(), "#333333", "#ffffff")
        )
        st.markdown(
            f"""
            <div style="
                width:{ESCUDO_ANCHO_PX}px; height:{ESCUDO_ANCHO_PX}px;
                border-radius:50%; background:{color_fondo}; color:{color_texto};
                display:flex; align-items:center; justify-content:center;
                font-family:'Courier New', monospace; font-weight:800; font-size:1.3rem;
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
    page_title="Terminal Sharp: Liga MX",
    page_icon="🎯",
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
        font-family: 'Courier New', monospace !important;
        letter-spacing: 1px;
    }
    .main-title {
        font-family: 'Courier New', monospace;
        font-size: 2.6rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(90deg, #00ff9d, #00c3ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #7d8b99;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        margin-top: 0;
        margin-bottom: 2.5rem;
        text-transform: uppercase;
        letter-spacing: 3px;
    }
    .vs-badge {
        text-align: center;
        font-family: 'Courier New', monospace;
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
        font-family: 'Courier New', monospace;
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
        font-family: 'Courier New', monospace;
        color: #ffd700;
        font-size: 1.2rem;
        text-align: center;
        margin: 1.5rem 0;
    }
    div.stButton > button {
        font-family: 'Courier New', monospace;
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
    columnas_requeridas = {"Equipo", "xG_favor", "xGA_contra", "Forma", "Jerarquia"}
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
    p_clean_local = p_clean_visit = 0.0

    for (gl, gv), p in matriz.items():
        if gl > gv: p_local += p
        elif gl == gv: p_empate += p
        else: p_visit += p

        if gl >= 1 and gv >= 1: p_btts += p
        if (gl + gv) >= 3: p_over25 += p
        if gv == 0: p_clean_local += p
        if gl == 0: p_clean_visit += p

    return {
        "local": p_local, "empate": p_empate, "visitante": p_visit,
        "btts": p_btts, "over25": p_over25,
        "clean_sheet_local": p_clean_local, "clean_sheet_visitante": p_clean_visit,
    }

def top_marcadores(matriz, top_n=3, max_goles=MAX_GOLES_DISPLAY):
    filtrados = {k: v for k, v in matriz.items() if k[0] <= max_goles and k[1] <= max_goles}
    return sorted(filtrados.items(), key=lambda x: x[1], reverse=True)[:top_n]


# ==============================================================
# 4. ENCABEZADO Y CONTROLES
# ==============================================================
st.markdown('<div class="main-title">🎯 TERMINAL SHARP: LIGA MX</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Motor Cuantitativo de Predicción · Distribución de Poisson</div>', unsafe_allow_html=True)

equipos = sorted(df_equipos.index.tolist())

col_local, col_vs, col_visit = st.columns([4, 1, 4])
with col_local:
    equipo_local = st.selectbox("🏠 Equipo Local", equipos, index=0, key="sb_local")
with col_vs:
    st.markdown('<div class="vs-badge">VS</div>', unsafe_allow_html=True)
with col_visit:
    idx_default = 1 if len(equipos) > 1 else 0
    equipo_visitante = st.selectbox("✈️ Equipo Visitante", equipos, index=idx_default, key="sb_visit")

st.write("") 
_, col_btn, _ = st.columns([3, 4, 3])
with col_btn:
    calcular = st.button("🔥 GENERAR PICK", type="primary", use_container_width=True)

if calcular:
    if equipo_local == equipo_visitante:
        st.warning("⚠ Selecciona dos equipos distintos para poder calcular una predicción.")
        st.session_state["resultado"] = None
    else:
        liga_gf_avg = df_equipos["xG_favor"].mean()
        liga_ga_avg = df_equipos["xGA_contra"].mean()

        row_local = df_equipos.loc[equipo_local]
        row_visit = df_equipos.loc[equipo_visitante]

        xg_l, xg_v = calcular_xg_esperado(row_local, row_visit, liga_gf_avg, liga_ga_avg)
        matriz = generar_matriz_poisson(xg_l, xg_v)
        mercados = calcular_mercados(matriz)
        top3 = top_marcadores(matriz)

        st.session_state["resultado"] = {
            "local": equipo_local, "visitante": equipo_visitante,
            "row_local": row_local, "row_visit": row_visit,
            "xg_l": xg_l, "xg_v": xg_v,
            "matriz": matriz, "mercados": mercados, "top3": top3,
        }


# ==============================================================
# 5. RENDERIZADO DE RESULTADOS
# ==============================================================
resultado = st.session_state.get("resultado")

if resultado:
    local = resultado["local"]
    visitante = resultado["visitante"]
    row_l = resultado["row_local"]
    row_v = resultado["row_visit"]
    xg_l = resultado["xg_l"]
    xg_v = resultado["xg_v"]
    matriz = resultado["matriz"]
    mercados = resultado["mercados"]
    top3 = resultado["top3"]

    opciones_1x2 = {"Gana " + local: mercados["local"], "Empate": mercados["empate"], "Gana " + visitante: mercados["visitante"]}
    pick_top = max(opciones_1x2, key=opciones_1x2.get)
    st.markdown(
        f'<div class="pick-banner">🏆 PICK SUGERIDO (1X2): <b>{pick_top}</b> '
        f'&nbsp;·&nbsp; {opciones_1x2[pick_top]*100:.1f}% de probabilidad</div>',
        unsafe_allow_html=True,
    )

    with st.expander("📊 Ver Inteligencia Matemática y Stats Base", expanded=False):
        col_a, col_b = st.columns(2)
        for col, nombre, row, xg_final in [(col_a, local, row_l, xg_l), (col_b, visitante, row_v, xg_v)]:
            with col:
                render_escudo(nombre, nombre)
                st.markdown(f"**{nombre}**")
                st.metric("xG Esperado (partido)", f"{xg_final:.2f}")
                st.progress(min(xg_final / 3.0, 1.0))
                st.metric("xGA Base (en contra)", f"{row['xGA_contra']:.2f}")
                st.progress(min(row["xGA_contra"] / 2.0, 1.0))
                st.metric("Forma Reciente", f"{row['Forma']*100:.0f}%")
                st.progress(min(row["Forma"], 1.0))
                st.metric("Jerarquía de Plantilla", f"{row['Jerarquia']:.0f}/10")
                st.progress(min(row["Jerarquia"] / 10, 1.0))

    st.divider()

    # Layout de dos columnas: Izquierda para Métricas, Derecha para la Matriz Interactiva
    col_izq, col_der = st.columns([5, 6])

    with col_izq:
        st.subheader("🎯 Marcador Exacto")
        medallas = ["🥇 1er Lugar", "🥈 2do Lugar", "🥉 3er Lugar"]
        cols_top = st.columns(3)
        for i, ((gl, gv), prob) in enumerate(top3):
            with cols_top[i]:
                st.metric(medallas[i], f"{gl} - {gv}", delta=f"{prob*100:.1f}% prob.", delta_color="off")

        st.divider()

        st.subheader("💰 Mercado 1X2 (Moneyline)")
        with st.container(border=True):
            col_l, col_e, col_v = st.columns(3)
            etiquetas_1x2 = [
                (col_l, f"👑 {local}" if pick_top == "Gana " + local else local, mercados["local"]),
                (col_e, "👑 Empate" if pick_top == "Empate" else "Empate", mercados["empate"]),
                (col_v, f"👑 {visitante}" if pick_top == "Gana " + visitante else visitante, mercados["visitante"]),
            ]
            for col, label, prob in etiquetas_1x2:
                with col:
                    st.metric(label, f"{prob*100:.1f}%")
                    st.progress(min(prob, 1.0))

        st.divider()

        st.subheader("📈 Mercado de Goles (Over/Under)")
        with st.container(border=True):
            goles_totales = xg_l + xg_v
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("⚽ Goles Totales", f"{goles_totales:.2f}")
            with c2: st.metric("🤝 Ambos Anotan", f"{mercados['btts']*100:.1f}%")
            with c3: st.metric("🔥 Más de 2.5", f"{mercados['over25']*100:.1f}%")
            
            st.write("")
            c4, c5 = st.columns(2)
            with c4: st.metric(f"🛡️ Valla Invicta — {local}", f"{mercados['clean_sheet_local']*100:.1f}%")
            with c5: st.metric(f"🛡️ Valla Invicta — {visitante}", f"{mercados['clean_sheet_visitante']*100:.1f}%")

    with col_der:
        st.subheader("📊 Matriz de Probabilidad por Resultado Exacto (%)")
        
        # Construcción de la matriz 0-6 para Plotly
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

        # Creación del Heatmap Premium con Plotly
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=[str(x) for x in goles_rango],
            y=[str(y) for y in goles_rango],
            text=text_data,
            texttemplate="%{text}",
            textfont=dict(family="Courier New", size=12, color="white"),
            hoverinfo="text",
            colorscale=[[0, '#0e1520'], [0.1, '#1d2a44'], [0.4, '#23607a'], [0.7, '#8b2516'], [1, '#c83219']],
            showscale=False
        ))

        fig.update_layout(
            xaxis=dict(
                title=dict(text=f"{visitante.upper()} (GOLES) →", font=dict(family="Courier New", color="#ffd700")), 
                side="top",
                tickfont=dict(family="Courier New", color="#ffd700")
            ),
            yaxis=dict(
                title=dict(text=f"← {local.upper()} (GOLES)", font=dict(family="Courier New", color="#00ff9d")), 
                autorange="reversed",
                tickfont=dict(family="Courier New", color="#00ff9d")
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=60, b=40),
            width=550,
            height=500
        )
        
        # Renderizado del mapa de calor interactivo
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("👆 Selecciona ambos equipos y presiona **GENERAR PICK** para correr el modelo.")