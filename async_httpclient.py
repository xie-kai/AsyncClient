# coding: utf-8

import warnings
import asyncio
import aiohttp
from yarl import URL


__all__ = ["AsyncHttpClient", "asyncio", "aiohttp"]


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
        """
        self._limit     = limit
        self._base_url  = base_url
        self._headers   = headers
        self._timeout   = timeout
        self._encoded   = bool(encoded) if encoded else False
        self._sleep     = sleep
        self._cstatus   = cstatus
        self._status_ok = bool(status_ok)
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
                # type(urls) -> str or URL
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


    def _set_session_parameter(self, kwargs):
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


    def _set_request_parameter(self, url, parameters):
        parameters["url"] = url
        # parameters - method
        method  = parameters.get("method")
        if isinstance(method, str):
            # 检测请求方式是否输入正确
            if method.upper() not in aiohttp.hdrs.METH_ALL:
                parameters["method"] = "GET"
            if method != method.upper():
                parameters["method"] = method.upper()
        else:
            parameters["method"] = "GET"



class AsyncHttpClient(AsyncHttpClientData):
    """https://docs.aiohttp.org/en/stable/client_quickstart.html"""

    async def gather_request(
        self,
        urls,
        custom_parse=None,
        item=None,
        encoded=False,
        sleep=None,
        cstatus=None,
        status_ok=None,
        **kwargs
    ):
        """
        :params urls         : 异步请求的所有URL type: str, list, dict
        :params custom_parse : 自定义解析方法(注意: 函数必须是异步函数)
        :params item         : 保存数据的字典, 数据来源custom_parse函数返回值
        :params encoded      : URL编码 default: False
        :params sleep        : 每个请求休眠 asyncio.sleep(sleep)
        :params cstatus      : 捕获请求状态码并重新发送请求
        :params status_ok    : 循环发送请求直到状态码200停止 default: True

        urls - type(urls) -> dict: format:
        urls = {
            'key': {
                'url'     : 'https://xxx',
                'headers' : 'dict()',
                'xxx'     : 'xxx'
            }
        }

        # 注意: urls[key]['url'] 为必需键
        # 'key' 将用于item字典的键 
        # item为当前方法返回值(所有解析结果存放与item) 可使用custom_parse自定义解析结果
        # 有时，如果服务器接受准确的表示而不重新引用URL本身，则规范化是不可取的
        # 禁用规范化使用 encoded=True 参数进行URL构造:
        """

        # URL编码
        if bool(encoded) is not self._encoded:
            self._encoded = bool(encoded)
        # item是运行完成返回的结果
        if not isinstance(item, dict):
            item = {}
        # 设置 aiohttp session 参数 配置连接池
        self._set_session_parameter(kwargs)
        # 构建urls
        urls = self._build_url_set(urls)
        # 休眠时间 sleep
        if isinstance(sleep, (int, float)) and sleep > 0:
            self._sleep = sleep
        # 请求状态码捕获
        if isinstance(cstatus, int):
            self._cstatus.append(cstatus)
        elif isinstance(cstatus, (list, tuple)):
            cstatus = [int(item) for item in _cstatus if str(item).isdigit()]
            self._cstatus.extend(cstatus)
        self._cstatus = tuple(set(self._cstatus))
        if status_ok is not None:
            self._status_ok = bool(status_ok)
        # 开启异步session连接池
        async with aiohttp.ClientSession(**kwargs) as session:
            # url地址包含在item字典中
            tasks = [
                self.request(
                    key=key,
                    session=session,
                    custom_parse=custom_parse,
                    item=item,
                    **_item
                )
                    for key, _item in urls.items()
            ]
            # 收集所有异步任务
            await asyncio.gather(*tasks)
        return item


    async def request(
        self,
        url,
        session=None,
        key=None,
        custom_parse=None,
        item=None,
        resp_close=True,
        **kwargs
    ):
        """
        :params url          : 异步请求URL type: str or yarl.URL
        :params session      : 异步请求连接池 aiohttp.ClientSession()
        :params custom_parse : 自定义解析方法(注意: 函数必须是异步函数)
        :params item         : 保存数据的字典, 数据来源custom_parse函数返回值
        :params resp_close   : 是否关闭response default: True

        # 关闭之后的 response 无法使用 await
        # await response.text(), await response.read(), await response.content.read(size)
        """

        # 判断session是否可用
        # 不建议直接使用send_request 因为它会为每个请求创建一个ClientSession()
        if not isinstance(session, aiohttp.ClientSession):
            new_session = {}
            self._set_session_parameter(new_session)
            # 创建session
            session = aiohttp.ClientSession(**new_session)
        else:
            new_session = False

        try:
            # Response
            response = await self._resquest(session, url, kwargs, new_session)
            # 休眠sleep
            if self._sleep is not None:
                await asyncio.sleep(self._sleep)
            # 解析请求内容 可以自定义解析函数(注意: 函数必须是异步函数)
            if callable(custom_parse):
                content = await custom_parse(
                    session=session,
                    response=response,
                    key=key,
                    instance=self,
                    request=kwargs)

            else:
                content = await self._parse_request(
                    session=session,
                    response=response,
                    key=key,
                    instance=self,
                    request=kwargs)

            # 保存内容
            if isinstance(item, dict) and content is not None:
                if key is None:
                    key = str(0)
                item[key] = content
            # 关闭Response
            if resp_close:
                response.close()
        finally:
            # 将创建的Session关闭
            if new_session is not False:
                await session.close()
        return response


    async def _resquest(self, session, url, parameters, new_session):
        # 为每个请求设置默认参数
        self._set_request_parameter(url, parameters)
        while True:
            try:
                response = await session.request(**parameters)
                status, status_ok   = response.status, self._status_ok
                # 状态码判断
                if str(status).startswith("4"):
                    raise aiohttp.client_exceptions.InvalidURL(
                        f"\nstatus code: \033[31m{status}\033[0m"
                        f"\n{url}"
                    )

                # 请求状态码 捕获
                if status_ok and status==200:
                    status_ok = False
                if status in self._cstatus or status_ok:
                    print(f"\r\033[31mresponse status: {response.status}\033[0m", end="")
                    await asyncio.sleep(self.ESLEEP)
                    continue

                # 返回Response
                return response

            except self.EXCEPTION as error:
                print(f"\r\033[31merror: {error}\033[0m", end="")
                await asyncio.sleep(self.ESLEEP)


    async def _parse_request(self, response, **kwrags):
        # 不知道做些什么, 就返回response吧
        return response


    def get(self, url, custom_parse=None, allow_redirects=True, **kwargs):
        return asyncio.run(
            self.request(
                method="GET",
                url=url,
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs))


    def post(self, url, custom_parse=None, allow_redirects=True, **kwargs):
        return asyncio.run(
            self.request(
                method="POST",
                url=url,
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs))


    def head(self, url, custom_parse=None, allow_redirects=True, **kwargs):
        return asyncio.run(
            self.request(
                method="HEAD",
                url=url,
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs))
