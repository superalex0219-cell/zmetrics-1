/// Parses a list endpoint response into `List<T>`.
///
/// The implemented backend returns a **bare JSON array** for list endpoints
/// (`response_model=list[...]`), but tolerate a `{"items": [...]}` envelope too
/// in case a future endpoint paginates (see api_contract.md / TASK handoff §5).
List<T> parseJsonList<T>(
  dynamic data,
  T Function(Map<String, dynamic>) fromItem,
) {
  final List<dynamic> raw;
  if (data is List) {
    raw = data;
  } else if (data is Map<String, dynamic> && data['items'] is List) {
    raw = data['items'] as List<dynamic>;
  } else {
    raw = const [];
  }
  return raw
      .map((e) => fromItem(e as Map<String, dynamic>))
      .toList(growable: false);
}
