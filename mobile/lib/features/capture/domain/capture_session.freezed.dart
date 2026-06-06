// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'capture_session.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

CaptureSession _$CaptureSessionFromJson(Map<String, dynamic> json) {
  return _CaptureSession.fromJson(json);
}

/// @nodoc
mixin _$CaptureSession {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'blast_event_id')
  String get blastEventId => throw _privateConstructorUsedError;
  @JsonKey(name: 'device_id')
  String? get deviceId => throw _privateConstructorUsedError;
  @JsonKey(name: 'calibration_id')
  String? get calibrationId => throw _privateConstructorUsedError;
  @JsonKey(name: 'frame_count')
  int get frameCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  DateTime? get createdAt => throw _privateConstructorUsedError;

  /// Local-only flag: false while the create op is still in the offline
  /// queue, true once the backend has acknowledged it.
  @JsonKey(includeToJson: false, includeFromJson: false)
  bool get synced => throw _privateConstructorUsedError;

  /// Serializes this CaptureSession to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CaptureSessionCopyWith<CaptureSession> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CaptureSessionCopyWith<$Res> {
  factory $CaptureSessionCopyWith(
          CaptureSession value, $Res Function(CaptureSession) then) =
      _$CaptureSessionCopyWithImpl<$Res, CaptureSession>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'blast_event_id') String blastEventId,
      @JsonKey(name: 'device_id') String? deviceId,
      @JsonKey(name: 'calibration_id') String? calibrationId,
      @JsonKey(name: 'frame_count') int frameCount,
      @JsonKey(name: 'created_at') DateTime? createdAt,
      @JsonKey(includeToJson: false, includeFromJson: false) bool synced});
}

/// @nodoc
class _$CaptureSessionCopyWithImpl<$Res, $Val extends CaptureSession>
    implements $CaptureSessionCopyWith<$Res> {
  _$CaptureSessionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? blastEventId = null,
    Object? deviceId = freezed,
    Object? calibrationId = freezed,
    Object? frameCount = null,
    Object? createdAt = freezed,
    Object? synced = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      blastEventId: null == blastEventId
          ? _value.blastEventId
          : blastEventId // ignore: cast_nullable_to_non_nullable
              as String,
      deviceId: freezed == deviceId
          ? _value.deviceId
          : deviceId // ignore: cast_nullable_to_non_nullable
              as String?,
      calibrationId: freezed == calibrationId
          ? _value.calibrationId
          : calibrationId // ignore: cast_nullable_to_non_nullable
              as String?,
      frameCount: null == frameCount
          ? _value.frameCount
          : frameCount // ignore: cast_nullable_to_non_nullable
              as int,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      synced: null == synced
          ? _value.synced
          : synced // ignore: cast_nullable_to_non_nullable
              as bool,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CaptureSessionImplCopyWith<$Res>
    implements $CaptureSessionCopyWith<$Res> {
  factory _$$CaptureSessionImplCopyWith(_$CaptureSessionImpl value,
          $Res Function(_$CaptureSessionImpl) then) =
      __$$CaptureSessionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'blast_event_id') String blastEventId,
      @JsonKey(name: 'device_id') String? deviceId,
      @JsonKey(name: 'calibration_id') String? calibrationId,
      @JsonKey(name: 'frame_count') int frameCount,
      @JsonKey(name: 'created_at') DateTime? createdAt,
      @JsonKey(includeToJson: false, includeFromJson: false) bool synced});
}

/// @nodoc
class __$$CaptureSessionImplCopyWithImpl<$Res>
    extends _$CaptureSessionCopyWithImpl<$Res, _$CaptureSessionImpl>
    implements _$$CaptureSessionImplCopyWith<$Res> {
  __$$CaptureSessionImplCopyWithImpl(
      _$CaptureSessionImpl _value, $Res Function(_$CaptureSessionImpl) _then)
      : super(_value, _then);

  /// Create a copy of CaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? blastEventId = null,
    Object? deviceId = freezed,
    Object? calibrationId = freezed,
    Object? frameCount = null,
    Object? createdAt = freezed,
    Object? synced = null,
  }) {
    return _then(_$CaptureSessionImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      blastEventId: null == blastEventId
          ? _value.blastEventId
          : blastEventId // ignore: cast_nullable_to_non_nullable
              as String,
      deviceId: freezed == deviceId
          ? _value.deviceId
          : deviceId // ignore: cast_nullable_to_non_nullable
              as String?,
      calibrationId: freezed == calibrationId
          ? _value.calibrationId
          : calibrationId // ignore: cast_nullable_to_non_nullable
              as String?,
      frameCount: null == frameCount
          ? _value.frameCount
          : frameCount // ignore: cast_nullable_to_non_nullable
              as int,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      synced: null == synced
          ? _value.synced
          : synced // ignore: cast_nullable_to_non_nullable
              as bool,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CaptureSessionImpl implements _CaptureSession {
  const _$CaptureSessionImpl(
      {required this.id,
      @JsonKey(name: 'blast_event_id') required this.blastEventId,
      @JsonKey(name: 'device_id') this.deviceId,
      @JsonKey(name: 'calibration_id') this.calibrationId,
      @JsonKey(name: 'frame_count') this.frameCount = 0,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(includeToJson: false, includeFromJson: false)
      this.synced = true});

  factory _$CaptureSessionImpl.fromJson(Map<String, dynamic> json) =>
      _$$CaptureSessionImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'blast_event_id')
  final String blastEventId;
  @override
  @JsonKey(name: 'device_id')
  final String? deviceId;
  @override
  @JsonKey(name: 'calibration_id')
  final String? calibrationId;
  @override
  @JsonKey(name: 'frame_count')
  final int frameCount;
  @override
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  /// Local-only flag: false while the create op is still in the offline
  /// queue, true once the backend has acknowledged it.
  @override
  @JsonKey(includeToJson: false, includeFromJson: false)
  final bool synced;

  @override
  String toString() {
    return 'CaptureSession(id: $id, blastEventId: $blastEventId, deviceId: $deviceId, calibrationId: $calibrationId, frameCount: $frameCount, createdAt: $createdAt, synced: $synced)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CaptureSessionImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.blastEventId, blastEventId) ||
                other.blastEventId == blastEventId) &&
            (identical(other.deviceId, deviceId) ||
                other.deviceId == deviceId) &&
            (identical(other.calibrationId, calibrationId) ||
                other.calibrationId == calibrationId) &&
            (identical(other.frameCount, frameCount) ||
                other.frameCount == frameCount) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.synced, synced) || other.synced == synced));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, blastEventId, deviceId,
      calibrationId, frameCount, createdAt, synced);

  /// Create a copy of CaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CaptureSessionImplCopyWith<_$CaptureSessionImpl> get copyWith =>
      __$$CaptureSessionImplCopyWithImpl<_$CaptureSessionImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CaptureSessionImplToJson(
      this,
    );
  }
}

abstract class _CaptureSession implements CaptureSession {
  const factory _CaptureSession(
      {required final String id,
      @JsonKey(name: 'blast_event_id') required final String blastEventId,
      @JsonKey(name: 'device_id') final String? deviceId,
      @JsonKey(name: 'calibration_id') final String? calibrationId,
      @JsonKey(name: 'frame_count') final int frameCount,
      @JsonKey(name: 'created_at') final DateTime? createdAt,
      @JsonKey(includeToJson: false, includeFromJson: false)
      final bool synced}) = _$CaptureSessionImpl;

  factory _CaptureSession.fromJson(Map<String, dynamic> json) =
      _$CaptureSessionImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'blast_event_id')
  String get blastEventId;
  @override
  @JsonKey(name: 'device_id')
  String? get deviceId;
  @override
  @JsonKey(name: 'calibration_id')
  String? get calibrationId;
  @override
  @JsonKey(name: 'frame_count')
  int get frameCount;
  @override
  @JsonKey(name: 'created_at')
  DateTime? get createdAt;

  /// Local-only flag: false while the create op is still in the offline
  /// queue, true once the backend has acknowledged it.
  @override
  @JsonKey(includeToJson: false, includeFromJson: false)
  bool get synced;

  /// Create a copy of CaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CaptureSessionImplCopyWith<_$CaptureSessionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

NewCaptureSession _$NewCaptureSessionFromJson(Map<String, dynamic> json) {
  return _NewCaptureSession.fromJson(json);
}

/// @nodoc
mixin _$NewCaptureSession {
  @JsonKey(name: 'blast_event_id')
  String get blastEventId => throw _privateConstructorUsedError;
  @JsonKey(name: 'quarry_id')
  String get quarryId => throw _privateConstructorUsedError;
  @JsonKey(name: 'passport_id')
  String get passportId => throw _privateConstructorUsedError;
  @JsonKey(name: 'device_id')
  String get deviceId => throw _privateConstructorUsedError;
  @JsonKey(name: 'calibration_id')
  String get calibrationId => throw _privateConstructorUsedError;
  @JsonKey(name: 'capture_datetime')
  String get captureDateTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'frame_count')
  int get frameCount => throw _privateConstructorUsedError;

  /// Serializes this NewCaptureSession to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of NewCaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $NewCaptureSessionCopyWith<NewCaptureSession> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $NewCaptureSessionCopyWith<$Res> {
  factory $NewCaptureSessionCopyWith(
          NewCaptureSession value, $Res Function(NewCaptureSession) then) =
      _$NewCaptureSessionCopyWithImpl<$Res, NewCaptureSession>;
  @useResult
  $Res call(
      {@JsonKey(name: 'blast_event_id') String blastEventId,
      @JsonKey(name: 'quarry_id') String quarryId,
      @JsonKey(name: 'passport_id') String passportId,
      @JsonKey(name: 'device_id') String deviceId,
      @JsonKey(name: 'calibration_id') String calibrationId,
      @JsonKey(name: 'capture_datetime') String captureDateTime,
      @JsonKey(name: 'frame_count') int frameCount});
}

/// @nodoc
class _$NewCaptureSessionCopyWithImpl<$Res, $Val extends NewCaptureSession>
    implements $NewCaptureSessionCopyWith<$Res> {
  _$NewCaptureSessionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of NewCaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? blastEventId = null,
    Object? quarryId = null,
    Object? passportId = null,
    Object? deviceId = null,
    Object? calibrationId = null,
    Object? captureDateTime = null,
    Object? frameCount = null,
  }) {
    return _then(_value.copyWith(
      blastEventId: null == blastEventId
          ? _value.blastEventId
          : blastEventId // ignore: cast_nullable_to_non_nullable
              as String,
      quarryId: null == quarryId
          ? _value.quarryId
          : quarryId // ignore: cast_nullable_to_non_nullable
              as String,
      passportId: null == passportId
          ? _value.passportId
          : passportId // ignore: cast_nullable_to_non_nullable
              as String,
      deviceId: null == deviceId
          ? _value.deviceId
          : deviceId // ignore: cast_nullable_to_non_nullable
              as String,
      calibrationId: null == calibrationId
          ? _value.calibrationId
          : calibrationId // ignore: cast_nullable_to_non_nullable
              as String,
      captureDateTime: null == captureDateTime
          ? _value.captureDateTime
          : captureDateTime // ignore: cast_nullable_to_non_nullable
              as String,
      frameCount: null == frameCount
          ? _value.frameCount
          : frameCount // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$NewCaptureSessionImplCopyWith<$Res>
    implements $NewCaptureSessionCopyWith<$Res> {
  factory _$$NewCaptureSessionImplCopyWith(_$NewCaptureSessionImpl value,
          $Res Function(_$NewCaptureSessionImpl) then) =
      __$$NewCaptureSessionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'blast_event_id') String blastEventId,
      @JsonKey(name: 'quarry_id') String quarryId,
      @JsonKey(name: 'passport_id') String passportId,
      @JsonKey(name: 'device_id') String deviceId,
      @JsonKey(name: 'calibration_id') String calibrationId,
      @JsonKey(name: 'capture_datetime') String captureDateTime,
      @JsonKey(name: 'frame_count') int frameCount});
}

/// @nodoc
class __$$NewCaptureSessionImplCopyWithImpl<$Res>
    extends _$NewCaptureSessionCopyWithImpl<$Res, _$NewCaptureSessionImpl>
    implements _$$NewCaptureSessionImplCopyWith<$Res> {
  __$$NewCaptureSessionImplCopyWithImpl(_$NewCaptureSessionImpl _value,
      $Res Function(_$NewCaptureSessionImpl) _then)
      : super(_value, _then);

  /// Create a copy of NewCaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? blastEventId = null,
    Object? quarryId = null,
    Object? passportId = null,
    Object? deviceId = null,
    Object? calibrationId = null,
    Object? captureDateTime = null,
    Object? frameCount = null,
  }) {
    return _then(_$NewCaptureSessionImpl(
      blastEventId: null == blastEventId
          ? _value.blastEventId
          : blastEventId // ignore: cast_nullable_to_non_nullable
              as String,
      quarryId: null == quarryId
          ? _value.quarryId
          : quarryId // ignore: cast_nullable_to_non_nullable
              as String,
      passportId: null == passportId
          ? _value.passportId
          : passportId // ignore: cast_nullable_to_non_nullable
              as String,
      deviceId: null == deviceId
          ? _value.deviceId
          : deviceId // ignore: cast_nullable_to_non_nullable
              as String,
      calibrationId: null == calibrationId
          ? _value.calibrationId
          : calibrationId // ignore: cast_nullable_to_non_nullable
              as String,
      captureDateTime: null == captureDateTime
          ? _value.captureDateTime
          : captureDateTime // ignore: cast_nullable_to_non_nullable
              as String,
      frameCount: null == frameCount
          ? _value.frameCount
          : frameCount // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$NewCaptureSessionImpl implements _NewCaptureSession {
  const _$NewCaptureSessionImpl(
      {@JsonKey(name: 'blast_event_id') required this.blastEventId,
      @JsonKey(name: 'quarry_id') required this.quarryId,
      @JsonKey(name: 'passport_id') required this.passportId,
      @JsonKey(name: 'device_id') required this.deviceId,
      @JsonKey(name: 'calibration_id') required this.calibrationId,
      @JsonKey(name: 'capture_datetime') required this.captureDateTime,
      @JsonKey(name: 'frame_count') this.frameCount = 0});

  factory _$NewCaptureSessionImpl.fromJson(Map<String, dynamic> json) =>
      _$$NewCaptureSessionImplFromJson(json);

  @override
  @JsonKey(name: 'blast_event_id')
  final String blastEventId;
  @override
  @JsonKey(name: 'quarry_id')
  final String quarryId;
  @override
  @JsonKey(name: 'passport_id')
  final String passportId;
  @override
  @JsonKey(name: 'device_id')
  final String deviceId;
  @override
  @JsonKey(name: 'calibration_id')
  final String calibrationId;
  @override
  @JsonKey(name: 'capture_datetime')
  final String captureDateTime;
  @override
  @JsonKey(name: 'frame_count')
  final int frameCount;

  @override
  String toString() {
    return 'NewCaptureSession(blastEventId: $blastEventId, quarryId: $quarryId, passportId: $passportId, deviceId: $deviceId, calibrationId: $calibrationId, captureDateTime: $captureDateTime, frameCount: $frameCount)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$NewCaptureSessionImpl &&
            (identical(other.blastEventId, blastEventId) ||
                other.blastEventId == blastEventId) &&
            (identical(other.quarryId, quarryId) ||
                other.quarryId == quarryId) &&
            (identical(other.passportId, passportId) ||
                other.passportId == passportId) &&
            (identical(other.deviceId, deviceId) ||
                other.deviceId == deviceId) &&
            (identical(other.calibrationId, calibrationId) ||
                other.calibrationId == calibrationId) &&
            (identical(other.captureDateTime, captureDateTime) ||
                other.captureDateTime == captureDateTime) &&
            (identical(other.frameCount, frameCount) ||
                other.frameCount == frameCount));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, blastEventId, quarryId,
      passportId, deviceId, calibrationId, captureDateTime, frameCount);

  /// Create a copy of NewCaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$NewCaptureSessionImplCopyWith<_$NewCaptureSessionImpl> get copyWith =>
      __$$NewCaptureSessionImplCopyWithImpl<_$NewCaptureSessionImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$NewCaptureSessionImplToJson(
      this,
    );
  }
}

abstract class _NewCaptureSession implements NewCaptureSession {
  const factory _NewCaptureSession(
      {@JsonKey(name: 'blast_event_id') required final String blastEventId,
      @JsonKey(name: 'quarry_id') required final String quarryId,
      @JsonKey(name: 'passport_id') required final String passportId,
      @JsonKey(name: 'device_id') required final String deviceId,
      @JsonKey(name: 'calibration_id') required final String calibrationId,
      @JsonKey(name: 'capture_datetime') required final String captureDateTime,
      @JsonKey(name: 'frame_count')
      final int frameCount}) = _$NewCaptureSessionImpl;

  factory _NewCaptureSession.fromJson(Map<String, dynamic> json) =
      _$NewCaptureSessionImpl.fromJson;

  @override
  @JsonKey(name: 'blast_event_id')
  String get blastEventId;
  @override
  @JsonKey(name: 'quarry_id')
  String get quarryId;
  @override
  @JsonKey(name: 'passport_id')
  String get passportId;
  @override
  @JsonKey(name: 'device_id')
  String get deviceId;
  @override
  @JsonKey(name: 'calibration_id')
  String get calibrationId;
  @override
  @JsonKey(name: 'capture_datetime')
  String get captureDateTime;
  @override
  @JsonKey(name: 'frame_count')
  int get frameCount;

  /// Create a copy of NewCaptureSession
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$NewCaptureSessionImplCopyWith<_$NewCaptureSessionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
