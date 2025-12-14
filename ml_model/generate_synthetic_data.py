"""
Synthetic training data generator for the salary predictor.

Creates ml_model/training_data.csv with columns:
 id, title, rate_per_hour, skill_list, level, location_city, employment_type, company_sector

Usage:
    python -m ml_model.generate_synthetic_data
    or call generate_synthetic_dataset(out_csv="ml_model/training_data.csv", n=2000)
"""
import os
import random
from typing import Optional
import pandas as pd
import numpy as np

def _sample_skills(skills_pool, k_min=3, k_max=7):
    k = random.randint(k_min, k_max)
    return ", ".join(random.sample(skills_pool, k))

def generate_synthetic_dataset(out_csv: str = "ml_model/training_data.csv", n: int = 2000, seed: Optional[int] = 42):
    random.seed(seed)
    np.random.seed(seed)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    job_titles = [
        "Backend Developer", "Frontend Developer", "Fullstack Developer", "Data Scientist",
        "DevOps Engineer", "QA Engineer", "Mobile Developer", "Machine Learning Engineer",
        "Site Reliability Engineer", "Product Engineer", "Software Engineer"
    ]
    skills_pool = [
        "Python","Django","Flask","FastAPI","JavaScript","React","Vue","Node.js","PostgreSQL",
        "MySQL","MongoDB","AWS","GCP","Docker","Kubernetes","Redis","Celery","REST API",
        "GraphQL","Git","Terraform","CI/CD","SQL","Pandas","NumPy","Scikit-learn"
    ]
    experience_levels = ["Intern", "Junior", "Mid", "Senior", "Lead"]
    locations = ["Yerevan", "Gyumri", "Vanadzor", "Dilijan", "Remote"]
    job_types = ["Full-time", "Part-time", "Contract"]
    industries = ["Software", "FinTech", "HealthTech", "E-commerce", "EdTech", "Gaming"]

    rows = []
    for i in range(1, n + 1):
        title = random.choice(job_titles)
        level = random.choices(experience_levels, weights=[5, 25, 40, 25, 5])[0]
        location = random.choices(locations, weights=[0.75, 0.08, 0.06, 0.03, 0.08])[0]
        job_type = random.choices(job_types, weights=[0.85, 0.10, 0.05])[0]
        industry = random.choice(industries)
        skill_list = _sample_skills(skills_pool, k_min=3, k_max=7)

        # base hourly ranges (USD) by experience
        base_ranges = {
            "Intern": (3, 6),
            "Junior": (6, 12),
            "Mid": (12, 25),
            "Senior": (25, 50),
            "Lead": (40, 80)
        }
        low, high = base_ranges.get(level, (10, 30))

        # role multiplier adjustments
        role_multiplier = 1.0
        if "Data" in title or "Machine" in title:
            role_multiplier *= 1.25
        if "DevOps" in title or "Site Reliability" in title:
            role_multiplier *= 1.2
        if "Frontend" in title:
            role_multiplier *= 0.95

        # industry adjustment
        industry_adj = 1.0
        if industry == "FinTech":
            industry_adj = 1.15
        elif industry == "HealthTech":
            industry_adj = 1.05
        elif industry == "E-commerce":
            industry_adj = 1.03

        # location adjustment: Remote slightly higher
        loc_adj = 1.0
        if location == "Remote":
            loc_adj = 1.05
        elif location != "Yerevan":
            loc_adj = 0.95

        # sample rate
        base = np.random.uniform(low, high)
        rate = base * role_multiplier * industry_adj * loc_adj
        # add small noise and clip
        rate = max(2.0, round(float(np.random.normal(rate, rate * 0.08)), 2))

        rows.append({
            "id": i,
            "title": title,
            "rate_per_hour": rate,
            "skill_list": skill_list,
            "level": level,
            "location_city": location,
            "employment_type": job_type,
            "company_sector": industry
        })

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    return df

if __name__ == "__main__":
    df = generate_synthetic_dataset(out_csv="ml_model/training_data.csv", n=2000, seed=42)
    print(f"Generated {len(df)} rows -> ml_model/training_data.csv")
