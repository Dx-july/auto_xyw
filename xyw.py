"""
深澜(Srun)校园网自动登录脚本
基于 XXTEA 加密协议，支持开机自启动、断网自动重连
配置文件：config.json（首次运行自动生成）

参考：
- 深澜认证协议分析: https://blog.csdn.net/qq_41797946/article/details/89417722
"""

import requests
import json
import hashlib
import hmac
import time
import os
import sys
import math

# ==================== 配置区域 ====================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "username": "你的学号",
    "password": "你的密码",
    "host": "10.5.0.100",
    "check_interval": 30,
    "retry_times": 3,
    "retry_interval": 5,
}

# ==================== 加载配置 ====================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"首次运行，已生成配置文件: {CONFIG_FILE}")
        print("请编辑该文件，填入你的校园网账号和密码，然后重新运行脚本。")
        sys.exit(0)

config = load_config()
USERNAME = config["username"]
PASSWORD = config["password"]
HOST = config["host"]
CHECK_INTERVAL = config.get("check_interval", 30)
RETRY_TIMES = config.get("retry_times", 3)
RETRY_INTERVAL = config.get("retry_interval", 5)

BASE_URL = f"http://{HOST}"

# ==================== 深澜 Srun 加密函数 ====================

def ordat(s: str, idx: int) -> int:
    """安全获取字符串指定位置的ASCII码"""
    if idx < len(s):
        return ord(s[idx])
    return 0


def sencode(msg: str, key: bool) -> list:
    """
    将字符串编码为32位整数数组（小端序）
    key=True: 用于消息，尾部追加长度
    key=False: 用于密钥，不追加长度
    """
    l = len(msg)
    pwd = []
    for i in range(0, l, 4):
        pwd.append(
            ordat(msg, i)
            | ordat(msg, i + 1) << 8
            | ordat(msg, i + 2) << 16
            | ordat(msg, i + 3) << 24
        )
    if key:
        pwd.append(l)
    return pwd


def lencode(msg: list, key: bool) -> str:
    """
    将32位整数数组解码为字符串
    key=True: 按长度截断
    key=False: 不解截断
    """
    l = len(msg)
    ll = (l - 1) << 2
    if key:
        m = msg[l - 1]
        if m < ll - 3 or m > ll:
            return ""
        ll = m
    result = []
    for i in range(l):
        v = msg[i] & 0xFFFFFFFF
        result.append(chr(v & 0xFF))
        result.append(chr((v >> 8) & 0xFF))
        result.append(chr((v >> 16) & 0xFF))
        result.append(chr((v >> 24) & 0xFF))
    s = "".join(result)
    if key:
        return s[:ll]
    return s


def xencode(msg: str, key: str) -> str:
    """
    深澜 Srun xEncode 加密（XXTEA 算法）
    """
    if not msg:
        return ""

    v = sencode(msg, True)
    k = sencode(key, False)

    # 密钥长度不足4时补0
    if len(k) < 4:
        k += [0] * (4 - len(k))

    n = len(v) - 1
    if n < 1:
        # 数据太短，直接返回 lencode 结果
        return lencode(v, False)

    z = v[n]
    y = v[0]
    c = 0x86014019 | 0x183639A0  # 0x9E3779B9 (delta for XXTEA)
    q = math.floor(6 + 52 / (n + 1))
    d = 0

    while q > 0:
        d = (d + c) & (0x8CE0D9BF | 0x731F2640)  # 0xFFFFFFFF
        e = (d >> 2) & 3
        p = 0
        while p < n:
            y = v[p + 1]
            m = (z >> 5) ^ ((y << 2) & 0xFFFFFFFF)
            m = (m + (((y >> 3) ^ ((z << 4) & 0xFFFFFFFF)) ^ (d ^ y))) & 0xFFFFFFFF
            m = (m + (k[(p & 3) ^ e] ^ z)) & 0xFFFFFFFF
            v[p] = (v[p] + m) & (0xEFB8D130 | 0x10472ECF)  # 0xFFFFFFFF
            z = v[p]
            p += 1
        y = v[0]
        m = (z >> 5) ^ ((y << 2) & 0xFFFFFFFF)
        m = (m + (((y >> 3) ^ ((z << 4) & 0xFFFFFFFF)) ^ (d ^ y))) & 0xFFFFFFFF
        m = (m + (k[(p & 3) ^ e] ^ z)) & 0xFFFFFFFF
        v[n] = (v[n] + m) & (0xBB390742 | 0x44C6F8BD)  # 0xFFFFFFFF
        z = v[n]
        q -= 1

    return lencode(v, False)


# ==================== 深澜自定义 Base64 ====================

_PADCHAR = "="
_ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"


def _getbyte(s: str, i: int) -> int:
    """获取字符串指定位置的字节值"""
    x = ord(s[i])
    if x > 255:
        raise ValueError("INVALID_CHARACTER_ERR: DOM Exception 5")
    return x


def srun_base64(s: str) -> str:
    """深澜自定义 Base64 编码"""
    if len(s) == 0:
        return s

    x = []
    imax = len(s) - len(s) % 3

    for i in range(0, imax, 3):
        b10 = (_getbyte(s, i) << 16) | (_getbyte(s, i + 1) << 8) | _getbyte(s, i + 2)
        x.append(_ALPHA[(b10 >> 18) & 63])
        x.append(_ALPHA[(b10 >> 12) & 63])
        x.append(_ALPHA[(b10 >> 6) & 63])
        x.append(_ALPHA[b10 & 63])

    i = imax
    remainder = len(s) - imax
    if remainder == 1:
        b10 = _getbyte(s, i) << 16
        x.append(_ALPHA[(b10 >> 18) & 63])
        x.append(_ALPHA[(b10 >> 12) & 63])
        x.append(_PADCHAR)
        x.append(_PADCHAR)
    elif remainder == 2:
        b10 = (_getbyte(s, i) << 16) | (_getbyte(s, i + 1) << 8)
        x.append(_ALPHA[(b10 >> 18) & 63])
        x.append(_ALPHA[(b10 >> 12) & 63])
        x.append(_ALPHA[(b10 >> 6) & 63])
        x.append(_PADCHAR)

    return "".join(x)


# ==================== HMAC-MD5 / SHA1 ====================

def pwd_hmd5(password: str, token: str) -> str:
    """HMAC-MD5 密码加密"""
    h = hmac.new(token.encode(), password.encode(), digestmod=hashlib.md5)
    return h.hexdigest()


def sha1_hash(s: str) -> str:
    """SHA1 哈希"""
    return hashlib.sha1(s.encode()).hexdigest()


# ==================== 网络操作 ====================

def check_online() -> bool:
    """检测外网连通性"""
    try:
        resp = requests.get("https://www.baidu.com", timeout=5, allow_redirects=False)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def get_challenge() -> dict:
    """获取认证 challenge（token）"""
    url = f"{BASE_URL}/cgi-bin/get_challenge"
    params = {
        "callback": "jsonp",
        "username": USERNAME,
        "ip": "",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        text = resp.text
        # 去掉 jsonp 包装
        if text.startswith("jsonp("):
            text = text[6:-1]
        return json.loads(text)
    except Exception as e:
        print(f"[错误] 获取 challenge 失败: {e}")
        return {}


def login() -> bool:
    """执行深澜校园网登录"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在登录校园网...")

    # 1. 获取 challenge
    challenge_data = get_challenge()
    if not challenge_data:
        print("[失败] 无法获取认证信息，请检查网络连接")
        return False

    token = str(challenge_data.get("challenge", ""))
    client_ip = str(challenge_data.get("client_ip", ""))
    # ac_id 优先从 config 读，否则从 challenge 返回中获取
    ac_id = str(config.get("ac_id", challenge_data.get("ac_id", 1)))

    if not token or not client_ip:
        print("[失败] 获取 challenge 或 IP 失败")
        print(f"  challenge 响应: {json.dumps(challenge_data, ensure_ascii=False)}")
        return False

    # 2. 计算 HMAC-MD5 密码
    hmd5 = pwd_hmd5(PASSWORD, token)

    # 3. 构建 info JSON 并用 xEncode + base64 编码
    n = "200"
    type_str = "1"
    enc_ver = "srun_bx1"

    info_dict = {
        "username": USERNAME,
        "password": PASSWORD,
        "ip": client_ip,
        "acid": ac_id,
        "enc_ver": enc_ver,
    }
    # 注意：info_json 必须紧凑无空格，用 separators 控制
    info_json = json.dumps(info_dict, separators=(",", ":"))
    # xEncode 加密后再 base64
    xencoded = xencode(info_json, token)
    info_base64 = srun_base64(xencoded)
    encoded_info = "{SRBX1}" + info_base64

    # 4. 计算校验和 chksum
    chkstr = (
        token + USERNAME +
        token + hmd5 +
        token + ac_id +
        token + client_ip +
        token + n +
        token + type_str +
        token + encoded_info
    )
    chksum = sha1_hash(chkstr)

    # 5. 发送登录请求
    login_url = f"{BASE_URL}/cgi-bin/srun_portal"
    payload = {
        "callback": "jsonp",
        "action": "login",
        "username": USERNAME,
        "password": "{MD5}" + hmd5,
        "ac_id": ac_id,
        "ip": client_ip,
        "info": encoded_info,
        "chksum": chksum,
        "n": n,
        "type": type_str,
        "os": "Windows",
        "name": "Windows",
        "double_stack": "0",
    }

    try:
        resp = requests.get(login_url, params=payload, timeout=10)
        text = resp.text
        if text.startswith("jsonp("):
            text = text[6:-1]
        result = json.loads(text)

        if result.get("error") == "ok":
            print("[成功] 校园网登录成功！")
            return True
        else:
            error_msg = result.get("error", "未知错误")
            print(f"[失败] 登录失败: {error_msg}")
            return False

    except Exception as e:
        print(f"[失败] 登录请求异常: {e}")
        return False


# ==================== 主循环 ====================

def main():
    print("=" * 50)
    print("  深澜(Srun)校园网自动登录脚本 (XXTEA)")
    print(f"  账号: {USERNAME}")
    print(f"  服务器: {HOST}")
    print(f"  检查间隔: {CHECK_INTERVAL} 秒")
    print("=" * 50)

    # 启动时先登录一次
    login()

    while True:
        try:
            if check_online():
                print(f"[{time.strftime('%H:%M:%S')}] 网络正常，{CHECK_INTERVAL}s后检查...")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 检测到断网，尝试重新登录...")
                success = False
                for i in range(RETRY_TIMES):
                    if login():
                        success = True
                        break
                    print(f"  重试 {i + 1}/{RETRY_TIMES}，{RETRY_INTERVAL}s后重试...")
                    time.sleep(RETRY_INTERVAL)

                if not success:
                    print(f"  登录失败，已重试{RETRY_TIMES}次，下次检查时重试")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[退出] 脚本已停止")
            break
        except Exception as e:
            print(f"[异常] {e}，{CHECK_INTERVAL}s后重试...")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
