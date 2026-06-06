import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/shared/widgets/mock_pipeline_badge.dart';

void main() {
  testWidgets('MockPipelineBadge shows the mandated synthetic-data warning',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: MockPipelineBadge())),
    );
    // SAFETY: exact wording required by rules/product-safety.md.
    expect(find.text('⚠ Mock pipeline — results are synthetic'), findsOneWidget);
  });
}
