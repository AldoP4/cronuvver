---
name: plan-real
description: "Planea y estima en tiempo real de 'humano + agente de IA', con fechas de calendario correctas. Separa el trabajo del agente (minutos), el trabajo de la persona (decisiones, revisiones, pruebas) y las esperas del mundo real (aprobaciones, DNS, clientes, envíos), que son las que mandan. Úsala siempre que haya que decir cuánto tarda algo, armar un plan por días o semanas, poner fechas de entrega, cotizar tiempos a un cliente, o cuando alguien pregunte '¿para cuándo queda?'."
argument-hint: 'plan-real lanzar la landing con pagos | plan-real ¿para cuándo queda la app de citas?'
allowed-tools: Bash, Read, Write, Edit, Glob
license: MIT
user-invocable: true
---

# /plan-real: tiempos y fechas de verdad

Los modelos estiman como si un humano escribiera todo el código: dicen "esto toma 2 o 3 semanas" y luego lo hacen en 20 minutos. Y al revés: ignoran lo que de verdad tarda, que son las personas y las esperas. Además no saben qué día es. Esta skill corrige las dos cosas.

## Paso 1: el reloj
Corre el script del reloj, que está en la skill hermana: `../cronuvver/scripts/cronuvver.py` desde la carpeta de esta skill (`python3`, o `python` en Windows; si no hay Python, `date`). Si no lo encuentras, búscalo con Glob (`**/cronuvver/scripts/cronuvver.py`). Toda fecha del plan se calcula desde ahí. Para fechas futuras usa `--habiles N` (qué día cae dentro de N días hábiles) y `--hasta AAAA-MM-DD` (cuánto falta). Si la persona vive en otra zona, `--utc <horas>`.

## Paso 2: el contexto de la persona
Sin preguntar de más, junta (de la conversación o con una sola pregunta):
- **Horas por semana** que la persona le puede dar, y qué días no trabaja.
- **Quién decide o aprueba** (ella sola, un socio, un cliente).
- **Fechas fijas** que no se mueven (un lanzamiento, una ley, una junta).

Si no lo dice, supón tiempo parcial (unas 20 horas por semana, de lunes a viernes) y dilo.

## Paso 3: parte el trabajo en tres tipos

| Tipo | Qué es | Cómo se estima |
|---|---|---|
| **Agente** | Lo que hace Claude Code: escribir código, investigar, redactar, generar archivos | En **minutos u horas de reloj**, contando que hay que correrlo, probarlo y corregirlo. Casi nunca son días. |
| **Persona** | Decidir, revisar, probar en el celular, grabar, contestar, dar accesos, pagar algo | En horas reales de la persona, repartidas en **sus** horas disponibles. |
| **Espera** | Lo que depende de otros: aprobaciones de Meta, Apple o Google, propagación de DNS, verificación de cuentas, respuesta de un cliente, envíos, bancos | En **días corridos o hábiles**, con el rango que publica quien controla la espera. Es lo que casi siempre define la fecha. |

Reglas:
- **Nunca** estimes trabajo del agente en semanas de humano. Si una tarea de código "se siente" de semanas, pártela hasta que cada pieza sea de minutos u horas.
- Las esperas van con su fuente cuando la tengas (por ejemplo, la documentación de la plataforma). Si no, rango conservador marcado como supuesto.
- Usa **rangos** (mejor caso y caso realista), no un solo número.
- Marca la **ruta crítica**: la cadena de pasos que, si se atrasa uno, se atrasa todo. Casi siempre pasa por las esperas y por las revisiones de la persona.
- Lo que se puede hacer **en paralelo** mientras se espera, dilo: es donde se gana tiempo.

## Paso 4: convierte a fechas
1. Acomoda las tareas de la persona en sus horas disponibles.
2. Suma las esperas en días corridos o hábiles según corresponda (con `cronuvver.py --habiles`).
3. Cada fecha se escribe con **día de la semana** ("viernes 27 de noviembre"), nunca solo "en una semana".
4. Si hay una fecha fija, calcula la holgura: cuántos días sobran o faltan.
5. `cronuvver.py` no descuenta feriados. Si el plan cruza fechas que suelen ser feriado o vacaciones (Navidad, Año Nuevo, Semana Santa, feriados del país), avísalo y suma holgura.

## Paso 5: entrega

```
Hoy: [fecha de cronuvver.py]

| Tarea | Tipo | Tiempo activo | Espera | Lista para |
|---|---|---|---|---|

Ruta crítica: ...
En paralelo mientras se espera: ...
Fecha realista: [día de la semana, fecha] · Mejor caso: [...]
Supuestos: horas por semana, quién aprueba, esperas sin fuente.
```

Primero la fecha realista en una línea; luego la tabla.

## Paso 6 (opcional): calibrar
Si la carpeta del proyecto tiene `.cronuvver/estimaciones.jsonl`, léelo antes de estimar: cada línea es `{"fecha": "...", "tarea": "...", "tipo": "agente|persona|espera", "estimado_min": N, "real_min": N}`. Si las tareas del mismo tipo suelen tardar más (o menos) de lo estimado, ajusta con esa proporción y dilo.

Cuando una tarea del plan termine y se sepa cuánto tardó, ofrece agregar la línea al archivo (solo con el OK de la persona). Así cada proyecto estima mejor que el anterior.

## Errores que esta skill evita
- "Esto te toma 2 o 3 semanas" para algo que el agente hace en una tarde.
- "Queda en una semana" sin contar que Meta tarda días en aprobar una plantilla o que el cliente contesta los lunes.
- "El jueves" sin decir qué jueves, o un jueves que cae en feriado.
- "Este año", "recientemente", "el mes pasado" calculados desde la fecha de entrenamiento del modelo.
