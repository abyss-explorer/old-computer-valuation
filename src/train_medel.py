# src/train_model.py
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.neighbors import KNeighborsRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import joblib
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils import smape # 导入评估指标
from src.feature_engineering import run_feature_engineering # 可以直接调用特征工程
import config # 导入配置文件

def train_and_evaluate():
    print("开始模型训练...")
    # --- 1. 获取数据 ---
    # 可以直接调用特征工程函数获取X, y
    X, y = run_feature_engineering()
    if X is None or y is None:
        print("错误：特征工程失败，无法进行训练。")
        return

    # 或者加载之前保存的处理后数据
    # try:
    #     processed_data = pd.read_csv(config.PROCESSED_DATA_PATH)
    #     feature_names = joblib.load(config.FEATURE_NAMES_PATH)
    #     X = processed_data[feature_names]
    #     y = processed_data['actual_price']
    # except FileNotFoundError:
    #     print(f"错误: 处理后的数据或特征名文件未找到。请先运行 feature_engineering.py")
    #     return

    feature_names = list(X.columns) # 获取最新的特征名

    # --- 2. 数据集划分 ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"训练集大小: {X_train.shape}, 测试集大小: {X_test.shape}")

    # --- 3. 训练各模型 (同之前步骤三的代码) ---
    models = {}
    predictions = {}
    smapes = {}

    # XGBoost
    print("训练 XGBoost...")
    xgb_model = xgb.XGBRegressor(**config.XGB_PARAMS) # 使用配置文件中的参数
    xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], eval_metric='rmse', early_stopping_rounds=10, verbose=False)
    models['xgb'] = xgb_model
    predictions['xgb'] = xgb_model.predict(X_test)
    smapes['xgb'] = smape(y_test, predictions['xgb'])
    print(f"XGBoost Test sMAPE: {smapes['xgb']:.2f}%")
    joblib.dump(xgb_model, config.XGB_MODEL_PATH)
    print(f"XGBoost 模型已保存到 {config.XGB_MODEL_PATH}")

    # KNN
    print("训练 KNN...")
    # 确保使用了正确的、存在于当前特征中的 knn 特征名
    knn_features_potential = ['cpu_score', 'ram_size', 'age'] # 示例核心特征
    # 从配置文件或动态确定哪些特征是one-hot编码后的存储类型等
    # knn_features_potential.extend([f for f in feature_names if 'storage_type_' in f]) # 添加one-hot编码特征示例
    knn_features = [f for f in knn_features_potential if f in feature_names]

    if knn_features:
        knn_model = KNeighborsRegressor(n_neighbors=config.KNN_K, weights='distance', n_jobs=-1)
        knn_model.fit(X_train[knn_features], y_train)
        models['knn'] = knn_model
        predictions['knn'] = knn_model.predict(X_test[knn_features])
        smapes['knn'] = smape(y_test, predictions['knn'])
        print(f"KNN (k={config.KNN_K}) Test sMAPE: {smapes['knn']:.2f}%")
        joblib.dump(knn_model, config.KNN_MODEL_PATH)
        joblib.dump(knn_features, config.KNN_FEATURES_PATH) # 保存KNN使用的特征
        print(f"KNN 模型及特征列表已保存。")
    else:
        print("警告: KNN所需特征不足，跳过KNN训练。")
        models['knn'] = None

    # Decay Model (Linear Regression)
    print("训练 Decay Model...")
    decay_features_potential = ['age_factor', 'age'] # 示例
    decay_features = [f for f in decay_features_potential if f in feature_names]
    if decay_features:
        decay_model = LinearRegression()
        decay_model.fit(X_train[decay_features], y_train)
        models['decay'] = decay_model
        predictions['decay'] = decay_model.predict(X_test[decay_features])
        smapes['decay'] = smape(y_test, predictions['decay'])
        print(f"Decay Model Test sMAPE: {smapes['decay']:.2f}%")
        joblib.dump(decay_model, config.DECAY_MODEL_PATH)
        joblib.dump(decay_features, config.DECAY_FEATURES_PATH) # 保存Decay模型使用的特征
        print(f"Decay 模型及特征列表已保存。")
    else:
        print("警告: Decay模型所需特征不足，跳过训练。")
        models['decay'] = None

    # --- 4. 混合模型评估与权重保存 ---
    print("评估混合模型...")
    weights = config.MODEL_WEIGHTS.copy() # 从配置加载权重
    final_pred_test = np.zeros_like(y_test, dtype=float)
    active_weight_sum = 0

    # 检查模型是否训练成功并累加预测
    if models['xgb']:
        final_pred_test += weights['xgb'] * predictions['xgb']
        active_weight_sum += weights['xgb']
    else: weights['xgb'] = 0 # 如果失败则权重置零

    if models['knn']:
        final_pred_test += weights['knn'] * predictions['knn']
        active_weight_sum += weights['knn']
    else: weights['knn'] = 0

    if models['decay']:
        final_pred_test += weights['decay'] * predictions['decay']
        active_weight_sum += weights['decay']
    else: weights['decay'] = 0

    # 归一化权重，如果部分模型失败
    if active_weight_sum > 0 and active_weight_sum < 1.0:
        scale = 1.0 / active_weight_sum
        for key in weights:
            weights[key] *= scale
        # 重新计算最终预测
        final_pred_test = np.zeros_like(y_test, dtype=float)
        if models['xgb']: final_pred_test += weights['xgb'] * predictions['xgb']
        if models['knn']: final_pred_test += weights['knn'] * predictions['knn']
        if models['decay']: final_pred_test += weights['decay'] * predictions['decay']


    final_smape = smape(y_test, final_pred_test)
    print(f"\nHybrid Model Test sMAPE: {final_smape:.2f}%")

    lower_bound = final_pred_test * config.PRICE_RANGE_FACTOR_LOW
    upper_bound = final_pred_test * config.PRICE_RANGE_FACTOR_HIGH
    hit_rate = np.mean((y_test >= lower_bound) & (y_test <= upper_bound)) * 100
    print(f"Price Range Hit Rate: {hit_rate:.2f}%")

    # 保存最终使用的权重
    joblib.dump(weights, config.MODEL_WEIGHTS_PATH)
    print(f"模型权重已保存到 {config.MODEL_WEIGHTS_PATH}")

    # --- 5. 特征重要性分析 (XGBoost) ---
    if models['xgb']:
        feature_importances = pd.DataFrame({
            'feature': feature_names, # 使用训练时的特征名
            'importance': models['xgb'].feature_importances_
        }).sort_values('importance', ascending=False)
        print("\nTop 10 Feature Importances (XGBoost):")
        print(feature_importances.head(10))

    print("模型训练和评估完成。")

if __name__ == "__main__":
    train_and_evaluate()
