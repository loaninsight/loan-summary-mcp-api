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

## 2. User activity (marketing charts)

Active users and new adopters for Daily / Weekly / Monthly series.

```
GET /api/users/activity
```

```bash
curl https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com/api/users/activity
```

`Daily` is Sunday–Saturday (7 points). `Weekly` / `Monthly` are the first 12 ISO weeks and calendar months of the current year.

## 3. System stats (hero tiles)

```
GET /api/system/stats
```

```bash
curl https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com/api/system/stats
```

| Field | Description |
|---|---|
| `stats.activeUsers` | Distinct `spring_session.principal_name` |
| `stats.calculations` | Rows in `loanapp` |
| `stats.loansAnalyzed` | Rows in `loan` |
| `stats.topLoanCount` / `topLoanName` | Most common `loan.loan_type` |

## 4. Loan summary (main test endpoint)

Returns all existing loans + summary totals for a user.

```
GET /api/loans/summary?email=USER_EMAIL
GET /api/loans/summary?email=all
```

Use `email=all` on the non-authenticated marketing site to aggregate every loan in the database.

```bash
curl "https://loan-summary-mcp-api-5f08d324cefc.herokuapp.com/api/loans/summary?email=all"
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

## Required Heroku config

| Variable | Value |
|---|---|
| `LOANCALCULATOR_BASE_URL` | `https://ayushiloancalculatorapp.herokuapp.com` |
| `MICROSERVICE_HOST_URL` | `https://ayushiloancalculatorappws.herokuapp.com` |
| `MICROSERVICE_GUEST_USERNAME` | `guestMachineUser@ayushisoftware.com` |
| `MICROSERVICE_GUEST_PASSWORD` | guest machine password (must be set on Heroku) |
| `TICKER_ML_API_ENDPOINT` | `https://ml-rec-74e65f711ec7.herokuapp.com` |
| `CORS_ALLOW_ORIGINS` | optional; defaults include `https://www.loaninsight.online` |

## Browser / React usage

Marketing site charts call:

```
GET /api/loans/summary?email=all
GET /api/users/activity
GET /api/system/stats
```

CORS is enabled for `www.loaninsight.online` so the React frontend can `fetch` this endpoint from the browser (same pattern as `LoanWebService.java` HTTP calls, but client-side).

## GitHub repo

https://github.com/loaninsight/loan-summary-mcp-api
