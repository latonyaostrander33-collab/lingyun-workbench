# -*- coding: utf-8 -*-
"""贝迪克凌云工作台 本地版服务器 (打包为 exe 供分发)
- 启动自动从 IMA 共享知识库「共享测试」拉取日报
- 每 30 分钟自动检测更新
- POST /api/refresh 即时刷新(页面刷新按钮调用, 真正去 IMA 拉最新)
- GET  /api/status  数据状态
- 静态服务 index.html / data.json 等(exe 同目录)
"""
import json, os, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

PORT = 8234
AUTO_MIN = 30

sys.path.insert(0, HERE)
import update_ribao
import merge_data
import fetch_news
import fetch_weather

def do_update(include_news=False):
    """完整更新链路: 日报(IMA) [+ 新闻(百度)] -> 合并 -> data.json; 返回状态字符串"""
    parts = []
    r = update_ribao.run_update()
    parts.append(r)
    try:
        parts.append(fetch_weather.run())
    except Exception as e:
        parts.append("天气失败: " + str(e))
    if include_news:
        try:
            parts.append(fetch_news.run())
        except Exception as e:
            parts.append("新闻失败: " + str(e))
    try:
        u = merge_data.merge()
        parts.append("已合并 (" + u + ")")
    except Exception as e:
        parts.append("合并失败: " + str(e))
    return " | ".join(parts)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, fmt, *args):
        pass  # 静默访问日志

    def _json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            try:
                d = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
                self._json({"ok": True, "updated": d.get("updated"),
                            "count": len(d.get("daily_reports", [])),
                            "source": d.get("ribao", {}).get("source")})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/refresh":
            try:
                result = do_update(include_news=True)
                self._json({"ok": True, "result": result})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

def auto_loop():
    # 日报每 AUTO_MIN(30)分钟检测; 新闻每 4 轮(约2小时)抓一次, 避免触发百度风控
    tick = 0
    while True:
        time.sleep(AUTO_MIN * 60)
        tick += 1
        try:
            r = do_update(include_news=(tick % 4 == 0))
            print(time.strftime("%H:%M:%S"), "自动更新:", r)
        except Exception as e:
            print("自动更新异常:", e)

BUILTIN_FILES = ["index.html", "news.json", "english.json"]

def ensure_static():
    """exe 被单独复制到任意目录时, 自动从内置资源补全必需文件(单文件可运行)"""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    for fn in BUILTIN_FILES:
        dst = os.path.join(HERE, fn)
        if not os.path.exists(dst):
            src = os.path.join(meipass, fn)
            if os.path.exists(src):
                try:
                    shutil.copy2(src, dst)
                    print("[自动补全]", fn, "->", HERE)
                except Exception as e:
                    print("补全失败:", fn, e)

def check_cred():
    try:
        update_ribao.load_cred("client_id")
        update_ribao.load_cred("api_key")
        return True
    except Exception:
        return False

if __name__ == "__main__":
    import shutil
    ensure_static()
    print("=" * 54)
    print("  贝迪克凌云工作台 本地版")
    print("  数据源: IMA 共享知识库「共享测试」")
    print("=" * 54)
    if check_cred():
        print("[✓] IMA 凭证已配置")
    else:
        print("[✗] 未找到 IMA 凭证!")
        print("    请先到 https://ima.qq.com/agent-interface 申请 Client ID 和 API Key,")
        print("    然后在 exe 同目录的 config.json 中填写:")
        print('    {"client_id": "你的ClientID", "api_key": "你的APIKey"}')
        print("    填写后重新启动本程序。")
    print("正在后台拉取最新日报 + 新闻 + 天气...")
    # 关键: 先启动服务器(立即响应), 首次更新在后台线程执行, 避免浏览器打开时白屏
    def first_update():
        try:
            print(do_update(include_news=True))
        except Exception as e:
            print("首次更新异常:", e)
    threading.Thread(target=first_update, daemon=True).start()
    threading.Thread(target=auto_loop, daemon=True).start()
    url = "http://127.0.0.1:" + str(PORT) + "/"
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("已打开浏览器:", url)
    print("提示: 关闭本窗口即退出服务; 数据自动更新(日报30分钟/新闻2小时/天气30分钟)")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except OSError as e:
        print("启动失败:", e, "(端口被占用? 请先关闭已运行的工作台)")
        time.sleep(5)