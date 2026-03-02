import csv

errors = [
    ["Component", "File", "Error/Missing Feature Description", "Severity", "Status"],
    ["Frontend (Flutter)", "lib/features/library_screen.dart", "Library screen for tracking downloaded tracks is completely missing.", "High", "Unresolved"],
    ["Frontend (Flutter)", "lib/features/downloads_screen.dart", "Downloads progress screen displaying active queue logic is missing.", "High", "Unresolved"],
    ["Frontend (Flutter)", "lib/bottom_nav.dart", "Bottom navigation and floating mini-player components are not implemented.", "High", "Unresolved"],
    ["Frontend (Flutter)", "lib/app/router.dart", "App routing utilizing go_router is completely missing.", "High", "Unresolved"],
    ["Frontend (Flutter)", "test/widget_test.dart", "Default Flutter widget test fails due to mismatched widget structure.", "Low", "Unresolved"],
    ["Backend (Go)", "handlers/download.go", "QueueDownload and GetDownloadStatus handlers only return dummy JSON, no actual integration with engine.", "High", "Unresolved"],
    ["Backend (Go)", "handlers/library.go", "Library fetching and deleting functions return empty collections and stub status.", "High", "Unresolved"],
    ["Backend (Go)", "handlers/lyrics.go", "Lyrics fetch logic ignores the Spotify ID and simply returns empty string.", "High", "Unresolved"],
    ["Backend (Go)", "handlers/websocket.go", "Websocket for real-time progress checking is not established.", "High", "Unresolved"],
    ["Backend (Go)", "downloader/engine.go", "Engine and queuing logic lacks parallel Goroutine concurrency as designed.", "High", "Unresolved"],
    ["Backend (Go)", "downloader/ffmpeg.go", "FFMPEG binary subprocessing and extraction logic remains stubbed out.", "High", "Unresolved"],
    ["Backend (Go)", "db/queries.go", "Functions returning download state are returning nil/stub structures.", "High", "Unresolved"],
    ["Android Wrapper", "android/app/src/main/java/*/GoService.java", "Android-specific Go instance launch and lifecycle service is completely missing.", "Critical", "Unresolved"],
    ["Android Wrapper", "android/app/src/main/AndroidManifest.xml", "Missing permissions (FOREGROUND_SERVICE, INTERNET, Storage) for the Go service execution.", "Critical", "Unresolved"]
]

with open("SaveTune_Errors.csv", "w", newline='', encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerows(errors)

print("Created SaveTune_Errors.csv")


