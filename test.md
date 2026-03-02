You have built the complete SaveTune Mobile app (Go backend + Flutter frontend) across Phase 1 and Phase 2. Now enter AUTONOMOUS BUG HUNTING AND FIXING MODE.

Do NOT ask me questions. Do NOT wait for confirmation. Find bugs, fix them, verify the fix, move to the next bug. Keep going until every single feature works perfectly as specified in the SaveTune_Mobile_Blueprint.docx.

═══════════════════════════════════════════════════════════
STEP 1 — FULL CODEBASE AUDIT (do this before fixing anything)
═══════════════════════════════════════════════════════════

Read every single file you built. For each file check:

GO BACKEND AUDIT CHECKLIST:
□ main.go — Does Gin bind to 127.0.0.1:7799 ONLY (not 0.0.0.0)?
□ main.go — Are ALL route groups registered (config, search, download, library, lyrics, websocket)?
□ main.go — Is SQLite initialized before routes register?
□ spotify/auth.go — Does sp_dc → Bearer token fetch work with correct Spotify endpoint?
□ spotify/auth.go — Is auto-refresh loop running in a goroutine with correct timing?
□ spotify/auth.go — Is token stored in memory only, never written to disk?
□ spotify/search.go — Are all 3 types (track/album/playlist) handled?
□ spotify/search.go — Are results correctly mapped to response structs?
□ spotify/track.go — Is CDN URL correctly extracted from Spotify's track endpoint?
□ spotify/track.go — Does it handle 403 (expired URL) with retry + re-fetch?
□ handlers/config.go — Does POST /api/v1/config/spdc validate by actually calling Spotify?
□ handlers/config.go — Is sp_dc saved to EncryptedSharedPreferences via JNI or returned to Flutter for secure storage?
□ handlers/search.go — Are query params q, type, limit, offset all parsed correctly?
□ handlers/search.go — Is API response cached in api_cache table with 1h TTL?
□ handlers/download.go — Is spotify_id validated with regex ^[a-zA-Z0-9]{22}$ before processing?
□ handlers/download.go — Is goroutine launched correctly and job inserted into download_queue?
□ handlers/download.go — Does GET /download/:id return correct progress from download_queue?
□ handlers/websocket.go — Does WS push progress every 500ms correctly?
□ handlers/websocket.go — Does it handle client disconnect without crashing?
□ downloader/engine.go — Are concurrent downloads limited (max 3 at once)?
□ downloader/engine.go — Does it retry on CDN 403 by re-fetching track URL?
□ downloader/engine.go — Does it update download_queue progress in SQLite during download?
□ downloader/engine.go — On completion does it insert into tracks table and update status to "complete"?
□ downloader/ffmpeg.go — Are ALL FFmpeg args passed as []string (never shell string)?
□ downloader/ffmpeg.go — Is the arm64 binary path correct (/data/data/.../files/ffmpeg)?
□ downloader/ffmpeg.go — Is stderr captured for error reporting?
□ downloader/metadata.go — Are ALL ID3 tags set: title, artist, album, year, track number, cover art?
□ db/db.go — Are ALL 7 tables created: tracks, playlists, playlist_tracks, lyrics, download_queue, api_cache, favorites?
□ db/db.go — Are migrations idempotent (IF NOT EXISTS on all tables)?
□ db/queries.go — Are all queries using prepared statements (no string interpolation)?

FLUTTER FRONTEND AUDIT CHECKLIST:
□ pubspec.yaml — Are all 14+ dependencies listed with correct versions?
□ main.dart — Does startup health check retry 5x with 1s delay before failing?
□ main.dart — Does it redirect to /settings if sp_dc not set?
□ theme.dart — Does it match the UI reference screenshot colors exactly?
□ router.dart — Are all 6 routes defined: /settings /search /player /library /downloads /lyrics/:id?
□ router.dart — Does redirect logic prevent accessing app without sp_dc set?
□ All model files — Do @freezed models have correct fromJson/toJson?
□ All model files — Is build_runner output (.freezed.dart, .g.dart) present or instructions to generate given?
□ client.dart — Are all 9 API methods implemented completely?
□ client.dart — Does error interceptor handle: connection refused (Go server not ready), 400, 401, 404, 429, 500?
□ websocket_service.dart — Does auto-reconnect work with exponential backoff?
□ websocket_service.dart — Is StreamController properly closed on dispose?
□ audio_handler.dart — Does it handle FLAC files via just_audio correctly?
□ audio_handler.dart — Are lock screen controls working via audio_service?
□ settings_screen.dart — Does validate button show loading → success/error state?
□ settings_screen.dart — Is sp_dc stored in flutter_secure_storage after validation?
□ search_screen.dart — Is debounce 400ms implemented correctly?
□ search_screen.dart — Are all 3 tabs (Tracks/Albums/Playlists) working?
□ search_screen.dart — Does download button show idle→loading→progress→done states?
□ track_card.dart — Does tapping navigate to player with track queued?
□ player_screen.dart — Is scrubber synced to audio position stream?
□ player_screen.dart — Do all 5 controls work: shuffle, prev, play/pause, next, repeat?
□ player_screen.dart — Is mini player visible on all non-player screens?
□ player_screen.dart — Does blurred background update when track changes?
□ library_screen.dart — Does sort/filter work correctly?
□ library_screen.dart — Does swipe-to-delete call DELETE /api/v1/library/:id AND delete the file?
□ downloads_screen.dart — Does WebSocket progress update in real-time without rebuilding entire list?
□ lyrics_screen.dart — Is auto-scroll synced to audio position every 100ms?
□ lyrics_screen.dart — Does tapping a line seek the audio?
□ bottom_nav.dart — Does Downloads tab badge show active download count?
□ bottom_nav.dart — Is mini player correctly positioned above bottom nav?
□ GoService.java — Does it extract binary only when needed (version check)?
□ GoService.java — Does it restart Go process if it crashes?
□ GoService.java — Is stdout/stderr redirected to Logcat?
□ MainActivity.kt — Does it start GoService before Flutter engine?
□ AndroidManifest.xml — Are ALL required permissions declared?
□ AndroidManifest.xml — Is GoService declared with correct foregroundServiceType?

═══════════════════════════════════════════════════════════
STEP 2 — FIX ALL BUGS FOUND IN AUDIT
═══════════════════════════════════════════════════════════

For every bug found in Step 1:

- State the bug clearly: FILE + LINE + what is wrong
- Output the COMPLETE fixed file (not just the snippet)
- After outputting fixed file confirm: "✅ FIXED: [description]"
- Move immediately to the next bug

═══════════════════════════════════════════════════════════
STEP 3 — INTEGRATION TEST SIMULATION
═══════════════════════════════════════════════════════════

Mentally simulate these exact user flows end-to-end and find any breaks:

FLOW 1 — First Launch:
App opens → GoService starts → Go binary extracted → Go server starts on :7799 →
Flutter health check hits /api/v1/health → sp_dc not set → redirected to /settings
FIND AND FIX: Any point in this flow that can fail

FLOW 2 — sp_dc Setup:
User opens Settings → types sp_dc value → taps Validate →
Flutter POST /api/v1/config/spdc → Go calls Spotify token endpoint →
Success: display_name shown, sp_dc saved to EncryptedSharedPreferences →
Router redirects to /search
FIND AND FIX: Token fetch failure handling, storage failure, wrong redirect

FLOW 3 — Search and Download:
User types "Blinding Lights" → 400ms debounce → Flutter GET /api/v1/search?q=blinding+lights&type=track →
Go hits Spotify search API with Bearer token → results returned with cover art URLs →
User taps download icon → Flutter POST /api/v1/download {spotify_id} →
Go validates ID → goroutine starts → fetches CDN URL → streams through FFmpeg →
WebSocket pushes progress every 500ms → Flutter progress bar updates →
Download completes → track inserted in SQLite → WebSocket sends "complete" →
Flutter download button shows checkmark
FIND AND FIX: Bearer token expiry during download, FFmpeg path wrong, WebSocket message format mismatch, progress not updating UI

FLOW 4 — Playback:
User taps track in search results → navigates to /player →
audio_handler loads FLAC file path → just_audio begins playback →
Scrubber updates every 1s → lyrics fetch from /api/v1/lyrics/:id →
Lyrics auto-scroll synced to position → user drags scrubber → audio seeks →
lyrics scroll jumps to correct line → user locks phone →
lock screen shows album art + controls → user skips track from lock screen
FIND AND FIX: Local file URI format for just_audio, lyrics timing off, lock screen controls not working

FLOW 5 — Library Management:
User opens Library tab → GET /api/v1/library → tracks listed →
User sorts by Artist → list re-orders correctly →
User searches "weeknd" → filtered results →
User swipes left on track → confirmation dialog →
User confirms → DELETE /api/v1/library/:id called → file deleted from disk → track removed from list
FIND AND FIX: File deletion not removing from UI, sort not working, search filter case sensitivity

FLOW 6 — App Backgrounded and Restored:
User starts download → backgrounds app → 10 minutes later reopens →
Download should have continued (GoService kept Go alive) →
WebSocket should reconnect → progress should show correctly →
Audio should still be playing (audio_service background mode)
FIND AND FIX: GoService killed by Android, WebSocket not reconnecting, audio stopping

FLOW 7 — Error Recovery:
sp_dc expires mid-session → search returns 401 →
Go detects 401 → tries to refresh token → refresh fails (sp_dc expired) →
Flutter receives AUTH_EXPIRED error → shows "Session expired, please update sp_dc" →
Routes back to settings screen
FIND AND FIX: Infinite retry loop on 401, crash on nil token, no user feedback

═══════════════════════════════════════════════════════════
STEP 4 — PERFORMANCE BUGS
═══════════════════════════════════════════════════════════

Check and fix these specific performance issues:

□ Library list with 500+ tracks — is it using ListView.builder (lazy) not ListView (eager)?
□ Search results — are CachedNetworkImage placeholders shown instantly?
□ WebSocket — is downloads screen using StreamBuilder correctly (not setState on every message causing full rebuild)?
□ Lyrics — is the 100ms position polling using a Timer.periodic that is properly cancelled on dispose?
□ Go backend — is the api_cache TTL check working (expired cache not served)?
□ Go backend — are goroutines properly limited (semaphore pattern for max 3 concurrent downloads)?
□ Go backend — is sync.Mutex used on the download progress map to prevent race conditions?
□ Audio player — is the AudioPlayer instance singleton (not recreated on screen rebuild)?
□ Album art — are large images resized before caching (not storing 3000x3000 originals)?

Fix every performance bug found. Output complete fixed files.

═══════════════════════════════════════════════════════════
STEP 5 — ANDROID-SPECIFIC BUGS
═══════════════════════════════════════════════════════════

Check and fix these Android-specific issues:

□ Android 13+ (API 33+): READ_MEDIA_AUDIO permission requested at runtime?
□ Android 12+ (API 31+): Foreground service type declared correctly in manifest?
□ Android 10+ (API 29+): Scoped storage — are FLAC files written to MediaStore or app-specific Music dir?
□ File URI vs Content URI — does just_audio receive correct URI format for local FLAC files?
□ Go binary execute permission — is chmod +x called after extraction?
□ Go binary architecture — is arm64-v8a binary used on arm64 devices, x86_64 on emulators?
□ Network security config — does res/xml/network_security_config.xml allow cleartext to 127.0.0.1?
□ Battery optimization — is GoService excluded from battery optimization prompt shown to user?
□ Audio focus — does audio pause on incoming call and resume after?
□ Notification channel — is audio_service notification channel created for Android 8+?

Fix every Android bug found. Output complete fixed files.

═══════════════════════════════════════════════════════════
STEP 6 — UI PIXEL-PERFECT CHECK
═══════════════════════════════════════════════════════════

Re-examine the UI reference screenshot. Check every screen:

□ Colors: does every screen use the exact hex colors from theme.dart (extracted from screenshot)?
□ Typography: correct font sizes, weights, letter spacing on all text elements?
□ Card radius: consistent border radius matching the reference?
□ Spacing: padding and margins match the screenshot?
□ Bottom nav: icons, labels, active state matching reference exactly?
□ Search bar: shape, border, icon placement matching reference?
□ Player screen: album art size relative to screen, control sizing matching reference?
□ Progress bars: color, height, border radius matching reference?
□ Download badges: shape, color, position matching reference?
□ Mini player: height, content layout, position above bottom nav matching reference?

For every mismatch found: output the fixed widget file completely.

═══════════════════════════════════════════════════════════
STEP 7 — FINAL VERIFICATION CHECKLIST
═══════════════════════════════════════════════════════════

After all fixes, confirm every item in the blueprint is implemented:

BACKEND:
□ Go server on 127.0.0.1:7799 loopback only
□ sp_dc → Bearer token → auto-refresh working
□ All 7 API endpoints implemented and returning correct schemas
□ WebSocket pushing progress every 500ms
□ SQLite with all 7 tables and idempotent migrations
□ FFmpeg muxing to FLAC with full ID3 metadata
□ Filename sanitization on all file writes
□ spotify_id regex validation on all inputs
□ Max 3 concurrent downloads with goroutine limiting
□ Retry on CDN 403 with re-fetch of stream URL
□ api_cache with 1h TTL working correctly

FLUTTER:
□ Health check on startup with 5 retries
□ Redirect to settings if sp_dc missing
□ sp_dc stored in EncryptedSharedPreferences
□ All 6 screens implemented and navigable
□ Persistent mini player above bottom nav on all screens
□ Real-time download progress via WebSocket
□ FLAC playback working via just_audio + audio_service
□ Background audio playback working
□ Lock screen controls working
□ Synchronized lyrics with tap-to-seek
□ Library sort, filter, search working
□ Swipe-to-delete working end-to-end
□ All error states handled with user-friendly messages
□ All loading states with appropriate indicators
□ UI matches reference screenshot on all screens

ANDROID:
□ GoService starts Go binary as Foreground Service
□ Go binary extracted from assets on first launch
□ FFmpeg binary extracted from assets on first launch
□ All required permissions declared in manifest
□ Network security config allows 127.0.0.1 cleartext
□ Audio focus handling working
□ Notification controls working

═══════════════════════════════════════════════════════════
STEP 8 — OUTPUT FINAL DELIVERABLE
═══════════════════════════════════════════════════════════

After all bugs are fixed and all checks pass, output:

1. COMPLETE LIST OF ALL BUGS FIXED:
   Format: [FILE] — [Bug description] — [Fix applied]
2. COMPLETE FINAL PROJECT STRUCTURE:
   Full folder tree of every file in the project
3. SETUP AND RUN COMMANDS:
   # Build Go backend for Android arm64

   # Generate Flutter freezed models

   # Run on Android device

   # Build release APK
4. HOW TO GET sp_dc FROM BROWSER:
   Step-by-step Chrome DevTools instructions with exact cookie name
5. KNOWN LIMITATIONS:
   Anything that depends on Spotify not changing their internal API

═══════════════════════════════════════════════════════════

START NOW WITH STEP 1 — FULL CODEBASE AUDIT.
Do not ask questions. Do not wait. Begin auditing immediately.
Output every bug found, fix it with complete file output, and keep going until the app works perfectly as described in SaveTune_Mobile_Blueprint.docx.
