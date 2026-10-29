import 'package:flutter/foundation.dart';

/// 会话控制器（阶段 1 骨架）：只负责登录态与启动就绪，驱动路由重定向。
/// 真实 token / 刷新在阶段 2 接入。
class SessionController extends ChangeNotifier {
  bool _ready = false;
  bool _loggedIn = false;

  bool get isReady => _ready;
  bool get isLoggedIn => _loggedIn;

  Future<void> bootstrap() async {
    // 阶段 1：无本地 token，短暂停留在启动页后进入登录。
    await Future<void>.delayed(const Duration(milliseconds: 500));
    _ready = true;
    notifyListeners();
  }

  /// 骨架演示登录；阶段 2 替换为真实鉴权。
  void demoSignIn() {
    if (_loggedIn) return;
    _loggedIn = true;
    notifyListeners();
  }

  void signOut() {
    if (!_loggedIn) return;
    _loggedIn = false;
    notifyListeners();
  }
}
