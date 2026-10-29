import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';
import 'package:rex_app/application/session_controller.dart';
import 'package:rex_app/features/detail/detail_page.dart';
import 'package:rex_app/features/home/home_page.dart';
import 'package:rex_app/features/launch/launch_page.dart';
import 'package:rex_app/features/library/library_page.dart';
import 'package:rex_app/features/login/login_page.dart';
import 'package:rex_app/features/player/player_page.dart';
import 'package:rex_app/features/search/search_page.dart';
import 'package:rex_app/features/settings/settings_page.dart';

/// iOS 层叠推入转场。linearTransition: false 才是原生手感（01 §3.1）。
CustomTransitionPage<void> iosPage({
  required GoRouterState state,
  required Widget child,
}) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      return CupertinoPageTransition(
        primaryRouteAnimation: animation,
        secondaryRouteAnimation: secondaryAnimation,
        linearTransition: false,
        child: child,
      );
    },
  );
}

/// 登录页淡入，禁返回手势。
CustomTransitionPage<void> fadePage({
  required GoRouterState state,
  required Widget child,
}) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 280),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      return FadeTransition(opacity: animation, child: child);
    },
  );
}

GoRouter createAppRouter(SessionController session) {
  return GoRouter(
    initialLocation: '/launch',
    refreshListenable: session,
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final loggingIn = loc == '/login';
      final launching = loc == '/launch';

      if (!session.isReady) {
        return launching ? null : '/launch';
      }
      if (!session.isLoggedIn) {
        return loggingIn ? null : '/login';
      }
      if (loggingIn || launching) {
        return '/';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/launch',
        pageBuilder: (context, state) => fadePage(
          state: state,
          child: const LaunchPage(),
        ),
      ),
      GoRoute(
        path: '/login',
        pageBuilder: (context, state) => fadePage(
          state: state,
          child: const LoginPage(),
        ),
      ),
      GoRoute(
        path: '/',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: const HomePage(),
        ),
      ),
      GoRoute(
        path: '/library',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: const LibraryPage(),
        ),
      ),
      GoRoute(
        path: '/search',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: const SearchPage(),
        ),
      ),
      GoRoute(
        path: '/search/:query',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: SearchPage(initialQuery: state.pathParameters['query']),
        ),
      ),
      GoRoute(
        path: '/media/:id',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: DetailPage(mediaId: state.pathParameters['id']!),
        ),
      ),
      GoRoute(
        path: '/player/:id',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: PlayerPage(mediaId: state.pathParameters['id']!),
        ),
      ),
      GoRoute(
        path: '/settings',
        pageBuilder: (context, state) => iosPage(
          state: state,
          child: const SettingsPage(),
        ),
      ),
    ],
  );
}
