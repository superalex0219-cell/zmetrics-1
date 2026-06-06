// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'quarry.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

Quarry _$QuarryFromJson(Map<String, dynamic> json) {
  return _Quarry.fromJson(json);
}

/// @nodoc
mixin _$Quarry {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  double? get latitude => throw _privateConstructorUsedError;
  double? get longitude => throw _privateConstructorUsedError;

  /// Serializes this Quarry to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Quarry
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuarryCopyWith<Quarry> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuarryCopyWith<$Res> {
  factory $QuarryCopyWith(Quarry value, $Res Function(Quarry) then) =
      _$QuarryCopyWithImpl<$Res, Quarry>;
  @useResult
  $Res call({String id, String name, double? latitude, double? longitude});
}

/// @nodoc
class _$QuarryCopyWithImpl<$Res, $Val extends Quarry>
    implements $QuarryCopyWith<$Res> {
  _$QuarryCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Quarry
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? latitude = freezed,
    Object? longitude = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      latitude: freezed == latitude
          ? _value.latitude
          : latitude // ignore: cast_nullable_to_non_nullable
              as double?,
      longitude: freezed == longitude
          ? _value.longitude
          : longitude // ignore: cast_nullable_to_non_nullable
              as double?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuarryImplCopyWith<$Res> implements $QuarryCopyWith<$Res> {
  factory _$$QuarryImplCopyWith(
          _$QuarryImpl value, $Res Function(_$QuarryImpl) then) =
      __$$QuarryImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String id, String name, double? latitude, double? longitude});
}

/// @nodoc
class __$$QuarryImplCopyWithImpl<$Res>
    extends _$QuarryCopyWithImpl<$Res, _$QuarryImpl>
    implements _$$QuarryImplCopyWith<$Res> {
  __$$QuarryImplCopyWithImpl(
      _$QuarryImpl _value, $Res Function(_$QuarryImpl) _then)
      : super(_value, _then);

  /// Create a copy of Quarry
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? latitude = freezed,
    Object? longitude = freezed,
  }) {
    return _then(_$QuarryImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      latitude: freezed == latitude
          ? _value.latitude
          : latitude // ignore: cast_nullable_to_non_nullable
              as double?,
      longitude: freezed == longitude
          ? _value.longitude
          : longitude // ignore: cast_nullable_to_non_nullable
              as double?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$QuarryImpl implements _Quarry {
  const _$QuarryImpl(
      {required this.id, required this.name, this.latitude, this.longitude});

  factory _$QuarryImpl.fromJson(Map<String, dynamic> json) =>
      _$$QuarryImplFromJson(json);

  @override
  final String id;
  @override
  final String name;
  @override
  final double? latitude;
  @override
  final double? longitude;

  @override
  String toString() {
    return 'Quarry(id: $id, name: $name, latitude: $latitude, longitude: $longitude)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuarryImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.latitude, latitude) ||
                other.latitude == latitude) &&
            (identical(other.longitude, longitude) ||
                other.longitude == longitude));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, name, latitude, longitude);

  /// Create a copy of Quarry
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuarryImplCopyWith<_$QuarryImpl> get copyWith =>
      __$$QuarryImplCopyWithImpl<_$QuarryImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$QuarryImplToJson(
      this,
    );
  }
}

abstract class _Quarry implements Quarry {
  const factory _Quarry(
      {required final String id,
      required final String name,
      final double? latitude,
      final double? longitude}) = _$QuarryImpl;

  factory _Quarry.fromJson(Map<String, dynamic> json) = _$QuarryImpl.fromJson;

  @override
  String get id;
  @override
  String get name;
  @override
  double? get latitude;
  @override
  double? get longitude;

  /// Create a copy of Quarry
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuarryImplCopyWith<_$QuarryImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
