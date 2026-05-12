import argparse
import csv
import importlib
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path


MONEY_MANAGER_HEADER = [
    "Date",
    "Account",
    "Category",
    "Subcategory",
    "Note",
    "IDR",
    "Income/Expense",
    "Description",
    "Amount",
    "Currency",
    "Account",
]

EXCEL_EPOCH = datetime(1899, 12, 30)


def excel_serial_date(value: datetime) -> str:
    delta = value - EXCEL_EPOCH
    serial = delta.days + (delta.seconds + delta.microseconds / 1_000_000) / 86400
    return f"{serial:.11f}".rstrip("0").rstrip(".")


def money_amount(value: float) -> str:
    if float(value).is_integer():
        return f"{float(value):.1f}"
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def parse_account_map(values):
    result = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Invalid --account-map value '{value}'. Use BANK=money-manager-account.")
        bank, account = value.split("=", 1)
        result[bank.strip().lower()] = account.strip()
    return result


def bank_key(bank_name: str) -> str:
    name = bank_name.lower()
    if "bca" in name:
        return "bca"
    if "mandiri" in name:
        return "mandiri"
    if "cimb" in name:
        return "cimb"
    return name


def default_account_name(transaction, owner_prefix: str) -> str:
    key = bank_key(transaction.bank_name)
    prefix = owner_prefix.strip().lower() if owner_prefix else "nigel"
    return f"{prefix}-{key}"


def compact_note(description: str) -> str:
    text = re.sub(r"\s+", " ", description or "").strip()
    replacements = [
        r"^Pembayaran QR ke\s+",
        r"^TRANSAKSI DEBIT TGL:\s*\d{2}/\d{2}\s+",
        r"^Transfer antar Mandiri DARI\s+",
        r"^Transfer antar Mandiri KE\s+",
        r"^BI-FAST CR BIF TRANSFER DR\s+\d+\s+",
        r"^BI-FAST DB BIF TRANSFER KE\s+\d+\s+",
    ]
    for pattern in replacements:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+\d{10,}$", "", text).strip()
    return text[:120] or (description or "").strip()[:120]


def classify_transaction(transaction, transfer_accounts):
    description = (transaction.description or "").upper()
    note = compact_note(transaction.description)

    transfer_match = re.search(
        r"(?:TRANSFER (?:KE|DR|DARI)|BI-FAST|ANTAR MANDIRI|TRSF|OVERBOOKING).*?([A-Z][A-Z\s.']{3,})",
        description,
    )
    if transfer_match and transaction.type == "DEBIT":
        candidate = compact_note(transfer_match.group(1)).lower()
        for account in transfer_accounts:
            if candidate and candidate in account.lower():
                return account, "Transfer-Out", note

    food_keywords = [
        "AYAM",
        "BAKSO",
        "BURGER",
        "CAFE",
        "COFFEE",
        "FOOD",
        "FRIE",
        "GOFOOD",
        "KOPI",
        "MCD",
        "RESTO",
        "RESTAURANT",
        "WARUNG",
    ]
    transport_keywords = ["GOJEK", "GRAB", "JOPARK", "PARKIR", "PARKING", "PERTAMINA", "TOL"]
    salary_keywords = ["PAYROLL", "SALARY", "GAJI"]
    fee_keywords = ["ADMIN", "BIAYA", "FEE"]

    if transaction.type == "CREDIT" and any(word in description for word in salary_keywords):
        return "Salary", "Income", note
    if any(word in description for word in food_keywords):
        return "Food", "Expense" if transaction.type == "DEBIT" else "Income", note
    if any(word in description for word in transport_keywords):
        return "Transport", "Expense" if transaction.type == "DEBIT" else "Income", note
    if any(word in description for word in fee_keywords):
        return "Other", "Expense", "Fees" if not note else note

    return "Other", "Expense" if transaction.type == "DEBIT" else "Income", note


def parser_for_file(file_path: Path, password=None):
    bca_pdf = importlib.import_module("bca-pdf")
    mandiri_xlsx = importlib.import_module("mandiri-xlsx")
    mandiri_pdf = importlib.import_module("mandiri-pdf")
    cimb_pdf = importlib.import_module("cimb-pdf")

    filename = file_path.name.lower()
    if filename.endswith(".pdf"):
        is_bca = "bca" in filename or any(
            month in filename
            for month in ["_jul_", "_agust_", "_sept_", "_okt_", "_nov_", "_des_", "_jan_", "_feb_", "_mar_", "_apr_", "_mei_", "_jun_"]
        )
        is_cimb = "cimb" in filename or "casa" in filename
        is_mandiri = "e-statement" in filename or "mandiri" in filename
        if is_mandiri and not is_cimb:
            return mandiri_pdf.MandiriPDFParser(str(file_path), "Unknown", password=password)
        if is_bca and not is_cimb and not is_mandiri:
            return bca_pdf.BCAPDFParser(str(file_path), "Unknown")
        if is_cimb:
            return cimb_pdf.CIMBPDFParser(str(file_path), "Unknown")
    if filename.endswith((".xlsx", ".xls")) and ("e-statement" in filename or "mandiri" in filename):
        return mandiri_xlsx.MandiriXLSXParser(str(file_path), "Unknown", password=password)
    return None


def find_bank_files(folder_path: Path, bank_name: str):
    bank_name = bank_name.lower()
    patterns = {
        "bca": {
            "extensions": (".pdf",),
            "filename_patterns": [
                "bca",
                "_jul_",
                "_agust_",
                "_sept_",
                "_okt_",
                "_nov_",
                "_des_",
                "_jan_",
                "_feb_",
                "_mar_",
                "_apr_",
                "_mei_",
                "_jun_",
                "_maret_",
                "_oktober_",
                "_desember_",
            ],
        },
        "mandiri": {
            "extensions": (".xlsx", ".xls", ".pdf"),
            "filename_patterns": ["mandiri", "e-statement"],
        },
        "cimb": {
            "extensions": (".pdf",),
            "filename_patterns": ["cimb", "casa"],
        },
    }
    if bank_name not in patterns:
        raise ValueError(f"Unknown bank '{bank_name}'. Use bca, mandiri, cimb, or all.")

    config = patterns[bank_name]
    matches = []
    for file_path in folder_path.rglob("*"):
        if not file_path.is_file():
            continue
        filename = file_path.name.lower()
        if not filename.endswith(config["extensions"]):
            continue
        if any(pattern in filename for pattern in config["filename_patterns"]):
            matches.append(file_path)
    return matches


def transactions_to_rows(transactions, account_map, owner_prefix, transfer_accounts):
    rows = []
    for transaction in transactions:
        category, kind, note = classify_transaction(transaction, transfer_accounts)
        account = account_map.get(bank_key(transaction.bank_name)) or default_account_name(transaction, owner_prefix)
        amount = money_amount(abs(transaction.amount))
        rows.append(
            [
                excel_serial_date(transaction.date),
                account,
                category,
                "",
                note,
                amount,
                kind,
                transaction.description,
                amount,
                transaction.currency or "IDR",
                amount,
            ]
        )
    return rows


def output_name(bank_name, account_name, transactions):
    dates = [t.date for t in transactions if t.date]
    start = min(dates).strftime("%Y%m%d") if dates else "unknown"
    end = max(dates).strftime("%Y%m%d") if dates else "unknown"
    safe_account = re.sub(r"[^A-Za-z0-9_.-]+", "-", account_name).strip("-") or "account"
    safe_bank = re.sub(r"[^A-Za-z0-9_.-]+", "-", bank_name).strip("-") or "bank"
    return f"{safe_bank}-{safe_account}-{start}-{end}.tsv"


def main():
    arg_parser = argparse.ArgumentParser(
        description="Convert supported bank statements to Money Manager-compatible TSV files."
    )
    arg_parser.add_argument("folder", help="Folder containing bank statements")
    arg_parser.add_argument("bank", nargs="?", default="all", help="bca, mandiri, cimb, or all")
    arg_parser.add_argument("-o", "--output", default="output", help="Output directory")
    arg_parser.add_argument("-p", "--password", default=None, help="Password for protected Mandiri files")
    arg_parser.add_argument(
        "--account-map",
        action="append",
        default=[],
        help="Map a bank to a Money Manager account, e.g. --account-map bca=nigel-bca",
    )
    arg_parser.add_argument(
        "--owner-prefix",
        default="nigel",
        help="Fallback account prefix when --account-map is not supplied, e.g. nigel -> nigel-bca",
    )
    arg_parser.add_argument(
        "--transfer-account",
        action="append",
        default=[],
        help="Known Money Manager account names used as transfer categories, e.g. tiya-mandiri",
    )
    arg_parser.add_argument(
        "--combined",
        action="store_true",
        help="Also write one combined Money Manager TSV containing all parsed transactions.",
    )
    args = arg_parser.parse_args()

    source_dir = Path(args.folder)
    if not source_dir.is_dir():
        print(f"Error: folder not found: {source_dir}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        account_map = parse_account_map(args.account_map)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    banks = ["bca", "mandiri", "cimb"] if args.bank.lower() == "all" else [args.bank.lower()]
    all_rows = []
    exported = 0

    for bank in banks:
        try:
            files = find_bank_files(source_dir, bank)
        except ValueError as exc:
            print(f"Error: {exc}")
            sys.exit(1)
        for file_path in files:
            parser = parser_for_file(file_path, password=args.password if bank == "mandiri" else None)
            if not parser:
                print(f"No parser found for {file_path}")
                continue
            try:
                transactions = parser.parse()
                if not transactions:
                    print(f"No transactions found in {file_path}")
                    continue
                account_name = account_map.get(bank_key(transactions[0].bank_name)) or default_account_name(
                    transactions[0], args.owner_prefix
                )
                rows = transactions_to_rows(transactions, account_map, args.owner_prefix, args.transfer_account)
                target = output_dir / output_name(transactions[0].bank_name, account_name, transactions)
                with target.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                    writer.writerow(MONEY_MANAGER_HEADER)
                    writer.writerows(rows)
                all_rows.extend(rows)
                exported += 1
                print(f"Exported {len(rows)} Money Manager rows to {target}")
            except Exception:
                print(f"Error processing {file_path}:")
                traceback.print_exc()

    if args.combined and all_rows:
        target = output_dir / "money-manager-combined.tsv"
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(MONEY_MANAGER_HEADER)
            writer.writerows(all_rows)
        print(f"Exported {len(all_rows)} combined Money Manager rows to {target}")

    if exported == 0:
        print("No matching bank statement files were exported.")
        sys.exit(1)


if __name__ == "__main__":
    main()
