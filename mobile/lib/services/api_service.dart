import 'dart:io';
import 'package:dio/dio.dart';
import '../models/child_model.dart';
import '../models/search_result.dart';

class ApiService {
  // ── IMPORTANT: Update this URL after deploying backend to Cloud Run ──────
  // Local dev (Android emulator): http://10.0.2.2:8000
  // Local dev (iOS simulator):    http://127.0.0.1:8000
  // Production (Cloud Run):       https://YOUR-SERVICE-URL.a.run.app
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
    ),
  );

  Future<Map<String, dynamic>> login(String email, String password) async {
    final r = await _dio.post('/api/auth/login',
        data: {'username': email, 'password': password},
        options: Options(contentType: Headers.formUrlEncodedContentType));
    return r.data as Map<String, dynamic>;
  }

  Future<List<ChildModel>> getChildren({String status = 'missing'}) async {
    final r = await _dio.get('/api/children/',
        queryParameters: {'status': status});
    return (r.data as List<dynamic>)
        .map((j) => ChildModel.fromJson(j as Map<String, dynamic>))
        .toList();
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
    final fields = <String, dynamic>{
      'name': name, 'age': age.toString(), 'gender': gender,
      if (description != null && description.isNotEmpty) 'description': description,
      if (lastSeenLocation != null && lastSeenLocation.isNotEmpty)
        'last_seen_location': lastSeenLocation,
      if (contactNumber != null && contactNumber.isNotEmpty)
        'contact_number': contactNumber,
      if (lat != null) 'geolocation_lat': lat.toString(),
      if (lng != null) 'geolocation_lng': lng.toString(),
      if (photo != null)
        'photo': await MultipartFile.fromFile(photo.path, filename: 'photo.jpg'),
    };
    final r = await _dio.post('/api/children/register',
        data: FormData.fromMap(fields));
    return r.data as Map<String, dynamic>;
  }

  Future<SearchResult> searchByFace({
    required File photo,
    double? lat,
    double? lng,
  }) async {
    final fd = FormData.fromMap({
      'photo': await MultipartFile.fromFile(photo.path, filename: 'search.jpg'),
      if (lat != null) 'location_lat': lat.toString(),
      if (lng != null) 'location_lng': lng.toString(),
      'searched_by': 'mobile_user',
    });
    final r = await _dio.post('/api/search/face', data: fd);
    return SearchResult.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> sendSOS({
    required String childId,
    required String reporterName,
    required String reporterPhone,
    double? lat,
    double? lng,
    String? message,
  }) async {
    final r = await _dio.post('/api/alerts/sos', data: {
      'child_id': childId,
      'reporter_name': reporterName,
      'reporter_phone': reporterPhone,
      if (lat != null) 'location_lat': lat,
      if (lng != null) 'location_lng': lng,
      if (message != null && message.isNotEmpty) 'message': message,
    });
    return r.data as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getAlerts() async {
    final r = await _dio.get('/api/alerts/');
    return (r.data as List<dynamic>)
        .map((e) => e as Map<String, dynamic>)
        .toList();
  }

  Future<Map<String, dynamic>> getStats() async {
    final r = await _dio.get('/api/reports/stats');
    return r.data as Map<String, dynamic>;
  }
}
