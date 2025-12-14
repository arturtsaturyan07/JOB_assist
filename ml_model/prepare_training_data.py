import os
from typing import Optional, Union
import pandas as pd

try:
    import psycopg2
except ImportError:
    psycopg2 = None

SQL = """
SELECT id, title, rate_per_hour, skill_list, level, location_city, employment_type, company_sector
FROM jobs
WHERE rate_per_hour IS NOT NULL
"""

def connect_to_db(dsn: Optional[str] = None):
    """
    Return a psycopg2 connection.
    - If psycopg2 is installed, uses provided dsn or DATABASE_URL env var.
    - If psycopg2 is not installed, raises RuntimeError so caller can provide a connection.
    """
    if not psycopg2:
        raise RuntimeError("psycopg2 is not installed; install it or provide a DB connection.")
    _dsn = dsn or os.environ.get("DATABASE_URL")
    if not _dsn:
        raise RuntimeError("No DSN provided and DATABASE_URL not set.")
    return psycopg2.connect(_dsn)

def prepare_training_data(conn_or_dsn: Optional[Union[str, object]] = None, out_csv: str = "ml_model/training_data.csv") -> pd.DataFrame:
    """
    Extract labeled job rows and prepare a DataFrame ready for training.
    - conn_or_dsn: either a psycopg2 connection object, a DSN string, or None (uses DATABASE_URL).
    - Saves CSV to out_csv and returns the dataframe.
    """
    conn_created = False
    conn = None
    try:
        if isinstance(conn_or_dsn, str):
            # treat as DSN string
            conn = connect_to_db(conn_or_dsn)
            conn_created = True
        elif conn_or_dsn is None:
            conn = connect_to_db()  # may raise
            conn_created = True
        else:
            # assume it's a DB-API connection
            conn = conn_or_dsn

        df = pd.read_sql_query(SQL, conn)

    finally:
        if conn_created and conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    # Rename to model-expected names
    df = df.rename(columns={
        "title": "job_title",
        "rate_per_hour": "hourly_rate",
        "skill_list": "required_skills",
        "level": "experience_level",
        "location_city": "job_location",
        "employment_type": "job_type",
        "company_sector": "company_industry"
    })

    # Normalize skills: comma-separated -> space-separated tokens for TF-IDF
    df["required_skills"] = df["required_skills"].fillna("").apply(
        lambda s: " ".join([p.strip() for p in str(s).split(",") if p.strip()])
    )

    # Ensure numeric target
    df["hourly_rate"] = pd.to_numeric(df["hourly_rate"], errors="coerce")
    df = df[df["hourly_rate"].notnull()]  # safety

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    return df

if __name__ == "__main__":
    # Example usage:
    # - Set DATABASE_URL env var, or pass a DSN string to connect_to_db / prepare_training_data
    # - Run: python ml_model/prepare_training_data.py
    try:
        conn = None
        try:
            conn = connect_to_db()  # will use DATABASE_URL or raise
        except Exception as e:
            print("Could not auto-connect to DB:", e)
            raise SystemExit(1)

        df = prepare_training_data(conn, out_csv="ml_model/training_data.csv")
        print(f"Saved {len(df)} rows to ml_model/training_data.csv")

        # Optionally, trigger training (requires ml_model.salary_predictor dependencies)
        try:
            from ml_model.salary_predictor import train_and_save
            res = train_and_save(df)
            print("Training completed:", res)
        except Exception as e:
            print("Could not run training automatically (missing dependencies or salary_predictor):", e)

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
