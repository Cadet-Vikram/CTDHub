// lib/screens/sos_screen.dart
// SOS button, camera capture, instant face match, authority alert

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

const String kApiBase = 'https://your-backend.com/api';

class SOSScreen extends StatefulWidget {
  const SOSScreen({super.key});

  @override
  State<SOSScreen> createState() => _SOSScreenState();
}

class _SOSScreenState extends State<SOSScreen> with TickerProviderStateMixin {
  bool _isSubmitting = false;
  File? _capturedPhoto;
  Map<String, dynamic>? _matchResult;
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  late AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 1))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  Future<void> _capturePhoto() async {
    final picker = ImagePicker();
    final img = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (img != null) setState(() => _capturedPhoto = File(img.path));
  }

  Future<Position?> _getLocation() async {
    bool enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) return null;
    LocationPermission perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied) return null;
    }
    return await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
  }

  Future<void> _submitSOS() async {
    if (_phoneCtrl.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your phone number')),
      );
      return;
    }

    setState(() { _isSubmitting = true; _matchResult = null; });

    try {
      final pos = await _getLocation();
      final req = http.MultipartRequest('POST', Uri.parse('$kApiBase/sos/report'));

      req.fields['reporter_name'] = _nameCtrl.text.isEmpty ? 'Anonymous' : _nameCtrl.text;
      req.fields['reporter_phone'] = _phoneCtrl.text;
      req.fields['description'] = _descCtrl.text;
      req.fields['latitude'] = (pos?.latitude ?? 0.0).toString();
      req.fields['longitude'] = (pos?.longitude ?? 0.0).toString();

      if (_capturedPhoto != null) {
        req.files.add(await http.MultipartFile.fromPath('photo', _capturedPhoto!.path));
      }

      final resp = await req.send().timeout(const Duration(seconds: 30));
      final body = jsonDecode(await resp.stream.bytesToString());
      setState(() => _matchResult = body);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SOS — Report a Sighting')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // SOS button
            AnimatedBuilder(
              animation: _pulseCtrl,
              builder: (_, __) => Container(
                margin: const EdgeInsets.symmetric(vertical: 16),
                child: ElevatedButton(
                  onPressed: _capturePhoto,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Color.lerp(Colors.red.shade700, Colors.red.shade400, _pulseCtrl.value),
                    foregroundColor: Colors.white,
                    minimumSize: const Size(120, 120),
                    shape: const CircleBorder(),
                    elevation: 4,
                  ),
                  child: const Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.camera_alt, size: 36),
                      SizedBox(height: 4),
                      Text('SOS', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
              ),
            ),

            // Photo preview
            if (_capturedPhoto != null)
              Container(
                height: 150,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  image: DecorationImage(image: FileImage(_capturedPhoto!), fit: BoxFit.cover),
                ),
              ),

            // Form
            TextField(controller: _nameCtrl, decoration: const InputDecoration(labelText: 'Your name (optional)', border: OutlineInputBorder())),
            const SizedBox(height: 10),
            TextField(controller: _phoneCtrl, decoration: const InputDecoration(labelText: 'Your phone number *', border: OutlineInputBorder()), keyboardType: TextInputType.phone),
            const SizedBox(height: 10),
            TextField(controller: _descCtrl, decoration: const InputDecoration(labelText: 'Description (location, clothing...)', border: OutlineInputBorder()), maxLines: 3),
            const SizedBox(height: 16),

            ElevatedButton.icon(
              onPressed: _isSubmitting ? null : _submitSOS,
              icon: _isSubmitting ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.send),
              label: Text(_isSubmitting ? 'Matching faces...' : 'Submit Emergency Report'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red.shade700,
                foregroundColor: Colors.white,
                minimumSize: const Size.fromHeight(48),
              ),
            ),

            // Match result
            if (_matchResult != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: _matchResult!['matched'] == true ? Colors.green.shade50 : Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _matchResult!['matched'] == true ? Colors.green.shade300 : Colors.orange.shade300),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Icon(_matchResult!['matched'] == true ? Icons.check_circle : Icons.info, color: _matchResult!['matched'] == true ? Colors.green : Colors.orange),
                      const SizedBox(width: 8),
                      Text(_matchResult!['matched'] == true ? 'Match Found!' : 'No Exact Match', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    ]),
                    const SizedBox(height: 8),
                    Text(_matchResult!['message'] ?? ''),
                    if (_matchResult!['matched'] == true) ...[
                      const SizedBox(height: 8),
                      Text('Case: ${_matchResult!['case_number']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      Text('Child: ${_matchResult!['child_name']}'),
                      Text('Similarity: ${(((_matchResult!['similarity'] ?? 0) as num) * 100).toStringAsFixed(1)}%'),
                      Text('Guardian: ${_matchResult!['guardian_phone']}', style: const TextStyle(color: Colors.blue)),
                    ],
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
