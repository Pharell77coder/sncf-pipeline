"""Extraction, validation stricte et remplacement transactionnel d'un snapshot."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

SOURCE = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/regularite-mensuelle-tgv-axes/exports/json"
SOURCE_COLUMNS = ["date", "axe", "regularite_composite", "ponctualite_origine"]

def clean(records):
    df = pd.DataFrame(records)
    missing = set(SOURCE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    df = df[SOURCE_COLUMNS].copy()
    df["axe"] = df["axe"].astype("string").str.strip()
    dates = df["date"].astype("string")
    if not dates.str.fullmatch(r"\d{4}-\d{2}", na=False).all():
        raise ValueError("Mois invalide")
    df["date"] = pd.to_datetime(dates, format="%Y-%m", errors="raise")
    for col in SOURCE_COLUMNS[2:]:
        df[col] = pd.to_numeric(df[col], errors="raise")
        if not df[col].dropna().between(0, 100).all():
            raise ValueError(f"Pourcentage hors limites : {col}")
    if df.empty or df["axe"].isna().any() or df["axe"].eq("").any():
        raise ValueError("Snapshot vide ou axe absent")
    before = len(df)
    df = df.drop_duplicates()
    if df.duplicated(["date", "axe"]).any():
        raise ValueError("Valeurs contradictoires pour un même mois et axe")
    return df.sort_values(["date", "axe"]), before - len(df)

def run(offline=False, validate_only=False):
    raw = Path("data/raw/sncf.json")
    raw.parent.mkdir(parents=True, exist_ok=True)
    if offline:
        payload = raw.read_bytes()
    else:
        import requests
        response = requests.get(SOURCE, timeout=(10, 90))
        response.raise_for_status()
        payload = response.content
    df, duplicates = clean(json.loads(payload))
    digest = hashlib.sha256(payload).hexdigest()
    report = dict(processed_at=datetime.now(timezone.utc).isoformat(), source=SOURCE,
                  sha256=digest, rows=len(df), duplicates_removed=duplicates,
                  null_rates={c: int(df[c].isna().sum()) for c in SOURCE_COLUMNS[2:]},
                  first_month=str(df.date.min().date()), last_month=str(df.date.max().date()), offline=offline)
    if not offline:
        raw.write_bytes(payload)
    Path("data/quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not validate_only:
        from sqlalchemy import text
        from db import engine
        with engine().begin() as conn:
            conn.execute(text("""CREATE TABLE IF NOT EXISTS regularity (
                date DATE NOT NULL, axe TEXT NOT NULL,
                regularite_composite DOUBLE PRECISION CHECK (regularite_composite BETWEEN 0 AND 100),
                ponctualite_origine DOUBLE PRECISION CHECK (ponctualite_origine BETWEEN 0 AND 100),
                PRIMARY KEY (date, axe))"""))
            conn.execute(text("""CREATE TABLE IF NOT EXISTS ingestion_runs (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                loaded_at TIMESTAMPTZ DEFAULT now(), report JSONB NOT NULL)"""))
            conn.execute(text("LOCK TABLE regularity IN ACCESS EXCLUSIVE MODE"))
            conn.execute(text("DELETE FROM regularity"))
            df.to_sql("regularity", conn, if_exists="append", index=False, method="multi", chunksize=500)
            conn.execute(text("INSERT INTO ingestion_runs(report) VALUES (CAST(:report AS jsonb))"),
                         {"report": json.dumps(report)})
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Utiliser le snapshot fourni")
    parser.add_argument("--validate-only", action="store_true", help="Sans connexion PostgreSQL")
    args = parser.parse_args()
    run(args.offline, args.validate_only)
