class Pokemon {
  final int id;
  final String name;
  final String type1;
  final String type2;

  Pokemon({
    required this.id,
    required this.name,
    required this.type1,
    required this.type2,
  });

  factory Pokemon.fromMap(Map<String, Object?> map) {
    return Pokemon(
      id: map['id'] as int,
      name: map['name'] as String,
      type1: map['type1'] as String,
      type2: map['type2'] as String,
    );
  }
}
