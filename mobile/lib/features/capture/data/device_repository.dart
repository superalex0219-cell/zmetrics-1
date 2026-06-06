import 'package:dio/dio.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/paginated.dart';
import '../domain/device.dart';

abstract class DeviceRepository {
  Future<List<Device>> listDevices();
  Future<List<DeviceCalibration>> listCalibrations(String deviceId);
}

class MockDeviceRepository implements DeviceRepository {
  static final _device = Device(
    id: 'mock-device-001',
    serialNumber: 'DEMO-ZED2-0001',
    model: 'ZED 2',
  );
  static final _cal = DeviceCalibration(
    id: 'mock-cal-001',
    deviceId: 'mock-device-001',
    baselineMm: 120,
    imageWidthPx: 1280,
    imageHeightPx: 720,
  );

  @override
  Future<List<Device>> listDevices() async => [_device];

  @override
  Future<List<DeviceCalibration>> listCalibrations(String deviceId) async =>
      [_cal];
}

class RemoteDeviceRepository implements DeviceRepository {
  RemoteDeviceRepository(this._dio);

  final Dio _dio;

  @override
  Future<List<Device>> listDevices() async {
    try {
      final res = await _dio.get('/api/v1/devices');
      return Paginated<Device>.fromJson(
        res.data as Map<String, dynamic>,
        Device.fromJson,
      ).items;
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<List<DeviceCalibration>> listCalibrations(String deviceId) async {
    try {
      final res = await _dio.get('/api/v1/devices/$deviceId/calibrations');
      return Paginated<DeviceCalibration>.fromJson(
        res.data as Map<String, dynamic>,
        DeviceCalibration.fromJson,
      ).items;
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }
}
