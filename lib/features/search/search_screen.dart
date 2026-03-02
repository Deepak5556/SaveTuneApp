import 'dart:async';
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
