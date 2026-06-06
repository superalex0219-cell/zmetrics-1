import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_context.dart';
import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/passport_detail_cubit.dart';
import '../domain/blast_passport.dart';

/// Passport detail with the human-initiated state-transition actions.
///
/// SAFETY: buttons map 1:1 to explicit backend actions (submit/approve/
/// revise). The backend enforces per-quarry RBAC; the UI never auto-advances
/// state and offers no bulk action (rules/product-safety.md).
class PassportDetailScreen extends StatelessWidget {
  const PassportDetailScreen({super.key, required this.quarryId});

  final String quarryId;

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Passport',
      body: BlocBuilder<PassportDetailCubit, DataState<BlastPassport>>(
        builder: (context, state) => AsyncView<BlastPassport>(
          state: state,
          onRetry: () => context.read<PassportDetailCubit>().load(),
          onData: (context, p) => _PassportBody(quarryId: quarryId, passport: p),
        ),
      ),
    );
  }
}

class _PassportBody extends StatelessWidget {
  const _PassportBody({required this.quarryId, required this.passport});

  final String quarryId;
  final BlastPassport passport;

  @override
  Widget build(BuildContext context) {
    final cubit = context.read<PassportDetailCubit>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Status: ${passport.status.label}',
            style: Theme.of(context).textTheme.titleMedium),
        Text('Revision ${passport.revisionNumber}'),
        const Divider(height: 24),
        _row('Explosive type', passport.explosiveType),
        _row('Total explosive', passport.totalExplosiveKg, unit: 'kg'),
        _row('Hole diameter', passport.holeDiameterMm, unit: 'mm'),
        _row('Hole depth', passport.holeDepthM, unit: 'm'),
        _row('Burden', passport.burdenM, unit: 'm'),
        _row('Spacing', passport.spacingM, unit: 'm'),
        _row('Stemming', passport.stemmingM, unit: 'm'),
        _row('Target P80', passport.targetP80Mm, unit: 'mm'),
        const Divider(height: 24),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            // Action visibility = passport state AND the user's role. The
            // backend enforces per-quarry RBAC; this hides dead-end buttons.
            if (passport.status.canSubmit && context.canManageBlastingOn(quarryId))
              FilledButton.icon(
                icon: const Icon(Icons.send),
                label: const Text('Submit'),
                onPressed: () => _run(context, cubit.submit, 'Submitted'),
              ),
            if (passport.status.canApprove && context.canApproveOn(quarryId))
              FilledButton.icon(
                icon: const Icon(Icons.verified),
                label: const Text('Approve'),
                onPressed: () => _run(context, cubit.approve, 'Approved'),
              ),
            if (passport.status.canComplete && context.canApproveOn(quarryId))
              FilledButton.icon(
                icon: const Icon(Icons.task_alt),
                label: const Text('Complete'),
                onPressed: () => _run(context, cubit.complete, 'Completed'),
              ),
            if (passport.status.canRevise && context.canManageBlastingOn(quarryId))
              OutlinedButton.icon(
                icon: const Icon(Icons.history_edu),
                label: const Text('Create revision'),
                onPressed: () => _run(context, () => cubit.revise(), 'New revision created'),
              ),
            OutlinedButton.icon(
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Captures'),
              onPressed: () => context.go(
                  '/quarries/$quarryId/passports/${passport.id}/captures'),
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.analytics_outlined),
              label: const Text('Reports'),
              onPressed: () => context.go('/quarries/$quarryId/reports'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _row(String label, Object? value, {String? unit}) {
    if (value == null) return const SizedBox.shrink();
    final text = unit == null ? '$value' : '$value $unit';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          Text(text, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Future<void> _run(
    BuildContext context,
    Future<void> Function() action,
    String okMessage,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await action();
      messenger.showSnackBar(SnackBar(content: Text(okMessage)));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  }
}
