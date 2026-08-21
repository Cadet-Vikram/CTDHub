import 'package:flutter/material.dart';
import 'lib/screens/home_screen.dart';

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
          elevation: 0,
        ),
        fontFamily: 'monospace',
      ),
      home: const HomeScreen(),
    );
  }
}
