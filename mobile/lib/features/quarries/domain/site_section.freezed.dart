// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'site_section.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

SiteSection _$SiteSectionFromJson(Map<String, dynamic> json) {
  return _SiteSection.fromJson(json);
}

/// @nodoc
mixin _$SiteSection {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'quarry_id')
  String get quarryId => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'block_number')
  String? get blockNumber => throw _privateConstructorUsedError;

  /// Serializes this SiteSection to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of SiteSection
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $SiteSectionCopyWith<SiteSection> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $SiteSectionCopyWith<$Res> {
  factory $SiteSectionCopyWith(
          SiteSection value, $Res Function(SiteSection) then) =
      _$SiteSectionCopyWithImpl<$Res, SiteSection>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'quarry_id') String quarryId,
      String name,
      @JsonKey(name: 'block_number') String? blockNumber});
}

/// @nodoc
class _$SiteSectionCopyWithImpl<$Res, $Val extends SiteSection>
    implements $SiteSectionCopyWith<$Res> {
  _$SiteSectionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of SiteSection
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? quarryId = null,
    Object? name = null,
    Object? blockNumber = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      quarryId: null == quarryId
          ? _value.quarryId
          : quarryId // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      blockNumber: freezed == blockNumber
          ? _value.blockNumber
          : blockNumber // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$SiteSectionImplCopyWith<$Res>
    implements $SiteSectionCopyWith<$Res> {
  factory _$$SiteSectionImplCopyWith(
          _$SiteSectionImpl value, $Res Function(_$SiteSectionImpl) then) =
      __$$SiteSectionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'quarry_id') String quarryId,
      String name,
      @JsonKey(name: 'block_number') String? blockNumber});
}

/// @nodoc
class __$$SiteSectionImplCopyWithImpl<$Res>
    extends _$SiteSectionCopyWithImpl<$Res, _$SiteSectionImpl>
    implements _$$SiteSectionImplCopyWith<$Res> {
  __$$SiteSectionImplCopyWithImpl(
      _$SiteSectionImpl _value, $Res Function(_$SiteSectionImpl) _then)
      : super(_value, _then);

  /// Create a copy of SiteSection
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? quarryId = null,
    Object? name = null,
    Object? blockNumber = freezed,
  }) {
    return _then(_$SiteSectionImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      quarryId: null == quarryId
          ? _value.quarryId
          : quarryId // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      blockNumber: freezed == blockNumber
          ? _value.blockNumber
          : blockNumber // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$SiteSectionImpl implements _SiteSection {
  const _$SiteSectionImpl(
      {required this.id,
      @JsonKey(name: 'quarry_id') required this.quarryId,
      required this.name,
      @JsonKey(name: 'block_number') this.blockNumber});

  factory _$SiteSectionImpl.fromJson(Map<String, dynamic> json) =>
      _$$SiteSectionImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'quarry_id')
  final String quarryId;
  @override
  final String name;
  @override
  @JsonKey(name: 'block_number')
  final String? blockNumber;

  @override
  String toString() {
    return 'SiteSection(id: $id, quarryId: $quarryId, name: $name, blockNumber: $blockNumber)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$SiteSectionImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.quarryId, quarryId) ||
                other.quarryId == quarryId) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.blockNumber, blockNumber) ||
                other.blockNumber == blockNumber));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, quarryId, name, blockNumber);

  /// Create a copy of SiteSection
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$SiteSectionImplCopyWith<_$SiteSectionImpl> get copyWith =>
      __$$SiteSectionImplCopyWithImpl<_$SiteSectionImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$SiteSectionImplToJson(
      this,
    );
  }
}

abstract class _SiteSection implements SiteSection {
  const factory _SiteSection(
          {required final String id,
          @JsonKey(name: 'quarry_id') required final String quarryId,
          required final String name,
          @JsonKey(name: 'block_number') final String? blockNumber}) =
      _$SiteSectionImpl;

  factory _SiteSection.fromJson(Map<String, dynamic> json) =
      _$SiteSectionImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'quarry_id')
  String get quarryId;
  @override
  String get name;
  @override
  @JsonKey(name: 'block_number')
  String? get blockNumber;

  /// Create a copy of SiteSection
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$SiteSectionImplCopyWith<_$SiteSectionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
