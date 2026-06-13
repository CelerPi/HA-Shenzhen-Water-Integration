# 如何获取深圳水务配置字段

深圳水务集成支持两种配置方式：

1. 推荐方式：只填写手机号和水务用户编码，让 Home Assistant 自动发送短信验证码并登录。
2. 抓包方式：从深圳水务网页请求里获取已有会话的 `Utoken` 和 `guid`，直接跳过短信验证码步骤。

一般用户建议使用第一种方式。只有在短信验证码流程不可用、想复用网页登录会话，或需要排查接口问题时，才需要抓包。

## 需要准备的信息

Home Assistant 添加 `深圳水务` 集成时会看到这些字段：

| Home Assistant 字段 | 说明 | 是否必填 |
| --- | --- | --- |
| `base_url` | 服务地址，默认 `https://szgk.sz-water.com.cn/api/wechat` | 保持默认 |
| `mobile` | 深圳水务网上营业厅登录手机号，也作为 `OpenId` 使用 | 必填 |
| `customer_codes` | 水务用户编码/户号，多个用英文逗号分隔 | 必填 |
| `tenant_id` | 网页请求头 `TenantId` | 默认即可 |
| `channel` | 网页请求头和请求体里的渠道，默认 `wt` | 默认即可 |
| `token` | 请求头 `Utoken` | 可选 |
| `guid` | 登录响应或账单请求体里的 `guid` | 可选 |

如果不填写 `token` 和 `guid`，集成会自动发送短信验证码。输入验证码后，集成会保存登录返回的 `token/guid`。

## 推荐方式：不抓包，短信登录

1. 打开 Home Assistant。
2. 进入 `设置 -> 设备与服务 -> 添加集成`。
3. 搜索 `深圳水务`。
4. 填写：
   - `base_url`：保持默认。
   - `mobile`：登录深圳水务网上营业厅的手机号。
   - `customer_codes`：水务用户编码，多个用户编码用英文逗号分隔。
   - `tenant_id`：保持默认。
   - `channel`：保持默认 `wt`。
   - `token`：留空。
   - `guid`：留空。
5. 提交后，集成会向手机号发送短信验证码。
6. 在下一步输入短信验证码。
7. 登录成功后，集成会创建设备和传感器实体。

如果你能正常收到短信验证码，这条路线最省心，也不需要处理加密请求。

## 如何找到水务用户编码

水务用户编码通常可以从以下位置找到：

- 深圳水务网上营业厅的用户信息或户号管理页面。
- 水费账单、缴费通知或历史缴费记录。
- 微信/网页端账单详情里的 `customerCode`。
- 抓包解密后的账单响应里 `data[].customerCode`。

如果同一手机号绑定多个水务用户编码，可以在 `customer_codes` 里填多个，格式如下：

```text
1175080065,105113177
```

请使用英文逗号，不要使用中文逗号。

## 抓包方式：获取 Utoken 和 guid

抓包方式的目标是从深圳水务网页请求里找到：

- 请求头 `Utoken`，填到 Home Assistant 的 `token`。
- 登录响应或账单请求体/响应里的 `guid`，填到 Home Assistant 的 `guid`。
- 请求头 `TenantId`，通常保持默认即可。
- 请求头或请求体里的 `channel`，通常是 `wt`。
- 请求头 `OpenId`，通常就是手机号；Home Assistant 里填 `mobile`。

### 第一步：准备抓包工具

在 Mac 上安装并打开一个 HTTPS 抓包工具，推荐任选其一：

- Proxyman
- Charles
- mitmproxy

下面以 Proxyman/Charles 这类图形工具为例。

### 第二步：设置手机代理

1. 确保 iPhone 和 Mac 在同一个 Wi-Fi。
2. 在 Mac 抓包工具里查看代理监听信息：
   - Mac IP：例如 `192.168.1.20`
   - 代理端口：Proxyman 常见为 `9090`，Charles 常见为 `8888`
3. iPhone 打开 `设置 -> Wi-Fi`。
4. 点当前 Wi-Fi 右侧详情按钮。
5. 滚动到 `HTTP 代理`。
6. 选择 `手动`。
7. 填入 Mac IP 和代理端口。
8. 保存。

### 第三步：安装并信任 HTTPS 证书

1. 按抓包工具提示，在 iPhone Safari 打开证书安装地址。常见形式类似：
   - `http://proxy.man/ssl`
   - `http://chls.pro/ssl`
2. 下载描述文件。
3. 打开 iPhone `设置`，安装描述文件。
4. 继续进入：
   `设置 -> 通用 -> 关于本机 -> 证书信任设置`
5. 找到抓包工具根证书并完全信任。
6. 在抓包工具里为 `szgk.sz-water.com.cn` 开启 SSL Proxying / HTTPS 解密。

如果证书没有信任成功，只能看到 HTTPS 连接，看不到请求头、响应头或解密后的内容。

### 第四步：打开深圳水务网页

在手机上打开深圳水务网上营业厅网页：

```text
https://www.82137777.com/
```

登录并进入账单、缴费记录或用户信息页面。回到 Mac 抓包工具，过滤：

```text
szgk.sz-water.com.cn
```

重点关注这些接口：

```text
POST https://szgk.sz-water.com.cn/api/wechat/op/user/GenerateValidationNumV20
POST https://szgk.sz-water.com.cn/api/wechat/op/user/LoginV20
POST https://szgk.sz-water.com.cn/api/wechat/op/BillInfo/GetLatestBillDetails2V30
```

### 第五步：读取请求头

点开任意深圳水务 API 请求，查看 `Request Headers`。

需要确认：

| Home Assistant 字段 | 抓包位置 | 常见值 |
| --- | --- | --- |
| `base_url` | 请求 URL 前缀 | `https://szgk.sz-water.com.cn/api/wechat` |
| `tenant_id` | 请求头 `TenantId` | `18a85453-ee3f-4cda-b3bf-7f6421319dcc` |
| `channel` | 请求头 `Channel` | `wt` |
| `mobile` | 请求头 `OpenId` | 登录手机号 |
| `token` | 请求头 `Utoken` | 一长串会话 token |

注意：

- `GenerateValidationNumV20` 和 `LoginV20` 这两个登录前接口通常没有 `Utoken`。
- `GetLatestBillDetails2V30` 账单接口通常会带 `Utoken` 和 `OpenId`，更适合提取可复用会话。

### 第六步：获取 guid

`guid` 有两种常见获取方式。

方式 A：看登录响应

1. 找到 `LoginV20` 请求。
2. 查看响应内容。
3. 如果抓包工具能显示解密后的 JSON，结构通常类似：

```json
{
  "code": 0,
  "data": {
    "token": "<Utoken>",
    "guid": "<guid>"
  }
}
```

其中：

- `data.token` 填到 Home Assistant 的 `token`。
- `data.guid` 填到 Home Assistant 的 `guid`。

方式 B：看账单请求

1. 找到 `GetLatestBillDetails2V30` 请求。
2. 查看请求体或抓包工具解密后的请求内容。
3. 请求内容通常包含：

```json
{
  "customerType": "details",
  "customercodelist": ["<水务用户编码>"],
  "channel": "wt",
  "openid": "<手机号>",
  "guid": "<guid>"
}
```

其中 `guid` 就是 Home Assistant 要填写的 `guid`。

## 关于加密请求体

深圳水务网页请求和响应做了应用层 AES 加密。即使 HTTPS 已经解密，部分抓包工具里看到的请求体也可能仍然是一段加密字符串，而不是明文 JSON。

这不是抓包失败。你仍然可以从请求头拿到：

- `TenantId`
- `Channel`
- `Utoken`
- `OpenId`

如果抓包工具看不到明文 `guid`，有两个更稳的办法：

1. 直接走 Home Assistant 的短信验证码流程，让集成自己调用 `LoginV20` 并保存 `guid`。
2. 使用仓库里的验证脚本登录，脚本会把 `token/guid` 写入本地配置文件。

## 使用验证脚本获取 token/guid

仓库提供了一个本地验证脚本：

```text
scripts/sz-water.js
```

使用方式：

```bash
cd HA-Shenzhen-Water-Integration
cp scripts/sz-water.config.example.json scripts/sz-water.config.json
```

编辑 `scripts/sz-water.config.json`：

```json
{
  "mobile": "你的手机号",
  "customer_codes": ["你的水务用户编码"],
  "tenant_id": "18a85453-ee3f-4cda-b3bf-7f6421319dcc",
  "channel": "wt",
  "token": "",
  "guid": ""
}
```

发送短信验证码：

```bash
node scripts/sz-water.js send-code
```

收到短信后登录：

```bash
node scripts/sz-water.js login <短信验证码>
```

登录成功后，脚本会更新 `scripts/sz-water.config.json` 里的 `token` 和 `guid`。这两个值可以填到 Home Assistant 的 `token` 和 `guid`，也可以继续留空让 Home Assistant 自己完成短信登录。

查询最新账单测试：

```bash
node scripts/sz-water.js latest-bill
```

注意：`scripts/sz-water.config.json` 包含手机号、用户编码、token 和 guid，不要提交到 Git。

## Home Assistant 字段填写对照

| Home Assistant 字段 | 推荐填写 |
| --- | --- |
| `base_url` | `https://szgk.sz-water.com.cn/api/wechat` |
| `mobile` | 深圳水务登录手机号 |
| `customer_codes` | 水务用户编码，多个用英文逗号分隔 |
| `tenant_id` | `18a85453-ee3f-4cda-b3bf-7f6421319dcc` |
| `channel` | `wt` |
| `token` | 可留空；或填请求头/脚本得到的 `Utoken` |
| `guid` | 可留空；或填登录响应/脚本得到的 `guid` |

## 常见问题

### 填手机号和用户编码后收不到验证码

- 确认手机号是深圳水务网上营业厅绑定的手机号。
- 确认 `tenant_id` 和 `channel` 没有改错。
- 稍等一段时间再试，避免频繁发送验证码。
- 可以先在浏览器打开 `https://www.82137777.com/` 确认网页侧是否能正常发送短信。

### 添加集成后提示登录失败

- 确认短信验证码没有过期。
- 确认没有把水务用户编码填到手机号字段。
- 如果手动填写了 `token/guid`，先清空它们，改用短信验证码流程。

### 添加成功后查不到账单

- 确认 `customer_codes` 是水务用户编码，不是手机号。
- 如果有多个户号，先只填一个确认可用。
- 在深圳水务网页端确认该用户编码能看到最新账单。
- 如果 token 过期，删除集成后重新添加，或重新获取 `token/guid`。

### 抓包看不到明文请求体

- 确认 HTTPS 证书已经安装并信任。
- 确认抓包工具对 `szgk.sz-water.com.cn` 开启 SSL Proxying。
- 如果仍然是一段加密字符串，这是网页自己的 AES 加密，不影响用短信验证码流程。

## 脱敏检查

不要公开以下内容：

- 手机号
- 水务用户编码
- `Utoken`
- `guid`
- `TenantId` 以外的个人会话字段
- 用户名、住址、账单原文
- 抓包文件原件

提交 issue 时可以保留字段名和结构，并把真实值替换成：

```json
{
  "mobile": "<redacted>",
  "customer_codes": ["<redacted>"],
  "token": "<redacted>",
  "guid": "<redacted>"
}
```
