class TrackModel {
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
