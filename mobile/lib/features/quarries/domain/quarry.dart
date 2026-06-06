import 'package:freezed_annotation/freezed_annotation.dart';

part 'quarry.freezed.dart';
part 'quarry.g.dart';

/// Quarry (карьер) — top of the entity hierarchy.
@freezed
class Quarry with _$Quarry {
  const factory Quarry({
    required String id,
    required String name,
    double? latitude,
    double? longitude,
  }) = _Quarry;

  factory Quarry.fromJson(Map<String, dynamic> json) => _$QuarryFromJson(json);
}
