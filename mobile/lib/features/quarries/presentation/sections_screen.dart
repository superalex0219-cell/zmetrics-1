import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_context.dart';
import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/sections_cubit.dart';
import '../domain/site_section.dart';

/// Sections (blocks) of a quarry, plus entry points into passports and capture.
class SectionsScreen extends StatelessWidget {
  const SectionsScreen({super.key, required this.quarryId});

  final String quarryId;

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Участки',
      actions: [
        TextButton.icon(
          onPressed: () => context.go('/quarries/$quarryId/reports'),
          icon: const Icon(Icons.analytics_outlined, color: Colors.white),
          label: const Text('Отчёты', style: TextStyle(color: Colors.white)),
        ),
        TextButton.icon(
          onPressed: () => context.go('/quarries/$quarryId/passports'),
          icon: const Icon(Icons.description, color: Colors.white),
          label: const Text('Паспорта', style: TextStyle(color: Colors.white)),
        ),
      ],
      // Creating a section requires blaster+ (backend enforces).
      floatingActionButton: context.canManageBlastingOn(quarryId)
          ? FloatingActionButton(
              onPressed: () => _showCreateDialog(context),
              child: const Icon(Icons.add),
            )
          : null,
      body: BlocBuilder<SectionsCubit, DataState<List<SiteSection>>>(
        builder: (context, state) => AsyncView<List<SiteSection>>(
          state: state,
          onRetry: () => context.read<SectionsCubit>().load(),
          onData: (context, sections) {
            if (sections.isEmpty) {
              return const Center(child: Text('Нет участков.'));
            }
            return ListView.separated(
              itemCount: sections.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final s = sections[i];
                return ListTile(
                  leading: CircleAvatar(child: Text(s.blockNumber ?? '–')),
                  title: Text(s.name),
                  subtitle: Text('Блок ${s.blockNumber ?? '—'}'),
                  trailing: IconButton(
                    tooltip: 'Capture',
                    icon: const Icon(Icons.camera_alt_outlined),
                    // Mock: treat the section id as a blast-event id for capture.
                    onPressed: () => context.go('/blast-events/${s.id}/captures'),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }

  Future<void> _showCreateDialog(BuildContext context) async {
    final cubit = context.read<SectionsCubit>();
    final nameCtrl = TextEditingController();
    final blockCtrl = TextEditingController();
    final messenger = ScaffoldMessenger.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Новый участок'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Название'),
            ),
            TextField(
              controller: blockCtrl,
              decoration: const InputDecoration(labelText: 'Номер блока'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Отмена'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Создать'),
          ),
        ],
      ),
    );
    if (ok != true || nameCtrl.text.trim().isEmpty) return;
    try {
      await cubit.createSection(
        name: nameCtrl.text.trim(),
        blockNumber: blockCtrl.text.trim().isEmpty ? null : blockCtrl.text.trim(),
      );
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Ошибка: $e')));
    }
  }
}
