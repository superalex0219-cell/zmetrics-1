import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/mock_pipeline_badge.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/report_cubit.dart';
import '../domain/analysis_result.dart';
import '../domain/recommendation.dart';
import '../domain/report.dart';

class ReportScreen extends StatelessWidget {
  const ReportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Analysis report',
      body: BlocBuilder<ReportCubit, DataState<Report>>(
        builder: (context, state) => AsyncView<Report>(
          state: state,
          onRetry: () => context.read<ReportCubit>().load(),
          onData: (context, report) => _ReportBody(report: report),
        ),
      ),
    );
  }
}

class _ReportBody extends StatelessWidget {
  const _ReportBody({required this.report});
  final Report report;

  @override
  Widget build(BuildContext context) {
    final result = report.analysisResult;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // SAFETY: synthetic mock results must be labelled prominently.
        if (report.analysisMethod.isMock) const MockPipelineBadge(),
        if (report.summary != null) ...[
          Text(report.summary!),
          const SizedBox(height: 16),
        ],
        if (report.title != null)
          Text(report.title!, style: Theme.of(context).textTheme.titleLarge),
        Text('Method: ${report.analysisMethod.name}',
            style: Theme.of(context).textTheme.labelLarge),
        const Divider(height: 24),
        if (result != null)
          _ResultSection(result: result)
        else
          // Backend mode: ReportRead exposes only analysis_result_id and there
          // is no GET-result-by-id endpoint yet (TASK handoff GAP-1).
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text(
              'Granulometry metrics (P10/P50/P80) are not available from the '
              'backend yet — pending an analysis-result endpoint.',
              style: TextStyle(fontSize: 12),
            ),
          ),
        const SizedBox(height: 16),
        Text('Recommendations',
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        if (report.recommendations.isEmpty)
          const Text('No recommendations.')
        else
          ...report.recommendations.map((r) => _RecommendationCard(rec: r)),
      ],
    );
  }
}

class _ResultSection extends StatelessWidget {
  const _ResultSection({required this.result});
  final AnalysisResult result;

  @override
  Widget build(BuildContext context) {
    final conf = result.confidenceScore;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Granulometry (mm)',
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        // Full precision — scientific outputs must not be rounded
        // (rules/01-safety.md data integrity).
        _kv('P10', '${result.p10Mm} mm'),
        _kv('P50', '${result.p50Mm} mm'),
        _kv('P80', '${result.p80Mm} mm'),
        _kv('Rosin-Rammler n', '${result.rosinRammlerN ?? '—'}'),
        _kv('Rosin-Rammler xc', '${result.rosinRammlerXc ?? '—'} mm'),
        _kv('Oversize (>500mm)', '${result.oversizePercent ?? '—'} %'),
        _kv('Fines (<25mm)', '${result.finesPercent ?? '—'} %'),
        _kv('Confidence', conf == null ? '—' : conf.toStringAsFixed(4)),
        // SAFETY: confidence_score < 0.5 must trigger a warning
        // (rules/product-safety.md error handling).
        if (conf != null && conf < 0.5)
          _warning('⚠ Low confidence (<0.5): interpret with extreme caution.'),
        if (conf != null && conf >= 0.5 && conf < 0.8)
          _warning('Confidence < 0.8 — review the confidence notes.'),
        const SizedBox(height: 12),
        if (result.sizeDistribution.isNotEmpty) ...[
          Text('Cumulative passing',
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          Table(
            border: TableBorder.all(color: Colors.black12),
            children: [
              const TableRow(children: [
                _Cell('Size (mm)', header: true),
                _Cell('Passing (%)', header: true),
              ]),
              for (final bin in result.sizeDistribution)
                TableRow(children: [
                  _Cell('${bin.sizeMm}'),
                  _Cell('${bin.cumulativePassingPct}'),
                ]),
            ],
          ),
        ],
      ],
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          children: [
            Expanded(child: Text(k)),
            Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      );

  Widget _warning(String text) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(text, style: const TextStyle(color: Colors.red)),
      );
}

class _Cell extends StatelessWidget {
  const _Cell(this.text, {this.header = false});
  final String text;
  final bool header;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(6),
        child: Text(text,
            style: header ? const TextStyle(fontWeight: FontWeight.bold) : null),
      );
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.rec});
  final Recommendation rec;

  @override
  Widget build(BuildContext context) {
    final cubit = context.read<ReportCubit>();
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Chip(
                  label: Text(rec.status.label,
                      style: const TextStyle(fontSize: 11)),
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(rec.recommendationText),
            if (rec.confidenceNotes != null) ...[
              const SizedBox(height: 8),
              Text(rec.confidenceNotes!,
                  style: const TextStyle(
                      fontStyle: FontStyle.italic, color: Colors.orange)),
            ],
            if (rec.parameterSuggestions.isNotEmpty) ...[
              const SizedBox(height: 8),
              // SAFETY: reference-only. There is no action that writes these
              // into a passport (rules/product-safety.md).
              const Text('Parameter suggestions (reference only):',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              for (final e in rec.parameterSuggestions.entries)
                Text('• ${e.key}: ${e.value}'),
            ],
            const Divider(height: 20),
            // SAFETY: only human-driven transitions are offered. Once reviewed,
            // no further auto-changes (rules/product-safety.md).
            if (!rec.status.isReviewed)
              Wrap(
                spacing: 8,
                children: [
                  FilledButton(
                    onPressed: () => _review(
                        context, cubit, rec.id, RecommendationStatus.accepted),
                    child: const Text('Accept'),
                  ),
                  OutlinedButton(
                    onPressed: () => _review(
                        context, cubit, rec.id, RecommendationStatus.rejected),
                    child: const Text('Reject'),
                  ),
                  TextButton(
                    onPressed: () => _review(
                        context, cubit, rec.id, RecommendationStatus.reviewed),
                    child: const Text('Mark reviewed'),
                  ),
                ],
              )
            else
              Text('Reviewed — ${rec.status.label}',
                  style: const TextStyle(color: Colors.green)),
            const SizedBox(height: 8),
            ...rec.comments.map((c) => Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('💬 ${c.authorName}: ${c.body}',
                      style: const TextStyle(fontSize: 12)),
                )),
            TextButton.icon(
              icon: const Icon(Icons.add_comment, size: 16),
              label: const Text('Add comment'),
              onPressed: () => _addComment(context, cubit, rec.id),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _review(
    BuildContext context,
    ReportCubit cubit,
    String recId,
    RecommendationStatus decision,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await cubit.review(recId, decision);
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  }

  Future<void> _addComment(
    BuildContext context,
    ReportCubit cubit,
    String recId,
  ) async {
    final controller = TextEditingController();
    final messenger = ScaffoldMessenger.of(context);
    final body = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add comment'),
        content: TextField(controller: controller, autofocus: true),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Post'),
          ),
        ],
      ),
    );
    if (body == null || body.isEmpty) return;
    try {
      await cubit.addComment(recId, body);
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  }
}
