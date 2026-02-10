import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
import pandas as pd
import re

if TYPE_CHECKING:
    from config import OutputFormat

@dataclass
class Transaction:
    date: datetime
    description: str
    amount: float = 0.0
    type: str = "DEBIT" # DEBIT or CREDIT
    balance: float = 0.0
    reference_no: str = ""
    bank_name: str = ""
    account_owner: str = ""
    currency: str = "IDR"  # Currency code
    
    def to_dict(self, output_format: Optional["OutputFormat"] = None):
        """
        Convert transaction to a dictionary based on output format.
        
        Args:
            output_format: OutputFormat configuration. If None, uses default format.
            
        Returns:
            Dictionary with formatted transaction data
        """
        if output_format is None:
            # Default format for backward compatibility
            return {
                "Date": self.date.strftime("%Y-%m-%d"),
                "Description": self.description,
                "Reference No": self.reference_no,
                "Debit": self.amount if self.type == "DEBIT" else 0,
                "Credit": self.amount if self.type == "CREDIT" else 0,
                "Balance": self.balance,
                "Bank": self.bank_name,
                "Owner": self.account_owner,
            }
        
        # Custom format
        result = {
            "Date": output_format.format_date(self.date),
            "Description": self.description,
        }
        
        if output_format.include_reference:
            result["Reference No"] = self.reference_no
        
        if output_format.combine_debit_credit:
            # Single Amount column: debit positive, credit negative
            amount = self.amount if self.type == "DEBIT" else -self.amount
            result["Amount"] = amount
            if output_format.include_currency_col:
                result["Currency"] = self.currency or output_format.currency
        else:
            # Separate Debit and Credit columns
            result["Debit"] = self.amount if self.type == "DEBIT" else 0
            result["Credit"] = self.amount if self.type == "CREDIT" else 0
            if output_format.include_currency_col:
                result["Currency"] = self.currency or output_format.currency
        
        if output_format.include_balance:
            result["Balance"] = self.balance
        
        if output_format.include_bank:
            result["Bank"] = self.bank_name
        
        if output_format.include_owner:
            result["Owner"] = self.account_owner
        
        return result

class BaseParser(abc.ABC):
    def __init__(self, file_path: str, account_owner: str):
        self.file_path = file_path
        self.account_owner = account_owner
        self.account_number = "Unknown"
        self.currency = "IDR"  # Default currency

    @abc.abstractmethod
    def parse(self) -> List[Transaction]:
        pass

    def export_csv(self, output_path: str, output_format: Optional["OutputFormat"] = None):
        """
        Export transactions to CSV with custom formatting.
        
        Args:
            output_path: Path to output CSV file
            output_format: OutputFormat configuration. If None, uses default format.
        """
        transactions = self.parse()
        if not transactions:
            print(f"No transactions found for {self.file_path}")
            return
            
        data = [t.to_dict(output_format) for t in transactions]
        df = pd.DataFrame(data)
        
        if output_format:
            # Use configured columns
            cols = output_format.get_column_names()
        else:
            # Default columns for backward compatibility
            cols = ["Date", "Description", "Reference No", "Debit", "Credit", "Balance", "Bank", "Owner"]
        
        # Ensure all cols exist
        for c in cols:
            if c not in df.columns:
                df[c] = None
        
        df = df[cols]
        df.to_csv(output_path, index=False)
        print(f"Exported {len(df)} transactions to {output_path}")

