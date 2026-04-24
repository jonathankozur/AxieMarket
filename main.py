"""
main.py
-------
Loop principal del bot de arbitraje estadístico Axie <-> Mementos.

Pipeline por tick:
    1. Pull floor (50 axies) desde GraphQL Marketplace.
    2. Para cada Axie:
       a. Calcular distribución de yield esperada.
       b. Cotizar Memento de su clase en Katana.
       c. Monte Carlo -> probabilidad de profit.
    3. Imprimir tabla ordenada por P(win).
    4. Si P(win) > 60%, pasar a `RoninSigner` en modo DRY-RUN.
       (Producción: quitar dry_run + proveer private key vía KMS.)

Ejecución:
    python main.py                   # un tick
    python main.py --loop 60         # cada 60 s
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import List

from tabulate import tabulate

from arbitrage_engine import ArbitrageEngine, ArbitrageResult, MarketContext
from config import PROFIT_PROBABILITY_THRESHOLD, SearchCriteria
from graphql_client import AxieListing, AxieMarketplaceClient
from price_oracle import KatanaPriceOracle
from ronin_signer import RoninSigner
from yield_calculator import YieldCalculator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("arb-bot")


# ---------------------------------------------------------------------------
def build_market_context(
    oracle: KatanaPriceOracle,
    classes_needed: List[str],
    eth_usd: float,
) -> MarketContext:
    memento_prices = {}
    for cls in classes_needed:
        quote = oracle.quote_memento(cls)
        memento_prices[cls] = quote.usd_price
        log.info("Memento %-8s = $%.4f (%s)", cls, quote.usd_price, quote.source)
    ron_usd = oracle.quote_ron_usd()
    log.info("RON = $%.4f | ETH (hardcoded) = $%.2f", ron_usd, eth_usd)
    return MarketContext(
        eth_usd=eth_usd,
        ron_usd=ron_usd,
        memento_usd_by_class=memento_prices,
    )


def run_once(criteria: SearchCriteria, eth_usd_override: float, dry_run: bool) -> None:
    mp = AxieMarketplaceClient()
    oracle = KatanaPriceOracle()
    yc = YieldCalculator()
    engine = ArbitrageEngine(yield_calc=yc)
    signer = RoninSigner(dry_run=dry_run)

    # 1. Floor
    log.info("Fetching floor (limit=%d, classes=%s) ...", criteria.limit, criteria.classes)
    try:
        listings: List[AxieListing] = mp.get_floor_axies(criteria)
    except Exception as e:                             # noqa: BLE001
        log.error("Fallo al leer Marketplace: %s", e)
        return

    if not listings:
        log.warning("No se devolvieron listings. Revisa criteria / API key.")
        return
    log.info("Floor recibido: %d axies.", len(listings))

    # 2. Contexto de mercado
    classes_needed = sorted({l.axie_class for l in listings})
    market = build_market_context(oracle, classes_needed, eth_usd_override)

    # 3. Evaluar
    results: List[ArbitrageResult] = [engine.evaluate(l, market) for l in listings]
    results.sort(key=lambda r: (r.execute, r.probability_profit, r.expected_pnl_usd),
                 reverse=True)

    # 4. Tabla
    rows = [r.to_row() for r in results]
    print("\n" + tabulate(rows, headers="keys", tablefmt="github"))
    exec_count = sum(1 for r in results if r.execute)
    print(
        f"\nThreshold P(win) >= {PROFIT_PROBABILITY_THRESHOLD*100:.0f}%  ·  "
        f"{exec_count}/{len(results)} axies marcados EJECUTAR."
    )

    # 5. Ejecución (dry-run por defecto)
    for r in results:
        if not r.execute:
            continue
        log.info(
            "EJECUTAR Axie %s | P(win)=%.1f%% | E[PnL]=$%.2f | VaR95=$%.2f",
            r.axie_id, r.probability_profit * 100, r.expected_pnl_usd, r.var_95_usd,
        )
        # Aquí iría: comprar_en_marketplace() -> release() -> vender_mementos()
        signer.release_axie(int(r.axie_id))


# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Axie statistical arbitrage bot")
    p.add_argument("--loop", type=int, default=0,
                   help="Segundos entre ticks. 0 = un solo tick.")
    p.add_argument("--classes", nargs="+", default=["Beast"],
                   help="Clases a escanear (Beast, Aquatic, Plant, ...)")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--min-breed", type=int, default=7)  # >6
    p.add_argument("--max-breed", type=int, default=7)
    p.add_argument("--min-level", type=int, default=2)  # >1
    p.add_argument("--max-level", type=int, default=60)
    p.add_argument("--eth-usd", type=float, default=2800.0,
                   help="Precio ETH/USD para conversión (en prod usa oráculo).")
    p.add_argument("--live", action="store_true",
                   help="Desactiva dry-run y firma transacciones reales. ¡Cuidado!")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    criteria = SearchCriteria(
        classes=tuple(args.classes),
        breed_count_range=(args.min_breed, args.max_breed),
        level_range=(args.min_level, args.max_level),
        limit=args.limit,
    )

    try:
        while True:
            run_once(criteria, eth_usd_override=args.eth_usd, dry_run=not args.live)
            if args.loop <= 0:
                break
            log.info("Durmiendo %ds ...", args.loop)
            time.sleep(args.loop)
    except KeyboardInterrupt:
        log.info("Interrumpido por el usuario.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
