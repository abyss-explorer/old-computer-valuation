# scripts/scraper_basic.py

import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import re # 引入 re

# 添加项目根目录到 Python 路径，以便导入 config
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

try:
    import config # 尝试导入配置文件
    print("成功导入 config.py")
    BASE_URL = config.SCRAPER_BASIC_BASE_URL
    SEARCH_KEYWORD = config.SCRAPER_SEARCH_KEYWORD
    MAX_PAGES = config.SCRAPER_BASIC_MAX_PAGES
    OUTPUT_CSV_FILE = config.SCRAPER_OUTPUT_DIR / f'basic_scraped_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    HEADERS = {'User-Agent': config.SCRAPER_USER_AGENT}
    SLEEP_MIN = config.SCRAPER_SLEEP_MIN
    SLEEP_MAX = config.SCRAPER_SLEEP_MAX
except ImportError:
    print("警告: 未找到或无法导入 config.py。将使用脚本内定义的默认值。")
    # --- 如果没有 config.py，则使用以下默认值 ---
    BASE_URL = "http://example-static-site.com/search" # !!! 必须替换 !!!
    SEARCH_KEYWORD = "二手 联想 小新"
    MAX_PAGES = 3
    OUTPUT_CSV_FILE = Path(f'basic_scraped_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv') # 保存在当前目录
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    SLEEP_MIN = 2.0
    SLEEP_MAX = 5.0
    # 确保输出目录存在 (如果不在config中创建)
    OUTPUT_CSV_FILE.parent.mkdir(parents=True, exist_ok=True)


# --- 辅助函数 (fetch_page, parse_html) ---
def fetch_page(url):
    """发送请求获取页面内容"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        print(f"成功获取页面: {url} (状态码: {response.status_code})")
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX)) # 使用配置的延时
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"请求页面失败: {url} - 错误: {e}")
        return None

def parse_html(html_content):
    """解析 HTML，提取所需数据"""
    # !!! 警告: 此函数包含大量假设，几乎肯定需要针对目标网站重写 !!!
    # !!! 这个简单版本很可能无法在闲鱼/转转等动态网站上工作 !!!
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'lxml')
    data_list = []
    # !!! 假设: 商品项在 class="item-card" 的 div 中 (必须修改!) !!!
    items = soup.find_all('div', class_='item-card')
    print(f"在当前页面找到 {len(items)} 个商品项 (基于假设的选择器 'div.item-card')")

    for item in items:
        try:
            data = {}
            # --- 再次强调: 以下定位符都是假设，必须修改! ---
            title_tag = item.find('a', class_='title') # 假设标题
            data['description'] = title_tag.get_text(strip=True) if title_tag else 'N/A'
            price_tag = item.find('span', class_='price') # 假设价格
            price_text = price_tag.get_text(strip=True) if price_tag else '0'
            data['actual_price'] = ''.join(filter(str.isdigit, price_text.split('.')[0])) or '0'
            info_tag = item.find('div', class_='info') # 假设其他信息
            info_text = info_tag.get_text(separator='|', strip=True) if info_tag else ''
            data['location'] = info_text.split('|')[0] if '|' in info_text else info_text
            data['post_date_text'] = info_text.split('|')[-1] if '|' in info_text else 'N/A'

            # --- 假设的配置解析 ---
            desc_lower = data['description'].lower()
            if 'gb' in desc_lower:
                ram_match = re.search(r'(\d+)\s*g', desc_lower)
                data['ram_size'] = ram_match.group(1) if ram_match else 'Unknown'
            else: data['ram_size'] = 'Unknown'
            data['brand'] = 'Unknown' # 需要规则判断
            # ... (其他字段设为 Unknown) ...
            for field in ['release_year', 'cpu_score', 'gpu_type', 'storage_type', 'screen_condition', 'battery_health']:
                data[field] = 'Unknown'

            data['scrape_timestamp'] = datetime.now().isoformat()

            if data['description'] != 'N/A' and data['actual_price'] != '0':
                data_list.append(data)
        except Exception as e:
            print(f"解析单个项目时出错: {e}")
            continue
    return data_list

# --- 主程序 ---
if __name__ == "__main__":
    all_data = []
    print(f"--- 开始基础爬虫 (requests + BS4) ---")
    print(f"目标关键词: '{SEARCH_KEYWORD}'")
    print(f"最大页数: {MAX_PAGES}")
    print(f"!!! 警告: 此脚本可能无法适用于动态加载内容的网站 (如闲鱼/转转) !!!")
    print(f"!!! 需要根据目标网站修改 HTML 解析逻辑 !!!")

    for page in range(1, MAX_PAGES + 1):
        print(f"\n--- 正在处理第 {page} 页 ---")
        try:
            # 构建 URL (需要适配目标网站的分页逻辑!)
            # 这是一个非常通用的假设，几乎肯定需要修改
            from urllib.parse import quote
            target_url = f"{BASE_URL}?query={quote(SEARCH_KEYWORD)}&page={page}"
        except Exception as e:
            print(f"构建 URL 时出错 (请检查 BASE_URL 和分页逻辑): {e}")
            break

        html = fetch_page(target_url)
        if html:
            page_data = parse_html(html)
            if not page_data and page > 1: # 第一页没数据可能正常，后面页没有可能结束了
                print("当前页未解析到数据，可能已到达末页或规则失效。")
                # break
            all_data.extend(page_data)
            print(f"第 {page} 页处理完毕，获得 {len(page_data)} 条数据。累计数据: {len(all_data)}")
        else:
            print(f"无法获取第 {page} 页内容，停止爬取。")
            break

        if page < MAX_PAGES:
             print("页面间暂停...")
             time.sleep(random.uniform(SLEEP_MIN + 1, SLEEP_MAX + 1)) # 页间暂停长一点

    # --- 保存数据 ---
    if all_data:
        print(f"\n爬取完成，总共获得 {len(all_data)} 条数据。")
        print(f"正在将数据保存到 {OUTPUT_CSV_FILE} ...")
        df = pd.DataFrame(all_data)
        desired_columns = [ # 定义期望列顺序
            'description', 'actual_price', 'location', 'post_date_text',
            'brand', 'release_year', 'cpu_score', 'gpu_type', 'ram_size',
            'storage_type', 'screen_condition', 'battery_health',
            'scrape_timestamp']
        df_output = pd.DataFrame(columns=desired_columns)
        for col in desired_columns:
             df_output[col] = df.get(col) # 使用 get 避免 KeyError

        try:
            df_output.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
            print(f"数据成功保存到: {OUTPUT_CSV_FILE}")
        except Exception as e:
            print(f"保存 CSV 文件失败: {e}")
    else:
        print("没有抓取到有效数据，未生成文件。")
