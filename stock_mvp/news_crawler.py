"""
国际财经新闻爬虫 - 金十数据 & 华尔街见闻
"""
import requests
from typing import List, Dict
from datetime import datetime



# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.jin10.com/',
}


def crawl_jin10_news(limit: int = 10) -> List[Dict[str, str]]:
    """
    金十数据快讯爬取
    
    Returns:
        [{"title": ..., "time": ..., "source": "jin10", "url": ...}]
    """
    news_list = []
    
    # 尝试多个可能的接口
    endpoints = [
        ('https://flash-api.jin10.com/get_flash_list', {'channel': '-1', 'vip': '1'}),
        ('https://rmdex.jin10.com/data.json', {}),
    ]
    
    for url, params in endpoints:
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # 解析数据
                items = []
                if isinstance(data, dict):
                    if 'data' in data:
                        items = data['data']
                    elif 'list' in data:
                        items = data['list']
                elif isinstance(data, list):
                    items = data
                
                for item in items[:limit]:
                    try:
                        title = item.get('title') or item.get('content') or item.get('text', '')
                        # 处理时间
                        time_str = item.get('time') or item.get('created_at') or item.get('publish_time', '')
                        if isinstance(time_str, (int, float)):
                            # 时间戳
                            time_str = datetime.fromtimestamp(time_str/1000).strftime('%Y-%m-%d %H:%M')
                        elif isinstance(time_str, str) and time_str:
                            # 解析各种时间格式
                            try:
                                dt = datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')
                                time_str = dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                time_str = time_str[:16]
                        
                        url_link = item.get('url') or f"https://www.jin10.com/detail/{item.get('id', '')}"
                        
                        if title:
                            news_list.append({
                                'title': title.strip(),
                                'time': time_str,
                                'source': 'jin10',
                                'url': url_link
                            })
                    except Exception:
                        continue
                
                if news_list:
                    break
                    
        except Exception as e:
            print(f"Jin10 接口 {url} 请求失败: {e}")
            continue
    
    return news_list[:limit]


def crawl_wallstreetcn_news(limit: int = 10) -> List[Dict[str, str]]:
    """
    华尔街见闻新闻爬取
    
    Returns:
        [{"title": ..., "time": ..., "source": "wallstreetcn", "url": ...}]
    """
    news_list = []
    
    # 尝试多个接口
    endpoints = [
        'https://api-one.wallstreetcn.com/apiv1/content/articles?channel=global-channel&limit=20',
        'https://api-one.wallstreetcn.com/apiv1/content/articles?limit=20',
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # 解析数据
                items = []
                if isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], dict):
                        items = data['data'].get('items', []) or data['data'].get('articles', [])
                    elif 'data' in data and isinstance(data['data'], list):
                        items = data['data']
                elif isinstance(data, list):
                    items = data
                
                for item in items[:limit]:
                    try:
                        title = item.get('title') or item.get('text', '')
                        # 处理时间
                        time_str = item.get('publish_time') or item.get('created_at') or item.get('display_time', '')
                        if isinstance(time_str, (int, float)):
                            time_str = datetime.fromtimestamp(time_str).strftime('%Y-%m-%d %H:%M')
                        elif isinstance(time_str, str) and time_str:
                            try:
                                # 尝试解析时间
                                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']:
                                    try:
                                        dt = datetime.strptime(time_str[:19], fmt)
                                        time_str = dt.strftime('%Y-%m-%d %H:%M')
                                        break
                                    except:
                                        continue
                            except:
                                time_str = time_str[:16]
                        
                        url_link = item.get('url') or item.get('share_url') or f"https://wallstreetcn.com/articles/{item.get('id', '')}"
                        
                        if title:
                            news_list.append({
                                'title': title.strip(),
                                'time': time_str,
                                'source': 'wallstreetcn',
                                'url': url_link
                            })
                    except Exception:
                        continue
                
                if news_list:
                    break
                    
        except Exception as e:
            print(f"Wallstreetcn 接口请求失败: {e}")
            continue
    
    return news_list[:limit]


def get_international_news(limit: int = 10) -> List[Dict[str, str]]:
    """
    获取国际财经新闻 - 合并多个来源
    
    Args:
        limit: 每个来源返回的新闻数量
    
    Returns:
        [{"title": ..., "time": ..., "source": "...", "url": ...}]
    """
    all_news = []
    
    # 并行爬取
    try:
        jin10_news = crawl_jin10_news(limit)
        all_news.extend(jin10_news)
    except Exception as e:
        print(f"金十数据爬取失败: {e}")
    
    try:
        wallstreetcn_news = crawl_wallstreetcn_news(limit)
        all_news.extend(wallstreetcn_news)
    except Exception as e:
        print(f"华尔街见闻爬取失败: {e}")
    
    # 按时间排序
    all_news.sort(key=lambda x: x.get('time', ''), reverse=True)
    
    return all_news[:limit]


if __name__ == '__main__':
    # 测试
    print("测试金十数据...")
    news1 = crawl_jin10_news(5)
    print(f"获取到 {len(news1)} 条金十快讯")
    for n in news1[:3]:
        print(f"  [{n['time']}] {n['title'][:50]}...")
    
    print("\n测试华尔街见闻...")
    news2 = crawl_wallstreetcn_news(5)
    print(f"获取到 {len(news2)} 条华尔街见闻新闻")
    for n in news2[:3]:
        print(f"  [{n['time']}] {n['title'][:50]}...")
    
    print("\n测试合并...")
    news = get_international_news(10)
    print(f"共获取到 {len(news)} 条国际财经新闻")
    for n in news[:5]:
        print(f"  [{n['source']}] [{n['time']}] {n['title'][:40]}")
