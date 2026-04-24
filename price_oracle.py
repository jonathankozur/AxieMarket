"""
price_oracle.py
---------------
Oráculo de precios para los tokens Memento.

Estrategia:
1. Si hay un `RONIN_RPC_URL` configurado, consulta directamente al router
   de Katana (`getAmountsOut`) usando el par Memento -> WRON -> USDC.
2. Si falla (RPC no disponible, token sin pool, token address placeholder),
   cae a un `FALLBACK_USD_PRICE` editable para no romper el pipeline
   en entornos de desarrollo.

El retorno es siempre USD por unidad de Memento (1.0 = token con 18 dec).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from config import (
    KATANA_ROUTER_ADDRESS,
    MEMENTO_TOKENS,
    RONIN_RPC_URL,
    USDC_ADDRESS,
    WRON_ADDRESS,
)

log = logging.getLogger(__name__)

# ABI mínima de UniswapV2Router02 (Katana es un fork).
ROUTER_ABI = [
    {
        "name": "getAmountsOut",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"},
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
    }
]

# Precios de fallback por clase (USD). Actualiza antes de producción
# o déjalos como floor conservador para el backtest.
FALLBACK_USD_PRICE: Dict[str, float] = {
    "BEAST":   0.018,
    "AQUATIC": 0.022,
    "PLANT":   0.020,
    "BIRD":    0.025,
    "BUG":     0.019,
    "REPTILE": 0.021,
    "MECH":    0.080,
    "DUSK":    0.090,
    "DAWN":    0.070,
}


@dataclass
class PriceQuote:
    token_class: str
    usd_price: float
    source: str  # "katana" | "fallback"


class KatanaPriceOracle:
    def __init__(self, rpc_url: str = RONIN_RPC_URL, router: str = KATANA_ROUTER_ADDRESS):
        self.rpc_url = rpc_url
        self.router_addr = router
        self._w3 = None
        self._router = None

    # -------------------------------------------------------------------
    def _ensure_web3(self) -> bool:
        if self._router is not None:
            return True
        try:
            from web3 import Web3                    # import tardío
            w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 10}))
            if not w3.is_connected():
                log.warning("Ronin RPC no alcanzable en %s", self.rpc_url)
                return False
            self._w3 = w3
            self._router = w3.eth.contract(
                address=Web3.to_checksum_address(self.router_addr),
                abi=ROUTER_ABI,
            )
            return True
        except Exception as e:                        # noqa: BLE001
            log.warning("web3 init falló (%s). Usando fallback.", e)
            return False

    # -------------------------------------------------------------------
    def quote_memento(self, token_class: str) -> PriceQuote:
        token_class = token_class.upper()
        token_addr = MEMENTO_TOKENS.get(token_class, "")

        # Placeholder? -> fallback
        if not token_addr or token_addr.startswith("0x000000"):
            return PriceQuote(token_class, FALLBACK_USD_PRICE.get(token_class, 0.02), "fallback")

        if not self._ensure_web3():
            return PriceQuote(token_class, FALLBACK_USD_PRICE.get(token_class, 0.02), "fallback")

        try:
            from web3 import Web3
            one_token = 10 ** 18
            path = [
                Web3.to_checksum_address(token_addr),
                Web3.to_checksum_address(WRON_ADDRESS),
                Web3.to_checksum_address(USDC_ADDRESS),
            ]
            amounts = self._router.functions.getAmountsOut(one_token, path).call()
            # USDC en Ronin usa 6 decimales.
            usd = amounts[-1] / 10 ** 6
            return PriceQuote(token_class, float(usd), "katana")
        except Exception as e:                        # noqa: BLE001
            log.warning("getAmountsOut falló para %s (%s). Fallback.", token_class, e)
            return PriceQuote(token_class, FALLBACK_USD_PRICE.get(token_class, 0.02), "fallback")

    # -------------------------------------------------------------------
    def quote_ron_usd(self) -> float:
        """Precio de 1 RON en USD (para convertir gas a USD)."""
        if not self._ensure_web3():
            return 0.45  # fallback razonable
        try:
            from web3 import Web3
            one = 10 ** 18
            path = [
                Web3.to_checksum_address(WRON_ADDRESS),
                Web3.to_checksum_address(USDC_ADDRESS),
            ]
            amounts = self._router.functions.getAmountsOut(one, path).call()
            return amounts[-1] / 10 ** 6
        except Exception:                             # noqa: BLE001
            return 0.45
