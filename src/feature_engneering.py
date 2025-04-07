# src/feature_engineering.py
import pandas as pd
import numpy as np
from datetime import datetime
import re
from sklearn.preprocessing import StandardScaler
import joblib
import sys
from pathlib import Path

# 添加src目录到Python路径，以便导入utils
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils import parse_ram # 导入辅助函数
import config # 导入配置文件

def run_feature_engineering():
    print("开始特征工程...")
    # --- 1. 加载数据 ---
    try:
        df = pd.read_csv(config.RAW_DATA_PATH)
        print(f"原始数据加载成功，行数: {len(df)}")
    except FileNotFoundError:
        print(f"错误: 原始数据文件未找到于 {config.RAW_DATA_PATH}")
        return None, None # 返回None表示失败

    # --- 2. 清洗与预处理 (同之前步骤二的代码) ---
    # ... (填充缺失值，类型转换等) ...
    df['ram_size'] = df['ram_desc'].apply(lambda x: parse_ram(x, default_ram=df['ram_size'].median() if not df['ram_size'].isnull().all() else 8))
    # ... (其他清洗步骤) ...
    # 移除价格异常或特征缺失过多的行
    df.dropna(subset=['actual_price', 'release_year', 'cpu_score'], inplace=True) # 关键特征不可缺


    # --- 3. 特征工程 (同之前步骤二的代码) ---
    current_year = datetime.now().year
    df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce')
    df.dropna(subset=['release_year'], inplace=True)
    df['release_year'] = df['release_year'].astype(int)
    df['age'] = current_year - df['release_year']
    df['age'] = df['age'].clip(lower=0) # 年龄不能为负
    df['age_factor'] = 0.9 ** df['age']

    df['cpu_score'] = pd.to_numeric(df['cpu_score'], errors='coerce')
    df.dropna(subset=['cpu_score'], inplace=True)
    bins = [-np.inf, 2000, 5000, 10000, np.inf]
    labels = ['low', 'mid', 'high', 'very_high']
    df['performance_tier'] = pd.cut(df['cpu_score'], bins=bins, labels=labels, right=False)

    categorical_features = ['brand', 'gpu_type', 'storage_type', 'screen_condition', 'battery_health', 'performance_tier']
    for col in categorical_features:
        df[col] = df[col].astype(str).fillna('Unknown') # 确保是字符串并填充

    df_encoded = pd.get_dummies(df, columns=categorical_features, dummy_na=False)

    # --- 4. 准备特征列表和目标变量 ---
    target = 'actual_price'
    # 移除原始列、中间列和非输入特征 (需要仔细检查这里的列表)
    original_cols_to_remove = ['ram_desc', 'post_date'] + categorical_features
    features_to_use = [col for col in df_encoded.columns if col != target and col not in original_cols_to_remove]

    # 检查特征列表是否为空
    if not features_to_use:
        print("错误：没有可用的特征列。请检查特征工程步骤。")
        return None, None

    X = df_encoded[features_to_use]
    y = df_encoded[target]

    # --- 5. 数值特征标准化 ---
    numerical_features = X.select_dtypes(include=np.number).columns.tolist()
    # 确保数值特征列表不为空再进行标准化
    if numerical_features:
        scaler = StandardScaler()
        X[numerical_features] = scaler.fit_transform(X[numerical_features])
        # 保存标准化器
        joblib.dump(scaler, config.SCALER_PATH)
        print(f"标准化器已保存到 {config.SCALER_PATH}")
    else:
        print("警告：未找到数值特征进行标准化。")


    # --- 6. 保存处理结果 ---
    # 保存特征名称列表 (非常重要，保证训练和预测时列顺序一致)
    joblib.dump(list(X.columns), config.FEATURE_NAMES_PATH)
    print(f"特征名称列表已保存到 {config.FEATURE_NAMES_PATH}")

    # (可选) 保存处理后的数据帧
    # data_to_save = pd.concat([X, y], axis=1)
    # data_to_save.to_csv(config.PROCESSED_DATA_PATH, index=False)
    # print(f"处理后的数据已保存到 {config.PROCESSED_DATA_PATH}")

    print("特征工程完成。")
    return X, y # 返回处理好的数据给训练脚本直接使用 (或者让训练脚本自行加载)


if __name__ == "__main__":
    run_feature_engineering()
