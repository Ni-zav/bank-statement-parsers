import re
import pdfplumber
from datetime import datetime
from typing import List
from base import BaseParser, Transaction

class CIMBPDFParser(BaseParser):
    def parse(self) -> List[Transaction]:
        transactions = []
        year = datetime.now().year 
        
        month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }

        with pdfplumber.open(self.file_path) as pdf:
            # Try to extract Year if possible or rely on line parsing
            
            # Extract Account Number from first page
            first_page_text = pdf.pages[0].extract_text()
            if first_page_text:
                # No. Rekening : [ACCOUNT_NUMBER]
                acct_match = re.search(r'No\.?\s*Rekening\s*:?\s*(\d+)', first_page_text, re.IGNORECASE)
                if acct_match:
                    self.account_number = acct_match.group(1)
            
            # Extract Name
            # Pattern: Name : [Account Owner Name]
            name_match = re.search(r'(?:Name|Nama)\s*:\s*(.*)', first_page_text, re.IGNORECASE)
            if name_match:
                # Take only the first line of the match to avoid capturing subsequent info
                self.account_owner = name_match.group(1).split('\n')[0].strip()
                    
            for page in pdf.pages:
                text = page.extract_text()
                if not text: 
                    continue
                
                lines = text.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Regex for Date: 01 Jan 2025
                    # Usually CIMB has full date on the line
                    date_match = re.match(r'^(\d{2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', line, re.IGNORECASE)
                    
                    if date_match and 'SALDO AWAL' not in line:
                        day = int(date_match.group(1))
                        month_str = date_match.group(2).title() # Ensure title case
                        year_val = int(date_match.group(3))
                        month = month_map.get(month_str, 1)
                        
                        tx_date = datetime(year_val, month, day)
                        
                        # The rest of the line contains Amount AND potentially part of description or type
                        rest_of_line = line[date_match.end():].strip()
                        
                        # Parse Amount from rest_of_line
                        # Look for number with optional negative sign
                        # Format: -100,000.00 or 100,000.00
                        # Usually at the end? No, Description usually follows?
                        # Let's check typical line structure.
                        # "01 Jan 2025 OVERBOOKING ... -100,000.00"
                        # Or "01 Jan 2025 ... 100,000.00"
                        
                        # Let's find all amount-like strings
                        amount_matches = list(re.finditer(r'(-?[\d,]+\.\d{2})', rest_of_line))
                        
                        amount = 0.0
                        balance = 0.0 # Often not present on every line in CIMB PDFs depending on format
                        tx_type = "CREDIT"
                        
                        # Use the last amount match as amount if only one?
                        # If multiple, last might be balance.
                        # But wait, CIMB PDF usually lists Amount then Balance? Or just Amount?
                        # The original parser looked for negative sign to determine debit.
                        
                        if amount_matches:
                            # Heuristic: Amount is usually the one with negative sign if debit
                            # Or the first number if credit?
                            # Let's check for negative number first
                            neg_found = False
                            for m in amount_matches:
                                val_str = m.group(1)
                                if val_str.startswith('-'):
                                    amount = abs(float(val_str.replace(',', '')))
                                    tx_type = "DEBIT"
                                    neg_found = True
                                    break
                            
                            if not neg_found:
                                # First number is amount (Credit)
                                val_str = amount_matches[0].group(1)
                                amount = float(val_str.replace(',', ''))
                                tx_type = "CREDIT"
                                
                            # Check for balance (usually second number if present)
                            if len(amount_matches) > 1:
                                bal_str = amount_matches[-1].group(1).replace(',', '')
                                # Verify it's not the same match object
                                if amount_matches[-1].start() != amount_matches[0].start():
                                    try:
                                        balance = float(bal_str)
                                    except:
                                        pass
                        
                        # Collect Description
                        # It spans multiple lines until next date
                        tx_lines = []
                        # Part of description might be in the first line before the amount?
                        # Or after date?
                        # We remove the date and amounts from the first line to get description part
                        
                        desc_part = rest_of_line
                        for m in reversed(amount_matches):
                            s, e = m.span()
                            desc_part = desc_part[:s] + desc_part[e:]
                        
                        tx_lines.append(desc_part.strip())
                        
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if re.match(r'^\d{2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', next_line, re.IGNORECASE):
                                break
                            
                            if 'Page' in next_line or 'Saldo' in next_line:
                                if 'Saldo Awal' in next_line or 'Saldo Akhir' in next_line:
                                    break
                            
                            tx_lines.append(next_line)
                            i += 1
                        
                        description = " ".join(tx_lines)
                        description = re.sub(r'\s+', ' ', description).strip()
                        
                        tr = Transaction(
                            date=tx_date,
                            description=description,
                            amount=amount,
                            type=tx_type,
                            balance=balance,
                            reference_no="",
                            bank_name="CIMB",
                            account_owner=self.account_owner,
                            currency="IDR"
                        )
                        transactions.append(tr)
                        
                        continue
                        
                    i += 1
                    
        return transactions
