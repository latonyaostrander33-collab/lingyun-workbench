# -*- coding: utf-8 -*-
"""fetch_news.py — 百度资讯抓取 (accidents/tech/ai 三板块)
纯标准库实现, 不依赖AI, 失败时保留旧 news.json
"""
import json, os, re, sys, urllib.request, urllib.parse

if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}

KEYWORDS = [("accidents", "民航维修事故"), ("tech", "民航维修技术"), ("ai", "AI人工智能")]
LIMIT = 6

def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()

def fetch_one(keyword):
    url = "https://news.baidu.com/ns?word=" + urllib.parse.quote(keyword) + "&tn=news&from=news&cl=2&rn=20&ct=1"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", "ignore")
    if "百度安全验证" in html or "网络不给力" in html:
        raise RuntimeError("百度触发验证码")
    items = []
    h3s = list(re.finditer(r'<h3 class="news-title[^"]*"[^>]*><a href="([^"]+)"[^>]*>(.*?)</a></h3>', html, re.S))
    for i, m in enumerate(h3s):
        title = clean(m.group(2))
        if not title:
            continue
        end = h3s[i + 1].start() if i + 1 < len(h3s) else m.end() + 3000
        seg = html[m.end():end]
        date = ""
        dm = re.search(r'aria-label="发布于：([^"]+)"', seg)
        if dm:
            date = dm.group(1).strip()
        src = ""
        sm = re.search(r'aria-label="新闻来源：([^"]+)"', seg)
        if sm:
            src = sm.group(1).strip()
        summ = ""
        mm = re.search(r'aria-label="摘要 ([^"]+)"', seg)
        if mm:
            summ = mm.group(1).replace("摘要结束，点击查看详情", "").strip()
        items.append({"title": title, "url": m.group(1).replace("&amp;", "&"),
                      "source": src, "date": date, "summary": summ})
        if len(items) >= LIMIT:
            break
    return items

def run():
    """抓取三板块并写 news.json; 任一板块失败则保留旧文件。返回状态字符串"""
    result = {}
    msgs = []
    for key, kw in KEYWORDS:
        try:
            items = fetch_one(kw)
            result[key] = items
            msgs.append(key + ":" + str(len(items)))
        except Exception as e:
            return "ERROR 新闻抓取失败(" + key + "/" + kw + "): " + str(e)
    # ai 板块: 以摘要作为关键信息(key字段, 页面有独立展示)
    for it in result.get("ai", []):
        it["key"] = it.get("summary", "")
    with open(os.path.join(HERE, "news.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return "OK 新闻 " + " ".join(msgs)

if __name__ == "__main__":
    print(run())