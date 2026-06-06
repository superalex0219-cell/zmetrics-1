// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'analysis_job.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

AnalysisJob _$AnalysisJobFromJson(Map<String, dynamic> json) {
  return _AnalysisJob.fromJson(json);
}

/// @nodoc
mixin _$AnalysisJob {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'capture_session_id')
  String get captureSessionId => throw _privateConstructorUsedError;
  AnalysisJobStatus get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'model_version_id')
  String? get modelVersionId => throw _privateConstructorUsedError;
  @JsonKey(name: 'report_id')
  String? get reportId => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_message')
  String? get errorMessage => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  DateTime? get createdAt => throw _privateConstructorUsedError;

  /// Serializes this AnalysisJob to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AnalysisJob
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AnalysisJobCopyWith<AnalysisJob> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AnalysisJobCopyWith<$Res> {
  factory $AnalysisJobCopyWith(
          AnalysisJob value, $Res Function(AnalysisJob) then) =
      _$AnalysisJobCopyWithImpl<$Res, AnalysisJob>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'capture_session_id') String captureSessionId,
      AnalysisJobStatus status,
      @JsonKey(name: 'model_version_id') String? modelVersionId,
      @JsonKey(name: 'report_id') String? reportId,
      @JsonKey(name: 'error_message') String? errorMessage,
      @JsonKey(name: 'created_at') DateTime? createdAt});
}

/// @nodoc
class _$AnalysisJobCopyWithImpl<$Res, $Val extends AnalysisJob>
    implements $AnalysisJobCopyWith<$Res> {
  _$AnalysisJobCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AnalysisJob
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? captureSessionId = null,
    Object? status = null,
    Object? modelVersionId = freezed,
    Object? reportId = freezed,
    Object? errorMessage = freezed,
    Object? createdAt = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      captureSessionId: null == captureSessionId
          ? _value.captureSessionId
          : captureSessionId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as AnalysisJobStatus,
      modelVersionId: freezed == modelVersionId
          ? _value.modelVersionId
          : modelVersionId // ignore: cast_nullable_to_non_nullable
              as String?,
      reportId: freezed == reportId
          ? _value.reportId
          : reportId // ignore: cast_nullable_to_non_nullable
              as String?,
      errorMessage: freezed == errorMessage
          ? _value.errorMessage
          : errorMessage // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AnalysisJobImplCopyWith<$Res>
    implements $AnalysisJobCopyWith<$Res> {
  factory _$$AnalysisJobImplCopyWith(
          _$AnalysisJobImpl value, $Res Function(_$AnalysisJobImpl) then) =
      __$$AnalysisJobImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'capture_session_id') String captureSessionId,
      AnalysisJobStatus status,
      @JsonKey(name: 'model_version_id') String? modelVersionId,
      @JsonKey(name: 'report_id') String? reportId,
      @JsonKey(name: 'error_message') String? errorMessage,
      @JsonKey(name: 'created_at') DateTime? createdAt});
}

/// @nodoc
class __$$AnalysisJobImplCopyWithImpl<$Res>
    extends _$AnalysisJobCopyWithImpl<$Res, _$AnalysisJobImpl>
    implements _$$AnalysisJobImplCopyWith<$Res> {
  __$$AnalysisJobImplCopyWithImpl(
      _$AnalysisJobImpl _value, $Res Function(_$AnalysisJobImpl) _then)
      : super(_value, _then);

  /// Create a copy of AnalysisJob
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? captureSessionId = null,
    Object? status = null,
    Object? modelVersionId = freezed,
    Object? reportId = freezed,
    Object? errorMessage = freezed,
    Object? createdAt = freezed,
  }) {
    return _then(_$AnalysisJobImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      captureSessionId: null == captureSessionId
          ? _value.captureSessionId
          : captureSessionId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as AnalysisJobStatus,
      modelVersionId: freezed == modelVersionId
          ? _value.modelVersionId
          : modelVersionId // ignore: cast_nullable_to_non_nullable
              as String?,
      reportId: freezed == reportId
          ? _value.reportId
          : reportId // ignore: cast_nullable_to_non_nullable
              as String?,
      errorMessage: freezed == errorMessage
          ? _value.errorMessage
          : errorMessage // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$AnalysisJobImpl implements _AnalysisJob {
  const _$AnalysisJobImpl(
      {required this.id,
      @JsonKey(name: 'capture_session_id') required this.captureSessionId,
      required this.status,
      @JsonKey(name: 'model_version_id') this.modelVersionId,
      @JsonKey(name: 'report_id') this.reportId,
      @JsonKey(name: 'error_message') this.errorMessage,
      @JsonKey(name: 'created_at') this.createdAt});

  factory _$AnalysisJobImpl.fromJson(Map<String, dynamic> json) =>
      _$$AnalysisJobImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'capture_session_id')
  final String captureSessionId;
  @override
  final AnalysisJobStatus status;
  @override
  @JsonKey(name: 'model_version_id')
  final String? modelVersionId;
  @override
  @JsonKey(name: 'report_id')
  final String? reportId;
  @override
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  @override
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  @override
  String toString() {
    return 'AnalysisJob(id: $id, captureSessionId: $captureSessionId, status: $status, modelVersionId: $modelVersionId, reportId: $reportId, errorMessage: $errorMessage, createdAt: $createdAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AnalysisJobImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.captureSessionId, captureSessionId) ||
                other.captureSessionId == captureSessionId) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.modelVersionId, modelVersionId) ||
                other.modelVersionId == modelVersionId) &&
            (identical(other.reportId, reportId) ||
                other.reportId == reportId) &&
            (identical(other.errorMessage, errorMessage) ||
                other.errorMessage == errorMessage) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, captureSessionId, status,
      modelVersionId, reportId, errorMessage, createdAt);

  /// Create a copy of AnalysisJob
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AnalysisJobImplCopyWith<_$AnalysisJobImpl> get copyWith =>
      __$$AnalysisJobImplCopyWithImpl<_$AnalysisJobImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AnalysisJobImplToJson(
      this,
    );
  }
}

abstract class _AnalysisJob implements AnalysisJob {
  const factory _AnalysisJob(
          {required final String id,
          @JsonKey(name: 'capture_session_id')
          required final String captureSessionId,
          required final AnalysisJobStatus status,
          @JsonKey(name: 'model_version_id') final String? modelVersionId,
          @JsonKey(name: 'report_id') final String? reportId,
          @JsonKey(name: 'error_message') final String? errorMessage,
          @JsonKey(name: 'created_at') final DateTime? createdAt}) =
      _$AnalysisJobImpl;

  factory _AnalysisJob.fromJson(Map<String, dynamic> json) =
      _$AnalysisJobImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'capture_session_id')
  String get captureSessionId;
  @override
  AnalysisJobStatus get status;
  @override
  @JsonKey(name: 'model_version_id')
  String? get modelVersionId;
  @override
  @JsonKey(name: 'report_id')
  String? get reportId;
  @override
  @JsonKey(name: 'error_message')
  String? get errorMessage;
  @override
  @JsonKey(name: 'created_at')
  DateTime? get createdAt;

  /// Create a copy of AnalysisJob
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AnalysisJobImplCopyWith<_$AnalysisJobImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
