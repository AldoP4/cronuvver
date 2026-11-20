#!/usr/bin/env python3
"""reloj: le da a un agente de IA noción del tiempo real.

Los modelos no saben qué día es ni cuánto tiempo pasó entre un mensaje y otro.
Este script lo calcula con el reloj de la computadora.

Uso humano o desde el agente:
    python reloj.py                          # hoy, hora, semana, cierres de mes, trimestre y año
    python reloj.py --hasta 2027-01-01       # cuánto falta (días corridos y hábiles)
    python reloj.py --habiles 5              # qué fecha es dentro de 5 días hábiles
    python reloj.py --utc -3                 # con la zona horaria de otra persona
    python reloj.py --json                   # salida en JSON

Uso como hook de Claude Code (lee el evento por stdin y nunca falla):
    python reloj.py --hook

Solo biblioteca estándar de Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# A partir de este hueco entre mensajes, el aviso se vuelve explícito.
HUECO_IMPORTANTE = timedelta(minutes=30)
# Entradas del estado más viejas que esto se borran.
RETENCION = timedelta(days=60)


# ---------- fechas ----------

def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date) -> str:
    return f"{DIAS_CORTOS[d.weekday()]} {d.day} {MESES_CORTOS[d.month - 1]} {d.year}"


def fin_de_mes(d: date) -> date:
    siguiente = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return siguiente - timedelta(days=1)


def fin_de_trimestre(d: date) -> date:
    return fin_de_mes(date(d.year, ((d.month - 1) // 3 + 1) * 3, 1))


def dias_habiles_entre(desde: date, hasta: date) -> int:
    """Días de lunes a viernes después de 'desde' y hasta 'hasta' inclusive."""
    total, d = 0, desde
    while d < hasta:
        d += timedelta(days=1)
        if d.weekday() < 5:
            total += 1
    return total


def sumar_habiles(desde: date, n: int) -> date:
    d, faltan = desde, n
    while faltan > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            faltan -= 1
    return d


def describir_hueco(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    if s < 90:
        return "menos de 2 minutos"
    m = s // 60
    if m < 60:
        return f"{m} minutos"
    h = m // 60
    if h < 48:
        resto = m % 60
        return f"{h} h {resto} min" if resto and h < 6 else f"{h} horas"
    return f"{h // 24} días"


def describir_hasta(hoy: date, objetivo: date) -> dict:
    dias = (objetivo - hoy).days
    if dias > 0:
        texto = f"faltan {dias} días ({dias_habiles_entre(hoy, objetivo)} hábiles, ~{dias / 7:.1f} semanas)"
    elif dias == 0:
        texto = "es hoy"
    else:
        texto = f"ya pasó hace {-dias} días"
    return {"fecha": objetivo.isoformat(), "dia": fecha_larga(objetivo), "dias": dias, "texto": texto}


def ahora_con_zona(utc: float | None) -> datetime:
    if utc is None and os.environ.get("RELOJ_UTC"):
        try:
            utc = float(os.environ["RELOJ_UTC"])
        except ValueError:
            utc = None
    if utc is not None:
        return datetime.now(timezone(timedelta(hours=utc)))
    return datetime.now().astimezone()


def zona_texto(dt: datetime) -> str:
    z = dt.strftime("%z")
    return f"UTC{z[:3]}:{z[3:]}" if z else "UTC"


# ---------- estado (para saber cuánto tiempo pasó) ----------

def ruta_estado() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".claude", "reloj")
    return Path(base) / "estado.json"


def leer_estado(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"sesiones": {}, "proyectos": {}}


def guardar_estado(ruta: Path, estado: dict, ahora: datetime) -> None:
    limite = ahora - RETENCION
    for clave in ("sesiones", "proyectos"):
        estado[clave] = {k: v for k, v in estado.get(clave, {}).items()
                         if _parse(v) and _parse(v) > limite}
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
        tmp.replace(ruta)
    except Exception:  # noqa: BLE001
        pass


def _parse(valor: str):
    try:
        return datetime.fromisoformat(valor)
    except Exception:  # noqa: BLE001
        return None


# ---------- hook ----------

def modo_hook() -> int:
    try:
        crudo = sys.stdin.read() if not sys.stdin.isatty() else ""
        evento = json.loads(crudo) if crudo.strip() else {}
    except Exception:  # noqa: BLE001
        evento = {}
    try:
        ahora = ahora_con_zona(None)
        nombre = evento.get("hook_event_name") or "UserPromptSubmit"
        sesion = str(evento.get("session_id") or "")
        proyecto = str(evento.get("cwd") or os.getcwd())
        ruta = ruta_estado()
        estado = leer_estado(ruta)

        base = f"{fecha_corta(ahora.date())}, {ahora.strftime('%H:%M')} ({zona_texto(ahora)})"
        if nombre == "SessionStart":
            texto = (f"[reloj] Hoy es {fecha_larga(ahora.date())}, {ahora.strftime('%H:%M')} hora local "
                     f"({zona_texto(ahora)}). Calcula todo lo de 'hoy', 'reciente', 'el año pasado' y los plazos "
                     f"desde esta fecha, no desde tus datos de entrenamiento.")
            anterior = _parse(estado.get("proyectos", {}).get(proyecto, ""))
            if anterior:
                texto += f" La última actividad en este proyecto fue hace {describir_hueco(ahora - anterior)} ({fecha_corta(anterior.date())})."
        else:
            anterior = _parse(estado.get("sesiones", {}).get(sesion, "")) if sesion else None
            texto = f"[reloj] {base}"
            if anterior:
                hueco = ahora - anterior
                texto += f" · pasaron {describir_hueco(hueco)} desde el mensaje anterior"
                if hueco >= HUECO_IMPORTANTE:
                    texto += (". Ojo: lo que en esta conversación era 'hoy', 'ahorita' o 'en un rato' ya no lo es; "
                              "revisa si algo que dabas por vigente (procesos, despliegues, fechas) cambió")
                    if anterior.date() != ahora.date():
                        texto += f". El mensaje anterior fue el {fecha_corta(anterior.date())}"
            texto += "."

        if sesion:
            estado.setdefault("sesiones", {})[sesion] = ahora.isoformat()
        estado.setdefault("proyectos", {})[proyecto] = ahora.isoformat()
        guardar_estado(ruta, estado, ahora)

        print(json.dumps({"hookSpecificOutput": {"hookEventName": nombre, "additionalContext": texto}},
                         ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass  # un reloj roto nunca debe frenar la sesión
    return 0


# ---------- modo normal ----------

def modo_normal(a: argparse.Namespace) -> int:
    ahora = ahora_con_zona(a.utc)
    hoy = ahora.date()
    datos = {
        "hoy": hoy.isoformat(),
        "hoy_texto": fecha_larga(hoy),
        "hora_local": ahora.strftime("%H:%M"),
        "zona": zona_texto(ahora),
        "semana_iso": hoy.isocalendar()[1],
        "fin_de_mes": describir_hasta(hoy, fin_de_mes(hoy)),
        "fin_de_trimestre": describir_hasta(hoy, fin_de_trimestre(hoy)),
        "fin_de_año": describir_hasta(hoy, date(hoy.year, 12, 31)),
        "fechas": [],
        "habiles": None,
    }
    for f in a.hasta:
        try:
            datos["fechas"].append(describir_hasta(hoy, date.fromisoformat(f)))
        except ValueError:
            print(f"Fecha inválida: {f} (usa AAAA-MM-DD)", file=sys.stderr)
            return 2
    if a.habiles is not None:
        destino = sumar_habiles(hoy, a.habiles)
        datos["habiles"] = {"dias": a.habiles, "fecha": destino.isoformat(), "dia": fecha_larga(destino)}

    if a.json:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return 0
    print(f"HOY: {datos['hoy_texto']} ({datos['hoy']}), {datos['hora_local']} hora local ({datos['zona']})")
    print(f"Semana {datos['semana_iso']} del año.")
    print(f"Fin de mes: {datos['fin_de_mes']['texto']}.")
    print(f"Fin de trimestre: {datos['fin_de_trimestre']['texto']}.")
    print(f"Fin de año: {datos['fin_de_año']['texto']}.")
    for f in datos["fechas"]:
        print(f"{f['fecha']} ({f['dia']}): {f['texto']}.")
    if datos["habiles"]:
        h = datos["habiles"]
        print(f"Dentro de {h['dias']} días hábiles: {h['dia']} ({h['fecha']}). No descuenta días feriados.")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    p = argparse.ArgumentParser(description="Noción del tiempo real para agentes de IA.")
    p.add_argument("--hook", action="store_true", help="modo hook de Claude Code (lee el evento por stdin)")
    p.add_argument("--hasta", nargs="*", default=[], metavar="AAAA-MM-DD", help="fechas para calcular cuánto falta")
    p.add_argument("--habiles", type=int, default=None, metavar="N", help="fecha dentro de N días hábiles")
    p.add_argument("--utc", type=float, default=None, metavar="HORAS", help="diferencia con UTC (ej. -3)")
    p.add_argument("--json", action="store_true", help="salida en JSON")
    a = p.parse_args()
    return modo_hook() if a.hook else modo_normal(a)


if __name__ == "__main__":
    sys.exit(main())
