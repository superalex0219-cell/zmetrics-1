import 'package:freezed_annotation/freezed_annotation.dart';

part 'site_section.freezed.dart';
part 'site_section.g.dart';

/// SiteSection (участок/блок) — a blast block within a [Quarry].
@freezed
class SiteSection with _$SiteSection {
  const factory SiteSection({
    required String id,
    @JsonKey(name: 'quarry_id') required String quarryId,
    required String name,
    @JsonKey(name: 'block_number') String? blockNumber,
  }) = _SiteSection;

  factory SiteSection.fromJson(Map<String, dynamic> json) =>
      _$SiteSectionFromJson(json);
}
