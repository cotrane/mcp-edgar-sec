"""Client module for interacting with the SEC EDGAR API using EdgarTools."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any, Hashable, Literal

import pandas as pd
import requests
from edgar import Company, set_identity  # type: ignore
from edgar.entities import COMPANY_FORMS  # type: ignore

# Redirect all package logging to stderr to avoid any stdout issues
# with the MCP client
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"": {"level": "INFO"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
            }
        },
    }
)


class EdgarError(Exception):
    """Base exception class for Edgar client errors."""

    def __init__(self, message: str, error_code: int = 500, error_traceback: str = ""):
        self.message = message
        self.error_code = error_code
        self.error_traceback = error_traceback
        super().__init__(self.message)


class EdgarClient:
    """Client for interacting with the SEC EDGAR API using EdgarTools.

    This client provides a simplified interface for working with company information
    from the SEC EDGAR database using the EdgarTools library.

    Attributes:
        output_dir: Directory where output files will be saved.
    """

    def __init__(self, output_dir: str | Path = "output") -> None:
        """Initialize the EDGAR client.

        Args:
            output_dir: Directory where output files will be saved.

        Raises:
            EdgarError: If initialization fails.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.headers = {"User-Agent": "mcp.edgar.sec.client@mcp.com"}
            ticker_cik = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=self.headers,
                timeout=10,
            )
            ticker_cik.raise_for_status()
            self.ticker_cik_df = pd.DataFrame.from_dict(ticker_cik.json(), orient="index")
            self.ticker_cik_df = self.ticker_cik_df.rename(
                columns={"cik_str": "cik", "title": "company_name"}
            )
            self.ticker_cik_df["cik"] = self.ticker_cik_df["cik"].astype(str).str.zfill(10)

            # Set identity for SEC EDGAR access
            set_identity("MCP EDGAR SEC Client mcp.edgar.sec.client@mcp.com")
        except requests.exceptions.RequestException as e:
            raise EdgarError(f"Failed to initialize EDGAR client: {str(e)}", 503) from e
        except Exception as e:
            raise EdgarError(f"Unexpected error during initialization: {str(e)}", 500) from e

    def get_valid_cik_ticker_data(self) -> list[dict[Hashable, Any]]:
        """Get a list of valid CIK and company tickers from the SEC EDGAR database.

        Raises:
            EdgarError: If the request fails

        Returns:
            list[dict[Hashable, Any]]: List of dictionaries containing valid CIK,
                company tickers, and company names.
        """
        try:
            return self.ticker_cik_df.to_dict(orient="records")
        except Exception as e:
            raise EdgarError(f"Failed to get valid CIK and ticker data: {str(e)}", 500) from e

    def get_valid_forms_data(self) -> list[str]:
        """Get a list of valid forms from the SEC EDGAR database.

        Raises:
            EdgarError: If the request fails

        Returns:
            list[str]: List of valid forms.
        """
        try:
            return list(COMPANY_FORMS)
        except Exception as e:
            raise EdgarError(f"Failed to get valid forms data: {str(e)}", 500) from e

    def get_company_info(self, entity_identifier: str | int) -> dict[str, Any]:
        """Get comprehensive company information.

        Args:
            entity_identifier (str | int): The company's CIK number (10 digits with leading zeros)
                or ticker.

        Raises:
            EdgarError: If the request fails

        Returns:
            dict[str, Any]: Dictionary containing company information including name, tickers,
                SIC description, and other details.
        """
        try:
            company = Company(entity_identifier)
            return company.to_dict()
        except Exception as e:
            raise EdgarError(f"Failed to get company info: {str(e)}", 500) from e

    def get_company_name(self, entity_identifier: str | int) -> str:
        """Get the company's name.

        Args:
            entity_identifier (str | int): The company's CIK number (10 digits with leading zeros)
                or ticker.

        Raises:
            EdgarError: If the request fails

        Returns:
            The company's name.
        """
        try:
            company = Company(entity_identifier)
            return company.name
        except Exception as e:
            raise EdgarError(f"Failed to get company name: {str(e)}", 500) from e

    def get_company_tickers(self, entity_identifier: str | int) -> list[str]:
        """Get the company's ticker symbols.

        Args:
            entity_identifier (str | int): The company's CIK number (10 digits with leading zeros)
                or ticker.

        Raises:
            EdgarError: If the request fails

        Returns:
            List of ticker symbols.
        """
        try:
            company = Company(entity_identifier)
            return company.tickers
        except Exception as e:
            raise EdgarError(f"Failed to get company tickers: {str(e)}", 500) from e

    def get_company_sic_description(self, entity_identifier: str | int) -> str:
        """Get the company's SIC description.

        Args:
            entity_identifier (str | int): The company's CIK number (10 digits with leading zeros)
                or ticker.

        Raises:
            EdgarError: If the request fails

        Returns:
            The company's SIC description.
        """
        try:
            company = Company(entity_identifier)
            return company.sic_description
        except Exception as e:
            raise EdgarError(f"Failed to get company SIC description: {str(e)}", 500) from e

    def get_company_filings(self, entity_identifier: str | int) -> list[dict[Hashable, Any]]:
        """Get all company filings.

        Args:
            entity_identifier (str | int): The company's CIK number (10 digits with leading zeros)
                or ticker.

        Raises:
            EdgarError: If the request fails

        Returns:
            list[dict[Hashable, Any]]: List of filing dictionaries containing basic filing
                information.
        """
        try:
            company = Company(entity_identifier)
            filings = company.get_filings()

            if not filings:
                return []

            filings_df = filings.to_pandas()
            filings_df["isXBRL"] = filings_df.isXBRL == 1  # replace checkmark with boolean
            return filings_df.filter(["form", "filing_date", "accession_number", "isXBRL"]).to_dict(
                orient="records"
            )
        except Exception as e:
            raise EdgarError(f"Failed to get company filings: {str(e)}", 500) from e

    def get_latest_financials(
        self,
        entity_identifier: str | int,
        table_type: Literal[
            "balance_sheet",
            "income_statement",
            "cash_flow_statement",
            "comprehensive_income",
            "equity",
            "cover_page",
        ],
        annual: bool = True,
    ) -> list[dict[Hashable, Any]]:
        """Get the company's financials.

        Args:
            entity_identifier (str | int): The company's CIK number (10 digits with leading zeros)
                or ticker.
            table_type (Literal["balance_sheet", "income_statement", "cash_flow_statement",
                "comprehensive_income", "equity", "cover_page"]): The type of financial table to
                    get.
            annual (bool): Whether to get the annual financials. Defaults to True.

        Returns:
            list[dict[Hashable, Any]]: List of dictionaries containing the company's financials.
        """
        try:
            company = Company(entity_identifier)
            if annual:
                financials = company.financials
            else:
                financials = company.quarterly_financials
            if not financials:
                return []
            if table_type == "balance_sheet":
                financials = financials.balance_sheet
            elif table_type == "income_statement":
                financials = financials.income
            elif table_type == "cash_flow_statement":
                financials = financials.cashflow
            elif table_type == "comprehensive_income":
                financials = financials.comprehensive_income
            elif table_type == "equity":
                financials = financials.equity
            elif table_type == "cover_page":
                financials = financials.cover
            df = financials.to_dataframe() if financials else pd.DataFrame()
            if not df.empty:
                df.reset_index(inplace=True)
                df.rename(columns={"index": "label"}, inplace=True)
            return df.to_dict(orient="records")
        except Exception as e:
            raise EdgarError(f"Failed to get company financials: {str(e)}", 500) from e
