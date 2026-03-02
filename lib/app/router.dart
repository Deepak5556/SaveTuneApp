import 'package:go_router/go_router.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../features/search/search_screen.dart';
import '../features/library_screen.dart';
import '../features/downloads_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/player/player_screen.dart';
import '../features/lyrics/lyrics_screen.dart';
import '../shared/widgets/bottom_nav.dart';

GoRouter createRouter(String initialRoute) {
  return GoRouter(
    initialLocation: initialRoute,
    redirect: (context, state) async {
      const storage = FlutterSecureStorage();
      final spDc = await storage.read(key: 'sp_dc');
      final bool loggedIn = spDc != null && spDc.isNotEmpty;
      final bool goingToSettings = state.matchedLocation == '/settings';
      if (!loggedIn && !goingToSettings) return '/settings';
      return null;
    },
    routes: [
      GoRoute(path: '/', redirect: (_, __) => '/search'),
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          GoRoute(path: '/search', builder: (c, s) => const SearchScreen()),
          GoRoute(path: '/library', builder: (c, s) => const LibraryScreen()),
          GoRoute(
              path: '/downloads', builder: (c, s) => const DownloadsScreen()),
          GoRoute(path: '/settings', builder: (c, s) => const SettingsScreen()),
        ],
      ),
      GoRoute(path: '/player', builder: (c, s) => const PlayerScreen()),
      GoRoute(
          path: '/lyrics/:id',
          builder: (c, s) =>
              LyricsScreen(spotifyId: s.pathParameters['id'] ?? '')),
    ],
  );
}
