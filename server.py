import os
from collections import defaultdict
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import psycopg2
from fastmcp import FastMCP
from psycopg2.extras import RealDictCursor
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

LOANCALCULATOR_BASE_URL = os.getenv(
    "LOANCALCULATOR_BASE_URL",
    "https://ayushiloancalculatorapp.herokuapp.com",
).rstrip("/")
MICROSERVICE_HOST_URL = os.getenv(
    "MICROSERVICE_HOST_URL",
    "https://ayushiloancalculatorappws.herokuapp.com",
).rstrip("/")
TICKER_ML_API_ENDPOINT = os.getenv(
    "TICKER_ML_API_ENDPOINT",
    "https://ml-rec-74e65f711ec7.herokuapp.com",
).rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MICROSERVICE_GUEST_USERNAME = os.getenv(
    "MICROSERVICE_GUEST_USERNAME",
    "guestMachineUser@ayushisoftware.com",
)
MICROSERVICE_GUEST_PASSWORD = os.getenv("MICROSERVICE_GUEST_PASSWORD", "")

LOAN_QUERY = """
SELECT
    loan_id,
    loan_amt,
    apr,
    int_rate,
    mthly_paymt,
    num_of_yrs,
    loan_type,
    loan_denom,
    email,
    region,
    vin,
    start_date,
    lender,
    st,
    username
FROM loan
WHERE lower(email) = lower(%s)
ORDER BY loan_id
"""

mcp = FastMCP(
    "Loan Calculator MCP",
    instructions=(
        "MCP server for the LoanCalculator website. Use these tools to check site "
        "health, fetch loan summaries, call loan microservices, and fetch ticker data."
    ),
)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30.0, follow_redirects=True)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _build_summary(loans: list[dict[str, Any]]) -> dict[str, Any]:
    if not loans:
        return {
            "totalAmount": 0.0,
            "monthlyAmount": 0.0,
            "loanCount": 0,
            "maximumNumOfYear": 0,
            "region": None,
            "denomination": None,
            "message": "No loans found for this user.",
        }

    total_amount = sum(float(loan.get("amount") or 0) for loan in loans)
    monthly_amount = sum(float(loan.get("monthlyPayment") or 0) for loan in loans)
    max_years = max(int(loan.get("numberOfYears") or 0) for loan in loans)

    return {
        "totalAmount": round(total_amount, 2),
        "monthlyAmount": round(monthly_amount, 2),
        "loanCount": len(loans),
        "maximumNumOfYear": max_years,
        "region": loans[0].get("region"),
        "denomination": loans[0].get("loanDenomination"),
    }


def _build_category_summary(loans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"loanType": "", "count": 0, "totalAmount": 0.0}
    )
    for loan in loans:
        loan_type = loan.get("loanType") or "Unknown"
        entry = grouped[loan_type]
        entry["loanType"] = loan_type
        entry["count"] += 1
        entry["totalAmount"] = round(
            float(entry["totalAmount"]) + float(loan.get("amount") or 0),
            2,
        )
    return list(grouped.values())


def fetch_loans_summary_from_db(email: str) -> dict[str, Any]:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured on the server")

    with psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor) as connection:
        with connection.cursor() as cursor:
            cursor.execute(LOAN_QUERY, (email,))
            rows = cursor.fetchall()

    loans: list[dict[str, Any]] = []
    for row in rows:
        loans.append(
            {
                "loanId": row["loan_id"],
                "name": row.get("username"),
                "lender": row.get("lender"),
                "state": row.get("st"),
                "region": row.get("region"),
                "amount": float(row.get("loan_amt") or 0),
                "apr": float(row.get("apr") or 0),
                "interestRate": float(row.get("int_rate") or 0),
                "monthlyPayment": float(row.get("mthly_paymt") or 0),
                "numberOfYears": int(row.get("num_of_yrs") or 0),
                "loanType": row.get("loan_type"),
                "loanDenomination": row.get("loan_denom"),
                "email": row.get("email"),
                "vin": row.get("vin"),
                "startDate": _serialize_value(row.get("start_date")),
            }
        )

    return {
        "success": True,
        "email": email,
        "loanCount": len(loans),
        "loans": loans,
        "categorySummary": _build_category_summary(loans),
        "summary": _build_summary(loans),
        "source": "postgres-database",
    }


async def _microservice_login(client: httpx.AsyncClient) -> str:
    if not MICROSERVICE_GUEST_PASSWORD:
        raise RuntimeError("MICROSERVICE_GUEST_PASSWORD is not configured on the server")

    response = await client.post(
        f"{MICROSERVICE_HOST_URL}/login/login",
        data={
            "username": MICROSERVICE_GUEST_USERNAME,
            "password": MICROSERVICE_GUEST_PASSWORD,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    token = response.headers.get("x-auth-token") or response.headers.get("X-Auth-Token")
    if not token:
        raise RuntimeError("Microservice login succeeded but no X-Auth-Token was returned")
    return token


async def fetch_loans_summary(email: str) -> dict[str, Any]:
    email = email.strip()
    if not email:
        raise ValueError("email is required")

    if DATABASE_URL:
        return fetch_loans_summary_from_db(email)

    async with _client() as client:
        token = await _microservice_login(client)
        graph_response = await client.get(
            f"{MICROSERVICE_HOST_URL}/graph/graph",
            params={"userEmail": email},
            headers={"x-auth-token": token},
        )
        graph_response.raise_for_status()
        graph_data = graph_response.json()

    loan_table = graph_data.get("loanTable") or []
    loan_graph = graph_data.get("loanGraph") or []
    total_amount = sum(float(item.get("amount", 0) or 0) for item in loan_table)

    return {
        "success": True,
        "email": email,
        "loanCount": len(loan_table),
        "loans": loan_table,
        "categorySummary": [
            {
                "loanType": item.get("loanName"),
                "totalAmount": item.get("amount"),
                "loanPercentage": item.get("loanPercentage"),
                "loanDenomination": item.get("loanDenomination"),
            }
            for item in loan_graph
        ],
        "summary": {
            "totalAmount": total_amount,
            "loanCount": len(loan_table),
            "message": "Summary generated from graph microservice",
        },
        "source": "graph-microservice",
    }


@mcp.tool()
async def check_website_health() -> dict[str, Any]:
    """Check whether the main LoanCalculator website is reachable."""
    async with _client() as client:
        response = await client.get(LOANCALCULATOR_BASE_URL)
        return {
            "url": LOANCALCULATOR_BASE_URL,
            "status_code": response.status_code,
            "reachable": response.status_code < 500,
        }


@mcp.tool()
async def get_loans_summary(email: str) -> dict[str, Any]:
    """Return a summary of all existing loans for a user."""
    return await fetch_loans_summary(email)


@mcp.tool()
async def calculate_loan(
    loan_amount: float,
    apr: float,
    lender: str,
    state: str,
    region: str,
    number_of_years: int,
    loan_type: str,
    name: str,
) -> dict[str, Any]:
    """Calculate a loan using the LoanCalculator microservice."""
    async with _client() as client:
        token = await _microservice_login(client)
        response = await client.get(
            f"{MICROSERVICE_HOST_URL}/calculate/calculateloan",
            params={
                "airVal": apr,
                "lender": lender,
                "loanAmt": loan_amount,
                "state": state,
                "region": region,
                "numOfYears": number_of_years,
                "loanType": loan_type,
                "name": name,
            },
            headers={"x-auth-token": token},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_ticker_feed(user_id: str = "") -> dict[str, Any]:
    """Fetch public or personalized ticker recommendations from the ML service."""
    async with _client() as client:
        if user_id.strip():
            url = f"{TICKER_ML_API_ENDPOINT}/feed/{user_id.strip()}"
        else:
            url = f"{TICKER_ML_API_ENDPOINT}/feed/public"
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def health(_: Request) -> JSONResponse:
    database_configured = bool(DATABASE_URL)
    database_host = None
    if database_configured:
        database_host = urlparse(DATABASE_URL).hostname

    return JSONResponse(
        {
            "status": "ok",
            "service": "loan-summary-mcp-api",
            "endpoints": {
                "health": "/health",
                "loan_summary": "/api/loans/summary?email=USER_EMAIL",
                "mcp": "/mcp",
            },
            "website": LOANCALCULATOR_BASE_URL,
            "databaseConfigured": database_configured,
            "databaseHost": database_host,
        }
    )


async def loan_summary_api(request: Request) -> JSONResponse:
    email = request.query_params.get("email", "").strip()
    if not email:
        return JSONResponse(
            {"success": False, "message": "email query parameter is required"},
            status_code=400,
        )
    try:
        payload = await fetch_loans_summary(email)
        return JSONResponse(payload)
    except ValueError as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=400)
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            {
                "success": False,
                "message": f"Upstream service error: {exc.response.status_code}",
            },
            status_code=502,
        )
    except Exception as exc:
        return JSONResponse(
            {"success": False, "message": str(exc)},
            status_code=500,
        )


mcp_app = mcp.http_app(path="/mcp", transport="streamable-http", stateless_http=True)
app = Starlette(
    routes=[
        Route("/", health),
        Route("/health", health),
        Route("/api/loans/summary", loan_summary_api, methods=["GET"]),
        Mount("/", app=mcp_app),
    ]
)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
