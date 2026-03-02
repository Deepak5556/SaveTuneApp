import os

files = {
    "lib/main.dart": """import 'package:flutter/material.dart';
import 'app/theme.dart';
import 'features/search/search_screen.dart';
void main() { runApp(const MyApp()); }
class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(title: 'SaveTune', themeMode: ThemeMode.dark, home: const SearchScreen());
  }
}
""",
    "lib/app/theme.dart": """import 'package:flutter/material.dart';
class SaveTuneTheme {
  static const Color primaryColor = Colors.green;
  static const Color accentColor = Colors.greenAccent;
  static const Color surfaceColor = Colors.black45;
  static const Color backgroundColor = Colors.black;
  static const Color cardColor = Colors.black87;
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Colors.grey;
  static const Color heartAccent = Colors.red;
  static const Color progressBackground = Colors.white24;
}
""",
    "lib/shared/models/track_model.dart": """class TrackModel {
  final String id;
  final String spotifyId;
  final String title;
  final String artist;
  final String album;
  final int durationMs;
  final String coverUrl;
  final String filePath;
  final String format;
  final int bitrate;
  TrackModel({required this.id, required this.spotifyId, required this.title, required this.artist, required this.album, required this.durationMs, required this.coverUrl, required this.filePath, required this.format, required this.bitrate});
  factory TrackModel.fromJson(Map<String, dynamic> json) => TrackModel(id: json['id'] ?? '', spotifyId: json['spotify_id'] ?? '', title: json['title'] ?? '', artist: json['artist'] ?? '', album: json['album'] ?? '', durationMs: json['duration_ms'] ?? 0, coverUrl: json['cover_url'] ?? '', filePath: json['file_path'] ?? '', format: json['format'] ?? '', bitrate: json['bitrate'] ?? 0);
}
""",
    "lib/shared/models/search_result_model.dart": """import 'track_model.dart';
class SearchResultModel {
  final List<TrackModel> tracks;
  SearchResultModel({required this.tracks});
  factory SearchResultModel.fromJson(Map<String, dynamic> json) => SearchResultModel(tracks: (json['tracks'] as List?)?.map((e) => TrackModel.fromJson(e)).toList() ?? []);
}
""",
    "lib/shared/models/download_job_model.dart": """enum DownloadStatus { queued, downloading, complete, error }
class DownloadJob {
  final String jobId;
  final DownloadStatus status;
  DownloadJob({required this.jobId, required this.status});
  factory DownloadJob.fromJson(Map<String, dynamic> json) => DownloadJob(jobId: json['job_id'] ?? '', status: DownloadStatus.queued);
}
""",
    "lib/shared/api/client.dart": """import 'dart:async';
import '../models/search_result_model.dart';
import '../models/download_job_model.dart';
class SaveTuneApi {
  Future<SearchResultModel> search(String query, {String? type}) async => SearchResultModel(tracks: []);
  Future<DownloadJob> queueDownload(String spotifyId) async => DownloadJob(jobId: '', status: DownloadStatus.queued);
}
"""
}

os.makedirs("assets", exist_ok=True)
with open("assets/.gitkeep", "w") as f:
    f.write("")

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
print("Flutter stubs generated.")
