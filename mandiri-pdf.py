import re
import pdfplumber
from datetime import datetime
from typing import List
from base import BaseParser, Transaction

class MandiriPDFParser(BaseParser):
    def __init__(self, file_path: str, account_owner: str, password: str = None):
        super().__init__(file_path, account_owner)
        self.password = password
    
    def parse(self) -> List[Transaction]:
        transactions = []
        
        try:
            with pdfplumber.open(self.file_path, password=self.password) as pdf:
                # Extract header info from first page
                first_page_text = pdf.pages[0].extract_text()
                
                if first_page_text:
                    # Extract account owner
                    name_match = re.search(r'Nama/Name\s*:\s*([A-Z\s]+?)(?:\s+Periode|$)', first_page_text)
                    if name_match:
                        self.account_owner = name_match.group(1).strip()
                    
                    # Extract account number
                    acct_match = re.search(r'Nomor Rekening/Account Number\s*:\s*(\d+)', first_page_text)
                    if acct_match:
                        self.account_number = acct_match.group(1)
                
                # Parse transactions from all pages
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    i = 0
                    
                    while i < len(lines):
                        line = lines[i].strip()
                        
                        date_match = re.match(r'^(\d{2})\s+(\w+)\s+(\d{4})$', line)
                        
                        if date_match:
                            day_str = date_match.group(1)
                            month_str = date_match.group(2)
                            year_str = date_match.group(3)
                            
                            try:
                                tx_date = datetime.strptime(f"{day_str} {month_str} {year_str}", "%d %b %Y")
                            except:
                                i += 1
                                continue
                            
                            desc_before = ""
                            if i > 0:
                                prev_line = lines[i-1].strip()
                                if prev_line and not re.match(r'^\d', prev_line) and prev_line not in ['WIB']:
                                    desc_before = prev_line
                            
                            tx_lines = []
                            i += 1
                            
                            while i < len(lines):
                                next_line = lines[i].strip()
                                
                                if re.match(r'^\d{2}\s+\w+\s+\d{4}$', next_line):
                                    break
                                
                                if next_line.startswith('No ') or 'PT Bank' in next_line or next_line.startswith('e-Statement'):
                                    break
                                
                                tx_lines.append(next_line)
                                i += 1
                                
                                if any(re.search(r'[\d,]+\.\d{2}\s+[\d,]+', tl) for tl in tx_lines[-3:]):
                                    break
                            
                            combined = " ".join([desc_before] + tx_lines).strip()
                            
                            amount_pattern = r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})'
                            matches = list(re.finditer(amount_pattern, combined))
                            
                            amount = 0.0
                            balance = 0.0
                            tx_type = "DEBIT"
                            
                            if matches:
                                amt_match = matches[0]
                                amt_str = amt_match.group(1)
                                amt_val = self._parse_amount(amt_str)
                                
                                if amt_val < 0:
                                    amount = abs(amt_val)
                                    tx_type = "DEBIT"
                                else:
                                    amount = amt_val
                                    tx_type = "CREDIT"
                                
                                if len(matches) > 1:
                                    bal_match = matches[-1]
                                    bal_str = bal_match.group(1)
                                    balance = self._parse_amount(bal_str)
                            
                            full_desc = combined
                            for m in reversed(matches):
                                s, e = m.span()
                                full_desc = full_desc[:s] + " " + full_desc[e:]
                            
                            full_desc = re.sub(r'^\d+\s+', '', full_desc)
                            full_desc = re.sub(r'\s+', ' ', full_desc).strip()
                            
                            tr = Transaction(
                                date=tx_date,
                                description=full_desc,
                                amount=amount,
                                type=tx_type,
                                balance=balance,
                                reference_no="",
                                bank_name="Mandiri",
                                account_owner=self.account_owner
                            )
                            transactions.append(tr)
                        else:
                            i += 1
                            
        except Exception as e:
            print(f"Error parsing Mandiri PDF {self.file_path}: {e}")
            import traceback
            traceback.print_exc()
        
        return transactions
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse Mandiri format: -5.500,00 -> -5500.0"""
        if not amount_str:
            return 0.0
        
        # Remove spaces
        s = amount_str.strip()
        
        # Handle sign
        is_negative = s.startswith('-')
        s = s.lstrip('+-')
        
        # Mandiri format: 5.500,00 (. = thousands, , = decimal)
        # Convert to standard format
        s = s.replace('.', '')  # Remove thousands separator
        s = s.replace(',', '.')  # Replace decimal comma with dot
        
        try:
            val = float(s)
            if is_negative:
                val = -val
            return val
        except:
            return 0.0
