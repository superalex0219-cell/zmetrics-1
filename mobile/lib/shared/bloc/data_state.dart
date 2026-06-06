/// Generic async state for list/detail screens. Native Dart 3 sealed class so
/// `switch` over it is exhaustive at compile time.
sealed class DataState<T> {
  const DataState();
}

class DataLoading<T> extends DataState<T> {
  const DataLoading();
}

class DataLoaded<T> extends DataState<T> {
  const DataLoaded(this.value);
  final T value;
}

class DataFailure<T> extends DataState<T> {
  const DataFailure(this.message);
  final String message;
}
