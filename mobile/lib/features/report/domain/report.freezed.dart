// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'report.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

Report _$ReportFromJson(Map<String, dynamic> json) {
  return _Report.fromJson(json);
}

/// @nodoc
mixin _$Report {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'analysis_result_id')
  String? get analysisResultId =>
      throw _privateConstructorUsedError; // Backend always sends analysis_method; default .mock is fail-safe —
// shows warning badge if the field is absent rather than silently hiding it.
  @JsonKey(name: 'analysis_method')
  AnalysisMethod get analysisMethod => throw _privateConstructorUsedError;
  String? get title => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  DateTime? get createdAt => throw _privateConstructorUsedError;
  String? get summary => throw _privateConstructorUsedError;
  @JsonKey(name: 'analysis_result')
  AnalysisResult? get analysisResult => throw _privateConstructorUsedError;
  List<Recommendation> get recommendations =>
      throw _privateConstructorUsedError;

  /// Serializes this Report to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Report
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ReportCopyWith<Report> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ReportCopyWith<$Res> {
  factory $ReportCopyWith(Report value, $Res Function(Report) then) =
      _$ReportCopyWithImpl<$Res, Report>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'analysis_result_id') String? analysisResultId,
      @JsonKey(name: 'analysis_method') AnalysisMethod analysisMethod,
      String? title,
      @JsonKey(name: 'created_at') DateTime? createdAt,
      String? summary,
      @JsonKey(name: 'analysis_result') AnalysisResult? analysisResult,
      List<Recommendation> recommendations});

  $AnalysisResultCopyWith<$Res>? get analysisResult;
}

/// @nodoc
class _$ReportCopyWithImpl<$Res, $Val extends Report>
    implements $ReportCopyWith<$Res> {
  _$ReportCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Report
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? analysisResultId = freezed,
    Object? analysisMethod = null,
    Object? title = freezed,
    Object? createdAt = freezed,
    Object? summary = freezed,
    Object? analysisResult = freezed,
    Object? recommendations = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      analysisResultId: freezed == analysisResultId
          ? _value.analysisResultId
          : analysisResultId // ignore: cast_nullable_to_non_nullable
              as String?,
      analysisMethod: null == analysisMethod
          ? _value.analysisMethod
          : analysisMethod // ignore: cast_nullable_to_non_nullable
              as AnalysisMethod,
      title: freezed == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      summary: freezed == summary
          ? _value.summary
          : summary // ignore: cast_nullable_to_non_nullable
              as String?,
      analysisResult: freezed == analysisResult
          ? _value.analysisResult
          : analysisResult // ignore: cast_nullable_to_non_nullable
              as AnalysisResult?,
      recommendations: null == recommendations
          ? _value.recommendations
          : recommendations // ignore: cast_nullable_to_non_nullable
              as List<Recommendation>,
    ) as $Val);
  }

  /// Create a copy of Report
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $AnalysisResultCopyWith<$Res>? get analysisResult {
    if (_value.analysisResult == null) {
      return null;
    }

    return $AnalysisResultCopyWith<$Res>(_value.analysisResult!, (value) {
      return _then(_value.copyWith(analysisResult: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$ReportImplCopyWith<$Res> implements $ReportCopyWith<$Res> {
  factory _$$ReportImplCopyWith(
          _$ReportImpl value, $Res Function(_$ReportImpl) then) =
      __$$ReportImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'analysis_result_id') String? analysisResultId,
      @JsonKey(name: 'analysis_method') AnalysisMethod analysisMethod,
      String? title,
      @JsonKey(name: 'created_at') DateTime? createdAt,
      String? summary,
      @JsonKey(name: 'analysis_result') AnalysisResult? analysisResult,
      List<Recommendation> recommendations});

  @override
  $AnalysisResultCopyWith<$Res>? get analysisResult;
}

/// @nodoc
class __$$ReportImplCopyWithImpl<$Res>
    extends _$ReportCopyWithImpl<$Res, _$ReportImpl>
    implements _$$ReportImplCopyWith<$Res> {
  __$$ReportImplCopyWithImpl(
      _$ReportImpl _value, $Res Function(_$ReportImpl) _then)
      : super(_value, _then);

  /// Create a copy of Report
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? analysisResultId = freezed,
    Object? analysisMethod = null,
    Object? title = freezed,
    Object? createdAt = freezed,
    Object? summary = freezed,
    Object? analysisResult = freezed,
    Object? recommendations = null,
  }) {
    return _then(_$ReportImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      analysisResultId: freezed == analysisResultId
          ? _value.analysisResultId
          : analysisResultId // ignore: cast_nullable_to_non_nullable
              as String?,
      analysisMethod: null == analysisMethod
          ? _value.analysisMethod
          : analysisMethod // ignore: cast_nullable_to_non_nullable
              as AnalysisMethod,
      title: freezed == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      summary: freezed == summary
          ? _value.summary
          : summary // ignore: cast_nullable_to_non_nullable
              as String?,
      analysisResult: freezed == analysisResult
          ? _value.analysisResult
          : analysisResult // ignore: cast_nullable_to_non_nullable
              as AnalysisResult?,
      recommendations: null == recommendations
          ? _value._recommendations
          : recommendations // ignore: cast_nullable_to_non_nullable
              as List<Recommendation>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ReportImpl implements _Report {
  const _$ReportImpl(
      {required this.id,
      @JsonKey(name: 'analysis_result_id') this.analysisResultId,
      @JsonKey(name: 'analysis_method')
      this.analysisMethod = AnalysisMethod.mock,
      this.title,
      @JsonKey(name: 'created_at') this.createdAt,
      this.summary,
      @JsonKey(name: 'analysis_result') this.analysisResult,
      final List<Recommendation> recommendations = const <Recommendation>[]})
      : _recommendations = recommendations;

  factory _$ReportImpl.fromJson(Map<String, dynamic> json) =>
      _$$ReportImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'analysis_result_id')
  final String? analysisResultId;
// Backend always sends analysis_method; default .mock is fail-safe —
// shows warning badge if the field is absent rather than silently hiding it.
  @override
  @JsonKey(name: 'analysis_method')
  final AnalysisMethod analysisMethod;
  @override
  final String? title;
  @override
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;
  @override
  final String? summary;
  @override
  @JsonKey(name: 'analysis_result')
  final AnalysisResult? analysisResult;
  final List<Recommendation> _recommendations;
  @override
  @JsonKey()
  List<Recommendation> get recommendations {
    if (_recommendations is EqualUnmodifiableListView) return _recommendations;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_recommendations);
  }

  @override
  String toString() {
    return 'Report(id: $id, analysisResultId: $analysisResultId, analysisMethod: $analysisMethod, title: $title, createdAt: $createdAt, summary: $summary, analysisResult: $analysisResult, recommendations: $recommendations)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ReportImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.analysisResultId, analysisResultId) ||
                other.analysisResultId == analysisResultId) &&
            (identical(other.analysisMethod, analysisMethod) ||
                other.analysisMethod == analysisMethod) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.summary, summary) || other.summary == summary) &&
            (identical(other.analysisResult, analysisResult) ||
                other.analysisResult == analysisResult) &&
            const DeepCollectionEquality()
                .equals(other._recommendations, _recommendations));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      analysisResultId,
      analysisMethod,
      title,
      createdAt,
      summary,
      analysisResult,
      const DeepCollectionEquality().hash(_recommendations));

  /// Create a copy of Report
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ReportImplCopyWith<_$ReportImpl> get copyWith =>
      __$$ReportImplCopyWithImpl<_$ReportImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ReportImplToJson(
      this,
    );
  }
}

abstract class _Report implements Report {
  const factory _Report(
      {required final String id,
      @JsonKey(name: 'analysis_result_id') final String? analysisResultId,
      @JsonKey(name: 'analysis_method') final AnalysisMethod analysisMethod,
      final String? title,
      @JsonKey(name: 'created_at') final DateTime? createdAt,
      final String? summary,
      @JsonKey(name: 'analysis_result') final AnalysisResult? analysisResult,
      final List<Recommendation> recommendations}) = _$ReportImpl;

  factory _Report.fromJson(Map<String, dynamic> json) = _$ReportImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'analysis_result_id')
  String?
      get analysisResultId; // Backend always sends analysis_method; default .mock is fail-safe —
// shows warning badge if the field is absent rather than silently hiding it.
  @override
  @JsonKey(name: 'analysis_method')
  AnalysisMethod get analysisMethod;
  @override
  String? get title;
  @override
  @JsonKey(name: 'created_at')
  DateTime? get createdAt;
  @override
  String? get summary;
  @override
  @JsonKey(name: 'analysis_result')
  AnalysisResult? get analysisResult;
  @override
  List<Recommendation> get recommendations;

  /// Create a copy of Report
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ReportImplCopyWith<_$ReportImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
