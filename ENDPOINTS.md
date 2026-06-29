# Endpoints — Loan Summary MCP Service

This is a **separate repo/service**. It does not modify `loancalculatorapp`.

## Base URL

`https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com`

## 1. Health check

```
GET /health
```

```bash
curl https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com/health
```

## 2. Loan summary (main test endpoint)

Returns all existing loans + summary totals for a user.

```
GET /api/loans/summary?email=USER_EMAIL
```

```bash
curl "https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com/api/loans/summary?email=guestMachineUser@ayushisoftware.com"
```

### Response fields

| Field | Description |
|---|---|
| `success` | `true` if the call worked |
| `email` | User email queried |
| `loanCount` | Number of loans found |
| `loans` | List of loan records from graph service |
| `categorySummary` | Totals grouped by loan type |
| `summary` | Aggregated totals |
| `source` | Always `graph-microservice` |

## 3. MCP endpoint (for AI clients)

```
POST /mcp
```

Cursor / Claude MCP URL:

```
https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com/mcp
```

MCP tools available:

- `get_loans_summary`
- `calculate_loan`
- `check_website_health`
- `get_ticker_feed`

## Required Heroku config

| Variable | Value |
|---|---|
| `LOANCALCULATOR_BASE_URL` | `https://ayushiloancalculatorapp.herokuapp.com` |
| `MICROSERVICE_HOST_URL` | `https://ayushiloancalculatorappws.herokuapp.com` |
| `MICROSERVICE_GUEST_USERNAME` | `guestMachineUser@ayushisoftware.com` |
| `MICROSERVICE_GUEST_PASSWORD` | guest machine password (must be set on Heroku) |
| `TICKER_ML_API_ENDPOINT` | `https://ml-rec-74e65f711ec7.herokuapp.com` |

## GitHub repo

https://github.com/loaninsight/loan-summary-mcp-api
