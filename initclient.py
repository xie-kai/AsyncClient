import warnings
from yarl import URL


DEFAULT_LIMIT   = 128
DEFAULT_TIMEOUT = 60
DEF_USER_AGENT  = "Mozilla/5.0 (Linux; Android 8.1.0; 16th Build/OPM1.171019.026; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/65.0.3325.110 Mobile Safari/537.36"



class InitAsyncClient:

    def __init__(
        self,
        base_url    = None,
        limit       = None,
        headers     = None,
        timeout     = None,
        encoded     = False,
        warn_switch = True,
        **kwargs
    ):
        """
        :params base_url    : 若存在base_url并且请求链接不是绝对路径会进行拼接 default: None
        :params limit       : 控制本度TCP同时连接数量 若同时请求太多访问被拒绝,请设置limit default: 100
        :params headers     : 请求头, 默认配置UserAgent在其中
        :params timeout     : 请求超时时间 若抛出超时异常,会重新请求 default: 60
        :params encoded     : URL编码 default: False
        :params warn_switch : 打印异常信息 default: False
        :params kwargs      : aiohttp.ClientSession() 参数
        """
        # encoded
        self._encoded = True if bool(encoded) else False

        # base_url
        self._base_url = None
        if isinstance(base_url, (str, URL)):
            base_url = URL(base_url, encoded=self._encoded)
            if base_url.is_absolute():
                self._base_url = base_url.origin()

        # limit
        self._limit = DEFAULT_LIMIT
        if isinstance(limit, int) and limit > 0:
            self._limit = limit

        # headers
        self._headers = {"user-agent": DEF_USER_AGENT}
        if isinstance(headers, dict):
            self._headers.update(headers)

        # timeout
        self._timeout = DEFAULT_TIMEOUT
        if isinstance(timeout, (int, float)) and timeout > 0:
            self._timeout = timeout

        # warn_switch
        self._warn_switch = True
        if bool(warn_switch) is False:
            self._warn_switch = False

        # aiohttp.ClientSesson 参数
        if kwargs.__contains__("connector"):
            warnings.warn(
                f"\n\033[33m{self.__class__.__name__} 'connector' 参数已弃用"
                "\n请使用 'limit' 将为您自动创建 connector\033[0m")
            kwargs.pop("connector")
        self._session_param = kwargs.copy()


    def _build_url(self, url):
        if not isinstance(url, URL):
            url = URL(url, encoded=self._encoded)
        if (
            self._base_url is not None
            and not url.is_absolute()
        ):
            return self._base_url.join(url)
        return url
