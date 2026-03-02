enum DownloadStatus { queued, downloading, complete, error }
class DownloadJob {
  final String jobId;
  final DownloadStatus status;
  DownloadJob({required this.jobId, required this.status});
  factory DownloadJob.fromJson(Map<String, dynamic> json) => DownloadJob(jobId: json['job_id'] ?? '', status: DownloadStatus.queued);
}
