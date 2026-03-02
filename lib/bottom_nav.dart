import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class BottomNavLayout extends StatelessWidget {
  final Widget child;
  const BottomNavLayout({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    int currentIndex = 0;
    if (location == '/library') currentIndex = 1;
    if (location == '/downloads') currentIndex = 2;

    return Scaffold(
      body: Column(
        children: [
          Expanded(child: child),
          Container(height: 60, color: Colors.blueGrey, child: const Center(child: Text('Mini-Player'))),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: currentIndex,
        onTap: (index) {
          if (index == 0) context.go('/');
          if (index == 1) context.go('/library');
          if (index == 2) context.go('/downloads');
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.search), label: 'Search'),
          BottomNavigationBarItem(icon: Icon(Icons.library_music), label: 'Library'),
          BottomNavigationBarItem(icon: Icon(Icons.download), label: 'Downloads'),
        ],
      ),
    );
  }
}
