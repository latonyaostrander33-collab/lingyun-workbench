# -*- coding: utf-8 -*-
"""update_ribao.py — 从 IMA 共享知识库读取生产日报 xlsx 并解析
数据源: IMA 知识库「共享测试」/ 2026年贝迪克凌云生产日报.xlsx
流程: search_knowledge 定位文件 -> get_media_info 拿签名下载URL -> 下载 -> MD5比对(无变化SKIP) -> 解析可见sheet
输出: ribao.json(最新一天) + daily_reports.json(全部可见日报明细)"""
import json, os, re, sys, hashlib, shutil, urllib.request
from datetime import datetime

KB_NAME = "共享测试"          # 按名称定位知识库(别人机器上也能用)
SEARCH_QUERY = "2026年贝迪克凌云生产日报"
MEDIA_TYPE = 5   # xlsx
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)   # 打包成exe后: 数据文件放exe同目录
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "ribao_src.xlsx")             # 上次下载的文件(用于MD5变化检测)
BASE_URL = "https://ima.qq.com"
CRED_DIR = os.path.join(os.path.expanduser("~"), ".config", "ima")
CONFIG = os.path.join(HERE, "config.json")               # 安装包版: 使用者自己的凭证

def load_cred(name):
    # 优先级: config.json(安装包版) -> ~/.config/ima/(OpenClaw版)
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
        if cfg.get(name):
            return str(cfg[name]).strip()
    except Exception:
        pass
    with open(os.path.join(CRED_DIR, name), encoding="utf-8") as f:
        return f.read().strip()

def find_kb_id():
    """按名称定位知识库「共享测试」(不硬编码 kb_id, 任何成员机器上都能找到)"""
    resp = ima_api("openapi/wiki/v1/search_knowledge_base", {"query": KB_NAME, "cursor": "", "limit": 20})
    if resp.get("code") != 0:
        raise RuntimeError(f"知识库搜索失败: {resp.get('msg')}")
    for it in resp.get("data", {}).get("info_list", []):
        if it.get("kb_name") == KB_NAME:
            return it["kb_id"]
    raise RuntimeError(f"未找到名为「{KB_NAME}」的知识库，请确认已被共享给你")

def ima_api(api_path, body):
    req = urllib.request.Request(
        f"{BASE_URL}/{api_path}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "ima-openapi-clientid": load_cred("client_id"),
            "ima-openapi-apikey": load_cred("api_key"),
            "ima-openapi-ctx": "skill_version=1.1.9",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def find_and_download():
    kb_id = find_kb_id()
    """定位知识库日报文件 -> 获取签名URL -> 下载到临时文件, 返回(路径, 标题)"""
    resp = ima_api("openapi/wiki/v1/search_knowledge",
                   {"query": SEARCH_QUERY, "knowledge_base_id": kb_id, "cursor": ""})
    if resp.get("code") != 0:
        raise RuntimeError(f"IMA 搜索失败: {resp.get('msg')}")
    item = next((it for it in resp.get("data", {}).get("info_list", [])
                 if it.get("media_type") == MEDIA_TYPE and "生产日报" in it.get("title", "")), None)
    if not item:
        raise RuntimeError(f"知识库「{KB_NAME}」中未找到 {SEARCH_QUERY}")

    info = ima_api("openapi/wiki/v1/get_media_info", {"media_id": item["media_id"]})
    if info.get("code") != 0:
        raise RuntimeError(f"get_media_info 失败: {info.get('msg')}")
    url = info["data"]["url_info"]["url"]

    tmp = os.path.join(HERE, "ribao_download.tmp.xlsx")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    return tmp, item["title"]

def skey(s):
    try:
        m, dd = s.split("."); return (int(m), int(dd))
    except Exception:
        return (0, 0)

def parse_sheet(ws):
    grid = [[("" if c is None else str(c).strip()) for c in row] for row in ws.iter_rows(values_only=True)]
    def cell(r, c):
        try: return grid[r][c]
        except Exception: return ""
    ri_minutes = ri_io = -1
    for i, row in enumerate(grid):
        j = "|".join(row)
        if "每日生产纪要" in j and ri_minutes < 0: ri_minutes = i
        if "飞机进出场信息" in j and ri_io < 0: ri_io = i
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", cell(2, 0))
    a3_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else cell(2, 0)
    # 兜底: A3 日期与 sheet 标题(如 8.10)不一致时以标题为准(防止复制sheet忘改日期)
    mm, dd = skey(ws.title)
    title_date = f"2026-{mm:02d}-{dd:02d}" if mm else None
    if title_date and a3_date != title_date:
        a3_date = title_date
        wd_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        from datetime import date as _date
        weekday = wd_map[_date(2026, mm, dd).weekday()]
    else:
        weekday = cell(2, 1)
    return {
        "date": a3_date,
        "weekday": weekday, "sheet": ws.title,
        "zaixiu": cell(3, 2), "fengcun": cell(3, 4),
        "categories": [{"name": cell(4, c).replace("\n", ""), "value": cell(5, c)} for c in range(8) if cell(4, c)],
        "minutes": [cell(r, 0) for r in range(ri_minutes + 1, ri_io) if ri_minutes >= 0 and ri_io > ri_minutes and cell(r, 0)],
        "io": {"yesterday_label": cell(ri_io + 1, 0), "yesterday": cell(ri_io + 2, 0),
               "today_label": cell(ri_io + 1, 2), "today": cell(ri_io + 2, 2),
               "tomorrow_label": cell(ri_io + 1, 4), "tomorrow": cell(ri_io + 2, 4),
               "note": cell(ri_io + 2, 6)} if ri_io >= 0 else {},
        "preparer": next((v for row in grid for v in row if "编写" in v or "PREPARE" in v), ""),
        "reviewer": next((v for row in grid for v in row if "审核" in v or "REVIEW" in v), ""),
    }

def run_update():
    """执行完整更新流程, 返回状态字符串 (OK.../SKIP.../ERROR...)"""
    try:
        # 1. 从 IMA 下载最新文件
        src_path, src_title = find_and_download()

        # 2. MD5 变化检测（与上次下载的缓存比较）
        src_hash = hashlib.md5(open(src_path, "rb").read()).hexdigest()
        cache_hash = ""
        if os.path.exists(CACHE):
            cache_hash = hashlib.md5(open(CACHE, "rb").read()).hexdigest()
        if src_hash == cache_hash:
            os.remove(src_path)
            return "SKIP 知识库日报文件无变化，无需更新"
        shutil.move(src_path, CACHE)

        # 3. 解析可见 sheet
        import openpyxl
        wb = openpyxl.load_workbook(CACHE, read_only=False)
        visible = [ws for ws in wb.worksheets if ws.sheet_state == "visible"]
        if not visible:
            raise RuntimeError("文件中没有可见的日报 sheet")
        visible_sorted = sorted(visible, key=lambda ws: skey(ws.title))

        reports = [parse_sheet(ws) for ws in visible_sorted]
        reports.reverse()  # 最新在前
        latest = reports[0]

        latest["total_sheets"] = len(visible)
        latest["hidden_sheets"] = len(wb.worksheets) - len(visible)
        latest["visible_range"] = f"{visible_sorted[0].title} ~ {visible_sorted[-1].title}"
        latest["source"] = f"IMA知识库「{KB_NAME}」/{src_title}"
        latest["parsed_at"] = datetime.now().isoformat(timespec="seconds")

        with open(os.path.join(HERE, "ribao.json"), "w", encoding="utf-8") as f:
            json.dump(latest, f, ensure_ascii=False, indent=2)
        with open(os.path.join(HERE, "daily_reports.json"), "w", encoding="utf-8") as f:
            json.dump({"updated": datetime.now().isoformat(timespec="seconds"),
                       "count": len(reports), "reports": reports}, f, ensure_ascii=False, indent=2)
        return "OK 可见日报 " + str(len(reports)) + " 天 | 最新: " + latest["date"] + " " + (latest["weekday"] or "")
    except Exception as e:
        return "ERROR " + str(e)

def main():
    print(run_update())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR", e, file=sys.stderr)
        sys.exit(1)