# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Juan Carlos Isaza Arenas

"""hysteresis-state — una máquina de estados con histéresis por confirmación,
para no dejar que un clasificador ruidoso haga *flapping*.

El problema: tienes una señal que a cada observación te dice en qué estado
estás (un clasificador de régimen, un sensor de conectividad, un detector de
modo...), pero cerca de los umbrales oscila —A, B, A, B— y cada cambio dispara
algo caro o peligroso. No quieres actuar en cada tembleque.

La regla: un estado nuevo solo se **commitea** tras sostenerse ``confirmations``
observaciones consecutivas. Si el candidato cambia o revierte antes, el contador
se reinicia. El estado vigente es estable; los parpadeos se ignoran.

    from hysteresis_state import HysteresisState

    estado = HysteresisState("OK", confirmations=3)
    for lectura in stream:
        actual = estado.update(lectura)   # solo cambia tras 3 lecturas seguidas
        if estado.changed:
            alertar(actual)

Nació del cerebro de régimen de un bot de trading (anti-flapping en los umbrales
de mercado), pero no dice nada de mercados: sirve para cualquier señal discreta
que no quieres que rebote. Sin dependencias.
"""
from __future__ import annotations

__all__ = ["HysteresisState", "__version__"]

__version__ = "0.1.1"


class HysteresisState:
    """Máquina de estados con histéresis por confirmación.

    Le das observaciones con :meth:`update`; el estado *committeado* solo cambia
    cuando una observación distinta a la vigente se repite ``confirmations``
    veces seguidas. Cualquier observación igual al estado vigente, o un candidato
    que cambia antes de confirmarse, reinicia la cuenta.

    :param initial: estado inicial (ya committeado; no requiere confirmación).
    :param confirmations: cuántas observaciones consecutivas de un candidato hacen
        falta para commitearlo. Puede ser:

        - un ``int`` >= 1 (histéresis simétrica). ``1`` = sin histéresis (cada
          observación distinta cambia en el acto).
        - un invocable ``(desde, hacia) -> int`` para histéresis **asimétrica**:
          p.ej. rápido para caer a un estado seguro, lento para volver a uno
          arriesgado.

    Ejemplo asimétrico::

        # 1 confirmación para ir a "CAÍDO", 5 para volver a "OK"
        conf = lambda desde, hacia: 1 if hacia == "CAIDO" else 5
        s = HysteresisState("OK", confirmations=conf)
    """

    __slots__ = ("_state", "_confirmations", "_candidate", "_count", "_changed")

    def __init__(self, initial, confirmations=3):
        self._validar_confirmations(confirmations)
        self._state = initial
        self._confirmations = confirmations
        self._candidate = None
        self._count = 0
        self._changed = False

    @staticmethod
    def _validar_confirmations(confirmations):
        if callable(confirmations):
            return
        if not isinstance(confirmations, int) or isinstance(confirmations, bool):
            raise TypeError("confirmations debe ser int o invocable")
        if confirmations < 1:
            raise ValueError("confirmations debe ser >= 1")

    def _umbral(self, hacia) -> int:
        """Confirmaciones necesarias para pasar del estado vigente a `hacia`."""
        if callable(self._confirmations):
            n = self._confirmations(self._state, hacia)
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                raise ValueError(
                    f"confirmations({self._state!r}, {hacia!r}) debe devolver un int >= 1, dio {n!r}")
            return n
        return self._confirmations

    def update(self, observed):
        """Procesa una observación y devuelve el estado committeado resultante.

        Consulta :attr:`changed` justo después para saber si esta llamada
        provocó una transición.
        """
        self._changed = False

        # Igual al vigente: se afianza, cualquier candidato pendiente se descarta.
        if observed == self._state:
            self._candidate = None
            self._count = 0
            return self._state

        # Candidato nuevo (o distinto al que veníamos contando): arranca la cuenta.
        if observed != self._candidate:
            self._candidate = observed
            self._count = 1
        else:
            self._count += 1

        # ¿Sostenido lo suficiente? Commit.
        if self._count >= self._umbral(observed):
            self._state = observed
            self._candidate = None
            self._count = 0
            self._changed = True

        return self._state

    def reset(self, state=None):
        """Reinicia el candidato pendiente. Con ``state`` dado, además fija el
        estado committeado a ese valor (sin exigir confirmación). No marca
        :attr:`changed`."""
        if state is not None:
            self._state = state
        self._candidate = None
        self._count = 0
        self._changed = False

    @property
    def state(self):
        """El estado actualmente committeado (estable)."""
        return self._state

    @property
    def candidate(self):
        """El estado candidato a la espera de confirmación, o ``None`` si no hay
        ninguno pendiente."""
        return self._candidate

    @property
    def progress(self):
        """Cuántas observaciones consecutivas lleva acumuladas el candidato
        pendiente (0 si no hay). Compáralo con las confirmaciones necesarias
        para saber cuánto falta."""
        return self._count

    @property
    def changed(self):
        """``True`` si la última :meth:`update` committeó una transición."""
        return self._changed

    def __repr__(self):
        pend = ""
        if self._candidate is not None:
            pend = f" pending={self._candidate!r}({self._count})"
        return f"HysteresisState(state={self._state!r}{pend})"
