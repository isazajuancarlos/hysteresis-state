# hysteresis-state

Una máquina de estados con **histéresis por confirmación**, en Python puro y sin
dependencias, para que un clasificador ruidoso no haga *flapping*.

## El problema

Tienes una señal que a cada observación te dice en qué estado estás —un
clasificador de régimen, un sensor de conectividad, un detector de modo, un
semáforo de salud— pero cerca de los umbrales **oscila**: `OK, CAÍDO, OK, CAÍDO`.
Y cada cambio dispara algo caro o peligroso: una alerta, un failover, entrar o
salir del mercado. No quieres actuar en cada tembleque.

## La regla

Un estado nuevo solo se **commitea** tras sostenerse `confirmations`
observaciones consecutivas. Si el candidato cambia o revierte antes, la cuenta se
reinicia. El estado vigente es estable; los parpadeos se ignoran.

```python
from hysteresis_state import HysteresisState

estado = HysteresisState("OK", confirmations=3)

for lectura in stream:                 # p.ej. "OK" / "CAIDO"
    actual = estado.update(lectura)    # solo cambia tras 3 lecturas seguidas
    if estado.changed:                 # ¿esta lectura provocó la transición?
        alertar(actual)
```

`OK, CAÍDO, OK, CAÍDO, OK` no cambia nada: ningún candidato se sostuvo. Hacen
falta tres `CAÍDO` seguidos para commitear el cambio.

## Instalación

```bash
pip install hysteresis-state
```

Sin dependencias. Requiere Python ≥ 3.9.

## Histéresis asimétrica

A menudo quieres cambiar rápido hacia un estado seguro y despacio de vuelta al
arriesgado. Pasa un invocable `(desde, hacia) -> int`:

```python
# 1 confirmación para caer a "CAIDO", 5 para volver a "OK"
conf = lambda desde, hacia: 1 if hacia == "CAIDO" else 5
estado = HysteresisState("OK", confirmations=conf)

estado.update("CAIDO")   # cae al instante
# ...hacen falta 5 "OK" seguidos para volver
```

Es el patrón de un disyuntor: salta a la primera, se rearma con cautela.

## Qué puedes inspeccionar

```python
estado.state        # el estado committeado (estable)
estado.candidate    # el candidato a la espera, o None
estado.progress     # observaciones consecutivas acumuladas del candidato
estado.changed      # ¿la última update() committeó una transición?
estado.reset()          # descarta el candidato pendiente
estado.reset("NUEVO")   # además fija el estado, sin exigir confirmación
```

Los estados pueden ser cualquier valor comparable, no solo strings: enteros,
enums, tuplas.

## `confirmations=1` es "sin histéresis"

Con una sola confirmación, cada observación distinta cambia el estado en el acto.
Útil como caso base o para desactivar el suavizado por configuración sin
ramificar el código.

## De dónde viene

Salió del cerebro de régimen de un bot de trading, donde los umbrales de mercado
(tendencia / rango / caos) parpadeaban y cada cambio congelaba o reactivaba la
operativa. El mecanismo no dice nada de mercados: es anti-flapping para cualquier
señal discreta. Por eso se extrajo como librería.

## Tests

```bash
pip install "hysteresis-state[test]"
pytest
```

15 tests que cubren el conteo exacto, el flapping, el reinicio del candidato, la
histéresis asimétrica y los casos límite. Verificados por mutación (cambiar el
`>=` del commit por `>` rompe los tests que debe romper).

## Licencia

Apache-2.0.
