import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:rex_app/app.dart';
import 'package:rex_app/application/session_controller.dart';
import 'package:rex_app/core/router/app_router.dart';

/// widget 测试里 Future.delayed 必须靠 pump 推进，不能裸 await。
Future<void> _bootstrap(WidgetTester tester, SessionController session) async {
  final done = session.bootstrap();
  await tester.pump(const Duration(milliseconds: 600));
  await done;
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  testWidgets('启动 → 登录 → 首页', (tester) async {
    final session = SessionController();
    final router = createAppRouter(session);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<SessionController>.value(value: session),
        ],
        child: RexApp(router: router),
      ),
    );
    await tester.pump();

    expect(find.text('115REX'), findsWidgets);

    await _bootstrap(tester, session);

    expect(find.text('登录'), findsWidgets);
    expect(find.text('登录后同步影视库与进度'), findsOneWidget);

    await tester.tap(find.text('登录').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('快捷入口'), findsOneWidget);
    expect(find.text('影视库'), findsWidgets);
  });

  testWidgets('未登录访问首页会重定向到登录', (tester) async {
    final session = SessionController();
    final router = createAppRouter(session);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<SessionController>.value(value: session),
        ],
        child: RexApp(router: router),
      ),
    );
    await tester.pump();
    await _bootstrap(tester, session);

    router.go('/');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('登录后同步影视库与进度'), findsOneWidget);
  });
}
