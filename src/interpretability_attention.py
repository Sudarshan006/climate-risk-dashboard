"""
interpretability_attention.py

Extracts TFT variable-selection weights and temporal attention weights
for interpretability - the deep-learning equivalent of SHAP for the
XGBoost baseline. Outputs mirror Table 3 and Fig. 4 of Lim et al. 2021.

Owner: Ganesh (ML Modeler)
"""

import pandas as pd
import matplotlib.pyplot as plt


def extract_variable_importance(tft_model, dataloader) -> pd.DataFrame:
    """
    Aggregate variable-selection weights across the test set, reporting
    10th / 50th / 90th percentiles per variable - mirrors Table 3 in
    the reference paper.
    """
    raw_predictions = tft_model.predict(dataloader, mode="raw", return_x=True)
    interpretation = tft_model.interpret_output(raw_predictions.output, reduction="none")

    # TODO: unpack interpretation["encoder_variables"] / ["decoder_variables"]
    # into a tidy DataFrame of percentiles per feature, once shapes are
    # confirmed against the pytorch-forecasting version in use.

    return pd.DataFrame()  # placeholder


def plot_attention_patterns(tft_model, dataloader, save_path: str = "../outputs/attention_patterns.png"):
    """
    Plot average attention weights across the test set to visualize
    persistent temporal patterns (seasonality, lag effects) - mirrors
    Fig. 4 in the reference paper.
    """
    raw_predictions = tft_model.predict(dataloader, mode="raw", return_x=True)
    interpretation = tft_model.interpret_output(raw_predictions.output, reduction="none")

    fig, ax = plt.subplots(figsize=(10, 5))
    # TODO: plot interpretation["attention"] averaged over samples,
    # against relative time position, once shapes confirmed.
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()
    print(f"Saved attention pattern plot to {save_path}")


def save_variable_importance(df: pd.DataFrame, path: str = "../outputs/variable_importance.csv"):
    df.to_csv(path, index=False)
    print(f"Saved variable importance to {path}")


if __name__ == "__main__":
    pass
