"""Tests for the run.py command-line interface."""

import argparse
import json
import logging
import sys
from io import StringIO
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest

from edgar_sec.client import EdgarClient
from edgar_sec.run import handle_financials, handle_info, main
from edgar_sec.utils.serializer import filing_serializer


@pytest.fixture
def mock_client() -> mock.MagicMock:
    """Create a mock EdgarClient instance for testing."""
    client = mock.MagicMock(spec=EdgarClient)
    return client


@pytest.fixture
def mock_logger() -> Generator[mock.MagicMock, None, None]:
    """Create a mock logger for testing."""
    with mock.patch("edgar_sec.run.logger") as mock_logger:
        yield mock_logger


@pytest.fixture
def captured_stdout() -> Generator[StringIO, None, None]:
    """Capture stdout for testing."""
    captured_output = StringIO()
    sys.stdout = captured_output
    yield captured_output
    sys.stdout = sys.__stdout__


@pytest.fixture
def captured_stderr() -> Generator[StringIO, None, None]:
    """Capture stderr for testing."""
    captured_output = StringIO()
    sys.stderr = captured_output
    yield captured_output
    sys.stderr = sys.__stderr__


class TestHandleInfo:
    """Tests for the handle_info function."""

    def test_handle_info_without_field(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_info function without specific field."""
        args = argparse.Namespace(entity_identifier="AAPL", field=None)
        mock_client.get_company_info.return_value = {"name": "Apple Inc.", "cik": "0000320193"}

        handle_info(mock_client, args)

        mock_client.get_company_info.assert_called_once_with("AAPL")
        mock_logger.info.assert_called_once_with(
            "%s", json.dumps({"name": "Apple Inc.", "cik": "0000320193"}, indent=2)
        )

    def test_handle_info_with_name_field(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_info function with name field."""
        args = argparse.Namespace(entity_identifier="AAPL", field="name")
        mock_client.get_company_name.return_value = "Apple Inc."

        handle_info(mock_client, args)

        mock_client.get_company_name.assert_called_once_with("AAPL")
        mock_logger.info.assert_called_once_with("%s", "Apple Inc.")

    def test_handle_info_with_tickers_field(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_info function with tickers field."""
        args = argparse.Namespace(entity_identifier="0000320193", field="tickers")
        mock_client.get_company_tickers.return_value = ["AAPL"]

        handle_info(mock_client, args)

        mock_client.get_company_tickers.assert_called_once_with("0000320193")
        mock_logger.info.assert_called_once_with("%s", "AAPL")

    def test_handle_info_with_sic_field(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_info function with sic field."""
        args = argparse.Namespace(entity_identifier="AAPL", field="sic")
        mock_client.get_company_sic_description.return_value = "Electronic Computers"

        handle_info(mock_client, args)

        mock_client.get_company_sic_description.assert_called_once_with("AAPL")
        mock_logger.info.assert_called_once_with("%s", "Electronic Computers")

    def test_handle_info_with_filings_field(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_info function with filings field."""
        args = argparse.Namespace(entity_identifier="AAPL", field="filings")
        filings = [
            {
                "form": "10-K",
                "filing_date": "2023-11-03",
                "accession_number": "0000320193-23-000105",
                "isXBRL": True,
            }
        ]
        mock_client.get_company_filings.return_value = filings

        handle_info(mock_client, args)

        mock_client.get_company_filings.assert_called_once_with("AAPL")
        mock_logger.info.assert_called_once_with(
            "%s", json.dumps(filings, indent=2, default=filing_serializer)
        )


class TestHandleFinancials:
    """Tests for the handle_financials function."""

    def test_handle_financials_with_annual_data(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_financials function with annual data."""
        args = argparse.Namespace(
            entity_identifier="AAPL", table_type="balance_sheet", quarterly=False
        )
        financials = [
            {"label": "Assets", "2023": 1000000, "2022": 900000},
            {"label": "Liabilities", "2023": 500000, "2022": 450000},
        ]
        mock_client.get_latest_financials.return_value = financials

        handle_financials(mock_client, args)

        mock_client.get_latest_financials.assert_called_once_with("AAPL", "balance_sheet", True)
        mock_logger.info.assert_called_once_with("%s", json.dumps(financials, indent=2))

    def test_handle_financials_with_quarterly_data(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_financials function with quarterly data."""
        args = argparse.Namespace(
            entity_identifier="AAPL", table_type="income_statement", quarterly=True
        )
        financials = [
            {"label": "Revenue", "Q4 2023": 100000, "Q3 2023": 90000},
            {"label": "Net Income", "Q4 2023": 20000, "Q3 2023": 18000},
        ]
        mock_client.get_latest_financials.return_value = financials

        handle_financials(mock_client, args)

        mock_client.get_latest_financials.assert_called_once_with("AAPL", "income_statement", False)
        mock_logger.info.assert_called_once_with("%s", json.dumps(financials, indent=2))

    def test_handle_financials_with_no_data(
        self, mock_client: mock.MagicMock, mock_logger: mock.MagicMock
    ) -> None:
        """Test handle_financials function with no data."""
        args = argparse.Namespace(
            entity_identifier="AAPL", table_type="cash_flow_statement", quarterly=False
        )
        mock_client.get_latest_financials.return_value = []

        handle_financials(mock_client, args)

        mock_client.get_latest_financials.assert_called_once_with(
            "AAPL", "cash_flow_statement", True
        )
        mock_logger.warning.assert_called_once_with("No financials found for %s", "AAPL")


class TestMain:
    """Tests for the main function."""

    @mock.patch("edgar_sec.run.setup_logging")
    @mock.patch("edgar_sec.run.EdgarClient")
    @mock.patch("edgar_sec.run.argparse.ArgumentParser.parse_args")
    def test_main_with_info_command(
        self,
        mock_parse_args: mock.MagicMock,
        mock_edgar_client: mock.MagicMock,
        mock_setup_logging: mock.MagicMock,
    ) -> None:
        """Test main function with info command."""
        args = argparse.Namespace(
            output_dir=Path("output"),
            verbose=False,
            log_file=None,
            command="info",
            entity_identifier="AAPL",
            field=None,
        )
        mock_parse_args.return_value = args
        mock_client = mock.MagicMock()
        mock_edgar_client.return_value = mock_client

        with mock.patch("edgar_sec.run.handle_info") as mock_handle_info:
            main()

        mock_setup_logging.assert_called_once_with(log_file=None, level=logging.INFO)
        mock_edgar_client.assert_called_once_with(output_dir=Path("output"))
        mock_handle_info.assert_called_once()
        args_passed = mock_handle_info.call_args[0]
        assert args_passed[0] == mock_client
        assert args_passed[1] == args

    @mock.patch("edgar_sec.run.setup_logging")
    @mock.patch("edgar_sec.run.EdgarClient")
    @mock.patch("edgar_sec.run.argparse.ArgumentParser.parse_args")
    def test_main_with_financials_command(
        self,
        mock_parse_args: mock.MagicMock,
        mock_edgar_client: mock.MagicMock,
        mock_setup_logging: mock.MagicMock,
    ) -> None:
        """Test main function with financials command."""
        args = argparse.Namespace(
            output_dir=Path("output"),
            verbose=True,
            log_file=Path("log.txt"),
            command="financials",
            entity_identifier="AAPL",
            table_type="balance_sheet",
            quarterly=False,
        )
        mock_parse_args.return_value = args
        mock_client = mock.MagicMock()
        mock_edgar_client.return_value = mock_client

        with mock.patch("edgar_sec.run.handle_financials") as mock_handle_financials:
            main()

        mock_setup_logging.assert_called_once_with(log_file=Path("log.txt"), level=logging.DEBUG)
        mock_edgar_client.assert_called_once_with(output_dir=Path("output"))
        mock_handle_financials.assert_called_once()
        args_passed = mock_handle_financials.call_args[0]
        assert args_passed[0] == mock_client
        assert args_passed[1] == args

    @mock.patch("edgar_sec.run.setup_logging")
    @mock.patch("edgar_sec.run.EdgarClient")
    @mock.patch("edgar_sec.run.argparse.ArgumentParser.parse_args")
    def test_main_with_no_command(
        self,
        mock_parse_args: mock.MagicMock,
        mock_edgar_client: mock.MagicMock,
        mock_setup_logging: mock.MagicMock,
    ) -> None:
        """Test main function with no command."""
        args = argparse.Namespace(
            output_dir=Path("output"),
            verbose=False,
            log_file=None,
            command=None,
        )
        mock_parse_args.return_value = args
        mock_client = mock.MagicMock()
        mock_edgar_client.return_value = mock_client

        with mock.patch("edgar_sec.run.argparse.ArgumentParser.print_help") as mock_print_help:
            main()

        mock_setup_logging.assert_called_once_with(log_file=None, level=logging.INFO)
        mock_edgar_client.assert_called_once_with(output_dir=Path("output"))
        mock_print_help.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
