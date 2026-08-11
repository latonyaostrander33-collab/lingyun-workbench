# -*- coding: utf-8 -*-
"""fetch_weather.py — wttr.in 天气抓取 (宜昌), 免key, 失败保留旧 weather.json"""
import json, os, sys, urllib.request
from datetime import datetime

if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

URL = "https://wttr.in/Yichang?format=j1&lang=zh"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}

# wttr.in weatherCode -> 中文
CODE_CN = {
    "113": "晴", "116": "多云", "119": "阴", "122": "阴", "143": "薄雾",
    "248": "雾", "260": "雾", "200": "雷阵雨",
    "176": "阵雨", "263": "小雨", "266": "小雨", "281": "冻雨", "284": "冻雨",
    "293": "小雨", "296": "小雨", "299": "中雨", "302": "中雨",
    "305": "大雨", "308": "大雨", "311": "冻雨", "314": "冻雨", "317": "冻雨",
    "320": "雨夹雪", "323": "小雪", "326": "小雪", "329": "中雪", "332": "中雪",
    "335": "大雪", "338": "大雪", "350": "冰雨", "353": "阵雨", "356": "阵雨",
    "359": "暴雨", "362": "阵雪", "365": "阵雪", "368": "小雪", "371": "中雪",
    "374": "冰雨", "377": "冰雨", "386": "雷阵雨", "389": "雷阵雨",
    "392": "雷雪", "395": "大雪",
}

def cn(code):
    return CODE_CN.get(str(code), "未知")

def run():
    """抓取宜昌天气写入 weather.json, 返回状态字符串"""
    try:
        req = urllib.request.Request(URL, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        cc = d["current_condition"][0]
        area = d["nearest_area"][0]["areaName"][0]["value"]
        forecast = []
        for w in d.get("weather", [])[:5]:
            h = w["hourly"][4]  # 中午时段
            forecast.append({"date": w["date"], "maxtempC": w["maxtempC"],
                             "mintempC": w["mintempC"], "desc": cn(h["weatherCode"])})
        data = {
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "city": "宜昌", "area": area,
            "tempC": cc["temp_C"], "feelsC": cc["FeelsLikeC"],
            "desc": cn(cc["weatherCode"]),
            "humidity": cc["humidity"], "windKmph": cc["windspeedKmph"],
            "windDir": cc["winddir16Point"], "code": cc["weatherCode"],
            "forecast": forecast,
        }
        with open(os.path.join(HERE, "weather.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return "OK 天气 " + data["desc"] + " " + str(data["tempC"]) + "C"
    except Exception as e:
        return "ERROR 天气: " + str(e)

if __name__ == "__main__":
    print(run())