# Axie Statistical Arbitrage Bot

Bot de arbitraje estadístico entre el **precio de floor de Axies** en el Marketplace y el **valor esperado de los Mementos** obtenidos al hacer *release* on-chain.

## Arquitectura

```
                 ┌────────────────────────┐
                 │  Sky Mavis GraphQL API │
                 └─────────────┬──────────┘
                               │  (GetAxieBriefList)
                               ▼
┌────────────────┐   ┌───────────────────┐   ┌─────────────────┐
│ YieldCalc      │◄──┤ graphql_client    │──►│ ArbitrageEngine │
│ (triangular    │   │ AxieListing       │   │ Monte Carlo     │
│  dist. por     │   └───────────────────┘   │ P(profit), VaR  │
│  clase/parts/  │                           └────────┬────────┘
│  level)        │                                    │
└────────┬───────┘                                    │
         │                                            ▼
         │                               ┌──────────────────────┐
         ▼                               │  Tabla + veredicto   │
┌────────────────┐                       │  EJECUTAR / SKIP     │
│ KatanaOracle   │                       └──────────┬───────────┘
│ (getAmountsOut)│                                  │
└────────────────┘                                  ▼
                                          ┌──────────────────────┐
                                          │   RoninSigner        │
                                          │   (web3.py, dry-run) │
                                          └──────────────────────┘
```

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Endpoints, constantes, `SearchCriteria`, carga `.env`. |
| `graphql_client.py` | Queries GraphQL + `AxieListing` tipado. |
| `price_oracle.py` | Precio de Mementos vía Katana `getAmountsOut`. |
| `yield_calculator.py` | Distribución triangular de drops (base + parts + level + breed). |
| `arbitrage_engine.py` | Monte Carlo, P(win), E[PnL], VaR95, veredicto. |
| `ronin_signer.py` | Stub web3.py para firmar `releaseAxie(uint256)`. |
| `main.py` | Loop principal, CLI, tabla, ejecución. |

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edita .env con tu SKYMAVIS_API_KEY
```

## Ejecución

```bash
# Un tick, clase Beast, dry-run:
python main.py --classes Beast

# Loop cada 60s, varias clases:
python main.py --loop 60 --classes Beast Aquatic Plant --limit 50

# Producción (¡firma real!):
python main.py --live --classes Beast
```

## Modelo de yield (editable en `yield_calculator.py`)

```
drop ~ Triangular(min, mode, max)
mode = (base_class + matching_parts * 1.5) * (1 + 0.22·ln(1+(level-1))) · (1 - 0.01·breed_count)
```

El *Monte Carlo* añade ruido log-normal al precio de Memento para modelar slippage.

## Filtros de ejecución

Un Axie se marca **EJECUTAR** sólo si:

1. `P(PnL > 0) ≥ PROFIT_PROBABILITY_THRESHOLD` (default 60%).
2. `E[PnL] > 0`.

Ambas condiciones evitan el típico falso positivo de "probabilidad alta, retorno bajo".

## Seguridad

- `RONIN_PRIVATE_KEY` **nunca** debe vivir en el código ni en un `.env` comiteado. Usa AWS KMS, GCP Secret Manager o un HSM.
- El signer arranca en `dry_run=True`. Activar `--live` exige pasar la flag explícita.
- El contrato de release debe ser verificado on-chain antes de firmar.
- Recomendado: añadir un *circuit breaker* por drawdown diario y un whitelist de contratos.

## Limitaciones conocidas

- El schema GraphQL del Marketplace cambia; si aparece `Cannot query field`, ajusta `FRAGMENT_AXIE` en `graphql_client.py`.
- Las direcciones de Memento (`MEMENTO_TOKENS`) son placeholders hasta que las calibres on-chain.
- El precio de ETH/USD se pasa por CLI (`--eth-usd`). En producción conéctalo a Chainlink o a la API de CoinGecko.
- No incluye compra en el marketplace (`settleAuction`): ese paso va entre la detección y el `release_axie()`.
