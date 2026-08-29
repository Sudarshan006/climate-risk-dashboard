"""
tft_model.py

Temporal Fusion Transformer setup and training via pytorch-forecasting.
Configures the TimeSeriesDataSet with static / known-future / observed
inputs per Lim et al. 2021, and trains with quantile loss to produce
probabilistic risk forecasts with confidence intervals.

Owner: Ganesh (ML Modeler)
"""

import pandas as pd
import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.data import GroupNormalizer
from pytorch_forecasting.metrics import QuantileLoss

from feature_engineering import STATIC_FEATURES, KNOWN_FUTURE_FEATURES, OBSERVED_FEATURES, SEQUENCE_LENGTH_DAYS

# Forecast horizon (days ahead to predict risk) - TODO: confirm with team
MAX_PREDICTION_LENGTH = 7
MAX_ENCODER_LENGTH = SEQUENCE_LENGTH_DAYS


def build_timeseries_dataset(df: pd.DataFrame, target_col: str, entity_col: str = "county_fips"):
    """
    Wrap the prepared DataFrame into a pytorch-forecasting TimeSeriesDataSet.

    Requires df to already have a `time_idx` column (see feature_engineering.build_sequences).
    """
    training_cutoff = df["time_idx"].max() - MAX_PREDICTION_LENGTH

    train_dataset = TimeSeriesDataSet(
        df[df.time_idx <= training_cutoff],
        time_idx="time_idx",
        target=target_col,
        group_ids=[entity_col],
        max_encoder_length=MAX_ENCODER_LENGTH,
        max_prediction_length=MAX_PREDICTION_LENGTH,
        static_categoricals=[c for c in STATIC_FEATURES if c in df.columns and df[c].dtype == "object"],
        static_reals=[c for c in STATIC_FEATURES if c in df.columns and df[c].dtype != "object"],
        time_varying_known_reals=[c for c in KNOWN_FUTURE_FEATURES if c in df.columns],
        time_varying_unknown_reals=[c for c in OBSERVED_FEATURES if c in df.columns] + [target_col],
        target_normalizer=GroupNormalizer(groups=[entity_col]),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    validation_dataset = TimeSeriesDataSet.from_dataset(
        train_dataset, df, predict=True, stop_randomization=True
    )

    return train_dataset, validation_dataset


def train_tft(train_dataset, validation_dataset, max_epochs: int = 30):
    """
    Train the TFT model with quantile loss (P10/P50/P90) for built-in
    uncertainty quantification.

    Hyperparameters loosely follow the "Volatility" dataset config in
    Table 1 of Lim et al. 2021, as the closest analog for a smaller/
    noisier dataset - tune once real data volume is known.
    """
    train_dataloader = train_dataset.to_dataloader(train=True, batch_size=64, num_workers=0)
    val_dataloader = validation_dataset.to_dataloader(train=False, batch_size=64, num_workers=0)

    early_stop_callback = EarlyStopping(monitor="val_loss", patience=5, mode="min")

    trainer = pl.Trainer(
        max_epochs=max_epochs,
        gradient_clip_val=0.1,
        callbacks=[early_stop_callback],
    )

    tft = TemporalFusionTransformer.from_dataset(
        train_dataset,
        learning_rate=0.01,
        hidden_size=160,       # per Volatility config, Table 1
        attention_head_size=1,
        dropout=0.3,
        hidden_continuous_size=80,
        loss=QuantileLoss(quantiles=[0.1, 0.5, 0.9]),
        log_interval=10,
        reduce_on_plateau_patience=4,
    )

    trainer.fit(tft, train_dataloaders=train_dataloader, val_dataloaders=val_dataloader)

    return tft, trainer


if __name__ == "__main__":
    # TODO: load prepared df from feature_engineering.py, call build_timeseries_dataset + train_tft
    pass
