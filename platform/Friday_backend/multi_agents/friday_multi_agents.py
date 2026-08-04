from dataclasses import dataclass, field
import json
import os
import re
import time
from typing import Any, Dict, List, Tuple
from volcenginesdkarkruntime import Ark
ElementUnderstandingAgentPrompt="""
You are an expert UI analysis agent. Your task is to analyze the provided mobile application screenshot and identify all interactive UI elements.

For each interactive element, you must extract the following information:
1.  `id`: A unique sequential integer, starting from 1.
2.  `type`: The type of the element. Use one of the following categories: 'button', 'input_field', 'text_link', 'checkbox', 'radio_button', 'image_button', 'slider', 'dropdown', 'icon'.
3.  `text`: The text content visible on the element. If there is no text, use an empty string "".
4.  `description`: A brief, clear description of the element's function (e.g., "Login button", "Search input field").
5.  `bbox`: The bounding box coordinates of the element in the format [x_min, y_min, x_max, y_max]. The origin (0,0) is the top-left corner of the image.

Your final output MUST be a single, valid JSON array containing a dictionary for each element. Do not include any other text, explanations, or markdown formatting in your response. Just the raw JSON.
"""
PLANNING_AGENT_SYSTEM_PROMPT = """
You are an expert AI agent designed to operate a mobile application to achieve a user's goal. 

**-- CORE INSTRUCTIONS --**

1.  **Analyze and Reason:** You will be given a user's goal, the current screen's interactive elements. Your first step is always to reason about the situation to determine the best next step. This reasoning should be articulated in your "thought" process.
2.  **Act Decisively:** After reasoning, you must choose a single, precise command to execute from the provided Action Grammar.
3.  **Strict Formatting:** Your entire response MUST be a single, valid JSON object with two keys: "thought" and "action". Do not add any text, notes, or apologies outside of this JSON object.

**-- ACTION GRAMMAR (Available Commands) --**
Your `action` string MUST strictly follow one of the formats below:
- `tap(x, y)`: Taps a specific coordinate on the screen.
- `text("text_to_type")`: Types the given string into a focused input field.
- `long_press(x, y)`: Performs a long press at a coordinate.
- `swipe_two_points(x1, y1, x2, y2)`: Swipes from a start coordinate to an end coordinate.
- `need_feedback("question_for_the_user")`: Use this if you require more information or are stuck.
- `FINISH`: Use this ONLY when the user's high-level goal is fully and successfully completed.
"""
@dataclass
class Action:
    """一个结构化的动作表示"""
    name: str
    params: List[Any] = field(default_factory=list)

class ActionParser:
    """
    负责将模型输出的字符串命令解析为结构化的Action对象。
    """
    def __init__(self):
        # 您提供的正则表达式字典
        self.action_patterns = {
            'tap': r'tap\(\s*(\d+)\s*,\s*(\d+)\s*\)',
            'text': r'text\(\s*"([^"]*)"\s*\)',
            'need_feedback': r'need_feedback\(\s*"([^"]*)"\s*\)',
            'long_press': r'long_press\(\s*(\d+)\s*,\s*(\d+)\s*\)',
            # 示例：swipe(element_id, direction, distance) - 您可以根据需要调整
            'swipe': r'swipe\(\s*(\d+)\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)',
            'swipe_two_points': r'swipe_two_points\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            'wait': r'wait\(\)',
            'FINISH': r'FINISH'
        }

    def parse(self, action_string: str) -> Action:
        """
        解析一个字符串，返回一个Action对象。
        """
        action_string = action_string.strip()

        for name, pattern in self.action_patterns.items():
            match = re.fullmatch(pattern, action_string)
            if match:
                params = list(match.groups())
                cleaned_params = []
                for p in params:
                    # 检查是否为浮点数或整数
                    try:
                        cleaned_params.append(int(p))
                    except ValueError:
                        try:
                            cleaned_params.append(float(p))
                        except ValueError:
                            cleaned_params.append(p)
                
                return Action(name=name, params=cleaned_params)

        print(f"警告: 无法解析动作 '{action_string}'。将请求用户反馈。")
        return Action(name='need_feedback', params=[f"我生成了一个无效的指令 '{action_string}'，我应该怎么做？"])


# ---------------------------------------------------------------------------- #
# 2. 元素理解Agent (无变化)
# ---------------------------------------------------------------------------- #
class ElementUnderstandingAgent:
    def __init__(self):
        print("ElementUnderstandingAgent 已初始化。")
        self.agent=Ark(
        api_key=os.getenv('ARK_API_KEY'),
        )

    def _call_vision_model(self, screenshot_base64: str) -> List[Dict[str, Any]]:
        # print(f"[模型调用] 正在分析截图: {screenshot_base64}...")
        # ==================== 请在这里填充您的模型调用逻辑 ====================
        # 返回值应包含 'id' 和 'bbox' (bounding box) [x1, y1, x2, y2]
        # dummy_elements = [
        #     {'id': 1, 'type': 'input_field', 'text': '', 'description': '用户名输入框', 'bbox': [100, 200, 800, 280]},
        #     {'id': 2, 'type': 'input_field', 'text': '', 'description': '密码输入框', 'bbox': [100, 300, 800, 380]},
        #     {'id': 3, 'type': 'button', 'text': '登录', 'description': '登录按钮', 'bbox': [100, 420, 800, 500]},
        #     {'id': 4, 'type': 'text_link', 'text': '忘记密码?', 'description': '忘记密码链接', 'bbox': [100, 520, 350, 560]}
        # ]
        response = self.agent.chat.completions.create(
            # 替换 <MODEL> 为模型的Model ID
            model="doubao-seed-1-6-250615",
            messages=[
                {
                    'role':'system',
                    'content': ElementUnderstandingAgentPrompt

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
                        "url":  f"{screenshot_base64}"
                    },         
                    },
                    {
                    "type": "text",
                    "text": "图里有什么",
                    },
                ],
                }
            ],
        )

        # =====================================================================
        content=response.choices[0].message.content
        print(f"元素识别输出:{content}")
        try:
            # 1. 替换单引号为双引号
            # 注意：这很粗暴，如果内容本身包含单引号会出问题，但对于这种格式通常有效
            cleaned_content = content.replace("'", '"')
            
            # 2. 将常见全角字符替换为半角字符
            # 创建一个转换表
            full_to_half = str.maketrans(
                "０１２３４５６７８９．：，（） ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                "0123456789.:,() abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"
            )
            cleaned_content = cleaned_content.translate(full_to_half)

            # 3. 移除键名中可能存在的多余空格（使用正则表达式更精确）
            import re
            # 匹配 " key " : 这种情况，并替换为 "key":
            cleaned_content = re.sub(r'"\s*([^"]+?)\s*"\s*:', r'"\1":', cleaned_content)

            # 4. 最后尝试解析清洗后的字符串
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print("即使在清洗后，JSON解析仍然失败!")
            print("原始字符串:", content)
            print("清洗后字符串:", cleaned_content)
            # 这里应该记录错误并优雅地失败，而不是让程序崩溃
            # 例如，可以返回一个空列表或抛出自定义异常
            return []

    def analyze_screenshot(self, screenshot_base64: str) -> List[Dict[str, Any]]:
        print("\n--- 元素理解Agent: 开始分析UI ---")
        ui_elements = self._call_vision_model(screenshot_base64)
        print(f"成功识别出 {len(ui_elements)} 个UI元素。")
        for element in ui_elements:
            # 确保每个元素都有中心点，方便LLM使用
            bbox = element['bbox']
            element['center_x'] = (bbox[0] + bbox[2]) // 2
            element['center_y'] = (bbox[1] + bbox[3]) // 2
        return ui_elements

# ---------------------------------------------------------------------------- #
# 3. 规划Agent (已修改)
# ---------------------------------------------------------------------------- #
class PlanningAgent:
    def __init__(self):
        print("PlanningAgent 已初始化。")
        self.agent=Ark(
        api_key=os.getenv('ARK_API_KEY'),
        )

    def _call_planning_model(self, goal: str, ui_elements: List[Dict[str, Any]], history: List[str]) -> Tuple[str, str]:
        """
        【模型调用部分 - 待您实现】
        调用LLM进行决策，返回一个包含“思考”和“动作字符串”的元组。

        Args:
            goal (str): 用户的最终目标。
            ui_elements (List[Dict[str, Any]]): 当前屏幕的元素列表。
            history (List[str]): 过去执行的动作字符串历史。

        Returns:
            Tuple[str, str]: 一个元组，包含 ('thought', 'action_string')。
        """
        print("[模型调用] 正在思考下一步行动...")
        response = self.agent.chat.completions.create(
            # 替换 <MODEL> 为模型的Model ID
            model="doubao-seed-1-6-250615",
            messages=[
                {
                    'role':'system',
                    'content': PLANNING_AGENT_SYSTEM_PROMPT

                },
                {
                "role": "user",
                "content": [      
                    {
                    "type": "text",
                    "text": f"""user's goal:{goal},ui_elements:{ui_elements}""",
                    },
                ],
                }
            ],
        )
        content=response.choices[0].message.content
        print(f"planning输出:{content}")
        result=json.loads(content)
        thought=result.get('thought')
        action=result.get('action')
        return thought,action
        # # ==================== 请在这里填充您的模型调用逻辑 ====================
        # # 构造一个复杂的Prompt，包含:
        # # 1. 角色设定
        # # 2. 最终目标 (goal)
        # # 3. 可用动作格式 (基于正则表达式的说明)
        # #    例如: "你的输出必须是以下格式之一: tap(x, y), text(\"some text\"), swipe(...), FINISH"
        # # 4. 当前屏幕元素 (ui_elements)，现在包含了中心点坐标。
        # # 5. 历史操作 (history)
        # # 6. 要求模型返回思考过程和最终的动作字符串。
        
        # # 以下是返回值的示例，用于演示：
        # thought = ""
        # action_string = ""
        
        # # 演示多步操作
        # if not history:
        #     thought = "用户的目标是登录。我需要先点击用户名输入框，然后输入用户名。"
        #     # 根据元素分析，用户名输入框(id=1)的中心点是(450, 240)
        #     action_string = "tap(450, 240)"
        # elif history[-1] == 'tap(450, 240)':
        #     thought = "我已经点击了用户名输入框，现在需要输入用户名 'user123'。"
        #     action_string = 'text("user123")'
        # elif history[-1] == 'text("user123")':
        #     thought = "已输入用户名，现在需要点击密码框并输入密码。"
        #      # 密码框(id=2)的中心点是(450, 340)
        #     action_string = "tap(450, 340)"
        # elif history[-1] == 'tap(450, 340)':
        #     thought = "已点击密码框，现在输入密码 'pass456'。"
        #     action_string = 'text("pass456")'
        # elif history[-1] == 'text("pass456")':
        #     thought = "用户名和密码都已输入，现在点击登录按钮。"
        #     # 登录按钮(id=3)的中心点是(450, 460)
        #     action_string = "tap(450, 460)"
        # else:
        #     thought = "登录操作已完成，任务结束。"
        #     action_string = "FINISH"
        # # =====================================================================
        
        # return thought, action_string

    def decide_next_action(self, goal: str, ui_elements: List[Dict[str, Any]], history: List[str]) -> str:
        """
        公开接口：决定下一步的动作字符串。
        """
        print("\n--- 规划Agent: 开始决策 ---")
        thought, action_string = self._call_planning_model(goal, ui_elements, history)
        
        print(f"思考过程: {thought}")
        print(f"生成动作: {action_string}")
        
        return thought,action_string

# ---------------------------------------------------------------------------- #
# 4. 主控制器
# ---------------------------------------------------------------------------- #
class MultiAgentSystem:
    def __init__(self):
        self.element_agent = ElementUnderstandingAgent()
        self.planning_agent = PlanningAgent()
        self.action_parser = ActionParser() # 新增
        self.action_history = []

    def _get_screenshot(self) -> str:
        print("\n--- 系统: 正在捕获屏幕截图 ---")
        dummy_path = "../screenshots/test.png"
        return dummy_path

    def _execute_action(self, action: Action):
        """
        【设备交互 - 待您实现】
        在设备上执行解析后的Action对象。
        """
        print(f"\n--- 系统: 正在执行动作: {action.name} ---")
        print(f"参数: {action.params}")

        if action.name == 'tap':
            x, y = action.params
            print(f"执行点击操作在坐标: ({x}, {y})")
            # os.system(f"adb shell input tap {x} {y}")
        
        elif action.name == 'text':
            text_to_type = action.params[0]
            print(f"执行输入文本操作: '{text_to_type}'")
            # os.system(f"adb shell input text '{text_to_type}'")

        elif action.name == 'long_press':
            x, y = action.params
            print(f"执行长按操作在坐标: ({x}, {y})")
            # os.system(f"adb shell input swipe {x} {y} {x} {y} 1000")

        elif action.name == 'swipe_two_points':
            x1, y1, x2, y2 = action.params
            print(f"执行两点滑动:从({x1}, {y1})到({x2}, {y2})")
            # os.system(f"adb shell input swipe {x1} {y1} {x2} {y2} 300")

        elif action.name == 'wait':
            print("执行等待操作 (e.g., 2 秒)...")
            time.sleep(2)
        
        # 其他动作...

    def run(self, initial_goal: str,screenshot_base64: str):
        goal = initial_goal
        print(f"===== 开始执行任务: {goal} =====")

        # 1. 获取状态
        # screenshot = self._get_screenshot()
        ui_elements = self.element_agent.analyze_screenshot(screenshot_base64)

        # 2. 规划Agent决定下一步 (返回字符串)
        thought,action_string = self.planning_agent.decide_next_action(goal, ui_elements, self.action_history)

        # 3. 解析动作字符串
        # action = self.action_parser.parse(action_string)
        action=action_string
        return action
        # # 4. 处理特殊动作
        # if action.name == 'FINISH':
        #     print("\n===== 任务完成 (Agent决定终止) =====")
        
        # if action.name == 'need_feedback':
        #     print("\n--- 系统: Agent需要更多信息 ---")
        #     question = action.params[0] if action.params else '我应该怎么做？'
        #     user_feedback = input(f"Agent提问: {question}\n您的回答: ")
            
        #     feedback_log = f'feedback_request: "{question}", user_response: "{user_feedback}"'
        #     self.action_history.append(feedback_log)
        #     goal += f"\n[用户补充信息]: {user_feedback}"

        # # 5. 执行动作
        # self._execute_action(action)

        # # 6. 记录历史
        # self.action_history.append(action_string)

# ---------------------------------------------------------------------------- #
# 5. 运行示例
# ---------------------------------------------------------------------------- #
# if __name__ == "__main__":
#     # user_goal = "帮我登录这个App，我的用户名是 user123，密码是 pass456。"
    
#     # app_automator = MultiAgentSystem()
#     # app_automator.run(initial_goal=user_goal)
