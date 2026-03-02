import 'package:flutter/material.dart';
class LyricsScreen extends StatelessWidget {
  final String spotifyId;
  const LyricsScreen({super.key, required this.spotifyId});
  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Center(child: Text("Lyrics Screen: $spotifyId")));
  }
}