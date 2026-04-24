"""
ronin_signer.py
---------------
Stub de firma / ejecución en Ronin. NO incluye llaves reales.

Uso previsto (producción):
    signer = RoninSigner(private_key=os.environ["RONIN_PRIVATE_KEY"])
    tx_hash = signer.release_axie(axie_id=12345678)

Importante:
    - Ronin usa EIP-155 con chainId = 2020 (mainnet) o 2021 (Saigon).
    - Direcciones Ronin usan prefijo `ronin:` en el UI pero `0x` en RPC.
    - Nunca hardcodear la private_key en el repo. Usar HSM / KMS.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from config import (
    RELEASE_CONTRACT_ADDRESS,
    RONIN_CHAIN_ID,
    RONIN_PRIVATE_KEY,
    RONIN_RPC_URL,
    RONIN_WALLET_ADDRESS,
)

log = logging.getLogger(__name__)

# ABI mínima del contrato Release (ajustar a la ABI real en producción).
RELEASE_ABI = [
    {
        "name": "releaseAxie",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "axieId", "type": "uint256"}],
        "outputs": [],
    }
]


class RoninSigner:
    def __init__(
        self,
        rpc_url: str = RONIN_RPC_URL,
        private_key: str = RONIN_PRIVATE_KEY,
        wallet: str = RONIN_WALLET_ADDRESS,
        release_contract: str = RELEASE_CONTRACT_ADDRESS,
        chain_id: int = RONIN_CHAIN_ID,
        dry_run: bool = True,
    ):
        self.rpc_url = rpc_url
        self.private_key = private_key
        self.wallet = wallet
        self.release_contract = release_contract
        self.chain_id = chain_id
        self.dry_run = dry_run
        self._w3 = None
        self._contract = None

    # -------------------------------------------------------------------
    def _ensure_web3(self) -> bool:
        if self._w3 is not None:
            return True
        try:
            from web3 import Web3
            from web3.middleware import geth_poa_middleware  # Ronin es POSA
        except ImportError:
            log.error("web3.py no está instalado. `pip install web3`")
            return False

        self._w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 15}))
        # Ronin requiere el middleware POA.
        self._w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self._w3.is_connected():
            log.error("No se pudo conectar al RPC de Ronin: %s", self.rpc_url)
            return False

        if self.release_contract:
            self._contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.release_contract),
                abi=RELEASE_ABI,
            )
        return True

    # -------------------------------------------------------------------
    def build_release_tx(self, axie_id: int) -> Optional[Dict[str, Any]]:
        """Construye la tx sin firmarla (útil para simulación / eth_call)."""
        if not self._ensure_web3() or self._contract is None:
            return None
        from web3 import Web3

        wallet = Web3.to_checksum_address(self.wallet)
        nonce = self._w3.eth.get_transaction_count(wallet)
        gas_price = self._w3.eth.gas_price

        return self._contract.functions.releaseAxie(int(axie_id)).build_transaction({
            "chainId": self.chain_id,
            "from": wallet,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": 300_000,   # ajustar con estimate_gas en prod
        })

    # -------------------------------------------------------------------
    def release_axie(self, axie_id: int) -> Optional[str]:
        """
        Firma y envía la tx de release. Si `dry_run=True`, solo loguea
        la tx que se enviaría.
        """
        tx = self.build_release_tx(axie_id)
        if tx is None:
            return None

        if self.dry_run:
            log.info("[DRY-RUN] releaseAxie(%s): %s", axie_id, tx)
            return None

        if not self.private_key:
            log.error("RONIN_PRIVATE_KEY vacío; no se puede firmar.")
            return None

        from web3 import Web3
        w3 = self._w3
        signed = w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        log.info("Release enviada: %s", tx_hash.hex())
        return tx_hash.hex()
