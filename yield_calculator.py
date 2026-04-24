"""
yield_calculator.py
-------------------
Motor de "Expected Yield" para el release mechanism.

Modelo parametrizable (NO un único valor fijo):
    drop ~ f(class_base, matching_parts_bonus, level_multiplier) * ruido

Las constantes aquí son *prior* educados a partir de observación histórica.
Ajústalas en `YieldConfig` tras calibrar con datos reales de releases.

La API pública devuelve *distribuciones* (min, mode, max) para que el
motor Monte Carlo en `arbitrage_engine.py` las samplee con una triangular.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from graphql_client import AxieListing


# ---------------------------------------------------------------------------
# Config del modelo - editable por clase
# ---------------------------------------------------------------------------
@dataclass
class YieldConfig:
    # Drop base de Mementos de su propia clase al hacer release.
    base_drop: Dict[str, float] = field(default_factory=lambda: {
        "BEAST": 18.0, "AQUATIC": 18.0, "PLANT": 18.0, "BIRD": 18.0,
        "BUG": 18.0, "REPTILE": 18.0, "MECH": 14.0, "DUSK": 14.0, "DAWN": 14.0,
    })
    # Ancho de la distribución triangular (±%) alrededor del drop base.
    base_spread: float = 0.25

    # Bono por cada parte que coincide con la clase del Axie (0–6).
    matching_part_bonus: float = 1.5
    matching_part_spread: float = 0.30

    # Multiplicador por nivel on-chain (curva suave).
    # M(level) = 1 + level_coeff * log1p(level - 1)
    level_coeff: float = 0.22

    # Breed count no da yield directo, pero sí penaliza (axies muy breeded
    # consumen un poco más de "energía" al hacer release). Escalar ligero.
    breed_penalty_per_count: float = 0.01   # -1% por breed count extra sobre 0


@dataclass
class YieldDistribution:
    """Distribución triangular (min, mode, max) de Mementos esperados."""
    axie_class: str
    min_: float
    mode: float
    max_: float

    def expected(self) -> float:
        return (self.min_ + self.mode + self.max_) / 3.0


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------
class YieldCalculator:
    def __init__(self, cfg: YieldConfig | None = None):
        self.cfg = cfg or YieldConfig()

    # -------------------------------------------------------------------
    def level_multiplier(self, level: int) -> float:
        import math
        return 1.0 + self.cfg.level_coeff * math.log1p(max(level - 1, 0))

    # -------------------------------------------------------------------
    def matching_parts(self, axie: AxieListing) -> int:
        """Nº de partes (0..6) cuya clase == clase del Axie."""
        return sum(1 for p in axie.part_classes if p == axie.axie_class)

    # -------------------------------------------------------------------
    def distribution(self, axie: AxieListing) -> YieldDistribution:
        cfg = self.cfg
        base = cfg.base_drop.get(axie.axie_class, 16.0)
        lvl_mult = self.level_multiplier(axie.level)
        match_n = self.matching_parts(axie)

        bonus_mode = match_n * cfg.matching_part_bonus
        bonus_min = match_n * cfg.matching_part_bonus * (1 - cfg.matching_part_spread)
        bonus_max = match_n * cfg.matching_part_bonus * (1 + cfg.matching_part_spread)

        breed_penalty = max(0.0, 1.0 - cfg.breed_penalty_per_count * axie.breed_count)

        mode = (base + bonus_mode) * lvl_mult * breed_penalty
        min_ = (base * (1 - cfg.base_spread) + bonus_min) * lvl_mult * breed_penalty
        max_ = (base * (1 + cfg.base_spread) + bonus_max) * lvl_mult * breed_penalty

        # Clamp sanity.
        min_ = max(min_, 0.0)
        mode = max(mode, min_)
        max_ = max(max_, mode)

        return YieldDistribution(axie.axie_class, min_, mode, max_)

    # -------------------------------------------------------------------
    def describe(self, axie: AxieListing) -> Dict[str, float]:
        dist = self.distribution(axie)
        return {
            "class": axie.axie_class,
            "level": axie.level,
            "matching_parts": self.matching_parts(axie),
            "breed_count": axie.breed_count,
            "yield_min": dist.min_,
            "yield_mode": dist.mode,
            "yield_max": dist.max_,
            "yield_expected": dist.expected(),
        }
