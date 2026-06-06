import 'package:flutter/material.dart';

import '../bloc/data_state.dart';

/// Renders a [DataState] as loading spinner / error+retry / data.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    super.key,
    required this.state,
    required this.onData,
    this.onRetry,
  });

  final DataState<T> state;
  final Widget Function(BuildContext context, T value) onData;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return switch (state) {
      DataLoading<T>() =>
        const Center(child: CircularProgressIndicator()),
      DataFailure<T>(message: final m) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 40, color: Colors.red),
                const SizedBox(height: 12),
                Text(m, textAlign: TextAlign.center),
                if (onRetry != null) ...[
                  const SizedBox(height: 12),
                  FilledButton.tonal(
                    onPressed: onRetry,
                    child: const Text('Retry'),
                  ),
                ],
              ],
            ),
          ),
        ),
      DataLoaded<T>(value: final v) => onData(context, v),
    };
  }
}
