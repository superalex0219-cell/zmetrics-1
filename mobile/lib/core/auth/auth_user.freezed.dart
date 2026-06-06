// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'auth_user.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

AuthUser _$AuthUserFromJson(Map<String, dynamic> json) {
  return _AuthUser.fromJson(json);
}

/// @nodoc
mixin _$AuthUser {
  String get id => throw _privateConstructorUsedError;
  String get displayName => throw _privateConstructorUsedError;
  String? get email => throw _privateConstructorUsedError;

  /// Keycloak `realm_access.roles` (e.g. `zmetrics-blaster`). Used for coarse
  /// UI gating only — the backend enforces the real per-quarry access.
  List<String> get realmRoles => throw _privateConstructorUsedError;

  /// Serializes this AuthUser to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AuthUser
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AuthUserCopyWith<AuthUser> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AuthUserCopyWith<$Res> {
  factory $AuthUserCopyWith(AuthUser value, $Res Function(AuthUser) then) =
      _$AuthUserCopyWithImpl<$Res, AuthUser>;
  @useResult
  $Res call(
      {String id, String displayName, String? email, List<String> realmRoles});
}

/// @nodoc
class _$AuthUserCopyWithImpl<$Res, $Val extends AuthUser>
    implements $AuthUserCopyWith<$Res> {
  _$AuthUserCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AuthUser
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? displayName = null,
    Object? email = freezed,
    Object? realmRoles = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      displayName: null == displayName
          ? _value.displayName
          : displayName // ignore: cast_nullable_to_non_nullable
              as String,
      email: freezed == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String?,
      realmRoles: null == realmRoles
          ? _value.realmRoles
          : realmRoles // ignore: cast_nullable_to_non_nullable
              as List<String>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AuthUserImplCopyWith<$Res>
    implements $AuthUserCopyWith<$Res> {
  factory _$$AuthUserImplCopyWith(
          _$AuthUserImpl value, $Res Function(_$AuthUserImpl) then) =
      __$$AuthUserImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id, String displayName, String? email, List<String> realmRoles});
}

/// @nodoc
class __$$AuthUserImplCopyWithImpl<$Res>
    extends _$AuthUserCopyWithImpl<$Res, _$AuthUserImpl>
    implements _$$AuthUserImplCopyWith<$Res> {
  __$$AuthUserImplCopyWithImpl(
      _$AuthUserImpl _value, $Res Function(_$AuthUserImpl) _then)
      : super(_value, _then);

  /// Create a copy of AuthUser
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? displayName = null,
    Object? email = freezed,
    Object? realmRoles = null,
  }) {
    return _then(_$AuthUserImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      displayName: null == displayName
          ? _value.displayName
          : displayName // ignore: cast_nullable_to_non_nullable
              as String,
      email: freezed == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String?,
      realmRoles: null == realmRoles
          ? _value._realmRoles
          : realmRoles // ignore: cast_nullable_to_non_nullable
              as List<String>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$AuthUserImpl extends _AuthUser {
  const _$AuthUserImpl(
      {required this.id,
      required this.displayName,
      this.email,
      final List<String> realmRoles = const <String>[]})
      : _realmRoles = realmRoles,
        super._();

  factory _$AuthUserImpl.fromJson(Map<String, dynamic> json) =>
      _$$AuthUserImplFromJson(json);

  @override
  final String id;
  @override
  final String displayName;
  @override
  final String? email;

  /// Keycloak `realm_access.roles` (e.g. `zmetrics-blaster`). Used for coarse
  /// UI gating only — the backend enforces the real per-quarry access.
  final List<String> _realmRoles;

  /// Keycloak `realm_access.roles` (e.g. `zmetrics-blaster`). Used for coarse
  /// UI gating only — the backend enforces the real per-quarry access.
  @override
  @JsonKey()
  List<String> get realmRoles {
    if (_realmRoles is EqualUnmodifiableListView) return _realmRoles;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_realmRoles);
  }

  @override
  String toString() {
    return 'AuthUser(id: $id, displayName: $displayName, email: $email, realmRoles: $realmRoles)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AuthUserImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.displayName, displayName) ||
                other.displayName == displayName) &&
            (identical(other.email, email) || other.email == email) &&
            const DeepCollectionEquality()
                .equals(other._realmRoles, _realmRoles));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, displayName, email,
      const DeepCollectionEquality().hash(_realmRoles));

  /// Create a copy of AuthUser
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AuthUserImplCopyWith<_$AuthUserImpl> get copyWith =>
      __$$AuthUserImplCopyWithImpl<_$AuthUserImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AuthUserImplToJson(
      this,
    );
  }
}

abstract class _AuthUser extends AuthUser {
  const factory _AuthUser(
      {required final String id,
      required final String displayName,
      final String? email,
      final List<String> realmRoles}) = _$AuthUserImpl;
  const _AuthUser._() : super._();

  factory _AuthUser.fromJson(Map<String, dynamic> json) =
      _$AuthUserImpl.fromJson;

  @override
  String get id;
  @override
  String get displayName;
  @override
  String? get email;

  /// Keycloak `realm_access.roles` (e.g. `zmetrics-blaster`). Used for coarse
  /// UI gating only — the backend enforces the real per-quarry access.
  @override
  List<String> get realmRoles;

  /// Create a copy of AuthUser
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AuthUserImplCopyWith<_$AuthUserImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
