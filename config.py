"""
Configuration and formatter for customizable CSV export options.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class DateFormatValidator:
    """Validates and processes custom date formats."""
    
    # Predefined common formats
    PRESETS = {
        "dd/mm/yyyy": "%d/%m/%Y",
        "ddmmyyyy": "%d%m%Y",
        "mmyyyy": "%m%Y",
        "mmmm": "%B",
        "mm": "%b",
        "dd/mm": "%d/%m",
        "yyyymmdd": "%Y%m%d",
    }
    
    @staticmethod
    def validate_and_get_format(format_string: str) -> str:
        """
        Validate and convert format string to strftime format.
        
        Requires that format contains both month and year components.
        
        Args:
            format_string: User-provided format (preset name or custom strftime)
            
        Returns:
            Valid strftime format string
            
        Raises:
            ValueError: If format doesn't contain both month and year
        """
        # Check if it's a preset
        if format_string.lower() in DateFormatValidator.PRESETS:
            return DateFormatValidator.PRESETS[format_string.lower()]
        
        # For custom formats, validate it contains both month and year
        # Check for month indicator in strftime format: %m, %b, %B
        has_month = '%m' in format_string or '%b' in format_string or '%B' in format_string
        
        # Check for year indicator in strftime format: %Y, %y
        has_year = '%Y' in format_string or '%y' in format_string
        
        if not has_month or not has_year:
            raise ValueError(
                f"Date format '{format_string}' must contain both month (%%m, %%b, %%B) "
                f"and year (%%Y, %%y) components."
            )
        
        # Validate it's a valid strftime format by testing it
        try:
            test_date = datetime(2025, 1, 15)
            test_date.strftime(format_string)
            return format_string
        except ValueError as e:
            raise ValueError(f"Invalid date format '{format_string}': {str(e)}")


class OutputFormat:
    """
    Configuration for CSV output formatting with customizable options.
    
    Features:
    - Custom date formats (must include month and year)
    - Combined or separate debit/credit columns
    - Optional columns (Reference, Balance, Bank, Owner)
    - Custom currency handling
    - Custom filename format
    """
    
    def __init__(
        self,
        date_format: str = "%d/%m/%Y",  # strftime format
        combine_debit_credit: bool = False,  # True = single Amount column (debit positive, credit negative)
        include_reference: bool = True,
        include_balance: bool = True,
        include_bank: bool = True,
        include_owner: bool = True,
        currency: str = "IDR",  # Currency code (IDR, USD, etc.)
        include_currency_col: bool = False,  # Add currency as a column
        filename_format: Optional[str] = None,  # Custom filename format
    ):
        """
        Initialize output format configuration.
        
        Args:
            date_format: strftime format for dates. Must contain both month and year.
                        Examples: '%d/%m/%Y', '%d%m%Y', '%m%Y', '%B', '%b'
                        Presets also supported: 'dd/mm/yyyy', 'ddmmyyyy', 'mmyyyy', 'mmmm', 'mm'
            combine_debit_credit: If True, use single "Amount" column with 
                                 debit as positive, credit as negative
            include_reference: Include "Reference No" column
            include_balance: Include "Balance" column
            include_bank: Include "Bank" column
            include_owner: Include "Owner" column
            currency: Currency code (e.g., "IDR", "USD")
            include_currency_col: If True, add a "Currency" column
            filename_format: Custom filename template. Available placeholders:
                           {bank}, {owner}, {account}, {currency}, {start_date}, {end_date}
                           If None, uses default: {bank}-[{owner}]-{account}-{start_date}-{end_date}.csv
        """
        # Validate and set date format
        self.date_format = DateFormatValidator.validate_and_get_format(date_format)
        self.combine_debit_credit = combine_debit_credit
        self.include_reference = include_reference
        self.include_balance = include_balance
        self.include_bank = include_bank
        self.include_owner = include_owner
        self.currency = currency
        self.include_currency_col = include_currency_col
        self.filename_format = filename_format or "{bank}-[{owner}]-{account}-{start_date}-{end_date}.csv"
    
    def format_date(self, date: datetime) -> str:
        """
        Format a date according to the configured format.
        
        Args:
            date: datetime object to format
            
        Returns:
            Formatted date string
        """
        try:
            return date.strftime(self.date_format)
        except Exception as e:
            print(f"Warning: Could not format date {date} with format {self.date_format}: {e}")
            return date.strftime("%Y-%m-%d")  # Fallback
    
    def get_column_names(self) -> List[str]:
        """
        Get the list of column names based on current configuration.
        
        Returns:
            List of column names for the CSV output
        """
        columns = ["Date", "Description"]
        
        if self.include_reference:
            columns.append("Reference No")
        
        if self.combine_debit_credit:
            columns.append("Amount")
            if self.include_currency_col:
                columns.append("Currency")
        else:
            columns.append("Debit")
            columns.append("Credit")
            if self.include_currency_col:
                columns.append("Currency")
        
        if self.include_balance:
            columns.append("Balance")
        
        if self.include_bank:
            columns.append("Bank")
        
        if self.include_owner:
            columns.append("Owner")
        
        return columns
    
    def format_filename(
        self,
        bank_name: str,
        owner_name: str,
        account_number: str,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """
        Format the output filename based on configuration.
        
        Args:
            bank_name: Bank name (e.g., "BCA", "Mandiri")
            owner_name: Account owner name
            account_number: Account number
            start_date: Statement start date
            end_date: Statement end date
            
        Returns:
            Formatted filename (without path)
        """
        # Sanitize owner name
        owner_safe = "".join(
            [c for c in owner_name if c.isalpha() or c.isspace() or c in ["."]]
        ).strip()
        
        format_dict = {
            "bank": bank_name,
            "owner": owner_safe,
            "account": account_number,
            "currency": self.currency,
            "start_date": self.format_date(start_date),
            "end_date": self.format_date(end_date),
        }
        
        try:
            return self.filename_format.format(**format_dict)
        except KeyError as e:
            print(f"Warning: Unknown placeholder in filename format: {e}")
            # Fallback to default format
            return f"{bank_name}-[{owner_safe}]-{account_number}-{self.format_date(start_date)}-{self.format_date(end_date)}.csv"


def from_args(args) -> OutputFormat:
    """
    Create an OutputFormat from command-line arguments.
    
    Args:
        args: argparse Namespace object
        
    Returns:
        OutputFormat instance
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        return OutputFormat(
            date_format=args.date_format,
            combine_debit_credit=args.combine_debit_credit,
            include_reference=not args.no_reference,
            include_balance=not args.no_balance,
            include_bank=not args.no_bank,
            include_owner=not args.no_owner,
            currency=args.currency,
            include_currency_col=args.include_currency,
            filename_format=args.filename_format,
        )
    except ValueError as e:
        print(f"Error: Invalid date format configuration: {e}")
        raise
