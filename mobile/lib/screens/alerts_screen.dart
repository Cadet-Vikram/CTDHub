import 'package:flutter/material.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  final _nameCtrl    = TextEditingController();
  final _phoneCtrl   = TextEditingController();
  final _messageCtrl = TextEditingController();
  bool _sending = false;
  bool _usingDemoData = true;

  final List<Map<String, String>> _alerts = [
    {'type': 'sos',       'child': 'Ravi Kumar',   'msg': 'SOS: Possible sighting near Egmore station', 'time': '09:42', 'status': 'sent'},
    {'type': 'broadcast', 'child': 'Priya Sharma',  'msg': 'AMBER Alert: Missing girl, Mumbai Andheri',  'time': '09:15', 'status': 'active'},
    {'type': 'match',     'child': 'Arjun Patel',   'msg': 'Face match 94.2% — child FOUND',            'time': '08:55', 'status': 'resolved'},
  ];

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _messageCtrl.dispose();
    super.dispose();
  }

  Future<void> _sendSOS() async {
    if (_nameCtrl.text.trim().isEmpty || _phoneCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter your name and phone number'),
          backgroundColor: Color(0xFFef4444),
        ),
      );
      return;
    }
    setState(() => _sending = true);
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    setState(() {
      _alerts.insert(0, {
        'type':   'sos',
        'child':  'Unknown',
        'msg':    _messageCtrl.text.trim().isEmpty
            ? 'SOS by ${_nameCtrl.text.trim()}'
            : _messageCtrl.text.trim(),
        'time':   TimeOfDay.now().format(context),
        'status': 'sent',
      });
      _sending = false;
      _nameCtrl.clear();
      _phoneCtrl.clear();
      _messageCtrl.clear();
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('SOS Alert sent to authorities!'),
        backgroundColor: Color(0xFF22c55e),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergency Alerts',
            style: TextStyle(fontSize: 14, letterSpacing: 1)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: const Color(0xFF1e2a45), height: 1),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // SOS form
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: const Color(0xFF0d1220),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFef4444).withOpacity(0.4)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: const BoxDecoration(
                      color: Color(0xFFef4444), shape: BoxShape.circle),
                ),
                const SizedBox(width: 10),
                const Text('SEND SOS ALERT',
                    style: TextStyle(
                        color: Color(0xFFef4444),
                        fontSize: 11,
                        letterSpacing: 2,
                        fontWeight: FontWeight.w700)),
              ]),
              const SizedBox(height: 18),
              _SOSField(label: 'YOUR NAME',     controller: _nameCtrl),
              const SizedBox(height: 12),
              _SOSField(
                label:         'PHONE NUMBER',
                controller:    _phoneCtrl,
                keyboardType:  TextInputType.phone,
              ),
              const SizedBox(height: 12),
              _SOSField(
                label:      'LOCATION / MESSAGE',
                controller: _messageCtrl,
                maxLines:   3,
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _sending ? null : _sendSOS,
                  icon: _sending
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.flash_on, size: 18),
                  label: Text(_sending ? 'SENDING...' : 'TRIGGER SOS'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFdc2626),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            ]),
          ),

          const SizedBox(height: 24),

          // Alert channels
          const Text('ALERT CHANNELS',
              style: TextStyle(
                  color: Color(0xFF94a3b8), fontSize: 10, letterSpacing: 2)),
          const SizedBox(height: 12),
          for (final ch in [
            [Icons.sms_outlined,            'SMS to Family',       true],
            [Icons.local_police_outlined,   'Police Station',      true],
            [Icons.people_outline,          'NGO Network',         true],
            [Icons.notifications_outlined,  'Push Notifications',  false],
          ])
            _ChannelRow(
              icon:   ch[0] as IconData,
              label:  ch[1] as String,
              active: ch[2] as bool,
            ),

          const SizedBox(height: 24),

          // Alert history
          const Text('ALERT HISTORY',
              style: TextStyle(
                  color: Color(0xFF94a3b8), fontSize: 10, letterSpacing: 2)),
          const SizedBox(height: 12),
          if (_usingDemoData)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: Text(
                'Demo alert history is shown until real alerts exist.',
                style: TextStyle(color: Color(0xFF94a3b8), fontSize: 11),
              ),
            ),
          for (final a in _alerts) _AlertTile(alert: a),
        ]),
      ),
    );
  }
}

class _SOSField extends StatelessWidget {
  final String label;
  final TextEditingController controller;
  final TextInputType keyboardType;
  final int maxLines;

  const _SOSField({
    required this.label,
    required this.controller,
    this.keyboardType = TextInputType.text,
    this.maxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label,
          style: const TextStyle(
              color: Color(0xFF475569), fontSize: 9, letterSpacing: 2)),
      const SizedBox(height: 6),
      TextFormField(
        controller:   controller,
        keyboardType: keyboardType,
        maxLines:     maxLines,
        style: const TextStyle(color: Color(0xFFe2e8f0), fontSize: 13),
        decoration: InputDecoration(
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(4),
            borderSide: const BorderSide(color: Color(0xFFef4444)),
          ),
        ),
      ),
    ]);
  }
}

class _ChannelRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;

  const _ChannelRow({
    required this.icon,
    required this.label,
    required this.active,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0xFF1e2a45)),
      ),
      child: Row(children: [
        Icon(icon, color: const Color(0xFF3b82f6), size: 20),
        const SizedBox(width: 14),
        Expanded(child: Text(label,
            style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 13))),
        Text(
          active ? 'ACTIVE' : 'SETUP NEEDED',
          style: TextStyle(
            color: active ? const Color(0xFF22c55e) : const Color(0xFFf59e0b),
            fontSize: 9,
            letterSpacing: 1,
          ),
        ),
      ]),
    );
  }
}

class _AlertTile extends StatelessWidget {
  final Map<String, String> alert;
  const _AlertTile({required this.alert});

  @override
  Widget build(BuildContext context) {
    const colors = {
      'sos':       Color(0xFFef4444),
      'broadcast': Color(0xFFf59e0b),
      'match':     Color(0xFF22c55e),
    };
    const icons = {
      'sos':       Icons.flash_on,
      'broadcast': Icons.campaign_outlined,
      'match':     Icons.person_search_outlined,
    };
    final color = colors[alert['type']] ?? const Color(0xFF64748b);
    final icon  = icons[alert['type']]  ?? Icons.notifications_outlined;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Row(children: [
        Container(
          width: 3,
          height: 64,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 12),
        Icon(icon, color: color, size: 22),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(alert['child'] ?? '',
              style: const TextStyle(
                  color: Color(0xFFe2e8f0),
                  fontSize: 13,
                  fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Text(alert['msg'] ?? '',
              style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text(alert['time'] ?? '',
              style: const TextStyle(
                  color: Color(0xFF475569), fontSize: 9)),
          const SizedBox(height: 4),
          Text(
            (alert['status'] ?? '').toUpperCase(),
            style: TextStyle(
              color: alert['status'] == 'resolved'
                  ? const Color(0xFF22c55e)
                  : const Color(0xFFf59e0b),
              fontSize: 9,
              letterSpacing: 1,
            ),
          ),
        ]),
      ]),
    );
  }
}
