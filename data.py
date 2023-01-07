# coding: utf-8
import asyncio
import aiohttp
from yarl import URL


class AsyncHttpClientData:

    # 异步请求默认值
    LIMIT      = 100
    TIMEOUT    = 60
    HEADERS    = {"user-agent": "Mozilla/5.0 (Linux; Android 8.1.0; 16th Build/OPM1.171019.026) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.110 Mobile Safari/537.36"}
    # 请求错误休眠时间
    ESLEEP     = 2
    # 捕获异常并重试
    EXCEPTION  = (
        asyncio.exceptions.TimeoutError,
        aiohttp.client_exceptions.ClientConnectorError,
    )
    # 捕获请求异常状态码 并重新发送请求 直到成功
    CAPTURE_STATUS = tuple()

    def __init__(
        self,
        base_url : str  = None,
        limit    : int  = None,
        headers  : dict = None,
        timeout  : int  = None,
        encoded  : bool = False,
        sleep    : int  = None,
        cstatus  : int  = None,
        status_ok: bool = True,
        message  : bool = False
    ):
        """
        :params base_url  : 若存在base_url并且请求链接不是绝对路径会进行拼接 default: None
        :params limit     : 控制本度TCP同时连接数量 若同时请求太多访问被拒绝,请设置limit default: 100
        :params headers   : 请求头, 默认配置UserAgent在其中
        :params timeout   : 请求超时时间 若抛出超时异常,会重新请求 default: 60
        :params encoded   : URL编码 default: False
        :params sleep     : 每个请求休眠 asyncio.sleep(sleep) default: None
        :params cstatus   : 捕获请求状态码并重新发送请求
        :params status_ok : 循环发送请求直到状态码200结束 default: True
        :params message   : 打印异常信息 default: False
        """
        self._limit     = limit
        self._base_url  = base_url
        self._headers   = headers
        self._timeout   = timeout
        self._encoded   = bool(encoded) if encoded else False
        self._sleep     = sleep
        self._cstatus   = cstatus
        self._status_ok = bool(status_ok)
        self._message   = bool(message)
        self._initialization()


    def _initialization(self):
        # base_url
        if isinstance(self._base_url, (str, URL)) and self._base_url:
            _base_url = URL(self._base_url, encoded=self._encoded)
            if not _base_url.is_absolute():
                _base_url = None
            self._base_url = _base_url
        else:
            self._base_url = None

        # limit
        if not isinstance(self._limit, int) \
            or (isinstance(self._limit, int) and self._limit < 0):
            self._limit = self.LIMIT

        # timeout
        if not isinstance(self._timeout, (int, float)) \
            or (isinstance(self._timeout, (int, float)) and self._timeout < 0):
            self._timeout = self.TIMEOUT

        # headers
        if not isinstance(self._headers, dict) \
            or not self._headers:
            self._headers = self.HEADERS
        else:
            _headers = {str(k).lower(): v for k, v in self._headers.items()}
            if not _headers.__contains__("user-agent"):
                _headers.update(self.HEADERS)
            if self._headers != _headers:
                self._headers = _headers

        # sleep
        if isinstance(self._sleep, (int, float)):
            if self._sleep <= 0:
                self._sleep = None
        else:
            self._sleep = None

        # cstatus - 捕获请求状态码并重新发送请求
        _cstatus = self._cstatus
        # type(_cstatus) -> int
        if isinstance(_cstatus, int):
            _cstatus = [_cstatus]
        # type(_cstatus) -> list tuple
        elif isinstance(_cstatus, (list, tuple)):
            _cstatus = [int(item) for item in _cstatus if str(item).isdigit()]
        else:
            _cstatus = []
        _cstatus.extend(self.CAPTURE_STATUS)
        self._cstatus = list(set(_cstatus))


    def _build_url_set(self, urls):
        iter_type = (list, tuple, set, frozenset)
        # type(urls) -> str or URL
        if isinstance(urls, (str, URL)):
            urls = {str(0): {"url": self._build_url(urls)}}

        # type(urls) -> iter_type
        elif isinstance(urls, iter_type):
            urls = {
                str(i): {"url": self._build_url(_url)}
                    for i, _url in enumerate(urls)
            }

        # type(urls) -> dict
        elif isinstance(urls, dict):
            for key, val in urls.items():
                _val = None
                # type(val) -> str or URL
                if isinstance(val, (str, URL)):
                    _val = self._build_url(val)
                # type(val) -> iter_type
                elif isinstance(val, iter_type):
                    _val = self._build_url(val[0])
                # type(val) -> dict
                elif isinstance(val, dict):
                    # 不符合设定格式
                    if not val.__contains__("url"):
                        error_message   = "\n{'key':\n\t{'url': 'http://...',\n\t 'headers': ...}\n}"
                        error_parameter = f"your params:\n{{'{key}':\n\t{val}\n}}\n\033[0m"
                        raise ValueError(
                            "\n\033[31m{self.__class__.__name__}.requests parameter 'urls' format:"
                            f"{error_message}\n"
                            f"{error_parameter}")
                    val["url"] = self._build_url(val["url"])
                # type(val) -> 不符合格式 raise TypeError
                else:
                    raise TypeError(
                        f"\033[31m{self.__class__.__name__}.requests 'urls' format exception\n"
                        f"value: {val} - type: '{type(val).__name__}'\033[0m")

                # 更新数据 到字典
                if _val is not None and val != _val:
                    urls[key] = {"url": _val}

        # type(urls) -> 不符合格式 raise TypeError
        else:
            raise TypeError(
                f"\033[31m{self.__class__.__name__}.requests 'urls' format exception\n"
                f"urls: '{urls}'\ntype: '{type(urls).__name__}'\033[0m")
        return urls


    def _build_url(self, url):
        url = URL(url, encoded=self._encoded)
        if self._base_url is None \
            or not self._base_url.is_absolute() \
            or url.is_absolute():
            return url
        else:
            return self._base_url.join(url)


    def _set_session_parameter(self, **kwargs):
        # warning: connector 应该在异步函数中创建，不建议通过参数传递
        if kwargs.__contains__("connector"):
            kwargs.pop("connector")
            warnings.warn(
                f"\033[33m{self.__class__.__name__}.requests 'connector' 不建议通过参数传递"
                "请使用'limit'将为你自动创建 connector\033[0m")

        # 获取默认参数
        base_url = kwargs.pop("base_url") if kwargs.__contains__("base_url") else None
        limit    = kwargs.pop("limit") if kwargs.__contains__("limit") else None
        headers  = kwargs.get("headers")
        timeout  = kwargs.pop("timeout") if kwargs.__contains__("timeout") else None

        # base_url
        if isinstance(base_url, (str, URL)) and base_url:
            base_url = URL(base_url, encoded=self._encoded)
            if base_url.is_absolute():
                self._base_url = base_url

        # limit update
        if isinstance(limit, int) \
            and not limit < 0 \
            and limit != self._limit:
            self._limit = limit

        # timeout update
        if isinstance(timeout, (int, float)) \
            and not timeout < 0 \
            and timeout != self._timeout:
            self._timeout = timeout

        # headers update
        if isinstance(headers, dict) and headers:
            self._headers.update(headers)
        # 创建session连接池参数
        kwargs["timeout"]   = aiohttp.ClientTimeout(total=self._timeout)
        kwargs["headers"]   = self._headers
        kwargs["connector"] = aiohttp.TCPConnector(limit=self._limit)
        return kwargs


    def _set_request_parameter(self, url, **kwargs):
        if not isinstance(url, URL):
            url = self._build_url(url)
        kwargs["url"] = url
        # parameters - method
        method  = kwargs.get("method")
        if isinstance(method, str):
            # 检测请求方式是否输入正确
            if method.upper() not in aiohttp.hdrs.METH_ALL:
                kwargs["method"] = "GET"
            if method != method.upper():
                kwargs["method"] = method.upper()
        else:
            kwargs["method"] = "GET"
        return kwargs
