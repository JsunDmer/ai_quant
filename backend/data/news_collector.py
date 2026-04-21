"""
多源新闻采集器 - 替代 akshare 新闻依赖

九路采集 + 去重合并:
  Source 1: DuckDuckGo 搜索 (AI搜索，最广覆盖)
  Source 2: 东方财富 JSON API (A股最相关)
  Source 3: 新浪财经 API (补充覆盖)
  Source 4: AI Agent (LLM 自主决定搜索关键词，function calling)
  Source 5: 第一财经 JSON API
  Source 6: 澎湃新闻 JSON API
  Source 7: 界面新闻 HTML 解析 (需 beautifulsoup4)
  Source 8: 财新 HTML 解析 (需 beautifulsoup4)
  Source 9: 观察者网 HTML 解析 (需 beautifulsoup4)

入口: collect_all_news(limit=20) -> List[Dict]
输出格式: {title, content, time, source, url}
"""
import json
import re
import traceback
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict

import requests
from openai import OpenAI

from backend.config import config

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="akshare")

# DuckDuckGo 搜索 - 可选依赖
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    DDGS = None  # for tests/mocking
    HAS_DDGS = False

# BeautifulSoup - 可选依赖 (用于 HTML 解析源)
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

_MAX_AGENT_TOOL_CALLS = 3  # Agent 最多搜索次数

AGENT_TOOLS = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "搜索最新财经新闻。可用不同关键词多次搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "description": "结果数上限", "default": 10}
            },
            "required": ["query"]
        }
    }
}]


# ---------------------------------------------------------------------------
# Source 1: DuckDuckGo 搜索
# ---------------------------------------------------------------------------
def _fetch_duckduckgo(max_results: int = 15) -> List[Dict]:
    """通过 DuckDuckGo 搜索财经新闻"""
    if not HAS_DDGS:
        print("[NewsCollector] duckduckgo-search 未安装，跳过 DuckDuckGo 源")
        return []

    results = []
    today = datetime.now().strftime('%Y-%m-%d')
    queries = [
        f"A股 财经新闻 {today}",
        "今日股市 重要新闻",
    ]

    try:
        ddgs = DDGS()
        for query in queries:
            try:
                items = ddgs.news(query, region="cn-zh", timelimit="d", max_results=max_results)
                for item in items:
                    results.append({
                        'title': item.get('title', ''),
                        'content': item.get('body', ''),
                        'time': item.get('date', ''),
                        'source': item.get('source', 'DuckDuckGo'),
                        'url': item.get('url', ''),
                    })
            except Exception as e:
                print(f"[NewsCollector] DuckDuckGo 查询 '{query}' 失败: {e}")
    except Exception as e:
        print(f"[NewsCollector] DuckDuckGo 初始化失败: {e}")

    print(f"[NewsCollector] DuckDuckGo 采集 {len(results)} 条")
    return results


# ---------------------------------------------------------------------------
# Source 2: 东方财富 API
# ---------------------------------------------------------------------------
def _fetch_eastmoney(limit: int = 20) -> List[Dict]:
    """通过东方财富 API 采集财经新闻"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.eastmoney.com/',
    }

    # 主接口: 财经新闻列表
    try:
        url = 'https://np-listapi.eastmoney.com/comm/wap/getListInfo'
        params = {
            'cb': '',
            'client': 'wap',
            'type': 1,
            'mTypeAndCode': '702',
            'pageSize': limit,
            'pageIndex': 0,
            'callback': '',
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        text = resp.text.strip()
        # 去除 JSONP 包裹
        if text.startswith('(') and text.endswith(')'):
            text = text[1:-1]

        import json
        data = json.loads(text)
        # 确保 data 是字典，如果是列表则设为空
        if not isinstance(data, dict):
            data = {}
        items = data.get('data', {}).get('list', [])
        for item in items:
            title = item.get('title', '')
            content = item.get('digest', '') or item.get('content', '')
            # 清除 HTML 标签
            content = re.sub(r'<[^>]+>', '', content)
            pub_time = item.get('showTime', '') or item.get('date', '')
            art_url = item.get('url', '') or item.get('shareUrl', '')

            if title:
                results.append({
                    'title': title,
                    'content': content[:500],
                    'time': pub_time,
                    'source': '东方财富',
                    'url': art_url,
                })
    except Exception as e:
        print(f"[NewsCollector] 东方财富主接口失败: {e}")

    # 备用接口: 快讯
    if not results:
        try:
            url = 'https://np-listapi.eastmoney.com/comm/wap/getListInfo'
            params = {
                'cb': '',
                'client': 'wap',
                'type': 1,
                'mTypeAndCode': '723',
                'pageSize': limit,
                'pageIndex': 0,
                'callback': '',
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()

            text = resp.text.strip()
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]

            import json
            data = json.loads(text)
            # 确保 data 是字典，如果是列表则设为空
            if not isinstance(data, dict):
                data = {}
            items = data.get('data', {}).get('list', [])
            for item in items:
                title = item.get('title', '')
                content = item.get('digest', '') or item.get('content', '')
                content = re.sub(r'<[^>]+>', '', content)
                pub_time = item.get('showTime', '') or item.get('date', '')
                art_url = item.get('url', '') or item.get('shareUrl', '')

                if title:
                    results.append({
                        'title': title,
                        'content': content[:500],
                        'time': pub_time,
                        'source': '东方财富',
                        'url': art_url,
                    })
        except Exception as e:
            print(f"[NewsCollector] 东方财富备用接口失败: {e}")

    print(f"[NewsCollector] 东方财富 采集 {len(results)} 条")
    return results


# ---------------------------------------------------------------------------
# Source 3: 新浪财经 API
# ---------------------------------------------------------------------------
def _fetch_sina(limit: int = 20) -> List[Dict]:
    """通过新浪财经 API 采集财经新闻"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn/',
    }

    # 主接口: 财经滚动新闻
    try:
        url = 'https://feed.mix.sina.com.cn/api/roll/get'
        params = {
            'pageid': 153,
            'lid': 2516,
            'k': '',
            'num': limit,
            'page': 1,
            'r': '',
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        # 确保 data 是字典，如果是列表则设为空
        if not isinstance(data, dict):
            data = {}
        items = data.get('result', {}).get('data', [])
        for item in items:
            title = item.get('title', '')
            content = item.get('intro', '') or item.get('summary', '')
            content = re.sub(r'<[^>]+>', '', content)

            # Unix 时间戳 -> 字符串
            create_time = item.get('ctime', '') or item.get('createtime', '')
            if create_time and str(create_time).isdigit():
                try:
                    create_time = datetime.fromtimestamp(int(create_time)).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OSError):
                    pass

            art_url = item.get('url', '') or item.get('link', '')

            if title:
                results.append({
                    'title': title,
                    'content': content[:500],
                    'time': str(create_time),
                    'source': '新浪财经',
                    'url': art_url,
                })
    except Exception as e:
        print(f"[NewsCollector] 新浪财经主接口失败: {e}")

    # 备用接口: 7x24 直播
    if not results:
        try:
            url = 'https://zhibo.sina.com.cn/api/zhibo/feed'
            params = {
                'page': 1,
                'page_size': limit,
                'zhibo_id': 152,
                'tag_id': 0,
                'type': 0,
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()

            data = resp.json()
            # 确保 data 是字典，如果是列表则设为空
            if not isinstance(data, dict):
                data = {}
            result = data.get('result', {})
            # 确保 result 是字典
            if not isinstance(result, dict):
                result = {}
            items = result.get('data', {}).get('feed', {}).get('list', [])
            for item in items:
                content = item.get('rich_text', '') or item.get('text', '')
                content = re.sub(r'<[^>]+>', '', content)
                title = content[:30] + '...' if len(content) > 30 else content

                create_time = item.get('create_time', '')
                if create_time and str(create_time).isdigit():
                    try:
                        create_time = datetime.fromtimestamp(int(create_time)).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OSError):
                        pass

                if content:
                    results.append({
                        'title': title,
                        'content': content[:500],
                        'time': str(create_time),
                        'source': '新浪财经',
                        'url': '',
                    })
        except Exception as e:
            print(f"[NewsCollector] 新浪财经备用接口失败: {e}")

    print(f"[NewsCollector] 新浪财经 采集 {len(results)} 条")
    return results


# ---------------------------------------------------------------------------
# Source 4: AI Agent (Function Calling)
# ---------------------------------------------------------------------------
def _execute_web_search(query: str, max_results: int = 10) -> str:
    """执行搜索并返回 JSON 字符串（供 tool role 回传给 LLM）"""
    if not HAS_DDGS:
        return json.dumps({"error": "duckduckgo-search 未安装"})
    try:
        ddgs = DDGS()
        items = ddgs.news(query, region="cn-zh", timelimit="d", max_results=max_results)
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "body": item.get("body", ""),
                "date": item.get("date", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
            })
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _parse_agent_response(text: str) -> List[Dict]:
    """解析 Agent 最终文本响应为统一新闻格式"""
    if not text or not text.strip():
        return []

    text = text.strip()

    # 剥离 markdown 代码块
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # 尝试直接解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return _filter_valid_items(data)
    except (json.JSONDecodeError, TypeError):
        pass

    # 从混合文本中提取 JSON 数组
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return _filter_valid_items(data)
        except (json.JSONDecodeError, TypeError):
            pass

    return []


def _filter_valid_items(items: list) -> List[Dict]:
    """过滤并标准化新闻条目，跳过无标题项"""
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        if not title:
            continue
        result.append({
            "title": title,
            "content": item.get("content", item.get("body", item.get("summary", ""))),
            "time": item.get("time", item.get("date", "")),
            "source": item.get("source", "AI Agent"),
            "url": item.get("url", ""),
        })
    return result


def _fetch_via_agent(max_results: int = 15) -> List[Dict]:
    """通过 AI Agent (function calling) 自主搜索新闻"""
    if not config.LLM_API_KEY:
        print("[NewsCollector] AI Agent: 无 API Key，跳过")
        return []
    if not HAS_DDGS:
        print("[NewsCollector] AI Agent: 无 DDGS，跳过")
        return []

    today = datetime.now().strftime('%Y-%m-%d')

    try:
        client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是财经新闻搜索助手。今天是 {today}。"
                    "请使用 web_search 工具搜索今日A股最重要的财经新闻，"
                    "你可以用不同关键词搜索多次以覆盖宏观、行业、政策等维度。"
                    "搜索完成后，请整理去重并以 JSON 数组返回，每条格式："
                    '{"title":"标题","content":"摘要","time":"时间","source":"来源","url":"链接"}'
                )
            },
            {"role": "user", "content": f"请搜索 {today} A股最重要的财经新闻，最多返回 {max_results} 条。"}
        ]

        for _ in range(_MAX_AGENT_TOOL_CALLS + 1):
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.3,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                # 将 assistant 消息加入对话
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in msg.tool_calls
                    ]
                })

                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    query = args.get("query", "A股新闻")
                    mr = args.get("max_results", 10)
                    print(f"[NewsCollector] AI Agent 搜索: {query}")
                    tool_result = _execute_web_search(query, mr)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    })
            else:
                # Agent 返回了最终文本
                result = _parse_agent_response(msg.content or "")
                print(f"[NewsCollector] AI Agent 采集 {len(result)} 条")
                return result

        # 超出循环限制，未获得最终文本
        print("[NewsCollector] AI Agent: 超出工具调用限额，未获取结果")
        return []

    except Exception as e:
        err = str(e).lower()
        if any(kw in err for kw in ("tool", "function", "unsupported", "400")):
            print(f"[NewsCollector] AI Agent: 代理不支持 function calling，降级模式 ({e})")
            try:
                client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
                return _fetch_agent_fallback(client, today, max_results)
            except Exception as fb_err:
                print(f"[NewsCollector] AI Agent 降级也失败: {fb_err}")
                return []
        else:
            print(f"[NewsCollector] AI Agent 异常: {e}")
            return []


def _fetch_agent_fallback(client, today: str, max_results: int = 15) -> List[Dict]:
    """降级模式：LLM 生成关键词 → DDGS 搜索 → LLM 合并"""
    try:
        # Step 1: 让 LLM 生成搜索关键词
        kw_resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是财经新闻搜索助手。"},
                {"role": "user", "content": (
                    f"今天是 {today}，请列出5个用于搜索今日A股重要新闻的关键词，"
                    "每行一个，不要编号和额外说明。"
                )}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        keywords_text = kw_resp.choices[0].message.content or ""
        keywords = [kw.strip() for kw in keywords_text.strip().split("\n") if kw.strip()][:5]

        if not keywords:
            return []

        # Step 2: 用 DDGS 执行搜索
        all_results = []
        ddgs = DDGS()
        for kw in keywords:
            try:
                items = ddgs.news(kw, region="cn-zh", timelimit="d", max_results=5)
                for item in items:
                    all_results.append({
                        "title": item.get("title", ""),
                        "body": item.get("body", ""),
                        "date": item.get("date", ""),
                        "source": item.get("source", ""),
                        "url": item.get("url", ""),
                    })
            except Exception:
                continue

        if not all_results:
            return []

        # Step 3: 让 LLM 合并去重
        merge_resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是财经新闻整理助手。"},
                {"role": "user", "content": (
                    f"以下是搜索到的新闻原始数据，请整理去重并返回最重要的 {max_results} 条，"
                    "以 JSON 数组格式返回，每条格式："
                    '{"title":"标题","content":"摘要","time":"时间","source":"来源","url":"链接"}\n\n'
                    + json.dumps(all_results, ensure_ascii=False)
                )}
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        merge_text = merge_resp.choices[0].message.content or ""
        result = _parse_agent_response(merge_text)
        print(f"[NewsCollector] AI Agent (降级) 采集 {len(result)} 条")
        return result

    except Exception as e:
        print(f"[NewsCollector] AI Agent 降级失败: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 5: 第一财经
# ---------------------------------------------------------------------------
def _fetch_yicai(limit: int = 20) -> List[Dict]:
    """通过第一财经 API 采集财经新闻"""
    results = []
    try:
        resp = requests.get(
            f'https://www.yicai.com/api/ajax/getlatest?page=1&pagesize={limit}',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else data.get('data', data.get('list', []))
        if isinstance(items, dict):
            items = items.get('list', [])
        for item in items:
            title = item.get('NewsTitle', '') or item.get('title', '')
            if not title:
                continue
            content = item.get('NewsNotes', '') or item.get('summary', '')
            pub_time = item.get('CreateDate', '') or item.get('date', '')
            url = item.get('url', '')
            if url and not url.startswith('http'):
                url = f'https://www.yicai.com{url}'
            results.append({
                'title': title,
                'content': content[:500],
                'time': pub_time,
                'source': '第一财经',
                'url': url,
            })
    except Exception as e:
        print(f"[NewsCollector] 第一财经采集失败: {e}")
    print(f"[NewsCollector] 第一财经 采集 {len(results)} 条")
    return results


# ---------------------------------------------------------------------------
# Source 6: 澎湃新闻
# ---------------------------------------------------------------------------
def _fetch_thepaper(limit: int = 20) -> List[Dict]:
    """通过澎湃新闻 API 采集财经新闻"""
    results = []
    try:
        resp = requests.get(
            'https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get('data', {})
        items = (data.get('hotNews', []) or []) + (data.get('financialInformationNews', []) or [])
        for item in items:
            title = item.get('name', '') or item.get('title', '')
            if not title:
                continue
            content = item.get('summary', '') or ''
            pub_time_long = item.get('pubTimeLong', '')
            pub_time = item.get('pubTime', '')
            if pub_time_long and str(pub_time_long).isdigit():
                try:
                    pub_time = datetime.fromtimestamp(int(pub_time_long) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OSError):
                    pass
            cont_id = item.get('contId', '')
            url = f'https://www.thepaper.cn/newsDetail_forward_{cont_id}' if cont_id else ''
            results.append({
                'title': title,
                'content': content[:500],
                'time': str(pub_time),
                'source': '澎湃新闻',
                'url': url,
            })
    except Exception as e:
        print(f"[NewsCollector] 澎湃新闻采集失败: {e}")
    print(f"[NewsCollector] 澎湃新闻 采集 {len(results)} 条")
    return results[:limit]


# ---------------------------------------------------------------------------
# Source 7: 界面新闻
# ---------------------------------------------------------------------------
def _fetch_jiemian(limit: int = 20) -> List[Dict]:
    """通过界面新闻 AJAX 接口采集财经新闻"""
    if not HAS_BS4:
        print("[NewsCollector] beautifulsoup4 未安装，跳过界面新闻源")
        return []
    results = []
    try:
        resp = requests.get(
            'https://a.jiemian.com/index.php?m=index&a=indexAjax&page=2&lasttime=0&callback=',
            headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.jiemian.com/'},
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.text.strip()
        # 去除 JSONP 包裹
        if text.startswith('(') and text.endswith(')'):
            text = text[1:-1]
        data = json.loads(text) if text.startswith('{') or text.startswith('[') else {}
        # 确保 data 是字典，如果是列表则使用 text
        if isinstance(data, dict):
            html = data.get('data', data.get('html', text))
        else:
            html = text
        if not isinstance(html, str):
            html = str(html)
        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            href = a_tag['href']
            if not href.startswith('http'):
                href = f'https://www.jiemian.com{href}'
            results.append({
                'title': title,
                'content': '',
                'time': '',
                'source': '界面新闻',
                'url': href,
            })
    except Exception as e:
        print(f"[NewsCollector] 界面新闻采集失败: {e}")
    print(f"[NewsCollector] 界面新闻 采集 {len(results)} 条")
    return results[:limit]


# ---------------------------------------------------------------------------
# Source 8: 财新
# ---------------------------------------------------------------------------
def _fetch_caixin(limit: int = 20) -> List[Dict]:
    """通过财新首页 HTML 采集财经新闻"""
    if not HAS_BS4:
        print("[NewsCollector] beautifulsoup4 未安装，跳过财新源")
        return []
    results = []
    try:
        resp = requests.get(
            'https://www.caixin.com/',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag['href']
            if not title or len(title) < 8 or not href.startswith('http'):
                continue
            if 'caixin.com' not in href:
                continue
            # 避免导航链接
            if any(kw in href for kw in ('/channel/', '/about/', '/user/', '/search')):
                continue
            results.append({
                'title': title,
                'content': '',
                'time': '',
                'source': '财新',
                'url': href,
            })
    except Exception as e:
        print(f"[NewsCollector] 财新采集失败: {e}")
    # 去重（同页面可能有重复链接）
    seen = set()
    unique = []
    for item in results:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    print(f"[NewsCollector] 财新 采集 {len(unique)} 条")
    return unique[:limit]


# ---------------------------------------------------------------------------
# Source 9: 观察者网
# ---------------------------------------------------------------------------
def _fetch_guancha(limit: int = 20) -> List[Dict]:
    """通过观察者网经济频道 HTML 采集财经新闻"""
    if not HAS_BS4:
        print("[NewsCollector] beautifulsoup4 未安装，跳过观察者网源")
        return []
    results = []
    try:
        resp = requests.get(
            'https://www.guancha.cn/economy',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag['href']
            if not title or len(title) < 8:
                continue
            if not href.startswith('http'):
                href = f'https://www.guancha.cn{href}'
            if 'guancha.cn' not in href:
                continue
            # 从 URL 提取日期 (格式: YYYY_MM_DD)
            date_match = re.search(r'(\d{4})_(\d{2})_(\d{2})', href)
            pub_time = f'{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}' if date_match else ''
            results.append({
                'title': title,
                'content': '',
                'time': pub_time,
                'source': '观察者网',
                'url': href,
            })
    except Exception as e:
        print(f"[NewsCollector] 观察者网采集失败: {e}")
    seen = set()
    unique = []
    for item in results:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    print(f"[NewsCollector] 观察者网 采集 {len(unique)} 条")
    return unique[:limit]


# ---------------------------------------------------------------------------
# 去重合并
# ---------------------------------------------------------------------------
def _normalize_title(title: str) -> str:
    """标题标准化：去标点、空格"""
    return re.sub(r'[\s\u3000\W]+', '', title)


def _deduplicate(news_list: List[Dict]) -> List[Dict]:
    """
    去重策略:
    1. 标题标准化后精确匹配
    2. SequenceMatcher 相似度 > 0.75 视为重复
    重复时保留内容更长的版本
    """
    seen_titles = {}  # normalized_title -> index in result
    result = []

    for item in news_list:
        title = item.get('title', '')
        if not title:
            continue

        norm = _normalize_title(title)
        if not norm:
            continue

        # 精确匹配
        if norm in seen_titles:
            idx = seen_titles[norm]
            if len(item.get('content', '')) > len(result[idx].get('content', '')):
                result[idx] = item
            continue

        # 相似度匹配
        is_dup = False
        for existing_norm, idx in seen_titles.items():
            if SequenceMatcher(None, norm, existing_norm).ratio() > 0.75:
                if len(item.get('content', '')) > len(result[idx].get('content', '')):
                    result[idx] = item
                is_dup = True
                break

        if not is_dup:
            seen_titles[norm] = len(result)
            result.append(item)

    return result


# ---------------------------------------------------------------------------
# 入口函数
# ---------------------------------------------------------------------------
ALL_SOURCE_NAMES = [
    'DuckDuckGo', '东方财富', '新浪财经', 'AI Agent',
    '第一财经', '澎湃新闻', '界面新闻', '财新', '观察者网',
]

# 名称 → 函数名映射（运行时通过 globals() 查找，确保 mock 生效）
_SOURCE_FETCHER_MAP = {
    'DuckDuckGo': '_fetch_duckduckgo',
    '东方财富': '_fetch_eastmoney',
    '新浪财经': '_fetch_sina',
    'AI Agent': '_fetch_via_agent',
    '第一财经': '_fetch_yicai',
    '澎湃新闻': '_fetch_thepaper',
    '界面新闻': '_fetch_jiemian',
    '财新': '_fetch_caixin',
    '观察者网': '_fetch_guancha',
}


def collect_all_news(limit: int = 20, enabled_sources: List[str] = None) -> List[Dict]:
    """
    多源采集入口 — 九源独立采集 → 去重 → 按时间倒序

    Args:
        limit: 最终返回的新闻条数上限
        enabled_sources: 启用的源名称列表，None 表示全部启用

    Returns:
        [{title, content, time, source, url}, ...]
    """
    # None / [] / 无效来源 都视为全量来源，避免误触发单一源兜底
    if enabled_sources is not None:
        normalized_sources = [s for s in enabled_sources if s in ALL_SOURCE_NAMES]
        enabled_sources = normalized_sources or None

    sources_str = ', '.join(enabled_sources) if enabled_sources is not None else '全部'
    print(f"[NewsCollector] 开始采集新闻，来源: {sources_str}")
    
    all_news = []
    _g = globals()
    source_counts = {}

    for name in ALL_SOURCE_NAMES:
        if enabled_sources is not None and name not in enabled_sources:
            continue
        fetcher = _g[_SOURCE_FETCHER_MAP[name]]
        try:
            items = fetcher()
            all_news.extend(items)
            source_counts[name] = len(items)
        except Exception as e:
            print(f"[NewsCollector] {name} 采集异常: {e}")
            traceback.print_exc()
            source_counts[name] = 0

    for name, count in source_counts.items():
        print(f"[NewsCollector] {name} 完成，获取 {count} 条")

    print(f"[NewsCollector] 合并前总计 {len(all_news)} 条")

    deduped = _deduplicate(all_news)
    print(f"[NewsCollector] 去重后 {len(deduped)} 条")

    def _parse_time(item):
        t = item.get('time', '')
        if not t:
            return datetime.min
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S',
                    '%Y/%m/%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(t[:19], fmt)
            except (ValueError, TypeError):
                continue
        return datetime.min

    deduped.sort(key=_parse_time, reverse=True)
    
    final_count = len(deduped[:limit])
    print(f"[NewsCollector] 新闻采集完成，共 {final_count} 条")
    
    return deduped[:limit]


# ---------------------------------------------------------------------------
# 独立测试入口
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("多源新闻采集器 - 独立测试")
    print("=" * 60)

    news = collect_all_news(limit=20)

    print(f"\n最终采集 {len(news)} 条新闻:\n")
    for i, item in enumerate(news, 1):
        print(f"{i}. [{item['source']}] {item['title']}")
        print(f"   时间: {item['time']}")
        print(f"   链接: {item['url'][:80]}")
        print(f"   摘要: {item['content'][:60]}...")
        print()
