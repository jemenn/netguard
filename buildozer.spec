[app]
title = NetGuard Pro
package.name = netguardpro
package.domain = com.netguard

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = tests,bin,venv,.git,__pycache__,.buildozer

version = 3.0.0
requirements = python3,kivy==2.3.0,requests,urllib3,certifi,chardet,idna

orientation = portrait

presplash.color = #080C12

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_STATE

android.minapi = 26
android.api = 34
android.ndk = 25b
android.sdk = 34
android.archs = arm64-v8a
android.allow_backup = False
android.accept_sdk_license = True
android.enable_androidx = True

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
build_dir = ./.buildozer
bin_dir = ./bin
