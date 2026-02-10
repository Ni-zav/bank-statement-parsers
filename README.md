# Bank Statement Parser

A Python tool to extract and parse bank statement files from multiple Indonesian banks and convert them to standardized CSV format for easier analysis and record-keeping.

## ⚠️ Data Privacy Warning

**Notice**: This tool processes bank statement files that contain personal financial information. Store processed files securely and do not share CSV exports publicly.

## Supported Banks

- **BCA** (Bank Central Asia) - PDF format
- **Mandiri** (Bank Mandiri) - Excel (.xlsx, .xls) and PDF formats
- **CIMB** (Bank CIMB Niaga) - PDF format

## Features

- **Automatic Bank Detection**: Recognizes default bank download filenames and custom naming patterns
- **Recursive File Search**: Finds all statement files in folders and subfolders automatically
- **Bank-Specific Parsing**: Uses dedicated parsers for each bank's unique statement format
- **Password-Protected Files**: Automatically decrypts password-protected Mandiri Excel files
- **Transaction Extraction**: Extracts date, description, amounts, balances, and reference numbers
- **Standardized Output**: Exports data to CSV with consistent columns across all banks
- **Account Information**: Automatically extracts account owner name and account number
- **Batch Processing**: Process all files of a specific bank or all banks at once
- **Mixed File Handling**: Safely processes folders with random files (validates file content)
- **Customizable Output Format**: Control date formats, column visibility, debit/credit handling, and more
- **Flexible Date Formats**: Presets (ddmmyyyy, mmyyyy, mmmm) and custom strftime patterns
- **Combined/Separate Debit-Credit**: Single amount column or separate debit/credit columns
- **Optional Columns**: Include/exclude Reference No, Balance, Bank, and Owner columns
- **Custom Currency Support**: Specify currency code and optionally add currency column
- **Custom Filenames**: Define your own output filename format with smart placeholders

## Installation

### Requirements

- Python 3.7+
- pandas
- pdfplumber
- openpyxl
- msoffcrypto-tool (for password-protected Mandiri files)

### Setup

1. Clone or download the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Process all bank statements of a specific bank:

```bash
python process_statements.py /path/to/statements bca
python process_statements.py /path/to/statements mandiri
python process_statements.py /path/to/statements cimb
```

### Process All Banks

Process files from all supported banks:

```bash
python process_statements.py /path/to/statements all
```

Or simply omit the bank parameter (defaults to 'all'):

```bash
python process_statements.py /path/to/statements
```

### Specify Output Directory

Save processed CSV files to a custom location:

```bash
python process_statements.py /path/to/statements bca -o /path/to/output
```

Or use the long form:

```bash
python process_statements.py /path/to/statements bca --output /path/to/output
```

### Password-Protected Mandiri Files

For password-protected Mandiri Excel files, provide the password with `-p` flag:

```bash
python process_statements.py /path/to/statements mandiri -p YOUR_PASSWORD -o /path/to/output
```

Alternatively, place a `password.txt` file in the Mandiri statements folder with the password on the first line - it will be used automatically.

## Customization Options

### Date Format

Control how dates appear in the CSV output and filenames. Must include both month and year components.

**Using Presets:**
```bash
# ISO 8601 format via preset
python process_statements.py input/statements all --date-format "yyyymmdd"

# Month and Year only
python process_statements.py input/statements all --date-format "mmyyyy"

# Full month name
python process_statements.py input/statements all --date-format "mmmm"
```

**Using Custom strftime Formats:**
```bash
# YYYY-MM-DD format
python process_statements.py input/statements bca --date-format "%Y-%m-%d"

# DD-Mon-YYYY format
python process_statements.py input/statements bca --date-format "%d-%b-%Y"

# Full date with month name
python process_statements.py input/statements bca --date-format "%d %B %Y"

# Month/Year only
python process_statements.py input/statements bca --date-format "%m/%Y"
```

**Available Date Format Presets:**
- `dd/mm/yyyy` → 15/03/2025
- `ddmmyyyy` → 15032025
- `mmyyyy` → 032025
- `mmmm` → March
- `mm` → Mar
- `yyyymmdd` → 20250315

**strftime Format Components:**
- `%d` - Day (01-31)
- `%m` - Month number (01-12)
- `%B` - Full month name (January, February, ...)
- `%b` - Short month name (Jan, Feb, ...)
- `%Y` - Year 4-digit (2025)
- `%y` - Year 2-digit (25)

### Debit/Credit Handling

Choose how transaction amounts are displayed:

```bash
# Separate Debit and Credit columns (default)
python process_statements.py input/statements all

# Combined Amount column: debit=positive, credit=negative
python process_statements.py input/statements all --combine-debit-credit
```

### Column Visibility

Include or exclude optional columns from the output:

```bash
# Exclude reference numbers
python process_statements.py input/statements all --no-reference

# Exclude balance column
python process_statements.py input/statements all --no-balance

# Exclude bank name column
python process_statements.py input/statements all --no-bank

# Exclude owner name column
python process_statements.py input/statements all --no-owner

# Minimal output: only Date, Description, Amount, Balance
python process_statements.py input/statements all --combine-debit-credit --no-reference --no-bank --no-owner
```

### Currency

Specify currency code and optionally add a currency column:

```bash
# Set currency to USD (default: IDR)
python process_statements.py input/statements all --currency USD

# Add currency column to output
python process_statements.py input/statements all --currency EUR --include-currency

# Combined options
python process_statements.py input/statements all --currency SGD --include-currency --combine-debit-credit
```

### Custom Filenames

Define custom output filename format using placeholders:

```bash
# Available placeholders:
# {bank}, {owner}, {account}, {currency}, {start_date}, {end_date}

# Example 1: Bank_Owner_DateRange format
python process_statements.py input/statements all --filename-format "{bank}_{owner}_{start_date}_to_{end_date}.csv"

# Example 2: Account number with date
python process_statements.py input/statements all --filename-format "{account}_{currency}_{start_date}.csv"

# Example 3: Simple date-based
python process_statements.py input/statements all --date-format "%Y-%m-%d" --filename-format "{bank}_{start_date}.csv"
```

### Combined Examples

```bash
# Professional format: ISO dates, combined amount, include currency, minimal columns
python process_statements.py input/statements all \
  --date-format "%Y-%m-%d" \
  --combine-debit-credit \
  --include-currency \
  --no-reference \
  --no-bank \
  --no-owner

# Readable format: Day-Month-Year, separate debit/credit, all columns
python process_statements.py input/statements all \
  --date-format "%d-%b-%Y" \
  --currency IDR \
  --include-currency

# Minimal format: Month-Year only, combined amount, no optional columns
python process_statements.py input/statements all \
  --date-format "%m/%Y" \
  --combine-debit-credit \
  --no-reference \
  --no-balance \
  --no-bank \
  --no-owner \
  --filename-format "{bank}_{account}_{start_date}.csv"

# Custom output with specific date format for filenames
python process_statements.py input/statements all \
  --date-format "%Y-%m-%d" \
  --combine-debit-credit \
  --filename-format "{bank}-{owner}-{account}-{start_date}.csv" \
  -o "output/formatted"
```

## Output Format

The tool generates CSV files with columns based on your configuration. Here's an example with default settings:

## Input File Requirements

### Automatic File Detection

The tool **automatically detects and parses** bank statements using the default download filenames generated by each bank. Just point it to a folder and it will identify and process the correct files.

**Supported Default Filenames:**

**BCA:**
```
[AccountNumber]_[MONTH]_[YEAR].pdf
Example: [ACCOUNT_NUMBER]_JUL_2025.pdf
```

**Mandiri:**
```
e-Statement_[AccountNumber]_[StartDate]-[EndDate].xlsx
Example: e-Statement_[ACCOUNT_NUMBER]_01 Apr 2024-30 Apr 2024.xlsx
```

**CIMB:**
```
CASA_Statement_[Date][Timestamp].pdf
Example: CASA_Statement_Nov2025_[TIMESTAMP].pdf
```

### Custom Naming

You can also rename files with the bank name or keywords. The tool will recognize:

| Bank | Accepted Patterns |
|------|-------------------|
| BCA | Filename contains "bca" or month names (JUL, AGUST, SEPT, OKT, NOV, DES, JAN, FEB, MAR, APR, MEI, JUN) |
| Mandiri | Filename contains "mandiri" or starts with "e-statement" |
| CIMB | Filename contains "cimb" or "casa" |

### File Filtering

The tool uses a **3-step validation process** to ensure accuracy:

1. **Filename Pattern Check**: File must match bank's naming pattern
2. **Extension Check**: File must have the correct format (pdf for BCA/CIMB, xlsx/xls for Mandiri)
3. **Content Validation**: First page/rows scanned for bank-specific keywords

This prevents false positives and ensures only real bank statements are processed.

## Output Format

The tool generates CSV files with columns based on your configuration. Here's an example with default settings:

| Column | Description | Customizable |
|--------|-------------|--------------|
| Date | Transaction date (default: YYYY-MM-DD) | ✓ Format with `--date-format` |
| Description | Transaction details/memo | - |
| Reference No | Transaction reference number | ✓ Exclude with `--no-reference` |
| Debit | Amount withdrawn | ✓ Combine with Credit using `--combine-debit-credit` |
| Credit | Amount deposited | ✓ Combine with Debit using `--combine-debit-credit` |
| Amount | Combined debit/credit amount* | ✓ Enable with `--combine-debit-credit` |
| Currency | Currency code (IDR, USD, etc.)* | ✓ Add with `--include-currency` |
| Balance | Account balance after transaction | ✓ Exclude with `--no-balance` |
| Bank | Bank name (BCA, Mandiri, CIMB) | ✓ Exclude with `--no-bank` |
| Owner | Account owner name | ✓ Exclude with `--no-owner` |

*Amount column appears only with `--combine-debit-credit` flag. Currency column appears only with `--include-currency` flag.

### Default Output Example

```csv
Date,Description,Reference No,Debit,Credit,Balance,Bank,Owner
2025-03-15,SWITCHING WITHDRAWAL DI 009 INDOMARET,XYZ123,250000.0,0,506470.99,BCA,NIGEL IHZA FIRDAUSY
2025-03-15,TRANSFER CREDIT,ABC456,0,150000.0,756470.99,BCA,NIGEL IHZA FIRDAUSY
```

### Custom Output Example (with `--combine-debit-credit --include-currency --no-reference`)

```csv
Date,Description,Amount,Currency,Balance,Bank,Owner
15-Mar-2025,SWITCHING WITHDRAWAL DI 009 INDOMARET,250000.0,IDR,506470.99,BCA,NIGEL IHZA FIRDAUSY
15-Mar-2025,TRANSFER CREDIT,-150000.0,IDR,756470.99,BCA,NIGEL IHZA FIRDAUSY
```

### Output Filename Format

Default format:
```
{BankName}-[{OwnerName}]-{AccountNumber}-{StartDate}-{EndDate}.csv
```

Example with default date format:
```
BCA-[NIGEL IHZA FIRDAUSY]-0374656844-01/03/2025-31/03/2025.csv
```

Example with custom format (`--date-format "%Y-%m-%d"`):
```
BCA-[NIGEL IHZA FIRDAUSY]-0374656844-2025-03-01-2025-03-31.csv
```

Example with custom filename (`--filename-format "{bank}_{account}_{start_date}.csv"`):
```
BCA_0374656844_2025-03-01.csv
```

## Practical Examples

### Example 1: Basic Processing (Default Format)

Process all BCA files with default settings:

```bash
python process_statements.py "C:\Users\Documents\Statements" bca
```

Output: CSV with standard format (dd/mm/yyyy, separate debit/credit, all columns)

### Example 2: Professional Format for Analysis

ISO date format, combined amounts, minimal columns, include currency:

```bash
python process_statements.py "D:\Financial\2025" all \
  --date-format "%Y-%m-%d" \
  --combine-debit-credit \
  --include-currency \
  --no-reference
```

Output files: `BCA-[Owner]-account-2025-01-01-2025-01-31.csv`

### Example 3: Human-Readable Format

Full month names with day, readable date format:

```bash
python process_statements.py input/statements mandiri \
  --date-format "%d %B %Y" \
  --currency IDR \
  --include-currency \
  -p "your-password" \
  -o "output/monthly"
```

### Example 4: Minimal Monthly Summary

Month-Year only, combined amounts, exclude optional columns:

```bash
python process_statements.py input/statements all \
  --date-format "%B %Y" \
  --combine-debit-credit \
  --no-reference \
  --no-balance \
  --no-bank \
  --no-owner \
  --currency EUR \
  --include-currency
```

### Example 5: Custom Filename with Account and Date Range

Process with ISO format dates and custom filename:

```bash
python process_statements.py input/statements cimb \
  --date-format "%Y-%m-%d" \
  --combine-debit-credit \
  --filename-format "{bank}_{account}_{start_date}_to_{end_date}.csv" \
  -o "output/formatted"
```

Output: `CIMB_1234567890_2025-03-01_to_2025-03-31.csv`

### Example 6: Process Multiple Currencies

If processing statements from different banks/currencies:

```bash
# BCA statements (IDR)
python process_statements.py input/statements/bca bca \
  --currency IDR \
  --include-currency

# CIMB statements (SGD)
python process_statements.py input/statements/cimb cimb \
  --currency SGD \
  --include-currency

# Or all together with specified currency
python process_statements.py input/statements all \
  --currency IDR \
  --include-currency
```

### Example 7: Excel-Friendly Format

Readable dates, separate debit/credit (for pivot tables), simple custom filename:

```bash
python process_statements.py input/statements all \
  --date-format "%d/%m/%Y" \
  --no-reference \
  --currency IDR \
  --filename-format "{bank}_{account}_{start_date}.csv" \
  -o "output/excel-import"
```

## Input File Requirements

### Automatic File Detection

The tool **automatically detects and parses** bank statements using the default download filenames generated by each bank. Just point it to a folder and it will identify and process the correct files.

**Supported Default Filenames:**

**BCA:**
```
[AccountNumber]_[MONTH]_[YEAR].pdf
Example: [ACCOUNT_NUMBER]_JUL_2025.pdf
```

**Mandiri:**
```
e-Statement_[AccountNumber]_[StartDate]-[EndDate].xlsx
Example: e-Statement_[ACCOUNT_NUMBER]_01 Apr 2024-30 Apr 2024.xlsx
```

**CIMB:**
```
CASA_Statement_[Date][Timestamp].pdf
Example: CASA_Statement_Nov2025_[TIMESTAMP].pdf
```

### Custom Naming

You can also rename files with the bank name or keywords. The tool will recognize:

| Bank | Accepted Patterns |
|------|-------------------|
| BCA | Filename contains "bca" or month names (JUL, AGUST, SEPT, OKT, NOV, DES, JAN, FEB, MAR, APR, MEI, JUN) |
| Mandiri | Filename contains "mandiri" or starts with "e-statement" |
| CIMB | Filename contains "cimb" or "casa" |

### File Filtering

The tool uses a **3-step validation process** to ensure accuracy:

1. **Filename Pattern Check**: File must match bank's naming pattern
2. **Extension Check**: File must have the correct format (pdf for BCA/CIMB, xlsx/xls for Mandiri)
3. **Content Validation**: First page/rows scanned for bank-specific keywords

This prevents false positives and ensures only real bank statements are processed.

## Data Privacy & Security

**Notice**: This tool processes financial documents containing personal and sensitive information including account numbers, balances, and transaction details. Store files securely and do not share CSV exports publicly.

### What Information the Tool Processes

The tool extracts and stores:
- Account numbers
- Account owner names
- Transaction details and amounts
- Reference numbers
- Account balances

### Best Practices

1. **Store in secure location**:
   - Don't keep in public/shared locations
   - Use encrypted storage if available
   - Set appropriate file permissions

2. **Handle CSV exports carefully**:
   - Do not share via email or cloud without encryption
   - Do not commit to public git repositories
   - Delete processed files when no longer needed

3. **Keep original statement files secure**:
   - Store with the same security as you would at the bank
   - Delete original files after processing if you don't need them
   - Do not share file names or locations with others

## Troubleshooting

### "No matching bank statement files were found" or "Skipped (not a valid [BANK] statement)"

**Causes:**
- Filename doesn't contain the bank name
- File extension is incorrect for the bank
- File content doesn't match bank-specific keywords
- PDF/Excel file is corrupted or uses non-standard format

**Solutions:**
1. Check filename contains bank keyword:
   - ✓ Good: `bca-december-2025.pdf`
   - ✗ Bad: `december-2025.pdf` (missing "bca")

2. Check file extension:
   - BCA/CIMB must end with `.pdf`
   - Mandiri must end with `.xlsx` or `.xls`

3. Verify it's a real bank statement by opening the file manually

4. Rename file to include bank name if needed:
   ```bash
   # Rename to include bank name
   mv December-Statement.pdf bca-December-Statement.pdf
   ```

### "Skipped (error validating)"

The tool couldn't read the file to validate content. This might be due to:
- File is corrupted
- Unusual file encoding
- File permissions
- Non-standard format

Try opening the file in a PDF reader or Excel to verify it's valid.

### "No transactions found in [filename]"

- The statement format may have changed
- The file may be empty or contain no transaction data
- The statement may use an unsupported format variant

### "Error parsing [bank name] file"

- The statement format differs from what the parser expects
- Try opening the file manually to check its structure
- Report the issue if it's a valid bank statement with unexpected format

### File Processing Output Meanings

- `✓ Valid statement:` File passed all validation checks and will be processed
- `✗ Skipped (not a valid [BANK] statement):` File matched criteria but content didn't match
- `✗ Skipped (error validating):` File couldn't be read or validated

## Supported Python Versions

- Python 3.7+
- Python 3.8+
- Python 3.9+
- Python 3.10+
- Python 3.11+

## Dependencies

See `requirements.txt` for the complete list:

```
pandas>=1.0.0
pdfplumber>=0.5.0
openpyxl>=3.0.0
```

## License

This project is provided as-is for personal use.

## Notes

- The tool is specifically designed for Indonesian bank statements
- Date formats and transaction structures are Indonesian bank-specific
- Account owners and numbers are extracted automatically from statements
- Transaction descriptions are extracted as-is from the statements

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify your input files match the required format
3. Review the output in the `/output` folder
4. Check console output for detailed error messages
