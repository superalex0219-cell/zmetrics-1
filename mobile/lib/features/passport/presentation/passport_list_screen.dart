import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_context.dart';
import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/passport_list_cubit.dart';
import '../domain/blast_passport.dart';
import '../domain/passport_status.dart';

class PassportListScreen extends StatelessWidget {
  const PassportListScreen({super.key, required this.quarryId});

  final String quarryId;

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Passports (БВР)',
      // Only blaster+ may create passports (backend enforces; this hides the
      // dead-end for everyone else).
      floatingActionButton: context.canManageBlastingOn(quarryId)
          ? FloatingActionButton.extended(
              onPressed: () => context.go('/quarries/$quarryId/passports/new'),
              icon: const Icon(Icons.add),
              label: const Text('New passport'),
            )
          : null,
      body: BlocBuilder<PassportListCubit, DataState<List<BlastPassport>>>(
        builder: (context, state) => AsyncView<List<BlastPassport>>(
          state: state,
          onRetry: () => context.read<PassportListCubit>().load(),
          onData: (context, passports) {
            if (passports.isEmpty) {
              return const Center(child: Text('No passports yet.'));
            }
            return ListView.separated(
              itemCount: passports.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final p = passports[i];
                return ListTile(
                  leading: const Icon(Icons.description_outlined),
                  title: Text('${p.explosiveType ?? 'Passport'} · rev ${p.revisionNumber}'),
                  subtitle: Text('Target P80: ${p.targetP80Mm ?? '—'} mm'),
                  trailing: _StatusChip(status: p.status),
                  onTap: () =>
                      context.go('/quarries/$quarryId/passports/${p.id}'),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});
  final PassportStatus status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      PassportStatus.draft => Colors.grey,
      PassportStatus.submitted => Colors.orange,
      PassportStatus.approved => Colors.green,
      PassportStatus.active => Colors.blue,
      PassportStatus.completed => Colors.teal,
      PassportStatus.cancelled => Colors.red,
      PassportStatus.superseded => Colors.brown,
    };
    return Chip(
      label: Text(status.label, style: const TextStyle(fontSize: 11)),
      backgroundColor: color.withValues(alpha: 0.15),
      side: BorderSide(color: color),
      visualDensity: VisualDensity.compact,
    );
  }
}
