# 01 · iOS 质感设计原则（第 1 部分）

> 唯一重点：**保证不翻车的基本框架。** 这一篇全是「不做就会一眼安卓」的系统层规则，
> 与品牌无关 —— 哪怕一行业务代码都不写、品牌色一个都不定义，只要遵守本文，观感就是原生的。
>
> 不涉及：色彩体系、圆角间距、材质、组件、页面类型等「怎么好看」的内容，见 [02](02-design-language.md)。
> 不涉及：目录分层（见 [04](04-app-architecture.md)）、接口字段（见 [07](07-api-contract.md)）。
> 不涉及：Web 端（本文只管 App 端），见 [03](03-web-frontend.md)。
>
> 基线：Flutter 3.24+ / Dart 3.5+，Windows 开发、云 Mac 打包。
>
> 配套 skill：`.trae/skills/apple-ui-designer/`（来自 `heyman333/atelier-ui`）。
> 它给**设计判断**（该不该加、要不要删、是否够克制），本文给**Flutter 落地写法**。
> 两者冲突时以本文为准 —— 它不知道 Flutter 的具体 API，也不了解 `CupertinoIcons` 的边界。

---

## 两篇文档的分工

| | 本文（第 1 部分） | [02](02-design-language.md)（第 2 部分） |
| --- | --- | --- |
| 回答 | 怎样**不像安卓** | 怎样**好看** |
| 来源 | iOS HIG + Flutter 框架行为 | 通用设计语言体系（可换品牌复用） |
| 性质 | 硬约束，违反即为 bug | 目标规范，代码须向它对齐 |
| 典型内容 | 滚动、转场、禁用 Material、语义色、安全区、手势冲突 | 气质、色彩/间距/圆角体系、材质、组件、页面类型、动效、验收 |
| 换掉品牌后 | 全部仍然成立 | 结构仍然成立，Token 取值整表替换 |

判断一条规则放哪：**换掉品牌视觉后，规则本身的写法还成立的，写进本文；只有具体取值属于 02。**

两篇都是**规定方向**，不是现状记录。差异只在范围：本文约束「不该怎么做」，02 规定「应该长什么样」。
代码与任一篇冲突时，以文档为准。

---

## 1. 先分清三类问题

「一眼安卓」通常来自三个层面，处理优先级从高到低：

| 层 | 典型症状 | 处理章节 |
| --- | --- | --- |
| **框架层** | 滚动手感不对、页面转场生硬、水波纹、Material 组件混入、点状态栏不回顶 | §2 §3 §4 |
| **视觉层** | 字体回退、数字跳动、图标风格杂 | §5 §6 |
| **交互与系统层** | 点击无反馈、状态栏错位、安全区重叠、无触觉、键盘不收、系统弹窗是英文 | §7 §8 |

框架层最难返工。一旦路由和滚动行为写错，后面每个页面都要返工修正。

---

## 2. 滚动：iOS 手感的根

### 2.1 全局注册 `CupertinoScrollBehavior`

```dart
CupertinoApp.router(
  scrollBehavior: const IosScrollBehavior(),
  routerConfig: router,
)

class IosScrollBehavior extends CupertinoScrollBehavior {
  const IosScrollBehavior();

  @override
  Widget buildScrollbar(BuildContext c, Widget child, ScrollableDetails d) => child;

  @override
  Widget buildOverscrollIndicator(BuildContext c, Widget child, ScrollableDetails d) => child;
}
```

三件事一次到位：

- 父类 `CupertinoScrollBehavior` 默认给 `BouncingScrollPhysics`（iOS 惯性回弹）。
- 关掉滚动条（iOS 无长期滚动条）。
- 关掉 Material 的 overscroll 辉光。

### 2.2 平台差异不算 bug

Windows 预览下没有回弹。原因是桌面端滚动是 `PointerScrollEvent`，不触发 overscroll。
**不要**为此手写 physics 强行造回弹 —— iOS 真机行为已正确。

### 2.3 大标题列表的骨架

```dart
CustomScrollView(
  slivers: [
    CupertinoSliverNavigationBar(largeTitle: Text('媒体库')),
    SliverSafeArea(
      top: false,                    // 顶部已由导航栏负责，必须 false
      sliver: SliverPadding(
        padding: EdgeInsets.symmetric(horizontal: 16),
        sliver: SliverList.builder(...),
      ),
    ),
  ],
)
```

两个坑：

| 坑 | 症状 | 修法 |
| --- | --- | --- |
| 用了 `SafeArea` 而不是 `SliverSafeArea` | sliver 布局报错或底部空白 | sliver 树内必须用 `SliverSafeArea` |
| `top` 忘了设 `false` | iPhone 上多出一段状态栏高空白 | `top: false` |

- 大标题已自动处理左右安全区，列表**只留内容 padding**，不要再包一层左右 `SafeArea`。
- 下拉刷新用 `CupertinoSliverRefreshControl`，包住大标题后第一个 sliver。
- 导航栏背景、氛围渐变的叠加方式属于设计语言，见 [02 §5.2](02-design-language.md)。

### 2.4 点击状态栏回到顶部

iOS 独有行为，官方 platform-adaptations 明确列为平台差异：**点击系统状态栏，滚动到顶部**。安卓没有这个行为，因此从安卓迁移过来的人最容易漏。

生效条件是「页面里有一个滚动组件真的注册成了 primary scroll controller」。满足任一即可：

- 滚动组件是页面 body 里**第一个**可滚动组件，且没有显式传 `controller` —— 框架自动挂上 `PrimaryScrollController`；
- 或者手动包一层 `PrimaryScrollController(controller: _controller, child: …)`。

**自绘大标题的页面（首页这种 Stack 叠层版式）必须手动挂**，因为滚动组件被包在 Stack 里、且常显式传了 `controller`，框架不会自动接管：

```dart
class _HomeState extends State<Home> {
  // withClampedTextScaling 之外，页面自己持有一个 controller
  final _scroll = ScrollController();

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PrimaryScrollController(
    controller: _scroll,          // 状态栏点击的目标
    child: CustomScrollView(
      controller: _scroll,        // 同一个实例，缺一不可
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      slivers: [ … ],
    ),
  );
}
```

三个坑：

| 坑 | 症状 | 修法 |
| --- | --- | --- |
| 只传 `controller:` 不包 `PrimaryScrollController` | 滚动正常，点状态栏毫无反应 | 两处都写，且是同一个实例 |
| `PrimaryScrollController` 包在 `CupertinoPageScaffold` 之外 | 页面切走后 controller 被复用，回来时位置错乱 | 包在页面 widget 内部，随页面 `dispose` |
| 用 `NestedScrollView` / 多个滚动区 | 点状态栏滚的不是外层 | 显式 `PrimaryScrollController.of` 指向外层；仍不明确时改为页面级单滚动区 |

验收：iOS 真机（或模拟器）滚到中段，点右上角时间区域，页面应带惯性回顶。模拟器状态下拉出的是控制中心，需要点时间文字本身。

---

## 3. 路由与转场

### 3.1 全局 `pageBuilder`，不逐页手写

```dart
GoRouter(
  pageBuilder: (context, state, child) => CustomTransitionPage(
    key: state.pageKey,
    child: child,
    transitionsBuilder: (context, animation, secondary, child) =>
        CupertinoPageTransition(
          primaryRouteAnimation: animation,
          secondaryRouteAnimation: secondary,
          linearTransition: false,   // 关键：false 才是 iOS 层叠位移
          child: child,
        ),
  ),
)
```

| 参数/场景 | 错写成 | 结果 |
| --- | --- | --- |
| `linearTransition` | `true` | 安卓式整页横向推入，最刺眼的一处 |
| Tab 间切换 | 复用 `CupertinoPageTransition` | 不该有滑动的切换出现了滑动，用 `NoTransitionPage` |
| 登录→首页 | 默认转场 | 出现从左滑入的「假返回」历史，用 `context.go` 而非 `push` |

### 3.2 返回手势

- `CupertinoPageTransition` 自带边缘侧滑返回，不需要额外代码。
- 侧滑期间必须禁用横向可滚动组件（如横向列表），否则手势冲突。用 `CupertinoPageScaffold` 会自动处理。
- 登录页、启动页不设置返回：路由用 `context.go`，不使用 `push`。

### 3.3 播放页

- 用 `CupertinoPageScaffold(child: Stack(...))`，**不要**导航栏。
- 自绘返回按钮（左上 `chevron.backward`），位置随安全区调整。
- 进入时 `SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive)`，退出时恢复 `edgeToEdge`。

---

## 4. 禁用 Material 的机制，不靠自觉

### 4.1 禁用清单

| 禁用 | 替代 |
| --- | --- |
| `MaterialApp` / `Scaffold` / `AppBar` | `CupertinoApp.router` / `CupertinoPageScaffold` / `CupertinoNavigationBar` |
| `InkWell` / `Ink` / `Material` | `IosButton`（自绘缩放反馈） |
| `ListTile` | `CupertinoListTile` |
| `Icons.*` | `IosIcon`（内部映射到 Phosphor，见 §6） |
| `Card` / `Chip` / `Divider` / `ElevatedButton` | `IosCard` / 自绘胶囊 / `Container` + `Border` |
| `showModalBottomSheet` / `AlertDialog` / `showMenu` | `showCupertinoModalPopup` / `showCupertinoDialog` / `CupertinoActionSheet` |
| `ClampingScrollPhysics` | 交给全局 `IosScrollBehavior` |
| `CircularProgressIndicator` | `CupertinoActivityIndicator` |
| `RefreshIndicator` | `CupertinoSliverRefreshControl` |

### 4.2 守门测试（比 lint 更快见效）

`test/lint/no_material_test.dart`：

```dart
const _banned = [
  'MaterialApp', 'Scaffold', 'InkWell', 'Ink(', 'Icons.',
  'ListTile', 'showModalBottomSheet', 'AlertDialog', 'CircularProgressIndicator',
];

test('lib 下不允许出现 Material 符号', () {
  final offenders = <String>[];
  for (final f in Directory('lib').listSync(recursive: true).whereType<File>()) {
    if (!f.path.endsWith('.dart')) continue;
    final src = f.readAsStringSync();
    for (final b in _banned) {
      if (src.contains(b)) offenders.add('${f.path}: $b');
    }
  }
  expect(offenders, isEmpty, reason: offenders.join('\n'));
});
```

注意：`CupertinoListTile` 含子串 `ListTile`，白名单里要排除，或改用 `\bListTile\b` 之外的更精确匹配。

### 4.3 `uses-material-design: false`

```yaml
flutter:
  uses-material-design: false
```

只影响是否打包 Material 图标字体，不阻止 import。真正去掉 Material 观感靠 §4.1。

---

## 5. 字体与排版

### 5.1 不指定 fontFamily

Flutter 在 iOS 上默认按系统字体族渲染：拉丁字符用 SF，中文自动回退 PingFang SC。**不写 `fontFamily` 就是最优解。**

写了 `fontFamily: 'SF Pro Display'` 的后果：Windows 静默回退到默认字体、iOS 上部分字形匹配失败、中英文行高不一致。

### 5.2 等宽数字

时间码、集数、进度百分比必须开 `tabularFigures`，否则每次刷新数字宽度变化，整行会抖动。

```dart
// 时间码、集数、进度百分比这类会刷新的数字
static TextStyle timecode(BuildContext context) => TextStyle(
  fontSize: 12,
  fontWeight: FontWeight.w500,
  fontFeatures: [FontFeature.tabularFigures()],
  color: AppPalette.of(context).textSecondary,
);
```

写成带 `context` 的工厂函数，而不是 `const` 常量：`TextStyle` 一旦是 `const`，里面的颜色就被冻结，切深色不会刷新（同 §8.8）。守门测试也禁止把 `AppText` 常量直接交给 `Text`。

### 5.3 动态字体

Cupertino 主题不做字号自动缩放。用户开启「大字体」后如果不生效，iOS 用户会立刻察觉。但完全放开到 2.0 倍会让布局崩，所以做区间钳制：

```dart
MediaQuery.withClampedTextScaling(
  minScaleFactor: 0.9,
  maxScaleFactor: 1.3,
  child: CupertinoApp.router(...),
)
```

### 5.4 字阶下限

本文只约束**必须存在的档位与相对关系**：大标题 > 导航标题 > 列表主标题 > 副标题 > 辅助说明，
且「以字号/字重建立层级，不靠颜色」。具体字号表是设计语言决策，见 [02 §8](02-design-language.md)。

| 场景 | 关系 |
| --- | --- |
| Large Title | 全区最大，仅大标题导航栏使用 |
| 导航栏标题 | 小于 Large Title，w600 |
| 列表主标题 | 正文基准字号 |
| 列表副标题 / 辅助说明 | 依次递减，取次级色 |
| 时间码 / 统计数字 | 必须等宽（§5.2） |

---

## 6. 图标

### 6.1 以 SF Symbols 名称为唯一键

`CupertinoIcons` 只有约 140 个字形，且 `IconData` 无法反向映射到 SF 名称。因此**常量表的值就用 SF 名称字符串**，映射表统一放在 `apps/app/lib/core/icons/ios_icon.dart`：

```dart
abstract final class IosSf {
  static const playCircleFill = 'play.circle.fill';
  static const chevronRight = 'chevron.right';
  static const gobackward10 = 'gobackward.10';
  static const goforward10 = 'goforward.10';
}

class IosIcon extends StatelessWidget {
  const IosIcon(this.sfName, {super.key, this.size = 22, this.color});

  final String sfName;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final data = _phosphorBySfName[sfName]; // SF 名称 → Phosphor 字形
    if (data == null) {
      assert(false, 'IosSf 缺少映射：$sfName，请在 _phosphorBySfName 中补齐');
      return SizedBox.square(dimension: size);
    }
    return PhosphorIcon(data, size: size, color: color);
  }
}
```

这样后续换图标库时**页面零改动**。如果一开始写成 `IosIcon(CupertinoIcons.xxx)`，以后要改所有调用点。

**为什么不是 `CupertinoIcons`**：它的字形数撑不满 iOS 语义（`gobackward.10`、`film.stack` 之类都没有），视觉也与 SF Symbols 有明显差距。现在用 **Phosphor**（MIT，字形量级与 SF 同档，风格贴近 SF）。

**为什么 fork**：`phosphor_flutter` 最新版是 2.1.0，其 `PhosphorIconData extends IconData`；而 Dart 3.13 / Flutter 3.47 起 `IconData` 是 `final class`，外部继承直接编译失败，上游两年未更新。于是把包拷进 [packages/phosphor_flutter](../packages/phosphor_flutter)，只做一处兼容改造——`PhosphorIconData` 由继承改为**组合**（内部字段 + `iconData` getter 现造 `IconData`），API 其余部分不变，根 `pubspec.yaml` 用 `path:` 依赖它。升级 Flutter 或上游发新版后，可整体换回 pub 版本，只影响这一个包。

### 6.2 缺失字形的处理顺序

1. 在 Phosphor 里找语义最接近的字形（优先 Rounded/Regular，实心态用 Fill），补进 `_phosphorBySfName`。
2. 确实没有对应的，先占位，不要退回 Material Icons。
3. **绝不**用 `Icons.*`。

新增一个图标 = 在 `IosSf` 加一个 SF 名称常量 + 在 `_phosphorBySfName` 加一行映射，调用点仍写 `IosIcon(IosSf.xxx)`。

### 6.3 尺寸与热区

- 视觉尺寸 22~26，播放页控制图标可到 26。
- 触控热区必须 ≥ 44×44：用 `SizedBox(width: 44, height: 44)` 包 `Center(child: IosIcon(...))`，不要靠 `padding` 凑。

线性图标与带底板的图标如何分工，属于设计语言，见 [02 §7](02-design-language.md)。

---

## 7. 交互反馈

### 7.1 按压反馈三件套

iOS 的按压反馈是「缩放 + 轻微变淡」，不是颜色变化。Android 的 `InkWell` 是水波纹 + 高亮色块 —— 两者观感差异极大。

```dart
class IosButton extends StatefulWidget {
  // AnimatedScale 0.96 + AnimatedOpacity 0.9，时长 120ms，Curves.easeOut
}
```

| 元素 | 反馈 |
| --- | --- |
| 主按钮 / 卡片 | scale 0.96 + opacity 0.9，120ms |
| 图标按钮 | opacity 0.4 的 pressed 态，或 `CupertinoButton` 自带 |
| 长按 | scale 0.97，不做额外动画 |
| 列表行 | 按下整行变灰底（`CupertinoListTile` 内置） |

### 7.2 触觉

| 场景 | API |
| --- | --- |
| 切换音轨 / 字幕 / 倍速 | `HapticFeedback.selectionClick()` |
| 收藏、开关 | `HapticFeedback.lightImpact()` |
| 删除、退出 | `HapticFeedback.mediumImpact()` |
| 拖动进度条 | **不震动**（连续操作震动手感很差） |

### 7.3 弹层

| 场景 | 组件 |
| --- | --- |
| 音轨 / 字幕 / 倍速选择 | `showCupertinoModalPopup` + 自绘 sheet（带抓手条） |
| 危险操作确认（退出登录、删除） | `showCupertinoModalPopup` + `CupertinoActionSheet`，破坏项 `isDestructiveAction: true`，取消放 `cancelButton` |
| 提示（操作失败、需要用户知晓） | `showCupertinoDialog` + `CupertinoAlertDialog` |

判断依据是**操作性质**而不是「要不要弹窗」：会让用户丢数据或退出登录的用 action sheet，纯告知用 alert dialog。

### 7.4 手势冲突

横向滚动嵌在纵向滚动里、播放页手势叠在系统侧滑返回上，是 iOS 上最容易被忽略的两类冲突。

| 场景 | 处理 |
| --- | --- |
| 横向 `ListView` 嵌在纵向 `CustomScrollView` / `ListView` 里 | 横向列表用 `BouncingScrollPhysics`，纵向父级也必须是 `BouncingScrollPhysics`；**不要**混入 `ClampingScrollPhysics`（安卓惯性），否则横滑到底会突然停硬 |
| 横向列表贴边 | 横向 `ListView` 加页面水平 padding，不要靠 `AspectRatio` 推算宽度，让首尾卡片完整露出，暗示「可横滑」 |
| 播放页左右半屏滑动手势 | 与系统侧滑返回冲突。播放页**不挂** `CupertinoPageScaffold` 的默认返回手势：用 `Navigator.pop` 的显式返回按钮，或在 `PageRouteBuilder` 里设 `popGestureEnabled: false` |
| 播放页横向拖动 seek | 用 `GestureDetector` 的 `onHorizontalDragStart/Update/End`，不要用 `onPanUpdate`；`pan` 会同时接管纵向，导致亮度和进度互相抢 |
| 长按 2x 倍速 | 用 `onLongPressStart` / `onLongPressEnd` 成对处理，`onLongPressEnd` 里必须还原倍速，否则用户中途松手会卡在 2x |
| 按钮放进 `Row` / `CupertinoNavigationBar.trailing` | `CupertinoButton` 的 `minimumSize` 会被父级压缩，必须显式 `minimumSize: Size(kMinTapTarget, kMinTapTarget)`，否则可点区域小于 44pt |
| 通栏按钮 | 主按钮默认 `width: double.infinity`（通栏）。需要按内容收窄时，调用方用 `IntrinsicWidth` 或 `Align` 包一层，不要指望父级「碰巧」拉伸 |
| 全屏 `GestureDetector` 收键盘 | 用 `behavior: HitTestBehavior.translucent` 而不是 `opaque`；`opaque` 会与内部按钮争抢手势竞技场，表现为「按钮点了没反应」 |

### 7.5 表单的 iOS 语义

`CupertinoTextField` 自带 iOS 文本编辑语义，**不要**去「修正」它们 —— 这些看起来像 bug，其实全是原生行为：

| 行为 | 说明 |
| --- | --- |
| 单击定位到**最近的词边界**，不是精确点击位置 | iOS 语义。安卓才是精确定位。不要为此换自定义 controller |
| 长按把光标放到长按处，拖拽移动光标 | iOS 语义。拖拽是移动光标，**不是**扩大选区 |
| 拖拽选区两端的把手才能改选区范围 | 与上一条配套 |
| `obscureText: true` 时系统接管「强密码」建议 | 页面上会出现系统密码浮层，这是正常的；不要自己画「显示密码」以外的额外提示 |

自动填充的关键三件事：

```dart
AutofillGroup(                       // 1. 同一表单的字段必须同组
  child: Column(
    children: [
      CupertinoTextField(
        placeholder: '账号',
        autofillHints: const [AutofillHints.username],   // 2. 语义要对
        textInputAction: TextInputAction.next,
      ),
      CupertinoTextField(
        placeholder: '密码',
        obscureText: true,
        autofillHints: const [AutofillHints.password],
        textInputAction: TextInputAction.done,
        onSubmitted: (_) => _submit(),
      ),
    ],
  ),
)

// 3. 提交成功后收尾，系统才会问「是否保存密码」
TextInput.finishAutofillContext();
```

- `AutofillHints` 是 `flutter/services.dart` 里的常量类（不是 Material 组件），`AutofillGroup` 来自 `flutter/widgets.dart`，两者都在 `cupertino.dart` 的导出链里，**不违反 §4**。
- `autofillHints` 必须**唯一且正确**：账号填 `username`，密码填 `password`，首次注册用 `newPassword`。填错会导致系统不弹自动填充。
- 没有 `AutofillGroup` 包裹时，键盘上方不会出现账号 / 密码快捷条。
- **不要**自己造键盘上方的工具栏。iOS 上 `CupertinoTextField` 的 `inputAssistantItem` 由系统管理，安卓的「上一项 / 下一项」是 Material 的习惯，iOS 没有。
- iOS 无「显示密码」原生开关，需要时用 `CupertinoButton` 自己切换 `obscureText`，图标用 `IosSf.eye`。

### 7.6 长按预览与共享元素转场

媒体类 App 两个高频的原生交互，Flutter 都有现成组件：

**长按预览**用 `CupertinoContextMenu`。媒体库里长按海报弹出「播放 / 详情」，是 iOS 用户预期的交互，比长按弹底部菜单更原生。本项目统一走 `apps/app/lib/features/library/widgets/ios_poster_preview.dart` 的 `IosPosterPreview`，不要各页面自己拼。

```dart
CupertinoContextMenu(
  actions: [
    CupertinoContextMenuAction(
      onPressed: () { … },
      isDefaultAction: true,
      child: const Text('播放'),
    ),
  ],
  child: PosterImage(item),
)
```

**只包海报本体，不包整行**：预览层会接管长按区域，包整行会把行内的箭头、进度条一起吞进去。

**海报转场**用 `Hero`。列表点击进详情时海报飞过去，是 iOS 的「共享元素」直觉。`CupertinoApp` 已自动装上 `HeroController`，不需要额外配置。

```dart
// 列表卡片与详情页海报用同一个 tag
Hero(tag: 'poster-${item.id}', child: PosterImage(item))
```

| 坑 | 症状 | 修法 |
| --- | --- | --- |
| 同一页面出现两个相同 tag | 抛 `multiple heroes share the same tag` | tag 必须带条目 id，不要用固定字符串 |
| `Hero` 内的图是网络图 | 转场时闪白 / 尺寸跳动 | 转场前后用同一个 `ImageProvider` 与 `BoxFit`，让图片缓存命中 |
| 长按预览放在可横滑卡片上 | 横滑抢走长按 | 卡片横滑用 `ListWheel` 之外的普通 `ListView` 时，长按优先由内层 `CupertinoContextMenu` 拿到；冲突时把 `CupertinoContextMenu` 包在最内层图片上 |

长按预览的弹出比例与圆角（放大、卡片 `radiusXl` 档）属于设计语言，见 [02 §5.1](02-design-language.md)。

---

## 8. 系统集成

### 8.1 安全区

| 位置 | 处理 |
| --- | --- |
| 顶部 | `CupertinoSliverNavigationBar` / `CupertinoNavigationBar` 已处理，不再叠加 |
| 底部 home indicator | 全屏内容延伸到底，交互元素用 `MediaQuery.paddingOf(context).bottom` 垫高 |
| 横屏左右（灵动岛侧） | `SafeArea(left: true, right: true)` |
| 键盘 | **不要**自己包 `Padding(MediaQuery.viewInsetsOf(context))`。`CupertinoPageScaffold` 已按 `viewInsets` 做避让，再包一层会让内容上跳两倍。只需保证可滚动（`ListView` / `CustomScrollView`），并把待输入字段滚进可视区 |

### 8.2 滚动收起键盘

iOS 用户在列表里往上一划，键盘就该收回去；只有安卓才习惯留着一个永远不走的键盘。Flutter 默认**不**做这件事，必须显式声明：

```dart
ListView(
  keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
  children: [ … ],
)
```

- `CustomScrollView` / `GridView` / 任何 `ScrollView` 子类都有这个参数。
- 用 `onDrag` 而不是 `onManual`：`onDrag` 在手指拖动时立刻收，符合 iOS「一划就收」的手感。
- 带表单的页面（登录、设置里的输入项）**必须**加；纯展示页面加不加不影响，但统一加更省心。
- 已有全屏 `GestureDetector` 点击收键盘的页面（如登录页），这一条是**补充而非替代**：点击空白收、拖动列表也收，两者都要。

### 8.3 状态栏

| 页面 | overlay style |
| --- | --- |
| 常规页面 | 跟随主题：深色文字配浅底 |
| 播放页 | `.light` |

不要在 `main()` 里全局设一次就完事，页面 `initState` / `dispose` 里成对切换。

### 8.4 本地化：默认只有英文

`CupertinoApp` 不传 `localizationsDelegates` 时，用的是 `DefaultCupertinoLocalizations` —— **纯英文实现**。于是这些地方会冒英文：

| 位置 | 实际显示 |
| --- | --- |
| `CupertinoAlertDialog` 的取消 / 默认按钮 | `Cancel` |
| `CupertinoDialogAction` 无文案时的无障碍标签 | 英文 |
| 文本选择菜单（拷贝 / 粘贴 / 全选 / 查找） | `Copy` / `Paste` / `Select All` |
| `CupertinoSearchTextField` 默认占位 | `Search` |
| `CupertinoDatePicker` / `CupertinoTimerPicker` 的年月日与「今天」 | 英文 |
| 导航栏返回按钮无障碍标签 | `Back` |

规则：

```dart
CupertinoApp.router(
  localizationsDelegates: const [
    GlobalCupertinoLocalizations.delegate,   // 关键：提供中文 Cupertino 文案
    GlobalMaterialLocalizations.delegate,    // 可选，但建议一并声明
    GlobalWidgetsLocalizations.delegate,     // 决定文本方向 RTL/LTR
  ],
  supportedLocales: const [Locale('zh', 'CN'), Locale('en', 'US')],
  …
)
```

- 需要 `flutter_localizations` 依赖（SDK 内置包，`pubspec.yaml` 里加 `flutter_localizations: {sdk: flutter}`），**不引入 Material 组件、不影响 §4 的禁用清单**。
- `supportedLocales` 第一项是**兜底语言**：用户系统语言既不是中文也不是英文时，回退到中文而不是框架默认英文。
- 文案本身仍由本项目自己控制（`title`、按钮文字、错误提示都写中文字面量），本地化只负责**框架内置文案**这一层，两者不冲突。

真机验证：把系统语言切成英文再切回中文，对话框按钮与文本选择菜单应同步变化；如果始终是英文，说明 delegate 没挂上。

### 8.5 屏幕方向

- **不要**在 `main()` 里锁死竖屏。
- 播放页 `initState` 放开横屏，`dispose` 恢复竖屏；其余页面竖屏。
- 用 `SystemChrome.setPreferredOrientations` 动态设置，而非全局常量。

### 8.6 iOS 工程配置（`ios/Runner/Info.plist`）

| 键 | 值 | 原因 |
| --- | --- | --- |
| `NSAppTransportSecurity` | 仅 `NSExceptionDomains`，**不设** `NSAllowsArbitraryLoads` | 全局放开会被审核质疑，且掩盖证书问题 |
| `NSLocalNetworkUsageDescription` | 一句中文说明 | iOS 14+ 访问局域网必需，缺了真机直接失败 |
| `UIBackgroundModes` | `audio`（仅当需要锁屏续播） | 不需要就不要加，会被审核追问 |
| `CFBundleDisplayName` | `115REX` | — |

`Podfile` 起始 `platform :ios, '13.0'`，`media_kit` 报错时再上调。

### 8.7 深浅色跟随系统

- `CupertinoApp` 没有 `darkTheme` 参数，跟随系统，不需要也不应该传 `ThemeMode`。
- 因为拿不到框架自动切换，主题要**自己按平台亮度选一份**，并写成 getter（不能 `const`，原因见 8.8）：

```dart
CupertinoThemeData _resolvedTheme(BuildContext context) {
  final brightness = MediaQuery.platformBrightnessOf(context);
  return brightness == Brightness.dark ? AppTheme.dark : AppTheme.light;
}

// CupertinoApp.router(theme: _resolvedTheme(context))
```

`MediaQuery.platformBrightnessOf` 会在系统切换时触发重建，颜色因此跟着刷新。
直接用 `MediaQuery.of(context)` 会订阅过多无关变化（如键盘弹出），不要用。

- 播放页强制深色：局部 `CupertinoTheme(data: AppTheme.dark, child: ...)`，同时 `SystemUiOverlayStyle.light`。
- 验收清单见 §10 D 段。

### 8.8 颜色只能用语义色，不写死色值

```dart
Text('副标题', style: TextStyle(color: palette.textSecondary))
```

- 禁止 `Color(0x…)` 散落在页面里 —— 这是深浅色切换失灵的常见源头。
- 禁止直接把 `const` 主题塞给 `CupertinoApp`：`const` 会冻结动态色，系统切深色时不刷新。
- 色值的**唯一定义处**是 `packages/design-tokens/tokens.json` 生成的
  `apps/app/lib/core/theme/design_tokens.dart`，由守门测试强制（见 02 §14）。
  本文只管「必须从语义入口取色」这条规则，
  具体有哪些语义、每个语义取什么值，见 [02 §3](02-design-language.md)。

---

## 9. 页面骨架模板

三种形态覆盖全部页面，新页面直接照抄，不要自由发挥。骨架只管**结构**（哪层套哪层、哪里不能多包 `SafeArea`）；
里面的配色、圆角、材质是设计语言，见 [02 §5](02-design-language.md)。

### 9.1 大标题页面（首页 / 列表页）

```dart
CupertinoPageScaffold(
  backgroundColor: AppPalette.of(context).mist,
  child: PrimaryScrollController(          // 状态栏回顶，见 §2.4
    controller: _scroll,
    child: CustomScrollView(
      controller: _scroll,
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      slivers: [
        CupertinoSliverNavigationBar(
          largeTitle: const Text('媒体库'),
          backgroundColor: palette.mist,           // 不透明，才能挡住滚动内容
          border: null,
          trailing: CupertinoButton(…),
        ),
        CupertinoSliverRefreshControl(onRefresh: _refresh),
        SliverSafeArea(top: false, sliver: …),   // top: false 必须
      ],
    ),
  ),
)
```

自绘大标题（首页叠层版式）不套 `CupertinoSliverNavigationBar`，但 `PrimaryScrollController` 与 `controller` 同样必须挂 —— 写法见 §2.4。

列表主体用**单张**卡片承载连续行，行间放分隔线组件（见 02 §5.2）。

### 9.2 普通页面（详情 / 设置）

```dart
CupertinoPageScaffold(
  navigationBar: CupertinoNavigationBar(
    middle: Text('详情', style: AppTextStyle.navTitle(context)),
    border: null,
  ),
  child: PrimaryScrollController(          // 状态栏回顶，见 §2.4
    controller: _scroll,
    child: ListView(                       // 不要再包 SafeArea
      controller: _scroll,
      physics: const BouncingScrollPhysics(),
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      children: [ … ],
    ),
  ),
)
```

`CupertinoPageScaffold` 已处理顶部导航栏高度与底部 home indicator。**多包一层 `SafeArea` 会让列表底部多出一段空白**，这是最容易犯的错。

普通页面同样要挂 `PrimaryScrollController`：页面被包进 `CupertinoPageTransition` 后，「body 里第一个滚动组件自动成为 primary」这条不保证成立，实测状态栏点击不生效。页面是 `StatelessWidget` 时可以 `PrimaryScrollController.maybeOf(context) ?? ScrollController()`；能拿到 `State` 就自己持有并 `dispose`。

### 9.3 全屏页面（播放）

```dart
class _PlayerState extends State<Player> {
  @override
  void initState() {
    super.initState();
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive);
    SystemChrome.setPreferredOrientations(const [
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
      DeviceOrientation.portraitUp,
    ]);
  }

  @override
  void dispose() {
    // 必须成对还原，否则退出后整个 App 仍是横屏 + 无状态栏
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    SystemChrome.setPreferredOrientations(const [DeviceOrientation.portraitUp]);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CupertinoPageScaffold(
    backgroundColor: CupertinoColors.black,
    child: Stack(…),   // 不要 navigationBar，返回用自绘按钮
  );
}
```

### 9.4 三态组件规范

统一用 `apps/app/lib/core/widgets/ios_card.dart` 里的现成组件，不要每页各写一份。

| 状态 | 组件 | 结构要求 |
| --- | --- | --- |
| 加载 | `IosLoading(label:)` | 居中 `CupertinoActivityIndicator(radius: 12)`，上下 64pt 留白；有 `label` 时下方 12pt 接次级色说明。**禁止**全屏白底 + 居中转圈 |
| 空 | `IosEmptyState(icon:, title:, message:, action:)` | 图标 44pt 三级色 → 16pt 后接 w600 标题 → 8pt 后接说明；有 `action` 时再空 24pt。四周 32/48 |
| 错误 | `IosErrorState(message:, onRetry:)` | `IosSf.arrowClockwise` 36pt 三级色 → 16pt 后接说明文案 → 24pt 后接「重试」按钮；**不要把错误码直接抛给用户** |

三态都放在 `SliverToBoxAdapter` 或页面主体位置，不要弹 dialog —— 弹层会被用户误认为阻断性错误。

---

## 10. 分段验收

**A 段（搭骨架时）**
- [ ] 全局 `IosScrollBehavior` 生效：无滚动条、无辉光
- [ ] `pageBuilder` 全局 `CupertinoPageTransition(linearTransition: false)`
- [ ] 守门测试通过
- [ ] `uses-material-design: false`
- [ ] `localizationsDelegates` 已挂，`supportedLocales` 首项为中文

**B 段（写页面时）**
- [ ] 所有可点区域 ≥ 44×44，按压有缩放反馈
- [ ] 时间码 / 数字使用 `tabularFigures`
- [ ] `MediaQuery.withClampedTextScaling(0.9, 1.3)` 生效
- [ ] 颜色只从 `AppPalette.of(context)` 取，无 `Color(0x…)` 残留
- [ ] 每个可滚动页面都注册了 primary scroll controller（自绘版式要手动包 `PrimaryScrollController`）
- [ ] 带输入的滚动页面设了 `keyboardDismissBehavior: onDrag`
- [ ] 账号 / 密码输入框在同一个 `AutofillGroup` 内，`autofillHints` 语义正确

**C 段（真机）**
- [ ] 点击状态栏，页面带惯性回顶
- [ ] 大标题收缩流畅，无多余空白
- [ ] 侧滑返回与横向滚动不冲突
- [ ] 刘海 / 灵动岛 / home indicator 无遮挡
- [ ] 播放页 `Video(controls: NoVideoControls)`，缓冲圈为 Cupertino 样式
- [ ] 横屏布局正确，退出后方向恢复
- [ ] 长按海报出现 `CupertinoContextMenu` 预览，点进详情海报有 `Hero` 飞行
- [ ] 系统语言为中文时，对话框按钮与文本选择菜单都是中文

**D 段（深色模式，逐项确认）**

切到系统深色后逐条对照，任何一项没变就是颜色被 `const` 冻结了。
具体变到哪个色值见 [02 §3](02-design-language.md)，这里只验收「有没有跟着变」：

- [ ] 导航栏背景变深
- [ ] 页面底色变深
- [ ] 正文文字与说明文字都变浅，且两者仍能区分
- [ ] 卡片底色与页面底色可区分
- [ ] 卡片内的次级块（`IosInset`）在卡片上仍可见
- [ ] 分隔线仍可见，不发白
- [ ] 品牌色在近黑底上不发闷
- [ ] 顶部氛围渐变（若有）变成暗色，导航栏文字对比度足够
- [ ] 进度条已播段与底段对比度足够
- [ ] 空态 / 错误态图标不发黑
- [ ] 播放页仍是纯黑背景，退出后页面底色正确恢复
- [ ] 在深色下切换回浅色，上述所有项同步反转（不是单向生效）

**禁止写法**：

```dart
// 错：const 冻结动态色，切深色不刷新
static const CupertinoThemeData light = CupertinoThemeData(
  barBackgroundColor: CupertinoColors.systemBackground,
);
```

---

## 11. 已知取舍

**Windows 开发、多端分发**下有意为之的妥协。每条都记了「风险点」和「什么时候该推翻它」——
取舍过期不退休，比没有取舍更糟。

「归属」列说明这一条约束的是框架（本文）还是设计语言（02）。

| 项 | 归属 | 现状 | 原因 | 风险点 / 推翻条件 |
| --- | --- | --- | --- | --- |
| SF Symbols | 框架 | 已定：Phosphor（`packages/phosphor_flutter` fork，`path:` 依赖），经 `IosIcon` 以 SF 名称查表（见 §6.1） | `sf_symbols_flutter` 在 pub 不存在；自建 `MethodChannel`/FFI 调 `UIImage(systemName:)` 必须云 Mac 做 iOS 联调，Windows 侧连预览都做不到；`CupertinoIcons` 只有约 140 个字形，撑不满 iOS 语义 | fork 是为了绕过上游 `PhosphorIconData extends IconData` 与 `IconData` 变 `final class` 的冲突，只改了这一处，其余 API 不变。上游发新版或再换库时只动这一个包 + `ios_icon.dart` 的映射表，页面零改动。**不要**打包苹果 SF 字体文件（版权） |
| 动态字体上限 1.3 | 框架 | 全局 `MediaQuery.withClampedTextScaling(0.9, 1.3)`，不做完全缩放 | 放开到 2.0 时，播放控制条、底部固定栏这类高度写死的组件会溢出、错位 | 代价是「超大字」用户被限流。真要做分区缩放（内容区跟系统、控制区锁 1.0），在控制层再包一层 `withClampedTextScaling` 即可 —— **当前未实现，只记在这里** |
| Windows 无回弹 | 框架 | 不主动模拟 iOS 回弹 | 桌面是 `PointerScrollEvent`，不触发 overscroll；手写 physics 造回弹会和真机 `CupertinoScrollBehavior` 表现不一致，造成双端割裂 | 按平台原生习惯走：iOS 自动回弹，Windows/Android 保持各自默认。**不要**为了「本地预览更像 iPhone」去改 |
| `fontFamily` 不指定 | 框架 | 依赖平台系统默认字体族（见 `apps/app/lib/core/theme/text_styles.dart`） | 手写字体名但不打包字体文件时，找不到会**静默回退**，跨平台的字重、行高随之失控 | 依赖系统意味着 Android / Windows / iOS 观感天然有差异。若要统一，字体文件必须放进 `assets/` + `pubspec.yaml` 声明；只写名字没用 |
| iOS 打包 & 预览 | 框架 | Windows 只写代码 + 安卓模拟器验证；iOS 构建走云 CI（Codemagic / GitHub Actions）或云 Mac | Windows 没有 Xcode 工具链，既不能本地编译 IPA，也跑不起 iOS 模拟器 | iOS 真机问题只能在 CI 产物上暴露，反馈环比安卓长。合入前至少跑通 `flutter analyze` + `flutter test`，别把 iOS 当成「最后再修」 |
| 图标库备选 | 视觉 | 已启用 Phosphor（fork 到 `packages/phosphor_flutter`，见 [02 §7](02-design-language.md)） | 风格贴近 SF Symbols，Windows / Android / iOS 都能预览，无苹果版权限制 | 接入统一走 `IosIcon` 这一层，调用点零改动（见 §6.1 的语义名设计）；再换库时同样只改映射表 |
| 视觉规范覆盖率 | 视觉 | 待按 02 重排：先做一套样板页做透，再按样板推广，避免边写边改规范 | 先把一套「样板页」做透，再按样板推广，避免边写边改规范 | 推进顺序见 [02 §15](02-design-language.md)。页面与 02 不一致即算视觉缺陷，**新代码必须直接按 02 写** |
| iOS 26 Liquid Glass | 框架 | 不启用。App 内控件保持 pre-iOS 26 的 Cupertino 观感 | flutter/flutter [#170310](https://github.com/flutter/flutter/issues/170310)：官方明确「暂不在 Cupertino 库中实现 Apple 2026 新设计语言，且当前不接受相关贡献」。官方 [ios-latest](https://docs.flutter.dev/platform-integration/ios/ios-latest) 页把 Liquid Glass 列为「未完全实现」的已知项之一 | 正面后果是可预期：iOS 26 真机上系统弹层、控制中心是玻璃质感，App 内是实色，**这种不一致是当前必然，不要当 bug 修**。官方支持到位后按 [02 §6](02-design-language.md) 的材质分层整层替换，不在页面里手写玻璃效果 |
| 状态栏点击回顶 | 框架 | 规则：**每个可滚动页面显式挂 `PrimaryScrollController` + 同名 `ScrollController`**（见 §2.4、§9.2） | 框架「body 第一个滚动组件自动成为 primary」在包进 `CupertinoPageTransition` 后不保证成立 | 新增滚动页面必须自己挂，不要赌自动注册；`flutter test` 里点状态栏无自动化覆盖，靠真机验收 |
| 中文本地化 | 框架 | 规则：`CupertinoApp` 挂三个 `Global*Localizations.delegate`，`supportedLocales` 首项 `zh_CN`，并加入 `flutter_localizations` 依赖（见 §8.4） | 框架内置文案默认纯英文，手写中文文案掩盖了这个缺口 | 新增语言时只改 `supportedLocales`，不要在页面里手写翻译表 |
| 滚动收键盘 | 框架 | 规则：**所有滚动容器设 `keyboardDismissBehavior: onDrag`**（见 §8.2） | 不设则带输入的页面划动键盘不走，是最容易被吐槽的安卓味 | 纯展示页面加不加都不影响，但统一加更省心 |
| 长按预览 / 海报转场 | 框架 | 规则：列表与详情用同一 `Hero` 标签；长按预览由 `apps/app/lib/features/library/widgets/ios_poster_preview.dart` 统一提供（见 §7.6） | 媒体类 App 的高频原生交互，各页面自己拼会出现不一致 | 预览只包海报本体、不包整行，避免吞掉行内其他热区；`Hero` 网图闪白问题按 §7.6 的 `ImageProvider` + `BoxFit` 一致原则验收 |
| iOS 17+ 缩放转场 | 框架 | 不用。统一走 `CupertinoPageTransition` 层叠位移 | 官方 [ios-latest](https://docs.flutter.dev/platform-integration/ios/ios-latest) 记录「iOS-style zoom page transition」为未实现项（[#150588](https://github.com/flutter/flutter/issues/150588)），无现成 Cupertino 组件可调 | 与原生最新系统存在观感差异，但层叠位移仍是「iOS 正确」的旧版行为，比自造转场安全。**不要**自己拼 `ScaleTransition` 模拟 |
| 文本选择放大镜 | 框架 | 不实现 | 放大镜是 `UITextView` 的原生渲染，Flutter 在 `cupertinoTextSelectionControls` 层无法完整复现 | 长按选字时无放大镜。属于**框架能力边界**，不是本项目可选项；不要为此换成 Material 输入框 |

