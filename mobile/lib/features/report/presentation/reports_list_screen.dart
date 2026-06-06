import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/reports_list_cubit.dart';
import '../domain/report.dart';

/// Reports generated for a quarry (the worker creates one per completed job).
class ReportsListScreen extends StatelessWidget {
  const ReportsListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Reports',
      body: BlocBuilder<ReportsListCubit, DataState<List<Report>>>(
        builder: (context, state) => AsyncView<List<Report>>(
          state: state,
          onRetry: () => context.read<ReportsListCubit>().load(),
          onData: (context, reports) {
            if (reports.isEmpty) {
              return const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No reports yet. Reports are generated automatically after '
                    'an analysis job completes.',
                    textAlign: TextAlign.center,
                  ),
                ),
              );
            }
            return ListView.separated(
              itemCount: reports.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final r = reports[i];
                return ListTile(
                  leading: Icon(
                    r.analysisMethod.isMock
                        ? Icons.science_outlined
                        : Icons.analytics_outlined,
                    color: r.analysisMethod.isMock ? Colors.amber.shade800 : null,
                  ),
                  title: Text(r.title ?? 'Report ${r.id.substring(0, 8)}…'),
                  subtitle: Text(r.analysisMethod.isMock
                      ? 'Mock pipeline (synthetic)'
                      : r.analysisMethod.name),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.go('/reports/${r.id}'),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
