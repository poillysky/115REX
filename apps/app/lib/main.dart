import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';
import 'package:rex_app/app.dart';
import 'package:rex_app/application/session_controller.dart';
import 'package:rex_app/core/router/app_router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // 播放器内核在阶段 6 接入；此处只保证绑定已就绪。
  final session = SessionController();
  final router = createAppRouter(session);
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<SessionController>.value(value: session),
      ],
      child: RexApp(router: router),
    ),
  );
  await session.bootstrap();
}
