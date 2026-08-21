import 'package:dio/dio.dart';
import 'dart:io';
import '../models/child_model.dart';
import '../models/search_result.dart';

class ApiService {
  // Override with:
  // flutter run --dart-define=API_BASE_URL=http://192.168.1.23:8000
  // Falls back to emulator-friendly defaults when not provided.
  static const String _apiBaseUrlFromEnv =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');

  static String get baseUrl {
    if (_apiBaseUrlFromEnv.isNotEmpty) {
      return _apiBaseUrlFromEnv;
    }
    if (Platform.isIOS) {
      return 'http://127.0.0.1:8000';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://localhost:8000';
  }

  late final Dio _dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 20),
      receiveTimeout: const Duration(seconds: 120),
    ),
  );

  // ── Auth ───────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post(
      '/api/auth/login',
      data: {'username': email, 'password': password},
      options: Options(contentType: Headers.formUrlEncodedContentType),
    );
    return response.data as Map<String, dynamic>;
  }

  // ── Children ───────────────────────────────────────────────────────────────

  Future<List<ChildModel>> getChildren({String status = 'missing'}) async {
    final response = await _dio.get(
      '/api/children/',
      queryParameters: {'status': status},
    );
    final list = response.data as List<dynamic>;
    return list.map((j) => ChildModel.fromJson(j as Map<String, dynamic>)).toList();
  }

  Future<Map<String, dynamic>> registerChild({
    required String name,
    required int age,
    required String gender,
    String? description,
    String? lastSeenLocation,
    String? contactNumber,
    File? photo,
    double? lat,
    double? lng,
  }) async {
    final Map<String, dynamic> fields = {
      'name': name,
      'age': age.toString(),
      'gender': gender,
      if (description != null && description.isNotEmpty) 'description': description,
      if (lastSeenLocation != null && lastSeenLocation.isNotEmpty)
        'last_seen_location': lastSeenLocation,
      if (contactNumber != null && contactNumber.isNotEmpty)
        'contact_number': contactNumber,
      if (lat != null) 'geolocation_lat': lat.toString(),
      if (lng != null) 'geolocation_lng': lng.toString(),
    };

    if (photo != null) {
      fields['photo'] = await MultipartFile.fromFile(
        photo.path,
        filename: 'photo.jpg',
      );
    }

    final formData = FormData.fromMap(fields);
    final response = await _dio.post('/api/children/register', data: formData);
    return response.data as Map<String, dynamic>;
  }

  // ── Face Search ────────────────────────────────────────────────────────────

  Future<SearchResult> searchByFace({
    required File photo,
    double? lat,
    double? lng,
  }) async {
    final formData = FormData.fromMap({
      'photo': await MultipartFile.fromFile(photo.path, filename: 'search.jpg'),
      if (lat != null) 'location_lat': lat.toString(),
      if (lng != null) 'location_lng': lng.toString(),
      'searched_by': 'mobile_user',
    });

    final response = await _dio.post('/api/search/face', data: formData);
    return SearchResult.fromJson(response.data as Map<String, dynamic>);
  }

  // ── Alerts ─────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> sendSOS({
    required String childId,
    required String reporterName,
    required String reporterPhone,
    double? lat,
    double? lng,
    String? message,
  }) async {
    final response = await _dio.post('/api/alerts/sos', data: {
      'child_id': childId,
      'reporter_name': reporterName,
      'reporter_phone': reporterPhone,
      if (lat != null) 'location_lat': lat,
      if (lng != null) 'location_lng': lng,
      if (message != null && message.isNotEmpty) 'message': message,
    });
    return response.data as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getAlerts() async {
    final response = await _dio.get('/api/alerts/');
    final list = response.data as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  // ── Stats ──────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getStats() async {
    final response = await _dio.get('/api/reports/stats');
    return response.data as Map<String, dynamic>;
  }
}
