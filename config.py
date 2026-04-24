"""
config.py
---------
Carga de configuración centralizada para el bot de arbitraje estadístico.
Separa credenciales (env) de parámetros de negocio (constantes).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv es opcional; si no está instalado, se usarán variables del entorno.
    pass


# ---------------------------------------------------------------------------
# Endpoints y red
# ---------------------------------------------------------------------------
MARKETPLACE_GRAPHQL_URL: str = os.getenv(
    "MARKETPLACE_GRAPHQL_URL",
    "https://graphql-gateway.axieinfinity.com/graphql",
)
SKYMAVIS_API_KEY: str = os.getenv("SKYMAVIS_API_KEY", "")

RONIN_RPC_URL: str = os.getenv("RONIN_RPC_URL", "https://api.roninchain.com/rpc")
RONIN_CHAIN_ID: int = int(os.getenv("RONIN_CHAIN_ID", "2020"))

# ---------------------------------------------------------------------------
# Claves / wallets - solo referencias; no hardcodear
# ---------------------------------------------------------------------------
RONIN_PRIVATE_KEY: str = os.getenv("RONIN_PRIVATE_KEY", "")
RONIN_WALLET_ADDRESS: str = os.getenv("RONIN_WALLET_ADDRESS", "")

# ---------------------------------------------------------------------------
# Contratos
# ---------------------------------------------------------------------------
RELEASE_CONTRACT_ADDRESS: str = os.getenv("RELEASE_CONTRACT_ADDRESS", "")
KATANA_ROUTER_ADDRESS: str = os.getenv(
    "KATANA_ROUTER_ADDRESS", "0x7d0556d55ca1a92708681e2e231733ebd922597d"
)
WRON_ADDRESS: str = os.getenv("WRON_ADDRESS", "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4")
USDC_ADDRESS: str = os.getenv("USDC_ADDRESS", "0x0b7007c13325c48911f73a2dad5fa5dcbf808adc")

# Direcciones orientativas de Mementos (verificar en docs oficiales antes de producción)
# Estos son placeholders: cada clase tiene su propio ERC-20 de "Memento".
MEMENTO_TOKENS: Dict[str, str] = {
    "BEAST":    os.getenv("MEMENTO_BEAST",    "0x0000000000000000000000000000000000000001"),
    "AQUATIC":  os.getenv("MEMENTO_AQUATIC",  "0x0000000000000000000000000000000000000002"),
    "PLANT":    os.getenv("MEMENTO_PLANT",    "0x0000000000000000000000000000000000000003"),
    "BIRD":     os.getenv("MEMENTO_BIRD",     "0x0000000000000000000000000000000000000004"),
    "BUG":      os.getenv("MEMENTO_BUG",      "0x0000000000000000000000000000000000000005"),
    "REPTILE":  os.getenv("MEMENTO_REPTILE",  "0x0000000000000000000000000000000000000006"),
    "MECH":     os.getenv("MEMENTO_MECH",     "0x0000000000000000000000000000000000000007"),
    "DUSK":     os.getenv("MEMENTO_DUSK",     "0x0000000000000000000000000000000000000008"),
    "DAWN":     os.getenv("MEMENTO_DAWN",     "0x0000000000000000000000000000000000000009"),
}

# ---------------------------------------------------------------------------
# Parámetros de negocio / riesgo
# ---------------------------------------------------------------------------
MARKETPLACE_FEE_RATE: float = float(os.getenv("MARKETPLACE_FEE_RATE", "0.0425"))
GAS_ESTIMATE_RON: float = float(os.getenv("GAS_ESTIMATE_RON", "0.0008"))
PROFIT_PROBABILITY_THRESHOLD: float = float(os.getenv("PROFIT_PROBABILITY_THRESHOLD", "0.60"))
MONTE_CARLO_ITERATIONS: int = int(os.getenv("MONTE_CARLO_ITERATIONS", "10000"))


@dataclass(frozen=True)
class SearchCriteria:
    """
    Criterios de búsqueda para el floor. Ajusta antes de cada run.
    Breed count > 6 y level > 1 son los filtros solicitados.
    """
    classes: Tuple[str, ...] = ("Beast",)
    parts: Tuple[str, ...] = ()              # slugs de partes (ej. "beast-nut-cracker")
    breed_count_range: Tuple[int, int] = (7, 7)   # >6  -> min 7
    level_range: Tuple[int, int] = (2, 60)        # >1  -> min 2
    stages: Tuple[int, ...] = (4,)                # 4 = adulto
    limit: int = 50
    sort: str = "PriceAsc"
    auction_type: str = "Sale"
    include_parts: Tuple[str, ...] = field(default_factory=tuple)
