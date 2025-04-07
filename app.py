# app.py
from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import joblib
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).resolve().parent))

import config # 导入配置文件
# 显式导入需要的工具函数，避免命名空间冲突
from src.utils import parse_description, parse_ram # 导入辅助函数

app = Flask(__name__)

# --- 加载模型和预处理组件 (在启动时加载一次) ---
try:
    print("正在加载模型和组件...")
    xgb_model = joblib.load(config.XGB_MODEL_PATH)
    weights = joblib.load(config.MODEL_WEIGHTS_PATH)
    feature_names = joblib.load(config.FEATURE_NAMES_PATH)
    scaler = joblib.load(config.SCALER_PATH)
    print("XGBoost, Weights, FeatureNames, Scaler 加载成功。")

    # 条件加载KNN和Decay模型
    try:
        knn_model = joblib.load(config.KNN_MODEL_PATH)
        knn_features = joblib.load(config.KNN_FEATURES_PATH)
        print("KNN 模型加载成功。")
    except FileNotFoundError:
        print("KNN 模型文件未找到，将在预测中禁用KNN。")
        knn_model = None
        weights['knn'] = 0 # 禁用权重

    try:
        decay_model = joblib.load(config.DECAY_MODEL_PATH)
        decay_features = joblib.load(config.DECAY_FEATURES_PATH)
        print("Decay 模型加载成功。")
    except FileNotFoundError:
        print("Decay 模型文件未找到，将在预测中禁用Decay模型。")
        decay_model = None
        weights['decay'] = 0 # 禁用权重

    # 重新归一化权重（如果某个模型加载失败）
    active_models_sum = sum(weights[k] for k in weights if (k == 'xgb' and xgb_model is not None) or \
                                                          (k == 'knn' and knn_model is not None) or \
                                                          (k == 'decay' and decay_model is not None))
    if active_models_sum > 0 and active_models_sum < 1.0:
         print("部分模型加载失败，重新归一化权重...")
         scale_factor = 1.0 / active_models_sum
         for k in weights:
             weights[k] *= scale_factor
    print(f"最终使用的模型权重: {weights}")
    MODELS_LOADED = True

except FileNotFoundError as e:
    print(f"错误: 加载模型或组件失败 - {e}。API可能无法正常工作。")
    MODELS_LOADED = False
except Exception as e:
     print(f"加载模型时发生未知错误: {e}")
     MODELS_LOADED = False


# --- 定义特征处理函数 (需要与feature_engineering.py中的逻辑严格一致!) ---
def preprocess_input_api(data):
    # data 是一个字典
    df = pd.DataFrame([data])

    # --- 执行与训练时相同的特征工程步骤 ---
    # (与 src/feature_engineering.py 中的逻辑保持一致，但只处理单行)
    # 1. 解析/设置基本特征
    df['ram_size'] = df['ram_desc'].apply(lambda x: parse_ram(x)) # 使用导入的函数
    # ... (处理 release_year, cpu_score 等, 注意填充方式要稳定) ...
    df['release_year'] = pd.to_numeric(df.get('release_year', config.BASE_DIR.now().year - 2), errors='coerce').fillna(config.BASE_DIR.now().year - 2).astype(int)
    df['cpu_score'] = pd.to_numeric(df.get('cpu_score', 3000), errors='coerce').fillna(3000) # 使用默认值

    # 2. 时间特征
    current_year = config.BASE_DIR.now().year
    df['age'] = (current_year - df['release_year']).clip(lower=0)
    df['age_factor'] = 0.9 ** df['age']

    # 3. 性能等级
    bins = [-np.inf, 2000, 5000, 10000, np.inf]
    labels = ['low', 'mid', 'high', 'very_high']
    df['performance_tier'] = pd.cut(df['cpu_score'], bins=bins, labels=labels, right=False)

    # 4. One-Hot Encoding (关键：需要对齐训练时的所有列)
    categorical_features = ['brand', 'gpu_type', 'storage_type', 'screen_condition', 'battery_health', 'performance_tier']
    for col in categorical_features:
       df[col] = df.get(col, 'Unknown') # 使用 get 获取，提供默认值
       df[col] = df[col].astype(str).fillna('Unknown')

    df_encoded = pd.get_dummies(df, columns=categorical_features, dummy_na=False)

    # **对齐特征列**
    aligned_df = pd.DataFrame(columns=feature_names, index=df_encoded.index).fillna(0)
    common_cols = list(set(aligned_df.columns) & set(df_encoded.columns))
    aligned_df[common_cols] = df_encoded[common_cols]

    # 5. 数值特征标准化
    numerical_features = aligned_df.select_dtypes(include=np.number).columns.tolist()
    numerical_features_present = [f for f in numerical_features if f in aligned_df.columns]
    if numerical_features_present:
         # 检查scaler是否加载成功
         if 'scaler' in globals() and scaler is not None:
             aligned_df[numerical_features_present] = scaler.transform(aligned_df[numerical_features_present])
         else:
             print("警告: Scaler未加载，未进行标准化。")


    return aligned_df[feature_names] # 确保返回训练时的列顺序

# --- API Endpoint ---
@app.route('/predict', methods=['POST'])
def predict():
    if not MODELS_LOADED:
        return jsonify({'error': '模型或依赖组件未成功加载，服务不可用'}), 503 # Service Unavailable

    try:
        data = request.json
        print(f"收到请求数据: {data}")

        # 如果输入是文本描述，先解析
        if 'description' in data and isinstance(data['description'], str):
            print("解析文本描述...")
            parsed_info = parse_description(data['description']) # 使用导入的函数
            # 合并信息，让 JSON 中明确给出的字段覆盖解析出的字段
            base_info = data.copy()
            base_info.update(parsed_info) # 解析结果覆盖默认值
            base_info.update(data) # 用户输入覆盖解析结果
            data = base_info
            # del data['description'] # 可以选择移除原始描述
            print(f"解析并合并后数据: {data}")


        # 数据预处理/特征工程
        print("进行特征处理...")
        features_df = preprocess_input_api(data)
        print(f"处理后特征维度: {features_df.shape}")
        # print(f"处理后特征样本: \n{features_df.head().to_string()}") # 打印样本用于调试

        # 模型预测
        print("进行模型预测...")
        final_prediction = 0.0
        if xgb_model:
            xgb_pred = xgb_model.predict(features_df)[0]
            final_prediction += weights['xgb'] * xgb_pred
            print(f"XGB Pred: {xgb_pred:.2f}")

        if knn_model:
            # 确保只使用KNN训练时的特征
            knn_input_features = features_df[knn_features]
            knn_pred = knn_model.predict(knn_input_features)[0]
            final_prediction += weights['knn'] * knn_pred
            print(f"KNN Pred: {knn_pred:.2f}")

        if decay_model:
             # 确保只使用Decay模型训练时的特征
            decay_input_features = features_df[decay_features]
            decay_pred = decay_model.predict(decay_input_features)[0]
            final_prediction += weights['decay'] * decay_pred
            print(f"Decay Pred: {decay_pred:.2f}")

        # 确保价格不为负
        final_prediction = max(0, float(final_prediction))
        print(f"最终预测价格 (原始): {final_prediction:.2f}")


        # (可选) 应用区域价格系数 / 人工校准系数
        # final_prediction *= get_region_coefficient(...)
        # final_prediction *= get_calibration_factor(...)

        # 格式化输出价格区间
        price_low = int(final_prediction * config.PRICE_RANGE_FACTOR_LOW)
        price_high = int(final_prediction * config.PRICE_RANGE_FACTOR_HIGH)
        price_low = max(config.MINIMUM_PRICE, price_low) # 应用最低价
        price_high = max(price_low + 50, price_high) # 保证区间宽度

        response_data = {
            'predicted_price': int(round(final_prediction)), # 四舍五入取整
            'price_range_low': price_low,
            'price_range_high': price_high,
            'price_range_str': f"{price_low}-{price_high}元"
        }
        print(f"返回结果: {response_data}")
        return jsonify(response_data)

    except KeyError as e:
         print(f"预测时发生KeyError: {e} - 输入数据可能缺少必要字段。")
         return jsonify({'error': f'Missing key in input data or processing: {e}'}), 400
    except Exception as e:
        print(f"预测过程中发生错误: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误栈
        return jsonify({'error': 'Prediction failed due to an internal error.', 'message': str(e)}), 500

# --- 根路径或其他辅助端点 ---
@app.route('/')
def home():
    return "旧电脑估价模型 API 已启动。请使用 /predict 端点进行估价。"

# --- 启动 Flask 应用 ---
if __name__ == '__main__':
    # 生产环境建议使用 Gunicorn: gunicorn --bind 0.0.0.0:5000 app:app
    app.run(host='0.0.0.0', port=5000, debug=False) # debug=False 用于生产或稳定测试
