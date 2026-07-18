# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Juan Carlos Isaza Arenas

"""Tests de hysteresis-state. Sin dependencias."""
import pytest

from hysteresis_state import HysteresisState


def _feed(s, observaciones):
    """Alimenta una secuencia y devuelve la lista de estados committeados."""
    return [s.update(o) for o in observaciones]


# ---------------------------------------------------------------------------
# Comportamiento básico
# ---------------------------------------------------------------------------
def test_estado_inicial_sin_confirmacion():
    s = HysteresisState("OK", confirmations=3)
    assert s.state == "OK"
    assert s.candidate is None
    assert s.progress == 0
    assert s.changed is False


def test_no_cambia_hasta_confirmar():
    s = HysteresisState("A", confirmations=3)
    assert s.update("B") == "A"      # 1ª: candidato, no commitea
    assert s.candidate == "B" and s.progress == 1
    assert s.update("B") == "A"      # 2ª
    assert s.progress == 2
    assert s.update("B") == "B"      # 3ª: commit
    assert s.changed is True
    assert s.candidate is None and s.progress == 0


def test_flapping_nunca_commitea():
    s = HysteresisState("A", confirmations=3)
    estados = _feed(s, ["B", "A", "B", "A", "B", "A"])
    assert estados == ["A"] * 6      # nunca se sostiene → nunca cambia
    assert s.state == "A"


def test_candidato_que_cambia_reinicia_la_cuenta():
    s = HysteresisState("A", confirmations=3)
    s.update("B")                    # cand B, count 1
    s.update("B")                    # cand B, count 2
    assert s.update("C") == "A"      # cambia el candidato → cand C, count 1
    assert s.candidate == "C" and s.progress == 1


def test_observacion_igual_al_vigente_descarta_candidato():
    s = HysteresisState("A", confirmations=3)
    s.update("B")                    # cand B, count 1
    assert s.update("A") == "A"      # vuelve al vigente → descarta candidato
    assert s.candidate is None and s.progress == 0


def test_changed_solo_en_la_transicion():
    s = HysteresisState("A", confirmations=2)
    s.update("B"); assert s.changed is False
    s.update("B"); assert s.changed is True     # commit
    s.update("B"); assert s.changed is False    # ya es el vigente, sin transición


# ---------------------------------------------------------------------------
# confirmations = 1  → sin histéresis
# ---------------------------------------------------------------------------
def test_confirmations_1_cambia_en_el_acto():
    s = HysteresisState("A", confirmations=1)
    assert s.update("B") == "B"
    assert s.changed is True
    assert s.update("C") == "C"


# ---------------------------------------------------------------------------
# Histéresis asimétrica
# ---------------------------------------------------------------------------
def test_asimetrica_rapido_a_seguro_lento_a_riesgo():
    # 1 confirmación para ir a CAIDO, 3 para volver a OK
    conf = lambda desde, hacia: 1 if hacia == "CAIDO" else 3
    s = HysteresisState("OK", confirmations=conf)

    assert s.update("CAIDO") == "CAIDO"          # cae al instante
    assert s.changed is True

    assert s.update("OK") == "CAIDO"             # volver cuesta 3
    assert s.update("OK") == "CAIDO"
    assert s.update("OK") == "OK"
    assert s.changed is True


def test_asimetrica_umbral_invalido_falla():
    s = HysteresisState("A", confirmations=lambda d, h: 0)
    with pytest.raises(ValueError):
        s.update("B")


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------
def test_reset_limpia_candidato():
    s = HysteresisState("A", confirmations=3)
    s.update("B")
    s.reset()
    assert s.candidate is None and s.progress == 0
    assert s.state == "A"


def test_reset_con_estado_fija_sin_confirmar():
    s = HysteresisState("A", confirmations=3)
    s.update("B")
    s.reset("Z")
    assert s.state == "Z"
    assert s.candidate is None
    assert s.changed is False


# ---------------------------------------------------------------------------
# Validación de construcción
# ---------------------------------------------------------------------------
def test_confirmations_cero_falla():
    with pytest.raises(ValueError):
        HysteresisState("A", confirmations=0)


def test_confirmations_tipo_invalido_falla():
    with pytest.raises(TypeError):
        HysteresisState("A", confirmations="tres")
    with pytest.raises(TypeError):
        HysteresisState("A", confirmations=True)   # bool no cuela


# ---------------------------------------------------------------------------
# Tipos de estado arbitrarios (no solo strings) y repr
# ---------------------------------------------------------------------------
def test_estados_pueden_ser_cualquier_cosa_hashable_o_no():
    s = HysteresisState(0, confirmations=2)
    assert s.update(1) == 0
    assert s.update(1) == 1

    # tuplas como estado
    s2 = HysteresisState((0, 0), confirmations=1)
    assert s2.update((1, 2)) == (1, 2)


def test_repr_muestra_pendiente():
    s = HysteresisState("A", confirmations=3)
    assert "state='A'" in repr(s)
    s.update("B")
    assert "pending='B'(1)" in repr(s)
