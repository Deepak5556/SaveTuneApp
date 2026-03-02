import 'dart:async';
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
