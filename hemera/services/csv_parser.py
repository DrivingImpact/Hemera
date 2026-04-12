"""CSV/Excel ingestion — parse, normalise, deduplicate accounting data.

Supports two modes:
  - spend: traditional accounting CSV (date, supplier, amount in GBP)
  - activity: utility/fuel data (date, supplier, quantity in kWh/litres/m3/kg/km)
"""

import io
import pandas as pd
from hemera.models.transaction import Transaction


# Common column name variations across accounting software
COLUMN_MAP = {
    # Date columns
    "date": "date", "transaction date": "date", "trans date": "date",
    "posted date": "date", "invoice date": "date", "payment date": "date",
    "reading date": "date", "bill date": "date", "period": "date",
    # Description columns
    "description": "description", "memo": "description", "narrative": "description",
    "details": "description", "transaction description": "description",
    "reference": "description", "particulars": "description", "notes": "description",
    # Supplier/payee columns
    "supplier": "supplier", "payee": "supplier", "vendor": "supplier",
    "contact": "supplier", "name": "supplier", "paid to": "supplier",
    "company": "supplier", "merchant": "supplier", "provider": "supplier",
    "utility": "supplier",
    # Amount columns (spend mode)
    "amount": "amount", "total": "amount", "net": "amount",
    "debit": "amount", "gross": "amount", "value": "amount",
    "net amount": "amount", "total amount": "amount", "cost": "amount",
    # Category/nominal code columns
    "category": "category", "nominal code": "category", "account": "category",
    "account name": "category", "nominal": "category", "gl code": "category",
    "type": "category", "expense type": "category", "cost centre": "category",
}


# Unit detection: column name → (canonical unit, activity hint)
# The canonical unit is what we store in quantity_unit.
UNIT_COLUMN_MAP = {
    # Electricity
    "kwh": ("kWh", "electricity"),
    "kilowatt hours": ("kWh", "electricity"),
    "kilowatt-hours": ("kWh", "electricity"),
    "consumption kwh": ("kWh", "electricity"),
    "mwh": ("MWh", "electricity"),
    # Gas
    "therms": ("therms", "natural_gas"),
    "m3": ("m3", None),  # generic volume — could be gas or water
    "cubic metres": ("m3", None),
    "cubic meters": ("m3", None),
    # Fuel
    "litres": ("litres", None),
    "liters": ("litres", None),
    "l": ("litres", None),
    "gallons": ("gallons", None),
    # Waste
    "tonnes": ("tonnes", "waste"),
    "tons": ("tonnes", "waste"),
    "kg": ("kg", None),
    "kilos": ("kg", None),
    "kilograms": ("kg", None),
    # Distance
    "km": ("km", "distance"),
    "kilometres": ("km", "distance"),
    "kilometers": ("km", "distance"),
    "miles": ("miles", "distance"),
    "distance": ("km", "distance"),
    # Generic
    "quantity": ("quantity", None),
    "qty": ("quantity", None),
    "usage": ("quantity", None),
    "consumption": ("quantity", None),
}


# Valid activity types (for validation / normalisation)
VALID_ACTIVITY_TYPES = {
    "electricity",
    "natural_gas",
    "diesel",
    "petrol",
    "lpg",
    "heating_oil",
    "heat",
    "water",
    "waste",
    "distance",
    "refrigerants",
    "other",
}


def parse_accounting_csv(
    file_bytes: bytes,
    filename: str,
    engagement_id: int,
    data_type: str = "spend",
    activity_type: str | None = None,
    raw_activity_label: str | None = None,
) -> tuple[list[Transaction], dict]:
    """Parse an accounting CSV or Excel file into Transaction objects.

    Args:
        file_bytes: raw file contents
        filename: used only to detect .xlsx/.xls vs .csv
        engagement_id: FK for the new Transaction rows
        data_type: "spend" (default, backward-compatible) or "activity"
        activity_type: when data_type="activity", one of VALID_ACTIVITY_TYPES.
            Ignored for spend uploads. If "other", raw_activity_label is used
            to capture what the user typed.
        raw_activity_label: freeform label when activity_type is "other" or
            the client doesn't know the canonical type.

    Returns:
        (list of Transaction objects, summary dict)
    """
    data_type = data_type or "spend"
    if data_type not in ("spend", "activity"):
        raise ValueError(
            f"data_type must be 'spend' or 'activity', got {data_type!r}"
        )
    if data_type == "activity" and activity_type and activity_type not in VALID_ACTIVITY_TYPES:
        # Don't reject unknown labels — fall back to "other" + raw label
        raw_activity_label = raw_activity_label or activity_type
        activity_type = "other"

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

    # Detect activity-mode columns (quantity + unit) if in activity mode
    quantity_col, detected_unit, detected_hint = (None, None, None)
    if data_type == "activity":
        quantity_col, detected_unit, detected_hint = _detect_quantity_column(df)
        # If caller didn't supply activity_type but we detected one from columns, use it
        if not activity_type and detected_hint:
            activity_type = detected_hint
        if quantity_col is None:
            raise ValueError(
                f"No quantity column found for activity upload. Columns detected: {list(df.columns)}. "
                "Activity uploads need a numeric column named kWh, litres, m3, kg, km, etc."
            )

    # Validate: spend mode needs an amount column
    if data_type == "spend" and "amount" not in df.columns:
        raise ValueError(
            f"No amount column found. Columns detected: {list(df.columns)}. "
            "Please ensure your CSV has a column for transaction amounts."
        )

    # Parse dates
    if "date" in df.columns:
        df["parsed_date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    else:
        df["parsed_date"] = pd.NaT

    # Clean amounts (spend) / clean quantities (activity) — both numeric
    if data_type == "spend":
        df["clean_amount"] = df["amount"].apply(_clean_amount)
        df = df[df["clean_amount"].abs() > 0.01].copy()
    else:
        df["clean_quantity"] = df[quantity_col].apply(_clean_amount)
        df = df[df["clean_quantity"].abs() > 0.001].copy()
        # Spend amount is optional on activity uploads (bill cost, if present)
        if "amount" in df.columns:
            df["clean_amount"] = df["amount"].apply(_clean_amount)
        else:
            df["clean_amount"] = None

    # Deduplicate — same date + supplier + (amount or quantity)
    original_count = len(df)
    dedup_cols = []
    if "date" in df.columns:
        dedup_cols.append("date")
    if "supplier" in df.columns:
        dedup_cols.append("supplier")
    dedup_cols.append("clean_amount" if data_type == "spend" else "clean_quantity")

    if len(dedup_cols) >= 2:
        df = df.drop_duplicates(subset=dedup_cols, keep="first")
    duplicates_removed = original_count - len(df)

    # Build Transaction objects
    transactions = []
    for idx, row in df.iterrows():
        amount_val = row.get("clean_amount")
        has_amount = amount_val is not None and pd.notna(amount_val)
        quantity_val = row.get("clean_quantity") if data_type == "activity" else None

        t = Transaction(
            engagement_id=engagement_id,
            row_number=int(idx) + 1,
            raw_date=str(row.get("date", "")) if pd.notna(row.get("date")) else None,
            raw_description=str(row.get("description", "")) if pd.notna(row.get("description")) else None,
            raw_supplier=str(row.get("supplier", "")) if pd.notna(row.get("supplier")) else None,
            raw_amount=float(amount_val) if has_amount else None,
            raw_category=str(row.get("category", "")) if pd.notna(row.get("category")) else None,
            transaction_date=row["parsed_date"].date() if pd.notna(row["parsed_date"]) else None,
            amount_gbp=float(amount_val) if has_amount else None,
            data_type=data_type,
            activity_type=activity_type if data_type == "activity" else None,
            quantity=float(quantity_val) if data_type == "activity" and pd.notna(quantity_val) else None,
            quantity_unit=detected_unit if data_type == "activity" else None,
            raw_activity_label=raw_activity_label if data_type == "activity" else None,
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
        "data_type": data_type,
        "activity_type": activity_type,
        "detected_unit": detected_unit,
        "total_quantity": sum(t.quantity for t in transactions if t.quantity) if data_type == "activity" else None,
    }

    return transactions, summary


def _normalise_column(col: str) -> str:
    """Map a column header to a standard name."""
    clean = col.strip().lower().replace("_", " ").replace("-", " ")
    return COLUMN_MAP.get(clean, clean)


def _detect_quantity_column(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    """Look at column headers and find one that matches a known unit.

    Returns (column_name, canonical_unit, activity_hint) or (None, None, None).
    """
    for col in df.columns:
        key = str(col).strip().lower()
        if key in UNIT_COLUMN_MAP:
            canonical_unit, hint = UNIT_COLUMN_MAP[key]
            return col, canonical_unit, hint
    # Fallback: a generic "amount" column if nothing unit-specific was found
    # (the caller already excluded spend mode by the time we get here)
    if "amount" in df.columns:
        return "amount", "quantity", None
    return None, None, None


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
