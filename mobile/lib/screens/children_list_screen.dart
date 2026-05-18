import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/child_model.dart';

class ChildrenListScreen extends StatefulWidget {
  const ChildrenListScreen({super.key});

  @override
  State<ChildrenListScreen> createState() => _ChildrenListScreenState();
}

class _ChildrenListScreenState extends State<ChildrenListScreen> {
  List<ChildModel> _children = _mockChildren
      .map((m) => ChildModel.fromJson(m as Map<String, dynamic>))
      .toList();
  String _filter = 'missing';
  bool   _loading = false;
  String _error = '';
  bool _usingDemoData = true;
  final _api = ApiService();

  static const _mockChildren = [
    {'id': 'm1', 'name': 'Ravi Kumar',   'age': 8,  'gender': 'Male',   'status': 'missing', 'last_seen_location': 'Chennai Central',   'contact_number': '+91-98765-43210', 'has_embedding': true},
    {'id': 'm2', 'name': 'Priya Sharma', 'age': 12, 'gender': 'Female', 'status': 'missing', 'last_seen_location': 'Mumbai Andheri',    'contact_number': '+91-87654-32109', 'has_embedding': true},
    {'id': 'm3', 'name': 'Arjun Patel',  'age': 6,  'gender': 'Male',   'status': 'found',   'last_seen_location': 'Delhi Connaught',   'contact_number': '+91-76543-21098', 'has_embedding': false},
    {'id': 'm4', 'name': 'Meena Devi',   'age': 9,  'gender': 'Female', 'status': 'missing', 'last_seen_location': 'Kolkata Park St',   'contact_number': '+91-65432-10987', 'has_embedding': true},
    {'id': 'm5', 'name': 'Suresh Reddy', 'age': 14, 'gender': 'Male',   'status': 'found',   'last_seen_location': 'Hyderabad Jubilee', 'contact_number': '+91-54321-09876', 'has_embedding': true},
  ];

  @override
  void initState() {
    super.initState();
    _children = _mockChildren
        .where((m) => _filter == 'all' || m['status'] == _filter)
        .map((m) => ChildModel.fromJson(m as Map<String, dynamic>))
        .toList();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = ''; });
    try {
      final data = await _api.getChildren(status: _filter);
      if (mounted) {
        setState(() {
          if (data.isEmpty) {
            _children = _mockChildren
                .where((m) => _filter == 'all' || m['status'] == _filter)
                .map((m) => ChildModel.fromJson(m as Map<String, dynamic>))
                .toList();
            _usingDemoData = true;
          } else {
            _children = data;
            _usingDemoData = false;
          }
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _children = _mockChildren
              .where((m) => _filter == 'all' || m['status'] == _filter)
              .map((m) => ChildModel.fromJson(m as Map<String, dynamic>))
              .toList();
          _usingDemoData = true;
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Children Registry',
            style: TextStyle(fontSize: 14, letterSpacing: 1)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: const Color(0xFF1e2a45), height: 1),
        ),
      ),
      body: Column(children: [
        // Filter chips
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Row(children: [
            for (final f in ['missing', 'found', 'all'])
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(
                    f.toUpperCase(),
                    style: TextStyle(
                      fontSize: 10,
                      letterSpacing: 1,
                      color: _filter == f ? Colors.white : const Color(0xFF64748b),
                    ),
                  ),
                  selected: _filter == f,
                  onSelected: (_) {
                    setState(() => _filter = f);
                    _load();
                  },
                  backgroundColor: const Color(0xFF0d1220),
                  selectedColor: const Color(0xFF1d4ed8),
                  checkmarkColor: Colors.white,
                  side: BorderSide(
                    color: _filter == f
                        ? const Color(0xFF3b82f6)
                        : const Color(0xFF1e2a45),
                  ),
                ),
              ),
          ]),
        ),
        if (_usingDemoData)
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 4, 16, 0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Demo registry data is shown until the backend has records.',
                style: TextStyle(color: Color(0xFF94a3b8), fontSize: 11),
              ),
            ),
          ),
        // List
        Expanded(
          child: _loading
              ? const Center(
                  child: CircularProgressIndicator(color: Color(0xFF3b82f6)))
              : _children.isEmpty
                  ? const Center(
                      child: Text('No records found',
                          style: TextStyle(color: Color(0xFF64748b))))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 8),
                        itemCount: _children.length,
                        itemBuilder: (_, i) => _ChildTile(_children[i]),
                      ),
                    ),
        ),
      ]),
    );
  }
}

class _ChildTile extends StatelessWidget {
  final ChildModel child;
  const _ChildTile(this.child);

  @override
  Widget build(BuildContext context) {
    final statusColor =
        child.isMissing ? const Color(0xFFef4444) : const Color(0xFF22c55e);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1e2a45)),
      ),
      child: Row(children: [
        Container(
          width: 3,
          height: 92,
          decoration: BoxDecoration(
            color: statusColor,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 12),
        CircleAvatar(
          backgroundColor: const Color(0xFF1e2a45),
          radius: 22,
          child: Text(
            child.name[0],
            style: const TextStyle(
                color: Color(0xFF94a3b8),
                fontWeight: FontWeight.w700,
                fontSize: 18),
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(child.name,
                style: const TextStyle(
                    color: Color(0xFFe2e8f0),
                    fontWeight: FontWeight.w700,
                    fontSize: 14)),
            const SizedBox(height: 2),
            Text('Age ${child.age} · ${child.gender}',
                style: const TextStyle(
                    color: Color(0xFF64748b), fontSize: 11)),
            if (child.lastSeenLocation != null)
              Text(child.lastSeenLocation!,
                  style: const TextStyle(
                      color: Color(0xFF475569), fontSize: 11)),
          ]),
        ),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(3),
              border: Border.all(color: statusColor.withOpacity(0.35)),
            ),
            child: Text(
              child.status.toUpperCase(),
              style: TextStyle(
                  color: statusColor, fontSize: 9, letterSpacing: 1),
            ),
          ),
          if (child.hasEmbedding) ...[
            const SizedBox(height: 6),
            const Text('◎ AI',
                style: TextStyle(color: Color(0xFF22c55e), fontSize: 9)),
          ],
        ]),
      ]),
    );
  }
}
