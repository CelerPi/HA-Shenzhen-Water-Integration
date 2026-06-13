# 深圳水务接入 Home Assistant

![version](https://img.shields.io/badge/version-v0.1.2-blue)

这是基于深圳水务集团网上营业厅网页接口实现的 Home Assistant 自定义集成。

> **第一次配置前请先看：** [如何获取深圳水务配置字段](docs/packet-capture.md)。教程里写了推荐短信登录流程、抓包获取 `Utoken/guid`、验证脚本和脱敏注意事项。

已还原的调用链：

- 服务地址：`https://szgk.sz-water.com.cn/api/wechat`
- 发送短信验证码：`op/user/GenerateValidationNumV20`
- 短信验证码登录：`op/user/LoginV20`
- 最新账单详情：`op/BillInfo/GetLatestBillDetails2V30`

网页端请求和响应使用 AES-256-ECB/PKCS7 加密，密钥由 `04A52C9F` 请求/响应头动态派生。本集成已经实现请求加密、响应解密和账单字段解析。

## 安装

把目录复制到 HA 配置目录：

```text
/config/custom_components/shenzhen_water
```

重启 Home Assistant 后，在 `设置 -> 设备与服务 -> 添加集成` 搜索 `深圳水务`。

## 配置

首次配置需要填写：

详细配置和抓包说明见：[如何获取深圳水务配置字段](docs/packet-capture.md)。

- `手机号 / OpenId`：深圳水务网上营业厅登录手机号。
- `水务用户编码`：水费户号/用户编码，多个可用逗号分隔。
- `TenantId`：默认 `18a85453-ee3f-4cda-b3bf-7f6421319dcc`。
- `渠道`：默认 `wt`。

如果不填写 `Utoken` 和 `guid`，集成会先发送短信验证码，并在下一步让你输入验证码完成登录。

如果你已经从网页抓包或脚本里拿到了有效 `Utoken/guid`，也可以直接填入，跳过短信登录步骤。

## 当前实体

- `账单`：状态为账单月份，属性里包含当前账单详情。
- `本期总金额`
- `水费`
- `污水费`
- `垃圾处理费`
- `待支付金额`
- `本期用水量`
- `缴费状态`
- `缴费截止日`
- `本期表码`
- `上期表码`
- `本期抄表日期`
- `上期抄表日期`

## 刷新策略

集成启动时刷新一次，之后每 12 小时刷新一次。深圳水务账单通常按月更新，不建议高频轮询。

## 安全说明

- 不要把手机号、用户编码、`Utoken`、`guid`、住址等信息提交到仓库或 issue。
- `Utoken` 是网页登录会话令牌，过期后需要删除并重新添加集成，或重新配置获取新验证码。
- 本项目只读取账单数据，不做缴费操作。
