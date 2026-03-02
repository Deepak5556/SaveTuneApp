import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../app/theme.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    int currentIndex = 0;
    if (location == '/search') currentIndex = 0;
    if (location == '/library') currentIndex = 1;
    if (location == '/downloads') currentIndex = 2;
    if (location == '/settings') currentIndex = 3;

    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        backgroundColor: SaveTuneTheme.surfaceColor,
        selectedItemColor: SaveTuneTheme.accentColor,
        unselectedItemColor: SaveTuneTheme.textSecondary,
        currentIndex: currentIndex,
        onTap: (index) {
          if (index == 0) context.go('/search');
          if (index == 1) context.go('/library');
          if (index == 2) context.go('/downloads');
          if (index == 3) context.go('/settings');
        },
        items: [
          const BottomNavigationBarItem(icon: Icon(Icons.search), label: 'Search'),
          const BottomNavigationBarItem(icon: Icon(Icons.library_music), label: 'Library'),
          BottomNavigationBarItem(
            icon: Stack(
              children: [
                const Icon(Icons.download),
                // Add badge logic here if needed
              ],
            ),
            label: 'Downloads',
          ),
          const BottomNavigationBarItem(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}
