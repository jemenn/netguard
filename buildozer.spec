[app]
# ── 应用基本信息 ──────────────────────────────────────────
title = NetGuard Pro
package.name = netguardpro
package.domain = com.netguard

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = tests, bin, venv, .git, __pycache__, .buildozer

version = 3.0.0
requirements = python3,kivy==2.3.0,requests,urllib3,certifi,chardet,idna

# 主程序
main.py = main.py

# ── 界面方向 ──────────────────────────────────────────────
orientation = portrait

# ── 图标与启动画面 ────────────────────────────────────────
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png
presplash.color = #080C12

# ── Android 权限 ──────────────────────────────────────────
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE

# ── Android API 级别 ──────────────────────────────────────
android.minapi  = 26
android.api     = 34
android.ndk     = 25b
android.sdk     = 34

# 目标 ABI（小米 14T Pro 是 arm64）
android.archs = arm64-v8a

# ── 应用特性 ──────────────────────────────────────────────
android.allow_backup = False
android.accept_sdk_license = True

# ── Gradle / 构建配置 ────────────────────────────────────
android.gradle_dependencies = ''
android.add_jars = 
android.enable_androidx = True

# ── p4a 配置 ─────────────────────────────────────────────
p4a.branch = master
p4a.local_recipes = 

# ── iOS（不使用，留空）────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1

# 构建目录
build_dir = ./.buildozer
bin_dir   = ./bin
