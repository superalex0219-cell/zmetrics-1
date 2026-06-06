// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'analysis_result.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

SizeBin _$SizeBinFromJson(Map<String, dynamic> json) {
  return _SizeBin.fromJson(json);
}

/// @nodoc
mixin _$SizeBin {
  @JsonKey(name: 'size_mm')
  double get sizeMm => throw _privateConstructorUsedError;
  @JsonKey(name: 'cumulative_passing_pct')
  double get cumulativePassingPct => throw _privateConstructorUsedError;

  /// Serializes this SizeBin to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of SizeBin
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $SizeBinCopyWith<SizeBin> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $SizeBinCopyWith<$Res> {
  factory $SizeBinCopyWith(SizeBin value, $Res Function(SizeBin) then) =
      _$SizeBinCopyWithImpl<$Res, SizeBin>;
  @useResult
  $Res call(
      {@JsonKey(name: 'size_mm') double sizeMm,
      @JsonKey(name: 'cumulative_passing_pct') double cumulativePassingPct});
}

/// @nodoc
class _$SizeBinCopyWithImpl<$Res, $Val extends SizeBin>
    implements $SizeBinCopyWith<$Res> {
  _$SizeBinCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of SizeBin
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? sizeMm = null,
    Object? cumulativePassingPct = null,
  }) {
    return _then(_value.copyWith(
      sizeMm: null == sizeMm
          ? _value.sizeMm
          : sizeMm // ignore: cast_nullable_to_non_nullable
              as double,
      cumulativePassingPct: null == cumulativePassingPct
          ? _value.cumulativePassingPct
          : cumulativePassingPct // ignore: cast_nullable_to_non_nullable
              as double,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$SizeBinImplCopyWith<$Res> implements $SizeBinCopyWith<$Res> {
  factory _$$SizeBinImplCopyWith(
          _$SizeBinImpl value, $Res Function(_$SizeBinImpl) then) =
      __$$SizeBinImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'size_mm') double sizeMm,
      @JsonKey(name: 'cumulative_passing_pct') double cumulativePassingPct});
}

/// @nodoc
class __$$SizeBinImplCopyWithImpl<$Res>
    extends _$SizeBinCopyWithImpl<$Res, _$SizeBinImpl>
    implements _$$SizeBinImplCopyWith<$Res> {
  __$$SizeBinImplCopyWithImpl(
      _$SizeBinImpl _value, $Res Function(_$SizeBinImpl) _then)
      : super(_value, _then);

  /// Create a copy of SizeBin
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? sizeMm = null,
    Object? cumulativePassingPct = null,
  }) {
    return _then(_$SizeBinImpl(
      sizeMm: null == sizeMm
          ? _value.sizeMm
          : sizeMm // ignore: cast_nullable_to_non_nullable
              as double,
      cumulativePassingPct: null == cumulativePassingPct
          ? _value.cumulativePassingPct
          : cumulativePassingPct // ignore: cast_nullable_to_non_nullable
              as double,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$SizeBinImpl implements _SizeBin {
  const _$SizeBinImpl(
      {@JsonKey(name: 'size_mm') required this.sizeMm,
      @JsonKey(name: 'cumulative_passing_pct')
      required this.cumulativePassingPct});

  factory _$SizeBinImpl.fromJson(Map<String, dynamic> json) =>
      _$$SizeBinImplFromJson(json);

  @override
  @JsonKey(name: 'size_mm')
  final double sizeMm;
  @override
  @JsonKey(name: 'cumulative_passing_pct')
  final double cumulativePassingPct;

  @override
  String toString() {
    return 'SizeBin(sizeMm: $sizeMm, cumulativePassingPct: $cumulativePassingPct)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$SizeBinImpl &&
            (identical(other.sizeMm, sizeMm) || other.sizeMm == sizeMm) &&
            (identical(other.cumulativePassingPct, cumulativePassingPct) ||
                other.cumulativePassingPct == cumulativePassingPct));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, sizeMm, cumulativePassingPct);

  /// Create a copy of SizeBin
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$SizeBinImplCopyWith<_$SizeBinImpl> get copyWith =>
      __$$SizeBinImplCopyWithImpl<_$SizeBinImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$SizeBinImplToJson(
      this,
    );
  }
}

abstract class _SizeBin implements SizeBin {
  const factory _SizeBin(
      {@JsonKey(name: 'size_mm') required final double sizeMm,
      @JsonKey(name: 'cumulative_passing_pct')
      required final double cumulativePassingPct}) = _$SizeBinImpl;

  factory _SizeBin.fromJson(Map<String, dynamic> json) = _$SizeBinImpl.fromJson;

  @override
  @JsonKey(name: 'size_mm')
  double get sizeMm;
  @override
  @JsonKey(name: 'cumulative_passing_pct')
  double get cumulativePassingPct;

  /// Create a copy of SizeBin
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$SizeBinImplCopyWith<_$SizeBinImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

AnalysisResult _$AnalysisResultFromJson(Map<String, dynamic> json) {
  return _AnalysisResult.fromJson(json);
}

/// @nodoc
mixin _$AnalysisResult {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'p10_mm')
  double get p10Mm => throw _privateConstructorUsedError;
  @JsonKey(name: 'p50_mm')
  double get p50Mm => throw _privateConstructorUsedError;
  @JsonKey(name: 'p80_mm')
  double get p80Mm => throw _privateConstructorUsedError;
  @JsonKey(name: 'rosin_rammler_n')
  double? get rosinRammlerN => throw _privateConstructorUsedError;
  @JsonKey(name: 'rosin_rammler_xc')
  double? get rosinRammlerXc => throw _privateConstructorUsedError;
  @JsonKey(name: 'oversize_percent')
  double? get oversizePercent => throw _privateConstructorUsedError;
  @JsonKey(name: 'fines_percent')
  double? get finesPercent => throw _privateConstructorUsedError;
  @JsonKey(name: 'confidence_score')
  double? get confidenceScore => throw _privateConstructorUsedError;
  @JsonKey(name: 'size_distribution')
  List<SizeBin> get sizeDistribution => throw _privateConstructorUsedError;

  /// Serializes this AnalysisResult to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AnalysisResult
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AnalysisResultCopyWith<AnalysisResult> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AnalysisResultCopyWith<$Res> {
  factory $AnalysisResultCopyWith(
          AnalysisResult value, $Res Function(AnalysisResult) then) =
      _$AnalysisResultCopyWithImpl<$Res, AnalysisResult>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'p10_mm') double p10Mm,
      @JsonKey(name: 'p50_mm') double p50Mm,
      @JsonKey(name: 'p80_mm') double p80Mm,
      @JsonKey(name: 'rosin_rammler_n') double? rosinRammlerN,
      @JsonKey(name: 'rosin_rammler_xc') double? rosinRammlerXc,
      @JsonKey(name: 'oversize_percent') double? oversizePercent,
      @JsonKey(name: 'fines_percent') double? finesPercent,
      @JsonKey(name: 'confidence_score') double? confidenceScore,
      @JsonKey(name: 'size_distribution') List<SizeBin> sizeDistribution});
}

/// @nodoc
class _$AnalysisResultCopyWithImpl<$Res, $Val extends AnalysisResult>
    implements $AnalysisResultCopyWith<$Res> {
  _$AnalysisResultCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AnalysisResult
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? p10Mm = null,
    Object? p50Mm = null,
    Object? p80Mm = null,
    Object? rosinRammlerN = freezed,
    Object? rosinRammlerXc = freezed,
    Object? oversizePercent = freezed,
    Object? finesPercent = freezed,
    Object? confidenceScore = freezed,
    Object? sizeDistribution = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      p10Mm: null == p10Mm
          ? _value.p10Mm
          : p10Mm // ignore: cast_nullable_to_non_nullable
              as double,
      p50Mm: null == p50Mm
          ? _value.p50Mm
          : p50Mm // ignore: cast_nullable_to_non_nullable
              as double,
      p80Mm: null == p80Mm
          ? _value.p80Mm
          : p80Mm // ignore: cast_nullable_to_non_nullable
              as double,
      rosinRammlerN: freezed == rosinRammlerN
          ? _value.rosinRammlerN
          : rosinRammlerN // ignore: cast_nullable_to_non_nullable
              as double?,
      rosinRammlerXc: freezed == rosinRammlerXc
          ? _value.rosinRammlerXc
          : rosinRammlerXc // ignore: cast_nullable_to_non_nullable
              as double?,
      oversizePercent: freezed == oversizePercent
          ? _value.oversizePercent
          : oversizePercent // ignore: cast_nullable_to_non_nullable
              as double?,
      finesPercent: freezed == finesPercent
          ? _value.finesPercent
          : finesPercent // ignore: cast_nullable_to_non_nullable
              as double?,
      confidenceScore: freezed == confidenceScore
          ? _value.confidenceScore
          : confidenceScore // ignore: cast_nullable_to_non_nullable
              as double?,
      sizeDistribution: null == sizeDistribution
          ? _value.sizeDistribution
          : sizeDistribution // ignore: cast_nullable_to_non_nullable
              as List<SizeBin>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AnalysisResultImplCopyWith<$Res>
    implements $AnalysisResultCopyWith<$Res> {
  factory _$$AnalysisResultImplCopyWith(_$AnalysisResultImpl value,
          $Res Function(_$AnalysisResultImpl) then) =
      __$$AnalysisResultImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'p10_mm') double p10Mm,
      @JsonKey(name: 'p50_mm') double p50Mm,
      @JsonKey(name: 'p80_mm') double p80Mm,
      @JsonKey(name: 'rosin_rammler_n') double? rosinRammlerN,
      @JsonKey(name: 'rosin_rammler_xc') double? rosinRammlerXc,
      @JsonKey(name: 'oversize_percent') double? oversizePercent,
      @JsonKey(name: 'fines_percent') double? finesPercent,
      @JsonKey(name: 'confidence_score') double? confidenceScore,
      @JsonKey(name: 'size_distribution') List<SizeBin> sizeDistribution});
}

/// @nodoc
class __$$AnalysisResultImplCopyWithImpl<$Res>
    extends _$AnalysisResultCopyWithImpl<$Res, _$AnalysisResultImpl>
    implements _$$AnalysisResultImplCopyWith<$Res> {
  __$$AnalysisResultImplCopyWithImpl(
      _$AnalysisResultImpl _value, $Res Function(_$AnalysisResultImpl) _then)
      : super(_value, _then);

  /// Create a copy of AnalysisResult
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? p10Mm = null,
    Object? p50Mm = null,
    Object? p80Mm = null,
    Object? rosinRammlerN = freezed,
    Object? rosinRammlerXc = freezed,
    Object? oversizePercent = freezed,
    Object? finesPercent = freezed,
    Object? confidenceScore = freezed,
    Object? sizeDistribution = null,
  }) {
    return _then(_$AnalysisResultImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      p10Mm: null == p10Mm
          ? _value.p10Mm
          : p10Mm // ignore: cast_nullable_to_non_nullable
              as double,
      p50Mm: null == p50Mm
          ? _value.p50Mm
          : p50Mm // ignore: cast_nullable_to_non_nullable
              as double,
      p80Mm: null == p80Mm
          ? _value.p80Mm
          : p80Mm // ignore: cast_nullable_to_non_nullable
              as double,
      rosinRammlerN: freezed == rosinRammlerN
          ? _value.rosinRammlerN
          : rosinRammlerN // ignore: cast_nullable_to_non_nullable
              as double?,
      rosinRammlerXc: freezed == rosinRammlerXc
          ? _value.rosinRammlerXc
          : rosinRammlerXc // ignore: cast_nullable_to_non_nullable
              as double?,
      oversizePercent: freezed == oversizePercent
          ? _value.oversizePercent
          : oversizePercent // ignore: cast_nullable_to_non_nullable
              as double?,
      finesPercent: freezed == finesPercent
          ? _value.finesPercent
          : finesPercent // ignore: cast_nullable_to_non_nullable
              as double?,
      confidenceScore: freezed == confidenceScore
          ? _value.confidenceScore
          : confidenceScore // ignore: cast_nullable_to_non_nullable
              as double?,
      sizeDistribution: null == sizeDistribution
          ? _value._sizeDistribution
          : sizeDistribution // ignore: cast_nullable_to_non_nullable
              as List<SizeBin>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$AnalysisResultImpl implements _AnalysisResult {
  const _$AnalysisResultImpl(
      {required this.id,
      @JsonKey(name: 'p10_mm') required this.p10Mm,
      @JsonKey(name: 'p50_mm') required this.p50Mm,
      @JsonKey(name: 'p80_mm') required this.p80Mm,
      @JsonKey(name: 'rosin_rammler_n') this.rosinRammlerN,
      @JsonKey(name: 'rosin_rammler_xc') this.rosinRammlerXc,
      @JsonKey(name: 'oversize_percent') this.oversizePercent,
      @JsonKey(name: 'fines_percent') this.finesPercent,
      @JsonKey(name: 'confidence_score') this.confidenceScore,
      @JsonKey(name: 'size_distribution')
      final List<SizeBin> sizeDistribution = const <SizeBin>[]})
      : _sizeDistribution = sizeDistribution;

  factory _$AnalysisResultImpl.fromJson(Map<String, dynamic> json) =>
      _$$AnalysisResultImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'p10_mm')
  final double p10Mm;
  @override
  @JsonKey(name: 'p50_mm')
  final double p50Mm;
  @override
  @JsonKey(name: 'p80_mm')
  final double p80Mm;
  @override
  @JsonKey(name: 'rosin_rammler_n')
  final double? rosinRammlerN;
  @override
  @JsonKey(name: 'rosin_rammler_xc')
  final double? rosinRammlerXc;
  @override
  @JsonKey(name: 'oversize_percent')
  final double? oversizePercent;
  @override
  @JsonKey(name: 'fines_percent')
  final double? finesPercent;
  @override
  @JsonKey(name: 'confidence_score')
  final double? confidenceScore;
  final List<SizeBin> _sizeDistribution;
  @override
  @JsonKey(name: 'size_distribution')
  List<SizeBin> get sizeDistribution {
    if (_sizeDistribution is EqualUnmodifiableListView)
      return _sizeDistribution;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_sizeDistribution);
  }

  @override
  String toString() {
    return 'AnalysisResult(id: $id, p10Mm: $p10Mm, p50Mm: $p50Mm, p80Mm: $p80Mm, rosinRammlerN: $rosinRammlerN, rosinRammlerXc: $rosinRammlerXc, oversizePercent: $oversizePercent, finesPercent: $finesPercent, confidenceScore: $confidenceScore, sizeDistribution: $sizeDistribution)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AnalysisResultImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.p10Mm, p10Mm) || other.p10Mm == p10Mm) &&
            (identical(other.p50Mm, p50Mm) || other.p50Mm == p50Mm) &&
            (identical(other.p80Mm, p80Mm) || other.p80Mm == p80Mm) &&
            (identical(other.rosinRammlerN, rosinRammlerN) ||
                other.rosinRammlerN == rosinRammlerN) &&
            (identical(other.rosinRammlerXc, rosinRammlerXc) ||
                other.rosinRammlerXc == rosinRammlerXc) &&
            (identical(other.oversizePercent, oversizePercent) ||
                other.oversizePercent == oversizePercent) &&
            (identical(other.finesPercent, finesPercent) ||
                other.finesPercent == finesPercent) &&
            (identical(other.confidenceScore, confidenceScore) ||
                other.confidenceScore == confidenceScore) &&
            const DeepCollectionEquality()
                .equals(other._sizeDistribution, _sizeDistribution));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      p10Mm,
      p50Mm,
      p80Mm,
      rosinRammlerN,
      rosinRammlerXc,
      oversizePercent,
      finesPercent,
      confidenceScore,
      const DeepCollectionEquality().hash(_sizeDistribution));

  /// Create a copy of AnalysisResult
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AnalysisResultImplCopyWith<_$AnalysisResultImpl> get copyWith =>
      __$$AnalysisResultImplCopyWithImpl<_$AnalysisResultImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AnalysisResultImplToJson(
      this,
    );
  }
}

abstract class _AnalysisResult implements AnalysisResult {
  const factory _AnalysisResult(
      {required final String id,
      @JsonKey(name: 'p10_mm') required final double p10Mm,
      @JsonKey(name: 'p50_mm') required final double p50Mm,
      @JsonKey(name: 'p80_mm') required final double p80Mm,
      @JsonKey(name: 'rosin_rammler_n') final double? rosinRammlerN,
      @JsonKey(name: 'rosin_rammler_xc') final double? rosinRammlerXc,
      @JsonKey(name: 'oversize_percent') final double? oversizePercent,
      @JsonKey(name: 'fines_percent') final double? finesPercent,
      @JsonKey(name: 'confidence_score') final double? confidenceScore,
      @JsonKey(name: 'size_distribution')
      final List<SizeBin> sizeDistribution}) = _$AnalysisResultImpl;

  factory _AnalysisResult.fromJson(Map<String, dynamic> json) =
      _$AnalysisResultImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'p10_mm')
  double get p10Mm;
  @override
  @JsonKey(name: 'p50_mm')
  double get p50Mm;
  @override
  @JsonKey(name: 'p80_mm')
  double get p80Mm;
  @override
  @JsonKey(name: 'rosin_rammler_n')
  double? get rosinRammlerN;
  @override
  @JsonKey(name: 'rosin_rammler_xc')
  double? get rosinRammlerXc;
  @override
  @JsonKey(name: 'oversize_percent')
  double? get oversizePercent;
  @override
  @JsonKey(name: 'fines_percent')
  double? get finesPercent;
  @override
  @JsonKey(name: 'confidence_score')
  double? get confidenceScore;
  @override
  @JsonKey(name: 'size_distribution')
  List<SizeBin> get sizeDistribution;

  /// Create a copy of AnalysisResult
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AnalysisResultImplCopyWith<_$AnalysisResultImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
