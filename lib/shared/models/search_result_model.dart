import 'track_model.dart';
class SearchResultModel {
  final List<TrackModel> tracks;
  SearchResultModel({required this.tracks});
  factory SearchResultModel.fromJson(Map<String, dynamic> json) => SearchResultModel(tracks: (json['tracks'] as List?)?.map((e) => TrackModel.fromJson(e)).toList() ?? []);
}
