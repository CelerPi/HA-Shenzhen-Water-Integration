# Handoff: HA-Shenzhen-Water-Integration

## 项目目标

这是一个 Home Assistant 自定义集成，用于接入深圳水务集团网上营业厅网页接口，查询用户最新水费账单，并把账单金额、用水量、费用拆分、缴费状态、抄表日期和表码等信息暴露为 HA 传感器实体。

项目已整理成适合上传 GitHub/HACS 的结构，目录风格参考 `HA-Qianhai-Power-Integration` 和 `HA-UpperCoast-Doorlock-Integration`。

## 当前目录结构要点

- `custom_components/shenzhen_water/`：Home Assistant 集成主体。
- `custom_components/shenzhen_water/brand/`：集成内 logo/icon 资源。
- `brand/`：仓库根目录品牌资源，供 HACS/GitHub 使用。
- `.github/workflows/validate.yml`：HACS 与 Hassfest 校验工作流。
- `hacs.json`：HACS 元数据。
- `README.md`：用户安装、配置、实体说明。
- `CHANGELOG.md`：版本变更记录。
- `LICENSE`：MIT License。
- `scripts/sz-water.js`：接口验证脚本，方便脱离 HA 测试短信登录和账单查询。
- `scripts/sz-water.config.example.json`：验证脚本的示例配置，不包含真实账号信息。

## 已知隐私状态

代码和文档中不应包含用户的真实手机号、用户编码、姓名、地址、`Utoken`、`guid`、Cookie、短信验证码或抓包密文样本。

最后一次整理时，真实本地配置文件没有复制进仓库；`.gitignore` 已忽略：

```text
scripts/sz-water.config.json
```

公开上传前仍建议再跑一次：

```bash
rg -n "14714412341|1175080065|1846679|105113177|Utoken|ALIPAYJSESSIONID|JSESSIONID|openid=|guid|token|短信验证码|住址|地址" .
```

正常情况下可以出现字段名说明，例如 `Utoken`、`guid`、`token`，但不应该出现真实值。

## 接口链路

服务基础地址：

```text
https://szgk.sz-water.com.cn/api/wechat
```

已实现的业务接口：

- `op/user/GenerateValidationNumV20`：发送短信验证码。
- `op/user/LoginV20`：短信验证码登录，返回 `token` 和 `guid`。
- `op/BillInfo/GetLatestBillDetails2V30`：查询最新水费账单详情。

网页来源：

```text
https://www.82137777.com/
```

## 加密逻辑

深圳水务网页端请求和响应使用应用层 AES 加密。HTTPS 抓包只能看到密文，需要按网页 JS 逻辑处理。

请求：

- 请求头 `04A52C9F` 是 32 位随机字符串。
- 请求体是 JSON 明文经 AES-256-ECB/PKCS7 加密后的 Base64。
- AES key：

```text
"33F4A3D6" + request_04A52C9F[8:24] + "A9E19798"
```

响应：

- 响应头也有 `04A52C9F`。
- 响应体是 JSON 字符串包裹的密文。
- 解密前需要重排密文：

```text
encrypted = body[0:7] + body[20:] + body[7:20]
```

- AES key：

```text
"33F4A3D6" + response_04A52C9F[8:24] + "A9E19798"
```

实现位于：

```text
custom_components/shenzhen_water/crypto.py
```

HA 依赖：

```text
pycryptodome==3.20.0
```

## 用户配置字段

用户在 Home Assistant 添加集成时填写：

- `base_url`：默认 `https://szgk.sz-water.com.cn/api/wechat`。
- `mobile`：深圳水务网上营业厅登录手机号，同时作为网页端 `openid`。
- `customer_codes`：水务用户编码，多个用逗号分隔。
- `tenant_id`：默认 `18a85453-ee3f-4cda-b3bf-7f6421319dcc`。
- `channel`：默认 `wt`。
- `token`：可选，网页端登录返回的 `Utoken`。
- `guid`：可选，网页端登录返回的用户 `guid`。

如果不填写 `token/guid`，config flow 会先调用短信验证码接口，然后进入 `sms` 步骤让用户输入验证码并完成登录。

## 登录流程

配置入口：

```text
custom_components/shenzhen_water/config_flow.py
```

流程：

1. 用户填写手机号和水务用户编码。
2. 如果没有 `token/guid`，调用 `GenerateValidationNumV20` 发送短信。
3. 用户输入短信验证码。
4. 调用 `LoginV20` 获取 `token/guid`。
5. 保存配置并创建实体。

已知限制：

- 当前版本没有实现 options flow 或 reauth flow。
- 如果 `token` 过期，需要删除并重新添加集成，或后续补 reauth 逻辑。

## 刷新策略

集成会在 Home Assistant 启动或重载时立即刷新一次。

之后每 12 小时刷新一次：

```text
update_interval=timedelta(hours=12)
```

实现位于：

```text
custom_components/shenzhen_water/__init__.py
```

深圳水务账单通常按月更新，不建议高频轮询。

## 账单字段中文对应

来自 `GetLatestBillDetails2V30` 的 `data[0]`：

| 接口字段 | 中文实体/含义 |
| --- | --- |
| `costDate` | 账单月份 |
| `customerCode` | 水务用户编码 |
| `totalAmount` | 本期总金额 |
| `displayTotal` | 展示总金额，当前未单独展示 |
| `waterAmount` | 水费 |
| `sewageAmount` | 污水费 |
| `garbageAmount` | 垃圾处理费 |
| `lateFee` | 违约金/滞纳金 |
| `needpay` | 待支付金额 |
| `waterConsumption` | 本期用水量 |
| `waterAfterReduced` | 减免后用水量 |
| `dueDate` | 缴费截止日 |
| `paymentStatus` | 缴费状态 |
| `waterStatus` | 水费状态 |
| `sewageStatus` | 污水费状态 |
| `garbageStatus` | 垃圾处理费状态 |

来自 `meterWaterUses[0]`：

| 接口字段 | 中文实体/含义 |
| --- | --- |
| `waterMeterCode` | 水表编号 |
| `waterNumber` | 本期表码 |
| `waterNumberPreTime` | 上期表码 |
| `meterCheckMonDate` | 本期抄表日期 |
| `meterCheckPreDate` | 上期抄表日期 |
| `waterUseDays` | 用水天数 |
| `waterConsumption` | 本期用水量 |
| `waterConsumptionPre` | 上期用水量，当前未单独展示 |

## 当前实体覆盖范围

主要实体包括：

- 账单
- 本期总金额
- 水费
- 污水费
- 垃圾处理费
- 待支付金额
- 本期用水量
- 缴费状态
- 缴费截止日
- 本期表码
- 上期表码
- 本期抄表日期
- 上期抄表日期

`账单` 实体的属性会附带完整解析后的账单字段和接口返回状态。

## Logo/Icon

logo 来源是用户提供的深圳水务图片，已生成 PNG：

- `brand/icon.png`
- `brand/icon@2x.png`
- `brand/logo.png`
- `brand/logo@2x.png`
- `brand/dark_icon.png`
- `brand/dark_icon@2x.png`
- `brand/dark_logo.png`
- `brand/dark_logo@2x.png`
- `custom_components/shenzhen_water/brand/*`
- `custom_components/shenzhen_water/icon.png`
- `custom_components/shenzhen_water/logo.png`

当前尺寸：

- `icon.png`：256 x 256
- `icon@2x.png`：512 x 512
- `logo.png`：512 x 512
- `logo@2x.png`：1024 x 1024

如果 HA 前端仍显示 `icon not available`，通常是前端缓存或自定义集成品牌资源缓存问题。重启 HA 后，必要时清浏览器缓存或重新加载集成。

## 验证脚本

仓库保留了一个 Node.js 验证脚本：

```text
scripts/sz-water.js
```

用法：

```bash
cp scripts/sz-water.config.example.json scripts/sz-water.config.json
node scripts/sz-water.js send-code
node scripts/sz-water.js login <短信验证码>
node scripts/sz-water.js latest-bill
```

注意：

- `scripts/sz-water.config.json` 包含手机号、用户编码、token、guid，不要提交。
- Node.js 脚本使用内置 `crypto` 和 `fetch`，不需要额外 npm 依赖。

## 发布前检查

推荐上传 GitHub 前执行：

```bash
python3 -m json.tool hacs.json >/dev/null
python3 -m json.tool custom_components/shenzhen_water/manifest.json >/dev/null
python3 -m json.tool custom_components/shenzhen_water/strings.json >/dev/null
python3 -m json.tool custom_components/shenzhen_water/translations/zh-Hans.json >/dev/null
python3 -m json.tool custom_components/shenzhen_water/translations/zh.json >/dev/null
python3 -m json.tool custom_components/shenzhen_water/translations/en.json >/dev/null
python3 -m py_compile custom_components/shenzhen_water/*.py
find . \( -name ".DS_Store" -o -name "__pycache__" -o -name "*.pyc" -o -name "sz-water.config.json" \) -print
```

`manifest.json` 当前仓库地址是：

```text
https://github.com/CelerPi/HA-Shenzhen-Water-Integration
```

如果最终仓库名不同，需要同步修改：

- `documentation`
- `issue_tracker`

