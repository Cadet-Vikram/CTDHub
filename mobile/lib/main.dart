import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const ConnectingTheDotsApp());
}

class ConnectingTheDotsApp extends StatelessWidget {
  const ConnectingTheDotsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Connecting the Dots',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0a0e1a),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF3b82f6),
          secondary: Color(0xFF22c55e),
          surface: Color(0xFF0d1220),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0d1220),
          foregroundColor: Color(0xFFe2e8f0),
          elevation: 0,
        ),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: Color(0xFF0d1220),
          selectedItemColor: Color(0xFF3b82f6),
          unselectedItemColor: Color(0xFF475569),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF111827),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(4),
            borderSide: const BorderSide(color: Color(0xFF1e2a45)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(4),
            borderSide: const BorderSide(color: Color(0xFF1e2a45)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(4),
            borderSide: const BorderSide(color: Color(0xFF3b82f6)),
          ),
          hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 12),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF2563eb),
            foregroundColor: Colors.white,
            textStyle: const TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.5,
            ),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          ),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}
