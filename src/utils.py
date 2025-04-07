# src/utils.py
import numpy as np
import re
from datetime import datetime

def smape(y_true, y_pred):
    """计算对称平均绝对百分比误差 (sMAPE)"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    numerator = np.abs(y_pred - y_true)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
    ratio = np.where(denominator == 0, 0, numerator / denominator)
    return np.mean(ratio) * 100

def parse_ram(desc, default_ram=8):
    """从文本描述解析内存大小 (GB)"""
    if isinstance(desc, (int, float)) and not pd.isna(desc):
        return int(desc)
    if isinstance(desc, str):
        match = re.search(r'(\d+)\s*G', desc, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return default_ram # 返回默认值

def parse_description(text):
    """从文本描述提取关键硬件信息 (简化版)"""
    # (将之前 app.py 中的解析逻辑移到这里)
    info = {}
    # ... (CPU, RAM, 存储, 品牌等解析逻辑) ...
    cpu_match = re.search(r'(i[3579]\s?-\s?\d{4,5}[A-Za-z]*)', text, re.IGNORECASE)
    if cpu_match: info['cpu_raw'] = cpu_match.group(1)
    else: info['cpu_raw'] = None

    ram_match = re.search(r'(\d+)\s*G[B]?\s*(内存)?', text, re.IGNORECASE)
    if ram_match: info['ram_desc'] = f"{ram_match.group(1)}GB"
    else: info['ram_desc'] = 'Unknown' # 或者根据上下文推断

    # ... 其他解析规则 ...
    if '联想' in text: info['brand'] = 'Lenovo'
    elif '戴尔' in text: info['brand'] = 'Dell'
    elif '苹果' in text or 'MacBook' in text: info['brand'] = 'Apple'
    else: info['brand'] = 'Other'

    # 假设默认值或尝试从文本提取其他字段
    info.setdefault('storage_type', 'Unknown')
    info.setdefault('screen_condition', '良好') # 假设默认
    info.setdefault('battery_health', '良好') # 假设默认
    info.setdefault('gpu_type', 'Integrated') # 假设默认
    info.setdefault('release_year', datetime.now().year - 2) # 假设默认2年前
    info.setdefault('cpu_score', 3000) # 假设默认分数

    return info

# 可以添加 get_region_coefficient, get_calibration_factor 等函数的占位符或实现
# def get_region_coefficient(ip_address): return 1.0
# def get_calibration_factor(data): return 1.0

# 确保导入pandas以处理NaN（如果在parse_ram等函数中使用了pd.isna）
try:
    import pandas as pd
except ImportError:
    pass # 如果只在特定函数中使用，可以在函数内部导入
