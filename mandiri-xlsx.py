import pandas as pd
import re
from datetime import datetime
from typing import List
from base import BaseParser, Transaction
import warnings

# Suppress warnings for openpyxl
warnings.filterwarnings("ignore")

class MandiriXLSXParser(BaseParser):
    def __init__(self, file_path: str, account_owner: str, password: str = None):
        super().__init__(file_path, account_owner)
        self.password = password
    
    def parse(self) -> List[Transaction]:
        transactions = []
        
        try:
            # Handle password-protected Excel files
            if self.password:
                import io
                import msoffcrypto
                
                try:
                    # Decrypt the file to memory
                    with open(self.file_path, 'rb') as encrypted_file:
                        office_file = msoffcrypto.OfficeFile(encrypted_file)
                        office_file.load_key(password=self.password)
                        
                        decrypted = io.BytesIO()
                        office_file.decrypt(decrypted)
                        decrypted.seek(0)
                        
                        # Read the decrypted content
                        df = pd.read_excel(decrypted, sheet_name=0, header=None)
                except Exception as e:
                    print(f"Error decrypting {self.file_path}: {e}")
                    print("  Trying without password...")
                    df = pd.read_excel(self.file_path, sheet_name=0, header=None)
            else:
                # Read the Excel file without password
                df = pd.read_excel(self.file_path, sheet_name=0, header=None)
            
            # Find header row
            header_row_idx = None
            for idx, row in df.iterrows():
                # Explicitly convert to string to avoid float issues
                row_str = [str(x).lower() for x in row.tolist()]
                
                # Check for Name/Nama in first few rows to extract Owner
                full_row_str = " ".join(row_str)
                if 'nama' in full_row_str or 'name' in full_row_str:
                    orig_row_str = " ".join([str(x) for x in row.tolist()])
                    
                    # Pattern: Nama/Name followed by anything then ":" followed by the name
                    # We want to be greedy but stop at keywords like "Periode"
                    name_match = re.search(r'(?:Nama|Name).*?\s*:\s*(.*)', orig_row_str, re.IGNORECASE)
                    
                    if name_match:
                        raw_val = name_match.group(1).strip()
                        # Cleanup: split by " nan ", multiple spaces, or keywords
                        # Also replace common noise
                        clean_val = re.split(r'\s+nan\s+|\s{2,}|Periode|Period', raw_val, flags=re.IGNORECASE)[0].strip()
                        
                        if clean_val and clean_val.lower() not in ['nan', 'unknown', '']:
                             self.account_owner = clean_val

                if any('tanggal' in s for s in row_str) and (any('uraian' in s for s in row_str) or any('keterangan' in s for s in row_str)):
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                # Try finding just 'tanggal' and assuming it's the header
                for idx, row in df.iterrows():
                     if 'tanggal' in str(row[0]).lower():
                         header_row_idx = idx
                         break

            if header_row_idx is None:
                print(f"Could not find header row in {self.file_path}")
                return []

            # Find account number in header section (rows before header_row_idx)
            if header_row_idx > 0:
                header_section = df.iloc[:header_row_idx]
                for _, row in header_section.iterrows():
                    # force string conversion
                    row_str = " ".join([str(x) for x in row.tolist()])
                    match = re.search(r'(?:No\.?|Nomor)\s*Rekening\s*:?\s*(\d+)', row_str, re.IGNORECASE)
                    if match:
                        self.account_number = match.group(1)
                        break
            
            # If not found in header, check footer (rows after the last transaction)
            if self.account_number == "Unknown":
                for idx, row in df.iterrows():
                    # force string conversion
                    row_str = " ".join([str(x) for x in row.tolist()])
                    if 'rekening' in row_str.lower():
                        match = re.search(r'(\d{10,20})', row_str)
                        if match:
                            self.account_number = match.group(1)
                            break

            # Set column names
            # We map explicit columns based on header content
            header = df.iloc[header_row_idx].astype(str).str.lower()
            
            date_col_idx = -1
            desc_col_idx = -1
            debit_col_idx = -1
            credit_col_idx = -1
            balance_col_idx = -1
            
            for i, val in enumerate(header):
                val = str(val).lower() # Force string conversion
                if 'tanggal' in val: date_col_idx = i
                elif 'uraian' in val or 'keterangan' in val: desc_col_idx = i
                elif 'debet' in val or 'debit' in val or 'dana keluar' in val: debit_col_idx = i # Outgoing is Debit
                elif 'kredit' in val or 'credit' in val or 'dana masuk' in val: credit_col_idx = i # Incoming is Credit
                elif 'saldo' in val: balance_col_idx = i
                
            # Fallback to fixed indices if dynamic failing
            if date_col_idx == -1: date_col_idx = 4
            if desc_col_idx == -1: desc_col_idx = 7
            # Original parser used 15 for Credit (Income) and 18 for Debit (Expense)? 
            # Or was it 15=Incoming, 18=Outgoing?
            # Let's check the original parser again:
            # incoming = row[15]  # Dana Masuk
            # outgoing = row[18]  # Dana Keluar
            if credit_col_idx == -1: credit_col_idx = 15
            if debit_col_idx == -1: debit_col_idx = 18
            if balance_col_idx == -1: balance_col_idx = 21 # Guessing

            print(f"Indices: Date={date_col_idx}, Desc={desc_col_idx}, Debit={debit_col_idx}, Credit={credit_col_idx}")

            data_start = header_row_idx + 1 # +2 in original, let's start +1 and strict check
            
            for i in range(data_start, len(df)):
                row = df.iloc[i]
                
                # Check valid date using index
                if date_col_idx >= len(row): continue
                
                date_val = row[date_col_idx]
                if pd.isna(date_val): continue
                
                try:
                    if isinstance(date_val, datetime):
                        tx_date = date_val
                    else:
                        # Try parsing string
                        s = str(date_val).strip()
                        if not s or not s[0].isdigit(): continue
                        tx_date = pd.to_datetime(s, dayfirst=True)
                except:
                    continue
                    
                # Description
                description = ""
                if desc_col_idx < len(row):
                    description = str(row[desc_col_idx]).strip()
                    description = description.replace('\n', ' ').replace('nan', '')
                    description = re.sub(r'\s+', ' ', description)
                
                # Debit
                debit = 0.0
                if debit_col_idx < len(row):
                    val = row[debit_col_idx]
                    debit = self._parse_amount(val)
                
                # Credit
                credit = 0.0
                if credit_col_idx < len(row):
                    val = row[credit_col_idx]
                    credit = self._parse_amount(val)
                    
                # Balance
                balance = 0.0
                if balance_col_idx < len(row):
                     balance = self._parse_amount(row[balance_col_idx])
                
                amount = max(debit, credit)
                if debit > 0:
                    tx_type = "DEBIT"
                elif credit > 0:
                    tx_type = "CREDIT"
                else:
                    # No amount? skip
                    if amount == 0: continue
                    tx_type = "DEBIT" # Fallback?
                
                tr = Transaction(
                    date=tx_date,
                    description=description,
                    amount=amount,
                    type=tx_type,
                    balance=balance,
                    reference_no="",
                    bank_name="Mandiri",
                    account_owner=self.account_owner,
                    currency="IDR"
                )
                transactions.append(tr)
                
        except Exception as e:
            print(f"Error parsing Mandiri Excel {self.file_path}: {e}")
            import traceback
            traceback.print_exc()
            
        return transactions

    def _parse_amount(self, val):
        if pd.isna(val) or str(val).strip() == '-':
            return 0.0
        s = str(val).strip()
        s = s.replace('Rp', '').strip()
        # Mandiri: 1.000,00 -> 1000.00
        # If already float/int
        if isinstance(val, (int, float)):
            return float(val)
            
        # String parsing
        s = s.replace('.', '')
        s = s.replace(',', '.')
        try:
            return float(s)
        except:
            return 0.0
