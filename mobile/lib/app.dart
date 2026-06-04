import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'core/router.dart';

class ZMetricsApp extends StatelessWidget {
  const ZMetricsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'ZMetrics',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1A56DB)),
        useMaterial3: true,
      ),
      routerConfig: appRouter,
    );
  }
}
