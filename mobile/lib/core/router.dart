import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const _PlaceholderScreen(title: 'ZMetrics'),
    ),
    GoRoute(
      path: '/quarries',
      builder: (context, state) => const _PlaceholderScreen(title: 'Quarries'),
    ),
    GoRoute(
      path: '/capture',
      builder: (context, state) => const _PlaceholderScreen(title: 'Capture'),
    ),
    GoRoute(
      path: '/reports',
      builder: (context, state) => const _PlaceholderScreen(title: 'Reports'),
    ),
  ],
);

class _PlaceholderScreen extends StatelessWidget {
  final String title;
  const _PlaceholderScreen({required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(child: Text('$title — coming soon')),
    );
  }
}
