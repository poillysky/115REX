# 07 · 服务端 ↔ 客户端接口契约 v2

> 唯一重点：**有哪些接口、各自的语义、错误码与刷新规则。**
> 不涉及：客户端分层（[04](04-app-architecture.md)）、UI 规范（[01](01-ios-essentials.md) / [02](02-design-language.md) / [03](03-web-frontend.md)）、
> 服务端内部实现（[06](06-backend.md)）、provider 抽象（[05](05-resource-search.md)）。
>
> **本篇是骨架**：先定接口清单与语义，字段级 JSON 在实现时逐个补齐。
> 契约是客户端与后端之间**唯一的事实来源**。客户端不得访问资源源，也不得持有 115 凭据。
> 视频字节不经服务端，由播放器直连播放信息接口返回的地址。

---

## 1. 通用约定

| 项 | 约定 |
| --- | --- |
| 开发地址 | `http://127.0.0.1:9959/api/v1` |
| 生产地址 | 自建反代域名 + `/api/v1`（后端监听 9959，反代终结 TLS）；**具体域名待定**，见 §5 Q7 |
| 编码 / 内容类型 | UTF-8，`application/json` |
| 时间 | 全部 epoch 秒（整数），客户端再格式化 |
| 时长 / 位置 / 大小 | 整数秒 / 整数秒 / 整数字节 |
| 分页 | `limit`（默认 20，最大 50）+ `cursor`（不透明字符串，`nextCursor: null` 表示到底） |
| 幂等 | 进度上报、收藏、偏好写入天然幂等 |
| 版本 | 路径带 `v1`；新增字段向后兼容，客户端必须忽略未知字段 |

请求头：`Authorization: Bearer <token>`、`X-Device-Id`、`X-App-Version`、`X-Client-Platform`（`ios` / `web`）。

---

## 2. 接口清单

### 2.1 鉴权

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/auth/registration` | GET | 是否开放注册。服务端**一个账号都没有**时为 `true`，客户端据此走注册而非登录 |
| `/auth/register` | POST | 创建账号，成功直接返回 access / refresh / 用户信息（免二次登录）；账号已存在时 403 |
| `/auth/login` | POST | 账号密码登录，返回 access / refresh / 用户信息 |
| `/auth/refresh` | POST | 刷新令牌；**refresh token 滚动，客户端必须覆盖旧值** |
| `/auth/me` | POST→GET | 当前用户 + 服务端信息 + **能力清单**（按能力开关功能，不靠版本号） |
| `/auth/logout` | POST | 吊销该设备的全部 refresh token |

**账号模型**：自托管单用户 —— 首个注册的账号即所有者，之后注册关闭（`REGISTRATION_CLOSED`）。
用户名 3–32 位，字母/数字/`. _ -`；密码 ≥ 6 位。密码以 PBKDF2-SHA256 存储，接口不外泄。

**令牌模型**：access 短有效期（2h），refresh 长有效期（30d 滚动），服务端只存 refresh 哈希。
**重放检测**：旧 refresh 被复用 → 吊销该设备全部令牌。客户端刷新必须单飞，否则会把设备踢下线。

### 2.2 网盘账号状态

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/storage/bindings` | GET | 只读状态列表，**不含任何凭据** |
| `/storage/115/auth/start` | POST | 申请扫码登录，返回二维码内容与轮询会话 ID |
| `/storage/115/auth/poll` | POST | 轮询一次扫码结果；前端按 `retryAfter` 秒后再来 |
| `/storage/115/auth/unbind` | POST | 解绑，清空该账号的 115 凭据 |

状态枚举：正常 / 即将失效 / 已失效 / 未绑定。已失效时客户端在播放与转存前拦截并引导去管理页。
绑定在服务端管理页完成，客户端不参与密码输入。**扫码设备码流程**：服务端向 115 申请设备码并算出 PKCE 挑战码，
只把**二维码内容**下发给前端自行渲染；用户在 115 手机端扫码确认后，前端轮询到 `authorized` 即绑定完成。
`code_verifier` 与 `access_token` / `refresh_token` 全程留在服务端，任何接口响应都不得出现。

| 字段 | 约定 |
| --- | --- |
| `qrcode` | 二维码**内容**（形如 `https://115.com/scan/dg-<uid>`），不是图片 |
| `state` | `pending` 待扫 / `slow_down` 降频 / `authorized` 成功 / `expired` 过期 / `failed` 失败 |
| `retryAfter` | 下次轮询的间隔秒数；服务端守最小间隔，早到的轮询不触达 115 |
| 凭据到期 | 访问令牌到期前由服务端自动刷新；刷新失败则状态变为「已失效」 |

### 2.3 聚合搜索（v2 新增）

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/search` | GET | 跨源搜索；参数含查询词、源集合、类型过滤、分页 |
| `/search/providers` | GET | 可用资源源列表 + 健康状态，用于过滤条与降级提示 |
| `/resources/{provider}/{ref}` | GET | 单个候选详情（列表里只带必要字段，详情页再取全量） |

**返回结构是两层：作品 → 候选。** 客户端必须按嵌套渲染，**不得把候选拍平成一维列表**。
候选自带「当前可执行动作」列表，客户端据此决定按钮显示与否。

**部分结果必须显式**：结果携带 `partial` 标志与每个源的状态。
`partial` 为真时客户端**必须**显示「部分资源源未响应」提示 ——
把「一个源挂了」呈现成「没搜到」属于契约违规。

### 2.4 资源动作（v2 新增）

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/resources/{provider}/{ref}/actions` | POST | 发起动作（转存 / 推送 / 下载），**返回 202 + 动作 ID** |
| `/actions/{id}` | GET | 动作状态与结果 |
| `/actions` | GET | 动作历史（我的转存记录） |
| `/actions/{id}/cancel` | POST | 取消待处理 / 执行中的动作 |

**动作是异步的**：发起后立即返回，客户端轮询状态。前端不得等待动作完成才刷新列表。

状态语义：待处理 / 执行中 / 成功 / 失败。

| 要点 | 约定 |
| --- | --- |
| 失败原因 | 必须可读（频控 / 目录不存在 / 源失效 / 未绑定 115），不能只给「操作失败」 |
| 进度 | 源侧不提供就不给，**不要显示假进度条** |
| 转存成功 | 结果可带条目 ID；条目尚未入库时客户端显示「已转存，正在整理」 |
| 校验 | 未绑定 115 → 提示去绑定且**保持登录态**；目录不存在 → 引导重选；源不支持 → 不显示按钮 |

### 2.5 影视库

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/library/items` | GET | 列表；参数含分页、排序、库内搜索、绑定过滤 |
| `/library/items/{id}` | GET | 详情：简介、视频规格、音轨、字幕、进度、收藏 |
| `/library/dirs` | GET | 网盘目录列表，用于「转存到哪」的目录选择器 |
| `/library/continue` | GET | 继续观看，按最近播放倒序 |

| 约定 | 说明 |
| --- | --- |
| 列表不含播放地址 | 避免一次性签发大量短链 |
| 进度 / 收藏 | 服务端关联当前用户回填；**账号级，Web 与 App 共享** |
| 溯源 | 条目可带「来自哪个源的哪个候选」，原生文件可缺省 |
| 库内搜索 ≠ 跨源搜索 | 库内搜索只查已入库条目，与 `/search` 是两个接口，不要混用 |
| 音轨 / 字幕为空 | 媒体探测未接入前恒为空数组，客户端应**隐藏**入口而不是显示空选择器 |
| 目录选择器 | 只支持一层展开 + 路径面包屑，网盘层级深，全树浏览体验差 |

### 2.6 播放信息

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/library/items/{id}/play-info` | POST | 签发播放信息 |

返回内容：直链地址、可选请求头、有效期、播放令牌、建议起播位置、外挂字幕、刷新上限。

| 约定 | 说明 |
| --- | --- |
| 契约禁止项 | 响应中不得出现 115 Cookie、refresh token、账号密码、永久直链 |
| 有效期 | 客户端在到期前主动刷新（提前量默认 60s，待实测校准） |
| 刷新触发 | 地址过期 / 数据面 401、403、410 / 播放器网络错误 |
| 频控 | 同设备同条目有刷新上限，超限返回 429 + 退避秒数 |
| 授权失效 | 返回 409，客户端引导去管理页重新绑定，**不踢登录态** |
| 未就绪 | 适配器未实现时返回 503「适配器未就绪」，客户端当作**可重试**错误，不崩溃 |

### 2.7 进度与收藏

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/library/items/{id}/progress` | PUT | 上报进度；服务端按客户端时间戳取较新者，避免多端互相覆盖 |
| `/library/items/{id}/favorite` | PUT | 收藏 / 取消收藏 |

**客户端上报时机**：定时、暂停、切后台、退出播放页、播放结束。
同一秒内不重复请求；离线时入本地队列，恢复后合并提交（只留最新一条）。

### 2.8 偏好

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/preferences` | PUT | 默认转存目录、默认字幕语言、启用的资源源、是否自动转存 |
| `/preferences/icon-libraries` | PUT | 整表替换图标库；顺序即匹配优先级 |
| `/preferences/network` | PUT | 整段替换出站代理 `{ proxy: { enabled, host } }`；协议由 host 的 scheme 表达（http / https / socks5 / socks5h），缺失或非法返回 400 |
| `/preferences/basic` | PUT | 整段替换基础设定 `{ lanUrl, bridgeUrl, filterRule, doubanCache, backgroundImage }`；filterRule 只接受 `off` / `basic` / `strict`，bridgeUrl 非空时须带 http(s) scheme |
| `/preferences/github` | PUT | 整段替换 GitHub 配置 `{ proxy, token, user }`；proxy 非空时须带 http(s) scheme |
| `/preferences/advanced` | PUT | 整段替换高级参数 `{ requestTimeout, concurrency }`；超时 1–120 秒、并发 1–64，越界返回 400 |
| `/preferences/token` | PUT | 替换 API 令牌 `{ apiToken }`；只接受 40 位十六进制，否则返回 400 |
| `/preferences/plugins` | PUT | 整段替换插件配置 `{ market: string[], autoReload }`；market 为非 http(s) 地址返回 400，重复项去重 |

以上接口均作用于当前令牌对应的账号，写入即落库，进程重启后仍可读回。

#### 2.8.1 GitHub 授权（设备码流程）

对照 MoviePilot 的 GitHub OAuth Device Flow：后端申请设备码 → 前端展示短码与验证地址 →
前端按 `interval` 轮询后端 → 后端换到 access_token 并落库。**访问令牌与刷新令牌都不进任何响应**，
前端只能看到脱敏摘要。

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/preferences/github/auth/status` | GET | 读取授权状态摘要 `{ configured, valid, source, login, maskedToken, expiresAt, needsReauthorization, clientIdConfigured }`；`valid` 为 `null` 表示暂时无法判断（如网络不可达） |
| `/preferences/github/auth/start` | POST | 申请设备码，返回 `{ sessionId, verificationUri, userCode, expiresIn, intervalSeconds }`；未配置 client_id 时返回 400 `GITHUB_NOT_CONFIGURED` |
| `/preferences/github/auth/poll` | POST | body `{ sessionId }`，返回 `{ state, message, retryAfter, status }`；`state` 取 `pending` / `slow_down` / `authorized` / `denied` / `expired` / `failed`，客户端按 `retryAfter` 秒后再轮询 |
| `/preferences/github/auth/manual` | POST | body `{ token }`，保存手动 PAT 并清除 OAuth 元数据；返回状态摘要 |
| `/preferences/github/auth/token` | DELETE | 清除访问令牌与 OAuth 元数据 |

约束：

1. 客户端轮询间隔由服务端裁决，早于 `retryAfter` 的请求直接返回 `pending` 且不触达 GitHub；
   GitHub 回 `slow_down` 时间隔至少 +5 秒。
2. `authorized` 之后才会写入令牌；`status` 仅在令牌临近过期（60 秒内）时尝试刷新，刷新失败保留原值并置
   `needsReauthorization`。
3. 授权元数据（refresh_token / scope / expires_at / login）存在当前账号的偏好记录里；
   访问令牌本身也只落库、只在服务端出站请求时使用，接口一律回脱敏值。

### 2.9 字幕资源

| 接口 | 方法 | 语义 |
| --- | --- | --- |
| `/assets/sub/{id}` | GET | 字幕原文（ASS / SRT） |

鉴权二选一：请求头，或查询参数带播放令牌（播放器无法带请求头时用后者）。

---

## 3. 错误码

统一信封：HTTP 状态 + 错误码 + 提示文案（+ 可选退避秒数）。

| 分类 | 码 | 客户端处理 |
| --- | --- | --- |
| 参数 | `BAD_REQUEST` / `INVALID_TARGET_DIR` / `ACTION_NOT_SUPPORTED` | 提示 + 修正入口（重选目录 / 隐藏按钮） |
| 登录 | `INVALID_CREDENTIALS` / `USERNAME_TAKEN` / `REGISTRATION_CLOSED` / `TOKEN_MISSING` / `TOKEN_EXPIRED` / `REFRESH_EXPIRED` | 登录页提示 / 静默刷新重放一次 / 清会话跳登录 |
| 授权 | `GITHUB_NOT_CONFIGURED` | 提示去填 OAuth App 的 client_id，隐藏设备码入口 |
| 权限 | `FORBIDDEN` | 不重试 |
| 资源 | `NOT_FOUND` | 条目已删，刷新列表 |
| 网盘 | `STORAGE_AUTH_REQUIRED` | 引导去管理页重新绑定，**保持登录态** |
| 播放 | `PLAY_URL_EXPIRED` / `PLAY_INFO_RATE_LIMITED` | 立即重拉 / 按退避秒数退避 |
| 搜索 | `SEARCH_RATE_LIMITED` | 短暂禁输入并提示 |
| 上游 | `UPSTREAM_ERROR` / `PROVIDER_NOT_READY` / `PROVIDER_UNAVAILABLE` | 可重试，文案区分于网络错误 |

**资源源级错误不作为 HTTP 错误返回**：单源失败时搜索接口仍返回成功，失败信息放在结果里的源状态中。
只有**所有**源都不可用时才返回 `PROVIDER_UNAVAILABLE`。

---

## 4. 安全约束

1. 服务端日志脱敏：直链查询串、请求头、播放令牌一律不落日志。
2. 客户端错误上报不得包含完整地址（只保留 host）。
3. 播放信息必须校验设备绑定关系，设备注销后立即失效。
4. 短链可被复制使用是已知残余风险，靠短有效期 + 刷新节流 + 设备审计降低影响。
5. 管理页的绑定操作需二次认证，与客户端会话隔离。
6. **资源源凭据不下发客户端**，候选的「源特有信息」不得含 Cookie / Token / API Key。
7. **候选引用不透明**：客户端只原样回传，不拼接、不猜测。
8. **115 凭据只在服务端**：`access_token` / `refresh_token` / `code_verifier` 不得出现在任何接口响应里，
   扫码接口只下发二维码内容；解绑随即清空令牌。

---

## 5. 未决项

| 编号 | 问题 | 影响 |
| --- | --- | --- |
| Q1 | 115 接入方案（open API 还是 Cookie） | 直链有效期量级、数据面能力实测；**扫码授权已定为开放平台设备码 + PKCE** |
| Q2 | 是否做 MKV→MP4 重封装 | 播放信息是否增加变体字段 |
| Q3 | 直链实际有效期 | 客户端提前刷新量 |
| Q4 | 反代 TLS 与 SNI | iOS 真机连通性 |
| Q5 | 搜索是否分页、跨源合并后如何稳定翻页 | 契约是否引入游标 |
| Q6 | 目录选择器的数据形态（扁平路径 vs 树） | 转存参数形态 |
| Q7 | 生产域名与反代端口 | 客户端 baseUrl 与 ATS 白名单 |
