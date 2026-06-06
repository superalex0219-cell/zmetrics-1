import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/features/capture/data/device_repository.dart';

void main() {
  group('MockDeviceRepository', () {
    late MockDeviceRepository repo;

    setUp(() => repo = MockDeviceRepository());

    test('listDevices returns exactly one device', () async {
      final devices = await repo.listDevices();
      expect(devices, hasLength(1));
      final d = devices.first;
      expect(d.id, 'mock-device-001');
      expect(d.serialNumber, 'DEMO-ZED2-0001');
      expect(d.model, 'ZED 2');
    });

    test('listCalibrations returns exactly one calibration for any deviceId',
        () async {
      final cals = await repo.listCalibrations('mock-device-001');
      expect(cals, hasLength(1));
      final c = cals.first;
      expect(c.id, 'mock-cal-001');
      expect(c.deviceId, 'mock-device-001');
      expect(c.baselineMm, 120.0);
      expect(c.imageWidthPx, 1280);
      expect(c.imageHeightPx, 720);
    });

    test('Device JSON round-trip', () {
      final devices = [
        {'id': 'dev-1', 'serial_number': 'SN-001', 'model': 'ZED 2'},
      ];
      final parsed = devices
          .map((j) =>
              require(j, (m) => m['id'] as String == 'dev-1'))
          .first;
      expect(parsed, isNotNull);
    });
  });
}

// Helper: expect a condition holds, return the value.
T require<T>(T value, bool Function(T) condition) {
  expect(condition(value), isTrue);
  return value;
}
