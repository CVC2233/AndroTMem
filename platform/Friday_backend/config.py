# config.py

import os
import sys

# ==============================================================================
#                      动态路径计算 (Do not change this part)
# ==============================================================================

def get_base_path():
    """获取应用的基础路径，兼容开发环境和PyInstaller打包环境"""
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件路径
        return os.path.dirname(sys.executable)
    else:
        # 正常的 .py 文件路径
        return os.path.dirname(os.path.abspath(__file__))

# 获取基础路径
_BASE_DIR = get_base_path()


# ==============================================================================
#                      可配置的字段 (Editable Configuration)
# ==============================================================================

# --- ADB 和安卓设备配置 ---
CLOUD_DEVICE_IP_PORT = 'emulator-5554'
ADB_PATH = 'adb'

# --- 应用程序配置 ---
DEFAULT_APP_NAME = 'com.sankuai.meituan.takeoutnew'

# --- 路径配置 (现在都是绝对路径了) ---
# 所有数据都将保存在可执行文件旁边的 'data' 文件夹中
BASE_DATA_DIR = os.path.join(_BASE_DIR, '../data')

LOG_PATH = os.path.join(BASE_DATA_DIR, 'logs', 'app.log')
BASE_ANNO_PATH = os.path.join(BASE_DATA_DIR, 'annotations')
BASE_SCREENSHOT_PATH = os.path.join(BASE_DATA_DIR, 'screenshots_tmp')
IMGS_PATH = os.path.join(BASE_DATA_DIR, 'imgs_all')

# 注意：你的原始代码中还有一个硬编码的 'screenshots' 目录
# 在 main 函数中 os.makedirs('screenshots', exist_ok=True)
# 为了统一管理，也建议将其放入 data 目录
# 例如：MAIN_SCREENSHOTS_PATH = os.path.join(BASE_DATA_DIR, 'screenshots')


# --- 外部服务配置 ---
VLLM_API_URL = "http://localhost:8000/v1/chat/completions"

# --- Flask 服务配置 ---
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5001