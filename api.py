import asyncio
from .client import AsyncClientSession


class AsyncClient(AsyncClientSession):

    def request(self, method, url, *, custom_parse=None, allow_redirects=True, **kwargs):

        result = asyncio.run(
            self.client_session(
                method,
                url,
                custom_parse=custom_parse,
                allow_redirects=allow_redirects,
                **kwargs
            )
        )
        return result


    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)


    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


    def gather(self, url, method=None, **kwargs):
        return self.request(method, url, **kwargs)
