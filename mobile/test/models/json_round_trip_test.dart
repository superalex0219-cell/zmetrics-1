import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/features/capture/domain/analysis_job.dart';
import 'package:zmetrics_mobile/features/capture/domain/capture_session.dart';
import 'package:zmetrics_mobile/features/passport/domain/blast_passport.dart';
import 'package:zmetrics_mobile/features/passport/domain/passport_status.dart';
import 'package:zmetrics_mobile/features/report/domain/analysis_result.dart';
import 'package:zmetrics_mobile/features/report/domain/recommendation.dart';
import 'package:zmetrics_mobile/features/report/domain/report.dart';

void main() {
  group('BlastPassport JSON', () {
    test('parses snake_case + enum and round-trips', () {
      final json = {
        'id': 'p-1',
        'site_section_id': 'sec-a1',
        'status': 'submitted',
        'revision_number': 2,
        'explosive_type': 'ANFO',
        'total_explosive_kg': 1850.5,
        'hole_diameter_mm': 115.0,
        'target_p80_mm': 350.0,
      };
      final p = BlastPassport.fromJson(json);
      expect(p.status, PassportStatus.submitted);
      expect(p.siteSectionId, 'sec-a1');
      expect(p.revisionNumber, 2);
      expect(p.totalExplosiveKg, 1850.5);

      final out = p.toJson();
      expect(out['site_section_id'], 'sec-a1');
      expect(out['status'], 'submitted');
      expect(out['target_p80_mm'], 350.0);
    });

    test('revision_number defaults to 1 when absent', () {
      final p = BlastPassport.fromJson({
        'id': 'p-x',
        'site_section_id': 's',
        'status': 'draft',
      });
      expect(p.revisionNumber, 1);
    });
  });

  test('Recommendation maps requires_human_review enum value', () {
    final r = Recommendation.fromJson({
      'id': 'rec-1',
      'report_id': 'r-1',
      'status': 'requires_human_review',
      'recommendation_text': 'text',
      'parameter_suggestions': {'burden_m': 3.0},
    });
    expect(r.status, RecommendationStatus.requiresHumanReview);
    expect(r.status.isReviewed, isFalse);
    expect(r.parameterSuggestions['burden_m'], 3.0);
  });

  test('AnalysisResult preserves full P-value precision', () {
    final ar = AnalysisResult.fromJson({
      'id': 'ar-1',
      'p10_mm': 42.137,
      'p50_mm': 187.502,
      'p80_mm': 318.964,
      'size_distribution': [
        {'size_mm': 25.0, 'cumulative_passing_pct': 11.205},
      ],
    });
    expect(ar.p50Mm, 187.502);
    expect(ar.sizeDistribution.single.cumulativePassingPct, 11.205);
    expect(ar.toJson()['p80_mm'], 318.964);
  });

  test('Report parses analysis_method enum', () {
    final rep = Report.fromJson({
      'id': 'r-1',
      'analysis_method': 'mock',
    });
    expect(rep.analysisMethod, AnalysisMethod.mock);
    expect(rep.analysisMethod.isMock, isTrue);
  });

  test('AnalysisJob terminal/status mapping', () {
    final j = AnalysisJob.fromJson({
      'id': 'j-1',
      'capture_session_id': 'c-1',
      'status': 'failed',
      'error_message': 'pipeline error',
    });
    expect(j.status, AnalysisJobStatus.failed);
    expect(j.status.isTerminal, isTrue);
    expect(j.errorMessage, 'pipeline error');
  });

  test('CaptureSession synced flag is local-only (not serialised)', () {
    const s = CaptureSession(
      id: 'c-1',
      blastEventId: 'e-1',
      synced: false,
    );
    expect(s.toJson().containsKey('synced'), isFalse);
  });
}
