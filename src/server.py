# Add lifespan support for startup/shutdown with strong typing
import json
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Hashable, Literal, Optional

import nest_asyncio  # type: ignore
from mcp.server.fastmcp import Context, FastMCP

from edgar_sec.client import EdgarClient, EdgarError
from edgar_sec.utils.decorators import process_error
from edgar_sec.utils.serializer import filing_serializer

# This is necessary as edgartools starts its own event loop
try:
    nest_asyncio.apply()
except Exception as e:
    raise EdgarError(f"Error during nest_asyncio.apply(): {str(e)}", 500) from e

# Global variable to store the client
client_instance: Optional[EdgarClient] = None


@dataclass
class AppContext:
    """Application context for the MCP server"""

    client: EdgarClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context

    Args:
        server (FastMCP): The MCP server instance

    Returns:
        AsyncIterator[AppContext]: The application context
    """
    global client_instance

    try:
        # Initialize on startup
        client_instance = EdgarClient()
        context = AppContext(client=client_instance)
        print("EDGAR client initialized successfully", file=sys.stderr)
        yield context
    finally:
        # Cleanup on shutdown
        pass


# Initialize FastMCP server with lifespan
mcp = FastMCP("edgar-sec", lifespan=app_lifespan)


@process_error
@mcp.resource(uri="config://valid_cik_ticker_data")
def get_valid_cik_ticker() -> str:
    """Get a list of valid CIK and company tickers from the SEC EDGAR database.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: A JSON string representation of the valid CIK and company tickers.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(client_instance.get_valid_cik_ticker_data(), default=str)


@process_error
@mcp.resource(uri="config://valid_forms")
def get_valid_forms() -> str:
    """Get a list of valid forms from the SEC EDGAR database.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: A JSON string representation of the valid forms.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(client_instance.get_valid_forms_data(), default=str)


# Access type-safe lifespan context in tools
@process_error
@mcp.tool()
def get_company_info(ctx: Context, entity_identifier: str) -> str:
    """Get comprehensive company information from the SEC EDGAR database
    through a supplied entity identifier (CIK or ticker).

    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: A JSON string representation of the company information.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(client_instance.get_company_info(entity_identifier), default=str)


@process_error
@mcp.tool()
def get_company_name(ctx: Context, entity_identifier: str) -> str:
    """Get the company name from the SEC EDGAR database through a supplied entity identifier
    (CIK or ticker).

    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: The company name.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(client_instance.get_company_name(entity_identifier), default=str)


@process_error
@mcp.tool()
def get_company_tickers(ctx: Context, entity_identifier: str) -> str:
    """Get the company tickers from the SEC EDGAR database through a supplied entity identifier
    (CIK or ticker).

    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: A JSON string representation of the company tickers.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(client_instance.get_company_tickers(entity_identifier), default=str)


@process_error
@mcp.tool()
def get_company_sic_description(ctx: Context, entity_identifier: str) -> str:
    """Get the company SIC description from the SEC EDGAR database through a supplied entity
    identifier (CIK or ticker).

    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: The company SIC description.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(client_instance.get_company_sic_description(entity_identifier), default=str)


@lru_cache(maxsize=1)
def _fetch_company_filings(entity_identifier: str) -> list[dict[Hashable, Any]]:
    """Fetch and cache all company filings for a given entity.

    This cache never expires.

    Args:
        entity_identifier (str): The entity identifier (CIK or ticker)

    Returns:
        list[dict[Hashable, Any]]: List of filing dictionaries

    Raises:
        EdgarError: If the client is not initialized or the request fails
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return client_instance.get_company_filings(entity_identifier)


@process_error
@mcp.tool()
def get_company_filings(
    ctx: Context, entity_identifier: str, page: int = 1, page_size: int = 100
) -> str:
    """Get company filings from the SEC EDGAR database through a supplied entity identifier
    (CIK or ticker) with pagination support.

    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.
        page (int): The page number to retrieve (starting from 1). Defaults to 1.
        page_size (int): The number of items per page. Defaults to 100.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: A JSON string representation of the paginated company filings with total count.
    """
    # Fetch all filings using the cached function
    all_filings = _fetch_company_filings(entity_identifier)

    # Calculate pagination values
    total_filings = len(all_filings)
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_filings)

    # Get the slice of filings for the requested page
    paginated_filings = all_filings[start_idx:end_idx]

    # Return both the paginated results and pagination metadata
    result = {
        "filings": paginated_filings,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_filings,
            "total_pages": (total_filings + page_size - 1) // page_size,
        },
    }

    return json.dumps(result, default=filing_serializer)


@process_error
@mcp.tool()
def get_latest_financials(
    ctx: Context,
    entity_identifier: str,
    table_type: Literal[
        "balance_sheet",
        "income_statement",
        "cash_flow_statement",
        "comprehensive_income",
        "equity",
        "cover_page",
    ],
    annual: bool = True,
) -> str:
    """Get the latest financials from the SEC EDGAR database through a supplied entity identifier
    (CIK or ticker).
    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.
        table_type (Literal["balance_sheet", "income_statement", "cash_flow_statement",
            "comprehensive_income", "equity", "cover_page"]): The type of financial table to get.
        annual (bool): Whether to get the annual financials. Defaults to True.

    Raises:
        EdgarError: If the request fails

    Returns:
        str: A JSON string representation of the company financials.
    """
    if client_instance is None:
        raise EdgarError("EDGAR client not initialized", 503)
    return json.dumps(
        client_instance.get_latest_financials(entity_identifier, table_type, annual),
        default=str,
    )


@mcp.prompt()
def get_latest_financials_prompt(
    entity_identifier: str,
    table_type: Literal[
        "balance_sheet",
        "income_statement",
        "cash_flow_statement",
        "comprehensive_income",
        "equity",
        "cover_page",
    ],
) -> str:
    """Get the latest financials from the SEC EDGAR database through a supplied entity identifier
    (CIK or ticker).
    """
    return f"""
    You are a helpful assistant that can get the latest financials from the SEC EDGAR database
    through a supplied entity identifier (CIK or ticker). Follow the steps below to get the latest 
    financials.

    Args:
        entity_identifier (str): The entity identifier to search for. This can be a CIK number
            (10 digits with leading zeros) or a company ticker.
        table_type (Literal["balance_sheet", "income_statement", "cash_flow_statement",
            "comprehensive_income", "equity", "cover_page"]): The type of financial table to get.
        annual (bool): Whether to get the annual financials. Defaults to True.

    Returns:
        str: A JSON string representation of the company financials.

    Steps:

    1. Check if the latest financials are annual or quarterly. Do this by using tool 
        get_company_filings to get the latest filings and then looking at the latest filing which 
        has isXBRL set to True. The data is sorted by filing date, so the latest filing is the 
        first one. Stop whenever you found the first filing with isXBRL set to True. If that 
        filing has Form 10-K or 10-K/A it is annual (annual=True). Otherwise it is interim 
        (annual=False).
    2. Use tool get_latest_financials to get the latest financials for {entity_identifier},
        table_type {table_type} and annual from step 1.
    3. Display the {table_type} in tabular format.
    """
