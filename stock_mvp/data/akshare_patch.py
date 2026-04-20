"""AKShare 网络兼容补丁 - 修复东方财富 API 代理问题；消除 datasets 对 resources.path 的弃用告警"""
import pathlib
import re
from importlib import resources

import requests

_original_get = requests.Session.get
_original_request = requests.Session.request
_patched = False
_datasets_patched = False


def _patch_akshare_datasets() -> None:
    """用 importlib.resources.files 替换 akshare.datasets 中的 path()，避免 Python 3.12+ DeprecationWarning。"""
    global _datasets_patched
    if _datasets_patched:
        return
    import akshare.datasets as ds

    def _pkg_data_path(filename: str) -> pathlib.Path:
        return pathlib.Path(resources.files("akshare.data").joinpath(filename))

    def get_ths_js(file: str = "ths.js") -> pathlib.Path:
        return _pkg_data_path(file)

    def get_crypto_info_csv(file: str = "crypto_info.zip") -> pathlib.Path:
        return _pkg_data_path(file)

    ds.get_ths_js = get_ths_js
    ds.get_crypto_info_csv = get_crypto_info_csv
    _datasets_patched = True


def _patched_get(self, url, **kwargs):
    if isinstance(url, str) and '.push2.eastmoney.com' in url:
        url = re.sub(r'https?://\d+\.push2\.eastmoney\.com', 'https://push2.eastmoney.com', url)
    if not hasattr(self, '_proxy_disabled'):
        self.trust_env = False
        self._proxy_disabled = True
    return _original_get(self, url, **kwargs)


def _patched_request(self, method, url, **kwargs):
    if isinstance(url, str) and '.push2.eastmoney.com' in url:
        url = re.sub(r'https?://\d+\.push2\.eastmoney\.com', 'https://push2.eastmoney.com', url)
    if not hasattr(self, '_proxy_disabled'):
        self.trust_env = False
        self._proxy_disabled = True
    return _original_request(self, method, url, **kwargs)


def patch():
    global _patched
    _patch_akshare_datasets()
    if not _patched:
        requests.Session.get = _patched_get
        requests.Session.request = _patched_request
        _original_get = requests.Session.get
        _patched = True