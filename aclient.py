# coding: utf-8
import warnings
import asyncio
import aiohttp
from .data import AsyncHttpClientData


__all__ = ["AsyncHttpClient"]


class AsyncHttpClient(AsyncHttpClientData):
    """https://docs.aiohttp.org/en/stable/client_quickstart.html"""

    async def gather_request(
        self,
        urls,
        custom_parse=None,
        encoded=False,
        sleep=None,
        cstatus=None,
        status_ok=None,
        **kwargs
    ):
        """
        :params urls         : 异步请求所有URL type: str, list, dict
        :params custom_parse : 自定义解析方法 (请注意: 函数必须是异步函数)
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
        # 'key' 将用于该方法返回值 字典的键
        # 可使用custom_parse自定义解析结果
        # 有时，如果服务器接受准确的表示而不重新引用URL本身，则规范化是不可取的
        # 禁用规范化使用 encoded=True 参数进行URL构造:
        """

        # URL编码
        if bool(encoded) is not self._encoded:
            self._encoded = bool(encoded)
        # 设置 aiohttp session 参数 配置连接池
        session_params = self._set_session_parameter(**kwargs)
        # 构建urls
        urls = self._build_url_set(urls)
        # 休眠时间 sleep
        if isinstance(sleep, (int, float)) and sleep > 0:
            self._sleep = sleep
        # 请求状态码捕获
        if isinstance(cstatus, int):
            self._cstatus.append(cstatus)
        elif isinstance(cstatus, (list, tuple)):
            cstatus = [int(item) for item in cstatus if str(item).isdigit()]
            self._cstatus.extend(cstatus)
        self._cstatus = tuple(set(self._cstatus))
        # status_ok
        if status_ok is not None:
            self._status_ok = bool(status_ok)
        # 开启异步session连接池
        async with aiohttp.ClientSession(**session_params) as session:
            # url地址包含在item字典中
            tasks = [
                self.request(
                    key=key,
                    session=session,
                    custom_parse=custom_parse,
                    **_item
                )
                    for key, _item in urls.items()
            ]
            # 收集所有异步任务 gather返回结果顺序为 tasks 传入顺序
            tasks_result = await asyncio.gather(*tasks)
            tasks_result = {
                key: tasks_result[index]
                    for index, key in enumerate(urls.keys())
            }
        return tasks_result


    async def request(
        self,
        url,
        session=None,
        custom_parse=None,
        key=None,
        status_ok=None,
        read=False,
        **kwargs
    ):
        """
        :params url          : 异步请求URL type: str or yarl.URL
        :params session      : 异步请求连接池 aiohttp.ClientSession()
        :params custom_parse : 自定义解析方法(注意: 函数必须是异步函数)
        :params key          : key 用于自定义方法 custom_parse 的关键字参数
        :params read         : 返回值 (response, read) read= await response.read()
                               数据量过大不建议开启 default: False

        # 判断session是否可用 不可用创建 session
        # 不建议直接使用request
        # 因为它会为每个请求创建一个ClientSession()
        """
        _new_session = False
        if not isinstance(session, aiohttp.ClientSession):
            session = aiohttp.ClientSession(**self._set_session_parameter())
            _new_session = True
        # status_ok
        if status_ok is not None:
            self._status_ok = bool(status_ok)
        try:
            content = await self._request(
                url, session, key, custom_parse, bool(read), **kwargs)
        finally:
            # 关闭创建的session
            if _new_session is True:
                await session.close()
        return content


    async def _request(
        self,
        url,
        session=None,
        key=None,
        custom_parse=None,
        read=False,
        **kwargs
    ):
        # 获取请求参数 type -> dict
        request_params = self._set_request_parameter(url, **kwargs)
        while True:
            try:
                async with session.request(**request_params) as response:
                    # 请求状态码 异常
                    if not await self._parse_status(url, response):
                        await asyncio.sleep(self.ESLEEP)
                        continue
                    # 解析 response 内容
                    content = await self._parse_response(
                        response=response, session=session,
                        custom_parse=custom_parse, key=key,
                        request=request_params)
                    # read数据
                    if read is True:
                        return (response, await response.read())
                    return content

            except self.EXCEPTION as error:
                if self._message is True:
                    warnings.warn(
                        f"\033[31merror: {error}\033[0m")
                await asyncio.sleep(self.ESLEEP)


    async def _parse_status(self, url, response):

        status, status_ok = response.status, self._status_ok
        # 状态码判断
        if str(status).startswith("4"):
            raise aiohttp.client_exceptions.InvalidURL(
                f"\nstatus code: \033[31m{status}\033[0m"
                f"\n{url}")
        # 请求状态码 捕获
        if status_ok and status==200:
            status_ok = False

        if status in self._cstatus or status_ok:
            if self._message is True:
                warnings.warn(
                    f"\033[31mresponse status: {response.status}\033[0m")
            return False
        return True


    async def _parse_response(self, response, custom_parse, **kwargs):
        if not callable(custom_parse):
            return response

        # 使用自定义解析函数(注意: 函数必须是异步函数)
        return await custom_parse(response=response, instance=self, **kwargs)


    def get(self, url, custom_parse=None, allow_redirects=True, read=False, **kwargs):
        return asyncio.run(
            self.request(
                method="GET",
                url=url,
                read=bool(read),
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs))


    def post(self, url, custom_parse=None, allow_redirects=True, read=False, **kwargs):
        return asyncio.run(
            self.request(
                method="POST",
                url=url,
                read=bool(read),
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs))


    def head(self, url, custom_parse=None, allow_redirects=True, read=False, **kwargs):
        return asyncio.run(
            self.request(
                method="HEAD",
                url=url,
                read=bool(read),
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs))
