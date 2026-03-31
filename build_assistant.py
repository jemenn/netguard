"""
NetGuard Pro — 一键构建辅助脚本
自动检测环境并给出最佳构建方案
"""
import sys, os, subprocess, platform

def check_env():
    print("=" * 58)
    print("  NetGuard Pro v3.0 — Android APK 构建助手")
    print("=" * 58)

    sys_name = platform.system()
    print("\n【系统检测】", sys_name)

    if sys_name == "Windows":
        print("""
⚠  Windows 不能直接运行 buildozer。
   推荐方案（按难度排序）：

   ✅ 方案A（推荐）— 使用 WSL2 + Ubuntu：
      1. 打开 PowerShell（管理员），运行：
         wsl --install
         重启电脑后自动安装 Ubuntu

      2. 在 Ubuntu 终端里运行：
         python3 build_assistant.py

   ✅ 方案B — 使用 GitHub Actions 云端构建（免费）：
      见下方 [GitHub Actions 说明]

   ✅ 方案C — 直接在 Linux/Mac 上运行本脚本
""")
        input("按 Enter 退出...")
        return

    if sys_name == "Linux" or sys_name == "Darwin":
        _build_linux()


def _build_linux():
    print("\n【Linux/Mac 环境】")

    # 检查 Python 版本
    v = sys.version_info
    print("Python: {}.{}.{}".format(v.major, v.minor, v.micro))
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print("❌ 需要 Python 3.8+")
        return

    # 检查依赖
    missing = []
    tools = {
        "java":       "sudo apt install -y default-jdk",
        "git":        "sudo apt install -y git",
        "zip":        "sudo apt install -y zip unzip",
        "wget":       "sudo apt install -y wget",
        "adb":        "sudo apt install -y adb",
    }
    for tool, install_cmd in tools.items():
        r = subprocess.run(["which", tool], capture_output=True)
        if r.returncode != 0:
            missing.append((tool, install_cmd))

    if missing:
        print("\n⚠  缺少以下工具，正在安装...")
        subprocess.run(["sudo", "apt", "update", "-q"])
        for tool, cmd in missing:
            print("  → 安装 {}...".format(tool))
            subprocess.run(cmd.split(), check=False)

    # 安装 buildozer
    print("\n【安装 buildozer 和 Cython】")
    deps = [
        "buildozer", "cython==0.29.37",
        "kivy", "requests"
    ]
    for dep in deps:
        print("  → pip install {}".format(dep))
        subprocess.run([sys.executable, "-m", "pip", "install", dep, "-q"],
                       check=False)

    # 安装 Android SDK 依赖
    print("\n【安装 Android 构建依赖】")
    android_deps = [
        "libffi-dev", "libssl-dev", "libzbar-dev",
        "python3-dev", "autoconf", "libtool",
        "pkg-config", "zlib1g-dev", "libncurses5-dev",
        "libncursesw5-dev", "libtinfo5", "cmake",
        "libffi-dev", "libssl-dev"
    ]
    subprocess.run(["sudo", "apt", "install", "-y"] + android_deps, check=False)

    print("""
【准备完毕！请执行以下命令构建 APK】

  cd /path/to/netguard_android
  buildozer android debug

  首次构建约需 20-40 分钟（需下载 Android SDK/NDK）
  构建完成后 APK 在 bin/ 目录下

【传输到手机】
  adb install bin/netguardpro-3.0.0-arm64-v8a-debug.apk

  或用 USB 线传输到手机后安装
  （小米手机需在设置→开发者选项→USB安装 中允许安装）
""")


def _show_github_actions():
    print("""
【GitHub Actions 云端构建（免费，无需本地 Linux）】

1. 将项目上传到 GitHub 仓库
2. 在仓库根目录创建 .github/workflows/build.yml：

---yaml
name: Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install buildozer cython==0.29.37
          sudo apt install -y default-jdk git zip unzip
      - name: Build APK
        run: buildozer android debug
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: netguard-apk
          path: bin/*.apk
---

3. Push 代码后，GitHub Actions 自动构建
4. 构建完成后在 Actions 页面下载 APK
""")


if __name__ == "__main__":
    if "--github" in sys.argv:
        _show_github_actions()
    else:
        check_env()
