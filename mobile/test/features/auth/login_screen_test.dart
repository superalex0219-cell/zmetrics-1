import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/core/auth/auth_cubit.dart';
import 'package:zmetrics_mobile/core/auth/auth_repository.dart';
import 'package:zmetrics_mobile/core/config.dart';
import 'package:zmetrics_mobile/features/auth/presentation/login_screen.dart';

Widget _buildScreen(AppConfig config) {
  return MultiRepositoryProvider(
    providers: [
      RepositoryProvider<AppConfig>.value(value: config),
    ],
    child: BlocProvider(
      create: (_) => AuthCubit(MockAuthRepository()),
      child: const MaterialApp(home: LoginScreen()),
    ),
  );
}

const _mockConfig = AppConfig(
  apiBaseUrl: 'http://localhost:8000',
  useMockServices: true,
  keycloakIssuer: 'http://localhost:8080/realms/zmetrics',
  keycloakClientId: 'zmetrics-mobile',
  keycloakRedirectUri: 'zmetrics://callback',
);

const _liveConfig = AppConfig(
  apiBaseUrl: 'http://localhost:8000',
  useMockServices: false,
  keycloakIssuer: 'http://localhost:8080/realms/zmetrics',
  keycloakClientId: 'zmetrics-mobile',
  keycloakRedirectUri: 'zmetrics://callback',
);

void main() {
  group('LoginScreen', () {
    testWidgets('mock mode: single Sign in button, no text fields',
        (tester) async {
      await tester.pumpWidget(_buildScreen(_mockConfig));

      expect(find.text('Sign in'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
    });

    testWidgets('live mode: single Sign in button, no username/password fields',
        (tester) async {
      await tester.pumpWidget(_buildScreen(_liveConfig));

      expect(find.text('Sign in'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
      expect(find.text('Sign in via Keycloak'), findsOneWidget);
    });
  });
}
