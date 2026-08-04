# AndroTMem Data Collection Platform

[English](README.md) | 简体中文

该目录包含 AndroTMem 数据采集平台的前后端代码，用于连接 Android 设备、获取截图和 UI XML、辅助模型推理、执行 ADB 动作，以及保存人工标注轨迹数据。

平台由两部分组成：

- `Friday_backend/`：Flask 后端，负责 ADB 设备控制、截图获取、模型推理接口、动作执行和标注保存。
- `friday_flywheel/`：Vue 3 + Vite 前端，负责数据采集与标注页面展示、截图预览、动作表单编辑和接口调用。

## 目录结构

```text
platform/
├── README.md
├── README.zh-CN.md
├── Friday_backend/
│   ├── friday.py
│   ├── config.py
│   ├── requirements.txt
│   ├── prompt_templates.py
│   ├── prompt_dispatcher.py
│   ├── app_prompts/
│   │   └── meituan_waimai_prompts.py
│   └── multi_agents/
│       ├── friday_multi_agents.py
│       ├── adb_executor.py
│       └── test_volcengine.py
└── friday_flywheel/
    ├── package.json
    ├── vite.config.js
    ├── .env
    ├── .env.development
    ├── .env.production
    ├── public/
    │   └── router/
    │       └── index.js
    └── src/
        ├── main.js
        ├── App.vue
        ├── utils/
        │   └── request.js
        ├── views/
        │   ├── HomePage.vue
        │   ├── SingleAgent0927.vue
        │   ├── MultiAgents0927.vue
        │   └── MultiAgents0927Edit.vue
        └── components/
```

## 后端说明

后端入口是：

```text
Friday_backend/friday.py
```

它启动一个 Flask 服务，默认监听配置来自：

```text
Friday_backend/config.py
```

核心职责：

- 通过 ADB 连接 Android 设备或模拟器。
- 获取当前屏幕截图。
- 获取当前 UI hierarchy XML。
- 获取截图、UI XML 和前台包名的组合状态。
- 重启目标 App。
- 调用视觉语言模型生成下一步动作。
- 执行人工或模型生成的动作。
- 保存单步或多步标注数据。
- 将截图保存为 PNG，并在标注 JSON 中写入 `image_name`。

### 关键文件

`friday.py`

- Flask 主服务。
- 定义 HTTP API。
- 内置 `ADBController`，封装截图、UI XML、点击、长按、滑动、文本输入、打开 App 等 ADB 操作。
- 定义标注保存逻辑。
- 定义单 Agent 和 Multi-Agent 推理入口。

`config.py`

- 后端本地配置文件。
- 配置设备 ID、ADB 路径、默认 App 包名、数据输出目录、模型服务地址和 Flask 端口。

`prompt_templates.py`

- 通用任务 prompt 模板。
- 当前包含购物类任务的基础模板。

`prompt_dispatcher.py`

- 根据 `(app_name, task_type)` 路由到具体 prompt 模板。
- 当前示例包含 `meituan_waimai/shopping` 和 `wechat/chat`。

`app_prompts/`

- 存放不同 App 和任务类型的 prompt 生成函数。

`multi_agents/friday_multi_agents.py`

- Multi-Agent 推理逻辑。
- 包含 UI 元素理解 Agent、规划 Agent、动作解析器等组件。

`multi_agents/adb_executor.py`

- 独立的 ADB 动作执行模块。
- 支持解析并执行 `tap(...)`、`text(...)`、`long_press(...)`、`swipe(...)`、`swipe_two_points(...)`、`screenshot()`、`restart_app()`、`back()`、`home()`、`clear()` 等动作字符串。

## 后端配置

编辑：

```text
Friday_backend/config.py
```

常用配置项：

```python
CLOUD_DEVICE_IP_PORT = "emulator-5554"
ADB_PATH = "adb"
DEFAULT_APP_NAME = "com.sankuai.meituan.takeoutnew"

BASE_DATA_DIR = os.path.join(_BASE_DIR, "../data")
LOG_PATH = os.path.join(BASE_DATA_DIR, "logs", "app.log")
BASE_ANNO_PATH = os.path.join(BASE_DATA_DIR, "annotations")
BASE_SCREENSHOT_PATH = os.path.join(BASE_DATA_DIR, "screenshots_tmp")
IMGS_PATH = os.path.join(BASE_DATA_DIR, "imgs_all")

VLLM_API_URL = "http://localhost:8000/v1/chat/completions"

FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
```

说明：

- `CLOUD_DEVICE_IP_PORT`：ADB 设备 ID，可通过 `adb devices` 查看。
- `ADB_PATH`：ADB 可执行文件路径。如果 `adb` 已加入系统环境变量，可保持为 `adb`。
- `DEFAULT_APP_NAME`：默认启动的 Android App 包名。
- `BASE_DATA_DIR`：采集数据输出根目录。
- `BASE_ANNO_PATH`：标注 JSON 输出目录。
- `BASE_SCREENSHOT_PATH`：临时截图和 XML 输出目录。
- `IMGS_PATH`：最终保存的标注截图目录。
- `VLLM_API_URL`：兼容 OpenAI Chat Completions 格式的本地模型服务地址。
- `FLASK_PORT`：后端端口，前端开发代理默认转发到 `5001`。

注意：模型 API Key、第三方 API Base URL 等敏感信息应放在本地配置或环境变量中，不要提交真实密钥。

## 后端安装与启动

进入后端目录：

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\Friday_backend
```

创建并激活 Python 环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirements.txt
```

确认设备连接：

```powershell
adb devices
```

启动后端：

```powershell
python friday.py
```

默认服务地址：

```text
http://127.0.0.1:5001
```

## ADB 和设备准备

采集前需要准备 Android 设备或模拟器：

1. 开启开发者模式和 USB 调试。
2. 确认本机可以执行 `adb devices`。
3. 将 `config.py` 中的 `CLOUD_DEVICE_IP_PORT` 改为目标设备 ID。
4. 如果文本输入依赖 ADB Keyboard，需要先在设备上安装并启用对应输入法。
5. 如需打开特定 App，确认 `DEFAULT_APP_NAME` 或前端传入的 `package_name` 与设备上实际包名一致。

常用命令：

```powershell
adb devices
adb -s emulator-5554 shell screencap -p /sdcard/screen.png
adb -s emulator-5554 shell uiautomator dump /sdcard/window_dump.xml
```

## 后端 API

主要接口如下。

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/get-screenshot` | 获取当前设备截图，返回 Base64 Data URL。 |
| `GET` | `/get-ally` | 获取当前 UI hierarchy XML。 |
| `GET` | `/get-all` | 一次返回截图、UI XML 和前台包名。 |
| `POST` | `/restart-app` | 重启默认目标 App。 |
| `POST` | `/infer` | 基于当前截图和任务槽位调用单 Agent 模型推理。 |
| `POST` | `/infer_multi_agents` | 基于当前截图和目标调用 Multi-Agent 推理。 |
| `POST` | `/save-annotation` | 保存旧版单步标注格式。 |
| `POST` | `/save-annotation-new` | 保存新版多步轨迹标注格式。 |
| `POST` | `/execute-action` | 根据 `action_info` 在设备上执行动作。 |
| `GET` | `/test_get` | 后端连通性测试。 |
| `POST` | `/test_post` | 后端连通性测试。 |
| `POST` | `/openai_infer` | 调用 OpenAI-compatible Chat Completions 接口。 |

### `/get-all`

返回示例结构：

```json
{
  "status": "success",
  "message": "ok",
  "data": {
    "screenshot_base64": "data:image/png;base64,...",
    "ui_xml": "...",
    "package_name": "com.example.app"
  }
}
```

### `/execute-action`

请求示例：

```json
{
  "action_info": {
    "action": "tap",
    "x": 500,
    "y": 1200
  }
}
```

支持的动作类型：

- `tap`
- `long_press`
- `swipe`
- `swipe_two_points`
- `text`
- `open_app`
- `wait`
- `FINISH`

其中 `wait` 和 `FINISH` 主要用于标注和模型输出，不一定会触发实际 ADB 操作。

### `/save-annotation-new`

这是更适合保存多步轨迹的接口。前端会提交：

```json
{
  "user_id": "annotator_001",
  "instruction": "任务指令",
  "step_list": [
    {
      "step_index": "1",
      "screenshot_64": "data:image/png;base64,...",
      "screenshot_xml": "...",
      "actionForm": {
        "action": "tap",
        "x": 500,
        "y": 1200
      },
      "application": "meituan_waimai",
      "application_name_cn": "美团外卖",
      "application_name_en": "Meituan Waimai",
      "extra_info": {}
    }
  ]
}
```

后端会生成：

```json
{
  "task_id": "uuid",
  "instruction": "任务指令",
  "applications": [],
  "steps": [
    {
      "step_index": "1",
      "actionForm": {},
      "application": "",
      "application_name_cn": "",
      "application_name_en": "",
      "extra_info": {},
      "image_name": "uuid.png",
      "image_xml": "..."
    }
  ]
}
```

标注 JSON 默认写入：

```text
Friday_backend/../data/annotations/<user_id>.json
```

截图默认写入：

```text
Friday_backend/../data/imgs_all/
```

## 前端说明

前端目录：

```text
friday_flywheel/
```

技术栈：

- Vue 3
- Vite
- Vue Router
- Ant Design Vue
- Axios

### 关键文件

`package.json`

- 定义前端依赖和启动命令。

`vite.config.js`

- 配置 Vite 插件。
- 配置开发代理：`/api` 转发到后端 `http://127.0.0.1:5001`。

`src/utils/request.js`

- 封装 Axios 的 `get` 和 `post`。
- `baseURL` 来自 `VITE_API_BASE_URL`。

`public/router/index.js`

- 定义前端页面路由。
- 使用 Hash Router，方便静态部署或本地打开。

`src/views/HomePage.vue`

- 首页。
- 提供入口跳转到 single-agent、multi-agent 和编辑页面。

`src/views/SingleAgent0927.vue`

- 单 Agent 标注页面。
- 支持截图获取、动作表单编辑、模型推理、动作执行和标注保存。

`src/views/MultiAgents0927.vue`

- Multi-Agent 标注页面。
- 支持多步轨迹编辑、截图与 UI XML 获取、模型推理、动作执行和新版标注保存。

`src/views/MultiAgents0927Edit.vue`

- Multi-Agent 编辑页面。
- 在多步轨迹标注基础上增加编辑和导入相关能力。

## 前端路由

| Path | 页面 | 说明 |
| --- | --- | --- |
| `/` | `HomePage.vue` | 首页入口。 |
| `/single-agent0927` | `SingleAgent0927.vue` | 单 Agent 标注。 |
| `/multi-agent0927` | `MultiAgents0927.vue` | Multi-Agent 标注。 |
| `/multi-agent0927-edit` | `MultiAgents0927Edit.vue` | Multi-Agent 轨迹编辑。 |

## 前端环境配置

开发环境：

```text
friday_flywheel/.env.development
```

当前配置：

```text
VITE_API_BASE_URL=/api
```

这表示前端请求会先打到 Vite dev server，再通过 `vite.config.js` 的 proxy 转发到 Flask 后端。

生产环境：

```text
friday_flywheel/.env.production
```

当前配置：

```text
VITE_API_BASE_URL=http://127.0.0.1:5001
```

如果后端部署在其他机器或端口，需要同步修改该值。

## 前端安装与启动

进入前端目录：

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\friday_flywheel
```

安装依赖：

```powershell
npm install
```

启动开发服务：

```powershell
npm run dev
```

构建生产版本：

```powershell
npm run build
```

本地预览构建结果：

```powershell
npm run preview
```

项目当前记录的本地版本：

```text
Node.js v22.14.0
npm 10.9.2
```

## 推荐启动流程

1. 启动 Android 设备或模拟器。
2. 使用 `adb devices` 确认设备在线。
3. 修改 `Friday_backend/config.py` 中的设备 ID、ADB 路径、默认包名和输出目录。
4. 启动后端：

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\Friday_backend
.\.venv\Scripts\Activate.ps1
python friday.py
```

5. 启动前端：

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\friday_flywheel
npm run dev
```

6. 打开前端页面。
7. 在首页选择 `single-agent标注`、`multi-agent标注` 或 `multi-agent---编辑`。
8. 点击初始化或获取截图，确认能看到设备当前界面。
9. 填写任务信息、编辑动作表单，必要时调用模型推理。
10. 保存标注，检查 `data/annotations` 和 `data/imgs_all` 是否生成文件。

## 数据输出

默认输出目录由 `config.py` 控制：

```text
Friday_backend/../data/
├── annotations/
├── imgs_all/
├── logs/
└── screenshots_tmp/
```

说明：

- `annotations/`：保存标注 JSON。
- `imgs_all/`：保存最终截图 PNG。
- `logs/`：保存后端日志。
- `screenshots_tmp/`：保存临时截图和 UI XML。

新版多步标注保存后，每个 step 的截图会被写入 `imgs_all/`，标注 JSON 中用 `image_name` 引用该图片。

## 常见问题

### 前端请求后端失败

检查：

- 后端是否已启动。
- 后端端口是否为 `5001`。
- 开发环境下 `.env.development` 是否为 `VITE_API_BASE_URL=/api`。
- `vite.config.js` 的 proxy target 是否指向正确后端地址。

### 无法获取截图

检查：

- `adb devices` 是否能看到目标设备。
- `config.py` 中 `CLOUD_DEVICE_IP_PORT` 是否与设备 ID 一致。
- 设备是否开启 USB 调试。
- `ADB_PATH` 是否正确。

### 文本输入失败

检查：

- 是否安装并启用了 ADB Keyboard 或等价输入法。
- 后端 `text` 动作是否使用设备支持的广播参数。

### 打开 App 失败

检查：

- `DEFAULT_APP_NAME` 或前端传入的 `package_name` 是否为设备上的真实包名。
- 可以用 ADB 或第三方工具确认目标 App 包名。

### 模型推理失败

检查：

- `VLLM_API_URL` 是否可访问。
- 模型服务是否兼容 Chat Completions 请求格式。
- 本地环境变量是否包含 Multi-Agent 所需的 API Key。
- 不要在代码仓库中提交真实 API Key。

## 维护建议

- 将真实密钥迁移到环境变量或未提交的本地配置文件。
- 将设备相关配置集中维护在 `config.py`。
- 新增 App 或任务类型时，优先在 `app_prompts/` 中添加 prompt 函数，再在 `prompt_dispatcher.py` 中注册路由。
- 新增动作类型时，需要同时更新前端动作表单、后端 `format_action`、`execute-action` 和必要的 ADB 执行逻辑。
- 采集后定期检查 `annotations/` 中的 JSON 是否能被后续数据处理脚本读取。
