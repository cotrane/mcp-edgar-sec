# EDGAR SEC MCP Server

The EDGAR SEC MCP server provides a powerful interface for AI systems to interact with SEC EDGAR data through the MCP (Model Control Protocol) framework.

## Overview

The MCP server mode enables AI systems to:

- Fetch company information using CIK numbers or ticker symbols
- Access financial statements and filing history
- Query specific company details (name, tickers, SIC description)
- Obtain structured financial data from SEC filings

## Available Resources

### Configuration Resources

These resources provide reference data that can be used by the MCP client:

- `config://valid_cik_ticker_data`: Returns a list of valid CIK numbers and their associated ticker symbols
- `config://valid_forms`: Returns a list of valid SEC form types

## Available Tools

The following tools are available to interact with SEC EDGAR data:

### Company Information Tools

- `get_company_info(entity_identifier)`: Get comprehensive company information
- `get_company_name(entity_identifier)`: Get only the company name
- `get_company_tickers(entity_identifier)`: Get company ticker symbols
- `get_company_sic_description(entity_identifier)`: Get SIC description
- `get_company_filings(entity_identifier, page=1, page_size=100)`: Get company filings with pagination support

### Financial Information Tools

- `get_latest_financials(entity_identifier, table_type, annual=True)`: Get financial statements
  - Supported table types: "balance_sheet", "income_statement", "cash_flow_statement", "comprehensive_income", "equity", "cover_page"
  - Option to retrieve annual (default) or quarterly statements

### Filing Detail Tools

- `get_filing_details(entity_identifier, accession_number)`: Get detailed information about a specific filing
- `get_filing_content(entity_identifier, accession_number)`: Get the full content of a specific filing
- `get_filing_documents(entity_identifier, accession_number)`: Get a list of documents in a specific filing

## Available Prompt Templates

### Latest Financials

- `get_latest_financials_prompt(entity_identifier, table_type, annual)`: A pre-defined prompt which will make sure the LLM checks if the latest financials are annual or interim and present the most recent in a tabular output.

## Testing the MCP Server

You can use the MCP Inspector to test the server before you include it in any client. The MCP Inspector allows you to test each tool while seeing log messages. You can start it with following command:

```bash
cd /path/to/mcp-edgar-sec-repo
uv run mcp dev src/server.py  --with-editable .
```

You can then open the tool in your browser using the displayed url `<http://127.0.0.1:6274>`.

Find more information in the [Inspector Guide](https://modelcontextprotocol.io/docs/tools/inspector) of the official documentation.