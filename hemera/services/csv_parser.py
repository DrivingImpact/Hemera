"""CSV/Excel ingestion — parse, normalise, deduplicate accounting data."""

import io
import pandas as pd
from hemera.models.transaction import Transaction


# Common column name variations across accounting software
COLUMN_MAP = {
    # Date columns
    "date": "date", "transaction date": "date", "trans date": "date",
    "posted date": "date", "invoice date": "date", "payment date": "date",
    # Description columns
    "description": "description", "memo": "description", "narrative": "description",
    "details": "description", "transaction description": "description",
    "reference": "description", "particulars": "description",
    # Supplier/payee columns
    "supplier": "supplier", "payee": "supplier", "vendor": "supplier",
    "contact": "supplier", "name": "supplier", "paid to": "supplier",
    "company": "supplier", "merchant": "supplier",
    # Amount columns
    "amount": "amount", "total": "amount", "net": "amount",
    "debit": "amount", "gross": "amount", "value": "amount",
    "net amount": "amount", "total amount": "amount",
    # Category/nominal code columns
    "category": "category", "nominal code": "category", "account": "category",
    "account name": "category", "nominal": "category", "gl code": "category",
    "type": "category", "expense type": "category", "cost centre": "category",
}


def parse_accounting_csv(
    file_bytes: bytes,
    filename: str,
    engagement_id: int,
) -> tuple[list[Transaction], dict]:
    """Parse an accounting CSV or Excel file into Transaction objects.

    Returns:
        (list of Transaction objects, summary dict)
    """
    # Read into pandas
    if filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        # Try common encodings
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8", errors="replace")

    # Normalise column names
    df.columns = [_normalise_column(c) for c in df.columns]

    # Ensure required columns exist
    if "amount" not in df.columns:
        raise ValueError(
            f"No amount column found. Columns detected: {list(df.columns)}. "
            "Please ensure your CSV has a column for transaction amounts."
        )

    # Parse dates
    if "date" in df.columns:
        df["parsed_date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    else:
        df["parsed_date"] = pd.NaT

    # Clean amounts — handle negatives, remove currency symbols
    df["clean_amount"] = df["amount"].apply(_clean_amount)

    # Remove zero-amount rows
    df = df[df["clean_amount"].abs() > 0.01].copy()

    # Deduplicate — same date + supplier + amount
    original_count = len(df)
    dedup_cols = []
    if "date" in df.columns:
        dedup_cols.append("date")
    if "supplier" in df.columns:
        dedup_cols.append("supplier")
    dedup_cols.append("clean_amount")

    if len(dedup_cols) >= 2:
        df = df.drop_duplicates(subset=dedup_cols, keep="first")
    duplicates_removed = original_count - len(df)

    # Build Transaction objects
    transactions = []
    for idx, row in df.iterrows():
        t = Transaction(
            engagement_id=engagement_id,
            row_number=int(idx) + 1,
            raw_date=str(row.get("date", "")) if pd.notna(row.get("date")) else None,
            raw_description=str(row.get("description", "")) if pd.notna(row.get("description")) else None,
            raw_supplier=str(row.get("supplier", "")) if pd.notna(row.get("supplier")) else None,
            raw_amount=float(row["clean_amount"]) if pd.notna(row["clean_amount"]) else None,
            raw_category=str(row.get("category", "")) if pd.notna(row.get("category")) else None,
            transaction_date=row["parsed_date"].date() if pd.notna(row["parsed_date"]) else None,
            amount_gbp=float(row["clean_amount"]) if pd.notna(row["clean_amount"]) else None,
        )
        transactions.append(t)

    # Summary
    unique_suppliers = set()
    for t in transactions:
        if t.raw_supplier:
            unique_suppliers.add(t.raw_supplier.strip().lower())

    dates = [t.transaction_date for t in transactions if t.transaction_date]
    date_range = None
    if dates:
        date_range = f"{min(dates).isoformat()} to {max(dates).isoformat()}"

    summary = {
        "unique_suppliers": len(unique_suppliers),
        "date_range": date_range,
        "total_spend": sum(t.amount_gbp for t in transactions if t.amount_gbp),
        "duplicates_removed": duplicates_removed,
    }

    return transactions, summary


def _normalise_column(col: str) -> str:
    """Map a column header to a standard name."""
    clean = col.strip().lower().replace("_", " ").replace("-", " ")
    return COLUMN_MAP.get(clean, clean)


def _clean_amount(val) -> float:
    """Convert an amount value to a float, handling currency symbols and commas."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # Remove currency symbols and whitespace
    for char in ["£", "$", "€", ",", " "]:
        s = s.replace(char, "")
    # Handle brackets as negative (accounting convention)
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return 0.0
