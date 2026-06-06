import 'package:flutter/material.dart';

import 'app.dart';
import 'core/di.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Composition root. Defaults to mock services (config.useMockServices) so
  // the app runs standalone — no backend / Keycloak / MinIO / worker required.
  final deps = AppDependencies.create();
  runApp(ZMetricsApp(deps: deps));
}
