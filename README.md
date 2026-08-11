# 贝迪克凌云工作台 (Lingyun Workbench)

生产信息一站式工作台：生产日报 + 民航维修事故 + 民航维修技术 + 民航英语学习 + AI资讯。

## 访问地址
- GitHub Pages: https://latonyaostrander33-collab.github.io/lingyun-workbench/
- 仓库: https://github.com/latonyaostrander33-collab/lingyun-workbench

## 板块说明
| 板块 | 内容 | 数据来源 |
|---|---|---|
| 📋 生产日报 | 在修/封存飞机、生产情况表、每日纪要、进出场信息 | IMA 共享知识库「共享测试」《2026年贝迪克凌云生产日报.xlsx》（知识库更新即自动同步） |
| ⚠️ 民航维修事故 | 6条最新事故新闻 + 可点击网址 | 百度资讯抓取 |
| 🔧 民航维修技术 | 维修产业与技术动态新闻 | 百度资讯抓取 |
| 📖 民航英语学习 | 每日词汇/句型 + 打卡（本地 localStorage 连续天数） | 内置内容每日轮换 |
| 🤖 AI资讯 | 最新AI新闻 + 关键信息提取 | 百度资讯抓取 |

## 更新机制
- 页面刷新按钮：手动拉取 data.json（带时间戳防缓存）
- 页面自动刷新：每 10 分钟
- 后端定时更新（OpenClaw cron，每 2 小时）：检测 IMA 知识库日报文件变化（下载+MD5）→ 解析 → 百度资讯更新新闻 → 更新英语 → 合并 → 推送 GitHub
- 数据源变更记录：2026-08-10 曾由 ima 知识库改为本地文件；2026-08-11 改回 IMA 共享知识库「共享测试」（search_knowledge 动态定位 + get_media_info 签名URL下载）

## 文件结构
- `index.html` — 单页工作台（无外部依赖）
- `data.json` — 页面读取的合并数据
- `ribao.json` — 生产日报（由 update_ribao.py 生成）
- `news.json` — 新闻数据（accidents/tech/ai）
- `english.json` — 英语学习内容
- `update_ribao.py` — 本地日报 xlsx → 解析（MD5 变化检测，无变化跳过）
- `merge_data.py` — 三份 JSON 合并为 data.json
- `gh_push.py` — GitHub Contents API 推送（绕开 git 协议网络问题）

## 部署要点
- GitHub Pages 开启：POST /repos/{owner}/{repo}/pages
- 推送用 Contents API（github.com git 协议在国内网络会被重置，api.github.com 可用）
- IMA 凭证位于 ~/.config/ima/（client_id / api_key）
- 日报文件 media_id 通过 search_knowledge("生产日报") 动态获取，文件名会变也不怕
