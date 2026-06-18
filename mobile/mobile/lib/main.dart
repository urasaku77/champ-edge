import 'package:flutter/material.dart';

import 'src/app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Firebase の初期化は起動ゲート（AuthGate）が行う（失敗時に再試行できるようにするため）。
  runApp(const ChampEdgeMobileApp());
}
