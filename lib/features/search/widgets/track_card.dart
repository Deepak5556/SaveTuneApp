import 'package:flutter/material.dart';
import '../../../../shared/models/track_model.dart';
import '../../../../app/theme.dart';
import '../../../../shared/api/client.dart';
import '../../../../shared/models/download_job_model.dart';

class TrackCard extends StatefulWidget {
  final TrackModel track;
  const TrackCard({super.key, required this.track});
  @override
  State<TrackCard> createState() => _TrackCardState();
}

class _TrackCardState extends State<TrackCard> {
  DownloadStatus _status = DownloadStatus.queued;
  bool _isDownloading = false;

  void _handleDownload() async {
    if (_isDownloading) return;
    setState(() {
      _isDownloading = true;
      _status = DownloadStatus.downloading;
    });

    try {
      await SaveTuneApi().queueDownload(widget.track.spotifyId);
      await Future.delayed(const Duration(seconds: 1));
      if (mounted) {
        setState(() {
          _status = DownloadStatus.complete;
          _isDownloading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _status = DownloadStatus.error;
          _isDownloading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: SaveTuneTheme.cardColor,
      child: ListTile(
        title: Text(widget.track.title),
        subtitle: Text(widget.track.artist),
        trailing: IconButton(
          icon: _buildDownloadIcon(),
          onPressed: _isDownloading || _status == DownloadStatus.complete ? null : _handleDownload,
        ),
      ),
    );
  }

  Widget _buildDownloadIcon() {
    if (_status == DownloadStatus.downloading) return const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2));
    if (_status == DownloadStatus.complete) return const Icon(Icons.check_circle, color: SaveTuneTheme.primaryColor);
    return const Icon(Icons.download_for_offline);
  }
}
