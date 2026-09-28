import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_PATH = "data/Teams.csv"

if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(
        f"'{DATA_PATH}' not found. Run 'scripts/download_data.py' first!"
    )

# 1. Load Data
teams = pd.read_csv(DATA_PATH)

# -------------------------------------------------------------
# Part 1: Exploratory Data Analysis (EDA)
# -------------------------------------------------------------
# Filter to Modern Era (1901–present)
modern_teams = teams[teams["yearID"] >= 1901].copy()
modern_teams["WinPct"] = (modern_teams["W"] / modern_teams["G"]).round(3)
modern_teams["RunDiff"] = modern_teams["R"] - modern_teams["RA"]

# EDA 1: Run Differential vs. Wins
plt.figure(figsize=(8, 5))
sns.regplot(
    data=modern_teams,
    x="RunDiff",
    y="W",
    scatter_kws={"alpha": 0.25, "color": "steelblue"},
    line_kws={"color": "darkred"},
)
plt.axhline(81, color="gray", linestyle="--", linewidth=0.8)
plt.axvline(0, color="gray", linestyle="--", linewidth=0.8)
plt.title("Wins vs. Run Differential (1901–Present)")
plt.xlabel("Run Differential (R - RA)")
plt.ylabel("Total Wins")
plt.tight_layout()
plt.savefig("eda_rundiff_vs_wins.png")
plt.close()

# EDA 2: League-wide HR Trend
hr_trend = modern_teams.groupby("yearID")["HR"].mean().reset_index()
plt.figure(figsize=(8, 5))
sns.lineplot(data=hr_trend, x="yearID", y="HR", color="forestgreen")
plt.title("Average Team Home Runs per Season (1901–Present)")
plt.xlabel("Season")
plt.ylabel("Average HR per Team")
plt.tight_layout()
plt.savefig("eda_hr_trends.png")
plt.close()

# EDA 3: Top 10 Single-Season Win Totals
top_10_teams = modern_teams.sort_values(by="W", ascending=False)[
    ["yearID", "name", "W", "L", "WinPct", "RunDiff", "WSWin"]
].head(10)
print("\n=== Top 10 Single-Season Win Totals ===")
print(top_10_teams.to_string(index=False))

# -------------------------------------------------------------
# Part 2: World Series Prediction Model
# -------------------------------------------------------------
# Filter to modern division/playoff era (1969+), exclude 1994 (cancelled WS)
playoffs = modern_teams[
    (modern_teams["yearID"] >= 1969)
    & (modern_teams["yearID"] != 1994)
    & ((modern_teams["DivWin"] == "Y") | (modern_teams["WCWin"] == "Y"))
].copy()

# Feature Engineering
playoffs["WS_Winner"] = playoffs["WSWin"].apply(lambda x: 1 if x == "Y" else 0)
playoffs["R_per_G"] = playoffs["R"] / playoffs["G"]
playoffs["RA_per_G"] = playoffs["RA"] / playoffs["G"]
playoffs["HR_per_G"] = playoffs["HR"] / playoffs["G"]

features = ["WinPct", "RunDiff", "ERA", "HR_per_G", "R_per_G", "RA_per_G"]
target = "WS_Winner"

# Clean missing entries
playoffs = playoffs.dropna(subset=features + [target])

# Temporal Train/Test Split (Train: 1969-2010 | Test: 2011-present)
train = playoffs[playoffs["yearID"] <= 2010].copy()
test = playoffs[playoffs["yearID"] > 2010].copy()

X_train, y_train = train[features], train[target]
X_test, y_test = test[features], test[target]

# Pipeline: Scaler + Logistic Regression with balanced weighting
model = Pipeline(
    [
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", random_state=42)),
    ]
)

model.fit(X_train, y_train)

# Predict probabilities on test seasons
test["pred_prob"] = model.predict_proba(X_test)[:, 1]

# -------------------------------------------------------------
# Part 3: Evaluation
# -------------------------------------------------------------
# 1. ROC-AUC score across all playoff contenders
test_auc = roc_auc_score(y_test, test["pred_prob"])
print(f"\nTest Postseason ROC-AUC: {test_auc:.3f}")

# 2. Year-by-Year Champ Prediction (Select highest-probability team per year)
predicted_champs = (
    test.sort_values(["yearID", "pred_prob"], ascending=[True, False])
    .groupby("yearID")
    .first()
    .reset_index()
)

print("\n=== Model's Pre-Playoff Picks vs. Reality (2011–Present) ===")
print(
    predicted_champs[["yearID", "name", "pred_prob", "WS_Winner"]].rename(
        columns={
            "name": "Predicted_Favorite",
            "pred_prob": "Win_Prob",
            "WS_Winner": "Actually_Won_WS",
        }
    )
)

correct_picks = predicted_champs["WS_Winner"].sum()
total_seasons = len(predicted_champs)
print(
    f"\nFavorite Pick Accuracy: {correct_picks}/{total_seasons} ({correct_picks / total_seasons:.1%})"
)
