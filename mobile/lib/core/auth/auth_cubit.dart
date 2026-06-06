import 'package:flutter_bloc/flutter_bloc.dart';

import 'auth_repository.dart';
import 'auth_user.dart';

/// Authentication state. Native Dart 3 sealed class (exhaustive `switch`).
sealed class AuthState {
  const AuthState();
}

class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthInProgress extends AuthState {
  const AuthInProgress();
}

class Authenticated extends AuthState {
  const Authenticated(this.user);
  final AuthUser user;
}

class Unauthenticated extends AuthState {
  const Unauthenticated({this.message});

  /// Optional reason (e.g. sign-in failed), shown on the login screen.
  final String? message;
}

class AuthCubit extends Cubit<AuthState> {
  AuthCubit(this._repo) : super(const AuthInitial());

  final AuthRepository _repo;

  /// Restores a session on startup.
  Future<void> restore() async {
    emit(const AuthInProgress());
    final user = await _repo.restore();
    emit(user == null ? const Unauthenticated() : Authenticated(user));
  }

  Future<void> signIn({String? username, String? password}) async {
    emit(const AuthInProgress());
    try {
      final user = await _repo.signIn(username: username, password: password);
      emit(Authenticated(user));
    } catch (e) {
      emit(Unauthenticated(message: e.toString()));
    }
  }

  Future<void> signOut() async {
    await _repo.signOut();
    emit(const Unauthenticated());
  }

  /// Triggered when a token refresh fails on a 401 (see AuthEventBus): clear the
  /// session and surface a message so the router sends the user to /login.
  Future<void> handleSessionExpired() async {
    await _repo.signOut();
    emit(const Unauthenticated(message: 'Your session expired. Please sign in again.'));
  }
}
