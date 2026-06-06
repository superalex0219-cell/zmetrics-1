import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/core/auth/auth_cubit.dart';
import 'package:zmetrics_mobile/core/auth/auth_repository.dart';
import 'package:zmetrics_mobile/features/passport/application/passport_detail_cubit.dart';
import 'package:zmetrics_mobile/features/passport/data/passport_repository.dart';
import 'package:zmetrics_mobile/features/passport/domain/passport_status.dart';
import 'package:zmetrics_mobile/features/quarries/application/quarries_cubit.dart';
import 'package:zmetrics_mobile/features/quarries/data/quarry_repository.dart';
import 'package:zmetrics_mobile/features/quarries/domain/quarry.dart';
import 'package:zmetrics_mobile/features/report/application/report_cubit.dart';
import 'package:zmetrics_mobile/features/report/data/report_repository.dart';
import 'package:zmetrics_mobile/features/report/domain/recommendation.dart';
import 'package:zmetrics_mobile/shared/bloc/data_state.dart';

void main() {
  test('QuarriesCubit.load emits DataLoaded with quarries', () async {
    final cubit = QuarriesCubit(MockQuarryRepository());
    await cubit.load();
    final state = cubit.state;
    expect(state, isA<DataLoaded<List<Quarry>>>());
    expect((state as DataLoaded<List<Quarry>>).value, isNotEmpty);
    await cubit.close();
  });

  test('PassportDetailCubit.submit transitions to SUBMITTED', () async {
    final cubit = PassportDetailCubit(MockPassportRepository(), 'q-granite', 'p-1');
    await cubit.load();
    await cubit.submit();
    final state = cubit.state as DataLoaded;
    expect(state.value.status, PassportStatus.submitted);
    await cubit.close();
  });

  test('ReportCubit.review applies an explicit decision', () async {
    final cubit = ReportCubit(MockReportRepository(), 'r-1');
    await cubit.load();
    await cubit.review('rec-1', RecommendationStatus.rejected);
    final report = (cubit.state as DataLoaded).value;
    expect(report.recommendations.single.status,
        RecommendationStatus.rejected);
    await cubit.close();
  });

  group('AuthCubit', () {
    test('restore with mock repo (no prior login) → Unauthenticated', () async {
      final cubit = AuthCubit(MockAuthRepository());
      await cubit.restore();
      expect(cubit.state, isA<Unauthenticated>());
      await cubit.close();
    });

    test('signIn → Authenticated', () async {
      final cubit = AuthCubit(MockAuthRepository());
      await cubit.signIn();
      expect(cubit.state, isA<Authenticated>());
      await cubit.close();
    });
  });
}
