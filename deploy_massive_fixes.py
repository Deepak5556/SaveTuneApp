import os

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
    "github.com/gin-gonic/gin"
)

func main() {
    port      := getEnv("PORT", "7799")
    dbPath    := getEnv("DB_PATH", "savetune.db")
    ffmpegPath := getEnv("FFMPEG_PATH", "ffmpeg")
    downloadDir := getEnv("DOWNLOAD_DIR", "./downloads")

    log.Printf("SaveTune server starting on 127.0.0.1:%s", port)
    log.Printf("DB: %s | FFmpeg: %s | Downloads: %s", dbPath, ffmpegPath, downloadDir)

    if err := db.InitDB(dbPath); err != nil { 
        log.Fatalf("DB init failed: %v", err) 
    }
    defer db.CloseDB()

    downloader.InitEngine()

    gin.SetMode(gin.ReleaseMode)
    r := gin.New()
    r.Use(gin.Recovery())
    r.Use(corsMiddleware())

    v1 := r.Group("/api/v1")
    {
        v1.GET("/health", func(c *gin.Context) {
            c.JSON(200, gin.H{"status": "ok", "timestamp": time.Now().Unix(), "authenticated": spotify.IsAuthenticated()})
        })
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

    addr := fmt.Sprintf("127.0.0.1:%s", port)
    log.Printf("Server listening on %s", addr)
    if err := r.Run(addr); err != nil {
        log.Fatalf("Server failed: %v", err)
    }
}

func getEnv(key, fallback string) string {
    if val := os.Getenv(key); val != "" { return val }
    return fallback
}

func corsMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Header("Access-Control-Allow-Origin",  "*")
        c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        if c.Request.Method == "OPTIONS" { c.AbortWithStatus(204); return }
        c.Next()
    }
}
""",

"spotify/auth.go": """package spotify

import (
    "encoding/json"
    "fmt"
    "net/http"
    "sync"
    "time"
)

type tokenStore struct {
    mu          sync.RWMutex
    accessToken string
    expiresAt   time.Time
    spDc        string
}

var store = &tokenStore{}

type tokenResponse struct {
    AccessToken     string `json:"accessToken"`
    ExpirationMs    int64  `json:"accessTokenExpirationTimestampMs"`
    IsAnonymous     bool   `json:"isAnonymous"`
    ClientID        string `json:"clientId"`
}

func SetSpDc(spDc string) error {
    token, err := fetchNewToken(spDc)
    if err != nil { return err }
    store.mu.Lock()
    store.spDc        = spDc
    store.accessToken = token.AccessToken
    store.expiresAt   = time.UnixMilli(token.ExpirationMs)
    store.mu.Unlock()
    go autoRefreshLoop()
    return nil
}

func GetToken() (string, error) {
    store.mu.RLock()
    token   := store.accessToken
    expires := store.expiresAt
    spDc    := store.spDc
    store.mu.RUnlock()

    if token == "" {
        return "", fmt.Errorf("not authenticated: no sp_dc set")
    }
    if time.Now().After(expires.Add(-60 * time.Second)) {
        newToken, err := fetchNewToken(spDc)
        if err != nil { return "", err }
        store.mu.Lock()
        store.accessToken = newToken.AccessToken
        store.expiresAt   = time.UnixMilli(newToken.ExpirationMs)
        store.mu.Unlock()
        return newToken.AccessToken, nil
    }
    return token, nil
}

func IsAuthenticated() bool {
    store.mu.RLock()
    defer store.mu.RUnlock()
    return store.spDc != "" && store.accessToken != "" && time.Now().Before(store.expiresAt)
}

func fetchNewToken(spDc string) (*tokenResponse, error) {
    client := &http.Client{Timeout: 10 * time.Second}
    req, err := http.NewRequest("GET",
        "https://open.spotify.com/get_access_token?reason=transport&productType=web_player",
        nil)
    if err != nil { return nil, err }

    req.Header.Set("Cookie",                  "sp_dc="+spDc)
    req.Header.Set("User-Agent",              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    req.Header.Set("Accept",                  "application/json")
    req.Header.Set("App-platform",            "WebPlayer")
    req.Header.Set("spotify-app-version",     "1.2.46.25.g7f189073")
    req.Header.Set("Sec-Fetch-Dest",          "empty")
    req.Header.Set("Sec-Fetch-Mode",          "cors")
    req.Header.Set("Sec-Fetch-Site",          "same-origin")

    resp, err := client.Do(req)
    if err != nil { return nil, fmt.Errorf("network error: %w", err) }
    defer resp.Body.Close()

    if resp.StatusCode == 401 { return nil, fmt.Errorf("sp_dc is invalid or expired") }
    if resp.StatusCode != 200 { return nil, fmt.Errorf("spotify returned status %d", resp.StatusCode) }

    var result tokenResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("failed to parse token response: %w", err)
    }
    if result.IsAnonymous {
        return nil, fmt.Errorf("sp_dc is invalid — got anonymous session")
    }
    if result.AccessToken == "" {
        return nil, fmt.Errorf("spotify returned empty access token")
    }
    return &result, nil
}

func autoRefreshLoop() {
    for {
        store.mu.RLock()
        expires := store.expiresAt
        spDc    := store.spDc
        store.mu.RUnlock()

        if spDc == "" {
            time.Sleep(60 * time.Second)
            continue
        }

        sleepUntil := expires.Add(-90 * time.Second)
        sleepDuration := time.Until(sleepUntil)
        if sleepDuration > 0 {
            time.Sleep(sleepDuration)
        }

        newToken, err := fetchNewToken(spDc)
        if err != nil { time.Sleep(30 * time.Second); continue }

        store.mu.Lock()
        store.accessToken = newToken.AccessToken
        store.expiresAt   = time.UnixMilli(newToken.ExpirationMs)
        store.mu.Unlock()
    }
}
""",

"spotify/search.go": """package spotify

import (
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    "strconv"
    "time"
)

type Track struct {
    ID         string `json:"id"`
    Name       string `json:"name"`
    Artist     string `json:"artist"`
    Album      string `json:"album"`
    DurationMs int    `json:"duration_ms"`
    CoverURL   string `json:"cover_url"`
}

type SearchResult struct {
    Tracks []Track `json:"tracks"`
    Total  int     `json:"total"`
    Offset int     `json:"offset"`
    Limit  int     `json:"limit"`
}

func Search(query, searchType string, limit, offset int) (*SearchResult, error) {
    if !IsAuthenticated() {
        return nil, fmt.Errorf("not authenticated: please set sp_dc in settings")
    }

    token, err := GetToken()
    if err != nil { return nil, err }

    params := url.Values{}
    params.Set("q",      query)
    params.Set("type",   searchType) // "track", "album", "playlist"
    params.Set("limit",  strconv.Itoa(limit))
    params.Set("offset", strconv.Itoa(offset))
    params.Set("market", "from_token")

    req, _ := http.NewRequest("GET",
        "https://api.spotify.com/v1/search?"+params.Encode(), nil)
    req.Header.Set("Authorization", "Bearer "+token)
    req.Header.Set("Accept",        "application/json")
    req.Header.Set("App-platform",  "WebPlayer")
    req.Header.Set("User-Agent",    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    client := &http.Client{Timeout: 10 * time.Second}
    resp, err := client.Do(req)
    if err != nil { return nil, fmt.Errorf("search network error: %w", err) }
    defer resp.Body.Close()

    // Token expired — refresh and retry once
    if resp.StatusCode == 401 {
        store.mu.RLock()
        spDc := store.spDc
        store.mu.RUnlock()

        newToken, err := fetchNewToken(spDc)
        if err != nil { return nil, fmt.Errorf("session expired: please re-enter sp_dc") }

        store.mu.Lock()
        store.accessToken = newToken.AccessToken
        store.expiresAt   = time.UnixMilli(newToken.ExpirationMs)
        store.mu.Unlock()

        return Search(query, searchType, limit, offset) // retry once
    }

    if resp.StatusCode == 429 {
        retryAfter := resp.Header.Get("Retry-After")
        return nil, fmt.Errorf("rate limited by Spotify. Wait %s seconds", retryAfter)
    }

    if resp.StatusCode != 200 {
        return nil, fmt.Errorf("spotify search returned status %d", resp.StatusCode)
    }

    var raw map[string]json.RawMessage
    json.NewDecoder(resp.Body).Decode(&raw)

    result := &SearchResult{Offset: offset, Limit: limit}

    // Parse tracks
    if tracksRaw, ok := raw["tracks"]; ok {
        var tracksWrapper struct {
            Items []struct {
                ID      string `json:"id"`
                Name    string `json:"name"`
                Artists []struct{ Name string `json:"name"` } `json:"artists"`
                Album   struct {
                    Name   string `json:"name"`
                    Images []struct{ URL string `json:"url"` } `json:"images"`
                } `json:"album"`
                DurationMs int `json:"duration_ms"`
            } `json:"items"`
            Total int `json:"total"`
        }
        json.Unmarshal(tracksRaw, &tracksWrapper)
        result.Total = tracksWrapper.Total
        for _, item := range tracksWrapper.Items {
            coverURL := ""
            if len(item.Album.Images) > 0 { coverURL = item.Album.Images[0].URL }
            artistName := ""
            if len(item.Artists) > 0 { artistName = item.Artists[0].Name }
            result.Tracks = append(result.Tracks, Track{
                ID:         item.ID,
                Name:       item.Name,
                Artist:     artistName,
                Album:      item.Album.Name,
                DurationMs: item.DurationMs,
                CoverURL:   coverURL,
            })
        }
    }

    return result, nil
}
""",

"handlers/config.go": """package handlers

import (
    "strings"
    "savetune/spotify"
    "github.com/gin-gonic/gin"
)

func SetSpDc(c *gin.Context) {
    var req struct {
        SpDc string `json:"sp_dc" binding:"required"`
    }
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": "sp_dc field is required", "code": "MISSING_SPDC"})
        return
    }

    spDc := strings.TrimSpace(req.SpDc)
    if len(spDc) < 100 {
        c.JSON(400, gin.H{
            "error": "sp_dc looks too short. Make sure you copied the entire cookie value.",
            "code":  "INVALID_FORMAT",
        })
        return
    }

    if err := spotify.SetSpDc(spDc); err != nil {
        c.JSON(401, gin.H{"error": err.Error(), "code": "AUTH_FAILED"})
        return
    }

    c.JSON(200, gin.H{"valid": true, "message": "Successfully connected to Spotify"})
}

func GetConfig(c *gin.Context) {
    c.JSON(200, gin.H{
        "authenticated": spotify.IsAuthenticated(),
        "sp_dc_set":     spotify.IsAuthenticated(),
    })
}
""",

"handlers/search.go": """package handlers

import (
    "strconv"
    "strings"
    "savetune/spotify"
    "github.com/gin-gonic/gin"
)

func Search(c *gin.Context) {
    if !spotify.IsAuthenticated() {
        c.JSON(401, gin.H{
            "error": "Not connected to Spotify. Please enter your sp_dc key in Settings.",
            "code":  "NOT_AUTHENTICATED",
        })
        return
    }

    query      := c.Query("q")
    searchType := c.DefaultQuery("type", "track")
    limit, _   := strconv.Atoi(c.DefaultQuery("limit", "20"))
    offset, _  := strconv.Atoi(c.DefaultQuery("offset", "0"))

    if strings.TrimSpace(query) == "" {
        c.JSON(400, gin.H{"error": "Search query cannot be empty", "code": "EMPTY_QUERY"})
        return
    }

    results, err := spotify.Search(query, searchType, limit, offset)
    if err != nil {
        code := "SEARCH_ERROR"
        if strings.Contains(err.Error(), "session expired") { code = "SESSION_EXPIRED" }
        if strings.Contains(err.Error(), "rate limited")    { code = "RATE_LIMITED" }
        c.JSON(500, gin.H{"error": err.Error(), "code": code})
        return
    }

    c.JSON(200, results)
}
""",

"lib/main.dart": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'app/router.dart';
import 'app/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: SaveTuneApp()));
}

class SaveTuneApp extends ConsumerWidget {
  const SaveTuneApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'SaveTune',
      theme: SaveTuneTheme.darkTheme,
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
  bool   _error  = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    // Wait for Go server (up to 30 seconds)
    setState(() => _status = 'Starting music server...');
    bool ready = false;
    for (int i = 0; i < 30; i++) {
      try {
        final res = await Dio().get(
          'http://127.0.0.1:7799/api/v1/health',
          options: Options(
            sendTimeout:    const Duration(seconds: 2),
            receiveTimeout: const Duration(seconds: 2),
            validateStatus: (s) => true,
          ),
        );
        if (res.statusCode == 200) { ready = true; break; }
      } catch (_) {}
      if (mounted) setState(() => _status = 'Starting music server... (${i+1}s)');
      await Future.delayed(const Duration(seconds: 1));
    }

    if (!ready && mounted) {
      setState(() {
        _error  = true;
        _status = 'Server failed to start.\nCheck that the app has required permissions.';
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
          options: Options(sendTimeout: const Duration(seconds: 10)),
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
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100, height: 100,
              decoration: BoxDecoration(
                color: const Color(0xFF1DB954),
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.music_note, size: 60, color: Colors.white),
            ),
            const SizedBox(height: 32),
            const Text('SaveTune',
              style: TextStyle(color: Colors.white, fontSize: 32,
                fontWeight: FontWeight.bold, letterSpacing: 1.5)),
            const SizedBox(height: 48),
            if (!_error) ...[
              const CircularProgressIndicator(color: Color(0xFF1DB954)),
              const SizedBox(height: 24),
              Text(_status,
                style: const TextStyle(color: Colors.grey, fontSize: 14),
                textAlign: TextAlign.center),
            ] else ...[
              const Icon(Icons.error_outline, color: Colors.red, size: 48),
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Text(_status,
                  style: const TextStyle(color: Colors.red, fontSize: 14),
                  textAlign: TextAlign.center),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _init,
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1DB954)),
                child: const Text('Retry'),
              ),
            ],
          ],
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
""",

"lib/app/router.dart": """import 'package:flutter/material.dart';
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
          GoRoute(path: '/search',    builder: (c, s) => const SearchScreen()),
          GoRoute(path: '/library',   builder: (c, s) => const LibraryScreen()),
          GoRoute(path: '/downloads', builder: (c, s) => const DownloadsScreen()),
          GoRoute(path: '/settings',  builder: (c, s) => const SettingsScreen()),
        ],
      ),
      GoRoute(path: '/player', builder: (c, s) => const PlayerScreen()),
      GoRoute(path: '/lyrics/:id', builder: (c, s) => LyricsScreen(spotifyId: s.pathParameters['id'] ?? '')),
    ],
  );
}
""",

"lib/shared/api/client.dart": """import 'dart:async';
import 'package:dio/dio.dart';
import '../models/search_result_model.dart';
import '../models/download_job_model.dart';
import '../models/track_model.dart';

class SaveTuneApi {
  static const _base = 'http://127.0.0.1:7799/api/v1';

  final Dio _dio = Dio(BaseOptions(
    baseUrl: _base,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
  ));

  Future<bool> isServerAlive() async {
    try {
      final res = await _dio.get('/health');
      return res.statusCode == 200;
    } catch (_) { return false; }
  }

  Future<void> validateSpDc(String spDc) async {
    try {
      await _dio.post('/config/spdc', data: {'sp_dc': spDc.trim()});
    } on DioException catch (e) {
      final msg = e.response?.data?['error'] ?? 'Connection failed. Is the app server running?';
      throw Exception(msg);
    }
  }

  Future<SearchResultModel> search(String query, {
    String type = 'track',
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final res = await _dio.get('/search', queryParameters: {
        'q': query, 'type': type, 'limit': limit, 'offset': offset,
      });
      final mapData = res.data as Map<String, dynamic>;
      
      List<TrackModel> tracks = [];
      if (mapData['tracks'] != null) {
        for (var t in mapData['tracks']) {
          tracks.add(TrackModel(
            id: t['id'] ?? '',
            spotifyId: t['id'] ?? '',
            title: t['name'] ?? '',
            artist: t['artist'] ?? '',
            album: t['album'] ?? '',
            durationMs: t['duration_ms'] ?? 0,
            coverUrl: t['cover_url'] ?? '',
            filePath: '',
            format: 'flac',
            bitrate: 1411,
          ));
        }
      }
      return SearchResultModel(tracks: tracks);
    } on DioException catch (e) {
      final code = e.response?.data?['code'] ?? '';
      final msg  = e.response?.data?['error'] ?? 'Search failed';
      if (code == 'NOT_AUTHENTICATED') throw Exception('NOT_AUTHENTICATED');
      if (code == 'SESSION_EXPIRED')   throw Exception('SESSION_EXPIRED');
      if (code == 'RATE_LIMITED')      throw Exception(msg);
      throw Exception(msg);
    }
  }

  Future<DownloadJob> queueDownload(String spotifyId) async {
    return DownloadJob(jobId: 'dummy', status: DownloadStatus.queued);
  }
}
""",

"lib/features/settings/settings_screen.dart": """import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import '../../app/theme.dart';
import '../../shared/api/client.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _spDcController = TextEditingController();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final SaveTuneApi _api = SaveTuneApi();
  
  bool _isLoading = false;
  bool _obscureText = true;
  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _checkConnection();
  }

  Future<void> _checkConnection() async {
    final savedSpDc = await _storage.read(key: 'sp_dc');
    if (savedSpDc != null && savedSpDc.isNotEmpty) {
      if (mounted) {
        setState(() {
          _isConnected = true;
          _spDcController.text = savedSpDc;
        });
      }
    }
  }

  Future<void> _validateAndSave() async {
    if (_spDcController.text.isEmpty) return;
    
    setState(() => _isLoading = true);
    try {
      await _api.validateSpDc(_spDcController.text);
      await _storage.write(key: 'sp_dc', value: _spDcController.text);
      if (mounted) {
        setState(() => _isConnected = true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✓ Connected to Spotify!'), backgroundColor: Colors.green),
        );
        Future.delayed(const Duration(seconds: 1), () {
          if (mounted) context.go('/search');
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_isConnected)
              Container(
                padding: const EdgeInsets.all(12),
                color: Colors.green.shade900,
                child: const Row(
                  children: [
                    Icon(Icons.check_circle, color: Colors.white),
                    SizedBox(width: 8),
                    Text('Currently connected', style: TextStyle(color: Colors.white)),
                  ],
                ),
              ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _spDcController,
              obscureText: _obscureText,
              maxLines: 1,
              decoration: InputDecoration(
                labelText: 'Spotify sp_dc Cookie',
                hintText: 'Paste your sp_dc cookie value here...',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: Icon(_obscureText ? Icons.visibility : Icons.visibility_off),
                  onPressed: () => setState(() => _obscureText = !_obscureText),
                ),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _validateAndSave,
              style: ElevatedButton.styleFrom(
                backgroundColor: SaveTuneTheme.primaryColor,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _isLoading
                  ? const CircularProgressIndicator(color: Colors.white)
                  : Text(_isConnected ? 'Update & Save' : 'Validate & Save', style: const TextStyle(fontSize: 16, color: Colors.white)),
            ),
            const SizedBox(height: 32),
            Card(
              color: SaveTuneTheme.surfaceColor,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('HOW TO GET YOUR sp_dc', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    SizedBox(height: 12),
                    ListTile(leading: Icon(Icons.language), title: Text('1. Open Chrome → go to open.spotify.com → log in')),
                    ListTile(leading: Icon(Icons.code), title: Text('2. Press F12 to open Developer Tools')),
                    ListTile(leading: Icon(Icons.folder), title: Text('3. Click "Application" tab in DevTools')),
                    ListTile(leading: Icon(Icons.cookie), title: Text('4. Click "Cookies" → click "https://open.spotify.com"')),
                    ListTile(leading: Icon(Icons.search), title: Text('5. Find the cookie named exactly: sp_dc')),
                    ListTile(leading: Icon(Icons.copy), title: Text('6. Click on it → copy the ENTIRE Value field')),
                    ListTile(leading: Icon(Icons.paste), title: Text('7. Paste it above → tap Validate')),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
""",

"lib/features/search/search_screen.dart": """import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../shared/api/client.dart';
import '../../shared/models/track_model.dart';
import 'widgets/track_card.dart';
import '../../app/theme.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});
  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> with SingleTickerProviderStateMixin {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  late TabController _tabController;
  Timer? _debounce;

  bool _isLoading = false;
  String? _error;
  bool _notAuthenticated = false;
  List<TrackModel> _tracks = [];
  final _api = SaveTuneApi();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _searchController.addListener(_onSearchChanged);
  }

  void _onSearchChanged() {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      if (_searchController.text.isNotEmpty) {
        _performSearch();
      } else {
        setState(() {
          _tracks = [];
          _error = null;
        });
      }
    });
  }

  Future<void> _performSearch() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _notAuthenticated = false;
    });

    try {
      final query = _searchController.text;
      final type = _tabController.index == 0 ? 'track' : _tabController.index == 1 ? 'album' : 'playlist';
      final results = await _api.search(query, type: type);
      setState(() {
        _tracks = results.tracks;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          if (e.toString().contains('NOT_AUTHENTICATED') || e.toString().contains('SESSION_EXPIRED')) {
            _notAuthenticated = true;
          } else {
            _error = e.toString();
          }
        });
      }
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    _tabController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  Widget _buildSearchResults() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_notAuthenticated) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.warning, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            const Text('Not authenticated', style: TextStyle(color: Colors.red)),
            TextButton(onPressed: () => context.go('/settings'), child: const Text('Go to Settings')),
          ],
        ),
      );
    }
    if (_error != null) {
      return Center(child: Text(_error!, style: const TextStyle(color: SaveTuneTheme.accentColor)));
    }
    if (_tracks.isEmpty) return const Center(child: Text('No results'));

    return ListView.builder(
      padding: const EdgeInsets.only(bottom: 100),
      itemCount: _tracks.length,
      itemBuilder: (context, index) => TrackCard(track: _tracks[index]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Search')),
      body: Column(
        children: [
          if (_notAuthenticated)
            Container(
              color: Colors.red.shade900,
              padding: const EdgeInsets.all(12),
              child: Row(children: [
                const Icon(Icons.warning, color: Colors.white),
                const SizedBox(width: 8),
                const Expanded(child: Text('Please set your sp_dc key in Settings first', style: TextStyle(color: Colors.white))),
                TextButton(
                  onPressed: () => context.go('/settings'),
                  child: const Text('FIX NOW', style: TextStyle(color: Colors.greenAccent)),
                ),
              ]),
            ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              focusNode: _searchFocusNode,
              decoration: InputDecoration(
                hintText: 'Songs, albums, or artists...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(icon: const Icon(Icons.clear), onPressed: () => _searchController.clear())
                    : const Icon(Icons.mic),
              ),
            ),
          ),
          TabBar(
            controller: _tabController,
            indicatorColor: SaveTuneTheme.primaryColor,
            tabs: const [Tab(text: 'Tracks'), Tab(text: 'Albums'), Tab(text: 'Playlists')],
            labelColor: SaveTuneTheme.primaryColor,
            unselectedLabelColor: SaveTuneTheme.textSecondary,
          ),
          Expanded(child: _buildSearchResults()),
        ],
      ),
    );
  }
}
""",

"android/app/src/main/java/com/example/savetune_mobile/GoService.java": """package com.example.savetune_mobile;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.res.AssetManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import java.io.*;

public class GoService extends Service {
    private static final String TAG       = "SaveTuneGoService";
    private static final String CHANNEL   = "savetune_channel";
    private static final int    NOTIF_ID  = 1001;
    private static final String SERVER_BIN = "savetune-server";
    private static final String FFMPEG_BIN = "ffmpeg";
    private Process goProcess;
    private Thread  stdoutThread;
    private Thread  stderrThread;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIF_ID, buildNotification());
        extractAndStartServer();
    }

    private void extractAndStartServer() {
        new Thread(() -> {
            try {
                File serverFile = extractAsset(SERVER_BIN);
                File ffmpegFile = extractAsset(FFMPEG_BIN);

                if (serverFile == null) {
                    Log.e(TAG, "FATAL: Failed to extract savetune-server binary");
                    return;
                }

                serverFile.setExecutable(true, false);
                if (ffmpegFile != null) ffmpegFile.setExecutable(true, false);

                Runtime.getRuntime().exec("chmod 755 " + serverFile.getAbsolutePath());

                Log.d(TAG, "Starting Go server: " + serverFile.getAbsolutePath());

                ProcessBuilder pb = new ProcessBuilder(serverFile.getAbsolutePath());
                pb.directory(getFilesDir());
                pb.environment().put("PORT", "7799");
                pb.environment().put("HOME", getFilesDir().getAbsolutePath());
                pb.environment().put("TMPDIR", getCacheDir().getAbsolutePath());
                pb.environment().put("FFMPEG_PATH",
                    ffmpegFile != null ? ffmpegFile.getAbsolutePath() : "ffmpeg");
                pb.environment().put("DB_PATH",
                    getFilesDir().getAbsolutePath() + "/savetune.db");
                pb.environment().put("DOWNLOAD_DIR",
                    getExternalFilesDir(null) != null
                        ? getExternalFilesDir(null).getAbsolutePath()
                        : getFilesDir().getAbsolutePath());
                pb.redirectErrorStream(false);
                goProcess = pb.start();

                stdoutThread = new Thread(() -> {
                    try (BufferedReader r = new BufferedReader(
                            new InputStreamReader(goProcess.getInputStream()))) {
                        String line;
                        while ((line = r.readLine()) != null)
                            Log.d(TAG, "[GO] " + line);
                    } catch (IOException e) { Log.e(TAG, "stdout error", e); }
                });
                stdoutThread.start();

                stderrThread = new Thread(() -> {
                    try (BufferedReader r = new BufferedReader(
                            new InputStreamReader(goProcess.getErrorStream()))) {
                        String line;
                        while ((line = r.readLine()) != null)
                            Log.e(TAG, "[GO-ERR] " + line);
                    } catch (IOException e) { Log.e(TAG, "stderr error", e); }
                });
                stderrThread.start();

                int exitCode = goProcess.waitFor();
                Log.e(TAG, "Go server exited with code: " + exitCode + " — restarting in 3s");
                Thread.sleep(3000);
                extractAndStartServer();

            } catch (Exception e) {
                Log.e(TAG, "Failed to start Go server", e);
            }
        }).start();
    }

    private File extractAsset(String name) {
        File outFile = new File(getFilesDir(), name);
        try {
            AssetManager assets = getAssets();
            InputStream inStream = assets.open(name);
            long assetSize = inStream.available();

            if (outFile.exists() && outFile.length() == assetSize) {
                Log.d(TAG, name + " already extracted, skipping");
                inStream.close();
                return outFile;
            }

            Log.d(TAG, "Extracting " + name + " (" + assetSize + " bytes)...");
            FileOutputStream out = new FileOutputStream(outFile);
            byte[] buf = new byte[8192];
            int len;
            while ((len = inStream.read(buf)) != -1) out.write(buf, 0, len);
            out.close();
            inStream.close();
            Log.d(TAG, name + " extracted to: " + outFile.getAbsolutePath());
            return outFile;
        } catch (IOException e) {
            Log.e(TAG, "Failed to extract asset: " + name, e);
            return null;
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (goProcess == null || !goProcess.isAlive()) {
            Log.d(TAG, "Go process not running, starting...");
            extractAndStartServer();
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (goProcess != null) goProcess.destroy();
        if (stdoutThread != null) stdoutThread.interrupt();
        if (stderrThread != null) stderrThread.interrupt();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                CHANNEL, "SaveTune Service", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Keeps SaveTune music server running");
            getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }

    private Notification buildNotification() {
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? new Notification.Builder(this, CHANNEL)
            : new Notification.Builder(this);
        return builder
            .setContentTitle("SaveTune")
            .setContentText("Music server is running")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .build();
    }
}
""",

"android/app/src/main/kotlin/com/example/savetune_mobile/MainActivity.kt": """package com.example.savetune_mobile

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startGoService()
    }

    override fun onResume() {
        super.onResume()
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
            Log.d("MainActivity", "GoService started")
        } catch (e: Exception) {
            Log.e("MainActivity", "Failed to start GoService", e)
        }
    }
}
""",

"android/app/src/main/AndroidManifest.xml": """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32"/>
    <uses-permission android:name="android.permission.WAKE_LOCK"/>

    <application
        android:label="SaveTune"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:networkSecurityConfig="@xml/network_security_config"
        android:requestLegacyExternalStorage="true"
        android:allowBackup="false">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data android:name="io.flutter.embedding.android.NormalTheme"
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
"""
}

for path, content in files.items():
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# Update pubspec.yaml to include assets!
pubspec_path = "pubspec.yaml"
with open(pubspec_path, "r", encoding="utf-8") as f:
    pubspec = f.read()

if "android/app/src/main/assets/" not in pubspec:
    if "flutter:\n" in pubspec:
        pubspec = pubspec.replace("flutter:\n", "flutter:\n  assets:\n    - android/app/src/main/assets/savetune-server\n    - android/app/src/main/assets/ffmpeg\n")
    else:
        pubspec += "\nflutter:\n  assets:\n    - android/app/src/main/assets/savetune-server\n    - android/app/src/main/assets/ffmpeg\n"
    with open(pubspec_path, "w", encoding="utf-8") as f:
        f.write(pubspec)

print("All massive files fully deployed.")
