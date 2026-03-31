# NetGuard Pro — Android APK 版

小米 14T Pro / Android 14 优化 | Kivy 2.3 | Python 3.10

## 功能

- **13 大路由器品牌**真实 API 对接（锐捷/小米/TP-Link/华为/华硕/网件/D-Link/360/腾达/水星/OpenWrt/中兴/演示）
- 📊 实时流量监控仪表盘
- 🖥 设备卡片列表（信号/延迟/丢包/稳定性）
- 🔒 访问控制（平台权限 + 时间段限制）
- 📡 设备 Ping 测试
- 📋 事件日志

---

## 打包为 APK（3 种方式选一）

### 方式 A：GitHub Actions（推荐，免安装）

1. 将本目录上传到 GitHub 仓库
2. 点击仓库的 **Actions** 标签
3. 选择 **Build NetGuard Pro APK** → **Run workflow**
4. 约 30 分钟后下载 APK

### 方式 B：WSL2 + Ubuntu（本地构建）

```bash
# 1. Windows PowerShell（管理员）安装 WSL2
wsl --install
# 重启后进入 Ubuntu

# 2. Ubuntu 终端
sudo apt update
sudo apt install -y python3-pip default-jdk git zip unzip \
    libffi-dev libssl-dev python3-dev autoconf libtool cmake

pip3 install buildozer==1.5.0 cython==0.29.37

# 3. 进入项目目录
cd /mnt/c/Users/你的用户名/netguard_android

# 4. 构建（首次约 30 分钟）
buildozer android debug

# 5. 安装到手机
adb install bin/netguardpro-3.0.0-arm64-v8a-debug.apk
```

### 方式 C：自动检测脚本

```bash
python3 build_assistant.py
```

---

## 安装到小米 14T Pro

1. 打开 **设置 → 更多设置 → 开发者选项**（连续点击版本号7次）
2. 开启 **USB 调试** 和 **允许 USB 安装**
3. 用 USB 线连接电脑，执行：
   ```
   adb install bin/netguardpro-3.0.0-arm64-v8a-debug.apk
   ```
   或直接将 APK 文件传到手机，用文件管理器安装

---

## 使用说明

1. 打开 App → 选择路由器品牌（锐捷）
2. 填写 IP（192.168.28.198）、账号密码
3. 点击连接 → 进入主界面
4. 底部导航切换：监控 / 设备 / 控制 / 日志

---

## 文件说明

```
netguard_android/
├── main.py              # Kivy 主程序（2100+ 行）
├── buildozer.spec       # Android 打包配置
├── build_assistant.py   # 构建辅助脚本
├── .github/
│   └── workflows/
│       └── build.yml    # GitHub Actions 自动构建
└── README.md
```
