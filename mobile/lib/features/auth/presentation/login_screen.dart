import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/auth/auth_cubit.dart';
import '../../../core/config.dart';

/// Sign-in screen. In mock mode this is a one-tap fake login; in live mode
/// it opens the Keycloak OIDC browser flow (PKCE via flutter_appauth).
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final mock = context.read<AppConfig>().useMockServices;
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: BlocBuilder<AuthCubit, AuthState>(
              builder: (context, state) {
                final busy = state is AuthInProgress;
                return Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.landscape, size: 64, color: Color(0xFF0F766E)),
                    const SizedBox(height: 16),
                    Text('ZMetrics',
                        style: Theme.of(context).textTheme.headlineMedium),
                    const SizedBox(height: 4),
                    Text(mock ? 'Демо-режим' : 'Войдите через Keycloak',
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 24),
                    if (state is Unauthenticated && state.message != null) ...[
                      Text(state.message!,
                          style: const TextStyle(color: Colors.red),
                          textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                    ],
                    FilledButton.icon(
                      onPressed: busy ? null : () => _signIn(context),
                      icon: busy
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.login),
                      label: const Text('Войти'),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }

  void _signIn(BuildContext context) {
    context.read<AuthCubit>().signIn();
  }
}
