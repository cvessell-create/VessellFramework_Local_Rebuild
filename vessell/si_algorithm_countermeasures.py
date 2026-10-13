# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Mathematical and game-theoretic countermeasures against Hail-to-the-Analyst algorithms.

This module formalizes analytical derivations and tactical policies designed
to solve and defeat the specific mathematical mechanics implemented in the
Hail-to-the-Analyst game engine:

1. Melee Collision & Altitude Decoupling:
   - Game Formula: damage applied only when `dist < 0.65 and (player.height or 0) < 0.8`.
   - Countermeasure: Jetpack elevation above h=0.8 completely neutralizes ground melee.

2. Harmonic Drone Strafe Prediction:
   - Game Formula: `dx_strafe = -uy * sin(phase) * dt * 0.35`, `dy_strafe = ux * sin(phase) * dt * 0.35`.
   - Countermeasure: Analytical harmonic lead targeting based on phase prediction.

3. Weapon Spread & Optimal Kill-Cone Geometry:
   - Game Formula: Pellet hit test `|da| < size` where `size = 0.35 / dist`, `spread = 0.15`.
   - Countermeasure: Guaranteed 100% pellet concentration at distances `dist <= 2.33`.

4. Game Theory Fair Division Auctions:
   - Game Formula: Vickrey second-price sealed bid; Knaster fair division; Adjusted Winner.
   - Countermeasure: Strict dominance of truth-revealing valuations and Nash equilibrium bids.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MeleeCountermeasure:
    """Analytical evaluation of enemy melee collision mechanics."""

    safe_from_melee: bool
    altitude_immunity: bool
    distance_margin: float
    recommended_action: str
    explanation: str


@dataclass(frozen=True)
class DroneTrajectoryPrediction:
    """Predictive lead calculation for harmonic sinusoidal drone movement."""

    predicted_dx: float
    predicted_dy: float
    turnaround_detected: bool
    recommended_lead_angle: float


@dataclass(frozen=True)
class WeaponOptimizationResult:
    """Ballistic kill-cone optimization for Breacher (shotgun) and Sidearm."""

    target_angular_size: float
    guaranteed_hit: bool
    recommended_weapon_id: int
    recommended_weapon_name: str
    effective_damage_multiplier: float


class GameAlgorithmCountermeasures:
    """Solver defeating the mathematical mechanics built into Hail-to-the-Analyst."""

    @staticmethod
    def evaluate_melee_threat(
        enemy_type: str,
        dist: float,
        player_height: float,
        player_fuel: float,
    ) -> MeleeCountermeasure:
        """Evaluate and defeat melee enemies (MOLE, ICE_PIG) via altitude & spacing."""
        is_melee_type = enemy_type in {"MOLE", "ICE_PIG"}
        if not is_melee_type:
            return MeleeCountermeasure(
                safe_from_melee=True,
                altitude_immunity=False,
                distance_margin=dist,
                recommended_action="STANDARD_ENGAGEMENT",
                explanation=f"{enemy_type} is a ranged combatant; melee collision rule does not apply.",
            )

        # Game condition: (dist <= 0.65) and (player.height < 0.8)
        altitude_immunity = player_height >= 0.8
        safe_distance = dist > 0.65

        if altitude_immunity:
            action = "HOVER_FIRE"
            explanation = (
                f"Altitude h={player_height:.2f} >= 0.8: player bounding box decouples from "
                f"ground melee hitbox. Enemy cannot inflict damage regardless of distance."
            )
        elif dist < 1.5:
            if player_fuel > 2.0:
                action = "LIFT_OFF_JETPACK"
                explanation = "Threat in close quarters. Ascend above h=0.8 to trigger altitude immunity."
            else:
                action = "KITE_BACKSTEP"
                explanation = "Threat in close quarters without fuel. Backstep at player sprint velocity."
        else:
            action = "MAINTAIN_SPACING"
            explanation = f"Distance {dist:.2f}m exceeds melee radius 0.65m. Maintain fire."

        return MeleeCountermeasure(
            safe_from_melee=altitude_immunity or safe_distance,
            altitude_immunity=altitude_immunity,
            distance_margin=dist - 0.65,
            recommended_action=action,
            explanation=explanation,
        )

    @staticmethod
    def predict_drone_lead(
        dist: float,
        phase: float,
        dt: float,
        unit_x: float,
        unit_y: float,
    ) -> DroneTrajectoryPrediction:
        """Predict drone harmonic strafe position defeating lateral evasion."""
        # Drone game equation: moveEntity(e, -uy * sin(phase) * dt * 0.35, ux * sin(phase) * dt * 0.35)
        current_sin = math.sin(phase)
        next_phase = phase + dt
        next_sin = math.sin(next_phase)

        # Strafe delta
        predicted_dx = -unit_y * next_sin * dt * 0.35
        predicted_dy = unit_x * next_sin * dt * 0.35

        # Detect harmonic turnaround (inflection point where derivative changes sign)
        turnaround = (current_sin * next_sin < 0) or (abs(next_sin) > 0.98)

        # Compute lead angle offset in radians
        lateral_displacement = next_sin * 0.35 * dt
        lead_angle = math.atan2(lateral_displacement, max(0.1, dist))

        return DroneTrajectoryPrediction(
            predicted_dx=predicted_dx,
            predicted_dy=predicted_dy,
            turnaround_detected=turnaround,
            recommended_lead_angle=lead_angle,
        )

    @staticmethod
    def optimize_weapon_selection(
        dist: float,
        bullets: int,
        shells: int,
        enemy_hp: float,
    ) -> WeaponOptimizationResult:
        """Optimize weapon selection defeating spread falloff and conserving ammo."""
        # Breacher spread: 0.15 rad. Hit radius: 0.35 / dist.
        # Condition for 100% pellet hit: (0.35 / dist) >= 0.15 <=> dist <= 2.333m.
        angular_size = 0.35 / max(0.1, dist)
        guaranteed_spread_hit = angular_size >= 0.15

        if dist <= 3.0 and shells > 0:
            return WeaponOptimizationResult(
                target_angular_size=angular_size,
                guaranteed_hit=guaranteed_spread_hit,
                recommended_weapon_id=1,
                recommended_weapon_name="BREACHER",
                effective_damage_multiplier=1.0 if guaranteed_spread_hit else (angular_size / 0.15),
            )
        elif bullets > 0:
            return WeaponOptimizationResult(
                target_angular_size=angular_size,
                guaranteed_hit=True,  # Single centered ray
                recommended_weapon_id=0,
                recommended_weapon_name="SIDEARM",
                effective_damage_multiplier=1.0,
            )
        elif shells > 0:
            return WeaponOptimizationResult(
                target_angular_size=angular_size,
                guaranteed_hit=guaranteed_spread_hit,
                recommended_weapon_id=1,
                recommended_weapon_name="BREACHER",
                effective_damage_multiplier=angular_size / 0.15,
            )
        else:
            return WeaponOptimizationResult(
                target_angular_size=angular_size,
                guaranteed_hit=False,
                recommended_weapon_id=0,
                recommended_weapon_name="SIDEARM",
                effective_damage_multiplier=0.0,
            )

    @staticmethod
    def compute_dominant_auction_bid(
        round_method: str,
        true_valuation: float,
        num_items: int = 1,
    ) -> list[float]:
        """Compute mathematically dominant bidding strategy defeating opposing agents."""
        if round_method == "vickrey":
            # In second-price sealed auctions, truth-revealing valuation is the unique weakly dominant strategy.
            return [round(true_valuation, 2)]
        elif round_method == "knaster":
            # In Knaster equitable division, bid true fair valuation across all resource caches
            return [round(true_valuation / max(1, num_items), 2)] * num_items
        elif round_method == "adjusted_winner":
            # In Adjusted Winner, allocate points proportionally to subjective utility
            return [round(100.0 / max(1, num_items), 2)] * num_items
        else:
            return [round(true_valuation, 2)]
