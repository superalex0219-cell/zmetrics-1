import 'package:freezed_annotation/freezed_annotation.dart';

/// BlastPassport (паспорт БВР) lifecycle. JSON values match the backend
/// `PassportStatus` enum (lowercase). State machine (docs/domain_model.md):
///
///   DRAFT → SUBMITTED → APPROVED → ACTIVE → COMPLETED
///   (+ SUBMITTED → DRAFT return, APPROVED → SUPERSEDED on revision, → CANCELLED)
///
/// SAFETY: transitions are driven only by explicit human HTTP actions; the
/// client never auto-advances state (rules/product-safety.md).
@JsonEnum()
enum PassportStatus {
  @JsonValue('draft')
  draft,
  @JsonValue('submitted')
  submitted,
  @JsonValue('approved')
  approved,
  @JsonValue('active')
  active,
  @JsonValue('completed')
  completed,
  @JsonValue('cancelled')
  cancelled,
  @JsonValue('superseded')
  superseded;

  String get label => switch (this) {
        PassportStatus.draft => 'Draft',
        PassportStatus.submitted => 'Submitted',
        PassportStatus.approved => 'Approved',
        PassportStatus.active => 'Active',
        PassportStatus.completed => 'Completed',
        PassportStatus.cancelled => 'Cancelled',
        PassportStatus.superseded => 'Superseded',
      };

  /// Whether a blaster may submit this passport (DRAFT → SUBMITTED).
  bool get canSubmit => this == PassportStatus.draft;

  /// Whether an admin may approve this passport (SUBMITTED → APPROVED).
  bool get canApprove => this == PassportStatus.submitted;

  /// Whether a blaster may create a new revision (APPROVED/ACTIVE → SUPERSEDED).
  bool get canRevise =>
      this == PassportStatus.approved || this == PassportStatus.active;

  /// Whether an admin may complete this passport (ACTIVE → COMPLETED).
  bool get canComplete => this == PassportStatus.active;
}
