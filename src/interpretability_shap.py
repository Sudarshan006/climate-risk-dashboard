"""
interpretability_shap.py

Generates SHAP values for the XGBoost baseline - shows which tabular
features drive each hazard risk prediction.

Owner: Ganesh (ML Modeler)
"""

import pandas as pd
import shap
import matplotlib.pyplot as plt


def compute_shap_values(model, X: pd.DataFrame):
    """Compute SHAP values for a trained XGBoost model."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return explainer, shap_values


def plot_summary(shap_values, X: pd.DataFrame, save_path: str = "../outputs/shap_summary.png"):
    """Save a SHAP summary plot (global feature importance) for the paper."""
    shap.summary_plot(shap_values, X, show=False)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()
    print(f"Saved SHAP summary plot to {save_path}")


def save_shap_values(shap_values, X: pd.DataFrame, path: str = "../outputs/shap_values.csv"):
    """Save raw SHAP values as a tidy CSV for reproducibility / paper tables."""
    shap_df = pd.DataFrame(shap_values, columns=X.columns)
    shap_df.to_csv(path, index=False)
    print(f"Saved SHAP values to {path}")


if __name__ == "__main__":
    # TODO: load trained XGBoost model + X_test from xgboost_baseline.py
    pass
