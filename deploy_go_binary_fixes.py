import os
import shutil

files = {
"main.go": """package main

import (
    "fmt"
    "log"
    "os"
    "time"
    "savetune/db"
    "savetune/downloader"
    "savetune/handlers"
    "savetune/spotify"
    // Use modernc.org/sqlite, not github.com/mattn/go-sqlite3
    _ "modernc.org/sqlite"
    "github.com/gin-gonic/gin"
)

func main() {
    // Read all config from env (set by GoService.java)
    host        := getEnv("HOST",         "127.0.0.1")
    port        := getEnv("PORT",         "7799")
    dbPath      := getEnv("DB_PATH",      "./savetune.db")
    downloadDir := getEnv("DOWNLOAD_DIR", "./downloads")
    ffmpegPath  := getEnv("FFMPEG_PATH",  "ffmpeg")

    log.SetFlags(log.LstdFlags | log.Lshortfile)
    log.Printf("=== SaveTune Server Starting ===")
    log.Printf("Bind:     %s:%s", host, port)
    log.Printf("DB:       %s", dbPath)
    log.Printf("Downloads:%s", downloadDir)
    log.Printf("FFmpeg:   %s", ffmpegPath)

    // Create download dir
    if err := os.MkdirAll(downloadDir, 0755); err != nil {
        log.Printf("Warning: could not create download dir: %v", err)
    }

    // Init DB
    if err := db.InitDB(dbPath); err != nil {
        log.Fatalf("FATAL: DB init failed: %v", err)
    }
    defer db.CloseDB()
    log.Printf("DB initialized: %s", dbPath)

    downloader.InitEngine()

    // Init Gin
    gin.SetMode(gin.ReleaseMode)
    r := gin.New()
    r.Use(gin.Recovery())
    r.Use(func(c *gin.Context) {
        c.Header("Access-Control-Allow-Origin",  "*")
        c.Header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        c.Header("Access-Control-Allow-Headers", "Content-Type")
        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }
        c.Next()
    })

    // Health check — Flutter polls this to know server is ready
    r.GET("/api/v1/health", func(c *gin.Context) {
        c.JSON(200, gin.H{
            "status":    "ok",
            "timestamp": time.Now().Unix(),
            "version":   "1.0.0",
        })
    })

    // All other routes
    v1 := r.Group("/api/v1")
    {
        v1.POST("/config/spdc", handlers.SetSpDc)
        v1.GET("/config",       handlers.GetConfig)
        v1.GET("/search",       handlers.Search)
        v1.POST("/download",    handlers.QueueDownload)
        v1.GET("/download/:id", handlers.GetDownloadStatus)
        v1.GET("/library",      handlers.GetLibrary)
        v1.DELETE("/library/:id", handlers.DeleteLibraryItem)
        v1.GET("/lyrics/:spotify_id",   handlers.GetLyrics)
    }
    r.GET("/ws/downloads", handlers.WebSocketDownloads)

    addr := fmt.Sprintf("%s:%s", host, port)
    log.Printf("Server ready on http://%s", addr)
    log.Printf("Health: http://%s/api/v1/health", addr)

    if err := r.Run(addr); err != nil {
        log.Fatalf("FATAL: Server failed: %v", err)
    }
}

func getEnv(key, fallback string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return fallback
}
""",

"android/app/src/main/java/com/example/savetune_mobile/GoService.java": """package com.example.savetune_mobile;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

public class GoService extends Service {
    private static final String TAG = "SaveTuneGoService";
    private static final String CHANNEL_ID = "savetune_go_channel";
    private static final int NOTIFICATION_ID = 9001;

    private Process serverProcess;
    private volatile boolean running = false;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "GoService onCreate");
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
        extractAndStart();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "GoService onStartCommand");
        if (!running || serverProcess == null || !isProcessAlive()) {
            extractAndStart();
        }
        return START_STICKY;
    }

    private boolean isProcessAlive() {
        try {
            serverProcess.exitValue();
            return false; // process ended
        } catch (IllegalThreadStateException e) {
            return true; // still running
        }
    }

    private void extractAndStart() {
        new Thread(() -> {
            try {
                File serverFile = extractBinary("savetune-server");
                if (serverFile == null) {
                    Log.e(TAG, "FATAL: Could not extract savetune-server");
                    return;
                }

                // Make executable
                boolean chmod = serverFile.setExecutable(true, false);
                Log.d(TAG, "chmod executable: " + chmod);

                // Double-check with shell chmod
                try {
                    Runtime.getRuntime().exec(
                        new String[]{"chmod", "755", serverFile.getAbsolutePath()}
                    ).waitFor();
                } catch (Exception e) {
                    Log.w(TAG, "shell chmod failed (ok): " + e.getMessage());
                }

                Log.d(TAG, "Binary path: " + serverFile.getAbsolutePath());
                Log.d(TAG, "Binary size: " + serverFile.length() + " bytes");
                Log.d(TAG, "Binary executable: " + serverFile.canExecute());

                // Prepare paths
                File dbFile = new File(getFilesDir(), "savetune.db");
                File dlDir = getExternalFilesDir("Music");
                if (dlDir == null) dlDir = new File(getFilesDir(), "downloads");
                dlDir.mkdirs();

                File ffmpegFile = extractBinary("ffmpeg");
                String ffmpegPath = (ffmpegFile != null && ffmpegFile.canExecute())
                    ? ffmpegFile.getAbsolutePath() : "";

                // Build and start process
                ProcessBuilder pb = new ProcessBuilder(serverFile.getAbsolutePath());
                pb.directory(getFilesDir());
                pb.redirectErrorStream(false);

                // Environment variables — Go binary reads these
                pb.environment().put("PORT",          "7799");
                pb.environment().put("HOST",          "127.0.0.1");
                pb.environment().put("DB_PATH",       dbFile.getAbsolutePath());
                pb.environment().put("DOWNLOAD_DIR",  dlDir.getAbsolutePath());
                pb.environment().put("FFMPEG_PATH",   ffmpegPath);
                pb.environment().put("HOME",          getFilesDir().getAbsolutePath());
                pb.environment().put("TMPDIR",        getCacheDir().getAbsolutePath());

                Log.d(TAG, "Starting Go server on 127.0.0.1:7799");
                serverProcess = pb.start();
                running = true;

                // Stream stdout to logcat
                new Thread(() -> {
                    try (BufferedReader br = new BufferedReader(
                            new InputStreamReader(serverProcess.getInputStream()))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            Log.i(TAG, "STDOUT: " + line);
                        }
                    } catch (IOException e) {
                        Log.e(TAG, "stdout reader error", e);
                    }
                }, "go-stdout").start();

                // Stream stderr to logcat
                new Thread(() -> {
                    try (BufferedReader br = new BufferedReader(
                            new InputStreamReader(serverProcess.getErrorStream()))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            Log.e(TAG, "STDERR: " + line);
                        }
                    } catch (IOException e) {
                        Log.e(TAG, "stderr reader error", e);
                    }
                }, "go-stderr").start();

                // Monitor and restart on crash
                int exitCode = serverProcess.waitFor();
                running = false;
                Log.e(TAG, "Go server exited with code: " + exitCode);
                Log.d(TAG, "Restarting in 2 seconds...");
                Thread.sleep(2000);
                extractAndStart();

            } catch (Exception e) {
                Log.e(TAG, "extractAndStart failed", e);
                running = false;
            }
        }, "go-server-thread").start();
    }

    private File extractBinary(String name) {
        File outFile = new File(getFilesDir(), name);
        try {
            InputStream in = getAssets().open(name);
            int assetSize = in.available();
            Log.d(TAG, "Extracting " + name + " (" + assetSize + " bytes)");

            // Always re-extract to ensure correct binary
            FileOutputStream out = new FileOutputStream(outFile);
            byte[] buffer = new byte[16384];
            int bytesRead;
            int total = 0;
            while ((bytesRead = in.read(buffer)) != -1) {
                out.write(buffer, 0, bytesRead);
                total += bytesRead;
            }
            out.flush();
            out.close();
            in.close();

            Log.d(TAG, "Extracted " + name + ": " + total + " bytes to " + outFile.getAbsolutePath());
            return outFile;
        } catch (IOException e) {
            Log.e(TAG, "Failed to extract " + name + ": " + e.getMessage());
            // If asset doesn't exist, return null gracefully
            return null;
        }
    }

    @Override
    public void onDestroy() {
        Log.d(TAG, "GoService onDestroy");
        running = false;
        if (serverProcess != null) {
            serverProcess.destroy();
            serverProcess = null;
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "SaveTune Server",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Keeps the SaveTune music server running");
            channel.setShowBadge(false);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification() {
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        return builder
            .setContentTitle("SaveTune")
            .setContentText("Music server running")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setOngoing(true)
            .build();
    }
}
""",

"android/app/src/main/kotlin/com/example/savetune_mobile/MainActivity.kt": """package com.example.savetune_mobile

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {

    companion object {
        private const val TAG = "SaveTuneMain"
        private const val REQ_PERMISSIONS = 100
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "MainActivity onCreate")
        requestRequiredPermissions()
        startGoService()
    }

    override fun onResume() {
        super.onResume()
        // Re-start service if killed
        startGoService()
    }

    private fun startGoService() {
        try {
            val intent = Intent(this, GoService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
            Log.d(TAG, "GoService start requested")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start GoService: ${e.message}", e)
        }
    }

    private fun requestRequiredPermissions() {
        val needed = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // Android 13+
            if (ContextCompat.checkSelfPermission(this,
                    Manifest.permission.READ_MEDIA_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.READ_MEDIA_AUDIO)
            }
            if (ContextCompat.checkSelfPermission(this,
                    Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        } else {
            // Android 12 and below
            if (ContextCompat.checkSelfPermission(this,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
            if (ContextCompat.checkSelfPermission(this,
                    Manifest.permission.READ_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
        }

        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this, needed.toTypedArray(), REQ_PERMISSIONS)
        }
    }
}
""",

"android/app/src/main/AndroidManifest.xml": """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32"/>
    <uses-permission android:name="android.permission.WAKE_LOCK"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>

    <application
        android:label="SaveTune"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:networkSecurityConfig="@xml/network_security_config"
        android:allowBackup="false"
        android:extractNativeLibs="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
                android:name="io.flutter.embedding.android.NormalTheme"
                android:resource="@style/NormalTheme"/>
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

        <service
            android:name=".GoService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="dataSync"
            android:stopWithTask="false"/>

        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />

    </application>
    <queries>
        <intent>
            <action android:name="android.intent.action.PROCESS_TEXT"/>
            <data android:mimeType="text/plain"/>
        </intent>
    </queries>
</manifest>
""",

"android/app/src/main/res/xml/network_security_config.xml": """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="false">127.0.0.1</domain>
        <domain includeSubdomains="false">localhost</domain>
    </domain-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system"/>
        </trust-anchors>
    </base-config>
</network-security-config>
""",

"pubspec.yaml": """name: savetune_mobile
description: SaveTune Mobile App
publish_to: 'none'

version: 1.0.0+1

environment:
  sdk: '>=3.2.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  just_audio: ^0.9.38
  audio_service: ^0.18.13
  dio: ^5.4.0
  flutter_secure_storage: ^9.0.0
  riverpod: ^2.5.0
  flutter_riverpod: ^2.5.0
  go_router: ^14.0.0
  cached_network_image: ^3.3.0
  fl_chart: ^0.67.0
  lottie: ^3.1.0
  freezed_annotation: ^2.4.0
  json_annotation: ^4.9.0
  web_socket_channel: ^2.4.0
  path_provider: ^2.1.0
  permission_handler: ^11.3.0
  google_fonts: ^6.1.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: any
  freezed: any
  json_serializable: any

flutter:
  uses-material-design: true
  assets:
    - assets/
    - android/app/src/main/assets/savetune-server
    - android/app/src/main/assets/ffmpeg
""",

"lib/main.dart": """import 'package:flutter/foundation.dart';
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
    setState(() { _hasError = false; _status = 'Starting music server...'; });

    bool serverReady = false;
    // Wait up to 60 seconds for Go server
    for (int i = 0; i < 60; i++) {
      if (!mounted) return;
      setState(() => _status =
        'Starting music server...\\n(${i + 1}/60 seconds)\\n\\n'
        'If this takes too long:\\n'
        '• Force close and reopen app\\n'
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
      if (mounted) setState(() {
        _hasError = true;
        _status = 'Music server failed to start.\\n\\n'
            'Make sure:\\n'
            '• savetune-server binary is in assets/\\n'
            '• App has storage permission\\n'
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
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const MainAppRouter(initialRoute: '/search')));
        }
      } catch (_) {
        if (mounted) {
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const MainAppRouter(initialRoute: '/settings')));
        }
      }
    } else {
      if (mounted) {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const MainAppRouter(initialRoute: '/settings')));
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
                  width: 100, height: 100,
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
                    color: Colors.white, fontSize: 36,
                    fontWeight: FontWeight.bold, letterSpacing: 1)),
                const SizedBox(height: 8),
                const Text('High Fidelity Music',
                  style: TextStyle(color: Color(0xFF1DB954), fontSize: 16)),
                const SizedBox(height: 64),
                if (!_hasError) ...[
                  const SizedBox(
                    width: 40, height: 40,
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
                  const Icon(Icons.error_outline,
                    color: Colors.red, size: 56),
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
                  width: 100, height: 100,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1DB954),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(Icons.music_note,
                    size: 60, color: Colors.white),
                ),
                const SizedBox(height: 32),
                const Text('SaveTune',
                  style: TextStyle(color: Colors.white, fontSize: 36,
                    fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                const Text('Android Only',
                  style: TextStyle(color: Color(0xFF1DB954),
                    fontSize: 20, fontWeight: FontWeight.w600)),
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
                        'You are running SaveTune in a web browser.\\n\\n'
                        'This app requires Android because the music\\n'
                        'server runs natively on your device.',
                        style: TextStyle(color: Color(0xFFAAAAAA),
                          fontSize: 15, height: 1.7),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      const Divider(color: Color(0xFF333333)),
                      const SizedBox(height: 16),
                      const Text('Run on Android instead:',
                        style: TextStyle(color: Colors.white,
                          fontWeight: FontWeight.bold, fontSize: 14)),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0A2E1A),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: const Color(0xFF1DB954).withOpacity(0.4)),
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
"""
}

# Remove old unused kotlin code to avoid duplicate class resolution
try:
    shutil.rmtree("android/app/src/main/kotlin/com/savetune/app", ignore_errors=True)
except:
    pass

for path, content in files.items():
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Files generated and deployed successfully.")
