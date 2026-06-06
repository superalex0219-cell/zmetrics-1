import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/features/capture/data/capture_repository.dart';
import 'package:zmetrics_mobile/features/capture/domain/capture_session.dart';
import 'package:zmetrics_mobile/features/passport/data/passport_repository.dart';
import 'package:zmetrics_mobile/features/passport/domain/blast_passport.dart';
import 'package:zmetrics_mobile/features/passport/domain/passport_status.dart';
import 'package:zmetrics_mobile/features/quarries/data/quarry_repository.dart';
import 'package:zmetrics_mobile/features/report/data/report_repository.dart';
import 'package:zmetrics_mobile/features/report/domain/recommendation.dart';
import 'package:zmetrics_mobile/shared/offline/sync_manager.dart';

void main() {
  group('MockQuarryRepository', () {
    test('lists seeded quarries and sections; create appends', () async {
      final repo = MockQuarryRepository();
      expect((await repo.listQuarries()).length, 2);
      expect((await repo.listSections('q-granite')).length, 2);

      await repo.createQuarry(name: 'New');
      expect((await repo.listQuarries()).length, 3);

      await repo.createSection('q-granite', name: 'S3', blockNumber: 'A3');
      expect((await repo.listSections('q-granite')).length, 3);
    });
  });

  group('MockPassportRepository (state machine)', () {
    test('create starts in DRAFT', () async {
      final repo = MockPassportRepository();
      final p = await repo.createPassport(
        'q-granite',
        const NewBlastPassport(siteSectionId: 'sec-a1', explosiveType: 'ANFO'),
      );
      expect(p.status, PassportStatus.draft);
      expect(p.revisionNumber, 1);
    });

    test('submit then approve advances DRAFT → SUBMITTED → APPROVED', () async {
      final repo = MockPassportRepository();
      var p = await repo.submit('q-granite', 'p-1');
      expect(p.status, PassportStatus.submitted);
      p = await repo.approve('q-granite', 'p-1');
      expect(p.status, PassportStatus.approved);
    });

    test('complete transitions to COMPLETED', () async {
      final repo = MockPassportRepository();
      final p = await repo.complete('q-granite', 'p-1');
      expect(p.status, PassportStatus.completed);
    });

    test('revise supersedes the old record and creates a new DRAFT', () async {
      final repo = MockPassportRepository();
      final next = await repo.revise('q-granite', 'p-2'); // p-2 is APPROVED
      expect(next.status, PassportStatus.draft);
      expect(next.revisionNumber, 3);
      final all = await repo.listPassports('q-granite');
      final old = all.firstWhere((p) => p.id == 'p-2');
      expect(old.status, PassportStatus.superseded);
      expect(old.supersededById, next.id);
    });
  });

  group('MockReportRepository (SAFETY)', () {
    test('seeded report is a labelled mock with a review-required rec',
        () async {
      final repo = MockReportRepository();
      final report = await repo.getReport('r-1');
      expect(report.analysisMethod.isMock, isTrue);
      expect(report.summary, contains('Mock pipeline'));

      final rec = report.recommendations.single;
      // The hard safety invariant: created recommendations require human review.
      expect(rec.status, RecommendationStatus.requiresHumanReview);
    });

    test('listReports returns the seeded mock report', () async {
      final repo = MockReportRepository();
      final reports = await repo.listReports('q-granite');
      expect(reports, hasLength(1));
      expect(reports.single.analysisMethod.isMock, isTrue);
    });

    test('review requires an explicit decision and persists it', () async {
      final repo = MockReportRepository();
      final updated = await repo.reviewRecommendation(
        'r-1',
        'rec-1',
        RecommendationStatus.accepted,
      );
      expect(updated.status, RecommendationStatus.accepted);
      // Reflected on reload.
      final report = await repo.getReport('r-1');
      expect(report.recommendations.single.status,
          RecommendationStatus.accepted);
    });
  });

  group('MockCaptureRepository (offline-first)', () {
    test('createSession enqueues to SyncManager and is unsynced', () async {
      final sync = InMemorySyncManager();
      final repo = MockCaptureRepository(sync);
      final CaptureSession s = await repo.createCaptureSession(
        const NewCaptureSession(blastEventId: 'e-1'),
      );
      expect(s.synced, isFalse);
      expect(await sync.pendingCount(), 1);
      final queued = (await sync.getPendingUploads()).single;
      expect(queued.operationType, kOpCreateCaptureSession);
      expect(queued.payload['blast_event_id'], 'e-1');
    });
  });
}
