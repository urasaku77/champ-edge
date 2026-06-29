import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

/// 画面に収まるときはスクロールさせず、はみ出したときだけスクロールする。
/// （iOS の既定 BouncingScrollPhysics は内容が収まっていても弾むため、
/// 全スクロール領域を ClampingScrollPhysics に統一して不要なスクロールを止める。）
class _NoBounceScrollBehavior extends MaterialScrollBehavior {
  const _NoBounceScrollBehavior();
  @override
  ScrollPhysics getScrollPhysics(BuildContext context) =>
      const ClampingScrollPhysics();
}

class ChampEdgeMobileApp extends StatelessWidget {
  const ChampEdgeMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ChampEdge',
      debugShowCheckedModeBanner: false,
      scrollBehavior: const _NoBounceScrollBehavior(),
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
