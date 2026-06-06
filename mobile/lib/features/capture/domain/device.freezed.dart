// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'device.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

Device _$DeviceFromJson(Map<String, dynamic> json) {
  return _Device.fromJson(json);
}

/// @nodoc
mixin _$Device {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'serial_number')
  String get serialNumber => throw _privateConstructorUsedError;
  String get model => throw _privateConstructorUsedError;

  /// Serializes this Device to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Device
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DeviceCopyWith<Device> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DeviceCopyWith<$Res> {
  factory $DeviceCopyWith(Device value, $Res Function(Device) then) =
      _$DeviceCopyWithImpl<$Res, Device>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'serial_number') String serialNumber,
      String model});
}

/// @nodoc
class _$DeviceCopyWithImpl<$Res, $Val extends Device>
    implements $DeviceCopyWith<$Res> {
  _$DeviceCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Device
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? serialNumber = null,
    Object? model = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      serialNumber: null == serialNumber
          ? _value.serialNumber
          : serialNumber // ignore: cast_nullable_to_non_nullable
              as String,
      model: null == model
          ? _value.model
          : model // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DeviceImplCopyWith<$Res> implements $DeviceCopyWith<$Res> {
  factory _$$DeviceImplCopyWith(
          _$DeviceImpl value, $Res Function(_$DeviceImpl) then) =
      __$$DeviceImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'serial_number') String serialNumber,
      String model});
}

/// @nodoc
class __$$DeviceImplCopyWithImpl<$Res>
    extends _$DeviceCopyWithImpl<$Res, _$DeviceImpl>
    implements _$$DeviceImplCopyWith<$Res> {
  __$$DeviceImplCopyWithImpl(
      _$DeviceImpl _value, $Res Function(_$DeviceImpl) _then)
      : super(_value, _then);

  /// Create a copy of Device
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? serialNumber = null,
    Object? model = null,
  }) {
    return _then(_$DeviceImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      serialNumber: null == serialNumber
          ? _value.serialNumber
          : serialNumber // ignore: cast_nullable_to_non_nullable
              as String,
      model: null == model
          ? _value.model
          : model // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DeviceImpl implements _Device {
  const _$DeviceImpl(
      {required this.id,
      @JsonKey(name: 'serial_number') required this.serialNumber,
      required this.model});

  factory _$DeviceImpl.fromJson(Map<String, dynamic> json) =>
      _$$DeviceImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'serial_number')
  final String serialNumber;
  @override
  final String model;

  @override
  String toString() {
    return 'Device(id: $id, serialNumber: $serialNumber, model: $model)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DeviceImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.serialNumber, serialNumber) ||
                other.serialNumber == serialNumber) &&
            (identical(other.model, model) || other.model == model));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, serialNumber, model);

  /// Create a copy of Device
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DeviceImplCopyWith<_$DeviceImpl> get copyWith =>
      __$$DeviceImplCopyWithImpl<_$DeviceImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DeviceImplToJson(
      this,
    );
  }
}

abstract class _Device implements Device {
  const factory _Device(
      {required final String id,
      @JsonKey(name: 'serial_number') required final String serialNumber,
      required final String model}) = _$DeviceImpl;

  factory _Device.fromJson(Map<String, dynamic> json) = _$DeviceImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'serial_number')
  String get serialNumber;
  @override
  String get model;

  /// Create a copy of Device
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DeviceImplCopyWith<_$DeviceImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

DeviceCalibration _$DeviceCalibrationFromJson(Map<String, dynamic> json) {
  return _DeviceCalibration.fromJson(json);
}

/// @nodoc
mixin _$DeviceCalibration {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'device_id')
  String get deviceId => throw _privateConstructorUsedError;
  @JsonKey(name: 'baseline_mm')
  double get baselineMm => throw _privateConstructorUsedError;
  @JsonKey(name: 'image_width_px')
  int get imageWidthPx => throw _privateConstructorUsedError;
  @JsonKey(name: 'image_height_px')
  int get imageHeightPx => throw _privateConstructorUsedError;

  /// Serializes this DeviceCalibration to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of DeviceCalibration
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DeviceCalibrationCopyWith<DeviceCalibration> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DeviceCalibrationCopyWith<$Res> {
  factory $DeviceCalibrationCopyWith(
          DeviceCalibration value, $Res Function(DeviceCalibration) then) =
      _$DeviceCalibrationCopyWithImpl<$Res, DeviceCalibration>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'device_id') String deviceId,
      @JsonKey(name: 'baseline_mm') double baselineMm,
      @JsonKey(name: 'image_width_px') int imageWidthPx,
      @JsonKey(name: 'image_height_px') int imageHeightPx});
}

/// @nodoc
class _$DeviceCalibrationCopyWithImpl<$Res, $Val extends DeviceCalibration>
    implements $DeviceCalibrationCopyWith<$Res> {
  _$DeviceCalibrationCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DeviceCalibration
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? deviceId = null,
    Object? baselineMm = null,
    Object? imageWidthPx = null,
    Object? imageHeightPx = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      deviceId: null == deviceId
          ? _value.deviceId
          : deviceId // ignore: cast_nullable_to_non_nullable
              as String,
      baselineMm: null == baselineMm
          ? _value.baselineMm
          : baselineMm // ignore: cast_nullable_to_non_nullable
              as double,
      imageWidthPx: null == imageWidthPx
          ? _value.imageWidthPx
          : imageWidthPx // ignore: cast_nullable_to_non_nullable
              as int,
      imageHeightPx: null == imageHeightPx
          ? _value.imageHeightPx
          : imageHeightPx // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DeviceCalibrationImplCopyWith<$Res>
    implements $DeviceCalibrationCopyWith<$Res> {
  factory _$$DeviceCalibrationImplCopyWith(_$DeviceCalibrationImpl value,
          $Res Function(_$DeviceCalibrationImpl) then) =
      __$$DeviceCalibrationImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'device_id') String deviceId,
      @JsonKey(name: 'baseline_mm') double baselineMm,
      @JsonKey(name: 'image_width_px') int imageWidthPx,
      @JsonKey(name: 'image_height_px') int imageHeightPx});
}

/// @nodoc
class __$$DeviceCalibrationImplCopyWithImpl<$Res>
    extends _$DeviceCalibrationCopyWithImpl<$Res, _$DeviceCalibrationImpl>
    implements _$$DeviceCalibrationImplCopyWith<$Res> {
  __$$DeviceCalibrationImplCopyWithImpl(_$DeviceCalibrationImpl _value,
      $Res Function(_$DeviceCalibrationImpl) _then)
      : super(_value, _then);

  /// Create a copy of DeviceCalibration
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? deviceId = null,
    Object? baselineMm = null,
    Object? imageWidthPx = null,
    Object? imageHeightPx = null,
  }) {
    return _then(_$DeviceCalibrationImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      deviceId: null == deviceId
          ? _value.deviceId
          : deviceId // ignore: cast_nullable_to_non_nullable
              as String,
      baselineMm: null == baselineMm
          ? _value.baselineMm
          : baselineMm // ignore: cast_nullable_to_non_nullable
              as double,
      imageWidthPx: null == imageWidthPx
          ? _value.imageWidthPx
          : imageWidthPx // ignore: cast_nullable_to_non_nullable
              as int,
      imageHeightPx: null == imageHeightPx
          ? _value.imageHeightPx
          : imageHeightPx // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DeviceCalibrationImpl implements _DeviceCalibration {
  const _$DeviceCalibrationImpl(
      {required this.id,
      @JsonKey(name: 'device_id') required this.deviceId,
      @JsonKey(name: 'baseline_mm') required this.baselineMm,
      @JsonKey(name: 'image_width_px') required this.imageWidthPx,
      @JsonKey(name: 'image_height_px') required this.imageHeightPx});

  factory _$DeviceCalibrationImpl.fromJson(Map<String, dynamic> json) =>
      _$$DeviceCalibrationImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'device_id')
  final String deviceId;
  @override
  @JsonKey(name: 'baseline_mm')
  final double baselineMm;
  @override
  @JsonKey(name: 'image_width_px')
  final int imageWidthPx;
  @override
  @JsonKey(name: 'image_height_px')
  final int imageHeightPx;

  @override
  String toString() {
    return 'DeviceCalibration(id: $id, deviceId: $deviceId, baselineMm: $baselineMm, imageWidthPx: $imageWidthPx, imageHeightPx: $imageHeightPx)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DeviceCalibrationImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.deviceId, deviceId) ||
                other.deviceId == deviceId) &&
            (identical(other.baselineMm, baselineMm) ||
                other.baselineMm == baselineMm) &&
            (identical(other.imageWidthPx, imageWidthPx) ||
                other.imageWidthPx == imageWidthPx) &&
            (identical(other.imageHeightPx, imageHeightPx) ||
                other.imageHeightPx == imageHeightPx));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType, id, deviceId, baselineMm, imageWidthPx, imageHeightPx);

  /// Create a copy of DeviceCalibration
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DeviceCalibrationImplCopyWith<_$DeviceCalibrationImpl> get copyWith =>
      __$$DeviceCalibrationImplCopyWithImpl<_$DeviceCalibrationImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DeviceCalibrationImplToJson(
      this,
    );
  }
}

abstract class _DeviceCalibration implements DeviceCalibration {
  const factory _DeviceCalibration(
          {required final String id,
          @JsonKey(name: 'device_id') required final String deviceId,
          @JsonKey(name: 'baseline_mm') required final double baselineMm,
          @JsonKey(name: 'image_width_px') required final int imageWidthPx,
          @JsonKey(name: 'image_height_px') required final int imageHeightPx}) =
      _$DeviceCalibrationImpl;

  factory _DeviceCalibration.fromJson(Map<String, dynamic> json) =
      _$DeviceCalibrationImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'device_id')
  String get deviceId;
  @override
  @JsonKey(name: 'baseline_mm')
  double get baselineMm;
  @override
  @JsonKey(name: 'image_width_px')
  int get imageWidthPx;
  @override
  @JsonKey(name: 'image_height_px')
  int get imageHeightPx;

  /// Create a copy of DeviceCalibration
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DeviceCalibrationImplCopyWith<_$DeviceCalibrationImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
