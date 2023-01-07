# aclient

##  安装说明

使用`pip`或其他 PyPi 软件包进行安装

```
pip install aclient
```

## 使用 aclient 发送异步请求

您可以试试：

```python
import re
from aclient import *


aclient = AsyncHttpClient()

# 自定义解析函数 注意; 函数必需是异步的
async def parse(response, **kwargs):

    text = await response.text()
    # 测试: 获取 title 文本 - 百度一下
    pattern = re.compile(f"<title>(.*?)</title>")
    title   = pattern.findall(text)[0]
    return title


# 请求地址 可以发送大量地址
url  = "https://www.baidu.com"

# urls列表格式
urls = [url for _ in range(2)]


result  = asyncio.run(
    aclient.gather_request(
        urls, custom_parse=parse
    )
)
# 打印item数据
print(result)
# 结果
# result = {'0': '百度一下', '1': '百度一下'}


# urls字典格式
urls = {
    f"第{i}个": {"url": url, "timeout": 5}
        for i in range(2)
}

result  = asyncio.run(
    aclient.gather_request(
        urls, custom_parse=parse
    )
)
# 打印item数据
print(result)
# 结果
# result = {'第0个': '百度一下', '第1个': '百度一下'}
```
