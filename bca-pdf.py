import re
import pdfplumber
from datetime import datetime
from typing import List
from base import BaseParser, Transaction

class BCAPDFParser(BaseParser):
    def parse(self) -> List[Transaction]:
        transactions = []
        year = datetime.now().year
        running_balance = 0.0
        opening_balance = 0.0

        with pdfplumber.open(self.file_path) as pdf:
            # Extract Year and Account Number from first page
            first_page_text = pdf.pages[0].extract_text()
            if first_page_text:
                # Extract opening balance (SALDO AWAL)
                saldo_match = re.search(r'SALDO\s+AWAL\s*:?\s*([\d,]+\.?\d*)', first_page_text, re.IGNORECASE)
                if saldo_match:
                    saldo_str = saldo_match.group(1).replace(',', '')
                    try:
                        opening_balance = float(saldo_str)
                        running_balance = opening_balance
                    except:
                        opening_balance = 0.0
                
                # Year extraction
                match = re.search(r'PERIODE\s*:\s*\w+\s+(\d{4})', first_page_text, re.IGNORECASE)
                if match:
                    year = int(match.group(1))
                
                # NAMA : [Account Owner Name] or just Name before NO. REKENING
                # Sample: "[Account Owner Name] NO. REKENING : [Account Number]"
                name_match = re.search(r'(.*?)\s+NO\.?\s*REKENING', first_page_text, re.IGNORECASE)
                if name_match:
                    self.account_owner = name_match.group(1).strip().split('\n')[-1].strip()
                else:
                    # Fallback for older formats "NAMA : VALUE"
                    name_match = re.search(r'NAMA\s*:\s*(.*)', first_page_text, re.IGNORECASE)
                    if name_match:
                         self.account_owner = name_match.group(1).strip().split('\n')[0].strip()
                
                # NO. REKENING : [ACCOUNT_NUMBER]
                acct_match = re.search(r'NO\.?\s*REKENING\s*:?\s*(\d+)', first_page_text, re.IGNORECASE)
                if acct_match:
                    self.account_number = acct_match.group(1)

            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Regex for Date DD/MM at start of line
                    date_match = re.match(r'^(\d{2}/\d{2})\s+(.+)', line)
                    
                    if date_match and 'SALDO AWAL' not in line:
                        date_str = date_match.group(1) # DD/MM
                        rest_of_line = date_match.group(2)
                        
                        try:
                            day_str, month_str = date_str.split('/')
                            day = int(day_str)
                            month = int(month_str)
                            tx_date = datetime(year, month, day)
                        except ValueError:
                            # Fallback
                            tx_date = datetime(year, 1, 1)

                        # Collect lines
                        tx_lines = [rest_of_line]
                        i += 1
                        
                        while i < len(lines):
                            next_line = lines[i].strip()
                            # Stop if next line is a new transaction (Date DD/MM)
                            if re.match(r'^\d{2}/\d{2}\s+', next_line):
                                break
                            
                            # Stop if footer/header junk
                            if 'BERSAMBUNG' in next_line.upper() or 'SALDO' in next_line.upper():
                                if 'SALDO AWAL' in next_line or 'SALDO AKHIR' in next_line:
                                    break
                            
                            # Skip known noise headers
                            if any(x in next_line for x in ['KETERANGAN', 'TANGGAL', 'MUTASI', 'REKENING TAHAPAN', 'PERIODE']):
                                i += 1
                                continue
                                
                            tx_lines.append(next_line)
                            i += 1
                        
                        full_content = " ".join(tx_lines)
                        
                        # Logic to extract amounts and type
                        # Find all amounts with optional DB suffix
                        # Regex: ([\d,]+\.\d{2})(\s+DB)?
                        # Note: BCA uses ',' as thousands and '.' as decimal. 
                        # Example: 250,000.00
                        # Sometimes there is a space between number and DB: "106,161.00 DB"
                        
                        # Use a more robust regex that allows for spaces
                        # matches = list(re.finditer(r'([\d,]+\.\d{2})(\s+DB)?', full_content))
                        
                        # Simplified: just look for numbers with 2 decimals
                        matches = list(re.finditer(r'([\d,]+\.\d{2})', full_content))
                        
                        amount = 0.0
                        balance = 0.0
                        tx_type = "CREDIT"
                        
                        if matches:
                            # First match is the Transaction Amount
                            amt_match = matches[0]
                            amt_val_str = amt_match.group(1).replace(',', '')
                            try:
                                amount = float(amt_val_str)
                            except:
                                amount = 0.0
                            
                            # Check if DB suffix exists for this amount
                            # We need to check the string AFTER the amount in full_content
                            amt_end = amt_match.end()
                            # Check next few chars for "DB"
                            post_amt = full_content[amt_end:amt_end+5]
                            if 'DB' in post_amt:
                                tx_type = "DEBIT"
                            else:
                                tx_type = "CREDIT"
                                
                            # If there is a second or more matches, the last one is likely the Balance
                            # unless it also has DB/CR marker right after it
                            if len(matches) > 1:
                                # Try the last match first
                                bal_match = matches[-1]
                                bal_end = bal_match.end()
                                # Check if this last amount has DB/CR marker - if so, it's not the balance
                                post_bal = full_content[bal_end:bal_end+5]
                                
                                if 'DB' not in post_bal and 'CR' not in post_bal:
                                    # This is likely the balance
                                    bal_val_str = bal_match.group(1).replace(',', '')
                                    try:
                                        balance = float(bal_val_str)
                                    except:
                                        balance = 0.0
                                elif len(matches) > 2:
                                    # If last match has a marker, try the second-to-last
                                    bal_match = matches[-2]
                                    bal_val_str = bal_match.group(1).replace(',', '')
                                    try:
                                        balance = float(bal_val_str)
                                    except:
                                        balance = 0.0
                            
                            # Clean description by removing the amounts
                            # Reverse order removal
                            clean_desc = full_content
                            for m in reversed(matches):
                                s, e = m.span()
                                # Also remove " DB" if present after the amount
                                post = full_content[e:e+5]
                                if 'DB' in post:
                                    # Find exact end of "DB" or " DB"
                                    db_idx = post.find('DB')
                                    e += db_idx + 2
                                    
                                clean_desc = clean_desc[:s] + clean_desc[e:]
                        else:
                            clean_desc = full_content
                        
                        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                        
                        # Extract Reference No
                        # Pattern: 1234/XYZ/... or similar alphanumeric codes
                        # Ref: 0112/FTSCY/WS95031
                        ref_match = re.search(r'\b\d{4}/[A-Z0-9]+/[A-Z0-9]+\b', clean_desc)
                        ref_no = ""
                        if ref_match:
                            ref_no = ref_match.group(0)
                        
                        tr = Transaction(
                            date=tx_date,
                            description=clean_desc,
                            amount=amount,
                            type=tx_type,
                            balance=balance,
                            reference_no=ref_no,
                            bank_name="BCA",
                            account_owner=self.account_owner
                        )
                        
                        # If balance from PDF is 0, calculate from running balance
                        if balance == 0.0 and opening_balance > 0.0:
                            if tx_type == "DEBIT":
                                running_balance -= amount
                            else:
                                running_balance += amount
                            tr.balance = running_balance
                        else:
                            # If PDF has balance, use it and update running balance
                            if balance > 0.0:
                                running_balance = balance
                        
                        transactions.append(tr)
                        
                        continue # Processed this transaction
                        
                    i += 1
                    
        return transactions
