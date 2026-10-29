# 08 · 全栈框架总览

> 唯一重点：**一页看清整个项目的技术栈、仓库结构、数据流与全局不变量。**
> 本文是 [00](00-product-architecture.md) 的工程化视角，细节仍归各篇：
> 契约看 [07](07-api-contract.md)，搜索看 [05](05-resource-search.md)，后端看 [06](06-backend.md)，
> App 看 [04](04-app-architecture.md)，Web 看 [03](03-web-frontend.md)。
>
> **本篇是框架层**：定「有哪些零件、怎么拼、什么不能破」，不定字段级实现。

---

## 1. 技术栈一览

| 层 | 选型 | 关键决策 |
| --- | --- | --- |
| **客户端 · App** | Flutter / Dart，Cupertino 体系 | iOS 优先；`media_kit`（libmpv）播放；`go_router` 路由；`provider` 状态；`http` 网络 |
| **客户端 · Web** | Vue 3 + Vite + TypeScript + Pinia + vue-router | 与后端同源托管；共用同一套 Token 与语义色；候选两层渲染 |
| **视觉与品牌** | 设计海报为视觉基准；Token 单源生成 | 品牌资产见 [09](09-brand-assets.md)，设计语言见 [02](02-design-language.md) |
| **控制面 · 后端** | Python 3.11+ / FastAPI / SQLAlchemy / Pydantic | 单机 Windows 部署；仓储层隔离以便迁 PG |
| **数据存储** | SQLite（WAL） | 读多写少；写入串行化 |
| **数据面** | 115 CDN 直链 | 视频字节不经后端 |
| **资源源** | 自建 PG / BitMagnet / CloudSaver / semitio addon | 可插拔 provider 适配层 |
| **媒体探测** | ffprobe | 无 ffprobe 时降级为文件名解析 |
| **开发环境** | Windows | 后端本机 + Web dev server + Flutter（Windows/Android 模拟器）；iOS 构建走云 Mac / CI |

---

## 2. 仓库结构

**顶层只按「产物」划分**，不按语言划分：每个 `apps/*` 都能独立启动与部署。共享物一律进 `packages/*`，
不许在产物之间互相 import。

```
115REX/
├── docs/                          本文档集（规范唯一事实源）
├── apps/                          可交付产物，一个目录一个进程
│   ├── app/                       Flutter · iOS
│   │   ├── lib/
│   │   │   ├── core/              跨功能基础：theme / router / api / icons / storage
│   │   │   ├── domain/            纯模型与业务规则，不 import Flutter
│   │   │   ├── data/              仓储实现：调 ApiClient、解析、缓存
│   │   │   ├── application/       Controller（ChangeNotifier）
│   │   │   └── features/          按功能切：search / library / player / settings
│   │   ├── test/
│   │   └── ios/  android/         平台工程
│   ├── web/                       Web（Vue 3 + Vite + TS，见 [03 §9](03-web-frontend.md)）
│   │   └── src/{core,domain,data,application,features}
│   └── server/                    Python 后端
│       ├── app/
│       │   ├── api/               路由：只做校验与序列化，不写 SQL
│       │   ├── services/          业务编排：Search / Transfer / Play / Library
│       │   ├── providers/         资源源适配，一源一文件，互不 import
│       │   ├── integrations/      115、元数据源
│       │   ├── storage/           模型与迁移
│       │   ├── tasks/             队列与 worker
│       │   └── web/               前端构建产物（仅静态托管入口，**不属后端源码**）
│       └── tests/
├── packages/                      跨产物共享
│   ├── brand/                     品牌资产母版（见 09）
│   ├── design-tokens/             Token 唯一源 tokens.json → 生成两端常量
│   └── phosphor_flutter/          图标 fork（见 01 §6）
└── tools/                         开发脚本：生成 Token、本地起服务、契约校验
```

### 2.1 三条分层约束

| 约束 | 违反后果 |
| --- | --- |
| `domain/` 不 import Flutter / 框架 API | 业务逻辑无法脱离 UI 测试，两端会各写一遍 |
| `api/` 不写 SQL，`providers/` 之间不互相 import | 改一个资源源要连带改其他源 |
| 色值与字阶只从 `packages/design-tokens` 生成 | 两端手写色值 = 不变量 8 失效 |

### 2.2 三个可独立启动的进程（开发期）

| 进程 | 端口 | 说明 |
| --- | --- | --- |
| 后端 | 9959 | API + 托管 Web 产物 |
| Web dev server | 5173 | 代理 `/api` 到 9959 |
| Flutter | —— | 指向 9959 |

> **现状**：仓库当前只有 `docs/`。上表是**目标结构**，不是已实现状态。
> 搬目录时 App 端从根目录 `lib/` 移到 `apps/app/lib/`，并同步更新 01 / 02 的路径引用。

---

## 3. 运行时全景

```
┌──────────────────────────┐        ┌──────────────────────────┐
│  App (Flutter / iOS)     │        │  Web (浏览器)            │
│  影视库 搜索 详情 播放   │        │  影视库 搜索 详情 播放   │
└───────────┬──────────────┘        └───────────┬──────────────┘
            │  REST / JSON                         │
            │  Bearer 令牌                        │
            └──────────────┬───────────────────────┘
                           ▼
              ┌────────────────────────────┐
              │  控制面：FastAPI            │
              │  鉴权 · 聚合搜索 · 动作编排  │
              │  索引刮削 · 播放信息签发     │
              └──────┬─────────────┬────────┘
                     │             │
        ┌────────────▼───┐   ┌─────▼──────────────┐
        │ SQLite         │   │  资源源（外部依赖）  │
        │ 媒体库/进度/收藏 │   │ PG · BitMagnet     │
        │ 令牌/绑定/任务  │   │ CloudSaver · semitio│
        └────────────────┘   └────────────────────┘
                     │
                     ▼  签发短时直链 + 请求头
              ┌────────────────────────────────┐
              │  数据面：115 CDN                │
              │  播放器直连拉流（不经后端）      │
              └────────────────────────────────┘
```

### 三个典型场景的调用链

| 场景 | 调用链 |
| --- | --- |
| **跨源搜索** | 客户端 → `/search` → 搜索服务并发调用各 provider → 归一化 → 合并成作品 → 返回（带 `partial` 与各源状态） |
| **转存入库** | 客户端 → 发起动作 → 任务队列 → 115 转存 → 探测 → 刮削 → 写入媒体库 → 客户端轮询到成功 |
| **播放** | 客户端 → 请求播放信息 → 服务端签发直链 → 播放器直连 115 → 定时上报进度（写回 SQLite） |

---

## 4. 各层关键抽象

| 抽象 | 所在层 | 职责 | 契约 |
| --- | --- | --- | --- |
| `ResourceProvider` | 后端 · providers | 一个资源源的检索与动作能力 | [05 §2](05-resource-search.md) |
| `Work` / `Candidate` | 后端 · services | 作品层与候选层的统一模型 | [05 §3](05-resource-search.md) |
| `SearchService` | 后端 · services | 并发、归一化、合并、排序、降级 | [05 §4–6](05-resource-search.md) |
| `TransferService` | 后端 · services | 动作编排与状态机 | [05 §6](05-resource-search.md) |
| `PlayService` | 后端 · services | 探测 + 签发播放信息 | [07 §2.6](07-api-contract.md) |
| `ApiClient` | App · core/api | 组装头、单飞刷新、错误码映射 | [04 §6](04-app-architecture.md) |
| `SessionController` | App · application | 登录态与失效重定向 | [04 §5](04-app-architecture.md) |
| `SearchController` | App · application | 保留两层结构、驱动降级提示 | [04 §5](04-app-architecture.md) |
| `ActionController` | App · application | 动作发起与状态轮询 | [04 §5](04-app-architecture.md) |
| `PlayerController` | App · application | 起播、字幕、进度上报 | [04 §5](04-app-architecture.md) |
| `AppPalette` / `AppText` | 两端共用 | 语义色与字阶的单一来源 | [02 §3 / §8](02-design-language.md) |
| `RexColors` 等品牌 Token | `packages/design-tokens` | `tokens.json` 是唯一来源，生成两端常量 | [02 §14](02-design-language.md) |

---

## 5. 全局不变量（跨端硬规则）

违反任意一条即视为 bug，不看实现方便。

| # | 不变量 | 理由 |
| --- | --- | --- |
| 1 | 客户端**永不**持有 115 凭据或资源源凭据 | 凭据泄漏 = 账号失守 |
| 2 | 视频字节**不经后端** | 后端无上行带宽，也无必要 |
| 3 | 搜索结果是**两层**（作品 → 候选），客户端不得拍平 | 拍平会丢掉「一个作品多源可选」的核心价值 |
| 4 | `partial` 为真时客户端**必须**提示「部分资源源未响应」 | 把「源挂了」显示成「没搜到」是产品事故 |
| 5 | 单个资源源失败**不影响**其他源返回 | 异构源的必然要求 |
| 6 | 客户端刷新令牌**必须单飞** | 并发刷新会触发服务端重放检测，把设备踢下线 |
| 7 | 进度 / 收藏**账号级**存服务端 | Web 与 App 必须看到同一份数据 |
| 8 | 两端共用**同一份 Token 与语义色**定义 | 双前端不能长成两个产品 |
| 9 | 动作是**异步**的，前端不阻塞等待 | 转存是长任务 |
| 10 | 源侧无进度就**不给进度**，不显示假进度条 | 假进度比无进度更伤信任 |
| 11 | App 端滚动页面显式挂 `PrimaryScrollController` | 状态栏回顶不保证自动生效 |
| 12 | 所有色值 / 间距 / 圆角取自 `packages/design-tokens`，禁止散落裸值 | 深色模式与两端一致的前提 |
| 13 | 品牌渐变**只用于品牌位**，一屏最多一处主渐变 | 渐变泛滥会毁掉层级 |
| 14 | 资产与代码里**不出现** RexHub 字样 | 旧品牌会把产品身份搞混 |

---

## 6. 开发环境与工作流

| 事项 | 约定 |
| --- | --- |
| 后端启动 | 端口 9959；开发用热重载；生产用 Windows 服务 |
| Web 联调 | dev server 5173，代理 `/api` 到 9959；生产由后端同源托管 |
| App 联调 | Windows / Android 模拟器走 `127.0.0.1:9959`；**iOS 真机必须 HTTPS**（ATS） |
| baseUrl | 按平台切换，不写死在业务代码 |
| 配置 | 全部走环境变量；密钥类必填项不落库、不入库 |
| 日志 | 直链查询串、请求头、播放令牌、115 Cookie 一律脱敏 |
| 提交前 | 静态分析 + 单元测试 + 守门测试（禁用 Material、色值裸写）全绿 |

---

## 7. 实施路线

| 阶段 | 产物 | 验收 |
| --- | --- | --- |
| 0 结构与资产 | `apps/` 目标目录骨架、`packages/design-tokens/tokens.json`、`packages/brand/svg/` 母版 | 目录能建起来；Token 能生成两端常量；资产可由 SVG 一键导出 |
| 1 骨架 | 后端最小可跑 + Web 空壳 + App 空壳 + 契约骨架 | 三端能启动并互相对上契约 |
| 2 鉴权 | 令牌 / 刷新 / 设备绑定 / 重放检测 | 登录、单飞刷新、注销踢设备 |
| 3 影视库 | 网盘绑定、目录浏览、条目入库、详情 | 目录可选、条目可查 |
| 4 搜索 | provider 接入 + 两层结果 + 降级提示 | 跨源合并正确、单源失败可见 |
| 5 动作 | 转存 + 目录选择 + 任务状态 | 异步可观测、失败可重试 |
| 6 播放 | 直链签发 + 播放器 + 字幕 + 进度 | 未就绪时显示可重试错误而非崩溃 |

**顺序理由**：搜索与动作是本项目区别于普通网盘客户端的部分，但依赖稳定的契约与鉴权，
所以先铺契约与影视库。契约（07）是全程唯一事实源，改契约要先改文档。
第 0 阶段先行的原因是**目录与 Token 一旦定下，后面所有代码路径都依赖它**，后改成本最高。

---

## 8. 技术选型的备选与推翻条件

| 项 | 当前选型 | 备选 | 什么时候推翻 |
| --- | --- | --- | --- |
| 后端框架 | FastAPI | Flask / Django | 需要 admin 后台与 ORM 全家桶时 |
| 存储 | SQLite | PostgreSQL | 并发写入 > 10/s，或库文件 > 2GB |
| 任务 | 进程内队列 | Celery / RQ | 任务量或耗时超出单机承受 |
| 状态管理（App） | provider | bloc / riverpod | 状态依赖复杂到 provider 难以追踪 |
| 路由（App） | go_router | 自写 | 需要深度定制导航栈时 |
| Web 框架 | Vue 3 + Vite + TS（已定） | React / Svelte | 见 [03 §9](03-web-frontend.md) |
| 图标 | Phosphor fork | 其他 | —— |

---

## 9. 未决项

| 编号 | 问题 | 影响 |
| --- | --- | --- |
| Q1 | Web 端框架与构建选型 | **已决**：Vue 3 + Vite + TS + Pinia + vue-router，见 [03 §9](03-web-frontend.md) |
| Q2 | **Web 端能否播 MKV** —— 浏览器原生不支持 MKV，而 App 端（libmpv）可以 | Web 端播放策略：限制 MP4 / 服务端重封装 / WASM 播放器。**这是 Web 端最大的技术风险** |
| Q3 | Web 端是否与 App 共用登录页与路由 | 端间跳转体验 |
| Q4 | iOS 真机的公网访问方案（反代 / 内网穿透） | 真机联调前置 |
| Q5 | 资源源清单与接入优先级 | 阶段 4 的排期 |
| Q6 | 是否引入 OpenAPI 契约文件作为前后端唯一生成源 | 契约漂移风险 |
| Q7 | 端到端测试的最小覆盖范围 | 发布质量基线 |
| Q8 | 主符号最终矢量母版由谁产出 | 品牌资产全部依赖它（见 [09 §8](09-brand-assets.md)） |
