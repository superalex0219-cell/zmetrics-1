import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/core/network/json_list.dart';
import 'package:zmetrics_mobile/features/quarries/domain/quarry.dart';
import 'package:zmetrics_mobile/features/report/domain/recommendation.dart';
import 'package:zmetrics_mobile/features/report/domain/report.dart';

/// Guards alignment with the *implemented* backend response shapes
/// (see docs/handoffs/TASK-backend-mobile-integration.md §5).
void main() {
  group('parseJsonList', () {
    test('parses a bare JSON array (the backend list shape)', () {
      final out = parseJsonList(
        [
          {'id': 'a', 'name': 'Demo Quarry'},
          {'id': 'b', 'name': 'Other'},
        ],
        Quarry.fromJson,
      );
      expect(out, hasLength(2));
      expect(out.first.name, 'Demo Quarry');
    });

    test('also tolerates a {items:[...]} envelope', () {
      final out = parseJsonList(
        {
          'items': [
            {'id': 'a', 'name': 'Q'}
          ],
          'total': 1,
        },
        Quarry.fromJson,
      );
      expect(out.single.id, 'a');
    });

    test('returns empty on unexpected shape', () {
      expect(parseJsonList(null, Quarry.fromJson), isEmpty);
    });
  });

  test('ReportRead without analysis_method defaults to mock (fail-safe badge)', () {
    // Absent field → .mock so the warning badge is shown rather than hidden.
    final r = Report.fromJson({
      'id': 'r-1',
      'analysis_result_id': 'ar-1',
      'title': 'Granulometry report',
    });
    expect(r.analysisMethod, AnalysisMethod.mock);
    expect(r.analysisMethod.isMock, isTrue);
    expect(r.analysisResultId, 'ar-1');
    expect(r.title, 'Granulometry report');
  });

  test('RecommendationRead with null parameter_suggestions parses to {}', () {
    final rec = Recommendation.fromJson({
      'id': 'rec-1',
      'report_id': 'r-1',
      'status': 'requires_human_review',
      'recommendation_text': 'review me',
      'parameter_suggestions': null,
    });
    expect(rec.parameterSuggestions, isEmpty);
    expect(rec.comments, isEmpty);
    expect(rec.status, RecommendationStatus.requiresHumanReview);
  });
}
