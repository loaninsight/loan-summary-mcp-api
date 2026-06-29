#!/usr/bin/env bash
set -euo pipefail

APP=loan-summary-mcp-api
WEBSITE=https://ayushiloancalculatorapp.herokuapp.com
MICROSERVICE=https://ayushiloancalculatorappws.herokuapp.com
ML_ENDPOINT=https://ml-rec-74e65f711ec7.herokuapp.com

cd "$(dirname "$0")"

echo "==> Heroku auth"
heroku auth:whoami

if ! heroku apps:info -a "$APP" >/dev/null 2>&1; then
  echo "==> Creating Heroku app: $APP"
  heroku create "$APP"
fi

echo "==> Heroku remote"
heroku git:remote -a "$APP" 2>/dev/null || git remote add heroku "https://git.heroku.com/${APP}.git"

echo "==> Config"
heroku config:set \
  "LOANCALCULATOR_BASE_URL=${WEBSITE}" \
  "MICROSERVICE_HOST_URL=${MICROSERVICE}" \
  "TICKER_ML_API_ENDPOINT=${ML_ENDPOINT}" \
  "MICROSERVICE_GUEST_USERNAME=guestMachineUser@ayushisoftware.com" \
  -a "$APP"

if [ -z "${MICROSERVICE_GUEST_PASSWORD:-}" ]; then
  echo "Set MICROSERVICE_GUEST_PASSWORD env var locally before deploy, then run:"
  echo "heroku config:set MICROSERVICE_GUEST_PASSWORD='...' -a $APP"
else
  heroku config:set "MICROSERVICE_GUEST_PASSWORD=${MICROSERVICE_GUEST_PASSWORD}" -a "$APP"
fi

echo "==> Deploy"
git push heroku main

echo "==> Smoke test"
curl -sS "https://${APP}.herokuapp.com/health"
echo
echo "Loan summary: https://${APP}.herokuapp.com/api/loans/summary?email=guestMachineUser@ayushisoftware.com"
