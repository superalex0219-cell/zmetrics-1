// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'quarry_access.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

QuarryAccess _$QuarryAccessFromJson(Map<String, dynamic> json) {
  return _QuarryAccess.fromJson(json);
}

/// @nodoc
mixin _$QuarryAccess {
  @JsonKey(name: 'quarry_id')
  String get quarryId => throw _privateConstructorUsedError;
  @JsonKey(name: 'quarry_name')
  String get quarryName => throw _privateConstructorUsedError;
  @JsonKey(name: 'role_name')
  String get roleName => throw _privateConstructorUsedError;
  @JsonKey(name: 'role_level')
  int get roleLevel => throw _privateConstructorUsedError;

  /// Serializes this QuarryAccess to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of QuarryAccess
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuarryAccessCopyWith<QuarryAccess> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuarryAccessCopyWith<$Res> {
  factory $QuarryAccessCopyWith(
          QuarryAccess value, $Res Function(QuarryAccess) then) =
      _$QuarryAccessCopyWithImpl<$Res, QuarryAccess>;
  @useResult
  $Res call(
      {@JsonKey(name: 'quarry_id') String quarryId,
      @JsonKey(name: 'quarry_name') String quarryName,
      @JsonKey(name: 'role_name') String roleName,
      @JsonKey(name: 'role_level') int roleLevel});
}

/// @nodoc
class _$QuarryAccessCopyWithImpl<$Res, $Val extends QuarryAccess>
    implements $QuarryAccessCopyWith<$Res> {
  _$QuarryAccessCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuarryAccess
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? quarryId = null,
    Object? quarryName = null,
    Object? roleName = null,
    Object? roleLevel = null,
  }) {
    return _then(_value.copyWith(
      quarryId: null == quarryId
          ? _value.quarryId
          : quarryId // ignore: cast_nullable_to_non_nullable
              as String,
      quarryName: null == quarryName
          ? _value.quarryName
          : quarryName // ignore: cast_nullable_to_non_nullable
              as String,
      roleName: null == roleName
          ? _value.roleName
          : roleName // ignore: cast_nullable_to_non_nullable
              as String,
      roleLevel: null == roleLevel
          ? _value.roleLevel
          : roleLevel // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuarryAccessImplCopyWith<$Res>
    implements $QuarryAccessCopyWith<$Res> {
  factory _$$QuarryAccessImplCopyWith(
          _$QuarryAccessImpl value, $Res Function(_$QuarryAccessImpl) then) =
      __$$QuarryAccessImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'quarry_id') String quarryId,
      @JsonKey(name: 'quarry_name') String quarryName,
      @JsonKey(name: 'role_name') String roleName,
      @JsonKey(name: 'role_level') int roleLevel});
}

/// @nodoc
class __$$QuarryAccessImplCopyWithImpl<$Res>
    extends _$QuarryAccessCopyWithImpl<$Res, _$QuarryAccessImpl>
    implements _$$QuarryAccessImplCopyWith<$Res> {
  __$$QuarryAccessImplCopyWithImpl(
      _$QuarryAccessImpl _value, $Res Function(_$QuarryAccessImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuarryAccess
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? quarryId = null,
    Object? quarryName = null,
    Object? roleName = null,
    Object? roleLevel = null,
  }) {
    return _then(_$QuarryAccessImpl(
      quarryId: null == quarryId
          ? _value.quarryId
          : quarryId // ignore: cast_nullable_to_non_nullable
              as String,
      quarryName: null == quarryName
          ? _value.quarryName
          : quarryName // ignore: cast_nullable_to_non_nullable
              as String,
      roleName: null == roleName
          ? _value.roleName
          : roleName // ignore: cast_nullable_to_non_nullable
              as String,
      roleLevel: null == roleLevel
          ? _value.roleLevel
          : roleLevel // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$QuarryAccessImpl extends _QuarryAccess {
  const _$QuarryAccessImpl(
      {@JsonKey(name: 'quarry_id') required this.quarryId,
      @JsonKey(name: 'quarry_name') required this.quarryName,
      @JsonKey(name: 'role_name') required this.roleName,
      @JsonKey(name: 'role_level') required this.roleLevel})
      : super._();

  factory _$QuarryAccessImpl.fromJson(Map<String, dynamic> json) =>
      _$$QuarryAccessImplFromJson(json);

  @override
  @JsonKey(name: 'quarry_id')
  final String quarryId;
  @override
  @JsonKey(name: 'quarry_name')
  final String quarryName;
  @override
  @JsonKey(name: 'role_name')
  final String roleName;
  @override
  @JsonKey(name: 'role_level')
  final int roleLevel;

  @override
  String toString() {
    return 'QuarryAccess(quarryId: $quarryId, quarryName: $quarryName, roleName: $roleName, roleLevel: $roleLevel)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuarryAccessImpl &&
            (identical(other.quarryId, quarryId) ||
                other.quarryId == quarryId) &&
            (identical(other.quarryName, quarryName) ||
                other.quarryName == quarryName) &&
            (identical(other.roleName, roleName) ||
                other.roleName == roleName) &&
            (identical(other.roleLevel, roleLevel) ||
                other.roleLevel == roleLevel));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, quarryId, quarryName, roleName, roleLevel);

  /// Create a copy of QuarryAccess
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuarryAccessImplCopyWith<_$QuarryAccessImpl> get copyWith =>
      __$$QuarryAccessImplCopyWithImpl<_$QuarryAccessImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$QuarryAccessImplToJson(
      this,
    );
  }
}

abstract class _QuarryAccess extends QuarryAccess {
  const factory _QuarryAccess(
          {@JsonKey(name: 'quarry_id') required final String quarryId,
          @JsonKey(name: 'quarry_name') required final String quarryName,
          @JsonKey(name: 'role_name') required final String roleName,
          @JsonKey(name: 'role_level') required final int roleLevel}) =
      _$QuarryAccessImpl;
  const _QuarryAccess._() : super._();

  factory _QuarryAccess.fromJson(Map<String, dynamic> json) =
      _$QuarryAccessImpl.fromJson;

  @override
  @JsonKey(name: 'quarry_id')
  String get quarryId;
  @override
  @JsonKey(name: 'quarry_name')
  String get quarryName;
  @override
  @JsonKey(name: 'role_name')
  String get roleName;
  @override
  @JsonKey(name: 'role_level')
  int get roleLevel;

  /// Create a copy of QuarryAccess
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuarryAccessImplCopyWith<_$QuarryAccessImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
