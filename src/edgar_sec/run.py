"""Command-line interface for the EDGAR SEC client."""

import argparse
import json
import logging
from pathlib import Path
from typing import Callable

from edgar_sec.client import EdgarClient
from edgar_sec.utils.logging import setup_logging
from edgar_sec.utils.serializer import filing_serializer

logger = logging.getLogger(__name__)


def handle_info(client: EdgarClient, args: argparse.Namespace) -> None:
    """Handle the info command.

    Args:
        client: The EdgarClient instance.
        args: The parsed command-line arguments.
    """
    if args.field:
        field_handlers: dict[str, Callable[[], str]] = {
            "name": lambda: client.get_company_name(args.entity_identifier),
            "tickers": lambda: ", ".join(client.get_company_tickers(args.entity_identifier)),
            "sic": lambda: client.get_company_sic_description(args.entity_identifier),
            "filings": lambda: json.dumps(
                client.get_company_filings(args.entity_identifier),
                indent=2,
                default=filing_serializer,
            ),
        }
        logger.info("%s", field_handlers[args.field]())
    else:
        info = client.get_company_info(args.entity_identifier)
        logger.info("%s", json.dumps(info, indent=2))


def handle_financials(client: EdgarClient, args: argparse.Namespace) -> None:
    """Handle the financials command."""
    financials = client.get_latest_financials(
        args.entity_identifier, args.table_type, not args.quarterly
    )
    if financials:
        logger.info("%s", json.dumps(financials, indent=2))
    else:
        logger.warning("No financials found for %s", args.entity_identifier)


def main() -> None:
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="EDGAR SEC API client")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="output",
        help="Directory to save output files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (default: stderr only)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get company information")
    info_parser.add_argument("entity_identifier", help="Company CIK number or ticker")
    info_parser.add_argument(
        "-f",
        "--field",
        choices=["name", "tickers", "sic", "filings"],
        help="Specific field to retrieve",
    )

    # Financials command
    financials_parser = subparsers.add_parser("financials", help="Get company financials")
    financials_parser.add_argument("entity_identifier", help="Company CIK number or ticker")
    financials_parser.add_argument(
        "-t",
        "--table-type",
        choices=[
            "balance_sheet",
            "income_statement",
            "cash_flow_statement",
            "comprehensive_income",
            "equity",
            "cover_page",
        ],
        help="Specific table type to retrieve",
    )
    financials_parser.add_argument(
        "-q",
        "--quarterly",
        action="store_true",
        help="Get quarterly financials. If not specified, annual financials are retrieved.",
    )

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_file=args.log_file, level=log_level)

    # Create client
    client = EdgarClient(output_dir=args.output_dir)

    # Handle command
    command_handlers = {
        "info": handle_info,
        "financials": handle_financials,
    }

    if args.command in command_handlers:
        command_handlers[args.command](client, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
