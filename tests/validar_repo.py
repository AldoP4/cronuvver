#!/usr/bin/env python3
"""Revisa el repo: manifiestos, hooks, skills y el comportamiento del reloj (incluido el hook)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "skills" / "cronuvver" / "scripts" / "cronuvver.py"
errores: list[str] = []


def revisar(cond: bool, msg: str) -> None:
    if not cond:
        errores.append(msg)


def correr(args: list[str], entrada: str = "", env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=entrada, capture_output=True,
                          text=True, encoding="utf-8", env=env, timeout=20)


# Manifiestos
plugin = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
market = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
revisar(market["plugins"][0]["name"] == plugin["name"], "el marketplace no coincide con plugin.json")
revisar(market["plugins"][0]["version"] == plugin["version"], "las versiones no coinciden")

# Hooks apuntan al script real
hooks = json.loads((RAIZ / "hooks" / "hooks.json").read_text(encoding="utf-8"))
for evento in ("SessionStart", "UserPromptSubmit"):
    cmd = hooks["hooks"][evento][0]["hooks"][0]["command"]
    ruta = cmd.split("${CLAUDE_PLUGIN_ROOT}/")[1].split('"')[0]
    revisar((RAIZ / ruta).exists(), f"el hook {evento} apunta a {ruta}, que no existe")

# Skills con frontmatter
for skill in ("cronuvver", "plan-real"):
    texto = (RAIZ / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    revisar(m is not None and f"name: {skill}" in m.group(1), f"{skill}: frontmatter inválido")

# Modo normal
r = correr(["--json", "--hasta", "2030-01-01", "--habiles", "5"])
revisar(r.returncode == 0, f"cronuvver.py --json falló: {r.stderr}")
if r.returncode == 0:
    d = json.loads(r.stdout)
    revisar(d["hoy"] == datetime.now().astimezone().date().isoformat(), "la fecha de hoy no coincide con el sistema")
    revisar(d["habiles"] is not None and d["fechas"], "faltan cálculos de --habiles o --hasta")

# Hook: sesión nueva, mensaje, hueco largo y entrada basura
with tempfile.TemporaryDirectory() as tmp:
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": tmp}
    ev = lambda nombre: json.dumps({"hook_event_name": nombre, "session_id": "t1", "cwd": "/proyecto"})
    r1 = correr(["--hook"], ev("SessionStart"), env)
    revisar(r1.returncode == 0 and "Hoy es" in r1.stdout, f"hook SessionStart: {r1.stdout} {r1.stderr}")
    r2 = correr(["--hook"], ev("UserPromptSubmit"), env)
    revisar(r2.returncode == 0 and "pasaron" in r2.stdout, f"hook UserPromptSubmit: {r2.stdout}")
    estado_p = Path(tmp) / "estado.json"
    estado = json.loads(estado_p.read_text(encoding="utf-8"))
    viejo = (datetime.now().astimezone() - timedelta(days=2)).isoformat()
    estado["sesiones"]["t1"] = viejo
    estado_p.write_text(json.dumps(estado), encoding="utf-8")
    r3 = correr(["--hook"], ev("UserPromptSubmit"), env)
    revisar("2 días" in r3.stdout and "Ojo" in r3.stdout, f"no avisó del hueco de 2 días: {r3.stdout}")
    r4 = correr(["--hook"], "esto no es json", env)
    revisar(r4.returncode == 0, "el hook falla con entrada basura")
    for r in (r1, r2, r3):
        try:
            json.loads(r.stdout)
        except Exception:  # noqa: BLE001
            errores.append(f"el hook no devolvió JSON válido: {r.stdout!r}")

if errores:
    print("FALLÓ:")
    for e in errores:
        print(f"  - {e}")
    sys.exit(1)
print("OK: manifiestos, hooks, skills y reloj en orden.")
