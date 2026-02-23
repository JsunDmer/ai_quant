"""
AKShare 网络兼容补丁

修复东方财富 CDN 节点 (如 17.push2.eastmoney.com) SSL 握手失败问题，
将带编号的子域名统一重定向到 push2.eastmoney.com 主域名。
"""
import re
import requests

_original_get = requests.Session.get
_patched = False


def _patched_get(self, url, **kwargs):
    if isinstance(url, str) and '.push2.eastmoney.com' in url:
        url = re.sub(r'https?://\d+\.push2\.eastmoney\.com', 'https://push2.eastmoney.com', url)
    return _original_get(self, url, **kwargs)


def patch():
    """应用补丁，幂等调用安全"""
    global _patched
    if not _patched:
        requests.Session.get = _patched_get
        _patched = True
