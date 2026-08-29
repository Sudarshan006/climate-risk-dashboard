"""
xgboost_baseline.py

Interpretable gradient-boosted baseline for county-level disaster risk
classification. Serves as the benchmark against the TFT model.

Owner: Ganesh (ML Modeler)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb


def train_xgboost_baseline(df: pd.DataFrame, feature_cols: list, target_col: str,
                            test_size: float = 0.2, random_state: int = 42):
    """
    Train an XGBoost classifier for a single hazard target
    (e.g. target_flood_risk).

    Returns the trained model and a held-out test set for evaluation.
    """
    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    return model, X_train, X_test, y_train, y_test


def evaluate_model(model, X_test, y_test) -> dict:
    """Print and return standard classification metrics."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, output_dict=True)
    auc = roc_auc_score(y_test, y_proba)

    print(classification_report(y_test, y_pred))
    print(f"ROC-AUC: {auc:.4f}")

    return {"report": report, "roc_auc": auc}


if __name__ == "__main__":
    # TODO: load prepared features from feature_engineering.py once data is ready
    # df = ...
    # feature_cols = [...]
    # model, X_train, X_test, y_train, y_test = train_xgboost_baseline(df, feature_cols, "target_flood_risk")
    # evaluate_model(model, X_test, y_test)
    pass
