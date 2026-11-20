---
name: reloj
description: "Dice la fecha y hora reales y hace cuentas de calendario: cuánto falta para una fecha, qué día cae dentro de N días hábiles, en qué semana estamos, cuánto falta para fin de mes, trimestre o año. Úsala antes de afirmar qué día es, de decir 'este año', 'recientemente' o 'el mes pasado', y cada vez que haya que calcular un plazo o una fecha límite."
argument-hint: 'reloj | reloj ¿cuánto falta para el 1 de enero? | reloj ¿qué día cae en 10 días hábiles?'
allowed-tools: Bash
license: MIT
user-invocable: true
---

# /reloj

No sabes qué día es: tu idea del "hoy" viene de tus datos de entrenamiento. Antes de decir una fecha o calcular un plazo, pregúntale al reloj de la computadora.

1. Corre `scripts/reloj.py`, que está en la carpeta de esta skill (`python3`, o `python` en Windows). Si no hay Python, usa `date`.
   - Cuánto falta: `--hasta AAAA-MM-DD` (acepta varias fechas).
   - Qué día cae: `--habiles N`.
   - Otra zona horaria: `--utc <horas>` (por ejemplo `--utc -3`).
   - Para leerlo desde código: `--json`.
2. Contesta con el **día de la semana y la fecha completa**, y en los plazos di si son días corridos o hábiles.
3. El script no conoce los feriados. Si el plazo cruza fechas que suelen ser feriado en el país de la persona, avísalo.
4. Si la pregunta es de planeación ("¿para cuándo queda?", "¿cuánto tarda?"), usa la skill `plan-real`.
