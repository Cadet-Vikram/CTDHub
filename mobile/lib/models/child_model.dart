class ChildModel {
  final String id;
  final String name;
  final int age;
  final String gender;
  final String status;
  final String? lastSeenLocation;
  final String? lastSeenDate;
  final String? contactNumber;
  final String? photoPath;
  final double? lat;
  final double? lng;
  final bool hasEmbedding;

  const ChildModel({
    required this.id,
    required this.name,
    required this.age,
    required this.gender,
    required this.status,
    this.lastSeenLocation,
    this.lastSeenDate,
    this.contactNumber,
    this.photoPath,
    this.lat,
    this.lng,
    this.hasEmbedding = false,
  });

  factory ChildModel.fromJson(Map<String, dynamic> j) {
    return ChildModel(
      id:                j['id'] as String,
      name:              j['name'] as String,
      age:               j['age'] as int,
      gender:            j['gender'] as String,
      status:            j['status'] as String,
      lastSeenLocation:  j['last_seen_location'] as String?,
      lastSeenDate:      j['last_seen_date'] as String?,
      contactNumber:     j['contact_number'] as String?,
      photoPath:         j['photo_path'] as String?,
      lat:               (j['geolocation_lat'] as num?)?.toDouble(),
      lng:               (j['geolocation_lng'] as num?)?.toDouble(),
      hasEmbedding:      (j['has_embedding'] as bool?) ?? false,
    );
  }

  bool get isMissing => status == 'missing';
  bool get isFound   => status == 'found';
}
