import 'package:flutter/cupertino.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:rex_app/core/theme/app_theme.dart';
import 'package:rex_app/core/theme/ios_scroll_behavior.dart';

/// 根组件：Cupertino + 中文本地化 + 动态字体钳制 + 跟随系统深浅色。
class RexApp extends StatelessWidget {
  const RexApp({super.key, required this.router});

  final GoRouter router;

  @override
  Widget build(BuildContext context) {
    return MediaQuery.withClampedTextScaling(
      minScaleFactor: 0.9,
      maxScaleFactor: 1.3,
      child: Builder(
        builder: (context) {
          return CupertinoApp.router(
            title: '115REX',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.resolve(context),
            scrollBehavior: const IosScrollBehavior(),
            localizationsDelegates: const [
              GlobalCupertinoLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
            ],
            supportedLocales: const [
              Locale('zh', 'CN'),
              Locale('en', 'US'),
            ],
            routerConfig: router,
          );
        },
      ),
    );
  }
}
