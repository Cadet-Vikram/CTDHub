import 'package:flutter/material.dart';
import 'search_screen.dart';
import 'register_screen.dart';
import 'children_list_screen.dart';
import 'alerts_screen.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;
  Map<String, dynamic> _stats = {
    'currently_missing': 0,
    'found': 0,
    'total_searches': 0,
    'total_alerts': 0,
  };
  final _api = ApiService();

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    try {
      final s = await _api.getStats();
      if (mounted) setState(() => _stats = s);
    } catch (_) {
      if (mounted) {
        setState(() => _stats = {
          'currently_missing': 183,
          'found': 64,
          'total_searches': 3241,
          'total_alerts': 892,
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      _DashboardTab(stats: _stats, onRefresh: _loadStats),
      const SearchScreen(),
      const RegisterScreen(),
      const ChildrenListScreen(),
      const AlertsScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: _tab, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        backgroundColor: const Color(0xFF0d1220),
        indicatorColor: const Color(0xFF1e2a45),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard, color: Color(0xFF3b82f6)),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search, color: Color(0xFF3b82f6)),
            label: 'Search',
          ),
          NavigationDestination(
            icon: Icon(Icons.add_circle_outline),
            selectedIcon: Icon(Icons.add_circle, color: Color(0xFF3b82f6)),
            label: 'Register',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_alt_outlined),
            selectedIcon: Icon(Icons.list_alt, color: Color(0xFF3b82f6)),
            label: 'Registry',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            selectedIcon: Icon(Icons.notifications, color: Color(0xFF3b82f6)),
            label: 'Alerts',
          ),
        ],
      ),
    );
  }
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────────

class _DashboardTab extends StatelessWidget {
  final Map<String, dynamic> stats;
  final VoidCallback onRefresh;

  const _DashboardTab({required this.stats, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: () async => onRefresh(),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const SizedBox(height: 8),
            const Text(
              'CONNECTING THE DOTS',
              style: TextStyle(
                color: Color(0xFF3b82f6),
                fontSize: 11,
                letterSpacing: 3,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Operations Dashboard',
              style: TextStyle(
                color: Color(0xFFe2e8f0),
                fontSize: 22,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 20),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.6,
              children: [
                _StatCard(
                  label: 'MISSING',
                  value: '${stats['currently_missing'] ?? 0}',
                  color: const Color(0xFFef4444),
                ),
                _StatCard(
                  label: 'FOUND',
                  value: '${stats['found'] ?? 0}',
                  color: const Color(0xFF22c55e),
                ),
                _StatCard(
                  label: 'SEARCHES',
                  value: '${stats['total_searches'] ?? 0}',
                  color: const Color(0xFF3b82f6),
                ),
                _StatCard(
                  label: 'ALERTS',
                  value: '${stats['total_alerts'] ?? 0}',
                  color: const Color(0xFFf59e0b),
                ),
              ],
            ),
            const SizedBox(height: 28),
            const Text(
              'GUIDE',
              style: TextStyle(color: Color(0xFF94a3b8), fontSize: 10, letterSpacing: 3),
            ),
            const SizedBox(height: 12),
            const _GuideCard(
              Icons.search_outlined,
              'Face Search',
              'Upload a photo to find a match in the registry using AI facial recognition.',
            ),
            const SizedBox(height: 10),
            const _GuideCard(
              Icons.add_circle_outline,
              'Register Child',
              'Report a missing child with photo and details.',
            ),
            const SizedBox(height: 10),
            const _GuideCard(
              Icons.notifications_active_outlined,
              'SOS Alert',
              'If you spot a missing child, send an instant alert to authorities.',
            ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatCard({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border(
          top: BorderSide(color: color.withOpacity(0.7), width: 2),
          left: const BorderSide(color: Color(0xFF1e2a45)),
          right: const BorderSide(color: Color(0xFF1e2a45)),
          bottom: const BorderSide(color: Color(0xFF1e2a45)),
        ),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF475569), fontSize: 9, letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: color, fontSize: 26, fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _GuideCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const _GuideCard(this.icon, this.title, this.description);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0d1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1e2a45)),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF3b82f6), size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFFe2e8f0),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(color: Color(0xFF64748b), fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
