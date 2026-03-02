import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'app/router.dart';
import 'app/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Platform guard — Android only
  if (kIsWeb) {
    runApp(const WebNotSupportedApp());
    return;
  }

  runApp(const ProviderScope(child: SplashApp()));
}

class SplashApp extends StatelessWidget {
  const SplashApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SaveTune',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF121212),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF1DB954),
          surface: Color(0xFF1E1E1E),
        ),
      ),
      home: const SplashScreen(),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  String _status = 'Starting SaveTune...';
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _startUp();
  }

  Future<void> _startUp() async {
    setState(() {
      _hasError = false;
      _status = 'Starting music server...';
    });

    bool serverReady = false;
    // Wait up to 60 seconds for Go server
    for (int i = 0; i < 60; i++) {
      if (!mounted) return;
      setState(
          () => _status = 'Starting music server...\n(${i + 1}/60 seconds)\n\n'
              'If this takes too long:\n'
              '• Force close and reopen app\n'
              '• Check adb logcat -s SaveTuneGoService');
      try {
        final res = await Dio().get(
          'http://127.0.0.1:7799/api/v1/health',
          options: Options(
            sendTimeout: const Duration(seconds: 2),
            receiveTimeout: const Duration(seconds: 2),
            validateStatus: (s) => true,
          ),
        );
        if (res.statusCode == 200) {
          serverReady = true;
          break;
        }
      } catch (_) {}
      await Future.delayed(const Duration(seconds: 1));
    }

    if (!serverReady) {
      if (mounted)
        setState(() {
          _hasError = true;
          _status = 'Music server failed to start.\n\n'
              'Make sure:\n'
              '• savetune-server binary is in assets/\n'
              '• App has storage permission\n'
              '• Try force-closing and reopening the app';
        });
      return;
    }

    if (mounted) setState(() => _status = 'Restoring session...');
    const storage = FlutterSecureStorage();
    final spDc = await storage.read(key: 'sp_dc');

    if (spDc != null && spDc.isNotEmpty) {
      try {
        await Dio().post(
          'http://127.0.0.1:7799/api/v1/config/spdc',
          data: {'sp_dc': spDc},
          options: Options(sendTimeout: const Duration(seconds: 15)),
        );
        if (mounted) {
          Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                  builder: (_) =>
                      const MainAppRouter(initialRoute: '/search')));
        }
      } catch (_) {
        if (mounted) {
          Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                  builder: (_) =>
                      const MainAppRouter(initialRoute: '/settings')));
        }
      }
    } else {
      if (mounted) {
        Navigator.pushReplacement(
            context,
            MaterialPageRoute(
                builder: (_) =>
                    const MainAppRouter(initialRoute: '/settings')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1DB954),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(Icons.music_note,
                      size: 60, color: Colors.white),
                ),
                const SizedBox(height: 32),
                const Text('SaveTune',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 36,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1)),
                const SizedBox(height: 8),
                const Text('High Fidelity Music',
                    style: TextStyle(color: Color(0xFF1DB954), fontSize: 16)),
                const SizedBox(height: 64),
                if (!_hasError) ...[
                  const SizedBox(
                    width: 40,
                    height: 40,
                    child: CircularProgressIndicator(
                      color: Color(0xFF1DB954),
                      strokeWidth: 3,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(_status,
                      style: const TextStyle(
                          color: Color(0xFF888888), fontSize: 14),
                      textAlign: TextAlign.center),
                ] else ...[
                  const Icon(Icons.error_outline, color: Colors.red, size: 56),
                  const SizedBox(height: 20),
                  Text(_status,
                      style: const TextStyle(
                          color: Colors.red, fontSize: 14, height: 1.6),
                      textAlign: TextAlign.center),
                  const SizedBox(height: 32),
                  ElevatedButton.icon(
                    onPressed: _startUp,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1DB954),
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 32, vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(100)),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// Shown when accidentally run on web
class WebNotSupportedApp extends StatelessWidget {
  const WebNotSupportedApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        backgroundColor: const Color(0xFF121212),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1DB954),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(Icons.music_note,
                      size: 60, color: Colors.white),
                ),
                const SizedBox(height: 32),
                const Text('SaveTune',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 36,
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                const Text('Android Only',
                    style: TextStyle(
                        color: Color(0xFF1DB954),
                        fontSize: 20,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 32),
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E1E1E),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFF333333)),
                  ),
                  child: Column(
                    children: [
                      const Icon(Icons.warning_amber_rounded,
                          color: Color(0xFFFFB020), size: 40),
                      const SizedBox(height: 16),
                      const Text(
                        'You are running SaveTune in a web browser.\n\n'
                        'This app requires Android because the music\n'
                        'server runs natively on your device.',
                        style: TextStyle(
                            color: Color(0xFFAAAAAA),
                            fontSize: 15,
                            height: 1.7),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      const Divider(color: Color(0xFF333333)),
                      const SizedBox(height: 16),
                      const Text('Run on Android instead:',
                          style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14)),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0A2E1A),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                              color: const Color(0xFF1DB954)
                                  .withValues(alpha: 0.4)),
                        ),
                        child: const SelectableText(
                          'flutter run -d android',
                          style: TextStyle(
                            color: Color(0xFF1DB954),
                            fontFamily: 'monospace',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class MainAppRouter extends StatelessWidget {
  final String initialRoute;
  const MainAppRouter({super.key, required this.initialRoute});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'SaveTune',
      themeMode: ThemeMode.dark,
      theme: SaveTuneTheme.darkTheme,
      routerConfig: createRouter(initialRoute),
    );
  }
}
