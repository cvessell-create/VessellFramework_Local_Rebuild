# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Unit tests verifying algorithm and formula countermeasures against Hail-to-the-Analyst."""

import pytest

from vessell.si_algorithm_countermeasures import (
    GameAlgorithmCountermeasures,
    MeleeCountermeasure,
    WeaponOptimizationResult,
)


def test_altitude_immunity_defeats_mole_melee():
    solver = GameAlgorithmCountermeasures()

    # When player is grounded (h=0.0) at dist=0.5m (inside melee range 0.65m)
    threat_ground = solver.evaluate_melee_threat(
        enemy_type="MOLE", dist=0.5, player_height=0.0, player_fuel=50.0
    )
    assert not threat_ground.safe_from_melee
    assert not threat_ground.altitude_immunity
    assert threat_ground.recommended_action == "LIFT_OFF_JETPACK"

    # When player ascends above h=0.8m using jetpack
    threat_flying = solver.evaluate_melee_threat(
        enemy_type="MOLE", dist=0.5, player_height=0.85, player_fuel=40.0
    )
    assert threat_flying.safe_from_melee
    assert threat_flying.altitude_immunity
    assert threat_flying.recommended_action == "HOVER_FIRE"
    assert "decouples" in threat_flying.explanation


def test_predict_drone_harmonic_lead():
    solver = GameAlgorithmCountermeasures()
    pred = solver.predict_drone_lead(
        dist=3.0, phase=1.57, dt=0.05, unit_x=0.0, unit_y=1.0
    )
    assert isinstance(pred.predicted_dx, float)
    assert isinstance(pred.predicted_dy, float)
    assert isinstance(pred.recommended_lead_angle, float)


def test_weapon_spread_guaranteed_hit_geometry():
    solver = GameAlgorithmCountermeasures()

    # At dist <= 2.33m, 0.35 / dist >= 0.15 (guaranteed 100% pellet hit for Breacher)
    opt_close = solver.optimize_weapon_selection(dist=1.8, bullets=20, shells=8, enemy_hp=62.0)
    assert opt_close.recommended_weapon_name == "BREACHER"
    assert opt_close.recommended_weapon_id == 1
    assert opt_close.guaranteed_hit is True

    # At long range (>3.0m), switch to Sidearm for pinpoint accuracy
    opt_far = solver.optimize_weapon_selection(dist=4.5, bullets=20, shells=8, enemy_hp=62.0)
    assert opt_far.recommended_weapon_name == "SIDEARM"
    assert opt_far.recommended_weapon_id == 0


def test_dominant_auction_bids():
    solver = GameAlgorithmCountermeasures()
    vickrey_bid = solver.compute_dominant_auction_bid("vickrey", 45.0)
    assert vickrey_bid == [45.0]

    knaster_bids = solver.compute_dominant_auction_bid("knaster", 60.0, num_items=3)
    assert knaster_bids == [20.0, 20.0, 20.0]

    aw_bids = solver.compute_dominant_auction_bid("adjusted_winner", 100.0, num_items=4)
    assert aw_bids == [25.0, 25.0, 25.0, 25.0]
