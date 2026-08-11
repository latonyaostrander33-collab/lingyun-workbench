# -*- coding: utf-8 -*-
"""merge_data.py — 合并 ribao.json + daily_reports.json + news.json + english.json 为 data.json"""
import json, os, sys
from datetime import datetime

if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)   # 打包成exe后: 数据文件在exe同目录
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

def load(n):
    with open(os.path.join(HERE, n), encoding="utf-8") as f:
        return json.load(f)

def merge():
    """合并三份JSON为 data.json, 返回 updated 时间字符串"""
    ribao = load("ribao.json")
    news = load("news.json")
    eng = load("english.json")
    daily = load("daily_reports.json") if os.path.exists(os.path.join(HERE, "daily_reports.json")) else {"reports": []}
    data = {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "ribao": ribao,
            "daily_reports": daily.get("reports", []),
            "accidents": news.get("accidents", []), "tech": news.get("tech", []),
            "ai": news.get("ai", []), "english": eng}
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data["updated"]

if __name__ == "__main__":
    u = merge()
    print("data.json merged at", u, "| daily_reports:", len(json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))["daily_reports"]))