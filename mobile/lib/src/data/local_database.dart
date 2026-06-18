import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

class LocalDatabase {
  static const String _assetPath = 'assets/data/pokemon.db';
  static const String _dbFileName = 'pokemon.db';

  Database? _database;

  Future<void> initialize() async {
    final dbPath = await _copyAssetDatabaseIfNeeded();
    _database = await openDatabase(dbPath, readOnly: true);
  }

  Future<String> _copyAssetDatabaseIfNeeded() async {
    final documentsDirectory = await getApplicationDocumentsDirectory();
    final dbFile = File(join(documentsDirectory.path, _dbFileName));
    if (!await dbFile.exists()) {
      final data = await rootBundle.load(_assetPath);
      await dbFile.writeAsBytes(data.buffer.asUint8List());
    }
    return dbFile.path;
  }

  Future<int> getPokemonCount() async {
    if (_database == null) {
      throw StateError('データベースが初期化されていません');
    }
    final countResult = await _database!.rawQuery('SELECT COUNT(*) AS count FROM pokemon');
    return countResult.isNotEmpty ? (countResult.first['count'] as int) : 0;
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}
