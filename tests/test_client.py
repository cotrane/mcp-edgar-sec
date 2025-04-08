"""Tests for the EdgarClient class."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from edgar_sec.client import EdgarClient, EdgarError


@pytest.fixture
def mock_client(tmp_path: Path) -> EdgarClient:
    """Create a test client with a temporary output directory."""
    with patch("requests.get") as mock_get:
        # Mock the ticker_cik response for initialization
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": "1234567890", "ticker": "TEST", "title": "Test Company"}
        }
        mock_get.return_value = mock_response

        # Mock set_identity to avoid actual API calls
        with patch("edgar_sec.client.set_identity", return_value=None):
            return EdgarClient(output_dir=tmp_path)


@pytest.fixture
def mock_edgar_response() -> dict:
    """Create a mock EDGAR API response."""
    return {
        "cik": 1234567,
        "name": "Test Company",
        "filings": {
            "recent": {
                "accessionNumber": ["0001234567-24-000001"],
                "form": ["10-K"],
                "filingDate": ["2024-01-01"],
                "reportDate": ["2024-01-01"],
                "primaryDocument": ["form10k.htm"],
                "primaryDocDescription": ["Test Filing"],
                "core_type": ["test"],
            },
            "files": [
                {
                    "name": "CIK0001234567-submissions-2024-01-01.txt",
                    "filingFrom": "2024-01-01",
                    "filingTo": "2024-01-01",
                }
            ],
        },
        "tickers": ["TEST"],
        "exchanges": ["NYSE"],
        "sic": "1234",
        "sicDescription": "Test Industry",
        "category": "Large Accelerated Filer",
        "country": "US",
        "stateOfIncorporation": "DE",
        "stateOfIncorporationDescription": "Delaware",
        "addresses": {
            "mailing": {
                "street1": "123 Test St",
                "city": "Test City",
                "stateOrCountry": "DE",
                "zipCode": "12345",
            }
        },
        "phone": "123-456-7890",
        "flags": "test",
        "formerNames": [{"name": "Old Name", "from": "2020-01-01", "to": "2023-12-31"}],
    }


@pytest.fixture
def mock_filings_data() -> list[dict]:
    """Create a mock filings data response."""
    return [
        {
            "form": "10-K",
            "filing_date": "2024-01-01",
            "accession_number": "0001234567-24-000001",
            "isXBRL": True,
        }
    ]


@patch("requests.get")
def test_client_initialization(mock_get: MagicMock, tmp_path: Path) -> None:
    """Test client initialization."""
    # Mock the ticker_cik response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "0": {"cik_str": "1234567890", "ticker": "TEST", "title": "Test Company"}
    }
    mock_get.return_value = mock_response

    # Create client
    with patch("edgar_sec.client.set_identity"):
        client = EdgarClient(output_dir=tmp_path)

    # Verify output directory was created
    assert client.output_dir.exists()

    # Verify headers were set
    assert "User-Agent" in client.headers

    # Verify dataframe was created
    assert hasattr(client, "ticker_cik_df")


@patch("edgar_sec.client.set_identity")
@patch("requests.get")
def test_client_initialization_failure(
    mock_get: MagicMock, mock_set_identity: MagicMock, tmp_path: Path
) -> None:
    """Test client initialization failure."""
    # Mock request failure
    mock_get.side_effect = requests.exceptions.RequestException("Connection error")

    # Verify EdgarError is raised
    with pytest.raises(EdgarError) as excinfo:
        EdgarClient(output_dir=tmp_path)
    assert "Failed to initialize EDGAR client" in str(excinfo.value)
    assert excinfo.value.error_code == 503


def test_get_valid_cik_ticker_data(mock_client: EdgarClient) -> None:
    """Test getting valid CIK and ticker data."""
    result = mock_client.get_valid_cik_ticker_data()
    assert isinstance(result, list)

    # Verify that exception handling works
    with patch.object(mock_client, "ticker_cik_df", None):
        with pytest.raises(EdgarError) as excinfo:
            mock_client.get_valid_cik_ticker_data()
        assert "Failed to get valid CIK and ticker data" in str(excinfo.value)
        assert excinfo.value.error_code == 500


@patch("edgar_sec.client.COMPANY_FORMS", ["10-K", "10-Q", "8-K"])
def test_get_valid_forms_data(mock_client: EdgarClient) -> None:
    """Test getting valid forms data."""
    result = mock_client.get_valid_forms_data()
    assert isinstance(result, list)
    assert "10-K" in result
    assert "10-Q" in result
    assert "8-K" in result


@patch("edgar_sec.client.Company")
def test_get_company_info_success(
    mock_company: MagicMock, mock_client: EdgarClient, mock_edgar_response: dict
) -> None:
    """Test getting company information."""
    mock_instance = MagicMock()
    mock_instance.to_dict.return_value = mock_edgar_response
    mock_company.return_value = mock_instance

    info = mock_client.get_company_info("0001234567")
    assert info["cik"] == 1234567
    assert info["name"] == "Test Company"
    assert info["tickers"] == ["TEST"]
    assert info["sicDescription"] == "Test Industry"
    assert info["category"] == "Large Accelerated Filer"
    assert info["country"] == "US"
    assert info["stateOfIncorporation"] == "DE"
    assert info["stateOfIncorporationDescription"] == "Delaware"
    assert info["phone"] == "123-456-7890"
    assert len(info["formerNames"]) == 1
    assert info["formerNames"][0]["name"] == "Old Name"


@patch("edgar_sec.client.Company")
def test_get_company_info_invalid_cik(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test that invalid CIK numbers raise ValueError."""
    mock_company.side_effect = ValueError("CIK must be a 10-digit number")

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_company_info("123")
    assert "CIK must be a 10-digit number" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_company_info_exception(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test exception handling when getting company information."""
    mock_company.side_effect = Exception("API Error")

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_company_info("0001234567")
    assert "Failed to get company info" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_company_name(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting company name."""
    mock_instance = MagicMock()
    mock_instance.name = "Test Company"
    mock_company.return_value = mock_instance

    name = mock_client.get_company_name("0001234567")
    assert name == "Test Company"


@patch("edgar_sec.client.Company")
def test_get_company_name_exception(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test exception handling when getting company name."""
    mock_company.side_effect = Exception("API Error")

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_company_name("0001234567")
    assert "Failed to get company name" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_company_tickers(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting company tickers."""
    mock_instance = MagicMock()
    mock_instance.tickers = ["TEST"]
    mock_company.return_value = mock_instance

    tickers = mock_client.get_company_tickers("0001234567")
    assert tickers == ["TEST"]


@patch("edgar_sec.client.Company")
def test_get_company_tickers_exception(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test exception handling when getting company tickers."""
    mock_company.side_effect = Exception("API Error")

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_company_tickers("0001234567")
    assert "Failed to get company tickers" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_company_sic_description(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting company SIC description."""
    mock_instance = MagicMock()
    mock_instance.sic_description = "Test Industry"
    mock_company.return_value = mock_instance

    sic_description = mock_client.get_company_sic_description("0001234567")
    assert sic_description == "Test Industry"


@patch("edgar_sec.client.Company")
def test_get_company_sic_description_exception(
    mock_company: MagicMock, mock_client: EdgarClient
) -> None:
    """Test exception handling when getting company SIC description."""
    mock_company.side_effect = Exception("API Error")

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_company_sic_description("0001234567")
    assert "Failed to get company SIC description" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_company_filings(
    mock_company: MagicMock, mock_client: EdgarClient, mock_filings_data: list
) -> None:
    """Test getting company filings."""
    mock_instance = MagicMock()
    mock_filings = MagicMock()

    # Configure to_pandas to return a dataframe that will match the expected output
    mock_df = MagicMock()
    mock_df.filter.return_value = MagicMock()
    mock_df.filter.return_value.to_dict.return_value = mock_filings_data
    mock_filings.to_pandas.return_value = mock_df

    mock_instance.get_filings.return_value = mock_filings
    mock_company.return_value = mock_instance

    filings = mock_client.get_company_filings("0001234567")
    assert isinstance(filings, list)
    assert len(filings) == 1
    assert filings[0]["form"] == "10-K"
    assert filings[0]["accession_number"] == "0001234567-24-000001"
    assert filings[0]["filing_date"] == "2024-01-01"
    assert filings[0]["isXBRL"] is True


@patch("edgar_sec.client.Company")
def test_get_company_filings_empty(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting company filings when none are available."""
    mock_instance = MagicMock()
    mock_instance.get_filings.return_value = None
    mock_company.return_value = mock_instance

    filings = mock_client.get_company_filings("0001234567")
    assert isinstance(filings, list)
    assert len(filings) == 0


@patch("edgar_sec.client.Company")
def test_get_company_filings_exception(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test exception handling when getting company filings."""
    mock_instance = MagicMock()
    mock_instance.get_filings.side_effect = Exception("API Error")
    mock_company.return_value = mock_instance

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_company_filings("0001234567")
    assert "Failed to get company filings" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_latest_financials_exception(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test exception handling when getting latest financials."""
    mock_company.side_effect = Exception("API Error")

    with pytest.raises(EdgarError) as excinfo:
        mock_client.get_latest_financials("0001234567", "balance_sheet")
    assert "Failed to get company financials" in str(excinfo.value)
    assert excinfo.value.error_code == 500


@patch("edgar_sec.client.Company")
def test_get_latest_financials_empty(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting latest financials when none are available."""
    # Create mock objects for the financials
    mock_instance = MagicMock()
    mock_instance.financials = None
    mock_company.return_value = mock_instance

    # Run the async method
    result = mock_client.get_latest_financials("0001234567", "balance_sheet", True)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 0


@patch("edgar_sec.client.Company")
def test_get_latest_financials_quarterly(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting quarterly financials."""
    # Create mock objects for the financials
    mock_instance = MagicMock()
    mock_financials = MagicMock()
    mock_income = MagicMock()
    mock_df = MagicMock()

    # Configure the mock to return an empty dataframe for to_dataframe
    mock_df.empty = False
    mock_df.reset_index = MagicMock()
    mock_df.rename = MagicMock()
    mock_df.to_dict.return_value = [{"label": "Revenue", "value": 500000}]

    mock_income.to_dataframe.return_value = mock_df
    mock_financials.income = mock_income
    mock_instance.quarterly_financials = mock_financials
    mock_company.return_value = mock_instance

    # Run the async method
    result = mock_client.get_latest_financials("0001234567", "income_statement", False)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["label"] == "Revenue"
    assert result[0]["value"] == 500000


@patch("edgar_sec.client.Company")
def test_get_latest_financials_cash_flow(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting cash flow statement financials."""
    # Create mock objects for the financials
    mock_instance = MagicMock()
    mock_financials = MagicMock()
    mock_cashflow = MagicMock()
    mock_df = MagicMock()

    # Configure the mock to return an empty dataframe for to_dataframe
    mock_df.empty = False
    mock_df.reset_index = MagicMock()
    mock_df.rename = MagicMock()
    mock_df.to_dict.return_value = [{"label": "Cash Flow", "value": 250000}]

    mock_cashflow.to_dataframe.return_value = mock_df
    mock_financials.cashflow = mock_cashflow
    mock_instance.financials = mock_financials
    mock_company.return_value = mock_instance

    # Run the async method
    result = mock_client.get_latest_financials("0001234567", "cash_flow_statement", True)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["label"] == "Cash Flow"
    assert result[0]["value"] == 250000


@patch("edgar_sec.client.Company")
def test_get_latest_financials_comprehensive_income(
    mock_company: MagicMock, mock_client: EdgarClient
) -> None:
    """Test getting comprehensive income financials."""
    # Create mock objects for the financials
    mock_instance = MagicMock()
    mock_financials = MagicMock()
    mock_comprehensive = MagicMock()
    mock_df = MagicMock()

    # Configure the mock to return an empty dataframe for to_dataframe
    mock_df.empty = False
    mock_df.reset_index = MagicMock()
    mock_df.rename = MagicMock()
    mock_df.to_dict.return_value = [{"label": "Comprehensive Income", "value": 300000}]

    mock_comprehensive.to_dataframe.return_value = mock_df
    mock_financials.comprehensive_income = mock_comprehensive
    mock_instance.financials = mock_financials
    mock_company.return_value = mock_instance

    # Run the async method
    result = mock_client.get_latest_financials("0001234567", "comprehensive_income", True)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["label"] == "Comprehensive Income"
    assert result[0]["value"] == 300000


@patch("edgar_sec.client.Company")
def test_get_latest_financials_equity(mock_company: MagicMock, mock_client: EdgarClient) -> None:
    """Test getting equity statement financials."""

    # Create mock objects for the financials
    mock_instance = MagicMock()
    mock_financials = MagicMock()
    mock_equity = MagicMock()
    mock_df = MagicMock()

    # Configure the mock to return an empty dataframe for to_dataframe
    mock_df.empty = False
    mock_df.reset_index = MagicMock()
    mock_df.rename = MagicMock()
    mock_df.to_dict.return_value = [{"label": "Equity", "value": 800000}]

    mock_equity.to_dataframe.return_value = mock_df
    mock_financials.equity = mock_equity
    mock_instance.financials = mock_financials
    mock_company.return_value = mock_instance

    # Run the async method
    result = mock_client.get_latest_financials("0001234567", "equity", True)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["label"] == "Equity"
    assert result[0]["value"] == 800000


@patch("edgar_sec.client.Company")
def test_get_latest_financials_cover_page(
    mock_company: MagicMock, mock_client: EdgarClient
) -> None:
    """Test getting cover page financials."""

    # Create mock objects for the financials
    mock_instance = MagicMock()
    mock_financials = MagicMock()
    mock_cover = MagicMock()
    mock_df = MagicMock()

    # Configure the mock to return an empty dataframe for to_dataframe
    mock_df.empty = False
    mock_df.reset_index = MagicMock()
    mock_df.rename = MagicMock()
    mock_df.to_dict.return_value = [{"label": "Cover", "value": "Information"}]

    mock_cover.to_dataframe.return_value = mock_df
    mock_financials.cover = mock_cover
    mock_instance.financials = mock_financials
    mock_company.return_value = mock_instance

    # Run the async method
    result = mock_client.get_latest_financials("0001234567", "cover_page", True)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["label"] == "Cover"
    assert result[0]["value"] == "Information"
