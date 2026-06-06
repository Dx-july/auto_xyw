# 校园网自动登录脚本 (深澜 Srun XXTEA)

基于深澜(Srun) XXTEA 加密协议的校园网自动登录工具，支持 **开机自启动**、**断网自动重连**，后台静默运行。

## 功能

- 深澜 Srun `xEncode` (XXTEA) 加密认证
- 启动自动登录，断网自动重连
- 开机自启动（后台静默运行，无控制台窗口）
- 可配置的检查间隔和重试次数

## 文件说明

| 文件 | 说明 |
|------|------|
| `xyw.py` | 主脚本，处理认证登录与断网检测 |
| `config.example.json` | 配置文件模板 |
| `setup_startup.ps1` | 配置开机自启动（右键 → 使用 PowerShell 运行） |
| `install_deps.bat` | 安装依赖（requests） |
| `.gitignore` | Git 忽略规则 |

## 快速开始

### 1. 安装依赖

双击运行 `install_deps.bat`，或手动执行：

```bash
pip install requests
```

### 2. 配置账号

将 `config.example.json` 复制为 `config.json`，并填入校园网账号密码：

> 或者直接运行 `python xyw.py`，首次运行会自动生成 `config.json`。

编辑 `config.json`：

```json
{
  "username": "你的学号",
  "password": "你的密码",
  "host": "10.5.0.100",
  "check_interval": 30,
  "retry_times": 3,
  "retry_interval": 5
}
```

| 配置项 | 说明 |
|--------|------|
| `username` | 校园网账号（学号） |
| `password` | 校园网密码 |
| `host` | 认证服务器地址（各学校不同，见下方说明） |
| `check_interval` | 断网检测间隔（秒） |
| `retry_times` | 登录失败重试次数 |
| `retry_interval` | 重试间隔（秒） |

> **如何获取 `host` 地址：** 连接校园网（不登录），浏览器访问任意网站会自动跳转到认证页面，地址栏中的 IP 就是你的认证服务器地址。

### 3. 手动运行

```bash
python xyw.py
```

### 4. 设置开机自启动

右键 `setup_startup.ps1` → **使用 PowerShell 运行**。

该脚本会自动：
- 检测 Python 路径
- 生成 `run_xyw.vbs` 启动器
- 在 Windows 启动文件夹创建快捷方式

开机后将自动在后台静默运行，无控制台弹窗。

### 5. 取消开机自启动

在文件资源管理器打开以下路径，删除 `CampusNetworkLogin.lnk`：

```
C:\Users\你的用户名\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```

## 原理

本脚本实现了深澜校园网 Srun 认证协议的完整流程：

1. **获取 challenge** — 从认证服务器获取 token 和 IP
2. **加密密码** — 使用 HMAC-MD5 对密码进行加密
3. **加密 info** — 将用户信息经 XXTEA (`xEncode`) 加密后再 Base64 编码
4. **计算校验和** — SHA1 哈希
5. **发送登录请求** — 带有加密参数的认证请求

参考：[深澜认证协议分析](https://blog.csdn.net/qq_41797946/article/details/89417722)

## 依赖

- Python 3.6+
- requests
