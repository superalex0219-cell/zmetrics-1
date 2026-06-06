// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'blast_passport.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

BlastPassport _$BlastPassportFromJson(Map<String, dynamic> json) {
  return _BlastPassport.fromJson(json);
}

/// @nodoc
mixin _$BlastPassport {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'site_section_id')
  String get siteSectionId => throw _privateConstructorUsedError;
  PassportStatus get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'revision_number')
  int get revisionNumber => throw _privateConstructorUsedError;
  @JsonKey(name: 'superseded_by_id')
  String? get supersededById => throw _privateConstructorUsedError;
  @JsonKey(name: 'explosive_type')
  String? get explosiveType => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_explosive_kg')
  double? get totalExplosiveKg => throw _privateConstructorUsedError;
  @JsonKey(name: 'hole_diameter_mm')
  double? get holeDiameterMm => throw _privateConstructorUsedError;
  @JsonKey(name: 'hole_depth_m')
  double? get holeDepthM => throw _privateConstructorUsedError;
  @JsonKey(name: 'burden_m')
  double? get burdenM => throw _privateConstructorUsedError;
  @JsonKey(name: 'spacing_m')
  double? get spacingM => throw _privateConstructorUsedError;
  @JsonKey(name: 'stemming_m')
  double? get stemmingM => throw _privateConstructorUsedError;
  @JsonKey(name: 'target_p80_mm')
  double? get targetP80Mm => throw _privateConstructorUsedError;

  /// Serializes this BlastPassport to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of BlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $BlastPassportCopyWith<BlastPassport> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $BlastPassportCopyWith<$Res> {
  factory $BlastPassportCopyWith(
          BlastPassport value, $Res Function(BlastPassport) then) =
      _$BlastPassportCopyWithImpl<$Res, BlastPassport>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'site_section_id') String siteSectionId,
      PassportStatus status,
      @JsonKey(name: 'revision_number') int revisionNumber,
      @JsonKey(name: 'superseded_by_id') String? supersededById,
      @JsonKey(name: 'explosive_type') String? explosiveType,
      @JsonKey(name: 'total_explosive_kg') double? totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') double? holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') double? holeDepthM,
      @JsonKey(name: 'burden_m') double? burdenM,
      @JsonKey(name: 'spacing_m') double? spacingM,
      @JsonKey(name: 'stemming_m') double? stemmingM,
      @JsonKey(name: 'target_p80_mm') double? targetP80Mm});
}

/// @nodoc
class _$BlastPassportCopyWithImpl<$Res, $Val extends BlastPassport>
    implements $BlastPassportCopyWith<$Res> {
  _$BlastPassportCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of BlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? siteSectionId = null,
    Object? status = null,
    Object? revisionNumber = null,
    Object? supersededById = freezed,
    Object? explosiveType = freezed,
    Object? totalExplosiveKg = freezed,
    Object? holeDiameterMm = freezed,
    Object? holeDepthM = freezed,
    Object? burdenM = freezed,
    Object? spacingM = freezed,
    Object? stemmingM = freezed,
    Object? targetP80Mm = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      siteSectionId: null == siteSectionId
          ? _value.siteSectionId
          : siteSectionId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as PassportStatus,
      revisionNumber: null == revisionNumber
          ? _value.revisionNumber
          : revisionNumber // ignore: cast_nullable_to_non_nullable
              as int,
      supersededById: freezed == supersededById
          ? _value.supersededById
          : supersededById // ignore: cast_nullable_to_non_nullable
              as String?,
      explosiveType: freezed == explosiveType
          ? _value.explosiveType
          : explosiveType // ignore: cast_nullable_to_non_nullable
              as String?,
      totalExplosiveKg: freezed == totalExplosiveKg
          ? _value.totalExplosiveKg
          : totalExplosiveKg // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDiameterMm: freezed == holeDiameterMm
          ? _value.holeDiameterMm
          : holeDiameterMm // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDepthM: freezed == holeDepthM
          ? _value.holeDepthM
          : holeDepthM // ignore: cast_nullable_to_non_nullable
              as double?,
      burdenM: freezed == burdenM
          ? _value.burdenM
          : burdenM // ignore: cast_nullable_to_non_nullable
              as double?,
      spacingM: freezed == spacingM
          ? _value.spacingM
          : spacingM // ignore: cast_nullable_to_non_nullable
              as double?,
      stemmingM: freezed == stemmingM
          ? _value.stemmingM
          : stemmingM // ignore: cast_nullable_to_non_nullable
              as double?,
      targetP80Mm: freezed == targetP80Mm
          ? _value.targetP80Mm
          : targetP80Mm // ignore: cast_nullable_to_non_nullable
              as double?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$BlastPassportImplCopyWith<$Res>
    implements $BlastPassportCopyWith<$Res> {
  factory _$$BlastPassportImplCopyWith(
          _$BlastPassportImpl value, $Res Function(_$BlastPassportImpl) then) =
      __$$BlastPassportImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'site_section_id') String siteSectionId,
      PassportStatus status,
      @JsonKey(name: 'revision_number') int revisionNumber,
      @JsonKey(name: 'superseded_by_id') String? supersededById,
      @JsonKey(name: 'explosive_type') String? explosiveType,
      @JsonKey(name: 'total_explosive_kg') double? totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') double? holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') double? holeDepthM,
      @JsonKey(name: 'burden_m') double? burdenM,
      @JsonKey(name: 'spacing_m') double? spacingM,
      @JsonKey(name: 'stemming_m') double? stemmingM,
      @JsonKey(name: 'target_p80_mm') double? targetP80Mm});
}

/// @nodoc
class __$$BlastPassportImplCopyWithImpl<$Res>
    extends _$BlastPassportCopyWithImpl<$Res, _$BlastPassportImpl>
    implements _$$BlastPassportImplCopyWith<$Res> {
  __$$BlastPassportImplCopyWithImpl(
      _$BlastPassportImpl _value, $Res Function(_$BlastPassportImpl) _then)
      : super(_value, _then);

  /// Create a copy of BlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? siteSectionId = null,
    Object? status = null,
    Object? revisionNumber = null,
    Object? supersededById = freezed,
    Object? explosiveType = freezed,
    Object? totalExplosiveKg = freezed,
    Object? holeDiameterMm = freezed,
    Object? holeDepthM = freezed,
    Object? burdenM = freezed,
    Object? spacingM = freezed,
    Object? stemmingM = freezed,
    Object? targetP80Mm = freezed,
  }) {
    return _then(_$BlastPassportImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      siteSectionId: null == siteSectionId
          ? _value.siteSectionId
          : siteSectionId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as PassportStatus,
      revisionNumber: null == revisionNumber
          ? _value.revisionNumber
          : revisionNumber // ignore: cast_nullable_to_non_nullable
              as int,
      supersededById: freezed == supersededById
          ? _value.supersededById
          : supersededById // ignore: cast_nullable_to_non_nullable
              as String?,
      explosiveType: freezed == explosiveType
          ? _value.explosiveType
          : explosiveType // ignore: cast_nullable_to_non_nullable
              as String?,
      totalExplosiveKg: freezed == totalExplosiveKg
          ? _value.totalExplosiveKg
          : totalExplosiveKg // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDiameterMm: freezed == holeDiameterMm
          ? _value.holeDiameterMm
          : holeDiameterMm // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDepthM: freezed == holeDepthM
          ? _value.holeDepthM
          : holeDepthM // ignore: cast_nullable_to_non_nullable
              as double?,
      burdenM: freezed == burdenM
          ? _value.burdenM
          : burdenM // ignore: cast_nullable_to_non_nullable
              as double?,
      spacingM: freezed == spacingM
          ? _value.spacingM
          : spacingM // ignore: cast_nullable_to_non_nullable
              as double?,
      stemmingM: freezed == stemmingM
          ? _value.stemmingM
          : stemmingM // ignore: cast_nullable_to_non_nullable
              as double?,
      targetP80Mm: freezed == targetP80Mm
          ? _value.targetP80Mm
          : targetP80Mm // ignore: cast_nullable_to_non_nullable
              as double?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$BlastPassportImpl implements _BlastPassport {
  const _$BlastPassportImpl(
      {required this.id,
      @JsonKey(name: 'site_section_id') required this.siteSectionId,
      required this.status,
      @JsonKey(name: 'revision_number') this.revisionNumber = 1,
      @JsonKey(name: 'superseded_by_id') this.supersededById,
      @JsonKey(name: 'explosive_type') this.explosiveType,
      @JsonKey(name: 'total_explosive_kg') this.totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') this.holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') this.holeDepthM,
      @JsonKey(name: 'burden_m') this.burdenM,
      @JsonKey(name: 'spacing_m') this.spacingM,
      @JsonKey(name: 'stemming_m') this.stemmingM,
      @JsonKey(name: 'target_p80_mm') this.targetP80Mm});

  factory _$BlastPassportImpl.fromJson(Map<String, dynamic> json) =>
      _$$BlastPassportImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'site_section_id')
  final String siteSectionId;
  @override
  final PassportStatus status;
  @override
  @JsonKey(name: 'revision_number')
  final int revisionNumber;
  @override
  @JsonKey(name: 'superseded_by_id')
  final String? supersededById;
  @override
  @JsonKey(name: 'explosive_type')
  final String? explosiveType;
  @override
  @JsonKey(name: 'total_explosive_kg')
  final double? totalExplosiveKg;
  @override
  @JsonKey(name: 'hole_diameter_mm')
  final double? holeDiameterMm;
  @override
  @JsonKey(name: 'hole_depth_m')
  final double? holeDepthM;
  @override
  @JsonKey(name: 'burden_m')
  final double? burdenM;
  @override
  @JsonKey(name: 'spacing_m')
  final double? spacingM;
  @override
  @JsonKey(name: 'stemming_m')
  final double? stemmingM;
  @override
  @JsonKey(name: 'target_p80_mm')
  final double? targetP80Mm;

  @override
  String toString() {
    return 'BlastPassport(id: $id, siteSectionId: $siteSectionId, status: $status, revisionNumber: $revisionNumber, supersededById: $supersededById, explosiveType: $explosiveType, totalExplosiveKg: $totalExplosiveKg, holeDiameterMm: $holeDiameterMm, holeDepthM: $holeDepthM, burdenM: $burdenM, spacingM: $spacingM, stemmingM: $stemmingM, targetP80Mm: $targetP80Mm)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$BlastPassportImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.siteSectionId, siteSectionId) ||
                other.siteSectionId == siteSectionId) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.revisionNumber, revisionNumber) ||
                other.revisionNumber == revisionNumber) &&
            (identical(other.supersededById, supersededById) ||
                other.supersededById == supersededById) &&
            (identical(other.explosiveType, explosiveType) ||
                other.explosiveType == explosiveType) &&
            (identical(other.totalExplosiveKg, totalExplosiveKg) ||
                other.totalExplosiveKg == totalExplosiveKg) &&
            (identical(other.holeDiameterMm, holeDiameterMm) ||
                other.holeDiameterMm == holeDiameterMm) &&
            (identical(other.holeDepthM, holeDepthM) ||
                other.holeDepthM == holeDepthM) &&
            (identical(other.burdenM, burdenM) || other.burdenM == burdenM) &&
            (identical(other.spacingM, spacingM) ||
                other.spacingM == spacingM) &&
            (identical(other.stemmingM, stemmingM) ||
                other.stemmingM == stemmingM) &&
            (identical(other.targetP80Mm, targetP80Mm) ||
                other.targetP80Mm == targetP80Mm));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      siteSectionId,
      status,
      revisionNumber,
      supersededById,
      explosiveType,
      totalExplosiveKg,
      holeDiameterMm,
      holeDepthM,
      burdenM,
      spacingM,
      stemmingM,
      targetP80Mm);

  /// Create a copy of BlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$BlastPassportImplCopyWith<_$BlastPassportImpl> get copyWith =>
      __$$BlastPassportImplCopyWithImpl<_$BlastPassportImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$BlastPassportImplToJson(
      this,
    );
  }
}

abstract class _BlastPassport implements BlastPassport {
  const factory _BlastPassport(
          {required final String id,
          @JsonKey(name: 'site_section_id') required final String siteSectionId,
          required final PassportStatus status,
          @JsonKey(name: 'revision_number') final int revisionNumber,
          @JsonKey(name: 'superseded_by_id') final String? supersededById,
          @JsonKey(name: 'explosive_type') final String? explosiveType,
          @JsonKey(name: 'total_explosive_kg') final double? totalExplosiveKg,
          @JsonKey(name: 'hole_diameter_mm') final double? holeDiameterMm,
          @JsonKey(name: 'hole_depth_m') final double? holeDepthM,
          @JsonKey(name: 'burden_m') final double? burdenM,
          @JsonKey(name: 'spacing_m') final double? spacingM,
          @JsonKey(name: 'stemming_m') final double? stemmingM,
          @JsonKey(name: 'target_p80_mm') final double? targetP80Mm}) =
      _$BlastPassportImpl;

  factory _BlastPassport.fromJson(Map<String, dynamic> json) =
      _$BlastPassportImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'site_section_id')
  String get siteSectionId;
  @override
  PassportStatus get status;
  @override
  @JsonKey(name: 'revision_number')
  int get revisionNumber;
  @override
  @JsonKey(name: 'superseded_by_id')
  String? get supersededById;
  @override
  @JsonKey(name: 'explosive_type')
  String? get explosiveType;
  @override
  @JsonKey(name: 'total_explosive_kg')
  double? get totalExplosiveKg;
  @override
  @JsonKey(name: 'hole_diameter_mm')
  double? get holeDiameterMm;
  @override
  @JsonKey(name: 'hole_depth_m')
  double? get holeDepthM;
  @override
  @JsonKey(name: 'burden_m')
  double? get burdenM;
  @override
  @JsonKey(name: 'spacing_m')
  double? get spacingM;
  @override
  @JsonKey(name: 'stemming_m')
  double? get stemmingM;
  @override
  @JsonKey(name: 'target_p80_mm')
  double? get targetP80Mm;

  /// Create a copy of BlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$BlastPassportImplCopyWith<_$BlastPassportImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

NewBlastPassport _$NewBlastPassportFromJson(Map<String, dynamic> json) {
  return _NewBlastPassport.fromJson(json);
}

/// @nodoc
mixin _$NewBlastPassport {
  @JsonKey(name: 'site_section_id')
  String get siteSectionId => throw _privateConstructorUsedError;
  @JsonKey(name: 'explosive_type')
  String? get explosiveType => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_explosive_kg')
  double? get totalExplosiveKg => throw _privateConstructorUsedError;
  @JsonKey(name: 'hole_diameter_mm')
  double? get holeDiameterMm => throw _privateConstructorUsedError;
  @JsonKey(name: 'hole_depth_m')
  double? get holeDepthM => throw _privateConstructorUsedError;
  @JsonKey(name: 'burden_m')
  double? get burdenM => throw _privateConstructorUsedError;
  @JsonKey(name: 'spacing_m')
  double? get spacingM => throw _privateConstructorUsedError;
  @JsonKey(name: 'stemming_m')
  double? get stemmingM => throw _privateConstructorUsedError;
  @JsonKey(name: 'target_p80_mm')
  double? get targetP80Mm => throw _privateConstructorUsedError;

  /// Serializes this NewBlastPassport to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of NewBlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $NewBlastPassportCopyWith<NewBlastPassport> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $NewBlastPassportCopyWith<$Res> {
  factory $NewBlastPassportCopyWith(
          NewBlastPassport value, $Res Function(NewBlastPassport) then) =
      _$NewBlastPassportCopyWithImpl<$Res, NewBlastPassport>;
  @useResult
  $Res call(
      {@JsonKey(name: 'site_section_id') String siteSectionId,
      @JsonKey(name: 'explosive_type') String? explosiveType,
      @JsonKey(name: 'total_explosive_kg') double? totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') double? holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') double? holeDepthM,
      @JsonKey(name: 'burden_m') double? burdenM,
      @JsonKey(name: 'spacing_m') double? spacingM,
      @JsonKey(name: 'stemming_m') double? stemmingM,
      @JsonKey(name: 'target_p80_mm') double? targetP80Mm});
}

/// @nodoc
class _$NewBlastPassportCopyWithImpl<$Res, $Val extends NewBlastPassport>
    implements $NewBlastPassportCopyWith<$Res> {
  _$NewBlastPassportCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of NewBlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? siteSectionId = null,
    Object? explosiveType = freezed,
    Object? totalExplosiveKg = freezed,
    Object? holeDiameterMm = freezed,
    Object? holeDepthM = freezed,
    Object? burdenM = freezed,
    Object? spacingM = freezed,
    Object? stemmingM = freezed,
    Object? targetP80Mm = freezed,
  }) {
    return _then(_value.copyWith(
      siteSectionId: null == siteSectionId
          ? _value.siteSectionId
          : siteSectionId // ignore: cast_nullable_to_non_nullable
              as String,
      explosiveType: freezed == explosiveType
          ? _value.explosiveType
          : explosiveType // ignore: cast_nullable_to_non_nullable
              as String?,
      totalExplosiveKg: freezed == totalExplosiveKg
          ? _value.totalExplosiveKg
          : totalExplosiveKg // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDiameterMm: freezed == holeDiameterMm
          ? _value.holeDiameterMm
          : holeDiameterMm // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDepthM: freezed == holeDepthM
          ? _value.holeDepthM
          : holeDepthM // ignore: cast_nullable_to_non_nullable
              as double?,
      burdenM: freezed == burdenM
          ? _value.burdenM
          : burdenM // ignore: cast_nullable_to_non_nullable
              as double?,
      spacingM: freezed == spacingM
          ? _value.spacingM
          : spacingM // ignore: cast_nullable_to_non_nullable
              as double?,
      stemmingM: freezed == stemmingM
          ? _value.stemmingM
          : stemmingM // ignore: cast_nullable_to_non_nullable
              as double?,
      targetP80Mm: freezed == targetP80Mm
          ? _value.targetP80Mm
          : targetP80Mm // ignore: cast_nullable_to_non_nullable
              as double?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$NewBlastPassportImplCopyWith<$Res>
    implements $NewBlastPassportCopyWith<$Res> {
  factory _$$NewBlastPassportImplCopyWith(_$NewBlastPassportImpl value,
          $Res Function(_$NewBlastPassportImpl) then) =
      __$$NewBlastPassportImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'site_section_id') String siteSectionId,
      @JsonKey(name: 'explosive_type') String? explosiveType,
      @JsonKey(name: 'total_explosive_kg') double? totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') double? holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') double? holeDepthM,
      @JsonKey(name: 'burden_m') double? burdenM,
      @JsonKey(name: 'spacing_m') double? spacingM,
      @JsonKey(name: 'stemming_m') double? stemmingM,
      @JsonKey(name: 'target_p80_mm') double? targetP80Mm});
}

/// @nodoc
class __$$NewBlastPassportImplCopyWithImpl<$Res>
    extends _$NewBlastPassportCopyWithImpl<$Res, _$NewBlastPassportImpl>
    implements _$$NewBlastPassportImplCopyWith<$Res> {
  __$$NewBlastPassportImplCopyWithImpl(_$NewBlastPassportImpl _value,
      $Res Function(_$NewBlastPassportImpl) _then)
      : super(_value, _then);

  /// Create a copy of NewBlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? siteSectionId = null,
    Object? explosiveType = freezed,
    Object? totalExplosiveKg = freezed,
    Object? holeDiameterMm = freezed,
    Object? holeDepthM = freezed,
    Object? burdenM = freezed,
    Object? spacingM = freezed,
    Object? stemmingM = freezed,
    Object? targetP80Mm = freezed,
  }) {
    return _then(_$NewBlastPassportImpl(
      siteSectionId: null == siteSectionId
          ? _value.siteSectionId
          : siteSectionId // ignore: cast_nullable_to_non_nullable
              as String,
      explosiveType: freezed == explosiveType
          ? _value.explosiveType
          : explosiveType // ignore: cast_nullable_to_non_nullable
              as String?,
      totalExplosiveKg: freezed == totalExplosiveKg
          ? _value.totalExplosiveKg
          : totalExplosiveKg // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDiameterMm: freezed == holeDiameterMm
          ? _value.holeDiameterMm
          : holeDiameterMm // ignore: cast_nullable_to_non_nullable
              as double?,
      holeDepthM: freezed == holeDepthM
          ? _value.holeDepthM
          : holeDepthM // ignore: cast_nullable_to_non_nullable
              as double?,
      burdenM: freezed == burdenM
          ? _value.burdenM
          : burdenM // ignore: cast_nullable_to_non_nullable
              as double?,
      spacingM: freezed == spacingM
          ? _value.spacingM
          : spacingM // ignore: cast_nullable_to_non_nullable
              as double?,
      stemmingM: freezed == stemmingM
          ? _value.stemmingM
          : stemmingM // ignore: cast_nullable_to_non_nullable
              as double?,
      targetP80Mm: freezed == targetP80Mm
          ? _value.targetP80Mm
          : targetP80Mm // ignore: cast_nullable_to_non_nullable
              as double?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$NewBlastPassportImpl implements _NewBlastPassport {
  const _$NewBlastPassportImpl(
      {@JsonKey(name: 'site_section_id') required this.siteSectionId,
      @JsonKey(name: 'explosive_type') this.explosiveType,
      @JsonKey(name: 'total_explosive_kg') this.totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') this.holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') this.holeDepthM,
      @JsonKey(name: 'burden_m') this.burdenM,
      @JsonKey(name: 'spacing_m') this.spacingM,
      @JsonKey(name: 'stemming_m') this.stemmingM,
      @JsonKey(name: 'target_p80_mm') this.targetP80Mm});

  factory _$NewBlastPassportImpl.fromJson(Map<String, dynamic> json) =>
      _$$NewBlastPassportImplFromJson(json);

  @override
  @JsonKey(name: 'site_section_id')
  final String siteSectionId;
  @override
  @JsonKey(name: 'explosive_type')
  final String? explosiveType;
  @override
  @JsonKey(name: 'total_explosive_kg')
  final double? totalExplosiveKg;
  @override
  @JsonKey(name: 'hole_diameter_mm')
  final double? holeDiameterMm;
  @override
  @JsonKey(name: 'hole_depth_m')
  final double? holeDepthM;
  @override
  @JsonKey(name: 'burden_m')
  final double? burdenM;
  @override
  @JsonKey(name: 'spacing_m')
  final double? spacingM;
  @override
  @JsonKey(name: 'stemming_m')
  final double? stemmingM;
  @override
  @JsonKey(name: 'target_p80_mm')
  final double? targetP80Mm;

  @override
  String toString() {
    return 'NewBlastPassport(siteSectionId: $siteSectionId, explosiveType: $explosiveType, totalExplosiveKg: $totalExplosiveKg, holeDiameterMm: $holeDiameterMm, holeDepthM: $holeDepthM, burdenM: $burdenM, spacingM: $spacingM, stemmingM: $stemmingM, targetP80Mm: $targetP80Mm)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$NewBlastPassportImpl &&
            (identical(other.siteSectionId, siteSectionId) ||
                other.siteSectionId == siteSectionId) &&
            (identical(other.explosiveType, explosiveType) ||
                other.explosiveType == explosiveType) &&
            (identical(other.totalExplosiveKg, totalExplosiveKg) ||
                other.totalExplosiveKg == totalExplosiveKg) &&
            (identical(other.holeDiameterMm, holeDiameterMm) ||
                other.holeDiameterMm == holeDiameterMm) &&
            (identical(other.holeDepthM, holeDepthM) ||
                other.holeDepthM == holeDepthM) &&
            (identical(other.burdenM, burdenM) || other.burdenM == burdenM) &&
            (identical(other.spacingM, spacingM) ||
                other.spacingM == spacingM) &&
            (identical(other.stemmingM, stemmingM) ||
                other.stemmingM == stemmingM) &&
            (identical(other.targetP80Mm, targetP80Mm) ||
                other.targetP80Mm == targetP80Mm));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      siteSectionId,
      explosiveType,
      totalExplosiveKg,
      holeDiameterMm,
      holeDepthM,
      burdenM,
      spacingM,
      stemmingM,
      targetP80Mm);

  /// Create a copy of NewBlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$NewBlastPassportImplCopyWith<_$NewBlastPassportImpl> get copyWith =>
      __$$NewBlastPassportImplCopyWithImpl<_$NewBlastPassportImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$NewBlastPassportImplToJson(
      this,
    );
  }
}

abstract class _NewBlastPassport implements NewBlastPassport {
  const factory _NewBlastPassport(
      {@JsonKey(name: 'site_section_id') required final String siteSectionId,
      @JsonKey(name: 'explosive_type') final String? explosiveType,
      @JsonKey(name: 'total_explosive_kg') final double? totalExplosiveKg,
      @JsonKey(name: 'hole_diameter_mm') final double? holeDiameterMm,
      @JsonKey(name: 'hole_depth_m') final double? holeDepthM,
      @JsonKey(name: 'burden_m') final double? burdenM,
      @JsonKey(name: 'spacing_m') final double? spacingM,
      @JsonKey(name: 'stemming_m') final double? stemmingM,
      @JsonKey(name: 'target_p80_mm')
      final double? targetP80Mm}) = _$NewBlastPassportImpl;

  factory _NewBlastPassport.fromJson(Map<String, dynamic> json) =
      _$NewBlastPassportImpl.fromJson;

  @override
  @JsonKey(name: 'site_section_id')
  String get siteSectionId;
  @override
  @JsonKey(name: 'explosive_type')
  String? get explosiveType;
  @override
  @JsonKey(name: 'total_explosive_kg')
  double? get totalExplosiveKg;
  @override
  @JsonKey(name: 'hole_diameter_mm')
  double? get holeDiameterMm;
  @override
  @JsonKey(name: 'hole_depth_m')
  double? get holeDepthM;
  @override
  @JsonKey(name: 'burden_m')
  double? get burdenM;
  @override
  @JsonKey(name: 'spacing_m')
  double? get spacingM;
  @override
  @JsonKey(name: 'stemming_m')
  double? get stemmingM;
  @override
  @JsonKey(name: 'target_p80_mm')
  double? get targetP80Mm;

  /// Create a copy of NewBlastPassport
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$NewBlastPassportImplCopyWith<_$NewBlastPassportImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
