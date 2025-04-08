# scripts/scraper_selenium.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import re # 引入 re

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

try:
    import config
    print("成功导入 config.py")
    START_URL = config.SCRAPER_SELENIUM_START_URL
    SEARCH_KEYWORD = config.SCRAPER_SEARCH_KEYWORD # 可能不需要，如果 URL 包含搜索
    MAX_ITEMS_TO_SCRAPE = config.SCRAPER_SELENIUM_MAX_ITEMS
    OUTPUT_CSV_FILE = config.SCRAPER_OUTPUT_DIR / f'selenium_scraped_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    USER_AGENT = config.SCRAPER_USER_AGENT
    SLEEP_MIN = config.SCRAPER_SLEEP_MIN
    SLEEP_MAX = config.SCRAPER_SLEEP_MAX
except ImportError:
    print("警告: 未找到或无法导入 config.py。将使用脚本内定义的默认值。")
    # --- 如果没有 config.py ---
    START_URL = "https://complex-dynamic-site.com" # !!! 必须替换 !!!
    SEARCH_KEYWORD = "二手 联想 小新"
    MAX_ITEMS_TO_SCRAPE = 50
    OUTPUT_CSV_FILE = Path(f'selenium_scraped_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    SLEEP_MIN = 2.0
    SLEEP_MAX = 5.0
    OUTPUT_CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

# --- WebDriver 初始化 ---
def initialize_driver():
    print("正在初始化 WebDriver...")
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 无头模式测试时可能需要注释掉，以便观察
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'user-agent={USER_AGENT}')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # 添加更多反检测选项 (可选)
    options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("WebDriver 初始化成功。")
        return driver
    except Exception as e:
        print(f"WebDriver 初始化失败: {e}")
        return None

# --- 主程序 ---
if __name__ == "__main__":
    all_data = []
    scraped_count = 0
    current_page = 1

    print(f"--- 开始 Selenium 爬虫 ---")
    print(f"目标起始 URL: {START_URL}")
    print(f"目标抓取数量: {MAX_ITEMS_TO_SCRAPE}")
    print(f"!!! 警告: 需要根据目标网站修改页面交互逻辑 (登录、搜索、滚动、点击下一页) !!!")
    print(f"!!! 需要根据目标网站修改元素定位器 (CSS 选择器) !!!")

    driver = initialize_driver()

    if driver:
        try:
            driver.get(START_URL)
            print(f"已打开页面: {START_URL}")
            time.sleep(random.uniform(3, 5)) # 等待初步加载

            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # +++ 在这里添加特定于目标网站的操作:                      +++
            # +++ 1. 处理登录 (如果需要)                             +++
            # +++ 2. 输入搜索关键词 (如果起始 URL 不是搜索结果页)        +++
            # +++ 3. 点击搜索按钮                                     +++
            # +++ 示例:                                               +++
            # +++ search_box = driver.find_element(By.ID, 'search-input') +++
            # +++ search_box.send_keys(SEARCH_KEYWORD)                 +++
            # +++ search_button = driver.find_element(By.CSS_SELECTOR, 'button.search-btn') +++
            # +++ search_button.click()                              +++
            # +++ time.sleep(5) # 等待搜索结果加载                      +++
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            wait = WebDriverWait(driver, 15) # 增加等待时间

            while scraped_count < MAX_ITEMS_TO_SCRAPE:
                print(f"\n--- 正在处理第 {current_page} 页 (已抓取 {scraped_count}/{MAX_ITEMS_TO_SCRAPE} 项) ---")

                # 尝试向下滚动加载更多内容
                try:
                    last_height = driver.execute_script("return document.body.scrollHeight")
                    for _ in range(3): # 滚动几次
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            # print("滚动到底部，高度未增加。")
                            break
                        last_height = new_height
                except Exception as scroll_e:
                    print(f"滚动页面时出错: {scroll_e}")


                # !!! 定位商品元素 (必须根据实际情况修改!) !!!
                # 假设商品项是 class="product-item" 的 div
                item_selector = 'div.product-item' # !!! 必须修改 !!!
                try:
                    item_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, item_selector)))
                    print(f"在当前页面找到 {len(item_elements)} 个商品元素 (基于选择器 '{item_selector}')")
                except TimeoutException:
                    print(f"等待商品元素 ('{item_selector}') 超时，可能页面结构已更改或无更多内容。")
                    if current_page == 1 and not all_data: # 如果第一页就找不到，很可能是选择器错了
                         print("错误：请检查商品元素的选择器是否正确！")
                    break # 停止

                # --- 遍历提取数据 (必须修改!) ---
                new_items_on_page = 0
                for element in item_elements:
                    # 可能需要检查这个元素是否已经被处理过（如果滚动加载导致重复）
                    if scraped_count >= MAX_ITEMS_TO_SCRAPE: break
                    try:
                        data = {}
                        # !!! 以下是假设的选择器，必须修改 !!!
                        title_element = element.find_element(By.CSS_SELECTOR, 'a.product-title') # 假设标题
                        data['description'] = title_element.text.strip() if title_element else 'N/A'

                        price_element = element.find_element(By.CSS_SELECTOR, 'span.product-price') # 假设价格
                        price_text = price_element.text.strip() if price_element else '0'
                        data['actual_price'] = ''.join(filter(str.isdigit, price_text.split('.')[0])) or '0'

                        # ... 尝试提取其他信息，同样需要适配选择器 ...
                        # info_element = element.find_element(By.CSS_SELECTOR, 'div.product-meta')
                        # data['info'] = info_element.text.strip() if info_element else 'N/A'

                        # 解析配置 (仍然困难，需要具体规则)
                        # ...
                        data['ram_size'] = 'Unknown'
                        data['brand'] = 'Unknown'
                        # ... 其他字段设为 Unknown ...
                        for field in ['release_year', 'cpu_score', 'gpu_type', 'storage_type', 'screen_condition', 'battery_health']:
                             data[field] = 'Unknown'

                        data['scrape_timestamp'] = datetime.now().isoformat()

                        # 简单的去重逻辑 (基于描述和价格)，或者使用更复杂的ID
                        item_key = (data['description'], data['actual_price'])
                        # 这里需要一个集合来存储已处理项的键
                        # if item_key not in processed_keys_set: # 假设有 processed_keys_set
                        if data['description'] != 'N/A' and data['actual_price'] != '0':
                             all_data.append(data)
                             scraped_count += 1
                             new_items_on_page += 1
                             # processed_keys_set.add(item_key) # 添加到已处理集合

                    except NoSuchElementException: continue # 元素内缺少子元素，跳过
                    except Exception as e: print(f"处理单个元素时出错: {e}"); continue

                print(f"本轮找到 {new_items_on_page} 个新项目。")
                if scraped_count >= MAX_ITEMS_TO_SCRAPE: break # 达到目标数量

                # --- 处理分页 (必须修改!) ---
                try:
                    # !!! 假设 "下一页" 按钮的选择器是 'button.next' !!!
                    next_button_selector = 'button.next' # !!! 必须修改 !!!
                    next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector)))
                    print("找到'下一页'按钮，准备点击...")
                    # 尝试滚动到按钮可见区域再点击
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(0.5)
                    # 使用 JS 点击可能更稳定
                    driver.execute_script("arguments[0].click();", next_button)
                    print("已点击'下一页'。")
                    current_page += 1
                    time.sleep(random.uniform(SLEEP_MIN + 1, SLEEP_MAX + 1)) # 等待新页面加载
                except TimeoutException:
                    print("找不到或无法点击'下一页'按钮 (基于选择器 '{next_button_selector}')，爬取结束。")
                    break
                except Exception as e:
                    print(f"点击下一页 ('{next_button_selector}') 时出错: {e}")
                    break

        except Exception as e:
            print(f"爬取主循环中发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()
                print("浏览器已关闭。")

    # --- 保存数据 ---
    if all_data:
        print(f"\n爬取结束，总共获得 {len(all_data)} 条有效数据。")
        print(f"正在将数据保存到 {OUTPUT_CSV_FILE} ...")
        df = pd.DataFrame(all_data)
        desired_columns = [ # 定义期望列顺序
             'description', 'actual_price', #'info',
             'brand', 'release_year', 'cpu_score', 'gpu_type', 'ram_size',
             'storage_type', 'screen_condition', 'battery_health',
             'scrape_timestamp']
        df_output = pd.DataFrame(columns=desired_columns)
        for col in desired_columns:
              df_output[col] = df.get(col)

        try:
            df_output.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
            print(f"数据成功保存到: {OUTPUT_CSV_FILE}")
        except Exception as e:
            print(f"保存 CSV 文件失败: {e}")
    else:
        print("没有抓取到有效数据，未生成文件。")
