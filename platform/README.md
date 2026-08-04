# AndroTMem Data Collection Platform

English | [Chinese](README.zh-CN.md)

This directory contains the frontend and backend code for the AndroTMem data collection platform. The platform is used to connect Android devices, capture screenshots and UI XML, run model-assisted action prediction, execute ADB actions, and save human-annotated interaction trajectories.

The platform has two main parts:

- `Friday_backend/`: a Flask backend for ADB device control, screenshot capture, model inference, action execution, and annotation persistence.
- `friday_flywheel/`: a Vue 3 + Vite frontend for data collection pages, screenshot preview, action form editing, and backend API calls.

## Directory Structure

```text
platform/
|-- README.md
|-- README.zh-CN.md
|-- Friday_backend/
|   |-- friday.py
|   |-- config.py
|   |-- requirements.txt
|   |-- prompt_templates.py
|   |-- prompt_dispatcher.py
|   |-- app_prompts/
|   |   `-- meituan_waimai_prompts.py
|   `-- multi_agents/
|       |-- friday_multi_agents.py
|       |-- adb_executor.py
|       `-- test_volcengine.py
`-- friday_flywheel/
    |-- package.json
    |-- vite.config.js
    |-- .env
    |-- .env.development
    |-- .env.production
    |-- public/
    |   `-- router/
    |       `-- index.js
    `-- src/
        |-- main.js
        |-- App.vue
        |-- utils/
        |   `-- request.js
        |-- views/
        |   |-- HomePage.vue
        |   |-- SingleAgent0927.vue
        |   |-- MultiAgents0927.vue
        |   `-- MultiAgents0927Edit.vue
        `-- components/
```

## Backend Overview

Backend entry point:

```text
Friday_backend/friday.py
```

Runtime configuration:

```text
Friday_backend/config.py
```

The backend starts a Flask service and provides the following capabilities:

- Connect to an Android device or emulator through ADB.
- Capture the current screen.
- Dump the current UI hierarchy XML.
- Return screenshot, UI XML, and foreground package information together.
- Restart the target application.
- Call a vision-language model to predict the next action.
- Execute human-edited or model-generated actions on the device.
- Save single-step or multi-step annotations.
- Save screenshots as PNG files and reference them with `image_name` in annotation JSON.

### Important Backend Files

`friday.py`

- Main Flask application.
- Defines all HTTP APIs.
- Contains `ADBController`, which wraps screenshot capture, UI XML dump, tap, long press, swipe, text input, and app launching.
- Implements annotation saving and model inference routes.

`config.py`

- Local backend configuration.
- Configures ADB device ID, ADB executable path, default package name, data output paths, model service endpoint, and Flask host/port.

`prompt_templates.py`

- Generic task prompt templates.
- Currently includes a base template for shopping tasks.

`prompt_dispatcher.py`

- Routes `(app_name, task_type)` to a concrete prompt builder.
- Current examples include `meituan_waimai/shopping` and `wechat/chat`.

`app_prompts/`

- Stores app-specific and task-specific prompt builders.

`multi_agents/friday_multi_agents.py`

- Multi-agent inference implementation.
- Includes UI element understanding, planning, and action parsing components.

`multi_agents/adb_executor.py`

- Standalone ADB action execution module.
- Parses and executes action strings such as `tap(...)`, `text(...)`, `long_press(...)`, `swipe(...)`, `swipe_two_points(...)`, `screenshot()`, `restart_app()`, `back()`, `home()`, and `clear()`.

## Backend Configuration

Edit:

```text
Friday_backend/config.py
```

Common fields:

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

Field meanings:

- `CLOUD_DEVICE_IP_PORT`: ADB device ID. Use `adb devices` to find it.
- `ADB_PATH`: ADB executable path. Keep it as `adb` if ADB is available in `PATH`.
- `DEFAULT_APP_NAME`: default Android package name to launch.
- `BASE_DATA_DIR`: root directory for collected data.
- `BASE_ANNO_PATH`: output directory for annotation JSON files.
- `BASE_SCREENSHOT_PATH`: temporary screenshot and XML directory.
- `IMGS_PATH`: output directory for final annotation screenshots.
- `VLLM_API_URL`: local OpenAI-compatible model endpoint.
- `FLASK_PORT`: backend port. The frontend development proxy points to `5001` by default.

Do not commit real API keys. Keep model API keys, third-party API base URLs, and other secrets in local configuration or environment variables.

## Backend Setup and Startup

Enter the backend directory:

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\Friday_backend
```

Create and activate a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Check device connection:

```powershell
adb devices
```

Start the backend:

```powershell
python friday.py
```

Default backend address:

```text
http://127.0.0.1:5001
```

## ADB and Device Preparation

Before collecting data, prepare an Android device or emulator:

1. Enable developer mode and USB debugging.
2. Verify that `adb devices` lists the target device.
3. Set `CLOUD_DEVICE_IP_PORT` in `config.py` to the target device ID.
4. If text input depends on ADB Keyboard, install and enable the corresponding input method on the device.
5. If a target app needs to be launched, make sure `DEFAULT_APP_NAME` or the frontend-provided `package_name` matches the actual package installed on the device.

Useful commands:

```powershell
adb devices
adb -s emulator-5554 shell screencap -p /sdcard/screen.png
adb -s emulator-5554 shell uiautomator dump /sdcard/window_dump.xml
```

## Backend APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/get-screenshot` | Capture the current device screenshot and return a Base64 Data URL. |
| `GET` | `/get-ally` | Return the current UI hierarchy XML. |
| `GET` | `/get-all` | Return screenshot, UI XML, and foreground package together. |
| `POST` | `/restart-app` | Restart the default target app. |
| `POST` | `/infer` | Run single-agent model inference from screenshot and task slots. |
| `POST` | `/infer_multi_agents` | Run multi-agent inference from screenshot and goal. |
| `POST` | `/save-annotation` | Save the legacy single-step annotation format. |
| `POST` | `/save-annotation-new` | Save the newer multi-step trajectory annotation format. |
| `POST` | `/execute-action` | Execute an `action_info` object on the device. |
| `GET` | `/test_get` | Backend connectivity test. |
| `POST` | `/test_post` | Backend connectivity test. |
| `POST` | `/openai_infer` | Call an OpenAI-compatible Chat Completions API. |

### `/get-all`

Example response:

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

Example request:

```json
{
  "action_info": {
    "action": "tap",
    "x": 500,
    "y": 1200
  }
}
```

Supported action types:

- `tap`
- `long_press`
- `swipe`
- `swipe_two_points`
- `text`
- `open_app`
- `wait`
- `FINISH`

`wait` and `FINISH` are mainly used for annotation and model output. They may not trigger a real ADB operation.

### `/save-annotation-new`

This route is the preferred endpoint for saving multi-step trajectories. The frontend sends:

```json
{
  "user_id": "annotator_001",
  "instruction": "Task instruction",
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
      "application_name_cn": "Meituan Waimai",
      "application_name_en": "Meituan Waimai",
      "extra_info": {}
    }
  ]
}
```

The backend writes a task object similar to:

```json
{
  "task_id": "uuid",
  "instruction": "Task instruction",
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

Annotation JSON is written to:

```text
Friday_backend/../data/annotations/<user_id>.json
```

Screenshots are written to:

```text
Friday_backend/../data/imgs_all/
```

## Frontend Overview

Frontend directory:

```text
friday_flywheel/
```

Technology stack:

- Vue 3
- Vite
- Vue Router
- Ant Design Vue
- Axios

### Important Frontend Files

`package.json`

- Defines frontend dependencies and npm scripts.

`vite.config.js`

- Configures Vite plugins.
- Configures the development proxy from `/api` to `http://127.0.0.1:5001`.

`src/utils/request.js`

- Wraps Axios `get` and `post` helpers.
- Reads `baseURL` from `VITE_API_BASE_URL`.

`public/router/index.js`

- Defines frontend routes.
- Uses hash history, which is convenient for static deployment and local preview.

`src/views/HomePage.vue`

- Home page with navigation buttons for single-agent, multi-agent, and edit pages.

`src/views/SingleAgent0927.vue`

- Single-agent annotation page.
- Supports screenshot capture, action form editing, model inference, action execution, and annotation saving.

`src/views/MultiAgents0927.vue`

- Multi-agent annotation page.
- Supports multi-step trajectory editing, screenshot and UI XML capture, model inference, action execution, and new-format annotation saving.

`src/views/MultiAgents0927Edit.vue`

- Multi-agent trajectory editing page.
- Extends the multi-step annotation workflow with editing and import-related features.

## Frontend Routes

| Path | Component | Description |
| --- | --- | --- |
| `/` | `HomePage.vue` | Home page. |
| `/single-agent0927` | `SingleAgent0927.vue` | Single-agent annotation. |
| `/multi-agent0927` | `MultiAgents0927.vue` | Multi-agent annotation. |
| `/multi-agent0927-edit` | `MultiAgents0927Edit.vue` | Multi-agent trajectory editing. |

## Frontend Environment

Development environment file:

```text
friday_flywheel/.env.development
```

Current value:

```text
VITE_API_BASE_URL=/api
```

This means frontend requests go to the Vite dev server first, then are forwarded to the Flask backend by the proxy in `vite.config.js`.

Production environment file:

```text
friday_flywheel/.env.production
```

Current value:

```text
VITE_API_BASE_URL=http://127.0.0.1:5001
```

If the backend is deployed on another host or port, update this value accordingly.

## Frontend Setup and Startup

Enter the frontend directory:

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\friday_flywheel
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Build for production:

```powershell
npm run build
```

Preview the production build locally:

```powershell
npm run preview
```

Local versions recorded by the project:

```text
Node.js v22.14.0
npm 10.9.2
```

## Recommended Workflow

1. Start the Android device or emulator.
2. Run `adb devices` and confirm that the target device is online.
3. Edit `Friday_backend/config.py` for device ID, ADB path, default package name, and output directories.
4. Start the backend:

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\Friday_backend
.\.venv\Scripts\Activate.ps1
python friday.py
```

5. Start the frontend:

```powershell
cd D:\WorkSpace\Projects\AndroTMem\platform\friday_flywheel
npm run dev
```

6. Open the frontend page in a browser.
7. Choose the single-agent annotation, multi-agent annotation, or multi-agent editing page from the home page.
8. Initialize the app or capture a screenshot and confirm that the current device screen appears.
9. Fill in task information, edit the action form, and optionally call model inference.
10. Save the annotation and check the output under `data/annotations` and `data/imgs_all`.

## Data Output

Default output root is configured in `config.py`:

```text
Friday_backend/../data/
|-- annotations/
|-- imgs_all/
|-- logs/
`-- screenshots_tmp/
```

Directory meanings:

- `annotations/`: annotation JSON files.
- `imgs_all/`: final screenshot PNG files.
- `logs/`: backend logs.
- `screenshots_tmp/`: temporary screenshots and UI XML files.

For the new multi-step annotation route, each step screenshot is saved to `imgs_all/`, and the annotation JSON references it with `image_name`.

## Troubleshooting

### Frontend cannot reach backend

Check:

- The backend is running.
- The backend port is `5001`.
- `.env.development` uses `VITE_API_BASE_URL=/api` in development.
- The proxy target in `vite.config.js` points to the correct backend address.

### Screenshot capture fails

Check:

- `adb devices` lists the target device.
- `CLOUD_DEVICE_IP_PORT` in `config.py` matches the device ID.
- USB debugging is enabled.
- `ADB_PATH` is correct.

### Text input fails

Check:

- ADB Keyboard or an equivalent input method is installed and enabled.
- The backend `text` action uses the broadcast parameters supported by the device.

### App launch fails

Check:

- `DEFAULT_APP_NAME` or frontend-provided `package_name` is the real package name on the device.
- Confirm the target package name before collection.

### Model inference fails

Check:

- `VLLM_API_URL` is reachable.
- The model service is compatible with the Chat Completions request format.
- Required environment variables for multi-agent inference are set locally.
- Real API keys are not committed to the repository.

## Maintenance Notes

- Move real secrets to environment variables or untracked local config files.
- Keep device-related configuration centralized in `config.py`.
- When adding a new app or task type, add a prompt builder under `app_prompts/` and register it in `prompt_dispatcher.py`.
- When adding a new action type, update the frontend action form, backend `format_action`, `/execute-action`, and ADB execution logic together.
- After collection, regularly validate that annotation JSON files can be consumed by downstream data processing scripts.
