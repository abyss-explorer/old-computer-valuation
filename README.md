# 旧电脑估价模型项目

本项目旨在使用经典机器学习方法（XGBoost, KNN, 线性回归混合模型）根据旧电脑的硬件配置、使用状况等因素预测其二手价值。

## 项目结构

(在此处描述上述目录结构)

## 环境设置

1.  **克隆仓库:**
    ```bash
    git clone <your-repo-url>
    cd old_computer_valuation
    ```
2.  **创建虚拟环境 (推荐):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate  # Windows
    ```
3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

## 数据准备

* 将原始数据放入 `data/raw_data.csv`。数据应包含字段：`brand`, `release_year`, `cpu_score`, `gpu_type`, `ram_desc`, `storage_type`, `screen_condition`, `battery_health`, `actual_price`, `post_date` 等 (根据实际情况调整)。
* (可选) 硬件天梯图数据需要自行准备或集成到代码中。

## 使用方法

1.  **特征工程:**
    ```bash
    python src/feature_engineering.py
    ```
    这将读取 `data/raw_data.csv`，进行处理，并将标准化器 (`scaler.pkl`) 和特征名 (`feature_names.pkl`) 保存到 `models/` 目录，(可选) 保存处理后的数据到 `data/processed_data.csv`。

2.  **模型训练:**
    ```bash
    python src/train_model.py
    ```
    这将加载处理后的数据 (或直接从特征工程步骤获取 DataFrame)，训练 XGBoost, KNN, Decay 模型，进行评估，并将训练好的模型 (`.pkl`) 和权重保存到 `models/` 目录。

3.  **启动 API 服务:**
    ```bash
    # 开发模式
    flask run --host=0.0.0.0 --port=5000
    # 或直接运行 python app.py (如果 app.run 在 __main__ 块中)

    # 生产模式 (推荐使用 Gunicorn)
    # gunicorn --bind 0.0.0.0:5000 app:app
    ```

4.  **调用 API:**
    向 `http://<your-server-ip>:5000/predict` 发送 POST 请求，JSON body 包含电脑配置信息。例如:
    ```json
    {
      "brand": "Apple",
      "release_year": 2021,
      "cpu_score": 7000,
      "gpu_type": "Integrated",
      "ram_desc": "8GB",
      "storage_type": "SSD",
      "screen_condition": "完美",
      "battery_health": "良好"
    }
    ```
    或包含文本描述：
    ```json
    {
      "description": "苹果 MacBook Pro M1 芯片 8G内存 256G固态硬盘 深空灰 外观完好 电池健康度90%"
    }
    ```

## 注意事项

* 爬虫脚本未包含在此核心项目中，需另行开发并遵守相关规定。
* 模型性能依赖于数据质量和特征工程。
* 配置文件 (`config.py`) 用于管理路径和参数，增强灵活性。
