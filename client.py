import asyncio
import warnings

from aiohttp import (
    hdrs,
    TCPConnector,
    ClientSession,
    ClientTimeout,
    client_exceptions
)

from .initclient import InitAsyncClient


EXCEPT_SLEEP   = 2
DEFAULT_METHOD = "GET"



class AsyncClientSession(InitAsyncClient):

    async def client_session(
        self,
        method,
        url,
        *,
        warn_switch    = None,
        custom_parse   = None,
        sleep          = None,
        status_ok      = False,
        status_capture = None,
        **kwargs
    ):
        """
        :params method         : 所有url的请求方式 或者 在参数 'url' 中单独设置
        :params url            : 异步请求所有 url - type: str, list, dict
        :params warn_switch    : 输出警告信息 default: True
        :params custom_parse   : 自定义解析方法 (请注意: 函数必须是异步函数)
        :params sleep          : 请求休眠 asyncio.sleep(sleep)
        :params status_ok      : 循环发送请求直到状态码200停止 default: False
        :params status_capture : 捕获请求状态码并重新发送请求
        :params kwargs         : 每个请求的参数 或者 在参数 'url' 中单独设置

        url - type(url) -> 'list' or 'tuple':
         - url = [ "https://xxx.xxx", ... ]
         - url = [ ("https://xxx.xxx", {'timeout': 5}), ... ]

        url - type(url) -> 'dict':
         - url = { "key": ("https://xxx.xxx", {"timeout": 5}), ... }
         - url = { "key": {"url": "https://xxx.xxx", {"timeout": 5}}, ... }

         - 注意: url["key"]["url"] 为必需键 或者使用元组 ("http://xxx.xxx", {key: val})
         - 'key' 将用于该方法返回值 字典的键
        """

        # 捕获请求异常状态码
        if isinstance(status_capture, (int, list, tuple)):
            if isinstance(status_capture, int):
                status_capture = (status_capture, )
            status_capture = set(
                int(item) for item in status_capture
                    if str(item).isdigit())
        else:
            status_capture = set()

        # 警告信息开关
        if (
            warn_switch is not None
            and bool(warn_switch) is not self._warn_switch
        ):
            self._warn_switch = bool(warn_switch)

        # 异步session配置
        timeout   = ClientTimeout(total=self._timeout)
        connector = TCPConnector(limit=self._limit)

        # 开启异步session连接池
        async with ClientSession(
            timeout   = timeout,
            connector = connector,
            headers   = self._headers,
            **self._session_param
        ) as session:
            # 格式化 url 为统一格式
            # url = { key: ( url, {url_params} ) }
            url = self._format_url(method, url, **kwargs)
            # 休眠时间
            if not (
                isinstance(sleep, (int, float))
                and sleep > 0
                and len(url) > 2
            ):
                sleep = None

            tasks = [
                self._send_request(
                    session,
                    url = url_item[0],
                    key = key,
                    sleep = sleep,
                    custom_parse = custom_parse,
                    status_ok = bool(status_ok),
                    status_capture = status_capture,
                    **url_item[1]
                )
                    for key, url_item in url.items()
            ]
            # 开启异步任务
            result = await asyncio.gather(*tasks)
            result = {key: result[index] for index, key in enumerate(url.keys())}
        return result


    async def _send_request(
        self,
        session,
        method,
        url,
        *,
        custom_parse   = None,
        status_ok      = False,
        status_capture = None,
        key   = None,
        sleep = None,
        **kwargs
    ):
        while True:
            try:
                async with session.request(method=method, url=url, **kwargs) as response:

                    # 状态码捕获 不符合要求重新发送请求
                    if not self._response_status(response, bool(status_ok), status_capture):
                        await asyncio.sleep(EXCEPT_SLEEP)
                        continue

                    # 使用 自定义函数 解析请求
                    content = response
                    if callable(custom_parse):
                        request = kwargs.copy()
                        request["method"] = method

                        content = await custom_parse(
                            session=session, response=response,
                            request=request, instance=self,
                            url=url, key=key)

                    # 请求休眠
                    if sleep is not None:
                        await asyncio.sleep(sleep)
                    return content

            # 请求超时 重试
            except asyncio.exceptions.TimeoutError:
                if self._warn_switch:
                    timeout = kwargs["timeout"] \
                        if kwargs.__contains__("timeout") \
                            else session.timeout.total
                    warnings.warn(
                        f"\033[33m'{url.human_repr()}' timeout: '{timeout}'\033[0m")
                await asyncio.sleep(EXCEPT_SLEEP)

            # 连接错误 重试
            except (
                client_exceptions.ClientOSError,
                client_exceptions.ClientConnectorError,
            ) as error:
                if self._warn_switch:
                    warnings.warn(
                        f"\033[33m'{url.human_repr()}' client_error: '{error}'\033[0m")
                await asyncio.sleep(EXCEPT_SLEEP)


    def _response_status(self, response, status_ok, status_capture):
        status = response.status
        # 4xx 状态码
        if str(status).startswith("4"):
            raise client_exceptions.InvalidURL(f"\033[31m{response.url} status: {status}\033[0m")

        if (
            status_ok is True and status != 200
            or (status_ok is False and status in status_capture)
        ):
            # 捕获状态码 发出警告
            if self._warn_switch:
                if self._warn_switch:
                    warnings.warn(
                        f"\033[33m'{response.url.human_repr()}' status: '{status}' \033[0m")
            return False
        return True


    def _format_url(self, method, url, **kwargs):

        kwargs.setdefault("method", self._init_method(method))
        # type(url) == 'str'
        if isinstance(url, str):
            url = {"0": (self._build_url(url), kwargs)}

        # type(url) == 'list' or 'tuple' or 'type'
        elif isinstance(url, (dict, list, tuple)):
            if isinstance(url, (list, tuple)):
                url = {str(index): _url for index, _url in enumerate(url)}
            url = {key: self._url_and_params(item, **kwargs) for key, item in url.items()}

        # type(url) == undefined
        else:
            raise ValueError(f"\033[31m无效数据: {url}\033[0m")
        return url


    def _init_method(self, method):
        if (
            isinstance(method, str)
            and method.upper() in hdrs.METH_ALL
        ):
            return method.upper()
        return DEFAULT_METHOD


    def _url_and_params(self, url_item, **kwargs):

        # type(url_item) == 'str'
        if isinstance(url_item, str):
            url_item = (self._build_url(url_item), kwargs)

        # type(url_item) == 'list' or 'tuple'
        elif isinstance(url_item, (list, tuple)):
            if not url_item:
                raise ValueError(f"\033[31m无效数据: {url_item}\033[0m")
            if (
                len(url_item) >= 2
                and isinstance(url_item[1], dict)
            ):
                kwargs.update(url_item[1])
            url_item = (self._build_url(url_item[0]), kwargs)

        # type(url_item) == 'dict'o
        elif (
            isinstance(url_item, dict)
            and url_item.__contains__("url")
        ):
            url = url_item.pop("url")
            kwargs.update(url_item)
            url_item = (self._build_url(url), kwargs)

        # other
        else:
            raise TypeError(f"\033[31m无效数据: {url_item}\033[0m")
        return url_item
