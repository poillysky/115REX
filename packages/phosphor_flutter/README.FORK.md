# phosphor_flutter fork（115REX）

上游：`phosphor_flutter` 2.1.0。

**唯一改动**：`PhosphorIconData` 不再 `extends IconData`（Dart 3.13 / Flutter 3.47 起
`IconData` 为 `final class`），改为组合 + `iconData` getter；`PhosphorIcon` 改为
独立 `StatelessWidget`，接收 `PhosphorIconData`。

其余 API 与字形文件保持原样。上游修复后可整体换回 pub 版本。
