import 'package:flutter/material.dart';

class SearchMatch {
  final String childId;
  final String name;
  final int age;
  final String gender;
  final double similarity;
  final double confidencePercent;
  final String? lastSeenLocation;
  final String? contactNumber;
  final String? photoPath;

  const SearchMatch({
    required this.childId,
    required this.name,
    required this.age,
    required this.gender,
    required this.similarity,
    required this.confidencePercent,
    this.lastSeenLocation,
    this.contactNumber,
    this.photoPath,
  });

  factory SearchMatch.fromJson(Map<String, dynamic> j) {
    return SearchMatch(
      childId:           j['child_id'] as String,
      name:              j['name'] as String,
      age:               j['age'] as int,
      gender:            j['gender'] as String,
      similarity:        (j['similarity'] as num).toDouble(),
      confidencePercent: (j['confidence_percent'] as num).toDouble(),
      lastSeenLocation:  j['last_seen_location'] as String?,
      contactNumber:     j['contact_number'] as String?,
      photoPath:         j['photo_path'] as String?,
    );
  }

  String get confidenceLabel {
    if (confidencePercent >= 90) return 'HIGH';
    if (confidencePercent >= 75) return 'MEDIUM';
    return 'LOW';
  }

  Color get confidenceColor {
    if (confidencePercent >= 90) return const Color(0xFF22c55e);
    if (confidencePercent >= 75) return const Color(0xFFf59e0b);
    return const Color(0xFFef4444);
  }
}

class SearchResult {
  final List<SearchMatch> matches;
  final int faceCount;
  final String message;
  final String? searchId;

  const SearchResult({
    required this.matches,
    required this.faceCount,
    required this.message,
    this.searchId,
  });

  factory SearchResult.fromJson(Map<String, dynamic> j) {
    final rawMatches = (j['matches'] as List<dynamic>?) ?? [];
    return SearchResult(
      matches:   rawMatches
          .map((m) => SearchMatch.fromJson(m as Map<String, dynamic>))
          .toList(),
      faceCount: (j['face_count'] as int?) ?? 0,
      message:   (j['message'] as String?) ?? '',
      searchId:  j['search_id'] as String?,
    );
  }
}
