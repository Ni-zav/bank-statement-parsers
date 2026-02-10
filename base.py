import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import pandas as pd
import re

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
    
    def to_dict(self):
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

class BaseParser(abc.ABC):
    def __init__(self, file_path: str, account_owner: str):
        self.file_path = file_path
        self.account_owner = account_owner
        self.account_number = "Unknown"

    @abc.abstractmethod
    def parse(self) -> List[Transaction]:
        pass

    def export_csv(self, output_path: str):
        transactions = self.parse()
        if not transactions:
            print(f"No transactions found for {self.file_path}")
            return
            
        data = [t.to_dict() for t in transactions]
        df = pd.DataFrame(data)
        
        # Standardize columns ordering
        cols = ["Date", "Description", "Reference No", "Debit", "Credit", "Balance", "Bank", "Owner"]
        # Ensure all cols exist
        for c in cols:
            if c not in df.columns:
                df[c] = None
        
        df = df[cols]
        df.to_csv(output_path, index=False)
        print(f"Exported {len(df)} transactions to {output_path}")

