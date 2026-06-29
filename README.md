# loan-summary-mcp-api

Standalone MCP + REST API service for LoanCalculator loan summaries.

This repo is **separate from** `loancalculatorapp`. It calls the existing microservices only.

## Live endpoints

Base URL: `https://loan-summary-mcp-api.herokuapp.com`

| Purpose | Method | URL |
|---|---|---|
| Health check | GET | `/health` |
| Loan summary | GET | `/api/loans/summary?email=USER_EMAIL` |
| MCP endpoint | POST | `/mcp` |

See [ENDPOINTS.md](./ENDPOINTS.md) for Gagan's testing guide.

## Environment variables (Heroku)

```bash
heroku config:set \
  LOANCALCULATOR_BASE_URL=https://ayushiloancalculatorapp.herokuapp.com \
  MICROSERVICE_HOST_URL=https://ayushiloancalculatorappws.herokuapp.com \
  TICKER_ML_API_ENDPOINT=https://ml-rec-74e65f711ec7.herokuapp.com \
  MICROSERVICE_GUEST_USERNAME=guestMachineUser@ayushisoftware.com \
  MICROSERVICE_GUEST_PASSWORD='YOUR_GUEST_PASSWORD' \
  -a APP_NAME
```

## Cursor MCP config

```json
{
  "mcpServers": {
    "loan-calculator": {
      "url": "https://APP_NAME.herokuapp.com/mcp"
    }
  }
}
```

## Deploy

```bash
git push heroku main
```

Or run:

```bash
./deploy-heroku.sh
```
