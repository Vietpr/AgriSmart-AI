"""
Train XGBoost models for temperature prediction with MLflow tracking.

This script:
1. Loads data from dataaaset_weather.xlsx
2. Preprocesses: handles outliers, scales with MinMaxScaler
3. Trains XGBoost models for tempmax and tempmin
4. Tracks experiments with MLflow
5. Exports .pkl files for production use
"""

import os
import sys
import warnings

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "dataaaset_weather.xlsx")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")

FEATURE_COLUMNS = [
    "humidity",
    "precip",
    "tempmax",
    "tempmin",
    "winddir",
    "windspeed",
    "precipcover",
    "solarenergy",
]

BEST_PARAMS = {
    "colsample_bytree": 1.0,
    "gamma": 0.1,
    "learning_rate": 0.05,
    "max_depth": 7,
    "min_child_weight": 5,
    "n_estimators": 200,
    "reg_lambda": 10,
    "subsample": 0.6,
}


def load_and_preprocess_data():
    print("[1/5] Loading data...")
    df = pd.read_excel(DATA_PATH)

    numeric_cols = FEATURE_COLUMNS.copy()
    df_clean = df[numeric_cols].copy()
    df_clean = df_clean.dropna()

    print(f"  Dataset shape: {df_clean.shape}")
    print(f"  Columns: {list(df_clean.columns)}")

    print("[2/5] Handling outliers (IQR method)...")
    outlier_cols = [
        "humidity",
        "precip",
        "precipcover",
        "tempmax",
        "tempmin",
        "winddir",
        "windspeed",
    ]
    for col in outlier_cols:
        if col in df_clean.columns:
            Q1 = df_clean[col].quantile(0.25)
            Q3 = df_clean[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            before = len(df_clean)
            df_clean = df_clean[(df_clean[col] >= lower) & (df_clean[col] <= upper)]
            removed = before - len(df_clean)
            if removed > 0:
                print(f"  Removed {removed} outliers from '{col}'")

    print(f"  Final dataset shape: {df_clean.shape}")

    print("[3/5] Scaling features with MinMaxScaler...")
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df_clean[FEATURE_COLUMNS])
    df_scaled = pd.DataFrame(scaled_data, columns=FEATURE_COLUMNS)

    return df_scaled, scaler


def train_model(df, target_col, model_name, scaler):
    print(f"\n{'='*60}")
    print(f"Training model: {model_name} (target: {target_col})")
    print(f"{'='*60}")

    feature_cols = [c for c in FEATURE_COLUMNS if c != target_col]

    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=43
    )

    print(f"  Train size: {len(X_train)}, Test size: {len(X_test)}")

    mlflow_uri = os.path.join(PROJECT_ROOT, "mlruns")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment("AgriSmart-AI-Training")

    with mlflow.start_run(run_name=f"xgboost_{target_col}"):
        mlflow.log_params(BEST_PARAMS)
        mlflow.log_param("target", target_col)
        mlflow.log_param("features", str(feature_cols))
        mlflow.log_param("test_size", 0.2)
        mlflow.log_param("random_state", 43)

        model = xgb.XGBRegressor(**BEST_PARAMS)
        model.fit(X_train, y_train)

        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)

        mse_train = mean_squared_error(y_train, y_pred_train)
        mse_test = mean_squared_error(y_test, y_pred_test)
        rmse_train = np.sqrt(mse_train)
        rmse_test = np.sqrt(mse_test)
        r2_train = r2_score(y_train, y_pred_train)
        r2_test = r2_score(y_test, y_pred_test)

        mlflow.log_metric("mse_train", mse_train)
        mlflow.log_metric("mse_test", mse_test)
        mlflow.log_metric("rmse_train", rmse_train)
        mlflow.log_metric("rmse_test", rmse_test)
        mlflow.log_metric("r2_train", r2_train)
        mlflow.log_metric("r2_test", r2_test)

        mlflow.sklearn.log_model(model, f"xgboost_{target_col}")

        print(f"\n  Results:")
        print(f"  {'Metric':<25} {'Train':>12} {'Test':>12}")
        print(f"  {'-'*49}")
        print(f"  {'MSE':<25} {mse_train:>12.6f} {mse_test:>12.6f}")
        print(f"  {'RMSE':<25} {rmse_train:>12.6f} {rmse_test:>12.6f}")
        print(f"  {'R-squared':<25} {r2_train:>12.6f} {r2_test:>12.6f}")

        model_path = os.path.join(MODEL_DIR, f"xgboost_{target_col}.pkl")
        joblib.dump(model, model_path)
        print(f"\n  Model saved to: {model_path}")

        mlflow.log_artifact(model_path)

    return model


def main():
    print("=" * 60)
    print("AgriSmart AI - Model Training Pipeline")
    print("=" * 60)

    df_scaled, scaler = load_and_preprocess_data()

    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"  Scaler saved to: {scaler_path}")

    feature_names_path = os.path.join(MODEL_DIR, "feature_names.pkl")
    joblib.dump(FEATURE_COLUMNS, feature_names_path)
    print(f"  Feature names saved to: {feature_names_path}")

    model_tempmax = train_model(df_scaled, "tempmax", "XGBoost TempMax", scaler)
    model_tempmin = train_model(df_scaled, "tempmin", "XGBoost TempMin", scaler)

    print("\n" + "=" * 60)
    print("[5/5] Training complete!")
    print("=" * 60)
    print(f"\nArtifacts saved to: {MODEL_DIR}")
    print(f"MLflow tracking at: {os.path.join(PROJECT_ROOT, 'mlruns')}")
    print(
        f"\nRun 'mlflow ui --backend-store-uri {os.path.join(PROJECT_ROOT, 'mlruns')}' to view experiments"
    )


if __name__ == "__main__":
    main()
