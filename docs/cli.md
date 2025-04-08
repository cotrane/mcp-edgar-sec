# EDGAR SEC CLI Mode

The EDGAR SEC client can be run as a command-line tool to fetch and analyze SEC EDGAR data directly from your terminal.

## Installation

Before using the CLI, ensure you have installed the package:

```bash
uv pip install -e .
```

## Basic Usage

```bash
python -m edgar_sec [options] <command> [command options]
```

## Global Options

- `--output-dir PATH`: Directory to save output files (default: "output")
- `--verbose, -v`: Enable verbose logging
- `--log-file PATH`: Path to log file (default: logs to stderr only)

## Available Commands

### Company Information

Fetch detailed information about a company:

```bash
python -m edgar_sec info <entity_identifier> [options]
```

Arguments:
- `entity_identifier`: Company CIK number or ticker symbol

Options:
- `-f, --field {name,tickers,sic,filings}`: Get specific information field

Examples:
```bash
# Get all company information
python -m edgar_sec info AAPL

# Get only company name
python -m edgar_sec info 0000320193 --field name

# Get company ticker symbols
python -m edgar_sec info AAPL --field tickers

# Get Standard Industrial Classification (SIC) description
python -m edgar_sec info AAPL --field sic

# Get company filings
python -m edgar_sec info AAPL --field filings
```

### Financial Information

Retrieve financial statements for a company:

```bash
python -m edgar_sec financials <entity_identifier> [options]
```

Arguments:
- `entity_identifier`: Company CIK number or ticker symbol

Options:
- `-t, --table-type {balance_sheet,income_statement,cash_flow_statement,comprehensive_income,equity,cover_page}`: Type of financial table to retrieve
- `-q, --quarterly`: Get quarterly financials (default is annual)

Examples:
```bash
# Get annual balance sheet
python -m edgar_sec financials AAPL --table-type balance_sheet

# Get quarterly income statement
python -m edgar_sec financials AAPL --table-type income_statement --quarterly
```

## Output

All commands return JSON-formatted data to stdout by default, making it easy to pipe the output to other tools or save to a file.

Example:
```bash
# Save company information to a JSON file
python -m edgar_sec info AAPL > apple_info.json
``` 