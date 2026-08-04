## Getting Started

These instructions will help you set up and run the project locally.

### Prerequisites

- Python 3.x installed on your machine.
- Git (optional, for cloning the repository).

### Installation

1. Clone the repository (if not already cloned):

```bash
git clone <your-repository-url>
cd <repository-folder>
```
## Init Project
Download the ADB keyboard.
```bash
adb install adb_keyboard.apk
adb -s <device_id> install app.apk
adb -s emulator-5554 shell am broadcast -a ADB_INPUT_TEXT --es text '测试一下'

Set it as the default settings.
```
0.前端和后端导出
后端使用pyinstallar导出，在对应虚拟环境下执行该命令



1. ADB安装
- 下载adb
https://blog.csdn.net/x2584179909/article/details/108319973
- 使用adb devices查看连接的设备的列表，获取设备id
List of devices attached
emulator-5554	device

- 手机打开开发者模式，打开USB调试

2. 后端设置
- 打开config.py文件，设置设备id，即CLOUD_DEVICE_IP_PORT的值
    - 标注和截图存在annotations和all_imgs文件夹下
- 双击friday.exe，打开后端

3. 前端设置
- 安装node.js
https://www.runoob.com/nodejs/nodejs-install-setup.html
- 在前端文件夹front下，执行`npx serve`，打开前端
- `/front/config/config.js`下，可以配置不同app的包名(com.xxx.xxx)
    - 不同应用商店的app包名不同
    - 使用appList和packageList两级映射，标注保存中间的value值，执行时打开value对应的具体包名
    - packageList需要标注者进行维护