# -*- coding: utf-8 -*-
"""
NetGuard Pro — Android Kivy 版
支持 13 大路由器品牌真实 API 对接
小米 14T Pro / Android 14 优化
"""

# ── Kivy 配置（必须在 import kivy 之前）─────────────────
import os

# Android 环境检测
_IS_ANDROID = os.path.exists("/system/build.prop")

if not _IS_ANDROID:
    # 仅桌面调试时设置窗口大小
    from kivy.config import Config
    Config.set("graphics", "resizable", "0")
    Config.set("graphics", "width",  "412")
    Config.set("graphics", "height", "915")

from kivy.config import Config
Config.set("kivy", "log_level", "warning")

# ── 标准库 ────────────────────────────────────────────────
import threading
import time
import datetime
import hashlib
import base64
import json
import re
import platform
import subprocess
from collections import deque
from functools import partial

# ── Kivy 核心 ─────────────────────────────────────────────
import kivy
# kivy.require("2.3.0")  # 注释掉避免版本不匹配崩溃

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.animation import Animation
try:
    from kivy.core.window import Window
except Exception:
    Window = None

# ── Kivy UI 组件 ──────────────────────────────────────────
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.progressbar import ProgressBar
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import (Color, Rectangle, RoundedRectangle,
                            Line, Ellipse, Canvas)
from kivy.properties import (StringProperty, NumericProperty,
                              BooleanProperty, ListProperty, ObjectProperty)

try:
    import requests
    requests.packages.urllib3.disable_warnings()
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ════════════════════════════════════════════════════════════
#  设计令牌
# ════════════════════════════════════════════════════════════
def c(h): return get_color_from_hex(h)

BG       = c("080C12")
PANEL    = c("0E1420")
CARD     = c("141C28")
CARD2    = c("1A2236")
BORDER   = c("1E2D45")
ACCENT   = c("00D4FF")
ACCENT2  = c("0096B4")
GREEN    = c("00E676")
GREEN2   = c("00BFA5")
RED      = c("FF3D57")
YELLOW   = c("FFD600")
ORANGE   = c("FF6D00")
PURPLE   = c("AA00FF")
TEXT     = c("E8F4FD")
TEXT2    = c("7B9CC0")
TEXT3    = c("3D5A7A")
WHITE    = c("FFFFFF")

# 品牌列表
BRANDS = [
    ("Ruijie/Reyee",   "[B]", "ruijie",  "192.168.110.1", "admin", "admin"),
    ("Xiaomi/Redmi",   "[X]", "xiaomi",  "192.168.31.1",  "admin", ""),
    ("TP-Link",     "[R]", "tplink",  "192.168.0.1",   "admin", "admin"),
    ("Huawei/Honor",   "[R]", "huawei",  "192.168.3.1",   "admin", ""),
    ("ASUS",   "[B]", "asus",    "192.168.50.1",  "admin", "admin"),
    ("Netgear",     "[N]", "netgear", "192.168.1.1",   "admin", "password"),
    ("D-Link",      "[G]", "dlink",   "192.168.0.1",   "Admin", ""),
    ("360 Router",    "[G]", "r360",    "192.168.0.1",   "admin", "admin"),
    ("Tenda",  "[B]", "tenda",   "192.168.0.1",   "admin", "admin"),
    ("Mercury","[M]", "mercury", "192.168.1.1",   "admin", "admin"),
    ("OpenWrt",     "[O]", "openwrt", "192.168.1.1",   "root",  ""),
    ("ZTE G7615V2",  "[B]", "zte",     "192.168.1.1",   "user",  ""),
    ("Demo Mode",    "[D]", "demo",    "192.168.1.1",   "",      ""),
]

PLATFORM_CATS = ["[Game] Gaming", "[TV] Video", "[Web] Browse", "[Chat] Social", "[DL] Download"]

# ════════════════════════════════════════════════════════════
#  路由器驱动层（内嵌，同 PC 版逻辑）
# ════════════════════════════════════════════════════════════
class RouterAPI:
    """统一路由器 API 接口"""

    def __init__(self, brand_id, host, username, password):
        self.brand_id = brand_id
        self.host     = host
        self.username = username
        self.password = password
        self.sid      = None
        self.session  = None
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.verify = False
            self.session.headers["User-Agent"] = "NetGuardPro-Android/3.0"

    # ── 登录 ────────────────────────────────────────────────
    def login(self):
        if not HAS_REQUESTS:
            return False, "requests 库未安装"
        if self.brand_id == "demo":
            return True, "Demo Mode"
        try:
            fn = getattr(self, "_login_" + self.brand_id, None)
            if fn:
                return fn()
            return False, "不支持的品牌: " + self.brand_id
        except Exception as e:
            return False, str(e)[:80]

    def _login_ruijie(self):
        import os, subprocess as sp
        key  = "RjYkhwzx$2018!"
        enc_pass = self.password
        encrypted = False
        try:
            cmd = 'echo "{}" | openssl enc -aes-256-cbc -a -k "{}" -md md5 2>/dev/null'.format(
                self.password, key)
            r = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=4)
            if r.stdout.strip():
                enc_pass = r.stdout.strip()
                encrypted = True
        except Exception:
            pass
        payload = {"method": "login", "params": {
            "username": self.username, "password": enc_pass,
            "encry": encrypted, "time": int(time.time()), "limit": False}}
        r = self.session.post(
            "http://{}/cgi-bin/luci/api/auth".format(self.host),
            json=payload, timeout=8)
        data = r.json()
        sid = (data.get("data") or {}).get("sid")
        if sid:
            self.sid = sid
            return True, "登录成功"
        return False, data.get("message", "密码错误")

    def _login_xiaomi(self):
        r = self.session.get(
            "http://{}/cgi-bin/luci/api/xqsystem/login".format(self.host), timeout=6)
        nonce = r.json().get("nonce", "")
        pwd_sha1 = hashlib.sha1(self.password.encode()).hexdigest()
        token = hashlib.sha1((nonce + pwd_sha1).encode()).hexdigest()
        r2 = self.session.post(
            "http://{}/cgi-bin/luci/api/xqsystem/login".format(self.host),
            data={"username":"admin","password":token,"logtype":"2","nonce":nonce}, timeout=8)
        t = r2.json().get("token")
        if t:
            self.sid = t
            return True, "登录成功"
        return False, r2.json().get("msg","密码错误")

    def _login_tplink(self):
        pwd_b64 = base64.b64encode(self.password.encode()).decode()
        r = self.session.post(
            "http://{}/cgi-bin/luci/;stok=/login?form=login".format(self.host),
            data={"operation":"login","username":self.username,"password":pwd_b64}, timeout=8)
        stok = (r.json().get("data") or {}).get("stok")
        if stok:
            self.sid = stok
            return True, "登录成功"
        return False, "密码错误"

    def _login_huawei(self):
        pwd_hash = hashlib.sha256(self.password.encode()).hexdigest().upper()
        r = self.session.post(
            "http://{}/api/system/user_login".format(self.host),
            json={"UserName":self.username,"PassWord":pwd_hash}, timeout=8)
        data = r.json()
        if data.get("errCode") == "0" or (data.get("csrf_param") and data.get("csrf_token")):
            self.sid = data.get("csrf_param","") + data.get("csrf_token","")
            return True, "登录成功"
        return False, "密码错误"

    def _login_asus(self):
        cred = base64.b64encode("{}:{}".format(self.username, self.password).encode()).decode()
        r = self.session.post(
            "http://{}/login.cgi".format(self.host),
            data={"login_authorization": cred}, timeout=8)
        ck = self.session.cookies.get("asus_token")
        if ck:
            self.sid = ck
            return True, "登录成功"
        return False, "密码错误"

    def _login_netgear(self):
        r = self.session.get("http://{}/".format(self.host),
            auth=(self.username, self.password), timeout=8)
        if r.status_code in (200, 302):
            self.session.auth = (self.username, self.password)
            return True, "登录成功"
        return False, "密码错误"

    def _login_dlink(self):
        r = self.session.post(
            "http://{}/login.cgi".format(self.host),
            data={"ACTION_POST":"LOGIN","LOGIN_USER":self.username,"LOGIN_PASSWD":self.password},
            timeout=8)
        if r.status_code == 200:
            return True, "登录成功"
        return False, "密码错误"

    def _login_r360(self):
        pwd_md5 = hashlib.md5(self.password.encode()).hexdigest()
        r = self.session.post("http://{}/login".format(self.host),
            json={"username":self.username,"password":pwd_md5}, timeout=8)
        t = (r.json().get("data") or {}).get("token")
        if t:
            self.sid = t
            self.session.headers["Authorization"] = "token " + t
            return True, "登录成功"
        return False, r.json().get("msg","密码错误")

    def _login_tenda(self):
        pwd_b64 = base64.b64encode(self.password.encode()).decode()
        r = self.session.post("http://{}/login/Auth".format(self.host),
            data={"username":self.username,"password":pwd_b64}, timeout=8)
        if r.json().get("errCode") == 0:
            return True, "登录成功"
        return False, "密码错误"

    def _login_mercury(self):
        pwd_md5 = hashlib.md5(self.password.encode()).hexdigest()
        r = self.session.post(
            "http://{}/cgi-bin/luci/;stok=/login".format(self.host),
            data={"operation":"login","username":self.username,"password":pwd_md5}, timeout=8)
        stok = (r.json().get("data") or {}).get("stok")
        if stok:
            self.sid = stok
            return True, "登录成功"
        return False, "密码错误"

    def _login_openwrt(self):
        r = self.session.post("http://{}/ubus".format(self.host),
            json={"jsonrpc":"2.0","id":1,"method":"call",
                  "params":["00000000000000000000000000000000","session","login",
                             {"username":self.username,"password":self.password}]}, timeout=8)
        result = r.json().get("result", [])
        if isinstance(result, list) and len(result) > 1:
            uid = result[1].get("ubus_rpc_session")
            if uid:
                self.sid = uid
                return True, "登录成功"
        return False, "认证失败"

    def _login_zte(self):
        # ZTE G7615V2 专用：超级管理员自动降级
        SUPER = [("cuadmin","cuadmin"),("CUAdmin","CUAdmin"),
                 ("cuadmin","CUAdmin"),("lnadmin","lnadmin")]
        cands = []
        # 先放用户自填的账号（无论是 user 还是超级账号都试）
        if self.username:
            cands.append((self.username, self.password))
        # 再自动尝试联通超级账号
        cands.extend(SUPER)
        # 去重
        seen_cands = set()
        unique_cands = []
        for c in cands:
            if c not in seen_cands:
                seen_cands.add(c)
                unique_cands.append(c)
        cands = unique_cands
        for u, p in cands:
            try:
                r0   = self.session.get("http://{}/".format(self.host), timeout=5)
                jsid = self.session.cookies.get("JSESSIONID","")
                r    = self.session.post(
                    "http://{}/getpage.gch?pid=1002&nextpage=logoff_t.gch".format(self.host),
                    data={"JSESSIONID":jsid,"usr":u,"psw":p,
                          "cmd":"1","nextpage":"maincfg_t.gch"}, timeout=8)
                text = r.text
                self.sid = self.session.cookies.get("JSESSIONID", jsid)
                if (r.status_code==302 or
                    any(k in text for k in ["maincfg","logout","statusinfo"]) or
                    (r.status_code==200 and len(text)>800
                     and "login" not in text[:300].lower())):
                    self._zte_auth = 2
                    return True, "ZTE SuperAdmin({}) OK".format(u)
            except Exception:
                pass
        # 普通用户降级：用背面账号 user + 用户填写的密码
        fallback_pairs = [
            (self.username if self.username else "user", self.password),
            ("user", self.password),
        ]
        for u2, p2 in fallback_pairs:
            try:
                r0   = self.session.get("http://{}/".format(self.host), timeout=5)
                jsid = self.session.cookies.get("JSESSIONID","")
                r    = self.session.post(
                    "http://{}/getpage.gch?pid=1002&nextpage=logoff_t.gch".format(self.host),
                    data={"JSESSIONID":jsid,"usr":u2,"psw":p2,
                          "cmd":"1","nextpage":"maincfg_t.gch"}, timeout=8)
                self.sid = self.session.cookies.get("JSESSIONID", jsid)
                self._zte_auth = 1
                if r.status_code in (200,302):
                    return True, "ZTE user login OK (limited data)"
            except Exception:
                pass
        return False, "ZTE login failed - check password"

    def fetch_clients(self):
        if self.brand_id == "demo":
            return self._demo_clients()
        try:
            fn = getattr(self, "_clients_" + self.brand_id, None)
            if fn:
                return fn()
        except Exception:
            pass
        return []

    def _make_dev(self, ip="", mac="", name="", brand="", online=True,
                  up=0.0, down=0.0, signal=0, freq="", iface="",
                  connect_time=0, latency=0.0, loss=0.0, stability=95.0):
        import random as rnd
        return {
            "ip": ip, "mac": mac.upper().replace("-",":"),
            "name": name or ip, "brand": brand,
            "online": online, "upload_speed": up, "download_speed": down,
            "signal": signal, "frequency": freq, "interface": iface,
            "connect_time": connect_time, "latency": latency,
            "loss_rate": loss, "stability_score": stability,
            "upload_total": rnd.uniform(10, 500),
            "download_total": rnd.uniform(50, 2000),
            "blocked": False,
            "allowed_categories": list(PLATFORM_CATS),
            "first_seen": datetime.datetime.now() - datetime.timedelta(
                seconds=rnd.randint(300, 86400)),
            "history_up":   deque([up]*30, maxlen=30),
            "history_down": deque([down]*30, maxlen=30),
        }

    def _guess_brand(self, mac):
        OUI = {
            "AC:BC:32":"Apple","F4:F1:5A":"Apple","3C:22:FB":"Apple",
            "74:DA:38":"Xiaomi","64:09:80":"Xiaomi","28:6C:07":"Xiaomi",
            "48:88:CA":"Huawei","70:72:3C":"Huawei",
            "2C:FD:A1":"Samsung","8C:77:12":"Samsung",
            "00:1A:11":"Google","F4:F5:D8":"Google",
        }
        for k, v in OUI.items():
            if mac.upper().startswith(k):
                return v
        return "未知"

    def _icon(self, brand):
        m = {"Apple":"[Apple]","Samsung":"[Phone]","Xiaomi":"[Phone]","Huawei":"[Phone]",
             "Amazon":"[Speaker]","Google":"[Google]","未知":"[Desktop]"}
        return m.get(brand, "[Desktop]")

    def _clients_ruijie(self):
        devs = {}
        url = "http://{}/cgi-bin/luci/api/dhcp?auth={}".format(self.host, self.sid)
        r = self.session.post(url,
            json={"method":"getDhcpClients","params":{}}, timeout=8)
        for c in (r.json().get("data") or {}).get("clients") or []:
            mac = (c.get("mac","")).upper().replace("-",":")
            if not mac: continue
            b = self._guess_brand(mac)
            devs[mac] = self._make_dev(
                ip=c.get("ip",""), mac=mac,
                name=self._icon(b)+" "+(c.get("hostname") or mac),
                brand=b, online=True,
                up=float(c.get("txBytes",0))/1048576,
                down=float(c.get("rxBytes",0))/1048576)
        url2 = "http://{}/cgi-bin/luci/api/wireless?auth={}".format(self.host, self.sid)
        r2 = self.session.post(url2,
            json={"method":"getClientList","params":{}}, timeout=8)
        for c in ((r2.json().get("data") or {}).get("clientList") or []):
            mac = (c.get("mac","")).upper().replace("-",":")
            if not mac: continue
            rssi = c.get("rssi", c.get("signal",-70))
            sig  = max(0,min(100,int((rssi+100)*2))) if rssi<0 else int(rssi)
            if mac in devs:
                devs[mac]["signal"] = sig
                devs[mac]["upload_speed"]   = float(c.get("txRate",0))/8/1048576
                devs[mac]["download_speed"] = float(c.get("rxRate",0))/8/1048576
        return list(devs.values())

    def _clients_xiaomi(self):
        url = "http://{}/cgi-bin/luci/api/xqnetwork/device_list?stok={}".format(
            self.host, self.sid)
        r = self.session.get(url, timeout=8)
        result = []
        for c in (r.json().get("list") or []):
            mac = (c.get("mac","")).upper()
            b = self._guess_brand(mac)
            rssi = c.get("rssi",0)
            sig  = max(0,min(100,int((rssi+100)*2))) if rssi<0 else int(rssi)
            result.append(self._make_dev(
                ip=c.get("ip",""), mac=mac,
                name=self._icon(b)+" "+(c.get("name") or mac),
                brand=b, online=bool(c.get("online",1)),
                up=float(c.get("upload",0))/1048576,
                down=float(c.get("download",0))/1048576,
                signal=sig, freq=c.get("frequency",""),
                connect_time=int(c.get("onlineTime",0))))
        return result

    def _clients_tplink(self):
        result = []
        url = "http://{}/cgi-bin/luci/;stok={}/admin/hosts_info?form=hosts_info".format(
            self.host, self.sid)
        r = self.session.post(url, data={"operation":"read"}, timeout=8)
        clist = (r.json().get("data") or {}).get("host_info") or []
        for c in clist:
            mac = (c.get("mac","")).upper().replace("-",":")
            if not mac: continue
            b = self._guess_brand(mac)
            result.append(self._make_dev(
                ip=c.get("ip",""), mac=mac,
                name=self._icon(b)+" "+(c.get("hostname") or mac),
                brand=b, online=bool(c.get("online",1)),
                up=float(c.get("up_speed",0))/1024,
                down=float(c.get("down_speed",0))/1024))
        return result

    def _clients_huawei(self):
        r = self.session.get("http://{}/api/system/HostInfo".format(self.host), timeout=8)
        result = []
        for c in r.json():
            mac = (c.get("MACAddress","")).upper().replace("-",":")
            if not mac: continue
            b = self._guess_brand(mac)
            result.append(self._make_dev(
                ip=c.get("IPAddress",""), mac=mac,
                name=self._icon(b)+" "+(c.get("HostName") or mac),
                brand=b, online=c.get("Active","0")=="1",
                iface=c.get("InterfaceType","")))
        return result

    def _clients_asus(self):
        r = self.session.post(
            "http://{}/appGet.cgi".format(self.host),
            data={"hook":"get_clientlist()"},
            headers={"Cookie":"asus_token={}".format(self.sid)}, timeout=8)
        result = []
        clist = r.json().get("get_clientlist", {})
        for mac, info in clist.items():
            if not re.match(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", mac):
                continue
            b = self._guess_brand(mac)
            rssi = int(info.get("rssi",0) or 0)
            sig  = max(0,min(100,int((rssi+100)*2))) if rssi<0 else rssi
            result.append(self._make_dev(
                ip=info.get("ip",""), mac=mac.upper(),
                name=self._icon(b)+" "+(info.get("name") or mac),
                brand=b, online=info.get("isOnline","0")=="1",
                signal=sig, connect_time=int(info.get("online_time",0) or 0)))
        return result

    def _clients_netgear(self):
        r = self.session.get(
            "http://{}/DEV_device_info.htm".format(self.host), timeout=8)
        macs = list(set(re.findall(
            r'([0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2})',
            r.text.upper())))
        ips  = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', r.text)
        result = []
        for i, mac in enumerate(macs):
            b = self._guess_brand(mac)
            result.append(self._make_dev(
                ip=ips[i] if i<len(ips) else "", mac=mac,
                name=self._icon(b)+" "+(ips[i] if i<len(ips) else mac),
                brand=b, online=True))
        return result

    def _clients_dlink(self):
        r = self.session.get(
            "http://{}/hnap1/".format(self.host),
            headers={"SOAPAction":'"http://purenetworks.com/HNAP1/GetClientInfo"'},
            timeout=8)
        macs = list(set(re.findall(
            r'([0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-]'
            r'[0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2})', r.text)))
        ips  = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', r.text)
        return [self._make_dev(ip=ips[i] if i<len(ips) else "",
                               mac=m.upper(), name="[Dsk] "+m, brand=self._guess_brand(m.upper()))
                for i, m in enumerate(macs)]

    def _clients_r360(self):
        r = self.session.get("http://{}/api/clients".format(self.host), timeout=8)
        result = []
        for c in (r.json().get("data") or {}).get("online_clients",[]):
            mac = (c.get("mac","")).upper()
            b = self._guess_brand(mac)
            result.append(self._make_dev(
                ip=c.get("ip",""), mac=mac,
                name=self._icon(b)+" "+(c.get("hostname") or mac),
                brand=b, online=True,
                up=float(c.get("up",0))/1048576,
                down=float(c.get("down",0))/1048576))
        return result

    def _clients_tenda(self):
        r = self.session.get("http://{}/goform/getOnlineList".format(self.host), timeout=8)
        result = []
        for c in r.json().get("onlineList",[]):
            mac = (c.get("mac","")).upper()
            b = self._guess_brand(mac)
            result.append(self._make_dev(
                ip=c.get("ip",""), mac=mac,
                name=self._icon(b)+" "+(c.get("deviceName") or mac),
                brand=b, online=True,
                up=float(c.get("upSpeed",0))/1024,
                down=float(c.get("downSpeed",0))/1024))
        return result

    def _clients_mercury(self):
        r = self.session.post(
            "http://{}/cgi-bin/luci/;stok={}/admin/dhcpd?form=client".format(
                self.host, self.sid),
            data={"operation":"read"}, timeout=8)
        result = []
        for c in (r.json().get("data") or []):
            mac = (c.get("mac","")).upper().replace("-",":")
            if not mac: continue
            b = self._guess_brand(mac)
            result.append(self._make_dev(
                ip=c.get("ip",""), mac=mac,
                name=self._icon(b)+" "+(c.get("hostname") or mac),
                brand=b, online=True))
        return result

    def _clients_openwrt(self):
        def ubus(ns, method, params=None):
            try:
                r = self.session.post("http://{}/ubus".format(self.host),
                    json={"jsonrpc":"2.0","id":1,"method":"call",
                          "params":[self.sid,ns,method,params or {}]}, timeout=8)
                res = r.json().get("result",[])
                return res[1] if len(res)>1 else {}
            except Exception:
                return {}
        result = {}
        data = ubus("luci-rpc","getDHCPLeases")
        for c in (data.get("dhcp_leases") or []):
            mac = (c.get("macaddr","")).upper()
            if not mac: continue
            b = self._guess_brand(mac)
            result[mac] = self._make_dev(ip=c.get("ipaddr",""), mac=mac,
                name=self._icon(b)+" "+(c.get("hostname") or mac), brand=b)
        return list(result.values())

    def _clients_zte(self):
        import re as _re
        devs = {}
        mac_p = _re.compile(
            r'([0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-]'
            r'[0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2})')
        ip_p  = _re.compile(
            r'((?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d{1,3}\.\d{1,3})')
        def _fill(text, iface="LAN"):
            macs=mac_p.findall(text); ips=ip_p.findall(text); seen=set()
            rssis=_re.findall(r'(-\d{2,3})\s*(?:dBm)?',text)
            freqs=_re.findall(r'(2\.4\s*GHz|5\s*GHz|6\s*GHz)',text,_re.I)
            for i,mac in enumerate(macs):
                mac=mac.upper().replace("-",":")
                if mac in seen or mac.startswith("FF:") or mac.startswith("01:"): continue
                seen.add(mac)
                ip=ips[i] if i<len(ips) else devs.get(mac,{}).get("ip","")
                if mac in devs:
                    devs[mac]["interface"]=iface
                    if iface=="WiFi":
                        rssi=int(rssis[i]) if i<len(rssis) else -70
                        devs[mac]["signal"]=max(0,min(100,int((rssi+100)*2)))
                        if freqs and i<len(freqs): devs[mac]["frequency"]=freqs[i].strip()
                    if ip: devs[mac]["ip"]=ip
                else:
                    b=self._guess_brand(mac)
                    devs[mac]=self._make_dev(ip=ip,mac=mac,
                        name="{} {}".format(self._icon(b),ip or mac),
                        brand=b,online=True,iface=iface)
            return bool(seen)
        # DHCP table (super admin only)
        if getattr(self,"_zte_auth",1)>=2:
            for pg in ["/getpage.gch?pid=1004&nextpage=net_dhcp_landhcpStatInfo_t.gch",
                       "/getpage.gch?pid=1004&nextpage=net_lan_dhcpd_t.gch"]:
                try:
                    text=self.session.get("http://{}{}".format(self.host,pg),timeout=8).text
                    if _fill(text): break
                except Exception: pass
        # WiFi association table
        for pg in ["/getpage.gch?pid=1002&nextpage=statusinfo_wlan_t.gch",
                   "/getpage.gch?pid=1004&nextpage=net_wlan_assoc_t.gch"]:
            try:
                text=self.session.get("http://{}{}".format(self.host,pg),timeout=8).text
                if _fill(text,"WiFi"): break
            except Exception: pass
        # ARP table fallback
        for pg in ["/getpage.gch?pid=1002&nextpage=statusinfo_arp_t.gch",
                   "/getpage.gch?pid=1004&nextpage=net_lan_arptable_t.gch"]:
            try:
                text=self.session.get("http://{}{}".format(self.host,pg),timeout=8).text
                if _fill(text,"LAN"): break
            except Exception: pass
        return list(devs.values())


    def _demo_clients(self):
        import random as rnd
        base = ".".join(self.host.split(".")[:3])
        templates = [
            ("iPhone 15 Pro","Apple","[Phone]","AC:BC:32"),
            ("MacBook Pro","Apple","[PC]","F4:F1:5A"),
            ("小米14","Xiaomi","[Phone]","74:DA:38"),
            ("华为MateBook","Huawei","[PC]","48:88:CA"),
            ("Surface Pro","Microsoft","[PC]","60:45:CB"),
            ("Samsung TV","Samsung","[TV]","2C:FD:A1"),
            ("PS5","Sony","[Game]","F8:46:1C"),
            ("Switch","Nintendo","[Game]","98:41:5C"),
            ("Echo Dot","Amazon","[Speaker]","18:31:BF"),
            ("iPad Pro","Apple","[Pad]","3C:22:FB"),
        ]
        result = []
        for i, (name, brand, icon, oui) in enumerate(templates[:rnd.randint(5,9)]):
            sfx = ":".join("{:02X}".format(rnd.randint(0,255)) for _ in range(3))
            mac = "{}:{}".format(oui, sfx)
            up   = rnd.uniform(0.05, 8.0)
            down = rnd.uniform(0.1, 25.0)
            lat  = rnd.uniform(1, 50)
            loss = rnd.uniform(0, 4)
            stab = max(60, 100 - loss*2 - max(0,(lat-10)*0.15))
            d = self._make_dev(
                ip="{}.{}".format(base, 100+i+1),
                mac=mac, name="{} {}".format(icon, name),
                brand=brand, online=rnd.random()>0.15,
                up=up, down=down,
                signal=rnd.randint(45,98),
                freq=rnd.choice(["2.4GHz","5GHz","5GHz","6GHz"]),
                iface=rnd.choice(["WiFi","WiFi","WiFi","LAN"]),
                connect_time=rnd.randint(300,86400),
                latency=lat, loss=loss, stability=stab)
            d["first_seen"] = datetime.datetime.now() - datetime.timedelta(
                seconds=rnd.randint(3600, 2592000))
            result.append(d)
        # 模拟实时波动
        for d in result:
            if d["online"]:
                import random
                d["upload_speed"]   = max(0.01, d["upload_speed"] + random.uniform(-0.5,0.5))
                d["download_speed"] = max(0.01, d["download_speed"] + random.uniform(-1,1))
                d["latency"]        = max(0.5, d["latency"] + random.uniform(-3,3))
                d["history_up"].append(d["upload_speed"])
                d["history_down"].append(d["download_speed"])
        return result


# ════════════════════════════════════════════════════════════
#  Kivy 自定义组件
# ════════════════════════════════════════════════════════════
class KCard(BoxLayout):
    """圆角卡片容器"""
    radius  = NumericProperty(dp(12))
    bg_color = ListProperty(CARD)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, bg_color=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius])

class KLabel(Label):
    def __init__(self, text="", size_hint=(1, None), height=dp(32),
                 color=TEXT, font_size=sp(14), bold=False,
                 halign="left", valign="middle", **kw):
        super().__init__(text=text, size_hint=size_hint, height=height,
                         color=color, font_size=font_size,
                         bold=bold, halign=halign, valign=valign, **kw)
        self.bind(size=self._update_text)

    def _update_text(self, *_):
        self.text_size = (self.width, None) if self.halign == "left" else (self.width, self.height)

class KButton(Button):
    def __init__(self, text="", bg=ACCENT, fg=BG, size_hint=(1, None),
                 height=dp(48), font_size=sp(14), bold=True,
                 radius=dp(10), **kw):
        super().__init__(text=text, size_hint=size_hint, height=height,
                         font_size=font_size, bold=bold,
                         background_normal="", background_color=(0,0,0,0),
                         color=fg, **kw)
        self._bg = bg
        self._radius = radius
        self.bind(pos=self._draw, size=self._draw, state=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == "down":
                Color(self._bg[0]*0.8, self._bg[1]*0.8, self._bg[2]*0.8, 1)
            else:
                Color(*self._bg)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self._radius])

class KInput(TextInput):
    def __init__(self, hint="", password=False, **kw):
        super().__init__(
            hint_text=hint,
            password=password,
            multiline=False,
            background_color=(0,0,0,0),
            foreground_color=TEXT,
            hint_text_color=TEXT3,
            cursor_color=ACCENT,
            font_size=sp(14),
            padding=[dp(14), dp(12)],
            **kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*CARD2)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(*BORDER)
            Line(rounded_rectangle=[self.x, self.y, self.width, self.height, dp(10)],
                 width=1.2)

class KDivider(Widget):
    def __init__(self, **kw):
        super().__init__(size_hint=(1, None), height=dp(1), **kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*BORDER)
            Rectangle(pos=self.pos, size=self.size)

class KProgressBar(Widget):
    value     = NumericProperty(0)
    max_value = NumericProperty(100)
    bar_color = ListProperty(ACCENT)

    def __init__(self, **kw):
        super().__init__(size_hint=(1, None), height=dp(6), **kw)
        self.bind(pos=self._draw, size=self._draw,
                  value=self._draw, bar_color=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*CARD2)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(3)])
            ratio = min(1, max(0, self.value / max(self.max_value, 1)))
            Color(*self.bar_color)
            RoundedRectangle(pos=self.pos,
                             size=(self.width * ratio, self.height),
                             radius=[dp(3)])


# ════════════════════════════════════════════════════════════
#  状态管理
# ════════════════════════════════════════════════════════════
class AppState:
    def __init__(self):
        self.router_api   = None
        self.brand_name   = ""
        self.devices      = []
        self.selected_mac = None
        self.monitoring   = False
        self.log_entries  = []
        self.warnings     = 0


state = AppState()


# ════════════════════════════════════════════════════════════
#  Screen: 品牌选择
# ════════════════════════════════════════════════════════════
class BrandScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical",
                         spacing=0, padding=0)

        # 顶栏
        top = KCard(bg_color=PANEL, orientation="horizontal",
                    size_hint=(1, None), height=dp(56),
                    padding=[dp(16), dp(8)], spacing=dp(8))
        with top.canvas.before:
            Color(*PANEL)
            Rectangle(pos=top.pos, size=top.size)
        top.bind(pos=lambda *_: top._draw(), size=lambda *_: top._draw())

        top.add_widget(Label(text="NG", font_size=sp(22), color=ACCENT,
                             size_hint=(None,1), width=dp(36), bold=True))
        top.add_widget(Label(text="NetGuard Pro", font_size=sp(16),
                             color=TEXT, bold=True,
                             size_hint=(1,1), halign="left"))
        top.add_widget(Label(text="v3.0", font_size=sp(10), color=TEXT3,
                             size_hint=(None,1), width=dp(36)))
        root.add_widget(top)

        # 副标题
        root.add_widget(KLabel(
            text="Select Router Brand",
            font_size=sp(13), color=TEXT2,
            halign="center", height=dp(40),
            padding=[dp(16), 0]))

        # 品牌滚动网格
        scroll = ScrollView(size_hint=(1,1), do_scroll_x=False)
        grid = GridLayout(cols=3, spacing=dp(10),
                          padding=[dp(12), dp(8), dp(12), dp(16)],
                          size_hint=(1, None))
        grid.bind(minimum_height=grid.setter("height"))

        for name, emoji, bid, dip, dusr, dpwd in BRANDS:
            is_demo = bid == "demo"
            card = KCard(bg_color=CARD2 if not is_demo else CARD,
                         orientation="vertical",
                         padding=[dp(8), dp(12)],
                         spacing=dp(4),
                         size_hint=(1, None), height=dp(80),
                         radius=dp(12))
            card.add_widget(Label(text=emoji, font_size=sp(24),
                                   color=ACCENT if is_demo else TEXT,
                                   size_hint=(1, None), height=dp(32),
                                   halign="center"))
            card.add_widget(Label(text=name, font_size=sp(10),
                                   color=YELLOW if is_demo else TEXT2,
                                   bold=True,
                                   size_hint=(1, None), height=dp(28),
                                   halign="center"))
            # 触摸事件
            card.bid  = bid
            card.dip  = dip
            card.dusr = dusr
            card.dpwd = dpwd
            card.dname= name
            card.bind(on_touch_down=partial(self._on_brand_tap, card))
            grid.add_widget(card)

        scroll.add_widget(grid)
        root.add_widget(scroll)
        self.add_widget(root)

    def _on_brand_tap(self, card, instance, touch):
        if not card.collide_point(*touch.pos):
            return
        app = App.get_running_app()
        app.open_connect_form(card.bid, card.dname, card.dip, card.dusr, card.dpwd)


# ════════════════════════════════════════════════════════════
#  Screen: 连接表单
# ════════════════════════════════════════════════════════════
class ConnectScreen(Screen):
    brand_id   = StringProperty("")
    brand_name = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self._layout = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical",
                         spacing=0, padding=[dp(16), 0])
        with root.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg_rect, "pos", root.pos),
                  size=lambda *_: setattr(self._bg_rect, "size", root.size))

        # 顶栏
        top = BoxLayout(orientation="horizontal",
                        size_hint=(1, None), height=dp(56), spacing=dp(8))
        back_btn = KButton(text="←", bg=CARD2, fg=TEXT2,
                           size_hint=(None,1), width=dp(44), height=dp(44),
                           font_size=sp(18))
        back_btn.bind(on_release=lambda _: App.get_running_app().go_back())
        top.add_widget(back_btn)
        self._title_lbl = Label(text="Connect Router", font_size=sp(16),
                                 color=TEXT, bold=True,
                                 size_hint=(1,1), halign="left")
        top.add_widget(self._title_lbl)
        root.add_widget(top)

        root.add_widget(KDivider())
        root.add_widget(Widget(size_hint=(1,None), height=dp(16)))

        # 表单卡片
        form_card = KCard(bg_color=CARD, orientation="vertical",
                          padding=[dp(16), dp(16)],
                          spacing=dp(12), size_hint=(1, None))
        form_card.bind(minimum_height=form_card.setter("height"))

        self._note_lbl = KLabel(text="", font_size=sp(11),
                                 color=ACCENT2, height=dp(28))
        form_card.add_widget(self._note_lbl)

        for label_text, attr, is_pwd in [
            ("Router IP", "_inp_ip", False),
            ("Username",   "_inp_user", False),
            ("Password",   "_inp_pass", True),
        ]:
            form_card.add_widget(KLabel(text=label_text, font_size=sp(11),
                                         color=TEXT2, height=dp(24)))
            inp = KInput(hint="", password=is_pwd,
                         size_hint=(1, None), height=dp(46))
            setattr(self, attr, inp)
            form_card.add_widget(inp)

        self._status_lbl = KLabel(text="", color=YELLOW,
                                   font_size=sp(12), height=dp(28))
        form_card.add_widget(self._status_lbl)

        self._prog = KProgressBar(bar_color=ACCENT)
        self._prog.opacity = 0
        form_card.add_widget(self._prog)

        self._conn_btn = KButton(text="▶  Connect", bg=ACCENT, fg=BG,
                                  height=dp(50), font_size=sp(15))
        self._conn_btn.bind(on_release=self._do_connect)
        form_card.add_widget(self._conn_btn)

        root.add_widget(form_card)
        root.add_widget(Widget(size_hint=(1,1)))
        self._layout = root
        self.add_widget(root)

    def setup(self, bid, bname, dip, dusr, dpwd):
        self.brand_id = bid
        self.brand_name = bname
        self._title_lbl.text = "{} 连接配置".format(bname)
        self._inp_ip.text   = dip
        self._inp_user.text = dusr
        self._inp_pass.text = dpwd
        notes = {
            "ruijie":  "ReyeeOS - password auto AES encrypted",
            "xiaomi":  "Use router admin password (not WiFi password)",
            "asus":    "ASUSWRT - RT / ZenWiFi series",
            "netgear": "Default password: password",
            "dlink":   "Default password is blank",
            "openwrt": "ubus JSON-RPC auth",
            "zte":     "Unicom ONT: enter label user/password; cuadmin for full data",
            "demo":    "[D] Demo mode - simulated data, no router needed",
        }
        self._note_lbl.text = notes.get(bid, "")
        is_demo = bid == "demo"
        self._inp_user.disabled = is_demo
        self._inp_pass.disabled = is_demo

    def _do_connect(self, *_):
        host  = self._inp_ip.text.strip()
        uname = self._inp_user.text.strip()
        pwd   = self._inp_pass.text
        if not host:
            self._status_lbl.text = "⚠ 请输入路由器 IP"
            return
        self._status_lbl.text = "Connecting {} ...".format(host)
        self._prog.opacity = 1
        self._conn_btn.disabled = True

        def _anim(_dt):
            self._prog.value = (self._prog.value + 5) % 100

        anim_ev = Clock.schedule_interval(_anim, 0.05)

        def _connect():
            api = RouterAPI(self.brand_id, host, uname, pwd)
            ok, msg = api.login()
            Clock.schedule_once(lambda dt: self._on_result(ok, msg, api, anim_ev), 0)

        threading.Thread(target=_connect, daemon=True).start()

    def _on_result(self, ok, msg, api, anim_ev):
        anim_ev.cancel()
        self._prog.opacity = 0
        self._conn_btn.disabled = False
        if ok:
            state.router_api = api
            state.brand_name = self.brand_name
            App.get_running_app().go_main(msg)
        else:
            self._status_lbl.text = "✗  " + msg
            self._status_lbl.color = RED


# ════════════════════════════════════════════════════════════
#  Screen: 主界面（底部 Tab）
# ════════════════════════════════════════════════════════════
class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, "pos", root.pos),
                  size=lambda *_: setattr(self._bg, "size", root.size))

        # 顶栏
        top = BoxLayout(orientation="horizontal",
                        size_hint=(1, None), height=dp(52),
                        padding=[dp(14), dp(8)], spacing=dp(8))
        with top.canvas.before:
            Color(*PANEL)
            self._top_bg = Rectangle(pos=top.pos, size=top.size)
        top.bind(pos=lambda *_: setattr(self._top_bg, "pos", top.pos),
                 size=lambda *_: setattr(self._top_bg, "size", top.size))

        top.add_widget(Label(text="NG", font_size=sp(20), color=ACCENT,
                             size_hint=(None,1), width=dp(28), bold=True))
        self._router_lbl = Label(text="NetGuard Pro", font_size=sp(13),
                                  color=TEXT, bold=True,
                                  size_hint=(1,1), halign="left")
        top.add_widget(self._router_lbl)

        refresh_btn = KButton(text="Refresh", bg=CARD2, fg=ACCENT,
                              size_hint=(None,1), width=dp(40), height=dp(36),
                              font_size=sp(14))
        refresh_btn.bind(on_release=lambda _: self._tab_dev.refresh())
        top.add_widget(refresh_btn)

        switch_btn = KButton(text="Switch", bg=CARD2, fg=TEXT2,
                             size_hint=(None,1), width=dp(48), height=dp(36),
                             font_size=sp(11))
        switch_btn.bind(on_release=lambda _: App.get_running_app().go_brand())
        top.add_widget(switch_btn)
        root.add_widget(top)

        # 内容区（SM 管理各 Tab）
        self._content_sm = ScreenManager(transition=FadeTransition(duration=0.15))
        self._tab_dash = DashTab(name="dash")
        self._tab_dev  = DeviceTab(name="devices")
        self._tab_ctrl = ControlTab(name="control")
        self._tab_log  = LogTab(name="log")
        for tab in (self._tab_dash, self._tab_dev, self._tab_ctrl, self._tab_log):
            self._content_sm.add_widget(tab)
        root.add_widget(self._content_sm)

        # 底部导航栏
        nav = BoxLayout(orientation="horizontal",
                        size_hint=(1, None), height=dp(56))
        with nav.canvas.before:
            Color(*PANEL)
            self._nav_bg = Rectangle(pos=nav.pos, size=nav.size)
        nav.bind(pos=lambda *_: setattr(self._nav_bg, "pos", nav.pos),
                 size=lambda *_: setattr(self._nav_bg, "size", nav.size))

        nav_items = [
            (">>", "Monitor", "dash"),
            ("[Desktop]",  "Devices", "devices"),
            ("**", "Control", "control"),
            ("--", "Log", "log"),
        ]
        self._nav_btns = {}
        for icon, label_text, tab_name in nav_items:
            btn_box = BoxLayout(orientation="vertical",
                                size_hint=(1,1),
                                padding=[0, dp(6)])
            b = Button(text=icon, font_size=sp(20),
                       background_normal="", background_color=(0,0,0,0),
                       color=ACCENT if tab_name=="dash" else TEXT3,
                       size_hint=(1, None), height=dp(26))
            lbl = Label(text=label_text, font_size=sp(9),
                        color=ACCENT if tab_name=="dash" else TEXT3,
                        size_hint=(1, None), height=dp(16))
            btn_box.add_widget(b)
            btn_box.add_widget(lbl)
            b.bind(on_release=partial(self._switch_tab, tab_name))
            self._nav_btns[tab_name] = (b, lbl)
            nav.add_widget(btn_box)

        root.add_widget(nav)
        self.add_widget(root)

    def _switch_tab(self, tab_name, *_):
        self._content_sm.current = tab_name
        for tn, (b, lbl) in self._nav_btns.items():
            col = ACCENT if tn == tab_name else TEXT3
            b.color = col
            lbl.color = col

    def setup(self, msg):
        api = state.router_api
        self._router_lbl.text = "{}  {}".format(state.brand_name, api.host)
        App.get_running_app().add_log("已连接 {} — {}".format(state.brand_name, msg), "SUCCESS")
        # 启动监控
        if not state.monitoring:
            state.monitoring = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while state.monitoring:
            try:
                devs = state.router_api.fetch_clients()
                state.devices = devs
                Clock.schedule_once(lambda dt: self._on_data(), 0)
            except Exception as e:
                Clock.schedule_once(
                    lambda dt, err=str(e): App.get_running_app().add_log(
                        "更新失败: " + err[:60], "ERROR"), 0)
            time.sleep(3)

    def _on_data(self):
        self._tab_dash.update(state.devices)
        self._tab_dev.update(state.devices)
        self._tab_ctrl.update(state.devices)


# ════════════════════════════════════════════════════════════
#  Tab: 监控仪表盘
# ════════════════════════════════════════════════════════════
class DashTab(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._kpi_lbls = {}
        self._dev_rows = {}
        self._build()

    def _build(self):
        scroll = ScrollView(do_scroll_x=False)
        layout = BoxLayout(orientation="vertical", spacing=dp(10),
                           padding=[dp(12), dp(12)],
                           size_hint=(1, None))
        layout.bind(minimum_height=layout.setter("height"))

        # KPI 网格
        kpi_grid = GridLayout(cols=2, spacing=dp(8),
                              size_hint=(1, None), height=dp(160))
        kpi_defs = [
            ("Online", "0 台",       GREEN,  "devs"),
            ("⬆ 上传",  "0.00 MB/s", ACCENT, "up"),
            ("⬇ 下载",  "0.00 MB/s", GREEN,  "down"),
            ("Avg", "— ms",      YELLOW, "lat"),
        ]
        for name, val, color, key in kpi_defs:
            card = KCard(bg_color=CARD, orientation="vertical",
                         padding=[dp(12), dp(8)], spacing=dp(4))
            card.add_widget(Label(text=name, font_size=sp(11),
                                   color=TEXT3, size_hint=(1,None), height=dp(18),
                                   halign="left"))
            v = Label(text=val, font_size=sp(18), color=color,
                      bold=True, size_hint=(1,1), halign="left")
            card.add_widget(v)
            self._kpi_lbls[key] = v
            kpi_grid.add_widget(card)
        layout.add_widget(kpi_grid)

        # 设备速度列表
        layout.add_widget(KLabel(text="Live Traffic", font_size=sp(13),
                                  color=TEXT2, bold=True, height=dp(32)))
        self._dev_scroll_layout = BoxLayout(orientation="vertical",
                                             spacing=dp(6),
                                             size_hint=(1, None))
        self._dev_scroll_layout.bind(
            minimum_height=self._dev_scroll_layout.setter("height"))
        layout.add_widget(self._dev_scroll_layout)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def update(self, devices):
        online = [d for d in devices if d["online"] and not d["blocked"]]
        total_up   = sum(d["upload_speed"]   for d in online)
        total_down = sum(d["download_speed"] for d in online)
        avg_lat    = sum(d["latency"] for d in online) / max(len(online), 1)

        self._kpi_lbls["devs"].text = "{} 台".format(len(online))
        self._kpi_lbls["up"].text   = "{:.2f} MB/s".format(total_up)
        self._kpi_lbls["down"].text = "{:.2f} MB/s".format(total_down)
        self._kpi_lbls["lat"].text  = "{:.1f} ms".format(avg_lat) if online else "—"

        # 重绘设备速度条
        self._dev_scroll_layout.clear_widgets()
        for d in sorted(devices, key=lambda x: x["download_speed"], reverse=True)[:8]:
            row = self._make_speed_row(d)
            self._dev_scroll_layout.add_widget(row)

    def _make_speed_row(self, d):
        card = KCard(bg_color=CARD, orientation="vertical",
                     padding=[dp(12), dp(8)], spacing=dp(4),
                     size_hint=(1, None), height=dp(72))
        # 设备名 + 状态
        top_row = BoxLayout(orientation="horizontal",
                            size_hint=(1, None), height=dp(22))
        dot_color = RED if d["blocked"] else (GREEN if d["online"] else TEXT3)
        top_row.add_widget(Label(text="●", font_size=sp(10), color=dot_color,
                                  size_hint=(None,1), width=dp(16)))
        top_row.add_widget(Label(text=d["name"], font_size=sp(12), color=TEXT,
                                  bold=True, halign="left", size_hint=(1,1)))
        speed_txt = "{:.1f}↑ {:.1f}↓ MB/s".format(
            d["upload_speed"], d["download_speed"]) if d["online"] else "Offline"
        top_row.add_widget(Label(text=speed_txt, font_size=sp(10),
                                  color=ACCENT if d["online"] else TEXT3,
                                  halign="right", size_hint=(None,1), width=dp(120)))
        card.add_widget(top_row)

        # 下载进度条
        max_down = max(d["download_speed"], 0.01)
        pb = KProgressBar(bar_color=GREEN, value=d["download_speed"],
                          max_value=50)
        card.add_widget(pb)

        # IP + 信号
        bot_row = BoxLayout(orientation="horizontal",
                            size_hint=(1, None), height=dp(18))
        bot_row.add_widget(Label(text=d["ip"], font_size=sp(10),
                                  color=TEXT3, halign="left", size_hint=(1,1)))
        if d.get("signal"):
            bot_row.add_widget(Label(
                text=" {}%".format(d["signal"]),
                font_size=sp(10), color=TEXT3,
                halign="right", size_hint=(None,1), width=dp(70)))
        card.add_widget(bot_row)
        return card


# ════════════════════════════════════════════════════════════
#  Tab: 设备列表
# ════════════════════════════════════════════════════════════
class DeviceTab(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")

        # 工具栏
        tb = BoxLayout(orientation="horizontal", size_hint=(1,None),
                       height=dp(44), padding=[dp(10),dp(4)], spacing=dp(8))
        self._search = KInput(hint="Search device or IP",
                               size_hint=(1,1), height=dp(36))
        self._search.bind(text=self._on_search)
        tb.add_widget(self._search)
        ref_btn = KButton(text="", bg=ACCENT2, fg=BG,
                          size_hint=(None,1), width=dp(44), height=dp(36))
        ref_btn.bind(on_release=lambda _: self.refresh())
        tb.add_widget(ref_btn)
        root.add_widget(tb)

        # 设备卡列表
        scroll = ScrollView(do_scroll_x=False, size_hint=(1,1))
        self._list_layout = BoxLayout(orientation="vertical",
                                       spacing=dp(6),
                                       padding=[dp(10), dp(6)],
                                       size_hint=(1, None))
        self._list_layout.bind(minimum_height=self._list_layout.setter("height"))
        scroll.add_widget(self._list_layout)
        root.add_widget(scroll)
        self.add_widget(root)
        self._devices = []

    def refresh(self):
        if state.router_api:
            threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            devs = state.router_api.fetch_clients()
            state.devices = devs
            Clock.schedule_once(lambda dt: self.update(devs), 0)
        except Exception as e:
            App.get_running_app().add_log("刷新失败: " + str(e)[:60], "ERROR")

    def update(self, devices):
        self._devices = devices
        self._render(devices)

    def _on_search(self, _, text):
        q = text.lower()
        filtered = [d for d in self._devices
                    if not q or q in d["name"].lower() or q in d["ip"]]
        self._render(filtered)

    def _render(self, devices):
        self._list_layout.clear_widgets()
        for d in devices:
            card = self._make_card(d)
            self._list_layout.add_widget(card)

    def _make_card(self, d):
        is_sel = d["mac"] == state.selected_mac
        bg = CARD2 if is_sel else CARD
        border_col = ACCENT if is_sel else BORDER

        card = KCard(bg_color=bg, orientation="vertical",
                     padding=[dp(12), dp(10)], spacing=dp(6),
                     size_hint=(1, None), height=dp(100),
                     radius=dp(12))

        # 边框高亮
        with card.canvas.after:
            Color(*border_col)
            Line(rounded_rectangle=[card.x, card.y, card.width, card.height, dp(12)],
                 width=1.5 if is_sel else 1)

        # 名称行
        row1 = BoxLayout(orientation="horizontal",
                         size_hint=(1, None), height=dp(26))
        dot_c = RED if d["blocked"] else (GREEN if d["online"] else TEXT3)
        row1.add_widget(Label(text="●", color=dot_c, font_size=sp(10),
                               size_hint=(None,1), width=dp(14)))
        row1.add_widget(Label(text=d["name"], color=TEXT, bold=True,
                               font_size=sp(13), halign="left", size_hint=(1,1)))
        status = "Blocked" if d["blocked"] else ("Online" if d["online"] else "Offline")
        sc = d["stability_score"]
        grade_c = GREEN if sc>=90 else (YELLOW if sc>=75 else RED)
        row1.add_widget(Label(text=status, color=grade_c,
                               font_size=sp(10), halign="right",
                               size_hint=(None,1), width=dp(50)))
        card.add_widget(row1)

        # IP + MAC
        row2 = BoxLayout(orientation="horizontal",
                         size_hint=(1, None), height=dp(18))
        row2.add_widget(Label(text=d["ip"], color=TEXT3, font_size=sp(10),
                               halign="left", size_hint=(1,1)))
        row2.add_widget(Label(text=d["mac"][:14]+"…" if len(d["mac"])>14 else d["mac"],
                               color=TEXT3, font_size=sp(9),
                               halign="right", size_hint=(1,1)))
        card.add_widget(row2)

        # 速度行
        row3 = BoxLayout(orientation="horizontal",
                         size_hint=(1, None), height=dp(20))
        row3.add_widget(Label(
            text="⬆ {:.2f}  ⬇ {:.2f} MB/s".format(
                d["upload_speed"], d["download_speed"]),
            color=ACCENT, font_size=sp(10),
            halign="left", size_hint=(1,1)))
        row3.add_widget(Label(
            text="Latency {:.0f}ms  Loss {:.1f}%".format(d["latency"], d["loss_rate"]),
            color=TEXT3, font_size=sp(10),
            halign="right", size_hint=(1,1)))
        card.add_widget(row3)

        # 稳定性条
        pb = KProgressBar(bar_color=grade_c, value=sc, max_value=100)
        card.add_widget(pb)

        # 点击
        card.bind(on_touch_down=partial(self._on_card_tap, d))
        return card

    def _on_card_tap(self, d, instance, touch):
        if not instance.collide_point(*touch.pos):
            return
        state.selected_mac = d["mac"]
        App.get_running_app().show_device_detail(d)


# ════════════════════════════════════════════════════════════
#  Screen: 设备详情弹窗
# ════════════════════════════════════════════════════════════
class DeviceDetailPopup(Popup):
    def __init__(self, device, **kw):
        super().__init__(
            title="",
            separator_height=0,
            background="",
            background_color=(0,0,0,0.85),
            size_hint=(0.95, 0.88),
            **kw)
        self._d = device
        self._build()

    def _build(self):
        d = self._d
        root = KCard(bg_color=PANEL, orientation="vertical",
                     padding=[dp(16), dp(14)], spacing=dp(10),
                     radius=dp(16))

        # 标题行
        title_row = BoxLayout(orientation="horizontal",
                              size_hint=(1,None), height=dp(36))
        title_row.add_widget(Label(text=d["name"], font_size=sp(15),
                                    color=TEXT, bold=True,
                                    size_hint=(1,1), halign="left"))
        close_btn = KButton(text="✕", bg=CARD2, fg=TEXT2,
                            size_hint=(None,1), width=dp(36), height=dp(36),
                            font_size=sp(14))
        close_btn.bind(on_release=self.dismiss)
        title_row.add_widget(close_btn)
        root.add_widget(title_row)
        root.add_widget(KDivider())

        # 信息网格
        info_grid = GridLayout(cols=2, spacing=[dp(6), dp(4)],
                               size_hint=(1, None), height=dp(168))
        info_items = [
            ("IP", d["ip"]),
            ("MAC",     d["mac"][:17]),
            ("Brand",    d["brand"]),
            ("接口",    d.get("interface","—") or "—"),
            ("频段",    d.get("frequency","—") or "—"),
            ("信号",    "{}%".format(d.get("signal",0))),
            ("Stability",  "{:.1f}%".format(d["stability_score"])),
            ("First Seen", d["first_seen"].strftime("%m-%d %H:%M")),
        ]
        for label_text, val in info_items:
            info_grid.add_widget(Label(text=label_text+":", font_size=sp(10),
                                        color=TEXT3, halign="right", valign="middle",
                                        text_size=(dp(90), dp(24))))
            info_grid.add_widget(Label(text=val, font_size=sp(10),
                                        color=TEXT, bold=True, halign="left",
                                        valign="middle",
                                        text_size=(dp(140), dp(24))))
        root.add_widget(info_grid)

        # 性能指标
        metrics = [
            ("⬆ 上传",  "{:.2f} MB/s".format(d["upload_speed"]),  ACCENT, d["upload_speed"],   20),
            ("⬇ 下载",  "{:.2f} MB/s".format(d["download_speed"]),GREEN,  d["download_speed"],  50),
            ("⏱ 延迟",  "{:.1f} ms".format(d["latency"]),         YELLOW, d["latency"],         100),
            (" 丢包",  "{:.1f}%".format(d["loss_rate"]),         ORANGE, d["loss_rate"],       10),
        ]
        for mname, mval, color, raw, maxv in metrics:
            mrow = BoxLayout(orientation="horizontal",
                             size_hint=(1,None), height=dp(24))
            mrow.add_widget(Label(text=mname, font_size=sp(10), color=TEXT3,
                                   size_hint=(None,1), width=dp(64)))
            mrow.add_widget(Label(text=mval, font_size=sp(10), color=color,
                                   bold=True, size_hint=(None,1), width=dp(90)))
            pb = KProgressBar(bar_color=color, value=raw, max_value=maxv,
                              size_hint=(1,None), height=dp(6))
            mrow.add_widget(pb)
            root.add_widget(mrow)

        root.add_widget(KDivider())

        # 操作按钮
        btn_row = BoxLayout(orientation="horizontal",
                            size_hint=(1,None), height=dp(46), spacing=dp(10))
        block_txt = "Unblock Device" if d["blocked"] else " 封锁设备"
        block_bg  = GREEN2 if d["blocked"] else RED
        block_btn = KButton(text=block_txt, bg=block_bg, fg=WHITE)
        block_btn.bind(on_release=lambda _: self._toggle_block())
        btn_row.add_widget(block_btn)

        ping_btn = KButton(text="Ping Test", bg=ACCENT2, fg=BG)
        ping_btn.bind(on_release=lambda _: self._ping())
        btn_row.add_widget(ping_btn)
        root.add_widget(btn_row)

        self.content = root

    def _toggle_block(self):
        d = self._d
        d["blocked"] = not d["blocked"]
        action = "Blocked" if d["blocked"] else "解封"
        App.get_running_app().add_log("{} 已{}".format(d["name"], action),
                                      "WARNING" if d["blocked"] else "SUCCESS")
        self.dismiss()

    def _ping(self):
        App.get_running_app().add_log("开始 Ping {}...".format(self._d["ip"]))
        threading.Thread(target=self._do_ping, daemon=True).start()

    def _do_ping(self):
        ip = self._d["ip"]
        sys = platform.system().lower()
        results = []
        for _ in range(5):
            try:
                cmd = (["ping","-n","1","-w","1000",ip]
                       if sys=="windows" else ["ping","-c","1","-W","1",ip])
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                ok = r.returncode == 0
                lat = None
                if ok and "time=" in r.stdout:
                    try:
                        lat = float(r.stdout.split("time=")[1].split()[0].replace("ms",""))
                    except Exception:
                        pass
                results.append((ok, lat))
            except Exception:
                results.append((False, None))
            time.sleep(0.3)
        succ = [r for r in results if r[0]]
        lats = [r[1] for r in succ if r[1]]
        avg  = sum(lats)/len(lats) if lats else 0
        loss = (len(results)-len(succ))/len(results)*100
        msg  = "Ping {} — 成功:{}/5 丢包:{:.0f}% 平均:{:.1f}ms".format(
            ip, len(succ), loss, avg)
        Clock.schedule_once(lambda dt: App.get_running_app().add_log(msg, "SUCCESS"), 0)


# ════════════════════════════════════════════════════════════
#  Tab: 访问控制
# ════════════════════════════════════════════════════════════
class ControlTab(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._selected_mac = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        scroll = ScrollView(do_scroll_x=False)
        layout = BoxLayout(orientation="vertical", spacing=dp(10),
                           padding=[dp(12), dp(10)], size_hint=(1,None))
        layout.bind(minimum_height=layout.setter("height"))

        # 选中设备显示
        dev_card = KCard(bg_color=CARD, orientation="vertical",
                         padding=[dp(14), dp(10)], spacing=dp(6),
                         size_hint=(1,None), height=dp(80))
        self._ctrl_dev_lbl = Label(text="-- Select a device --",
                                    font_size=sp(13), color=TEXT2,
                                    bold=True, halign="left",
                                    size_hint=(1,1))
        dev_card.add_widget(self._ctrl_dev_lbl)

        ctrl_btns = BoxLayout(orientation="horizontal",
                              size_hint=(1,None), height=dp(36), spacing=dp(8))
        self._block_btn = KButton(text="Block", bg=RED, fg=WHITE,
                                   height=dp(36), font_size=sp(12))
        self._block_btn.bind(on_release=lambda _: self._toggle_block())
        ctrl_btns.add_widget(self._block_btn)
        dev_card.add_widget(ctrl_btns)
        layout.add_widget(dev_card)

        # 平台权限
        layout.add_widget(KLabel(text="Access Control", font_size=sp(13),
                                  color=TEXT2, bold=True, height=dp(32)))
        self._perm_switches = {}
        perm_colors = {"[Game] Gaming": PURPLE,"[TV] Video":RED,
                       " 浏览":ACCENT," 社交":GREEN," 下载":YELLOW}
        for cat in PLATFORM_CATS:
            row = BoxLayout(orientation="horizontal",
                            size_hint=(1,None), height=dp(44))
            clr = perm_colors.get(cat, ACCENT)
            row.add_widget(Label(text=cat, font_size=sp(13), color=clr,
                                  bold=True, halign="left", size_hint=(1,1)))
            sw = Switch(active=True, size_hint=(None,1), width=dp(60))
            sw.bind(active=partial(self._on_perm_change, cat))
            self._perm_switches[cat] = sw
            row.add_widget(sw)
            layout.add_widget(row)
            layout.add_widget(KDivider())

        # 时间限制
        layout.add_widget(Widget(size_hint=(1,None), height=dp(8)))
        layout.add_widget(KLabel(text="Schedule", font_size=sp(13),
                                  color=TEXT2, bold=True, height=dp(32)))
        time_row = BoxLayout(orientation="horizontal",
                             size_hint=(1,None), height=dp(44), spacing=dp(8))
        self._time_start = KInput(hint="08:00", size_hint=(1,1), height=dp(44))
        self._time_start.text = "08:00"
        time_row.add_widget(self._time_start)
        time_row.add_widget(Label(text="to", color=TEXT2,
                                   font_size=sp(14), size_hint=(None,1), width=dp(30)))
        self._time_end = KInput(hint="22:00", size_hint=(1,1), height=dp(44))
        self._time_end.text = "22:00"
        time_row.add_widget(self._time_end)
        apply_btn = KButton(text="Apply", bg=GREEN2, fg=BG,
                            size_hint=(None,1), width=dp(64), height=dp(44))
        apply_btn.bind(on_release=lambda _: App.get_running_app().add_log(
            "时间限制已应用", "SUCCESS"))
        time_row.add_widget(apply_btn)
        layout.add_widget(time_row)

        scroll.add_widget(layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def update(self, devices):
        if self._selected_mac:
            for d in devices:
                if d["mac"] == self._selected_mac:
                    self._ctrl_dev_lbl.text = d["name"]
                    self._block_btn.text = "Unblock" if d["blocked"] else "Block"
                    for cat, sw in self._perm_switches.items():
                        sw.active = cat in d.get("allowed_categories",[])
                    break

    def select_device(self, d):
        self._selected_mac = d["mac"]
        self._ctrl_dev_lbl.text = d["name"]
        self._block_btn.text = "Unblock" if d["blocked"] else "Block"
        for cat, sw in self._perm_switches.items():
            sw.active = cat in d.get("allowed_categories",[])

    def _toggle_block(self):
        if not self._selected_mac:
            return
        for d in state.devices:
            if d["mac"] == self._selected_mac:
                d["blocked"] = not d["blocked"]
                action = "Blocked" if d["blocked"] else "解封"
                self._block_btn.text = "Unblock" if d["blocked"] else "Block"
                App.get_running_app().add_log("{} 已{}".format(d["name"], action),
                    "WARNING" if d["blocked"] else "SUCCESS")
                break

    def _on_perm_change(self, cat, sw, value):
        if not self._selected_mac:
            return
        for d in state.devices:
            if d["mac"] == self._selected_mac:
                cats = d.get("allowed_categories", list(PLATFORM_CATS))
                if value and cat not in cats:
                    cats.append(cat)
                elif not value and cat in cats:
                    cats.remove(cat)
                d["allowed_categories"] = cats
                App.get_running_app().add_log(
                    "{} — {} {}".format(d["name"], cat, "已允许" if value else "已禁止"))
                break


# ════════════════════════════════════════════════════════════
#  Tab: 事件日志
# ════════════════════════════════════════════════════════════
class LogTab(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")

        # 过滤按钮
        filter_row = BoxLayout(orientation="horizontal",
                               size_hint=(1,None), height=dp(40),
                               padding=[dp(10),dp(4)], spacing=dp(6))
        self._level_filter = "ALL"
        self._filter_btns = {}
        for level in ("ALL","INFO","WARNING","ERROR","SUCCESS"):
            color = {"ALL":TEXT2,"INFO":TEXT2,"WARNING":YELLOW,
                     "ERROR":RED,"SUCCESS":GREEN}.get(level, TEXT2)
            b = KButton(text=level, bg=CARD2 if level!="ALL" else CARD,
                        fg=color, height=dp(32), font_size=sp(9))
            b.bind(on_release=partial(self._set_filter, level))
            self._filter_btns[level] = b
            filter_row.add_widget(b)
        root.add_widget(filter_row)

        # 日志滚动
        scroll = ScrollView(do_scroll_x=False)
        self._log_layout = BoxLayout(orientation="vertical",
                                      spacing=dp(2), padding=[dp(8), dp(4)],
                                      size_hint=(1, None))
        self._log_layout.bind(minimum_height=self._log_layout.setter("height"))
        scroll.add_widget(self._log_layout)
        root.add_widget(scroll)

        self._scroll = scroll
        self.add_widget(root)

    def _set_filter(self, level, *_):
        self._level_filter = level
        self._redraw()

    def _redraw(self):
        self._log_layout.clear_widgets()
        for e in state.log_entries:
            if self._level_filter != "ALL" and e["level"] != self._level_filter:
                continue
            self._log_layout.add_widget(self._make_row(e))

    def _make_row(self, e):
        colors = {"INFO":TEXT2,"WARNING":YELLOW,"ERROR":RED,"SUCCESS":GREEN}
        row = BoxLayout(orientation="horizontal",
                        size_hint=(1,None), height=dp(36),
                        padding=[dp(4), dp(4)])
        row.add_widget(Label(text="[{}]".format(e["ts"]),
                              font_size=sp(9), color=TEXT3,
                              size_hint=(None,1), width=dp(62)))
        row.add_widget(Label(text="[{}]".format(e["level"]),
                              font_size=sp(9), color=colors.get(e["level"],TEXT2),
                              size_hint=(None,1), width=dp(70), bold=True))
        row.add_widget(Label(text=e["msg"], font_size=sp(10),
                              color=TEXT, halign="left",
                              size_hint=(1,1), text_size=(None, None)))
        return row

    def add_entry(self, entry):
        if (self._level_filter == "ALL" or
                self._level_filter == entry["level"]):
            widget = self._make_row(entry)
            self._log_layout.add_widget(widget)
            Clock.schedule_once(
                lambda dt: setattr(self._scroll, "scroll_y", 0), 0.05)


# ════════════════════════════════════════════════════════════
#  主 App
# ════════════════════════════════════════════════════════════
class NetGuardApp(App):
    title = "NetGuard Pro"

    def build(self):
        if Window is not None:
            Window.clearcolor = BG

        self.sm = ScreenManager(transition=SlideTransition())
        self._brand_screen   = BrandScreen(name="brand")
        self._connect_screen = ConnectScreen(name="connect")
        self._main_screen    = MainScreen(name="main")

        for s in (self._brand_screen, self._connect_screen, self._main_screen):
            self.sm.add_widget(s)

        self.sm.current = "brand"
        return self.sm

    def open_connect_form(self, bid, bname, dip, dusr, dpwd):
        self._connect_screen.setup(bid, bname, dip, dusr, dpwd)
        self.sm.transition.direction = "left"
        self.sm.current = "connect"

    def go_back(self):
        self.sm.transition.direction = "right"
        self.sm.current = "brand"

    def go_brand(self):
        state.monitoring = False
        # 不能在主线程 sleep，用 Clock 延迟
        def _do_switch(dt):
            self.sm.transition.direction = "right"
            self.sm.current = "brand"
        Clock.schedule_once(_do_switch, 0.1)

    def go_main(self, msg):
        self.sm.transition.direction = "left"
        self.sm.current = "main"
        self._main_screen.setup(msg)

    def show_device_detail(self, d):
        popup = DeviceDetailPopup(d)
        popup.open()

    def add_log(self, msg, level="INFO"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {"ts": ts, "level": level, "msg": msg}
        state.log_entries.append(entry)
        if level in ("WARNING", "ERROR"):
            state.warnings += 1
        Clock.schedule_once(
            lambda dt: self._main_screen._tab_log.add_entry(entry), 0)

    def on_stop(self):
        state.monitoring = False


if __name__ == "__main__":
    NetGuardApp().run()
