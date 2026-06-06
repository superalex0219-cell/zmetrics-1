/// Envelope for list endpoints: {"items": [...], "total", "page", "page_size"}
/// (see docs/api_contract.md pagination).
class Paginated<T> {
  const Paginated({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<T> items;
  final int total;
  final int page;
  final int pageSize;

  factory Paginated.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) fromItem,
  ) {
    final rawItems = (json['items'] as List<dynamic>? ?? const []);
    return Paginated<T>(
      items: rawItems
          .map((e) => fromItem(e as Map<String, dynamic>))
          .toList(growable: false),
      total: (json['total'] as num?)?.toInt() ?? rawItems.length,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? rawItems.length,
    );
  }
}
