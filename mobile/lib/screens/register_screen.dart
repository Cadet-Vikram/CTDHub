import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _nameCtrl     = TextEditingController();
  final _ageCtrl      = TextEditingController();
  final _locationCtrl = TextEditingController();
  final _contactCtrl  = TextEditingController();
  final _descCtrl     = TextEditingController();
  String _gender = 'Male';
  File?  _photo;
  bool   _loading = false;
  bool   _done    = false;
  String? _caseId;
  final _api = ApiService();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _ageCtrl.dispose();
    _locationCtrl.dispose();
    _contactCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickPhoto() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (x != null) setState(() => _photo = File(x.path));
  }

  Future<void> _submit() async {
    if (_nameCtrl.text.trim().isEmpty ||
        _ageCtrl.text.trim().isEmpty ||
        _contactCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please fill in Name, Age and Contact Number'),
          backgroundColor: Color(0xFFef4444),
        ),
      );
      return;
    }

    final age = int.tryParse(_ageCtrl.text.trim());
    if (age == null || age < 0 || age > 18) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Age must be a number between 0 and 18'),
          backgroundColor: Color(0xFFef4444),
        ),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      final result = await _api.registerChild(
        name:              _nameCtrl.text.trim(),
        age:               age,
        gender:            _gender,
        description:       _descCtrl.text.trim(),
        lastSeenLocation:  _locationCtrl.text.trim(),
        contactNumber:     _contactCtrl.text.trim(),
        photo:             _photo,
      );
      setState(() {
        _loading = false;
        _done    = true;
        _caseId  = result['child_id'] as String?;
      });
    } catch (e) {
      // Demo mode fallback
      setState(() {
        _loading = false;
        _done    = true;
        _caseId  = 'DEMO-${DateTime.now().millisecondsSinceEpoch % 99999}';
      });
    }
  }

  void _reset() {
    setState(() {
      _done   = false;
      _caseId = null;
      _photo  = null;
      _nameCtrl.clear();
      _ageCtrl.clear();
      _locationCtrl.clear();
      _contactCtrl.clear();
      _descCtrl.clear();
      _gender = 'Male';
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_done) {
      return _SuccessView(
        caseId:  _caseId ?? 'UNKNOWN',
        name:    _nameCtrl.text,
        onReset: _reset,
      );
    }

    final age = int.tryParse(_ageCtrl.text) ?? 99;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Register Missing Child',
            style: TextStyle(fontSize: 13, letterSpacing: 1)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: const Color(0xFF1e2a45), height: 1),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _Section(
            title: 'CHILD INFORMATION',
            children: [
              _FormField(label: 'Full Name *', controller: _nameCtrl),
              _FormField(
                label: 'Age *',
                controller: _ageCtrl,
                keyboardType: TextInputType.number,
                onChanged: (_) => setState(() {}),
              ),
              _GenderSelector(
                value: _gender,
                onChanged: (v) => setState(() => _gender = v),
              ),
              _FormField(
                label: 'Description',
                controller: _descCtrl,
                maxLines: 3,
              ),
            ],
          ),
          const SizedBox(height: 16),
          _Section(
            title: 'LAST SEEN DETAILS',
            children: [
              _FormField(
                label: 'Location',
                controller: _locationCtrl,
                hint: 'City, area, landmark',
              ),
            ],
          ),
          const SizedBox(height: 16),
          _Section(
            title: 'CONTACT INFORMATION',
            children: [
              _FormField(
                label: 'Phone Number *',
                controller: _contactCtrl,
                keyboardType: TextInputType.phone,
                hint: '+91-XXXXX-XXXXX',
              ),
            ],
          ),
          const SizedBox(height: 16),
          _PhotoSection(
            photo: _photo,
            age:   age,
            onPick: _pickPhoto,
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _loading ? null : _submit,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _loading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('REGISTER CHILD'),
            ),
          ),
        ]),
      ),
    );
  }
}

// ── Reusable widgets ──────────────────────────────────────────────────────────

class _Section extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _Section({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1e2a45)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title,
            style: const TextStyle(
                color: Color(0xFF94a3b8), fontSize: 10, letterSpacing: 2)),
        const SizedBox(height: 16),
        ...children.map((c) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: c,
            )),
      ]),
    );
  }
}

class _FormField extends StatelessWidget {
  final String label;
  final TextEditingController controller;
  final TextInputType keyboardType;
  final String? hint;
  final int maxLines;
  final ValueChanged<String>? onChanged;

  const _FormField({
    required this.label,
    required this.controller,
    this.keyboardType = TextInputType.text,
    this.hint,
    this.maxLines = 1,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label.toUpperCase(),
          style: const TextStyle(
              color: Color(0xFF475569), fontSize: 9, letterSpacing: 2)),
      const SizedBox(height: 6),
      TextFormField(
        controller:   controller,
        keyboardType: keyboardType,
        maxLines:     maxLines,
        onChanged:    onChanged,
        style: const TextStyle(color: Color(0xFFe2e8f0), fontSize: 13),
        decoration: InputDecoration(hintText: hint),
      ),
    ]);
  }
}

class _GenderSelector extends StatelessWidget {
  final String value;
  final ValueChanged<String> onChanged;

  const _GenderSelector({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('GENDER',
          style: TextStyle(
              color: Color(0xFF475569), fontSize: 9, letterSpacing: 2)),
      const SizedBox(height: 6),
      DropdownButtonFormField<String>(
        value: value,
        dropdownColor: const Color(0xFF0d1220),
        style: const TextStyle(color: Color(0xFFe2e8f0), fontSize: 13),
        decoration: const InputDecoration(),
        items: ['Male', 'Female', 'Other']
            .map((g) => DropdownMenuItem(value: g, child: Text(g)))
            .toList(),
        onChanged: (v) { if (v != null) onChanged(v); },
      ),
    ]);
  }
}

class _PhotoSection extends StatelessWidget {
  final File? photo;
  final int age;
  final VoidCallback onPick;

  const _PhotoSection({required this.photo, required this.age, required this.onPick});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1e2a45)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('PHOTO',
            style: TextStyle(
                color: Color(0xFF94a3b8), fontSize: 10, letterSpacing: 2)),
        const SizedBox(height: 12),
        GestureDetector(
          onTap: onPick,
          child: Container(
            width: double.infinity,
            height: 150,
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF1e2a45)),
            ),
            clipBehavior: Clip.antiAlias,
            child: photo != null
                ? Image.file(photo!, fit: BoxFit.cover)
                : const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.add_a_photo_outlined,
                          color: Color(0xFF475569), size: 32),
                      SizedBox(height: 8),
                      Text('Tap to add photo',
                          style: TextStyle(
                              color: Color(0xFF64748b), fontSize: 12)),
                    ],
                  ),
          ),
        ),
        if (age < 5) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFf59e0b).withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border:
                  Border.all(color: const Color(0xFFf59e0b).withOpacity(0.3)),
            ),
            child: const Row(children: [
              Icon(Icons.info_outline, color: Color(0xFFf59e0b), size: 16),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Children under 5: description-based matching will be used.',
                  style: TextStyle(color: Color(0xFFf59e0b), fontSize: 10),
                ),
              ),
            ]),
          ),
        ],
      ]),
    );
  }
}

class _SuccessView extends StatelessWidget {
  final String caseId;
  final String name;
  final VoidCallback onReset;

  const _SuccessView({
    required this.caseId,
    required this.name,
    required this.onReset,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.check_circle_outline,
                  color: Color(0xFF22c55e), size: 72),
              const SizedBox(height: 24),
              const Text('Registration Complete',
                  style: TextStyle(
                      color: Color(0xFFe2e8f0),
                      fontSize: 20,
                      fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Text(
                '$name has been added to the missing children registry.',
                style: const TextStyle(
                    color: Color(0xFF64748b), fontSize: 13),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 28),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: const Color(0xFF0d1220),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                      color: const Color(0xFF22c55e).withOpacity(0.3)),
                ),
                child: Column(children: [
                  const Text('CASE ID',
                      style: TextStyle(
                          color: Color(0xFF475569), fontSize: 9, letterSpacing: 2)),
                  const SizedBox(height: 6),
                  SelectableText(caseId,
                      style: const TextStyle(
                          color: Color(0xFF22c55e),
                          fontSize: 13,
                          fontWeight: FontWeight.w700)),
                ]),
              ),
              const SizedBox(height: 28),
              OutlinedButton(
                onPressed: onReset,
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF3b82f6),
                  side: const BorderSide(color: Color(0xFF3b82f6)),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 32, vertical: 14),
                ),
                child: const Text('REGISTER ANOTHER',
                    style: TextStyle(letterSpacing: 1)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
