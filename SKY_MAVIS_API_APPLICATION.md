# Sky Mavis API Application Form

## Información de Solicitud para API Permissions

### Project Information

**Project Name:** ArbiBot

**Website URL:** https://jonathankozur.github.io/AxieMarket/

**GitHub Repository:** https://github.com/jonathankozur/AxieMarket

**Description:**
ArbiBot is an open-source statistical arbitrage bot designed for the Axie Infinity ecosystem. It identifies mispricings between marketplace axies and their implied value through release mechanics, enabling profitable trading strategies grounded in quantitative analysis.

The bot combines real-time market data, probabilistic yield modeling, and risk-adjusted execution to discover and capitalize on temporary inefficiencies in the marketplace—while maintaining strict risk controls and transparency.

### Project Type

**Type:** Developer Tool / Trading Bot / DeFi Application

**Category:** Marketplace Analysis & Arbitrage

### Legal Documents

- **Terms of Service:** https://jonathankozur.github.io/AxieMarket/terms.html
- **Privacy Policy:** https://jonathankozur.github.io/AxieMarket/privacy.html

### Contact Information

**Contact Email:** jonathankozur@gmail.com

**GitHub Profile:** https://github.com/jonathankozur

### Project Logo

**Logo File:** logo.svg (300×300 pixels)

**Description:** Professional logo featuring currency symbols (€ and $) with an upward arrow representing profit/growth, using blue gradient colors consistent with modern fintech branding.

---

## API Integration Requirements

ArbiBot requires access to the following Sky Mavis APIs:

1. **Axie Marketplace GraphQL API**
   - Endpoint: `https://graphql-gateway.axieinfinity.com/graphql`
   - Queries: `GetAxieBriefList`, `GetAxieDetail`
   - Purpose: Fetch marketplace floor prices and axie details

2. **Release/Breeding System**
   - Purpose: Calculate expected yield from breeding releases
   - Frequency: Real-time analysis

3. **Pricing & Memento Tokens**
   - Purpose: Track memento token values and ETH/RON conversion rates

---

## Features

- Real-time marketplace floor price monitoring
- Advanced filtering by class, breed count, level, and parts
- Probabilistic yield modeling using Monte Carlo simulations
- Multi-source price oracle integration
- Risk-adjusted execution with VaR metrics
- Ronin blockchain integration for transaction signing
- Comprehensive trade reporting and analytics
- Open-source MIT License

---

## Security & Compliance

✅ API key management via environment variables (.env file)
✅ No private key exposure in public repositories
✅ Clear Terms of Service and Privacy Policy
✅ Compliance with Axie Infinity marketplace terms
✅ No malicious intent or market manipulation
✅ Transparent, auditable code

---

## Use Cases

1. **Arbitrage Analysis:** Identify profitable trading opportunities
2. **Yield Estimation:** Calculate expected returns from breeding mechanics
3. **Risk Management:** Quantify probability-adjusted P&L
4. **Market Intelligence:** Track floor price trends and market efficiency
5. **Portfolio Optimization:** Algorithm-driven trading strategy

---

## Documentation

Full documentation and source code available at: https://github.com/jonathankozur/AxieMarket

---

*This application was prepared on April 24, 2026*
