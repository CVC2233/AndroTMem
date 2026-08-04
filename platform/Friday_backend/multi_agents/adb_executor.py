# adb_controller.py
import subprocess
import os
import re
import logging
import uuid

# --- 配置 ---
# 这些配置将由这个模块管理
ADB_PATH = "adb"
CLOUD_DEVICE_IP_PORT = '4af63a6b'
BASE_SCREENSHOT_PATH = './screenshots_tmp_new'
DEFAULT_APP_NAME = 'com.sankuai.meituan.takeoutnew'

# --- 日志配置 ---
# 保证在被导入时也能正常工作
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [ADB_Controller] - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # 默认输出到控制台
)

class _ADBControllerInternal:
    """
    一个内部类，封装所有原生的ADB命令。
    不建议在模块外部直接使用。
    """
    def __init__(self, device_id, adb_path):
        self.device_id = device_id
        self.adb_path = adb_path

    def _run_adb_command(self, *args):
        """执行ADB命令的通用方法"""
        command = [self.adb_path, '-s', self.device_id] + list(args)
        logging.info(f"Executing: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
        if result.returncode != 0:
            logging.error(f"Error executing command: {' '.join(command)}")
            logging.error(f"Stderr: {result.stderr.strip()}")
        return result

    def get_screenshot(self):
        """截屏并保存到本地，返回本地路径"""
        os.makedirs(BASE_SCREENSHOT_PATH, exist_ok=True)
        local_path = os.path.join(BASE_SCREENSHOT_PATH, f'screen_{uuid.uuid4()}.png')
        device_path = '/sdcard/screen.png'

        self._run_adb_command('shell', 'screencap', '-p', device_path)
        result = self._run_adb_command('pull', device_path, local_path)
        
        if result.returncode == 0 and os.path.exists(local_path):
            logging.info(f"Screenshot saved to: {local_path}")
            return local_path
        else:
            logging.error("Failed to get screenshot.")
            return None

    def restart_app(self, app_name):
        logging.info(f"Restarting app: {app_name}")
        self._run_adb_command('shell', 'am', 'force-stop', app_name)
        self._run_adb_command('shell', 'monkey', '-p', app_name, '-c', 'android.intent.category.LAUNCHER', '1')
        logging.info(f"{app_name} has been restarted.")
        return True

    def tap(self, x, y):
        self._run_adb_command('shell', 'input', 'tap', str(x), str(y))
        return True

    def long_press(self, x, y, duration=1000):
        self._run_adb_command('shell', 'input', 'swipe', str(x), str(y), str(x), str(y), str(duration))
        return True

    def swipe(self, x1, y1, x2, y2, duration=300):
        self._run_adb_command('shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration))
        return True

    def input_text(self, text):
        self._run_adb_command('shell', "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", f"'{text}'")
        return True

    def clear_text(self):
        # 模拟多次删除
        for _ in range(50):
            self._run_adb_command('shell', 'input', 'keyevent', '67') # KEYCODE_DEL
        return True

    def press_back(self):
        self._run_adb_command('shell', 'input', 'keyevent', '4')
        return True

    def press_home(self):
        self._run_adb_command('shell', 'input', 'keyevent', '3')
        return True

def _parse_action_string(text):
    """
    内部辅助函数：解析动作字符串。
    """
    text = text.strip()
    patterns = {
        'tap': r'tap\(\s*(\d+),\s*(\d+)\s*\)',
        'text': r'text\(\s*"([^"]*)"\s*\)',
        'long_press': r'long_press\(\s*(\d+),\s*(\d+)\s*\)',
        'swipe': r'swipe\(\s*(\d+),\s*(\d+),\s*"([^"]+)",\s*"([^"]+)"\s*\)',
        'swipe_two_points': r'swipe_two_points\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
        'screenshot': r'screenshot\(\s*\)',
        'restart_app': r'restart_app\(\s*\)',
        'back': r'back\(\s*\)',
        'home': r'home\(\s*\)',
        'clear': r'clear\(\s*\)',
    }
    for action_type, pattern in patterns.items():
        match = re.fullmatch(pattern, text)
        if match:
            if action_type == 'tap': return {'action': 'tap', 'x': int(match.group(1)), 'y': int(match.group(2))}
            if action_type == 'text': return {'action': 'text', 'value': match.group(1)}
            if action_type == 'long_press': return {'action': 'long_press', 'x': int(match.group(1)), 'y': int(match.group(2))}
            if action_type == 'swipe': return {'action': 'swipe', 'x': int(match.group(1)), 'y': int(match.group(2)), 'direction': match.group(3), 'distance': match.group(4)}
            if action_type == 'swipe_two_points': return {'action': 'swipe_two_points', 'x_start': int(match.group(1)), 'y_start': int(match.group(2)), 'x_end': int(match.group(3)), 'y_end': int(match.group(4))}
            if action_type in ['screenshot', 'restart_app', 'back', 'home', 'clear']: return {'action': action_type}
    
    logging.error(f"Could not parse action string: {text}")
    return None

# --- 公共接口函数 ---
def execute_action(action_string: str):
    """
    解析并执行一个ADB动作字符串。这是模块的主要入口点。

    :param action_string: 要执行的动作, e.g., 'tap(100,200)' or 'screenshot()'.
    :return: 对于 screenshot，返回图片路径；对于其他操作，返回 True 表示成功，False 表示失败。
    """
    logging.info(f"Received action string to execute: '{action_string}'")
    action_info = _parse_action_string(action_string)
    
    if not action_info:
        return False

    # 每次调用时都创建一个控制器实例
    controller = _ADBControllerInternal(device_id=CLOUD_DEVICE_IP_PORT, adb_path=ADB_PATH)
    action_type = action_info['action']

    if action_type == 'tap':
        return controller.tap(action_info['x'], action_info['y'])
    elif action_type == 'long_press':
        return controller.long_press(action_info['x'], action_info['y'], duration=2000)
    elif action_type == 'swipe':
        x, y = action_info['x'], action_info['y']
        direction, dist = action_info['direction'], action_info['distance']
        rate = {'short': 1, 'medium': 2, 'long': 3}.get(dist.lower(), 1)
        base_dist = 200 * rate
        x_end, y_end = x, y
        if direction == 'up': y_end = max(0, y - base_dist)
        elif direction == 'down': y_end = y + base_dist
        elif direction == 'left': x_end = max(0, x - base_dist)
        elif direction == 'right': x_end = x + base_dist
        return controller.swipe(x, y, x_end, y_end)
    elif action_type == 'swipe_two_points':
        return controller.swipe(action_info['x_start'], action_info['y_start'], action_info['x_end'], action_info['y_end'])
    elif action_type == 'text':
        controller.clear_text()
        return controller.input_text(action_info['value'])
    elif action_type == 'clear':
        return controller.clear_text()
    elif action_type == 'screenshot':
        return controller.get_screenshot()  # 特殊：返回路径
    elif action_type == 'restart_app':
        return controller.restart_app(DEFAULT_APP_NAME)
    elif action_type == 'back':
        return controller.press_back()
    elif action_type == 'home':
        return controller.press_home()
    else:
        logging.error(f"Unknown action type: {action_type}")
        return False

# 用于直接运行此文件进行测试
if __name__ == '__main__':
    print("--- Testing adb_controller.py ---")
    
    print("\n[Test 1] Executing tap(540, 1500)")
    success = execute_action("tap(540, 1500)")
    print(f"Result: {'Success' if success else 'Failed'}")

    print("\n[Test 2] Executing screenshot()")
    path = execute_action("screenshot()")
    if path:
        print(f"Result: Success, screenshot saved at: {path}")
    else:
        print("Result: Failed")
    
    print("\n[Test 3] Executing an invalid action")
    success = execute_action("fly_to_the_moon()")
    print(f"Result: {'Success' if success else 'Failed'} (Expected Fail)")

    print("\n--- Testing complete ---")

