#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 MÓDULO 1: sync_espn_ligamx.py
 Conector en tiempo real con el endpoint público de ESPN para
 Liga MX (mex.1), normalizador de nombres hacia el CSV/DataFrame
 y generador de escudos oficiales en alta definición (CDN ESPN).
==============================================================
"""

import unicodedata
from datetime import datetime, timezone, timedelta
import requests

# Endpoint público oficial de ESPN Scoreboard para Liga MX
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"

# Mapeo oficial de IDs de ESPN para la Liga MX (PNG 500x500 en alta definición)
ESPN_LIGA_MX_IDS = {
    "América": "227",
    "Atlas": "216,
    "Atlético de San Luis": "15720",
    "Cruz Azul": "218",
    "FC Juárez": "17851",
    "Guadalajara": "219",
    "León": "228",
    "Mazatlán FC": "20448",
    "Monterrey": "220",
    "Necaxa": "229",
    "Pachuca": "234",
    "Puebla": "231",
    "Pumas UNAM": "233",
    "Querétaro": "222",
    "Santos Laguna": "225",
    "Tigres UANL": "232",
    "Toluca": "223",
    "Tijuana": "10125",
    "Atlante": "226",
}

# Diccionario exhaustivo de variantes de ESPN / CSV -> Nombre Canónico Estándar
MAPEO_NOMBRES_ESPN = {
    # América
    "america": "América",
    "club america": "América",
    "cf america": "América",
    "aguilas": "América",
    "ame": "América",
    # Atlas
    "atlas": "Atlas",
    "atlas fc": "Atlas",
    "futbol club atlas": "Atlas",
    # Atlético de San Luis
    "atletico de san luis": "Atlético de San Luis",
    "atletico san luis": "Atlético de San Luis",
    "san luis": "Atlético de San Luis",
    "asl": "Atlético de San Luis",
    # Cruz Azul
    "cruz azul": "Cruz Azul",
    "cd cruz azul": "Cruz Azul",
    "club de futbol cruz azul": "Cruz Azul",
    "caz": "Cruz Azul",
    # FC Juárez
    "fc juarez": "FC Juárez",
    "juarez": "FC Juárez",
    "bravos": "FC Juárez",
    "jua": "FC Juárez",
    # Guadalajara
    "guadalajara": "Guadalajara",
    "chivas": "Guadalajara",
    "guadalajara (chivas)": "Guadalajara",
    "cd guadalajara": "Guadalajara",
    "chivas guadalajara": "Guadalajara",
    "gdl": "Guadalajara",
    # León
    "leon": "León",
    "club leon": "León",
    "leo": "León",
    # Mazatlán FC
    "mazatlan fc": "Mazatlán FC",
    "mazatlan": "Mazatlán FC",
    "maz": "Mazatlán FC",
    # Monterrey
    "monterrey": "Monterrey",
    "cf monterrey": "Monterrey",
    "rayados": "Monterrey",
    "mty": "Monterrey",
    # Necaxa
    "necaxa": "Necaxa",
    "club necaxa": "Necaxa",
    "rayos": "Necaxa",
    "nec": "Necaxa",
    # Pachuca
    "pachuca": "Pachuca",
    "cf pachuca": "Pachuca",
    "tuzos": "Pachuca",
    "pac": "Pachuca",
    # Puebla
    "puebla": "Puebla",
    "club puebla": "Puebla",
    "pue": "Puebla",
    # Pumas UNAM
    "pumas unam": "Pumas UNAM",
    "pumas": "Pumas UNAM",
    "unam": "Pumas UNAM",
    "club universidad nacional": "Pumas UNAM",
    "pum": "Pumas UNAM",
    # Querétaro
    "queretaro": "Querétaro",
    "queretaro fc": "Querétaro",
    "gallos blancos": "Querétaro",
    "qro": "Querétaro",
    # Santos Laguna
    "santos laguna": "Santos Laguna",
    "santos": "Santos Laguna",
    "club santos laguna": "Santos Laguna",
    "san": "Santos Laguna",
    # Tigres UANL
    "tigres uanl": "Tigres UANL",
    "tigres": "Tigres UANL",
    "uanl": "Tigres UANL",
    "tig": "Tigres UANL",
    # Toluca
    "toluca": "Toluca",
    "deportivo toluca": "Toluca",
    "club toluca": "Toluca",
    "tol": "Toluca",
    # Tijuana
    "tijuana": "Tijuana",
    "club tijuana": "Tijuana",
    "xolos": "Tijuana",
    "tijuana (xolos)": "Tijuana",
    "xoloitzcuintles": "Tijuana",
    "tij": "Tijuana",
    # Atlante
    "atlante": "Atlante",
    "atlante fc": "Atlante",
}

EMOJIS_LIGA_MX = {
    "América": "🦅",
    "Guadalajara": "🐐",
    "Guadalajara (Chivas)": "🐐",
    "Cruz Azul": "🚂",
    "Pumas": "🐾",
    "Pumas UNAM": "🐾",
    "Tigres": "🐯",
    "Tigres UANL": "🐯",
    "Monterrey": "⛰️",
    "Toluca": "👿",
    "Pachuca": "🐹",
    "León": "🦁",
    "Santos": "😇",
    "Santos Laguna": "😇",
    "Atlas": "🦊",
    "Necaxa": "⚡",
    "Tijuana": "🐕",
    "Tijuana (Xolos)": "🐕",
    "Puebla": "🎽",
    "Juárez": "🐎",
    "FC Juárez": "🐎",
    "Mazatlán": "⚓",
    "Mazatlán FC": "⚓",
    "Querétaro": "🐓",
    "San Luis": "⛪",
    "Atlético de San Luis": "⛪",
    "Atlante": "🦈",
}

# Cartelera de respaldo en caso de que la API de ESPN esté en receso o sin conexión
CARTELERA_RESPALDO_LIGAMX = [
    {"id_partido": "LMX-001", "nombre": "Guadalajara at América", "away": "Guadalajara", "home": "América", "hora": "SÁB · 21:10 HRS", "estado": "Programado"},
    {"id_partido": "LMX-002", "nombre": "Tigres UANL at Monterrey", "away": "Tigres UANL", "home": "Monterrey", "hora": "SÁB · 19:05 HRS", "estado": "Programado"},
    {"id_partido": "LMX-003", "nombre": "Pumas UNAM at Cruz Azul", "away": "Pumas UNAM", "home": "Cruz Azul", "hora": "SÁB · 17:00 HRS", "estado": "Programado"},
    {"id_partido": "LMX-004", "nombre": "Pachuca at Toluca", "away": "Pachuca", "home": "Toluca", "hora": "DOM · 12:00 HRS", "estado": "Programado"},
    {"id_partido": "LMX-005", "nombre": "Atlas at León", "away": "Atlas", "home": "León", "hora": "VIE · 19:00 HRS", "estado": "Programado"},
    {"id_partido": "LMX-006", "nombre": "Santos Laguna at Necaxa", "away": "Santos Laguna", "home": "Necaxa", "hora": "VIE · 21:05 HRS", "estado": "Programado"},
    {"id_partido": "LMX-007", "nombre": "Querétaro at Atlético de San Luis", "away": "Querétaro", "home": "Atlético de San Luis", "hora": "DOM · 18:00 HRS", "estado": "Programado"},
    {"id_partido": "LMX-008", "nombre": "Puebla at Tijuana", "away": "Puebla", "home": "Tijuana", "hora": "DOM · 20:05 HRS", "estado": "Programado"},
    {"id_partido": "LMX-009", "nombre": "Mazatlán FC at FC Juárez", "away": "Mazatlán FC", "home": "FC Juárez", "hora": "SÁB · 19:00 HRS", "estado": "Programado"},
]


def _limpiar_texto(texto):
    """Elimina tildes/diacríticos y normaliza a minúsculas."""
    texto = str(texto or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def resolver_nombre_canonico(nombre):
    """
    Convierte cualquier variante de nombre de club (ESPN o CSV) al nombre
    canónico estándar de ESPN_LIGA_MX_IDS.
    """
    nombre_limpio = str(nombre or "").strip()
    mapeo_directo = {
        "Chivas": "Guadalajara",
        "Guadalajara (Chivas)": "Guadalajara",
        "San Luis": "Atlético de San Luis",
        "Atlético San Luis": "Atlético de San Luis",
        "Pumas": "Pumas UNAM",
        "Xolos": "Tijuana",
        "Tijuana (Xolos)": "Tijuana",
        "Juárez": "FC Juárez",
        "Tigres": "Tigres UANL",
        "Mazatlán": "Mazatlán FC",
        "Santos": "Santos Laguna",
    }
    if nombre_limpio in mapeo_directo:
        return mapeo_directo[nombre_limpio]
    if nombre_limpio in ESPN_LIGA_MX_IDS:
        return nombre_limpio

    clave_norm = _limpiar_texto(nombre_limpio)
    if clave_norm in MAPEO_NOMBRES_ESPN:
        return MAPEO_NOMBRES_ESPN[clave_norm]

    # Coincidencia parcial por subcadena
    for k_alias, v_canon in MAPEO_NOMBRES_ESPN.items():
        if len(k_alias) >= 4 and (k_alias in clave_norm or clave_norm in k_alias):
            return v_canon

    return nombre_limpio


def normalizar_equipo_para_df(nombre_espn, equipos_df=None):
    """
    Garantiza que el nombre extraído de ESPN coincida exactamente con la
    etiqueta presente en la columna/índice 'Equipo' del CSV del usuario.
    """
    canon = resolver_nombre_canonico(nombre_espn)
    if equipos_df is None or len(equipos_df) == 0:
        return canon

    lista_equipos = [str(x).strip() for x in equipos_df]
    if canon in lista_equipos:
        return canon

    # Si el CSV usa nombres cortos (ej. 'San Luis', 'Pumas', 'Tigres', 'Juárez', 'Santos')
    canon_norm = _limpiar_texto(canon)
    for eq_csv in lista_equipos:
        if resolver_nombre_canonico(eq_csv) == canon or _limpiar_texto(eq_csv) == canon_norm:
            return eq_csv

    return canon


def escudo_ligamx_html(equipo_nombre, size=32):
    """
    Retorna el tag <img> con el CDN oficial de escudos de ESPN en PNG (500x500)
    libre de bloqueos CORS/403.
    """
    nombre = resolver_nombre_canonico(equipo_nombre)
    id_espn = ESPN_LIGA_MX_IDS.get(nombre)
    if id_espn:
        url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{id_espn}.png"
    else:
        url = "https://a.espncdn.com/i/teamlogos/soccer/500/default-team-logo.png"

    return (
        f'<img src="{url}" width="{size}" height="{size}" '
        f'alt="{nombre}" '
        f'style="object-fit: contain; vertical-align: middle; margin-right: 8px;">'
    )


def _formatear_fecha_hora_espn(iso_date_str, status_detail=""):
    """Convierte el timestamp ISO-8601 de ESPN a horario local de México (UTC-6)."""
    if not iso_date_str:
        return status_detail or "HORARIO POR DEFINIR"
    try:
        dt_utc = datetime.fromisoformat(iso_date_str.replace("Z", "+00:00"))
        tz_mx = timezone(timedelta(hours=-6))
        dt_mx = dt_utc.astimezone(tz_mx)
        dias = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
        dia_str = dias[dt_mx.weekday()]
        return f"{dia_str} {dt_mx.strftime('%d/%m · %H:%M')} HRS"
    except Exception:
        return status_detail or "JORNADA LIGA MX"


def _traducir_estado_espn(state_code, description, short_detail=""):
    """Traduce el estado del partido de ESPN a una etiqueta clara en español."""
    state_code = str(state_code or "").lower()
    desc_low = str(description or "").lower()
    if state_code == "in" or "progress" in desc_low or "half" in desc_low:
        return f"🔴 EN VIVO · {short_detail}" if short_detail else "🔴 EN VIVO"
    if state_code == "post" or "final" in desc_low or "full time" in desc_low:
        return "Finalizado"
    return "Programado"


def obtener_calendario_ligamx(equipos_df=None, timeout=8):
    """
    Consulta el endpoint público de ESPN Scoreboard para Liga MX:
    'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard'

    Retorna una lista de diccionarios con la estructura:
    [
        {
            'id_partido': str,
            'nombre': str,
            'away': str,
            'home': str,
            'hora': str,
            'estado': str
        },
        ...
    ]
    Si no hay conexión o la liga está en receso sin eventos activos, devuelve
    la cartelera de respaldo normalizada hacia los nombres del CSV/DataFrame.
    """
    partidos = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TerminalSharp/5.2"
        }
        resp = requests.get(ESPN_SCOREBOARD_URL, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        eventos = data.get("events", [])
        for ev in eventos:
            id_partido = str(ev.get("id", ""))
            competitions = ev.get("competitions", [])
            if not competitions:
                continue

            comp = competitions[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            home_raw = None
            away_raw = None
            for c in competitors:
                team_obj = c.get("team", {})
                raw_name = (
                    team_obj.get("displayName")
                    or team_obj.get("shortDisplayName")
                    or team_obj.get("name")
                    or ""
                )
                if c.get("homeAway") == "home":
                    home_raw = raw_name
                elif c.get("homeAway") == "away":
                    away_raw = raw_name

            if not home_raw or not away_raw:
                home_raw = competitors[0].get("team", {}).get("displayName", "Local")
                away_raw = competitors[1].get("team", {}).get("displayName", "Visita")

            home_norm = normalizar_equipo_para_df(home_raw, equipos_df=equipos_df)
            away_norm = normalizar_equipo_para_df(away_raw, equipos_df=equipos_df)

            status_obj = comp.get("status", {}) or ev.get("status", {})
            status_type = status_obj.get("type", {})
            state_code = status_type.get("state", "pre")
            description = status_type.get("description", "Scheduled")
            short_detail = status_type.get("shortDetail", "")

            hora_fmt = _formatear_fecha_hora_espn(
                comp.get("date") or ev.get("date", ""),
                status_detail=short_detail,
            )
            estado_fmt = _traducir_estado_espn(state_code, description, short_detail)

            partidos.append({
                "id_partido": id_partido or f"{away_norm}_{home_norm}",
                "nombre": f"{away_norm} vs {home_norm}",
                "away": away_norm,
                "home": home_norm,
                "hora": hora_fmt,
                "estado": estado_fmt,
            })

    except Exception:
        partidos = []

    # Si ESPN devuelve lista vacía (ej. fecha FIFA / receso o modo offline), usamos respaldo normalizado
    if not partidos:
        for item in CARTELERA_RESPALDO_LIGAMX:
            h_norm = normalizar_equipo_para_df(item["home"], equipos_df=equipos_df)
            a_norm = normalizar_equipo_para_df(item["away"], equipos_df=equipos_df)
            partidos.append({
                "id_partido": item["id_partido"],
                "nombre": f"{a_norm} vs {h_norm}",
                "away": a_norm,
                "home": h_norm,
                "hora": item["hora"],
                "estado": item["estado"],
            })

    return partidos
