import os
from typing import Any

import httpx
from fastmcp import FastMCP
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
MICROSERVICE_GUEST_USERNAME = os.getenv(
    "MICROSERVICE_GUEST_USERNAME",
    "guestMachineUser@ayushisoftware.com",
)
MICROSERVICE_GUEST_PASSWORD = os.getenv("MICROSERVICE_GUEST_PASSWORD", "")

mcp = FastMCP(
    "Loan Calculator MCP",
    instructions=(
        "MCP server for the LoanCalculator website. Use these tools to check site "
        "health, fetch loan summaries, call loan microservices, and fetch ticker data."
    ),
)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30.0, follow_redirects=True)


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
    """Fetch loan summary from the main website API, with graph-service fallback."""
    email = email.strip()
    if not email:
        raise ValueError("email is required")

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
        category_summary = []
        for item in loan_graph:
            category_summary.append(
                {
                    "loanType": item.get("loanName"),
                    "totalAmount": item.get("amount"),
                    "loanPercentage": item.get("loanPercentage"),
                    "loanDenomination": item.get("loanDenomination"),
                }
            )

        return {
            "success": True,
            "email": email,
            "loanCount": len(loan_table),
            "loans": loan_table,
            "categorySummary": category_summary,
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
    return JSONResponse(
        {
            "status": "ok",
            "service": "python-mcp-server",
            "endpoints": {
                "health": "/health",
                "loan_summary": "/api/loans/summary?email=USER_EMAIL",
                "mcp": "/mcp",
            },
            "website": LOANCALCULATOR_BASE_URL,
            "microservice": MICROSERVICE_HOST_URL,
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
