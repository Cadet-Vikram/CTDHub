import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import '../models/search_result.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  File? _image;
  SearchResult? _result;
  bool _loading = false;
  final _api    = ApiService();
  final _picker = ImagePicker();

  Future<void> _pickImage(ImageSource source) async {
    final xFile = await _picker.pickImage(source: source, imageQuality: 85);
    if (xFile == null) return;
    setState(() {
      _image  = File(xFile.path);
      _result = null;
    });
  }

  Future<void> _search() async {
    if (_image == null) return;
    setState(() => _loading = true);
    try {
      final result = await _api.searchByFace(photo: _image!);
      setState(() {
        _result  = result;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Search failed: ${e.toString()}'),
            backgroundColor: const Color(0xFFef4444),
          ),
        );
      }
    }
  }

  void _showPickerSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0d1220),
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: Color(0xFF3b82f6)),
              title: const Text('Camera', style: TextStyle(color: Color(0xFFe2e8f0))),
              onTap: () { Navigator.pop(context); _pickImage(ImageSource.camera); },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: Color(0xFF3b82f6)),
              title: const Text('Gallery', style: TextStyle(color: Color(0xFFe2e8f0))),
              onTap: () { Navigator.pop(context); _pickImage(ImageSource.gallery); },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Face Search', style: TextStyle(fontSize: 14, letterSpacing: 2)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: const Color(0xFF1e2a45), height: 1),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // ── Upload zone ─────────────────────────────────────────────────
            GestureDetector(
              onTap: _showPickerSheet,
              child: Container(
                width: double.infinity,
                height: 240,
                decoration: BoxDecoration(
                  color: const Color(0xFF0d1220),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFF1e2a45),
                    style: BorderStyle.solid,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: _image != null
                    ? Image.file(_image!, fit: BoxFit.contain)
                    : const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_photo_alternate_outlined,
                              color: Color(0xFF475569), size: 48),
                          SizedBox(height: 12),
                          Text('Tap to add photo',
                              style: TextStyle(color: Color(0xFF64748b), fontSize: 13)),
                          SizedBox(height: 4),
                          Text('CAMERA OR GALLERY',
                              style: TextStyle(
                                  color: Color(0xFF475569), fontSize: 10, letterSpacing: 2)),
                        ],
                      ),
              ),
            ),

            const SizedBox(height: 14),

            // ── Action buttons ───────────────────────────────────────────────
            if (_image != null)
              Row(children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _showPickerSheet,
                    icon: const Icon(Icons.camera_alt_outlined, size: 16),
                    label: const Text('RETAKE'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF64748b),
                      side: const BorderSide(color: Color(0xFF1e2a45)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _loading ? null : _search,
                    icon: _loading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.search, size: 16),
                    label: Text(_loading ? 'SEARCHING...' : 'SEARCH'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF16a34a),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ]),

            const SizedBox(height: 24),

            // ── Results ──────────────────────────────────────────────────────
            if (_loading)
              const Column(children: [
                CircularProgressIndicator(color: Color(0xFF3b82f6)),
                SizedBox(height: 14),
                Text('Analysing with ArcFace...',
                    style: TextStyle(color: Color(0xFF64748b), fontSize: 12)),
              ])
            else if (_result != null) ...[
              _ResultHeader(result: _result!),
              const SizedBox(height: 12),
              if (_result!.matches.isEmpty)
                _EmptyResults()
              else
                ...(_result!.matches.map((m) => _MatchCard(match: m))),
            ] else
              _PipelineInfo(),
          ],
        ),
      ),
    );
  }
}

class _ResultHeader extends StatelessWidget {
  final SearchResult result;
  const _ResultHeader({required this.result});

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Container(
        width: 8,
        height: 8,
        decoration: const BoxDecoration(
          color: Color(0xFF22c55e), shape: BoxShape.circle,
        ),
      ),
      const SizedBox(width: 8),
      Text(
        result.message,
        style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 11, letterSpacing: 1),
      ),
    ]);
  }
}

class _EmptyResults extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1e2a45)),
      ),
      child: const Column(children: [
        Icon(Icons.search_off, color: Color(0xFF475569), size: 40),
        SizedBox(height: 12),
        Text('No matches found',
            style: TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
        SizedBox(height: 4),
        Text('Below similarity threshold (60%)',
            style: TextStyle(color: Color(0xFF475569), fontSize: 11)),
      ]),
    );
  }
}

class _MatchCard extends StatelessWidget {
  final SearchMatch match;
  const _MatchCard({required this.match});

  @override
  Widget build(BuildContext context) {
    final color = match.confidenceColor;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(match.name,
                style: const TextStyle(
                    color: Color(0xFFe2e8f0), fontSize: 16, fontWeight: FontWeight.w700)),
            Text('Age ${match.age} · ${match.gender}',
                style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
          ]),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text(
              '${match.confidencePercent.toStringAsFixed(1)}%',
              style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.w800),
            ),
            Text(match.confidenceLabel,
                style: TextStyle(color: color, fontSize: 9, letterSpacing: 2)),
          ]),
        ]),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: match.confidencePercent / 100,
            minHeight: 4,
            backgroundColor: const Color(0xFF1e2a45),
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
        const SizedBox(height: 14),
        if (match.lastSeenLocation != null)
          _InfoRow('LAST SEEN', match.lastSeenLocation!),
        if (match.contactNumber != null)
          _InfoRow('CONTACT', match.contactNumber!),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.notifications_active, size: 14),
              label: const Text('SOS ALERT', style: TextStyle(fontSize: 10, letterSpacing: 1)),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFef4444),
                side: const BorderSide(color: Color(0xFFef4444), width: 0.5),
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.person_outline, size: 14),
              label: const Text('VIEW', style: TextStyle(fontSize: 10, letterSpacing: 1)),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF3b82f6),
                side: const BorderSide(color: Color(0xFF1e2a45)),
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ),
        ]),
      ]),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(children: [
        Text('$label  ',
            style: const TextStyle(
                color: Color(0xFF475569), fontSize: 9, letterSpacing: 2)),
        Expanded(
          child: Text(value,
              style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 11)),
        ),
      ]),
    );
  }
}

class _PipelineInfo extends StatelessWidget {
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
        const Text('HOW IT WORKS',
            style: TextStyle(color: Color(0xFF475569), fontSize: 9, letterSpacing: 2)),
        const SizedBox(height: 12),
        for (final step in [
          ['01', 'DETECT', 'MTCNN locates faces in the image'],
          ['02', 'EMBED', 'ArcFace extracts a 512-dim vector'],
          ['03', 'MATCH', 'Cosine similarity vs all registered faces'],
          ['04', 'RANK', 'Results filtered above 60% threshold'],
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Row(children: [
              Text(step[0],
                  style: const TextStyle(
                      color: Color(0xFF3b82f6), fontSize: 9, letterSpacing: 1)),
              const SizedBox(width: 12),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(step[1],
                    style: const TextStyle(
                        color: Color(0xFF94a3b8), fontSize: 9, letterSpacing: 2)),
                Text(step[2],
                    style: const TextStyle(color: Color(0xFF475569), fontSize: 10)),
              ]),
            ]),
          ),
      ]),
    );
  }
}
