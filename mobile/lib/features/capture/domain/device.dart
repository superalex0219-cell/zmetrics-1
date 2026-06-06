import 'package:freezed_annotation/freezed_annotation.dart';

part 'device.freezed.dart';
part 'device.g.dart';

/// A ZED 2 stereo camera registered in the system.
@freezed
class Device with _$Device {
  const factory Device({
    required String id,
    @JsonKey(name: 'serial_number') required String serialNumber,
    required String model,
  }) = _Device;

  factory Device.fromJson(Map<String, dynamic> json) => _$DeviceFromJson(json);
}

/// Stereo calibration set for a [Device].
@freezed
class DeviceCalibration with _$DeviceCalibration {
  const factory DeviceCalibration({
    required String id,
    @JsonKey(name: 'device_id') required String deviceId,
    @JsonKey(name: 'baseline_mm') required double baselineMm,
    @JsonKey(name: 'image_width_px') required int imageWidthPx,
    @JsonKey(name: 'image_height_px') required int imageHeightPx,
  }) = _DeviceCalibration;

  factory DeviceCalibration.fromJson(Map<String, dynamic> json) =>
      _$DeviceCalibrationFromJson(json);
}
