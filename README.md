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


# 自定义解析函数 注意; 函数必需是异步的
async def parse(response, **kwargs):

    text = await response.text()
    # 测试: 获取 title 文本 - 百度一下
    pattern = re.compile(f"<title>(.*?)</title>")
    title   = pattern.findall(text)[0]
    return title


# 请求地址 可以发送大量地址
url  = "https://www.baidu.com"
# 保存解析后的数据
item = {}

aclient = AsyncHttpClient()
asyncio.run(
    aclient.gather_request(
        url, custom_parse=parse, item=item
    )
)
# 打印item数据
print(item)

# 结果
# item = {'0': '百度一下'}
```
