import os
from typing import Dict, Any, Optional
import pandas as pd
import joblib
import inspect

# sklearn imports
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

MODEL_PATH_DEFAULT = os.path.join("ml_model", "salary_model.joblib")

# ...helpers...
def _ensure_df_row(job_dict: Dict[str, Any]):
	# ensure keys exist and are strings, normalize skills (comma -> space, collapse whitespace)
	req = job_dict.get("required_skills", "") or ""
	if isinstance(req, (list, tuple)):
		req_str = " ".join([str(x).strip() for x in req if str(x).strip()])
	else:
		req_str = " ".join(str(req).replace(",", " ").split())
	return pd.DataFrame([{
		"job_title": job_dict.get("job_title", "") or "",
		"required_skills": req_str,
		"experience_level": job_dict.get("experience_level", "") or "",
		"job_location": job_dict.get("job_location", "") or "",
		"job_type": job_dict.get("job_type", "") or "",
		"company_industry": job_dict.get("company_industry", "") or ""
	}])

def build_pipeline():
	# Feature columns
	text_cols = ["required_skills"]
	cat_cols = ["job_title", "experience_level", "job_location", "job_type", "company_industry"]

	# Create OneHotEncoder with appropriate kwarg for sklearn version
	ohe_kwargs = {"handle_unknown": "ignore"}
	params = inspect.signature(OneHotEncoder.__init__).parameters
	if "sparse_output" in params:
		ohe_kwargs["sparse_output"] = False
	elif "sparse" in params:
		ohe_kwargs["sparse"] = False
	ohe = OneHotEncoder(**ohe_kwargs)

	preprocessor = ColumnTransformer(
		transformers=[
			("skills_tfidf", TfidfVectorizer(max_features=500, ngram_range=(1,2)), "required_skills"),
			("cats", ohe, cat_cols),
		],
		remainder="drop",
		sparse_threshold=0.0
	)

	model = GradientBoostingRegressor(random_state=42, n_estimators=200)
	pipeline = Pipeline([("pre", preprocessor), ("model", model)])
	return pipeline

def train_and_save(df: pd.DataFrame, model_path: str = MODEL_PATH_DEFAULT, test_size: float = 0.2, random_state: int = 42):
    """
    df must contain columns: hourly_rate (target), job_title, required_skills (list or str),
    experience_level, job_location, job_type, company_industry (optional).
    """
    df = df.copy()

    # Accept alternative column names commonly used in DB / synthetic CSVs and normalize
    col_map = {
        "rate_per_hour": "hourly_rate",
        "title": "job_title",
        "skill_list": "required_skills",
        "level": "experience_level",
        "location_city": "job_location",
        "employment_type": "job_type",
        "company_sector": "company_industry"
    }
    rename_map = {k: v for k, v in col_map.items() if k in df.columns}
    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure target exists
    if "hourly_rate" not in df.columns:
        raise ValueError("Training data must contain 'hourly_rate' (or 'rate_per_hour').")

    # Normalize and clean features
    # required_skills: list -> space-joined string; comma-separated -> space-separated
    df["required_skills"] = df.get("required_skills", "").fillna("").apply(
        lambda x: " ".join(x) if isinstance(x, (list, tuple)) else str(x)
    ).str.replace(",", " ").str.replace(r"\s+", " ", regex=True).str.strip()

    for c in ["job_title", "experience_level", "job_location", "job_type", "company_industry"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
        else:
            df[c] = ""

    # Prepare target rows: coerce to numeric and drop invalid
    df["hourly_rate"] = pd.to_numeric(df["hourly_rate"], errors="coerce")
    df = df[df["hourly_rate"].notnull()]
    if df.empty:
        raise ValueError("No valid rows with numeric 'hourly_rate' found after cleaning.")

    X = df[["job_title", "required_skills", "experience_level", "job_location", "job_type", "company_industry"]]
    y = df["hourly_rate"].astype(float)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    # Compute RMSE in a sklearn-version-compatible way
    try:
        rmse = mean_squared_error(y_test, y_pred, squared=False)
    except TypeError:
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
    
    dir_name = os.path.dirname(model_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    joblib.dump(pipeline, model_path)
    return {"model_path": model_path, "mae": float(mae), "rmse": float(rmse)}

def load_model(model_path: str = MODEL_PATH_DEFAULT) -> Optional[Pipeline]:
    if not os.path.exists(model_path):
        return None
    return joblib.load(model_path)

def predict_missing_salary(job_dict: Dict[str, Any], model: Optional[Pipeline] = None) -> Optional[float]:
    """
    Predict hourly_rate for a single job dict. Returns float or None if model not available.
    job_dict keys used: job_title, required_skills (list or str), experience_level, job_location, job_type, company_industry
    """
    if model is None:
        model = load_model()
    if model is None:
        return None
    Xrow = _ensure_df_row(job_dict)
    try:
        pred = model.predict(Xrow)[0]
        if np.isnan(pred):
            return None
        return float(pred)
    except Exception:
        return None

if __name__ == "__main__":
    # quick CLI for training with CSV (optional)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="CSV file with training data")
    parser.add_argument("--out", default=MODEL_PATH_DEFAULT)
    args = parser.parse_args()
    if args.data:
        df = pd.read_csv(args.data)
        res = train_and_save(df, model_path=args.out)
        print("Training done:", res)
