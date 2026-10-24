#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 MÓDULO 2: engine_ligamx.py
 Motor Cuantitativo Liga MX:
 - Distribución de Poisson Bivariada + Corrección Dixon-Coles
 - Amortiguación de xG + Factor de Localía Dinámico por Altitud/Estadio
 - Simulación de Córners por Dominio (Game State) + Poisson PMF
 - Calculadora de Momios Justos (Fair Odds: Decimal y Americano)
 - Mercados 1X2, Over/Under 2.5 y 3.5, BTTS, DNB, Doble Oportunidad y Hándicap -1.5
==============================================================
"""

import math
import unicodedata
import pandas as pd
from sync_espn_ligamx import resolver_nombre_canonico

# ==============================================================
# PARÁMETROS GLOBALES DEL MOTOR CUANTITATIVO
# ==============================================================
HOME_ADVANTAGE_DEFAULT = 1.18  # Localía base si el equipo no está en el diccionario
DIXON_COLES_RHO = -0.13        # Correlación negativa para ajustar empates bajos (0-0, 1-1)
LINEA_CORNERS_DEFAULT = 9.5    # Línea asiática estándar para Over/Under de córners
MAX_GOLES_CALCULO = 10         # Rango de la matriz para mercados (precisión 100%)
MAX_GOLES_DISPLAY = 5          # Rango a mostrar en marcadores exactos (0-0 a 5-5)
MATRIZ_MAX_GOLES = 6           # Rango de la matriz visual Plotly (0 a 6 goles)

FACTOR_LOCALIA_EQUIPOS = {
    "Toluca": 1.26,
    "Pumas": 1.24,
    "Pumas UNAM": 1.24,
    "Pachuca": 1.24,
    "América": 1.23,
    "Cruz Azul": 1.22,
    "Tigres": 1.23,
    "Tigres UANL": 1.23,
    "Monterrey": 1.22,
    "Guadalajara": 1.19,
    "Guadalajara (Chivas)": 1.19,
    "León": 1.20,
    "Santos": 1.18,
    "Santos Laguna": 1.18,
    "Atlas": 1.16,
    "San Luis": 1.17,
    "Atlético de San Luis": 1.17,
    "Necaxa": 1.16,
    "Tijuana": 1.21,
    "Tijuana (Xolos)": 1.21,
    "Puebla": 1.16,
    "Querétaro": 1.14,
    "Juárez": 1.13,
    "FC Juárez": 1.13,
    "Mazatlán": 1.12,
    "Mazatlán FC": 1.12,
    "Atlante": 1.18,
}


def _normalizar_texto(texto):
    texto = str(texto or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


_LOCALIA_NORMALIZADA = {_normalizar_texto(k): v for k, v in FACTOR_LOCALIA_EQUIPOS.items()}


# ==============================================================
# FUNCIONES MATEMÁTICAS BASE
# ==============================================================
def poisson_pmf(k, lam):
    """Función de masa de probabilidad de Poisson P(X = k)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def formatear_momio_justo(prob):
    """
    Convierte una probabilidad (0 a 1) en su Cuota Justa (Fair Odd) sin vig
    en formato Decimal y Americano, ej: '1.85 (-118)' o '2.40 (+140)'.
    """
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
    """Obtiene el multiplicador de localía desde la fila del DataFrame o por altitud/estadio."""
    if "Localia" in row_local and pd.notna(row_local["Localia"]):
        return float(row_local["Localia"])
    canon = resolver_nombre_canonico(eq_local)
    if canon in FACTOR_LOCALIA_EQUIPOS:
        return FACTOR_LOCALIA_EQUIPOS[canon]
    return _LOCALIA_NORMALIZADA.get(_normalizar_texto(eq_local), HOME_ADVANTAGE_DEFAULT)


def _preparar_df_indexado(df_stats):
    """
    Asegura que el DataFrame esté indexado por 'Equipo' sin mutar el objeto original
    en sesión.
    """
    if "Equipo" in df_stats.columns:
        return df_stats.set_index("Equipo", drop=False)
    return df_stats


def _obtener_fila_equipo(nombre_equipo, df_idx):
    """
    Localiza la fila estadística de un club soportando coincidencia exacta,
    nombre canónico de ESPN o normalización sin acentos.
    """
    if nombre_equipo in df_idx.index:
        fila = df_idx.loc[nombre_equipo]
        return (fila.iloc[0] if isinstance(fila, pd.DataFrame) else fila), str(nombre_equipo)

    canon = resolver_nombre_canonico(nombre_equipo)
    if canon in df_idx.index:
        fila = df_idx.loc[canon]
        return (fila.iloc[0] if isinstance(fila, pd.DataFrame) else fila), canon

    norm_buscado = _normalizar_texto(nombre_equipo)
    norm_canon = _normalizar_texto(canon)

    for idx_val in df_idx.index:
        idx_norm = _normalizar_texto(idx_val)
        idx_canon_norm = _normalizar_texto(resolver_nombre_canonico(idx_val))
        if idx_norm in (norm_buscado, norm_canon) or idx_canon_norm in (norm_buscado, norm_canon):
            fila = df_idx.loc[idx_val]
            return (fila.iloc[0] if isinstance(fila, pd.DataFrame) else fila), str(idx_val)

    raise KeyError(f"El club '{nombre_equipo}' no se encontró en el DataFrame de estadísticas.")


def calcular_xg_esperado(eq_local, row_local, row_visit, liga_gf_avg, liga_ga_avg):
    """Calcula el xG proyectado amortiguado para Local y Visitante."""
    ataque_local = float(row_local["xG_favor"]) / liga_gf_avg
    defensa_visit = float(row_visit["xGA_contra"]) / liga_ga_avg
    ataque_visit = float(row_visit["xG_favor"]) / liga_gf_avg
    defensa_local = float(row_local["xGA_contra"]) / liga_ga_avg

    fuerza_base_local = (ataque_local * defensa_visit) ** 0.85
    fuerza_base_visit = (ataque_visit * defensa_local) ** 0.85

    # Normalización defensiva si Forma viene en escala 0-100 o 0-1
    f_loc_raw = float(row_local["Forma"])
    f_vis_raw = float(row_visit["Forma"])
    if f_loc_raw > 1.0:
        f_loc_raw = f_loc_raw / 100.0 if f_loc_raw > 10.0 else f_loc_raw / 10.0
    if f_vis_raw > 1.0:
        f_vis_raw = f_vis_raw / 100.0 if f_vis_raw > 10.0 else f_vis_raw / 10.0

    forma_local = 0.92 + (f_loc_raw * 0.16)
    forma_visit = 0.92 + (f_vis_raw * 0.16)

    diff_jerarquia = (float(row_local["Jerarquia"]) - float(row_visit["Jerarquia"])) * 0.01
    ventaja_local = obtener_factor_localia(eq_local, row_local)

    xg_local = (
        liga_gf_avg * fuerza_base_local * ventaja_local
        * forma_local * (1.0 + diff_jerarquia)
    )
    xg_visit = (
        liga_gf_avg * fuerza_base_visit
        * forma_visit * (1.0 - diff_jerarquia)
    )

    xg_local = max(0.25, min(xg_local, 3.80))
    xg_visit = max(0.20, min(xg_visit, 3.50))

    return round(xg_local, 3), round(xg_visit, 3), round(ventaja_local, 2)


def tau_dixon_coles(gl, gv, xg_local, xg_visit, rho=DIXON_COLES_RHO):
    """Factor de ajuste de dependencia de Dixon-Coles para marcadores bajos."""
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
    """Genera la matriz bivariada (gl, gv) normalizada al 100%."""
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
    """Agrega las probabilidades de todos los mercados principales y asiáticos."""
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
        "local": p_local,
        "empate": p_empate,
        "visitante": p_visit,
        "btts": p_btts,
        "no_btts": 1.0 - p_btts,
        "over25": p_over25,
        "under25": p_under25,
        "under35": p_under35,
        "clean_sheet_local": p_clean_local,
        "clean_sheet_visitante": p_clean_visit,
        "dnb_local": dnb_local,
        "dnb_visit": dnb_visit,
        "doble_1x": doble_1x,
        "doble_x2": doble_x2,
        "doble_12": doble_12,
        "hc_local_15": p_handicap_local_15,
        "hc_visit_15": p_handicap_visit_15,
    }


def top_marcadores(matriz, top_n=3, max_goles=MAX_GOLES_DISPLAY):
    """Retorna el Top N de marcadores exactos más probables."""
    filtrados = {k: v for k, v in matriz.items() if k[0] <= max_goles and k[1] <= max_goles}
    return sorted(filtrados.items(), key=lambda x: x[1], reverse=True)[:top_n]


def calcular_xcorners(row_local, row_visit, xg_local, xg_visit, linea=LINEA_CORNERS_DEFAULT):
    """Simula tiros de esquina esperados ajustados por Dominio (Game State) + Poisson PMF."""
    base_local = (float(row_local["Corners_Favor"]) + float(row_visit["Corners_Contra"])) / 2.0
    base_visit = (float(row_visit["Corners_Favor"]) + float(row_local["Corners_Contra"])) / 2.0

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
# FUNCIÓN PRINCIPAL DE ORQUESTACIÓN CUANTITATIVA POR PARTIDO
# ==============================================================
def calcular_probabilidades_partido(local, visita, df_stats, linea_corners=LINEA_CORNERS_DEFAULT):
    """
    Consume xG_favor, xGA_contra, Forma, Jerarquia, Corners_Favor y Corners_Contra
    desde `df_stats` y retorna todas las probabilidades, Fair Odds, Over/Under 2.5,
    mercados asiáticos, matriz de marcadores exactos y proyección de córners.
    """
    df_idx = _preparar_df_indexado(df_stats)

    if resolver_nombre_canonico(local) == resolver_nombre_canonico(visita):
        return {
            "local": str(local),
            "visitante": str(visita),
            "error": True,
            "mensaje_error": f"{local} no puede enfrentarse a sí mismo.",
        }

    try:
        row_local, nombre_local_df = _obtener_fila_equipo(local, df_idx)
        row_visit, nombre_visit_df = _obtener_fila_equipo(visita, df_idx)
    except KeyError as exc:
        return {
            "local": str(local),
            "visitante": str(visita),
            "error": True,
            "mensaje_error": str(exc),
        }

    liga_gf_avg = float(df_idx["xG_favor"].astype(float).mean())
    liga_ga_avg = float(df_idx["xGA_contra"].astype(float).mean())

    xg_l, xg_v, factor_loc = calcular_xg_esperado(
        nombre_local_df, row_local, row_visit, liga_gf_avg, liga_ga_avg
    )
    matriz = generar_matriz_poisson(xg_l, xg_v)
    mercados = calcular_mercados(matriz)
    top3 = top_marcadores(matriz, top_n=3)
    xc_l, xc_v, total_corners, prob_over_c, prob_under_c = calcular_xcorners(
        row_local, row_visit, xg_l, xg_v, linea=linea_corners
    )

    gl_proy, gv_proy = top3[0][0]
    prob_proy = top3[0][1]

    fair_odds = {
        "local": formatear_momio_justo(mercados["local"]),
        "empate": formatear_momio_justo(mercados["empate"]),
        "visitante": formatear_momio_justo(mercados["visitante"]),
        "over25": formatear_momio_justo(mercados["over25"]),
        "under25": formatear_momio_justo(mercados["under25"]),
        "under35": formatear_momio_justo(mercados["under35"]),
        "btts": formatear_momio_justo(mercados["btts"]),
        "no_btts": formatear_momio_justo(mercados["no_btts"]),
        "dnb_local": formatear_momio_justo(mercados["dnb_local"]),
        "dnb_visit": formatear_momio_justo(mercados["dnb_visit"]),
        "doble_1x": formatear_momio_justo(mercados["doble_1x"]),
        "doble_x2": formatear_momio_justo(mercados["doble_x2"]),
        "hc_local_15": formatear_momio_justo(mercados["hc_local_15"]),
        "hc_visit_15": formatear_momio_justo(mercados["hc_visit_15"]),
        "clean_sheet_local": formatear_momio_justo(mercados["clean_sheet_local"]),
        "clean_sheet_visitante": formatear_momio_justo(mercados["clean_sheet_visitante"]),
        "over_corners": formatear_momio_justo(prob_over_c),
        "under_corners": formatear_momio_justo(prob_under_c),
    }

    return {
        "local": nombre_local_df,
        "visitante": nombre_visit_df,
        "error": False,
        # Métricas xG y Localía
        "xg_l": xg_l,
        "xg_v": xg_v,
        "xg_total": round(xg_l + xg_v, 2),
        "factor_loc": factor_loc,
        # Probabilidades directas 1X2 y Goles (acceso rápido + diccionario mercados)
        "prob_local": mercados["local"],
        "prob_empate": mercados["empate"],
        "prob_visita": mercados["visitante"],
        "prob_over25": mercados["over25"],
        "prob_under25": mercados["under25"],
        "prob_btts": mercados["btts"],
        "mercados": mercados,
        "fair_odds": fair_odds,
        # Marcadores Exactos y Matriz
        "matriz": matriz,
        "top3": top3,
        "proy_gl": gl_proy,
        "proy_gv": gv_proy,
        "proy_prob": prob_proy,
        # Córners proyectados
        "linea_corners": linea_corners,
        "xc_l": xc_l,
        "xc_v": xc_v,
        "total_corners": total_corners,
        "prob_over_c": prob_over_c,
        "prob_under_c": prob_under_c,
        # Radiografía de plantillas
        "forma_l": float(row_local["Forma"]),
        "forma_v": float(row_visit["Forma"]),
        "jerarquia_l": float(row_local["Jerarquia"]),
        "jerarquia_v": float(row_visit["Jerarquia"]),
        "xga_l": float(row_local["xGA_contra"]),
        "xga_v": float(row_visit["xGA_contra"]),
        "xgf_l": float(row_local["xG_favor"]),
        "xgf_v": float(row_visit["xG_favor"]),
    }