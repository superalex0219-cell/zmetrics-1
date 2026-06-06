import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_context.dart';
import '../../../core/auth/auth_cubit.dart';
import '../../../core/dev/dev_seed_service.dart';
import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../../../shared/offline/sync_cubit.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/stat_card.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/quarries_cubit.dart';
import '../domain/quarry.dart';

class QuarriesScreen extends StatelessWidget {
  const QuarriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Карьеры',
      actions: [
        IconButton(
          tooltip: 'Загрузить демо-данные',
          icon: const Icon(Icons.science_outlined),
          onPressed: () => _seedDemo(context),
        ),
        IconButton(
          tooltip: 'Выйти',
          icon: const Icon(Icons.logout),
          onPressed: () => context.read<AuthCubit>().signOut(),
        ),
      ],
      // Creating a quarry requires admin (mobile-auth-notes §5). Backend is
      // authoritative and still returns 403 if the role check fails.
      floatingActionButton: context.isAdminAnywhere
          ? FloatingActionButton(
              onPressed: () => _showCreateDialog(context),
              child: const Icon(Icons.add),
            )
          : null,
      body: BlocBuilder<QuarriesCubit, DataState<List<Quarry>>>(
        builder: (context, state) => AsyncView<List<Quarry>>(
          state: state,
          onRetry: () => context.read<QuarriesCubit>().load(),
          onData: (context, quarries) {
            if (quarries.isEmpty) {
              return const Center(child: Text('Нет карьеров.'));
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                  child: Row(
                    children: [
                      Expanded(
                        child: StatCard(
                          icon: Icons.terrain,
                          label: 'Карьеры',
                          value: '${quarries.length}',
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: BlocBuilder<SyncCubit, SyncState>(
                          builder: (context, sync) => StatCard(
                            icon: sync.online
                                ? Icons.cloud_done
                                : Icons.cloud_off,
                            label: 'Подключение',
                            value: sync.online ? 'Онлайн' : 'Оффлайн',
                            valueColor: sync.online
                                ? const Color(0xFF0F766E)
                                : Colors.orange.shade800,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: ListView.separated(
                    itemCount: quarries.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      final q = quarries[i];
                      return ListTile(
                        leading: const Icon(Icons.terrain),
                        title: Text(q.name),
                        subtitle: q.latitude != null && q.longitude != null
                            ? Text('${q.latitude}, ${q.longitude}')
                            : null,
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.go('/quarries/${q.id}'),
                      );
                    },
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _seedDemo(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    final cubit = context.read<QuarriesCubit>();
    try {
      final result = await context.read<DevSeedService>().seed();
      await cubit.load();
      messenger.showSnackBar(SnackBar(
        content: const Text('Демо-данные загружены'),
        action: SnackBarAction(
          label: 'Открыть отчет',
          onPressed: () => router.go('/reports/${result.reportId}'),
        ),
      ));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Ошибка загрузки: ${friendlyError(e)}')));
    }
  }

  Future<void> _showCreateDialog(BuildContext context) async {
    final cubit = context.read<QuarriesCubit>();
    final controller = TextEditingController();
    final messenger = ScaffoldMessenger.of(context);
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Новый карьер'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Название'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Отмена'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Создать'),
          ),
        ],
      ),
    );
    if (name == null || name.isEmpty) return;
    try {
      await cubit.createQuarry(name: name);
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  }
}
