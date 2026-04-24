"""
arbitrage_engine.py
-------------------
Motor estadístico. Dado:
    - un Axie listado,
    - una distribución de yield (min, mode, max),
    - un precio de Memento (USD),
    - un precio de ETH (USD) y RON (USD),

Calcula mediante Monte Carlo la probabilidad de que el revenue supere
el costo total (precio + fee 4.25% + gas), y devuelve un veredicto.

Se asume que el Axie Marketplace cotiza en ETH (Ronin bridged-ETH) a día de hoy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import numpy as np

from config import (
    GAS_ESTIMATE_RON,
    MARKETPLACE_FEE_RATE,
    MONTE_CARLO_ITERATIONS,
    PROFIT_PROBABILITY_THRESHOLD,
)
from graphql_client import AxieListing
from yield_calculator import YieldCalculator, YieldDistribution

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
@dataclass
class MarketContext:
    """Snapshot de mercado para una pasada del bot."""
    eth_usd: float
    ron_usd: float
    memento_usd_by_class: Dict[str, float]   # {"BEAST": 0.02, ...}


@dataclass
class ArbitrageResult:
    axie_id: str
    axie_class: str
    level: int
    breed_count: int
    matching_parts: int

    price_eth: float
    price_usd: float
    fee_usd: float
    gas_usd: float
    cost_total_usd: float

    expected_mementos: float
    expected_revenue_usd: float
    probability_profit: float
    expected_pnl_usd: float
    var_95_usd: float         # VaR 5% (peor 5% de escenarios)

    execute: bool

    def to_row(self) -> Dict[str, str]:
        return {
            "ID":        self.axie_id,
            "Class":     self.axie_class,
            "Lvl":       str(self.level),
            "BC":        str(self.breed_count),
            "Match":     str(self.matching_parts),
            "Price ETH": f"{self.price_eth:.5f}",
            "Cost USD":  f"{self.cost_total_usd:.2f}",
            "E[Mem]":    f"{self.expected_mementos:.1f}",
            "E[Rev] USD": f"{self.expected_revenue_usd:.2f}",
            "E[PnL] USD": f"{self.expected_pnl_usd:+.2f}",
            "VaR95 USD":  f"{self.var_95_usd:+.2f}",
            "P(win)":    f"{self.probability_profit*100:.1f}%",
            "Action":    "EJECUTAR ✅" if self.execute else "SKIP",
        }


# ---------------------------------------------------------------------------
class ArbitrageEngine:
    def __init__(
        self,
        yield_calc: YieldCalculator,
        n_iter: int = MONTE_CARLO_ITERATIONS,
        fee_rate: float = MARKETPLACE_FEE_RATE,
        gas_ron: float = GAS_ESTIMATE_RON,
        profit_threshold: float = PROFIT_PROBABILITY_THRESHOLD,
        seed: int | None = 42,
    ):
        self.yield_calc = yield_calc
        self.n_iter = n_iter
        self.fee_rate = fee_rate
        self.gas_ron = gas_ron
        self.profit_threshold = profit_threshold
        self.rng = np.random.default_rng(seed)

    # -------------------------------------------------------------------
    def _simulate_revenue(
        self,
        dist: YieldDistribution,
        memento_usd: float,
    ) -> np.ndarray:
        """
        Muestra N drops con distribución triangular y los convierte a USD.
        Añade ruido multiplicativo (±5%) sobre el precio para modelar
        slippage / movimiento del pool de Katana durante la venta.
        """
        drops = self.rng.triangular(
            left=dist.min_,
            mode=dist.mode,
            right=dist.max_,
            size=self.n_iter,
        )
        # Slippage lognormal ligero (sigma=0.05) centrado en 1.
        price_noise = self.rng.lognormal(mean=0.0, sigma=0.05, size=self.n_iter)
        prices = memento_usd * price_noise
        return drops * prices

    # -------------------------------------------------------------------
    def evaluate(
        self,
        axie: AxieListing,
        market: MarketContext,
    ) -> ArbitrageResult:
        # 1. Distribución de yield
        dist = self.yield_calc.distribution(axie)
        matching = self.yield_calc.matching_parts(axie)
        memento_usd = market.memento_usd_by_class.get(axie.axie_class, 0.0)

        # 2. Costos
        price_usd = axie.price_eth * market.eth_usd
        fee_usd = price_usd * self.fee_rate
        gas_usd = self.gas_ron * market.ron_usd
        cost_total_usd = price_usd + fee_usd + gas_usd

        # 3. Monte Carlo
        revenues = self._simulate_revenue(dist, memento_usd)
        pnls = revenues - cost_total_usd

        prob_profit = float(np.mean(pnls > 0))
        expected_revenue = float(np.mean(revenues))
        expected_pnl = float(np.mean(pnls))
        var_95 = float(np.percentile(pnls, 5))   # peor 5%

        return ArbitrageResult(
            axie_id=axie.axie_id,
            axie_class=axie.axie_class,
            level=axie.level,
            breed_count=axie.breed_count,
            matching_parts=matching,
            price_eth=axie.price_eth,
            price_usd=price_usd,
            fee_usd=fee_usd,
            gas_usd=gas_usd,
            cost_total_usd=cost_total_usd,
            expected_mementos=dist.expected(),
            expected_revenue_usd=expected_revenue,
            probability_profit=prob_profit,
            expected_pnl_usd=expected_pnl,
            var_95_usd=var_95,
            execute=prob_profit >= self.profit_threshold and expected_pnl > 0,
        )
