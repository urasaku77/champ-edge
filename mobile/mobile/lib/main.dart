import 'package:flutter/material.dart';

import 'src/app.dart';
import 'src/data/entitlement_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // フル機能の解放状態（IAP/プロモコード）を初期化。Firebase はクラウド機能を
  // 開くときに遅延初期化する（無料のローカル計算では不要）。
  EntitlementService.instance.init();
  runApp(const ChampEdgeMobileApp());
}
