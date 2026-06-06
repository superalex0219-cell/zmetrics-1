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
      title: 'Паспорт БВР',
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
        Text('Статус: ${passport.status.label}',
            style: Theme.of(context).textTheme.titleMedium),
        Text('Редакция ${passport.revisionNumber}'),
        const Divider(height: 24),
        _row('Тип ВВ', passport.explosiveType),
        _row('Масса ВВ', passport.totalExplosiveKg, unit: 'кг'),
        _row('Диаметр скв.', passport.holeDiameterMm, unit: 'мм'),
        _row('Глубина скв.', passport.holeDepthM, unit: 'м'),
        _row('Линия сопротивления', passport.burdenM, unit: 'м'),
        _row('Расстояние между скв.', passport.spacingM, unit: 'м'),
        _row('Забойка', passport.stemmingM, unit: 'м'),
        _row('Цель P80', passport.targetP80Mm, unit: 'мм'),
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
                label: const Text('Подать'),
                onPressed: () => _run(context, cubit.submit, 'Паспорт подан'),
              ),
            if (passport.status.canApprove && context.canApproveOn(quarryId))
              FilledButton.icon(
                icon: const Icon(Icons.verified),
                label: const Text('Одобрить'),
                onPressed: () => _run(context, cubit.approve, 'Паспорт одобрен'),
              ),
            if (passport.status.canComplete && context.canApproveOn(quarryId))
              FilledButton.icon(
                icon: const Icon(Icons.task_alt),
                label: const Text('Завершить'),
                onPressed: () => _run(context, cubit.complete, 'Паспорт завершён'),
              ),
            if (passport.status.canRevise && context.canManageBlastingOn(quarryId))
              OutlinedButton.icon(
                icon: const Icon(Icons.history_edu),
                label: const Text('Создать редакцию'),
                onPressed: () => _run(context, () => cubit.revise(), 'Новая редакция создана'),
              ),
            OutlinedButton.icon(
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Съемки'),
              onPressed: () => context.go(
                  '/quarries/$quarryId/passports/${passport.id}/captures'),
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.analytics_outlined),
              label: const Text('Отчёты'),
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
