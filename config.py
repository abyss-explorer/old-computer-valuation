# config.py
from pathlib import Path

# 定义项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据路径
RAW_DATA_PATH = BASE_DIR / "data" / "raw_data.csv"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed_data.csv" # 可选

# 模型及组件保存路径
MODELS_DIR = BASE_DIR / "models"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
FEATURE_NAMES_PATH = MODELS_DIR / "feature_names.pkl"
XGB_MODEL_PATH = MODELS_DIR / "xgb_model.pkl"
KNN_MODEL_PATH = MODELS_DIR / "knn_model.pkl"
KNN_FEATURES_PATH = MODELS_DIR / "knn_features.pkl"
DECAY_MODEL_PATH = MODELS_DIR / "decay_model.pkl"
DECAY_FEATURES_PATH = MODELS_DIR / "decay_features.pkl"
MODEL_WEIGHTS_PATH = MODELS_DIR / "model_weights.pkl"

# 模型参数 (示例)
KNN_K = 5
XGB_PARAMS = {
    'objective': 'reg:squarederror',
    'max_depth': 5,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.7,
    'random_state': 42,
    'n_jobs': -1
}
MODEL_WEIGHTS = {'xgb': 0.6, 'knn': 0.3, 'decay': 0.1}

# API 设置
PRICE_RANGE_FACTOR_LOW = 0.85
PRICE_RANGE_FACTOR_HIGH = 1.15
MINIMUM_PRICE = 50
