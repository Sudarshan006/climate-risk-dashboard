"""
uncertainty.py

Extracts probabilistic risk scores and confidence intervals from the
trained TFT's quantile predictions (P10 / P50 / P90), formatted for
downstream use by the dashboard and paper.

Owner: Ganesh (ML Modeler)
"""

import pandas as pd


def extract_quantile_predictions(tft_model, dataloader) -> pd.DataFrame:
    """
    Run inference and extract P10/P50/P90 quantile forecasts per
    county/date/horizon.

    Returns a tidy DataFrame:
        county_fips | date | horizon | p10 | p50 | p90
    """
    raw_predictions = tft_model.predict(dataloader, mode="quantiles", return_x=True)

    # TODO: unpack raw_predictions into a tidy DataFrame once real
    # dataloader/output shape is confirmed against pytorch-forecasting version in use.
    # Expected: raw_predictions.output has shape [n_samples, horizon, n_quantiles]

    results = []
    # placeholder loop structure - fill in once shapes are confirmed
    # for i, county in enumerate(entities):
    #     for h in range(horizon):
    #         results.append({
    #             "county_fips": county,
    #             "horizon": h + 1,
    #             "p10": raw_predictions.output[i, h, 0].item(),
    #             "p50": raw_predictions.output[i, h, 1].item(),
    #             "p90": raw_predictions.output[i, h, 2].item(),
    #         })

    return pd.DataFrame(results)


def save_predictions(df: pd.DataFrame, path: str = "../outputs/predictions.csv"):
    """Save formatted predictions for Sud (paper) and Manoj (dashboard)."""
    df.to_csv(path, index=False)
    print(f"Saved predictions to {path}")


if __name__ == "__main__":
    pass
