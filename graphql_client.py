"""
graphql_client.py
-----------------
Cliente mínimo para el gateway GraphQL de Sky Mavis / Axie Marketplace.

- Autenticación por header `X-API-Key` (Developer Console de Sky Mavis).
- Query `GetAxieBriefList` para obtener floor con filtros ricos.
- Query auxiliar `GetAxieDetail` para leer nivel / AXP / parts on-chain.

El schema de GraphQL del Marketplace cambia; los campos expuestos aquí
son el subconjunto que ha sido estable durante v2-v3. Si el endpoint
responde con `Cannot query field`, ajusta los campos en FRAGMENT_AXIE.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from config import MARKETPLACE_GRAPHQL_URL, SKYMAVIS_API_KEY, SearchCriteria

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fragmentos y queries
# ---------------------------------------------------------------------------
FRAGMENT_AXIE = """
fragment AxieBrief on Axie {
  id
  name
  class
  breedCount
  level
  stage
  newGenes
  battleInfo { banned }
  parts { id name class type specialGenes }
  order {
    id
    currentPrice      # wei
    currentPriceUsd
    startedAt
    expiredAt
    maker
    kind
  }
}
"""

QUERY_GET_AXIE_BRIEF_LIST = FRAGMENT_AXIE + """
query GetAxieBriefList(
  $auctionType: AuctionType
  $criteria: AxieSearchCriteria
  $from: Int
  $sort: SortBy
  $size: Int
  $owner: String
) {
  axies(
    auctionType: $auctionType
    criteria: $criteria
    from: $from
    sort: $sort
    size: $size
    owner: $owner
  ) {
    total
    results { ...AxieBrief }
  }
}
"""

QUERY_GET_AXIE_DETAIL = FRAGMENT_AXIE + """
query GetAxieDetail($axieId: ID!) {
  axie(axieId: $axieId) { ...AxieBrief }
}
"""


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------
@dataclass
class AxieListing:
    """Projección interna de un axie listado, lista para el motor de yield."""
    axie_id: str
    axie_class: str
    breed_count: int
    level: int
    stage: int
    part_classes: List[str]           # clases de las 6 partes
    price_wei: int                    # precio en WEI (ETH en Ronin)
    price_eth: float                  # precio en ETH (float)

    @classmethod
    def from_node(cls, node: Dict[str, Any]) -> Optional["AxieListing"]:
        order = node.get("order") or {}
        cur = order.get("currentPrice")
        if not cur:
            return None
        try:
            price_wei = int(cur)
        except (TypeError, ValueError):
            return None
        parts = node.get("parts") or []
        return cls(
            axie_id=str(node["id"]),
            axie_class=(node.get("class") or "").upper(),
            breed_count=int(node.get("breedCount") or 0),
            level=int(node.get("level") or 1),
            stage=int(node.get("stage") or 0),
            part_classes=[(p.get("class") or "").upper() for p in parts],
            price_wei=price_wei,
            price_eth=price_wei / 1e18,
        )


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
class AxieMarketplaceClient:
    """Wrapper ligero sobre `requests` con retry opcional."""

    def __init__(
        self,
        url: str = MARKETPLACE_GRAPHQL_URL,
        api_key: str = SKYMAVIS_API_KEY,
        timeout: int = 20,
    ):
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AxieArbBot/0.1",
        })
        if api_key:
            self.session.headers["X-API-Key"] = api_key

    # -------------------------------------------------------------------
    def _post(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables}
        resp = self.session.post(self.url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data and data["errors"]:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")
        return data["data"]

    # -------------------------------------------------------------------
    def get_floor_axies(self, criteria: SearchCriteria) -> List[AxieListing]:
        """
        Devuelve los `criteria.limit` Axies más baratos que cumplen los filtros.

        El schema del Marketplace espera el criteria así (valores de ejemplo):
            {
                "classes": ["Beast"],
                "breedCount": [7],
                "level": [2,3,...,60],
                "stages": [4],
                "parts": ["..."]
            }
        """
        # Expandir rangos a listas discretas porque el schema usa In-filters.
        breed_counts = list(range(criteria.breed_count_range[0],
                                  criteria.breed_count_range[1] + 1))
        levels = list(range(criteria.level_range[0],
                            criteria.level_range[1] + 1))

        gql_criteria: Dict[str, Any] = {
            "classes": [c.capitalize() for c in criteria.classes] or None,
            "breedCount": breed_counts or None,
            "level": levels or None,
            "stages": list(criteria.stages) or None,
        }
        if criteria.parts:
            gql_criteria["parts"] = list(criteria.parts)

        # Quitar keys vacías (el schema es estricto).
        gql_criteria = {k: v for k, v in gql_criteria.items() if v}

        variables = {
            "auctionType": criteria.auction_type,
            "criteria": gql_criteria,
            "from": 0,
            "sort": criteria.sort,
            "size": criteria.limit,
        }

        log.debug("GraphQL variables: %s", variables)
        data = self._post(QUERY_GET_AXIE_BRIEF_LIST, variables)
        results = (data.get("axies") or {}).get("results") or []

        listings: List[AxieListing] = []
        for node in results:
            listing = AxieListing.from_node(node)
            if listing is not None:
                listings.append(listing)
        return listings

    # -------------------------------------------------------------------
    def get_axie_detail(self, axie_id: str) -> Optional[AxieListing]:
        data = self._post(QUERY_GET_AXIE_DETAIL, {"axieId": axie_id})
        node = data.get("axie")
        if not node:
            return None
        return AxieListing.from_node(node)
