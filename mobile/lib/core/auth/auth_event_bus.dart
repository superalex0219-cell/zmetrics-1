import 'dart:async';

/// Bridges the network layer (Dio interceptor) and [AuthCubit]: when a token
/// refresh fails on a 401, the interceptor fires [notifySessionExpired] and the
/// app signs the user out and routes to /login.
class AuthEventBus {
  final _controller = StreamController<void>.broadcast();

  Stream<void> get onSessionExpired => _controller.stream;

  void notifySessionExpired() {
    if (!_controller.isClosed) _controller.add(null);
  }

  Future<void> dispose() => _controller.close();
}
