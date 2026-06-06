import 'package:flutter/material.dart';

/// Prominent banner shown on any report produced by the mock CV pipeline.
///
/// SAFETY: reports MUST display the analysis method prominently and synthetic
/// results MUST be labelled "⚠ Mock pipeline — results are synthetic"
/// (rules/product-safety.md AI/ML labelling).
class MockPipelineBadge extends StatelessWidget {
  const MockPipelineBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.shade100,
        border: Border.all(color: Colors.amber.shade700),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: Color(0xFF8A6D00)),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '⚠ Mock pipeline — results are synthetic',
              style: TextStyle(
                color: Color(0xFF8A6D00),
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
