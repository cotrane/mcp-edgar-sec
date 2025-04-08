"""Tests for the server module."""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mcp.server.fastmcp import Context, FastMCP

from edgar_sec.client import EdgarClient, EdgarError
from server import (
    _fetch_company_filings,
    app_lifespan,
    get_company_filings,
    get_company_info,
    get_company_name,
    get_company_sic_description,
    get_company_tickers,
    get_latest_financials,
    get_valid_cik_ticker,
    get_valid_forms,
)

# Add path to sys.path if needed for testing
sys.path.insert(0, "src")


@pytest.fixture
def mock_context() -> Context:
    """Create a mock MCP Context."""
    return MagicMock(spec=Context)


@pytest.fixture
def mock_edgar_client() -> MagicMock:
    """Create a mock Edgar client."""
    mock_client = MagicMock(spec=EdgarClient)

    # Set up common return values for methods
    mock_client.get_valid_cik_ticker_data.return_value = [
        {"cik": "0001234567890", "ticker": "TEST", "title": "Test Company"}
    ]
    mock_client.get_valid_forms_data.return_value = ["10-K", "10-Q", "8-K"]
    mock_client.get_company_info.return_value = {
        "cik": "0001234567890",
        "name": "Test Company",
        "tickers": ["TEST"],
    }
    mock_client.get_company_name.return_value = "Test Company"
    mock_client.get_company_tickers.return_value = ["TEST"]
    mock_client.get_company_sic_description.return_value = "Test Industry"
    mock_client.get_company_filings.return_value = [
        {"form": "10-K", "filing_date": "2023-01-01", "accession_number": "123456789"}
    ]
    mock_client.get_latest_financials.return_value = [{"label": "Total Assets", "value": 1000000}]

    return mock_client


@pytest.fixture
def patch_global_client(mock_edgar_client: MagicMock) -> Generator[MagicMock, None, None]:
    """Patch the global client_instance in server module."""
    with patch("server.client_instance", mock_edgar_client) as mock_client_instance:
        yield mock_client_instance


@pytest.fixture
def mock_mcp_server() -> MagicMock:
    """Create a mock FastMCP server."""
    return MagicMock(spec=FastMCP)


@pytest.mark.asyncio
async def test_app_lifespan_success() -> None:
    """Test app_lifespan when initialization succeeds."""
    mock_server = MagicMock()

    # Patch the EdgarClient constructor and client_instance
    with (
        patch("server.EdgarClient") as mock_client_class,
        patch("server.client_instance", None),
        patch("server.print") as mock_print,
    ):
        # Configure the mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Use the context manager
        async with app_lifespan(mock_server) as context:
            # Verify that the client was created
            assert context.client == mock_client
            mock_client_class.assert_called_once()
            mock_print.assert_called_with(
                "EDGAR client initialized successfully", file=mock_print.call_args[1]["file"]
            )


def test_get_valid_cik_ticker(patch_global_client: None, mock_edgar_client: MagicMock) -> None:
    """Test get_valid_cik_ticker endpoint."""
    # Call the endpoint
    result = get_valid_cik_ticker()

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, list)
    assert data[0]["ticker"] == "TEST"

    # Verify the client method was called
    mock_edgar_client.get_valid_cik_ticker_data.assert_called_once()


def test_get_valid_cik_ticker_no_client() -> None:
    """Test get_valid_cik_ticker endpoint with no client initialized."""
    # Patch the global client to be None
    with patch("server.client_instance", None):
        # Call the endpoint and verify it raises an EdgarError
        response = get_valid_cik_ticker()
        assert response == json.dumps(
            {"error": True, "message": "EDGAR client not initialized", "code": 503, "traceback": ""}
        )


def test_get_valid_forms(patch_global_client: None, mock_edgar_client: MagicMock) -> None:
    """Test get_valid_forms endpoint."""
    # Call the endpoint
    result = get_valid_forms()

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, list)
    assert "10-K" in data

    # Verify the client method was called
    mock_edgar_client.get_valid_forms_data.assert_called_once()


def test_get_valid_forms_no_client() -> None:
    """Test get_valid_forms endpoint with no client initialized."""
    # Patch the global client to be None
    with patch("server.client_instance", None):
        # Call the endpoint and verify it raises an EdgarError
        response = get_valid_forms()
        assert response == json.dumps(
            {"error": True, "message": "EDGAR client not initialized", "code": 503, "traceback": ""}
        )


def test_get_company_info(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_company_info endpoint."""
    # Call the endpoint
    result = get_company_info(mock_context, "0001234567890")

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert data["name"] == "Test Company"
    assert data["tickers"] == ["TEST"]

    # Verify the client method was called with the correct argument
    mock_edgar_client.get_company_info.assert_called_once_with("0001234567890")


def test_get_company_info_no_client(mock_context: Context) -> None:
    """Test get_company_info endpoint with no client initialized."""
    # Patch the global client to be None
    with patch("server.client_instance", None):
        # Call the endpoint and verify it raises an EdgarError
        response = get_company_info(mock_context, "0001234567890")
        assert response == json.dumps(
            {"error": True, "message": "EDGAR client not initialized", "code": 503, "traceback": ""}
        )


def test_get_company_name(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_company_name endpoint."""
    # Call the endpoint
    result = get_company_name(mock_context, "0001234567890")

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert data == "Test Company"

    # Verify the client method was called with the correct argument
    mock_edgar_client.get_company_name.assert_called_once_with("0001234567890")


def test_get_company_name_no_client(mock_context: Context) -> None:
    """Test get_company_name endpoint with no client initialized."""
    # Patch the global client to be None
    with patch("server.client_instance", None):
        # Call the endpoint and verify it raises an EdgarError
        response = get_company_name(mock_context, "0001234567890")
        assert response == json.dumps(
            {"error": True, "message": "EDGAR client not initialized", "code": 503, "traceback": ""}
        )


def test_get_company_tickers(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_company_tickers endpoint."""
    # Call the endpoint
    result = get_company_tickers(mock_context, "0001234567890")

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert data == ["TEST"]

    # Verify the client method was called with the correct argument
    mock_edgar_client.get_company_tickers.assert_called_once_with("0001234567890")


def test_get_company_tickers_no_client(mock_context: Context) -> None:
    """Test get_company_tickers endpoint with no client initialized."""
    # Call the endpoint
    response = get_company_tickers(mock_context, "0001234567890")
    assert response == json.dumps(
        {"error": True, "message": "EDGAR client not initialized", "code": 503, "traceback": ""}
    )


def test_get_company_sic_description(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_company_sic_description endpoint."""
    # Call the endpoint
    result = get_company_sic_description(mock_context, "0001234567890")

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert data == "Test Industry"

    # Verify the client method was called with the correct argument
    mock_edgar_client.get_company_sic_description.assert_called_once_with("0001234567890")


def test_get_company_sic_description_no_client(mock_context: Context) -> None:
    """Test get_company_sic_description endpoint with no client initialized."""
    # Call the endpoint
    response = get_company_sic_description(mock_context, "0001234567890")
    assert response == json.dumps(
        {"error": True, "message": "EDGAR client not initialized", "code": 503, "traceback": ""}
    )


def test_fetch_company_filings_cache(
    patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test that _fetch_company_filings caches results."""
    # Call the function twice with same argument
    result1 = _fetch_company_filings("0001234567890")
    result2 = _fetch_company_filings("0001234567890")

    # Verify results are the same
    assert result1 == result2

    # Verify the client method was called only once (caching works)
    mock_edgar_client.get_company_filings.assert_called_once_with("0001234567890")


def test_fetch_company_filings_different_entities(
    patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test that _fetch_company_filings caches different entities separately."""
    # Setup mock to return different values for different arguments
    with patch.object(mock_edgar_client, "get_company_filings") as mock_get_company_filings:
        mock_get_company_filings.side_effect = lambda entity_id: [
            {"entity": entity_id, "form": "10-K"}
        ]

        # Clear the cache before the first call so the new mock has an effect
        _fetch_company_filings.cache_clear()

        # Call the function with different arguments
        result1 = _fetch_company_filings("0001234567890")
        result2 = _fetch_company_filings("0009876543210")

        # Verify results are different
        assert result1 != result2
        assert result1[0]["entity"] == "0001234567890"
        assert result2[0]["entity"] == "0009876543210"

        # Verify the client method was called twice (different cache keys)
        assert mock_edgar_client.get_company_filings.call_count == 2


def test_fetch_company_filings_no_client() -> None:
    """Test _fetch_company_filings with no client initialized."""
    # Patch the global client to be None
    with patch("server.client_instance", None):
        # Call the function and verify it raises an EdgarError
        with pytest.raises(EdgarError) as excinfo:
            _fetch_company_filings("0001234567890")

        # Verify the error message and code
        assert "EDGAR client not initialized" in str(excinfo.value)
        assert excinfo.value.error_code == 503


def test_get_company_filings(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_company_filings endpoint."""

    # Setup mock data with multiple filings
    mock_filings = [
        {"form": "10-K", "filing_date": "2023-01-01", "accession_number": "0001"},
        {"form": "10-Q", "filing_date": "2023-04-01", "accession_number": "0002"},
        {"form": "10-Q", "filing_date": "2023-07-01", "accession_number": "0003"},
        {"form": "10-Q", "filing_date": "2023-10-01", "accession_number": "0004"},
        {"form": "8-K", "filing_date": "2023-12-01", "accession_number": "0005"},
    ]
    mock_edgar_client.get_company_filings.return_value = mock_filings

    # Clear the cache before the first call so the new mock has an effect
    _fetch_company_filings.cache_clear()

    # Call the endpoint with pagination params
    result = get_company_filings(mock_context, "0001234567890", page=1, page_size=2)

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert "filings" in data
    assert "pagination" in data
    assert len(data["filings"]) == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 2
    assert data["pagination"]["total_items"] == 5
    assert data["pagination"]["total_pages"] == 3

    # Call with different page
    result2 = get_company_filings(mock_context, "0001234567890", page=2, page_size=2)
    data2 = json.loads(result2)
    assert len(data2["filings"]) == 2
    assert data2["filings"][0]["accession_number"] == "0003"

    # Verify the client method was called only once due to caching
    mock_edgar_client.get_company_filings.assert_called_once_with("0001234567890")


def test_get_company_filings_empty(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_company_filings endpoint with empty results."""
    # Setup mock to return empty list
    mock_edgar_client.get_company_filings.return_value = []

    # Clear the cache before the first call so the new mock has an effect
    _fetch_company_filings.cache_clear()

    # Call the endpoint
    result = get_company_filings(mock_context, "0001234567890")

    # Verify the result
    data = json.loads(result)
    assert len(data["filings"]) == 0
    assert data["pagination"]["total_items"] == 0
    assert data["pagination"]["total_pages"] == 0


def test_get_latest_financials(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_latest_financials endpoint."""
    # Setup mock to return annual data
    annual_data = [{"label": "Total Assets", "value": 1000000}]
    mock_edgar_client.get_latest_financials.return_value = annual_data

    # Call the endpoint
    result = get_latest_financials(mock_context, "0001234567890", "balance_sheet", True)

    # Verify the result
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, list)
    assert data[0]["label"] == "Total Assets"

    # Verify the client method was called with the correct arguments
    mock_edgar_client.get_latest_financials.assert_called_once_with(
        "0001234567890", "balance_sheet", True
    )


def test_get_latest_financials_quarterly(
    mock_context: Context, patch_global_client: None, mock_edgar_client: MagicMock
) -> None:
    """Test get_latest_financials endpoint with quarterly data."""
    # Setup mock to return quarterly data
    quarterly_data = [{"label": "Revenue", "value": 250000}]
    mock_edgar_client.get_latest_financials.return_value = quarterly_data

    # Call the endpoint with quarterly param
    result = get_latest_financials(mock_context, "0001234567890", "income_statement", False)

    # Verify the result
    data = json.loads(result)
    assert data[0]["label"] == "Revenue"
    assert data[0]["value"] == 250000

    # Verify the client method was called with the correct arguments
    mock_edgar_client.get_latest_financials.assert_called_once_with(
        "0001234567890", "income_statement", False
    )
