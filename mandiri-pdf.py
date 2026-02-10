import re
import pdfplumber
from datetime import datetime
from typing import List
from base import BaseParser, Transaction

class MandiriPDFParser(BaseParser):
    def __init__(self, file_path: str, account_owner: str = None, password: str = None):
        super().__init__(file_path, account_owner or "Unknown")
        self.password = password
        self._extract_header_info()
    
    def _extract_header_info(self):
        """Extract account owner and number from PDF header"""
        try:
            with pdfplumber.open(self.file_path, password=self.password) as pdf:
                first_page_text = pdf.pages[0].extract_text()
                if first_page_text:
                    name_match = re.search(r'Nama/Name\s*:\s*([A-Z\s]+?)(?:\s+Periode|$)', first_page_text)
                    if name_match:
                        self.account_owner = name_match.group(1).strip()
                    
                    acct_match = re.search(r'Nomor\s+Rekening.*?:\s*(\d+)', first_page_text, re.IGNORECASE)
                    if acct_match:
                        self.account_number = acct_match.group(1).strip()
        except Exception as e:
            pass  # Use defaults if extraction fails
    
    def _parse_amount(self, amount_str: str) -> float:
        if not amount_str:
            return 0.0
        s = amount_str.strip()
        is_negative = s.startswith('-')
        s = s.lstrip('+-')
        s = s.replace('.', '').replace(',', '.')
        try:
            val = float(s)
            return -val if is_negative else val
        except:
            return 0.0
    
    def parse(self) -> List[Transaction]:
        transactions = []
        
        try:
            with pdfplumber.open(self.file_path, password=self.password) as pdf:
                
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    i = 0
                    
                    while i < len(lines):
                        line = lines[i].strip()
                        date_match = re.match(r'^(\d{2})\s+(\w+)\s+(\d{4})', line)
                        
                        if date_match:
                            day_str = date_match.group(1)
                            month_str = date_match.group(2)
                            year_str = date_match.group(3)
                            
                            try:
                                tx_date = datetime.strptime(f"{day_str} {month_str} {year_str}", "%d %b %Y")
                            except:
                                i += 1
                                continue
                            
                            desc_lines = []
                            tx_type = "DEBIT"
                            
                            if i > 0:
                                prev_line = lines[i-1].strip()
                                if prev_line and not re.match(r'^\d', prev_line) and prev_line != 'WIB' and len(prev_line) < 50:
                                    desc_lines.append(prev_line)
                            
                            after_date = line[date_match.end():].strip()
                            if after_date:
                                desc_lines.append(after_date)
                            
                            amount = 0.0
                            balance = 0.0
                            i += 1
                            
                            while i < len(lines):
                                next_line = lines[i].strip()
                                
                                if re.match(r'^(\d{2})\s+(\w+)\s+(\d{4})', next_line):
                                    break
                                
                                if next_line.startswith('No ') or 'PT Bank' in next_line or next_line.startswith('e-Statement'):
                                    break
                                
                                if not next_line or next_line == 'WIB':
                                    i += 1
                                    continue
                                
                                if re.search(r'[\d.]+,\d{2}\s+[\d.]+,\d{2}', next_line):
                                    amount_pattern = r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})'
                                    matches = list(re.finditer(amount_pattern, next_line))
                                    
                                    if matches:
                                        before_amount = next_line[:matches[0].start()].strip()
                                        before_amount = re.sub(r'^(\d{1,2})\s+', '', before_amount)
                                        if before_amount and not re.match(r'^\d+$', before_amount):
                                            desc_lines.append(before_amount)
                                        
                                        amt_str = matches[0].group(1)
                                        amt_val = self._parse_amount(amt_str)
                                        amount = abs(amt_val)
                                        tx_type = "DEBIT" if amt_val < 0 else "CREDIT"
                                        
                                        if len(matches) > 1:
                                            balance = self._parse_amount(matches[-1].group(1))
                                    
                                    i += 1
                                    if i < len(lines):
                                        skip_ts = lines[i].strip()
                                        ts_match = re.match(r'^(\d{2}:\d{2}:\d{2}\s+WIB)\s+(.*)', skip_ts)
                                        if ts_match:
                                            after_ts = ts_match.group(2).strip()
                                            if after_ts and not re.match(r'^(\d{2})\s+(\w+)\s+(\d{4})', after_ts):
                                                desc_lines.append(after_ts)
                                            i += 1
                                        elif re.match(r'^\d{2}:\d{2}:\d{2}', skip_ts):
                                            i += 1
                                            if i < len(lines):
                                                ref_code = lines[i].strip()
                                                if ref_code and not re.match(r'^(\d{2})\s+(\w+)\s+(\d{4})', ref_code) and not ref_code.startswith(('Pembayaran', 'Transfer', 'PT Bank', 'e-Statement', 'No ')):
                                                    desc_lines.append(ref_code)
                                                    i += 1
                                    break
                                
                                desc_lines.append(next_line)
                                i += 1
                            
                            description = " ".join(desc_lines).strip()
                            description = re.sub(r'^\d+\s+', '', description)
                            description = re.sub(r'\d{2}:\d{2}:\d{2}\s+WIB\s*', '', description)
                            description = re.sub(r'^No\s+Date\s+Remarks\s+Amount\s+\(\w+\)\s+Balance\s+\(\w+\)\s*', '', description, flags=re.IGNORECASE)
                            description = re.sub(r'^\d+\s+dari\s+\d+.*?4\s+of\s+7', '', description, flags=re.IGNORECASE)
                            description = re.sub(r'\s+', ' ', description).strip()
                            
                            if description and amount > 0:
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
                        else:
                            i += 1
                            
        except Exception as e:
            print(f"Error parsing Mandiri PDF {self.file_path}: {e}")
        
        return transactions
