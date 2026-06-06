import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/auth/auth_cubit.dart';
import '../../../core/config.dart';

/// Sign-in screen. In mock mode this is a one-tap fake login; against the live
/// backend it does a dev ROPC login (username/password) to Keycloak.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // Dev defaults for the seeded Keycloak user (admin-user / changeme).
  final _username = TextEditingController(text: 'admin-user');
  final _password = TextEditingController(text: 'changeme');

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

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
                    const Icon(Icons.landscape, size: 64, color: Color(0xFF1A56DB)),
                    const SizedBox(height: 16),
                    Text('ZMetrics',
                        style: Theme.of(context).textTheme.headlineMedium),
                    const SizedBox(height: 4),
                    Text(mock ? 'Mock mode' : 'Connected to backend',
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 24),
                    if (!mock) ...[
                      TextField(
                        controller: _username,
                        decoration: const InputDecoration(
                            labelText: 'Username', border: OutlineInputBorder()),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _password,
                        obscureText: true,
                        decoration: const InputDecoration(
                            labelText: 'Password', border: OutlineInputBorder()),
                        onSubmitted: (_) => _signIn(context, mock),
                      ),
                      const SizedBox(height: 16),
                    ],
                    if (state is Unauthenticated && state.message != null) ...[
                      Text(state.message!,
                          style: const TextStyle(color: Colors.red),
                          textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                    ],
                    FilledButton.icon(
                      onPressed: busy ? null : () => _signIn(context, mock),
                      icon: busy
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.login),
                      label: const Text('Sign in'),
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

  void _signIn(BuildContext context, bool mock) {
    final cubit = context.read<AuthCubit>();
    if (mock) {
      cubit.signIn();
    } else {
      cubit.signIn(
        username: _username.text.trim(),
        password: _password.text,
      );
    }
  }
}
