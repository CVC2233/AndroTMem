# 后端 Flask 应用 app.py
import base64
import io
from flask import Flask, request, jsonify, send_file
import subprocess
import json
import os
import re
import logging
from io import BytesIO
from PIL import Image
from prompt_templates import SHOPPING_QUESTION_PROMPT
import requests 
import uuid
import sys
from prompt_dispatcher import get_task_prompt
from flask_cors import CORS # 1. 导入 CORS
from openai import OpenAI
# 1. 初始化 Flask 应用
app = Flask(__name__)
CORS(app) # 2. 将 app 实例传递给 CORS，完成初始化
# 2. 从 config.py 文件加载配置
# 2. 动态确定 config.py 的路径并加载配置
#    这是解决 PyInstaller 问题的核心代码
def get_base_path():
    # 如果是 PyInstaller 打包的，sys.frozen 属性会被设置成 True
    if getattr(sys, 'frozen', False):
        # 返回可执行文件所在的目录
        return os.path.dirname(sys.executable)
    else:
        # 否则，返回脚本文件所在的目录
        return os.path.dirname(os.path.abspath(__file__))

try:
    # 构造 config.py 的绝对路径
    config_path = os.path.join(get_base_path(), 'config.py')
    
    # 检查文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError
    
    # 使用 from_pyfile 从绝对路径加载
    app.config.from_pyfile(config_path)

except FileNotFoundError:
    print(f"错误: 无法在路径 '{config_path}' 找到 'config.py' 文件。")
    print("请确保 config.py 文件与可执行文件或主脚本在同一目录下。")
    sys.exit(1) # 使用 sys.exit(1) 来终止程序，这比 exit() 更规范

# 3. 使用 app.config[] 来获取配置值
CLOUD_DEVICE_IP_PORT = app.config['CLOUD_DEVICE_IP_PORT']
ADB_PATH = app.config['ADB_PATH']
DEFAULT_APP_NAME = app.config['DEFAULT_APP_NAME']
LOG_PATH = app.config['LOG_PATH']
BASE_ANNO_PATH = app.config['BASE_ANNO_PATH']
BASE_SCREENSHOT_PATH = app.config['BASE_SCREENSHOT_PATH']
IMGS_PATH = app.config['IMGS_PATH']
API_URL = app.config['VLLM_API_URL']
# --- OpenAI-compatible API 配置 ---
# 通过环境变量提供密钥，避免将真实凭据提交到代码仓库。
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE") or None
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gemini-2.5-pro-preview-06-05")
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),            # 控制台输出
        logging.FileHandler(LOG_PATH, encoding='utf-8')  # 文件输出
    ]
)

openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE
        )
        logging.info("OpenAI 客户端初始化成功。")
    except Exception as e:
        logging.error(f"OpenAI 客户端初始化失败: {e}")
else:
    logging.warning("在 config.py 中未找到 OPENAI_API_KEY。/openai_infer 接口将不可用。")

# 确保日志和数据目录存在
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(BASE_ANNO_PATH, exist_ok=True)
os.makedirs(BASE_SCREENSHOT_PATH, exist_ok=True)
os.makedirs(IMGS_PATH, exist_ok=True)

# ADB操作
class ADBController:
    @staticmethod
    def connect_device():
        """通过 adb connect 连接远程设备"""
        logging.info(f"尝试连接设备: {CLOUD_DEVICE_IP_PORT}")
        result = subprocess.run([ADB_PATH, "connect", CLOUD_DEVICE_IP_PORT], capture_output=True, text=True)
        logging.info(result.stdout)
        if "connected" in result.stdout.lower():
            logging.info(f"成功连接设备：{CLOUD_DEVICE_IP_PORT}")
            return True
        else:
            logging.warning(f"连接失败：{result.stderr}")
            return False

    @staticmethod
    def get_screenshot():
        if not os.path.exists(BASE_SCREENSHOT_PATH):
            # 不存在则创建目录
            os.makedirs(BASE_SCREENSHOT_PATH)
            print(f"目录 {BASE_SCREENSHOT_PATH} 已创建。")
        # 定义目标路径
        local_path = f'{BASE_SCREENSHOT_PATH}/screen_{uuid.uuid4()}.png'
        # 确保本地文件夹存在
        if not os.path.exists(BASE_SCREENSHOT_PATH):
            os.makedirs(BASE_SCREENSHOT_PATH)

        # 使用adb截屏到设备
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'screencap', '-p', '/sdcard/screen.png'])
        # 拉取到本地
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'pull', '/sdcard/screen.png', local_path])
        logging.info(f"截图:{local_path}")
        # 返回图片路径
        return local_path
    @staticmethod
    def get_ui_hierarchy():
        """
        获取设备的UI层次结构 (window_dump)。
        :return: UI层次结构的XML内容字符串，失败则返回None。
        """
        # 确保临时目录存在
        if not os.path.exists(BASE_SCREENSHOT_PATH):
            os.makedirs(BASE_SCREENSHOT_PATH)
            
        local_xml_path = f'{BASE_SCREENSHOT_PATH}/ui_dump_{uuid.uuid4()}.xml'
        device_xml_path = '/sdcard/window_dump.xml'

        try:
            # 1. 在设备上dump UI树
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'uiautomator', 'dump', device_xml_path], check=True, capture_output=True)
            # 2. 从设备拉取XML文件
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'pull', device_xml_path, local_xml_path], check=True, capture_output=True)
            
            logging.info(f"UI树文件成功保存至: {local_xml_path}")
            
            # 3. 读取XML文件内容
            with open(local_xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # 4. (可选) 清理本地的临时XML文件
            os.remove(local_xml_path)
            
            return xml_content
            
        except subprocess.CalledProcessError as e:
            logging.error(f"ADB获取UI树操作失败: {e.stderr.decode()}")
            return None
        except FileNotFoundError:
            logging.error(f"未找到拉取下来的UI树文件: {local_xml_path}")
            return None
        except Exception as e:
            logging.error(f"读取或处理UI树文件时发生未知错误: {e}")
            return None

    @staticmethod
    def get_foreground_package():
        """
        获取当前前台（焦点/可见）应用包名，采用多策略回退。
        返回: 包名字符串，无法获取时返回 'unknown'
        """
        strategies = [
            # 优先从 window 当前焦点窗口解析
            [ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'dumpsys', 'window', 'windows'],
            # 从 Activity 栈中找 top resumed
            [ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'dumpsys', 'activity', 'activities'],
            # 从 top（兼容部分系统）
            [ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'dumpsys', 'activity', 'top'],
            # Android 11+ 的可见活动
            [ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'cmd', 'activity', 'get-visible-activities'],
        ]
        try:
            # 1) dumpsys window windows
            out = subprocess.run(strategies[0], capture_output=True, text=True).stdout
            m = re.search(r'mCurrentFocus=Window\{[^ ]+\s+([^/}\s]+)', out)
            if m:
                return m.group(1)

            # 2) dumpsys activity activities
            out = subprocess.run(strategies[1], capture_output=True, text=True).stdout
            m = re.search(r'topResumedActivity.*\s+([^/\s]+)/', out)
            if m:
                return m.group(1)

            # 3) dumpsys activity top
            out = subprocess.run(strategies[2], capture_output=True, text=True).stdout
            m = re.search(r'ACTIVITY\s+([^/\s]+)/', out)
            if m:
                return m.group(1)

            # 4) get-visible-activities
            out = subprocess.run(strategies[3], capture_output=True, text=True).stdout.strip()
            if out:
                # 可能是形如 "com.xxx/.MainActivity" 或多行，取第一段包名
                first_line = out.splitlines()[0]
                return first_line.split('/')[0]
        except Exception as e:
            logging.error(f"获取前台包名失败: {e}")

        return "unknown"

    @staticmethod
    def capture_all(remove_local_tmp_xml=True):
        """
        一次性获取：截图(base64)、UI树(XML字符串)、前台包名。
        返回:
            {
                'screenshot_base64': 'data:image/png;base64,...',
                'ui_xml': '<hierarchy ...>...</hierarchy>',
                'package': 'com.xxx.yyy'
            }
        失败时对应字段可能为 None/unknown，但不抛异常。
        """
        # 目录准备
        os.makedirs(BASE_SCREENSHOT_PATH, exist_ok=True)

        # 临时路径
        local_png = os.path.join(BASE_SCREENSHOT_PATH, f'screen_{uuid.uuid4()}.png')
        device_png = '/sdcard/screen.png'
        local_xml = os.path.join(BASE_SCREENSHOT_PATH, f'ui_dump_{uuid.uuid4()}.xml')
        device_xml = '/sdcard/window_dump.xml'

        screenshot_b64 = None
        ui_xml_str = None

        # A) 截图
        try:
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'screencap', '-p', device_png],
                           check=True, capture_output=True)
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'pull', device_png, local_png],
                           check=True, capture_output=True)
            # 读取并编码
            with open(local_png, 'rb') as f:
                screenshot_b64 = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
            logging.info(f"截图完成: {local_png}")
        except subprocess.CalledProcessError as e:
            logging.error(f"截图失败: {e.stderr.decode() if e.stderr else e}")
        except Exception as e:
            logging.error(f"处理截图失败: {e}")
        finally:
            # 设备侧清理
            try:
                subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'rm', '-f', device_png],
                               capture_output=True)
            except Exception:
                pass
            # 本地可按需保留
            # 可选：os.remove(local_png)

        # B) UI 树
        try:
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'uiautomator', 'dump', device_xml],
                           check=True, capture_output=True)
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'pull', device_xml, local_xml],
                           check=True, capture_output=True)
            with open(local_xml, 'r', encoding='utf-8') as f:
                ui_xml_str = f.read()
            logging.info(f"UI树完成: {len(ui_xml_str)} chars")
        except subprocess.CalledProcessError as e:
            logging.error(f"UI树dump失败: {e.stderr.decode() if e.stderr else e}")
        except Exception as e:
            logging.error(f"读取UI树失败: {e}")
        finally:
            # 设备侧清理
            try:
                subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'rm', '-f', device_xml],
                               capture_output=True)
            except Exception:
                pass
            # 本地临时 XML 可选清理
            if remove_local_tmp_xml:
                try:
                    os.remove(local_xml)
                except Exception:
                    pass

        # C) 前台包名
        pkg = ADBController.get_foreground_package()

        return {
            'screenshot_base64': screenshot_b64,
            'ui_xml': ui_xml_str,
            'package': pkg
        }
    @staticmethod
    def execute_command(command):
        # 执行ADB命令
        result = subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', command], capture_output=True)
        return result.stdout.decode()

    @staticmethod
    def restart_app():
        """重启指定应用：先关闭再启动"""
        global app_name
        if not app_name:
            logging.warning("未设置应用包名(app_name)")
            return
        logging.info(f"重启应用：{app_name}")
        # 先关闭应用
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'am', 'force-stop', app_name])
        # 启动应用
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'monkey', '-p', app_name, '-c', 'android.intent.category.LAUNCHER', '1'])
        logging.info(f"{app_name} 已重启")
        return None
    @staticmethod
    def open_app(package_name):
        """
        启动特定app (使用更健壮的 am start 命令)。
        该方法首先尝试动态解析应用的主Activity，然后使用 `am start` 启动。
        如果解析失败，会回退到使用 monkey 命令。
        """
        logging.info(f"尝试启动应用包: {package_name}")
        try:
            # 步骤1: 动态解析应用的主启动Activity
            # 这个命令会返回 "package_name/full.activity.name"
            # 使用 `cmd package` 兼容性更好
            cmd_resolve = [
                ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell',
                'cmd', 'package', 'resolve-activity', '--brief', package_name
            ]
            result = subprocess.run(cmd_resolve, capture_output=True, text=True, check=True, timeout=5)
            
            # 取输出的最后一行，以防有警告信息
            component_name = result.stdout.strip().splitlines()[-1]

            if not component_name or '/' not in component_name:
                # 如果解析失败，回退到原来的 monkey 命令
                logging.warning(f"无法为 {package_name} 解析到主Activity。尝试使用 monkey 命令作为备用方案。")
                cmd_fallback = [
                    ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 
                    'monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'
                ]
                subprocess.run(cmd_fallback, check=True, timeout=5)
            else:
                # 步骤2: 使用 am start -n 精确启动解析到的组件
                logging.info(f"解析到组件: {component_name}，正在启动...")
                cmd_start = [
                    ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 
                    'am', 'start', '-n', component_name
                ]
                subprocess.run(cmd_start, check=True, timeout=5)
            
            logging.info(f"启动命令已成功发送给包: {package_name}")

        except subprocess.CalledProcessError as e:
            # 捕获命令执行失败的错误
            error_message = e.stderr.strip() if e.stderr else e.stdout.strip()
            logging.error(f"启动应用 {package_name} 失败: {error_message}")
        except subprocess.TimeoutExpired:
            logging.error(f"启动应用 {package_name} 超时。")
        except Exception as e:
            logging.error(f"启动应用时发生未知错误: {e}")

    # 新增操作方法
    @staticmethod
    def tap(x, y):
        """点击屏幕坐标 (x, y)"""
        command = f'input tap {x} {y}'
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', command])

    @staticmethod
    def long_press(x, y, duration=1000):
        """长按屏幕坐标 (x, y)，持续时间毫秒"""
        # 使用 input swipe 模拟长按，起点和终点相同，持续时间即为长按时间
        command = f'input swipe {x} {y} {x} {y} {duration}'
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', command])

    @staticmethod
    def swipe(x1, y1, x2, y2, duration=300):
        """滑动从 (x1, y1) 到 (x2, y2)，持续时间毫秒"""
        command = f'input swipe {x1} {y1} {x2} {y2} {duration}'
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', command])

    @staticmethod
    def input_text(text):
        """输入文字"""
        # 使用ADB keyboard输入
        command = f"am broadcast -a ADB_INPUT_TEXT --es msg '{text}'"
        # 安装输入法：https://android.bihe0832.com/doc/summary/samples.html
        # command = f"am broadcast -a ZIXIE_ADB_INPUT_TEXT --es msg '{text}'"
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', command])
    # @staticmethod
    # def input_text(text):
    #     """
    #     使用 "紫雪ADB输入法" (ZIXIE_ADB_INPUT) 通过 Base64 广播方式输入文本。
    #     这种方法能够可靠地处理中文、特殊符号和 Emoji。
        
    #     :param text: 要输入的任意文本。
    #     """
    #     logging.info(f"准备通过紫雪ADB输入法输入文本: '{text}'")

    #     if not text:
    #         logging.warning("尝试输入空文本，操作已跳过。")
    #         return

    #     try:
    #         # 1. 将原始文本字符串编码为 UTF-8 字节序列
    #         text_bytes = text.encode('utf-8')
            
    #         # 2. 对 UTF-8 字节序列进行 Base64 编码，得到 Base64 字节序列
    #         base64_bytes = base64.b64encode(text_bytes)
            
    #         # 3. 将 Base64 字节序列解码为 ASCII 字符串，以便在命令行中使用
    #         base64_string = base64_bytes.decode('ascii')

    #         # 4. 构建 adb broadcast 命令
    #         #    am broadcast -a ZIXIE_ADB_INPUT_BASE64 --es msg <base64_string>
    #         #    我们不需要像shell脚本那样手动处理转义，因为base64字符串是安全的。
    #         command = [
    #             ADB_PATH,
    #             '-s', CLOUD_DEVICE_IP_PORT,
    #             'shell',
    #             'am', 'broadcast',
    #             '-a', 'ZIXIE_ADB_INPUT_BASE64',
    #             '--es', 'msg', base64_string
    #         ]

    #         # 5. 执行命令
    #         result = subprocess.run(
    #             command,
    #             capture_output=True,
    #             check=True,  # 如果命令返回非0退出码，将抛出 CalledProcessError
    #             timeout=10   # 设置一个10秒的超时
    #         )
            
    #         # 广播命令成功时，通常会输出类似 "Broadcast completed: result=0" 的信息
    #         # 我们可以检查 stderr 是否为空，或者 stdout 中是否包含成功信息
    #         # 在大多数情况下，check=True 已经足够保证命令被 adb 成功派发
    #         logging.info(f"成功发送广播以输入文本。ADB输出: {result.stdout.decode('utf-8', errors='ignore').strip()}")

    #     except subprocess.CalledProcessError as e:
    #         # 命令执行失败
    #         error_output = e.stderr.decode('utf-8', errors='ignore').strip()
    #         logging.error(f"使用紫雪ADB输入法失败，命令返回错误: {error_output}")
    #         logging.error("请确认：1. 设备已安装并切换到紫雪ADB输入法。2. ADB连接正常。")
    #     except subprocess.TimeoutExpired:
    #         # 命令超时
    #         logging.error("使用紫雪ADB输入法超时。设备可能无响应或输入法服务卡住。")
    #     except Exception as e:
    #         # 其他未知错误，如编码失败等
    #         logging.error(f"使用紫雪ADB输入法时发生未知错误: {e}")

    @staticmethod
    def clear_text():
        """清除文本内容，模拟长按删除或多次Backspace，也可以用命令"""
        # 这里用模拟多次Backspace
        # 或者直接使用 input keyevent
        for _ in range(20):  # 假设要清除50次
            subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'input', 'keyevent', '67'])  # KEYCODE_DEL

    
    @staticmethod
    def press_back():
        """模拟返回键"""
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'input', 'keyevent', '4'])

    @staticmethod
    def press_home():
        """回到home"""
        subprocess.run([ADB_PATH, '-s', CLOUD_DEVICE_IP_PORT, 'shell', 'input', 'keyevent', '3'])
# 解析模型输出
def parse_action(text):
    # 去除前后空白字符（包括换行、空格等）
    text = text.strip()
    # 去除Action:
    match = re.search(r'Action:\s*(.*)', text)
    if match:
        operation = match.group(1)
        text=operation
        # 多个匹配的正则表达式
        patterns = {
            'tap': r'tap\(\s*(\d+),\s*(\d+)\s*\)',
            'text': r'text\(\s*"([^"]*)"\s*\)',
            'need_feedback': r'need_feedback\(\s*"([^"]*)"\s*\)',
            'long_press': r'long_press\(\s*(\d+),\s*(\d+)\s*\)',
            'swipe': r'swipe\(\s*(\d+),\s*(\d+),\s*"([^"]+)",\s*"([^"]+)"\s*\)',
            'swipe_two_points': r'swipe_two_points\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            'wait': r'wait\(\s*\)',
            'FINISH': r'FINISH'
        }
        
        for action_type, pattern in patterns.items():
            match = re.match(pattern, text)
            if match:
                # 根据不同的action类型，返回不同的参数结构
                if action_type == 'tap':
                    x, y = match.groups()
                    return {'action': 'tap', 'x': int(x), 'y': int(y)}
                elif action_type == 'text':
                    content = match.group(1)
                    return {'action': 'text', 'value': content}
                elif action_type == 'long_press':
                    x, y = match.groups()
                    return {'action': 'long_press', 'x': int(x), 'y': int(y)}
                elif action_type == 'swipe':
                    x, y, direction, dist = match.groups()
                    return {
                        'action': 'swipe', 
                        'x': int(x), 
                        'y': int(y), 
                        'direction': direction, 
                        'distance': dist
                    }
                elif action_type == 'swipe_two_points':
                    x_start,y_start,x_end,y_end=match.groups()
                    return {
                        'action': 'swipe_two_points',
                        'x_start': int(x_start),
                        'y_start': int(y_start),
                        'x_end': int(x_end),
                        'y_end': int(y_end)
                    }
                elif action_type == 'wait':
                    return {'action': 'wait'}
                elif action_type == 'need_feedback':
                    content = match.group(1)
                    return {'action': 'need_feedback', 'value': content}
                elif action_type == 'FINISH':
                    return {'action': 'FINISH'}
        return None  # 如果没有匹配到
    return None
def format_action(action_data):
    """
    将 parse_action 生成的字典对象转换回 "Action: ..." 格式的字符串。
    
    :param action_dict: 一个包含 action 信息的字典，例如 {'action': 'tap', 'x': 100, 'y': 200}
    :return: 格式化后的字符串，例如 "Action: tap(100, 200)"，如果输入无效则返回 None
    """
    if not isinstance(action_data, dict) or 'action' not in action_data:
        return None  # 如果输入不是字典或没有 'action' 键，则返回 None

    action_type = action_data.get('action')
    operation_str = ""

    if action_type == 'tap':
        operation_str = f"tap({action_data['x']}, {action_data['y']})"

    
    elif action_type == 'text':
        # 注意：为了和原始格式匹配，字符串值需要用双引号包裹
        operation_str = f'text("{action_data["value"]}")'
    
    elif action_type == 'need_feedback':
        operation_str = f'need_feedback("{action_data["value"]}")'
    
    elif action_type == 'long_press':
        operation_str = f"long_press({action_data['x']}, {action_data['y']})"

    elif action_type == 'swipe':
        # 注意：direction 和 distance 也需要用双引号包裹
        operation_str = (
            f'swipe({action_data["x"]}, {action_data["y"]}, '
            f'"{action_data["direction"]}", "{action_data["distance"]}")'
        )
    elif action_type == 'swipe_two_points':
        operation_str = f"swipe_two_points({action_data['x']},{action_data['y']},{action_data['x_end']},{action_data['y_end']})"

    elif action_type == 'wait':
        operation_str = "wait()"
        
    elif action_type == 'FINISH':
        operation_str = "FINISH"
        
    else:
        # 如果 action 类型未知，返回 None
        return None
    print(operation_str)
    return f"Action: {operation_str}"

# 标注数据存储
class AnnotationStore:
    def __init__(self):
        self.data_file = 'annotations.json'

    def save(self, data):
        with open(self.data_file, 'a') as f:
            f.write(json.dumps(data) + '\n')
@app.route('/get-screenshot',methods=['GET'])
def get_screenshot():
    # 获取屏幕截图
    # 本地图片路径
    # image_path = 'screenshots/test.png'
    image_path=ADBController.get_screenshot()
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    # 转成 base64
    encoded_string = base64.b64encode(image_bytes).decode('utf-8')
    return jsonify({
        'status': 'success',
        'message': 'Screenshot retrieved successfully',
        'data': f'data:image/png;base64,{encoded_string}'
    })
@app.route('/get-ally',methods=['GET'])
def get_ally():
    # 获取ally树
    ui_xml=ADBController.get_ui_hierarchy()
    print(ui_xml)
    return jsonify({
        'status': 'success',
        'message': 'Screenshot retrieved successfully',
        'data': f'{ui_xml}'
    })
@app.route('/get-all', methods=['GET'])
def capture_all():
    """
    一次返回：截图(Base64)、UI XML树、前台包名
    """
    data = ADBController.capture_all()
    status = 'success' if any([data.get('screenshot_base64'), data.get('ui_xml')]) else 'failed'
    msg = 'ok' if status == 'success' else 'capture failed'
    return jsonify({
        'status': status,
        'message': msg,
        'data': data
    })
@app.route('/restart-app',methods=['POST'])
def restart_app():
    # 重启app
    ADBController.restart_app()
    return jsonify({'status':'success','data':None,'message':"重启成功"})
# 根据任务类型填充不同的模版
def fill_templete_by_task(task_type,app_name,slot_info):
    return get_task_prompt(
        task_type=task_type,
        app_name=app_name,
        **slot_info
    )
    # if(slot_info.get('task_type','')=='shopping'):
    #     # return SHOPPING_QUESTION_PROMPT.format(
    #     #     task_type='shopping',
    #     #     app_name=slot_info.get('app_name',''),
    #     #     item_name=slot_info.get('item_name',''),
    #     #     store_name=slot_info.get('store_name',''),
    #     #     specs=slot_info.get('specs',''),
    #     #     quantity=slot_info.get('quantity',1)
    #     # )
    #     return get_task_prompt(
    #         task_type='shopping',
    #         app_name=slot_info.get('app_name'),
    #         item_name=slot_info.get('item_name',''),
    #         store_name=slot_info.get('store_name',''),
    #         specs=slot_info.get('specs',''),
    #         quantity=slot_info.get('quantity',1)
    #     )
    # return ''
# 填充
# 构建请求体
def build_payload(image_base64, query):
    return {
        "model": "qwen2.5-vl-meituan", # 模型名称需与你部署的保持一致
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_base64}},
                    {"type": "text", "text": query}
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.7
    }
@app.route('/infer',methods=['POST'])
def infer():
    # 推理
    # 传参:image_base64,base_64编码的png图片内容;slot_info:任务相关内容,根据任务的不同参数不同,具体参考prompt_templates.py中的模版
    # 1. 获取前端传来的 Base64 图片和其他参数
    data = request.get_json()
    base64_str = data['image_base64']  # 格式如 "data:image/png;base64,xxxxx"
    task_type=data.get('task_type','')
    app_name=data.get('app_name','')
    slot_info=data.get('slot_info',{})
    print(slot_info)
    # 2. 填充query
    query=fill_templete_by_task(task_type=task_type,app_name=app_name,slot_info=slot_info)
    logging.info(query)
    # 3. 构建prompt
    payload=build_payload(base64_str,query=query)
    # 4. 请求模型
    # 发送请求
    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()  # 抛出HTTP错误
    
    # 解析结果
    result = response.json()
    content = result['choices'][0]['message']['content']
    logging.debug(f"✅  响应内容:\n{content}")
    content=parse_action(content)
    return jsonify({
        'status':'success',
        'data':content,
        'message':'模型成功响应'
    })
def append_to_json_file(data_to_append, filename):
    """
    向一个JSON文件追加一个JSON对象（字典）。
    文件内容被维护为一个JSON数组。

    :param data_to_append: 要追加的Python字典。
    :param filename: JSON文件的路径。
    """
    
    # 步骤1: 检查文件是否存在且不为空
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            # 文件存在，读取现有数据
            with open(filename, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
            
            # 确保读取的数据是列表
            if not isinstance(data_list, list):
                print(f"错误: 文件 '{filename}' 的内容不是一个JSON数组。正在覆盖为新数组。")
                data_list = []
        
        except json.JSONDecodeError:
            # 文件内容不是有效的JSON，可能已损坏或为空
            print(f"警告: 无法解析 '{filename}'。将创建一个新的文件。")
            data_list = []
    else:
        # 文件不存在或为空，初始化一个空列表
        data_list = []

    # 步骤2: 将新数据追加到列表中
    data_list.append(data_to_append)

    # 步骤3: 将更新后的列表写回文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # json.dump() 写入文件
            # indent=4 让JSON格式化，更易读
            # ensure_ascii=False 确保中文字符能正确显示
            json.dump(data_list, f, indent=4, ensure_ascii=False)
        print(f"数据成功追加到 {filename}")
    except IOError as e:
        print(f"错误: 无法写入文件 {filename}。{e}")

@app.route('/infer_multi_agents', methods=['POST'])
def infer_multi_agents():
    # 推理
    # 传参:image_base64,base_64编码的png图片内容;goal: 用户指令的字符串
    # 1. 获取前端传来的 Base64 图片和其他参数
    data = request.get_json()
    base64_str = data['image_base64']  # 格式如 "data:image/png;base64,xxxxx"
    task_type=data.get('task_type','')
    app_name=data.get('app_name','')
    slot_info=data.get('slot_info',{})
    goal=fill_templete_by_task(task_type=task_type,app_name=app_name,slot_info=slot_info)
    print(goal)
    app_automator = MultiAgentSystem()
    content=app_automator.run(goal,base64_str)
    print(f"✅  响应内容:\n{content}")
    logging.debug(f"✅  响应内容:\n{content}")
    content=parse_action(content)
    print(content)
    return jsonify({
        'status':'success',
        'data':content,
        'message':'模型成功响应'
    })

def save_base64_to_png(base64_string, output_dir, filename=None):
    """
    解码Base64字符串并将其保存为PNG图片文件。

    :param base64_string: Base64编码的字符串 (可以带 'data:image/png;base64,' 前缀)。
    :param output_dir: 图片要保存的目录。
    :param filename: (可选) 保存的文件名。如果未提供，将生成一个唯一的UUID文件名。
    :return: 成功时返回完整的文件路径，失败时返回None。
    # 这是一个 1x1 像素的透明PNG的Base64编码，非常适合用于测试
    # 格式1: 带 "Data URL" 前缀
    sample_base64_with_prefix = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    # 格式2: 不带前缀的纯Base64字符串
    sample_base64_pure = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    # 指定输出目录
    output_directory = "saved_images"

    print("--- 测试1: 带前缀的Base64，自动生成文件名 ---")
    save_base64_to_png(sample_base64_with_prefix, output_directory)

    print("\n--- 测试2: 不带前缀的Base64，指定文件名 ---")
    save_base64_to_png(sample_base64_pure, output_directory, filename="my_first_image.png")

    print("\n--- 测试3: 错误格式的Base64 ---")
    invalid_base64 = "this_is_not_base64"
    save_base64_to_png(invalid_base64, output_directory)
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 使用正则表达式去除 "data:image/png;base64," 前缀
    #    这使得函数对于两种格式的输入都能正常工作
    try:
        # re.sub finds the pattern and replaces it with an empty string
        pure_base64_str = re.sub(r'^data:image/.+;base64,', '', base64_string)
        
        # 2. 解码Base64字符串
        image_data = base64.b64decode(pure_base64_str)
    except (ValueError, base64.binascii.Error) as e:
        print(f"错误: Base64 解码失败 - {e}")
        return None

    # 3. 确定文件名
    if filename:
        # 如果提供了文件名，确保它是安全的
        if not filename.lower().endswith('.png'):
            filename += '.png'
    else:
        # 如果未提供文件名，生成一个唯一的UUID文件名
        filename = f"{uuid.uuid4()}.png"
        
    # 构造完整的文件路径
    file_path = os.path.join(output_dir, filename)

    # 4. 以二进制写入模式保存文件
    try:
        with open(file_path, 'wb') as f:
            f.write(image_data)
        print(f"图片成功保存到: {file_path}")
        return file_path
    except IOError as e:
        print(f"错误: 文件写入失败 - {e}")
        return None
# slot_info: 任务信息
# action_info: 动作信息
# user_id: 用户id----不同的用户分开保存;后期还可以进行统计
# image_base64: 64位格式的图片信息
@app.route('/save-annotation', methods=['POST'])
def save_annotation():
    """
        保存标注信息
    """
    data = request.get_json()
    slot_info=data['slot_info']
    action_info=data['action_info']
    app_name=data.get('app_name','')
    task_type=data.get('task_type','')
    user_id=data.get('user_id','default')# 如果未填,则保存到default文件中
    image_base64=data['image_base64']
    
    query=fill_templete_by_task(slot_info=slot_info,app_name=app_name,task_type=task_type)
    action=format_action(action_data=action_info)
    image_name=f"{uuid.uuid4()}.png"
    prompt =   {
        "messages": [
        {
            "role": "user",
            "content": f"""{query}"""
        },
        {
            "role": "assistant",
            "content": f"""{action}"""
        }
        ],
        "images": [
            f"imgs_all/{image_name}"
        ]
    }
    # 保存图片到指定路径
    save_base64_to_png(image_base64,IMGS_PATH,image_name)
    # 保存数据到指定路径
    append_to_json_file(prompt,os.path.join(BASE_ANNO_PATH,f'{user_id}.json'))
    return jsonify({'status': 'success','data':None,'message':'成功保存标注并执行'})
# user_id: 用户id----不同的用户分开保存;后期还可以进行统计
# data: 用户标注的数据
#   step_index
#   screenshot_64
@app.route('/save-annotation-new', methods=['POST'])
def save_annotation_new():
    data = request.get_json()
    user_id=data.get('user_id','default')# 如果未填,则保存到default文件中
    step_list=data.get('step_list')
    cleaned_steps = []
    for idx, step in enumerate(step_list):
        if not isinstance(step, dict):
            print(f"step[{idx}] is not an object")
            continue
        image_name=f"{uuid.uuid4()}.png"
        image_base64=step.get('screenshot_64')
        # 保存图片到指定路径
        save_base64_to_png(image_base64,IMGS_PATH,image_name)
        image_xml=step.get('screenshot_xml')

        cleaned = {
            "step_index": step.get('step_index'),
            "actionForm": step.get("actionForm", {}),
            "application": step.get("application", ""),
            "application_name_cn": step.get("application_name_cn", ""),
            "application_name_en": step.get("application_name_en", ""),
            "extra_info": step.get("extra_info", {}),
            # 新增字段：图片相对路径（如果保存成功）
            "image_name": image_name ,
            "image_xml":image_xml
        }
        cleaned_steps.append(cleaned)
    instruction=data.get('instruction')
    anno={
        "task_id": f"{uuid.uuid4()}",
        "instruction":instruction,
        "applications":[],
        "steps": cleaned_steps
    }
    # 保存数据到指定路径
    append_to_json_file(anno,os.path.join(BASE_ANNO_PATH,f'{user_id}.json'))
    return jsonify({'status': 'success','data':None,'message':'成功保存标注并执行'})


@app.route('/execute-action', methods=['POST'])
def execute_action():
    action_info = request.json['action_info']
    # 示例：执行adb点击操作
    if action_info['action']=='tap':
        ADBController.tap(action_info['x'],action_info['y'])
    elif action_info['action']=='long_press':
        ADBController.long_press(action_info['x'],action_info['y'],2000)
    elif action_info['action']=='swipe':
        x=action_info['x']
        y=action_info['y']
        base_dist = 200
        x_end=x
        y_end=y
        direction=action_info['direction']
        dist = action_info['distance']
        rate = 3 if dist=='long' else 2 if dist=='medium' else 1
        if direction == 'up':
            x_end = x
            y_end = y-base_dist*rate
        elif direction == 'down':
            x_end = x
            y_end = y+base_dist*rate
        elif direction == 'left':
            x_end = x-base_dist*rate
            y_end = y
        elif direction == 'right':
            x_end = x+base_dist*rate
            y_end = y
        ADBController.swipe(x,y,x_end,y_end)
    elif action_info['action'] == 'swipe_two_points':
        ADBController.swipe(action_info['x'],action_info['y'],action_info['x_end'],action_info['y_end'])
    elif action_info['action']=='text':
        ADBController.clear_text()
        ADBController.input_text(action_info['value'])
    elif action_info['action']=='open_app':
        package_name=action_info['package_name']
        logging.info(f"包-{package_name} 启动")
        ADBController.open_app(package_name)
    return jsonify({'status': 'success','data':None,'message':'执行成功'})

@app.route('/test_get',methods=['GET'])
def hello_world():
    return 'Hello, World!'
@app.route('/test_post', methods=['POST'])
def test_post():
    return jsonify({
        'test':'Hello, World!'
    })


# --- 新增：通用 OpenAI API 调用函数 ---
def call_openai_api( messages):
    """
    一个独立的、通用的函数，用于调用 OpenAI Chat Completions API。

    Args:
        messages (dict): 符合 OpenAI API 规范的请求体字典。

    Returns:
        tuple: 一个包含两个元素的元组 (is_success, result)。
               - 如果成功, (True, response_dict)。
               - 如果失败, (False, error_message_string)。
    """
    payload={
        "model":MODEL_NAME,
        "messages":messages,
        "max_tokens":1000
    }
    
    try:
        logging.info(f"向 OpenAI 发送请求, 模型: {payload.get('model')}")
        
        # 使用 ** 将字典解包为关键字参数，直接传递给 `create` 方法
        response = openai_client.chat.completions.create(**payload)
        
        # 将 OpenAI 的 Pydantic 模型对象转换为字典
        response_dict = response.choices[0].message.content
        
        logging.info("OpenAI API 调用成功。")
        logging.debug(f"OpenAI 响应: {response_dict}")
        
        return True, response_dict

    except Exception as e:
        # 捕获所有可能的异常 (API认证失败, 网络问题, 无效请求等)
        error_message = str(e)
        logging.error(f"OpenAI API 调用失败: {error_message}")
        return False, error_message

@app.route('/openai_infer', methods=['POST'])
def openai_infer():
    """
    处理 /openai_infer POST 请求的 Flask 路由。
    它作为 web 接口，调用核心的 `call_openai_api` 函数。
    """
    # 1. 检查服务器端配置
    if not openai_client:
        return jsonify({
            'status': 'error',
            'message': 'OpenAI client is not configured on the server. Please check OPENAI_API_KEY in config.py.'
        }), 500
    prompt('testttt')
    # 2. 检查客户端请求
    prompt=[
        {
            'role':'system',
            'content': ""
        },
        {
            "role": "user",
            "content": [
                {
                "type": "image_url",
                "image_url": {
                # 需要注意：传入Base64编码前需要增加前缀 data:image/{图片格式};base64,{Base64编码}：
                # PNG图片："url":  f"data:image/png;base64,{base64_image}"
                # JPEG图片："url":  f"data:image/jpeg;base64,{base64_image}"
                # WEBP图片："url":  f"data:image/webp;base64,{base64_image}"
                    "url":  "{screenshot_base64}"
                },         
                },
                {
                "type": "text",
                "text": "Analyze the UI elements in the figure",
                },
            ],
        }
    ]
    prompt_json = request.json['prompt_json']
    if not prompt_json:
        return jsonify({'status': 'error', 'message': 'Invalid or empty JSON payload.'}), 400

    # 3. 调用核心逻辑函数
    is_success, result = call_openai_api(messages=prompt_json)
    logging.info(f"生成任务---{is_success}---{result}")
    # 4. 根据结果构造响应
    if is_success:
        return jsonify({
            'status': 'success',
            'data': result,  # result 在这里是 response_dict
            'message': 'OpenAI API call successful.'
        })
    else:
        # result 在这里是 error_message_string
        return jsonify({
            'status': 'error',
            'message': f"An error occurred with the OpenAI API: {result}"
        }), 500


if __name__ == '__main__':
    # 从配置中获取主机和端口
    host = app.config['FLASK_HOST']
    port = app.config['FLASK_PORT']
    
    # 确保主截图目录存在（原始代码中的逻辑）
    os.makedirs('screenshots', exist_ok=True)
    
    logging.info(f"Flask 应用启动，监听地址 http://{host}:{port}")
    app.run(host=host, port=port)
