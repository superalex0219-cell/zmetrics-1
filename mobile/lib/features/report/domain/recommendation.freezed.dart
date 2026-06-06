// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'recommendation.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

Recommendation _$RecommendationFromJson(Map<String, dynamic> json) {
  return _Recommendation.fromJson(json);
}

/// @nodoc
mixin _$Recommendation {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'report_id')
  String get reportId => throw _privateConstructorUsedError;
  RecommendationStatus get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'recommendation_text')
  String get recommendationText => throw _privateConstructorUsedError;
  @JsonKey(name: 'confidence_notes')
  String? get confidenceNotes => throw _privateConstructorUsedError;
  @JsonKey(name: 'parameter_suggestions')
  Map<String, dynamic> get parameterSuggestions =>
      throw _privateConstructorUsedError;
  List<Comment> get comments => throw _privateConstructorUsedError;

  /// Serializes this Recommendation to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Recommendation
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $RecommendationCopyWith<Recommendation> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RecommendationCopyWith<$Res> {
  factory $RecommendationCopyWith(
          Recommendation value, $Res Function(Recommendation) then) =
      _$RecommendationCopyWithImpl<$Res, Recommendation>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'report_id') String reportId,
      RecommendationStatus status,
      @JsonKey(name: 'recommendation_text') String recommendationText,
      @JsonKey(name: 'confidence_notes') String? confidenceNotes,
      @JsonKey(name: 'parameter_suggestions')
      Map<String, dynamic> parameterSuggestions,
      List<Comment> comments});
}

/// @nodoc
class _$RecommendationCopyWithImpl<$Res, $Val extends Recommendation>
    implements $RecommendationCopyWith<$Res> {
  _$RecommendationCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Recommendation
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? reportId = null,
    Object? status = null,
    Object? recommendationText = null,
    Object? confidenceNotes = freezed,
    Object? parameterSuggestions = null,
    Object? comments = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      reportId: null == reportId
          ? _value.reportId
          : reportId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as RecommendationStatus,
      recommendationText: null == recommendationText
          ? _value.recommendationText
          : recommendationText // ignore: cast_nullable_to_non_nullable
              as String,
      confidenceNotes: freezed == confidenceNotes
          ? _value.confidenceNotes
          : confidenceNotes // ignore: cast_nullable_to_non_nullable
              as String?,
      parameterSuggestions: null == parameterSuggestions
          ? _value.parameterSuggestions
          : parameterSuggestions // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>,
      comments: null == comments
          ? _value.comments
          : comments // ignore: cast_nullable_to_non_nullable
              as List<Comment>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$RecommendationImplCopyWith<$Res>
    implements $RecommendationCopyWith<$Res> {
  factory _$$RecommendationImplCopyWith(_$RecommendationImpl value,
          $Res Function(_$RecommendationImpl) then) =
      __$$RecommendationImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'report_id') String reportId,
      RecommendationStatus status,
      @JsonKey(name: 'recommendation_text') String recommendationText,
      @JsonKey(name: 'confidence_notes') String? confidenceNotes,
      @JsonKey(name: 'parameter_suggestions')
      Map<String, dynamic> parameterSuggestions,
      List<Comment> comments});
}

/// @nodoc
class __$$RecommendationImplCopyWithImpl<$Res>
    extends _$RecommendationCopyWithImpl<$Res, _$RecommendationImpl>
    implements _$$RecommendationImplCopyWith<$Res> {
  __$$RecommendationImplCopyWithImpl(
      _$RecommendationImpl _value, $Res Function(_$RecommendationImpl) _then)
      : super(_value, _then);

  /// Create a copy of Recommendation
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? reportId = null,
    Object? status = null,
    Object? recommendationText = null,
    Object? confidenceNotes = freezed,
    Object? parameterSuggestions = null,
    Object? comments = null,
  }) {
    return _then(_$RecommendationImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      reportId: null == reportId
          ? _value.reportId
          : reportId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as RecommendationStatus,
      recommendationText: null == recommendationText
          ? _value.recommendationText
          : recommendationText // ignore: cast_nullable_to_non_nullable
              as String,
      confidenceNotes: freezed == confidenceNotes
          ? _value.confidenceNotes
          : confidenceNotes // ignore: cast_nullable_to_non_nullable
              as String?,
      parameterSuggestions: null == parameterSuggestions
          ? _value._parameterSuggestions
          : parameterSuggestions // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>,
      comments: null == comments
          ? _value._comments
          : comments // ignore: cast_nullable_to_non_nullable
              as List<Comment>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$RecommendationImpl implements _Recommendation {
  const _$RecommendationImpl(
      {required this.id,
      @JsonKey(name: 'report_id') required this.reportId,
      required this.status,
      @JsonKey(name: 'recommendation_text') required this.recommendationText,
      @JsonKey(name: 'confidence_notes') this.confidenceNotes,
      @JsonKey(name: 'parameter_suggestions')
      final Map<String, dynamic> parameterSuggestions =
          const <String, dynamic>{},
      final List<Comment> comments = const <Comment>[]})
      : _parameterSuggestions = parameterSuggestions,
        _comments = comments;

  factory _$RecommendationImpl.fromJson(Map<String, dynamic> json) =>
      _$$RecommendationImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'report_id')
  final String reportId;
  @override
  final RecommendationStatus status;
  @override
  @JsonKey(name: 'recommendation_text')
  final String recommendationText;
  @override
  @JsonKey(name: 'confidence_notes')
  final String? confidenceNotes;
  final Map<String, dynamic> _parameterSuggestions;
  @override
  @JsonKey(name: 'parameter_suggestions')
  Map<String, dynamic> get parameterSuggestions {
    if (_parameterSuggestions is EqualUnmodifiableMapView)
      return _parameterSuggestions;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_parameterSuggestions);
  }

  final List<Comment> _comments;
  @override
  @JsonKey()
  List<Comment> get comments {
    if (_comments is EqualUnmodifiableListView) return _comments;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_comments);
  }

  @override
  String toString() {
    return 'Recommendation(id: $id, reportId: $reportId, status: $status, recommendationText: $recommendationText, confidenceNotes: $confidenceNotes, parameterSuggestions: $parameterSuggestions, comments: $comments)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RecommendationImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.reportId, reportId) ||
                other.reportId == reportId) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.recommendationText, recommendationText) ||
                other.recommendationText == recommendationText) &&
            (identical(other.confidenceNotes, confidenceNotes) ||
                other.confidenceNotes == confidenceNotes) &&
            const DeepCollectionEquality()
                .equals(other._parameterSuggestions, _parameterSuggestions) &&
            const DeepCollectionEquality().equals(other._comments, _comments));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      reportId,
      status,
      recommendationText,
      confidenceNotes,
      const DeepCollectionEquality().hash(_parameterSuggestions),
      const DeepCollectionEquality().hash(_comments));

  /// Create a copy of Recommendation
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RecommendationImplCopyWith<_$RecommendationImpl> get copyWith =>
      __$$RecommendationImplCopyWithImpl<_$RecommendationImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RecommendationImplToJson(
      this,
    );
  }
}

abstract class _Recommendation implements Recommendation {
  const factory _Recommendation(
      {required final String id,
      @JsonKey(name: 'report_id') required final String reportId,
      required final RecommendationStatus status,
      @JsonKey(name: 'recommendation_text')
      required final String recommendationText,
      @JsonKey(name: 'confidence_notes') final String? confidenceNotes,
      @JsonKey(name: 'parameter_suggestions')
      final Map<String, dynamic> parameterSuggestions,
      final List<Comment> comments}) = _$RecommendationImpl;

  factory _Recommendation.fromJson(Map<String, dynamic> json) =
      _$RecommendationImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'report_id')
  String get reportId;
  @override
  RecommendationStatus get status;
  @override
  @JsonKey(name: 'recommendation_text')
  String get recommendationText;
  @override
  @JsonKey(name: 'confidence_notes')
  String? get confidenceNotes;
  @override
  @JsonKey(name: 'parameter_suggestions')
  Map<String, dynamic> get parameterSuggestions;
  @override
  List<Comment> get comments;

  /// Create a copy of Recommendation
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RecommendationImplCopyWith<_$RecommendationImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
