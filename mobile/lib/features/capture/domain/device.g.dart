// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$DeviceImpl _$$DeviceImplFromJson(Map<String, dynamic> json) => _$DeviceImpl(
      id: json['id'] as String,
      serialNumber: json['serial_number'] as String,
      model: json['model'] as String,
    );

Map<String, dynamic> _$$DeviceImplToJson(_$DeviceImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'serial_number': instance.serialNumber,
      'model': instance.model,
    };

_$DeviceCalibrationImpl _$$DeviceCalibrationImplFromJson(
        Map<String, dynamic> json) =>
    _$DeviceCalibrationImpl(
      id: json['id'] as String,
      deviceId: json['device_id'] as String,
      baselineMm: (json['baseline_mm'] as num).toDouble(),
      imageWidthPx: (json['image_width_px'] as num).toInt(),
      imageHeightPx: (json['image_height_px'] as num).toInt(),
    );

Map<String, dynamic> _$$DeviceCalibrationImplToJson(
        _$DeviceCalibrationImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'device_id': instance.deviceId,
      'baseline_mm': instance.baselineMm,
      'image_width_px': instance.imageWidthPx,
      'image_height_px': instance.imageHeightPx,
    };
