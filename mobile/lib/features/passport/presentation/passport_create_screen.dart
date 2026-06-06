import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../features/quarries/data/quarry_repository.dart';
import '../../../features/quarries/domain/site_section.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/passport_list_cubit.dart';
import '../domain/blast_passport.dart';

/// Manual blast-passport entry form.
///
/// SAFETY (rules/product-safety.md hard limit #4): every field starts EMPTY.
/// Nothing here is pre-filled from AI recommendations — the blaster types the
/// blast design values manually.
class PassportCreateScreen extends StatefulWidget {
  const PassportCreateScreen({super.key, required this.quarryId});

  final String quarryId;

  @override
  State<PassportCreateScreen> createState() => _PassportCreateScreenState();
}

class _PassportCreateScreenState extends State<PassportCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _explosiveType = TextEditingController();
  final _totalExplosiveKg = TextEditingController();
  final _holeDiameterMm = TextEditingController();
  final _holeDepthM = TextEditingController();
  final _burdenM = TextEditingController();
  final _spacingM = TextEditingController();
  final _stemmingM = TextEditingController();
  final _targetP80Mm = TextEditingController();

  late Future<List<SiteSection>> _sectionsFuture;
  String? _sectionId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _sectionsFuture =
        context.read<QuarryRepository>().listSections(widget.quarryId);
  }

  @override
  void dispose() {
    for (final c in [
      _explosiveType,
      _totalExplosiveKg,
      _holeDiameterMm,
      _holeDepthM,
      _burdenM,
      _spacingM,
      _stemmingM,
      _targetP80Mm,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'New passport (БВР)',
      body: FutureBuilder<List<SiteSection>>(
        future: _sectionsFuture,
        builder: (context, snap) {
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final sections = snap.data!;
          _sectionId ??= sections.isNotEmpty ? sections.first.id : null;
          return Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'Enter all parameters manually. Values are NOT pre-filled '
                    'from AI recommendations — the licensed blaster is '
                    'responsible for the design.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
                DropdownButtonFormField<String>(
                  initialValue: _sectionId,
                  decoration: const InputDecoration(labelText: 'Site section'),
                  items: [
                    for (final s in sections)
                      DropdownMenuItem(
                        value: s.id,
                        child: Text('${s.name} (${s.blockNumber ?? '—'})'),
                      ),
                  ],
                  validator: (v) => v == null ? 'Select a section' : null,
                  onChanged: (v) => setState(() => _sectionId = v),
                ),
                _text(_explosiveType, 'Explosive type'),
                _number(_totalExplosiveKg, 'Total explosive (kg)'),
                _number(_holeDiameterMm, 'Hole diameter (mm)'),
                _number(_holeDepthM, 'Hole depth (m)'),
                _number(_burdenM, 'Burden (m)'),
                _number(_spacingM, 'Spacing (m)'),
                _number(_stemmingM, 'Stemming (m)'),
                _number(_targetP80Mm, 'Target P80 (mm)'),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: _saving ? null : _submit,
                  icon: _saving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.save),
                  label: const Text('Create draft'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _text(TextEditingController c, String label) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: TextFormField(
          controller: c,
          decoration: InputDecoration(labelText: label),
        ),
      );

  Widget _number(TextEditingController c, String label) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: TextFormField(
          controller: c,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
          ],
          decoration: InputDecoration(labelText: label),
          validator: (v) {
            if (v == null || v.isEmpty) return null; // optional
            return double.tryParse(v) == null ? 'Invalid number' : null;
          },
        ),
      );

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    setState(() => _saving = true);
    try {
      await context.read<PassportListCubit>().create(
            NewBlastPassport(
              siteSectionId: _sectionId!,
              explosiveType: _explosiveType.text.trim().isEmpty
                  ? null
                  : _explosiveType.text.trim(),
              totalExplosiveKg: double.tryParse(_totalExplosiveKg.text),
              holeDiameterMm: double.tryParse(_holeDiameterMm.text),
              holeDepthM: double.tryParse(_holeDepthM.text),
              burdenM: double.tryParse(_burdenM.text),
              spacingM: double.tryParse(_spacingM.text),
              stemmingM: double.tryParse(_stemmingM.text),
              targetP80Mm: double.tryParse(_targetP80Mm.text),
            ),
          );
      messenger.showSnackBar(
        const SnackBar(content: Text('Draft passport created')),
      );
      router.go('/quarries/${widget.quarryId}/passports');
    } catch (e) {
      setState(() => _saving = false);
      messenger.showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }
}
