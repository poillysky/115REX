# 04 · App 架构（Flutter 客户端）

> 唯一重点：**客户端怎么分层、模块放哪、状态怎么流转。**
> 不涉及：iOS 硬规则（[01](01-ios-essentials.md)）、设计语言（[02](02-design-language.md)）、
> Web 端规范（[03](03-web-frontend.md)）、接口字段（[07](07-api-contract.md)）、
> 服务端内部实现（[06](06-backend.md)）。
>
> **本篇是骨架**：定分层与职责边界，不定类实现。

---

## 1. 架构决策

| 决策 | 结论 | 理由 |
| --- | --- | --- |
| 控制面 / 数据面 | 分离。服务端只做账号、配置、索引、签发；视频字节由播放器直连 115 | 服务端不承担视频上行带宽 |
| 路由 | `go_router` | 需要登录态重定向与统一转场 |
| 状态管理 | `provider` + `ChangeNotifier` | 规模小，避免引入重框架 |
| 网络 | `http` + 自写 `ApiClient` | 需要统一 401 处理与可中断请求；不引入 dio |
| 播放内核 | `media_kit`（libmpv） | 需要 MKV 容器、ASS 字幕、多音轨 |
| 本地存储 | `shared_preferences` + 钥匙串 | 只存 token、设备 ID、偏好、离线队列 |
| 对接后端 | Python FastAPI，契约见 [07](07-api-contract.md) | —— |

**核心原则：客户端永远不持有网盘长期凭据**，只拿服务端签发的播放信息。

---

## 2. 分层

```
Presentation    页面 / 组件（只读 Provider，不 new 网络对象）
     ▲ watch/read            ▼ 用户动作
Application     Session / Library / Search / Action / Player Controller
     ▲ 领域模型              ▼ 仓储接口
Domain          models（纯 Dart）  repositories（abstract）
     ▲ 实现
Data            remote（HTTP）  repositories（impl）  mock
```

硬约束：

- `domain` 不 import Flutter，不 import `media_kit`。
- `presentation` / `features` 不直接构造 `ApiClient`。
- `PlayerController` 是**唯一**同时接触 `media_kit` 与仓储的层。

---

## 3. 目录

```
apps/app/lib/
├── main.dart                    # runApp
├── app.dart                     # MultiProvider + CupertinoApp.router
├── core/
│   ├── theme/                   # design_tokens.dart（生成） / text_styles / app_theme
│   ├── icons/                   # ios_icon.dart（SF 名 → 字形）+ 功能图标
│   ├── widgets/                 # ios_button ios_card ios_list_tile ios_slider
│   │                            # segmented_control sheet_picker
│   ├── router/                  # GoRouter + 重定向
│   ├── api/                     # api_client / api_exception / endpoints
│   └── storage/                 # token / deviceId / 偏好 / 离线队列
├── domain/
│   ├── models/                  # session media_item media_detail play_info
│   │                            # progress work candidate action
│   └── repositories/            # auth / library / search / action（abstract）
├── data/
│   ├── remote/                  # *_remote.dart
│   ├── repositories/            # 接口实现
│   └── mock/                    # 服务端未启动时的演示数据
├── application/
│   ├── session_controller.dart
│   ├── library_controller.dart
│   ├── search_controller.dart
│   ├── action_controller.dart
│   └── player_controller.dart
└── features/
    ├── launch/ login/ home/     # 各页 + 页内私有组件
    ├── library/                 # 影视库 + widgets/ios_poster_preview.dart
    ├── search/ detail/          # 搜索结果 / 详情
    ├── player/                  # 播放页
    └── settings/                # 设置
```

五层命名 `core / domain / data / application / features` 与 Web 端一致，
共享规则见 [08 §2.1](08-fullstack-framework.md)。页面私有组件放在各自 `features/<页>/widgets/`，
只有跨两页以上复用的才上提到 `core/widgets/`。

**搜索与动作是新增的两个领域**（`work` / `candidate` / `action` 模型），
其余按原结构补齐。

---

## 4. 路由

| 路径 | 页面 | 转场 |
| --- | --- | --- |
| `/launch` | LaunchPage | 无（跳完即弃） |
| `/login` | LoginPage | 淡入，禁返回 |
| `/` | HomePage | 默认 |
| `/library` | LibraryPage | 默认（影视库） |
| `/search` | SearchPage | 搜索页（无参数） |
| `/search/:query` | SearchPage | 带初始查询词 |
| `/resource/:provider/:ref` | ResourceDetailPage | 候选详情 |
| `/media/:id` | DetailPage | `CupertinoPageTransition` |
| `/player/:id` | PlayerPage | `CupertinoPageTransition` |
| `/settings` | SettingsPage | `CupertinoPageTransition` |

重定向：未登录且不在登录页 → 登录页；已登录在登录页 → 首页；其余放行。
`routerConfig` 要读登录态，所以 `MultiProvider` 必须包在 `CupertinoApp.router` **外面**。

---

## 5. Controller

| Controller | 职责要点 |
| --- | --- |
| `SessionController` | 启动校验 token；收到不可恢复 401 时清会话触发重定向；不弹全屏错误、不走 Navigator |
| `LibraryController` | 分页触底加载；库内搜索防抖；空态 / 错误态 / 加载态**显式建模**，不靠列表是否为空猜 |
| `SearchController` | 维护查询词与防抖；调用 `/search`；保存 `partial` 与各源状态用于降级提示；**保留作品 → 候选的两层结构**，不拍平 |
| `ActionController` | 发起动作、轮询状态、维护动作列表；状态变化时通知 UI；取消动作 |
| `PlayerController` | 解析播放信息 → 起播 → 加载字幕 → 首播 seek → 进度上报节拍 |

**播放信息解析**：内存缓存，键为条目 ID，有效期 = 服务端有效期减去提前刷新量（默认 60s）；
同一条目并发请求去重；失败抛出可识别异常，不吞异常。

| 情况 | 动作 |
| --- | --- |
| 403 / 410 或临近过期 | 重拉一次，seek 回原位置 |
| 连续刷新 2 次仍失败 | 提示「播放地址失效」并返回详情页 |
| 409 网盘授权失效 | 提示去管理页重新绑定，**保持登录态** |
| 429 频控 | 按退避秒数退避 |

**进度上报**：定时、暂停、切后台、退出页面、播放结束。
同一秒不重复请求；位置变化很小且非关键事件时跳过。

**播放器生命周期**：在播放页内创建，随页面销毁释放实例。
若后续要做后台音频 / 画中画，改为全局单例并引入音频会话管理，届时修订本节。

---

## 6. ApiClient 规则

```
组装头：Authorization / X-Device-Id / X-App-Version / X-Client-Platform
  ├─ 2xx            → 解 JSON
  ├─ 401 TOKEN_EXPIRED → 单飞 refresh → 重放一次 → 仍失败抛会话过期
  ├─ 401 其他        → 抛会话过期
  ├─ 4xx / 5xx      → 按错误码映射 ApiException
  └─ 网络异常        → 网络异常类型
```

三条硬性要求：

1. **刷新必须单飞**。并发多个 401 只发一次刷新，否则服务端重放检测会把整台设备踢下线。
2. 只有 `TOKEN_EXPIRED` 触发重放，其余错误直接上抛。
3. 刷新失败只通知一次会话控制器。

**搜索接口的额外处理**：`/search` 的资源源级失败不走错误分支，走正常返回里的源状态。
只有全部源不可用（503）才进入错误分支。

---

## 7. 依赖

| 用途 | 选择 |
| --- | --- |
| 路由 | `go_router` |
| 状态 | `provider` |
| 网络 | `http` |
| 本地存储 | `shared_preferences` + 钥匙串 |
| 播放 | `media_kit` + `media_kit_video` + 平台库 |
| 图标 | Phosphor（fork，见 [01 §6](01-ios-essentials.md)） |
| 品牌 SVG | `flutter_svg`（仅用于主符号与功能图标，见 [09 §6](09-brand-assets.md)） |

`main()` 首行必须初始化绑定与播放器内核。

**不引入**：Material 体系的任何组件库、无使用点的动画库。

---

## 8. 实施顺序

| 阶段 | 内容 | 验收 |
| --- | --- | --- |
| 1 装配 | 依赖 + 空壳页面 + 路由 + 重定向 | 分析零问题；能从启动走到登录再走到首页 |
| 2 登录 | 网络层 + 本地存储 + 会话控制器 | 真实登录；坏 access 自动刷新；坏 refresh 回登录页 |
| 3 影视库 | 库控制器 + 列表 + 详情 | 分页触底、下拉刷新、库内搜索、空态 |
| 4 搜索 | 搜索控制器 + 搜索页 + 候选两层渲染 + 降级提示 | 跨源返回能正确分两层展示；单源失败有提示 |
| 5 动作 | 动作控制器 + 转存面板 + 目录选择器 + 动作状态轮询 | 转存能发起、能看状态、失败可重试 |
| 6 播放 | 播放器 + 播放控制器 + 字幕 | 适配器未就绪时显示可重试错误而非崩溃 |

**平台差异**：Windows 调试走 `127.0.0.1:9959`；iOS 真机必须走 HTTPS 地址。
baseUrl 按平台切换，否则本地调通、真机全挂。

---

## 9. 未决项

| 编号 | 问题 | 影响 |
| --- | --- | --- |
| Q1 | 搜索是独立 Tab 还是从首页进入 | 路由与底部导航结构 |
| Q2 | 候选详情是否单独路由，还是在搜索页内展开 | 路由表 |
| Q3 | 动作轮询的间隔与前后台策略 | 电量与实时性 |
| Q4 | 离线队列的存储形态与上限 | 本地存储设计 |
| Q5 | 是否支持深链 / 分享链接 | 与 Web 端的联动 |
