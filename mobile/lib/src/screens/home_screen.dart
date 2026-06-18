import 'dart:async';

import 'package:flutter/material.dart';

import '../data/ability_values.dart';
import '../data/home_stats.dart';
import '../data/option_data.dart';
import '../data/party_store.dart';
import '../data/poke_db.dart';
import '../data/ref_data.dart';
import '../data/scrape_data.dart';
import '../data/waza_effects.dart';
import '../model/battle_pokemon.dart';
import '../service/appear_ability.dart';
import '../service/damage_engine.dart';
import '../data/battle_db.dart';
import '../data/app_settings.dart';
import 'adder_dialog.dart';
import 'battle_analysis_screen.dart';
import 'similar_party_dialog.dart';
import 'battle_history_screen.dart';
import 'battle_record_dialog.dart';
import 'box_screen.dart';
import 'party_manager_screen.dart';
import 'pokemon_picker.dart';
import 'settings_screen.dart';
import 'speed_compare_dialog.dart';
import 'weight_compare_dialog.dart';

/// 対戦画面。旧 champ-edge のレイアウト・操作を踏襲する。
/// 左=自分 / 右=相手 にパーティ（タップで選出＝チェック）と、選択ポケモンの
/// 基本情報（種族値・実数値・特性・持ち物・性格・やけど・じゅうでん・急所・壁）、
/// 技と相手へのダメージを表示する。
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  int _myActive = 0;
  int _oppActive = 0;
  // 選出（選んだ順のスロット番号。番号バッジとして表示）。原典同様、初期は空で
  // タップにより明示的に登録する（登録/クリアでは勝手に選出しない）。
  final List<int> _myChosen = [];
  final List<int> _oppChosen = [];

  // パーティ（編集可能）。自分は前回状態を復元（無ければ空）、相手は毎回スカウトし直す
  // 想定なので起動時は常に空（前回の相手は復元しない）。
  late List<BattlePokemon> _myParty = _ensure6(const []);
  final List<BattlePokemon> _oppParty = _ensure6(const []);

  int _similarHits = 0; // 自動検索でヒットした類似パーティ数（バッジ用）
  bool _isTablet = false; // iPad など大画面（build で更新）
  bool _tabletOppNormalized = false; // iPad初回に相手技を10化したか

  Weather _weather = Weather.none;
  Field _field = Field.none;

  // タイマー（原典 TimerFrame：20分・残10分で青/5分黄/3分赤）。閉じても計測継続。
  static const int _timerInitial = 1200;
  final ValueNotifier<int> _timerLeft = ValueNotifier(_timerInitial);
  Timer? _timerTicker;
  DateTime? _timerEnd;

  // 自分パーティの識別（番号/連番/タイトル）。対戦記録の絞り込みキー。
  String _myPartyNum = '';
  String _myPartySubnum = '';
  String _myPartyTitle = '';

  // 対戦記録ダイアログの入力ドラフト（登録するまで保持＝閉じても消えない）。
  // パーティ番号/連番は使用中パーティから自動補完する。
  final TextEditingController _recTn = TextEditingController();
  final TextEditingController _recRate = TextEditingController();
  final TextEditingController _recMemo = TextEditingController();
  final TextEditingController _recPartyNum = TextEditingController();
  final TextEditingController _recPartySubnum = TextEditingController();
  bool _recFavorite = false;

  // カウンタ（3個・0〜99）。[0] は中央列に直接表示、全3個はメニューのポップアップで扱う。
  // 対戦記録または明示リセットまで永続化する。
  static const int _counterCount = 3;
  final List<int> _counterValues = List.filled(_counterCount, 0);
  final List<TextEditingController> _counterTitles =
      List.generate(_counterCount, (_) => TextEditingController());

  @override
  void dispose() {
    _timerTicker?.cancel();
    _timerLeft.dispose();
    for (final c in _counterTitles) {
      c.dispose();
    }
    _recTn.dispose();
    _recRate.dispose();
    _recMemo.dispose();
    _recPartyNum.dispose();
    _recPartySubnum.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _initDb();
    BattleDb.instance.open();
    _initParties();
    _restoreCounters();
    _restorePartyMeta();
    HomeStats.instance.load();
    ScrapeData.instance.load();
    AppSettings.instance.load();
    // 参照データ（HOME/構築記事/ランキング/シーズン）を Cloudflare Pages 配信から
    // バックグラウンド取得してキャッシュを更新する（stale-while-revalidate・TTL 24h）。
    // 取得分は次回読み込みから反映。失敗時は同梱アセットへフォールバック（オフライン可）。
    RefData.instance.refreshAll();
  }

  Future<void> _restorePartyMeta() async {
    final m = await PartyStore.instance.loadMyPartyMeta();
    if (m == null || !mounted) return;
    final (num, subnum, title) = m;
    setState(() {
      _myPartyNum = num;
      _myPartySubnum = subnum;
      _myPartyTitle = title;
    });
  }

  /// パーティ初期化：前回セッションを復元し、未補完（サンプル/新規）のポケモンは
  /// HOME 使用率で補完する。これにより初期表示の持ち物等も HOME 準拠になる。
  /// （サンプルパーティ自体はリリース時に削除予定。GitHub Issue 参照）
  Future<void> _initParties() async {
    await _restoreLast();
    await HomeStats.instance.load();
    var changed = false;
    for (final p in [..._myParty, ..._oppParty]) {
      if (p.name.isNotEmpty && !p.homeFilled) {
        await _fillFromHome(p);
        changed = true;
      }
    }
    if (changed && mounted) setState(() {});
  }

  /// 前回セッションの自分パーティのみ復元（相手は毎回スカウトし直すため復元しない）。
  Future<void> _restoreLast() async {
    final my = await PartyStore.instance.loadLast('my');
    if (!mounted || my == null) return;
    setState(() {
      _myParty = _ensure6(my);
      _myActive = _myActive.clamp(0, _myParty.length - 1);
    });
    _backfillWeights();
  }

  /// 旧形式（weight 未保存）のパーティに DB から重さを補完する。
  Future<void> _backfillWeights() async {
    await PokeDb.instance.open(); // _initDb と並走しても二重には開かない
    var changed = false;
    for (final p in [..._myParty, ..._oppParty]) {
      if (p.name.isEmpty || p.weight > 0) continue;
      final w = await PokeDb.instance.weightOf(p.pid);
      if (w != null && w > 0) {
        p.weight = w;
        changed = true;
      }
    }
    if (changed && mounted) setState(() {});
  }

  /// パーティを必ず6枠に揃える（不足分は空ポケで補完）。
  static List<BattlePokemon> _ensure6(List<BattlePokemon> party) {
    final list = party.take(6).toList();
    while (list.length < 6) {
      list.add(BattlePokemon(
        name: '',
        pid: '0000-0',
        baseStats: const [0, 0, 0, 0, 0, 0],
        type1: PokeType.none,
        abilityOptions: const ['—'],
        moves: List.generate(4, (_) => emptyMove()),
      ));
    }
    return list;
  }

  /// 直近の自分パーティを自動保存（編集のたびに呼ぶ）。相手は復元しないため保存しない。
  void _autosaveLast() {
    PartyStore.instance.saveLast('my', _myParty);
    _maybeAutoSimilar();
  }

  /// 自動検索モードがオンなら相手パーティで類似検索し、ヒット数をバッジ用に保持。
  Future<void> _maybeAutoSimilar() async {
    if (!AppSettings.instance.autoSimilarSearch) {
      if (_similarHits != 0 && mounted) setState(() => _similarHits = 0);
      return;
    }
    final n = (await findSimilarParties(_oppParty)).total;
    if (!mounted || n == _similarHits) return;
    setState(() => _similarHits = n);
  }

  /// ポケモンを選択（選出/切替）する共通処理。切替時はランク・一過性効果をクリアし、
  /// 未補完の実ポケモンは HOME 使用率から自動補完する。
  Future<void> _selectActive(int i, bool isMy) async {
    final myOld = _myParty[_myActive];
    final oppOld = _oppParty[_oppActive];
    final curActive = isMy ? _myActive : _oppActive;
    final switching = i != curActive;
    setState(() {
      if (switching) {
        if (isMy) {
          _resetMoveToggles(myOld, oppOld);
          resetAppearAbility(myOld);
          myOld.boosts.fillRange(0, 6, 0); // 場を離れる側の自分のランクをクリア
        } else {
          _resetMoveToggles(oppOld, myOld);
          resetAppearAbility(oppOld);
          oppOld.boosts.fillRange(0, 6, 0);
        }
      }
      if (isMy) {
        _myActive = i;
        _chooseOnTap(_myChosen, i);
      } else {
        _oppActive = i;
        _chooseOnTap(_oppChosen, i);
      }
    });
    // 初回選出時の HOME 自動補完（実ポケモンで技が空・未補完のときだけ）。
    final p = isMy ? _myParty[i] : _oppParty[i];
    if (p.name.isNotEmpty && !p.homeFilled && p.moves.every((m) => m.isEmpty)) {
      await _fillFromHome(p);
    }
    if (!isMy && p.name.isNotEmpty) {
      // 相手はダメージ計算用に「物理・特殊のみ5枠」へ整える（変化技を除外し、
      // 足りない枠＝5枠目スカウト枠を HOME 使用率上位で補完）。
      await _normalizeOpponentMoves(p);
    }
    if (!mounted) return;
    setState(() {
      _applyAbilityWeatherField(p);
      applyAppearAbility(p, isMy ? _oppParty[_oppActive] : _myParty[_myActive]);
    });
  }

  /// ポケモン切替で場を離れるポケモンの技トグル効果をすべて解除しリセットする。
  void _resetMoveToggles(BattlePokemon attacker, BattlePokemon defender) {
    for (var i = 0; i < attacker.moves.length; i++) {
      final m = attacker.moves[i];
      final n = m.currentEffectValue.toInt();
      if (m.effect.isToggle && n >= 1) {
        final isRank = m.effect.kind == WazaEffectKind.selfRank ||
            m.effect.kind == WazaEffectKind.opponentRank;
        // ランク変化は「変化させられた側」が場を離れるときにクリアされる（自分のランクは
        // 直後の boosts クリアで、相手に入れたランクは相手の切替時に処理）。適用した側が
        // 引っ込むときは戻さない。タイプ変更/特性入替などのトグルのみここで解除する。
        if (!isRank) {
          applyMoveToggle(m.effect, attacker, defender, false);
        }
        attacker.moves[i] = m.copyWith(effectValue: 0);
      }
    }
  }

  /// 特性による天候・フィールドの自動反映（旧 champ-edge の after_appear 相当）。
  /// ポケモンが場に出た（選択された）ときにその特性で天候/フィールドを変える。
  void _applyAbilityWeatherField(BattlePokemon p) {
    switch (p.ability) {
      case 'すなおこし':
        _weather = Weather.sandstorm;
      case 'ひでり' || 'ひひいろのこどう' || 'メガソーラー':
        _weather = Weather.sunny;
      case 'あめふらし':
        _weather = Weather.rainy;
      case 'ゆきふらし':
        _weather = Weather.snow;
      case 'エレキメイカー' || 'ハドロンエンジン':
        _field = Field.electric;
      case 'グラスメイカー':
        _field = Field.grassy;
      case 'ミストメイカー':
        _field = Field.misty;
      case 'サイコメイカー':
        _field = Field.psychic;
    }
  }

  Future<void> _initDb() async {
    final ok = await PokeDb.instance.open();
    if (!ok) return;
    try {
      loadedItemOptions = await PokeDb.instance.itemNames();
      if (mounted) setState(() {});
    } catch (e) {
      debugPrint('[Home] DB init error: $e');
    }
  }

  void _refresh() {
    setState(() {});
    _autosaveLast();
  }

  @override
  Widget build(BuildContext context) {
    _myActive = _myActive.clamp(0, _myParty.length - 1);
    _oppActive = _oppActive.clamp(0, _oppParty.length - 1);
    final my = _myParty[_myActive];
    final opp = _oppParty[_oppActive];
    final fieldState = FieldState(weather: _weather, field: _field);
    // iPad など大画面では余白を活かして間隔を広げ、相手技は10枠表示する。
    _isTablet = MediaQuery.of(context).size.shortestSide >= 600;
    if (_isTablet && !_tabletOppNormalized) {
      _tabletOppNormalized = true;
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        await _normalizeOpponentMoves(_oppParty[_oppActive]);
        if (mounted) setState(() {});
      });
    }
    return Scaffold(
      key: _scaffoldKey,
      endDrawer: _buildMenuDrawer(),
      body: SafeArea(
        // iPad は余白が多いので文字を拡大して見やすく・押しやすくする。
        child: MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(_isTablet ? 1.45 : 1.0),
          ),
          child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: _SidePanel(
                title: '自分',
                accent: Colors.blue,
                isTablet: _isTablet,
                moveCount: 5,
                party: _myParty,
                activeIndex: _myActive,
                chosen: _myChosen,
                active: my,
                opponentActive: opp,
                field: fieldState,
                onChanged: _refresh,
                onTapPoke: (i) => _selectActive(i, true),
                onLongPoke: (i) => setState(() {
                  _myActive = i;
                  _myChosen.remove(i);
                }),
                onEdit: () => _editParty(_myParty, '自分'),
                footer: _isTablet ? _bottomControls() : null,
              ),
            ),
            _centerMenu(opp),
            Expanded(
              child: _SidePanel(
                title: '相手',
                accent: Colors.red,
                isTablet: _isTablet,
                moveCount: _isTablet ? 10 : 5,
                party: _oppParty,
                activeIndex: _oppActive,
                chosen: _oppChosen,
                active: opp,
                opponentActive: my,
                field: fieldState,
                onChanged: _refresh,
                onTapPoke: (i) => _selectActive(i, false),
                onLongPoke: (i) => setState(() {
                  _oppActive = i;
                  _oppChosen.remove(i);
                }),
                onEdit: () => _editParty(_oppParty, '相手'),
              ),
            ),
          ],
        ),
        ),
      ),
    );
  }

  /// 中央列：メニュー/HOME アイコンと天候/フィールド選択（押しやすいよう間隔をあける）。
  /// 中央列のアイコンボタン（未実装はスナックバー）。
  Widget _centerIcon(IconData icon, String label, VoidCallback onTap) {
    return IconButton(
      padding: EdgeInsets.zero,
      constraints: const BoxConstraints(),
      icon: Icon(icon),
      iconSize: _isTablet ? 30 : 20,
      tooltip: label,
      onPressed: onTap,
    );
  }

  // ===== タイマー / カウンタ（原典 TimerFrame / CountersFrame）=====

  bool get _timerRunning => _timerTicker != null;

  /// スタート/ストップの切替（原典 start_button_clicked）。
  void _timerStartStop() {
    if (_timerRunning) {
      _timerTicker?.cancel();
      _timerTicker = null;
      _timerEnd = null;
    } else if (_timerLeft.value >= 1) {
      _timerEnd = DateTime.now().add(Duration(seconds: _timerLeft.value));
      _timerTicker = Timer.periodic(const Duration(milliseconds: 250), (_) {
        final leftMs = _timerEnd!.difference(DateTime.now()).inMilliseconds;
        final left = (leftMs / 1000).ceil();
        if (left <= 0) {
          _timerTicker?.cancel();
          _timerTicker = null;
          _timerEnd = null;
          _timerLeft.value = 0;
        } else {
          _timerLeft.value = left;
        }
      });
    }
  }

  void _timerReset() {
    _timerTicker?.cancel();
    _timerTicker = null;
    _timerEnd = null;
    _timerLeft.value = _timerInitial;
    _notify('タイマーをリセットしました');
  }

  /// 切替/クリア操作の結果をスナックバーで知らせる（特性長押しと同じ通知）。
  void _notify(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        duration: const Duration(milliseconds: 900), content: Text(msg)));
  }

  /// 天候を長押しでクリア（通知付き）。
  void _clearWeather() {
    setState(() => _weather = Weather.none);
    _notify('天候をクリアしました');
  }

  /// フィールドを長押しでクリア（通知付き）。
  void _clearField() {
    setState(() => _field = Field.none);
    _notify('フィールドをクリアしました');
  }

  /// 残り時間の色（原典: <180 赤 / <300 黄 / <600 青 / それ以上 緑）。
  Color _timerColor(int left) {
    if (left < 180) return Colors.red;
    if (left < 300) return Colors.amber;
    if (left < 600) return Colors.blue;
    return Colors.lightGreen;
  }

  String _mmss(int s) =>
      '${(s ~/ 60).toString().padLeft(2, '0')}:${(s % 60).toString().padLeft(2, '0')}';

  /// 中央列のタイマー（直接表示）。一回押し＝スタート/ストップ、長押し＝リセット。
  /// サイズ固定でレイアウトがずれないようにする。
  Widget _timerInline() {
    return ValueListenableBuilder<int>(
      valueListenable: _timerLeft,
      builder: (_, left, __) => GestureDetector(
        onTap: _timerStartStop,
        onLongPress: _timerReset,
        child: Container(
          width: 64,
          height: 20,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: _timerColor(left).withValues(alpha: 0.30),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(_mmss(left),
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  height: 1.0,
                  fontFeatures: [FontFeature.tabularFigures()])),
        ),
      ),
    );
  }

  Future<void> _restoreCounters() async {
    final loaded = await PartyStore.instance.loadCounters();
    if (loaded == null || !mounted) return;
    final (values, titles) = loaded;
    setState(() {
      for (var i = 0; i < _counterCount; i++) {
        if (i < values.length) _counterValues[i] = values[i];
        if (i < titles.length) _counterTitles[i].text = titles[i];
      }
    });
  }

  void _saveCounters() => PartyStore.instance.saveCounters(
      _counterValues, [for (final c in _counterTitles) c.text]);

  void _setCounter(int i, int v) {
    setState(() => _counterValues[i] = v.clamp(0, 99));
    _saveCounters();
  }

  /// 中央列のカウンタ（[0] のみ・直接表示）。上段に値、下段に −/＋ を横いっぱいに
  /// 並べて押しやすくする。**長押しで 0 リセット**（複数カウンタの一覧は置き場所検討中）。
  Widget _counterInline() {
    return GestureDetector(
      onLongPress: () => _setCounter(0, 0),
      child: Container(
        width: 64,
        padding: const EdgeInsets.symmetric(vertical: 2),
        decoration: BoxDecoration(
          color: Colors.blueGrey.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Colors.black12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 上段：値。
            Text('${_counterValues[0]}',
                style: const TextStyle(
                    fontSize: 14, fontWeight: FontWeight.bold, height: 1.0)),
            const SizedBox(height: 2),
            // 下段：−／＋ を横いっぱいに。
            Row(
              children: [
                Expanded(
                    child: _counterTap(
                        '−', () => _setCounter(0, _counterValues[0] - 1))),
                const SizedBox(width: 2),
                Expanded(
                    child: _counterTap(
                        '＋', () => _setCounter(0, _counterValues[0] + 1))),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _counterTap(String text, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: 18,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.blueGrey.withValues(alpha: 0.18),
          borderRadius: BorderRadius.circular(3),
        ),
        child: Text(text,
            style: const TextStyle(
                fontSize: 13, fontWeight: FontWeight.bold, height: 1.0)),
      ),
    );
  }

  /// 複数カウンタ（3個・タイトル付き）の一覧ポップアップ。値は永続化。
  /// ※起動導線は置き場所検討中（ダブルタップ起動は廃止）。確定したら再配線する。
  // ignore: unused_element
  Future<void> _showCountersDialog() {
    return showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
          child: StatefulBuilder(
            builder: (ctx, setLocal) => SizedBox(
              width: 380,
              child: SingleChildScrollView(
                child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      const Text('カウンター',
                          style: TextStyle(
                              fontSize: 15, fontWeight: FontWeight.bold)),
                      const Spacer(),
                      TextButton(
                        onPressed: () => setLocal(() {
                          for (var i = 0; i < _counterCount; i++) {
                            _counterValues[i] = 0;
                            _counterTitles[i].clear();
                          }
                          _saveCounters();
                        }),
                        child: const Text('全リセット'),
                      ),
                    ],
                  ),
                  for (var i = 0; i < _counterCount; i++)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 5),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _counterTitles[i],
                              style: const TextStyle(fontSize: 15),
                              onChanged: (_) => _saveCounters(),
                              decoration: const InputDecoration(
                                hintText: 'タイトル',
                                isDense: true,
                                contentPadding:
                                    EdgeInsets.symmetric(vertical: 12),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          _countersBtn('−', () {
                            _setCounter(i, _counterValues[i] - 1);
                            setLocal(() {});
                          }),
                          SizedBox(
                            width: 44,
                            child: Center(
                              child: Text('${_counterValues[i]}',
                                  style: const TextStyle(
                                      fontSize: 26,
                                      fontWeight: FontWeight.bold)),
                            ),
                          ),
                          _countersBtn('＋', () {
                            _setCounter(i, _counterValues[i] + 1);
                            setLocal(() {});
                          }),
                          const SizedBox(width: 8),
                          _countersBtn('0', () {
                            _setCounter(i, 0);
                            setLocal(() {});
                          }, subtle: true),
                        ],
                      ),
                    ),
                ],
              ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _countersBtn(String text, VoidCallback onTap, {bool subtle = false}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 50,
        height: 46,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.blueGrey.withValues(alpha: subtle ? 0.07 : 0.16),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.black12),
        ),
        child: Text(text,
            style: TextStyle(
                fontSize: subtle ? 16 : 22, fontWeight: FontWeight.bold)),
      ),
    );
  }

  /// 対戦記録の登録（中央列の対戦記録アイコン）。
  void _recordBattle() {
    // パーティ番号/連番は使用中パーティの識別から自動補完（既知のときは上書き）。
    if (_myPartyNum.isNotEmpty) _recPartyNum.text = _myPartyNum;
    if (_myPartySubnum.isNotEmpty) _recPartySubnum.text = _myPartySubnum;
    showBattleRecordDialog(
      context,
      myParty: _myParty,
      oppParty: _oppParty,
      myChosen: _myChosen,
      oppChosen: _oppChosen,
      tn: _recTn,
      rate: _recRate,
      memo: _recMemo,
      partyNum: _recPartyNum,
      partySubnum: _recPartySubnum,
      favorite: _recFavorite,
      onFavoriteChanged: (v) => _recFavorite = v,
      partyTitle: _myPartyTitle,
      onSaved: _onBattleSaved,
    );
  }

  /// 対戦記録の登録後：入力ドラフトをクリアし、相手パーティを空にする。
  void _onBattleSaved() {
    setState(() {
      // 相手パーティをクリア（登録後・参照を保つため中身を入れ替える）。
      _oppParty
        ..clear()
        ..addAll(_ensure6(const []));
      _oppChosen.clear();
      _oppActive = 0;
      // ドラフトをクリア（登録したのでリセット。番号/連番は識別なので保持）。
      _recTn.clear();
      _recRate.clear();
      _recMemo.clear();
      _recFavorite = false;
    });
    _autosaveLast();
  }

  void _snack(String message) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          duration: const Duration(seconds: 1), content: Text(message)));

  /// iPad：自分の技の下に置く天候/フィールド/カウンタ（大きめ・横並び・パネル幅いっぱい）。
  Widget _bottomControls() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: _centerSelect<Weather>(
              '天候', _weather, Weather.values, (w) => w.jp,
              (w) => setState(() => _weather = w),
              onClear: () => _clearWeather()),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _centerSelect<Field>(
              'フィールド', _field, Field.values, (f) => f.jp,
              (f) => setState(() => _field = f),
              onClear: () => _clearField()),
        ),
        const SizedBox(width: 10),
        Expanded(child: _counterInline()),
      ],
    );
  }

  Widget _centerMenu(BattlePokemon opp) {
    // 画面が低い端末では天候/フィールド/カウンタが縦にはみ出すため、中央列も
    // スクロール可能にする（収まるときは _NoBounceScrollBehavior で弾まない）。
    return SizedBox(
      width: 70,
      child: SingleChildScrollView(
        child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // アイコンは間隔を詰め、天候/フィールド/タイマー/カウンタは間隔を広くとる。
          _centerIcon(Icons.menu, 'メニュー',
              () => _scaffoldKey.currentState?.openEndDrawer()),
          const SizedBox(height: 8),
          // タイマー（ハンバーガーの下）。一回押し=スタート/ストップ、長押し=リセット。
          _timerInline(),
          const SizedBox(height: 12),
          _centerIcon(
              Icons.home_filled, 'HOME 使用率（相手）', () => _showHomeInfo(opp)),
          const SizedBox(height: 1),
          Badge(
            isLabelVisible: _similarHits > 0,
            label: Text('$_similarHits'),
            child: _centerIcon(Icons.travel_explore, '類似パーティ検索', () {
              setState(() => _similarHits = 0); // 開いたらバッジを消す
              showSimilarPartyDialog(context, _oppParty);
            }),
          ),
          const SizedBox(height: 1),
          _centerIcon(Icons.history_edu, '対戦記録', _recordBattle),
          // iPad では天候/フィールド/カウンタは「自分の技の下」に移動（footer）。
          if (!_isTablet) ...[
            const SizedBox(height: 12),
            _centerSelect<Weather>('天候', _weather, Weather.values, (w) => w.jp,
                (w) => setState(() => _weather = w),
                onClear: () => _clearWeather()),
            const SizedBox(height: 8),
            _centerSelect<Field>('フィールド', _field, Field.values, (f) => f.jp,
                (f) => setState(() => _field = f),
                onClear: () => _clearField()),
            const SizedBox(height: 12),
            // カウンタ（[0]・直接表示）。ダブルタップでポップアップ、長押しでリセット。
            _counterInline(),
          ],
          const SizedBox(height: 8),
        ],
        ),
      ),
    );
  }

  /// 中央列のコンパクトな天候/フィールド選択（ラベル＋ドロップダウン）。
  /// 長押しで「なし」へクリアする（onClear）。
  Widget _centerSelect<T>(String label, T value, List<T> items,
      String Function(T) jp, ValueChanged<T> onChanged,
      {VoidCallback? onClear}) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label,
            style: const TextStyle(fontSize: 8, color: Colors.black54)),
        GestureDetector(
          onLongPress: onClear,
          child: SizedBox(
            width: 66,
            height: 19,
            child: DropdownButton<T>(
            isExpanded: true,
            isDense: true,
            value: value,
            underline: const SizedBox.shrink(),
            iconSize: 14,
            alignment: Alignment.center,
            style: const TextStyle(fontSize: 11, color: Colors.black87),
            items: [
              for (final it in items)
                DropdownMenuItem(
                    value: it,
                    child: Center(
                        child: Text(jp(it),
                            style: const TextStyle(fontSize: 11)))),
            ],
            onChanged: (v) {
              if (v != null) onChanged(v);
            },
            ),
          ),
        ),
      ],
    );
  }

  /// タップ時の選出：3匹未満なら追加、3匹選出済みなら選出は変えない。
  void _chooseOnTap(List<int> s, int i) {
    if (s.contains(i)) return;
    if (s.length < 3) s.add(i);
  }

  /// HOME 使用率データから性格・持ち物・特性・努力値・技を自動補完する
  /// （旧 champ-edge：登録時に HOME データから反映）。
  Future<void> _fillFromHome(BattlePokemon p) async {
    await HomeStats.instance.load();
    final s = HomeStats.instance;
    final nat = s.entries(p.name, HomeCategory.nature);
    if (nat.isNotEmpty) p.nature = nat.first.value;
    final item = s.entries(p.name, HomeCategory.item);
    if (item.isNotEmpty) p.item = item.first.value;
    final abil = s.entries(p.name, HomeCategory.ability);
    if (abil.isNotEmpty && p.abilityOptions.contains(abil.first.value)) {
      p.ability = abil.first.value;
    }
    // 努力値：合計66（252+252+4+4相当）の最上位を優先。
    for (final e in s.entries(p.name, HomeCategory.ev)) {
      final ev = HomeStats.parseDoryoku(e.value);
      if (ev.fold<int>(0, (a, b) => a + b) == 66) {
        p.ev = ev;
        break;
      }
    }
    // 技：HOME 使用率上位を DB で解決して最大5つ（5枠目＝相手スカウトの暫定技）。
    // ダメージ計算用に**物理・特殊のみ**を採用し、変化技は除外する。
    final moves = <BattleMove>[];
    for (final e in s.entries(p.name, HomeCategory.waza)) {
      final mv = await PokeDb.instance.moveByName(e.value);
      if (mv != null &&
          mv.category != MoveCategory.status &&
          !_isHiddenAttackMove(mv)) {
        moves.add(mv);
        if (moves.length >= 5) break;
      }
    }
    if (moves.isNotEmpty) {
      while (moves.length < 5) {
        moves.add(emptyMove());
      }
      p.moves = moves;
    }
    p.homeFilled = true;
  }

  /// 相手の技を「物理・特殊のみ5枠」に整える。変化技（状態技）は除外し、足りない枠を
  /// HOME 使用率上位（非変化・重複なし）で補完する。5枠目＝スカウト枠の自動補完を兼ねる。
  Future<void> _normalizeOpponentMoves(BattlePokemon p) async {
    await HomeStats.instance.load();
    // iPad（大画面）は変化技も含め HOME 使用率トップ10、iPhone は非変化技5枠。
    final cap = _isTablet ? 10 : 5;
    final includeStatus = _isTablet;
    // 既存技を順に残す（iPhone は変化技を除外）。
    final kept = <BattleMove>[
      for (final m in p.moves)
        if (!m.isEmpty &&
            !_isHiddenAttackMove(m) &&
            (includeStatus || m.category != MoveCategory.status))
          m,
    ];
    final have = kept.map((m) => m.name).toSet();
    // 空き枠を HOME 使用率上位の技で補完。
    for (final e in HomeStats.instance.entries(p.name, HomeCategory.waza)) {
      if (kept.length >= cap) break;
      if (have.contains(e.value)) continue;
      final mv = await PokeDb.instance.moveByName(e.value);
      if (mv != null &&
          !_isHiddenAttackMove(mv) &&
          (includeStatus || mv.category != MoveCategory.status)) {
        kept.add(mv);
        have.add(e.value);
      }
    }
    while (kept.length < cap) {
      kept.add(emptyMove());
    }
    p.moves = kept;
  }

  /// 自分パーティの識別表示（番号/連番/タイトル）。手動入力は廃止し、パーティ編集で
  /// 「使用中」にしたパーティの番号/連番/タイトルを自動で引き継ぐ（対戦記録の絞り込みキー）。
  Widget _partyMetaRow() {
    final label = [
      [_myPartyNum, _myPartySubnum].where((e) => e.isNotEmpty).join('-'),
      _myPartyTitle,
    ].where((e) => e.isNotEmpty).join(' ').trim();
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          const Icon(Icons.badge_outlined, size: 14, color: Colors.black45),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              label.isEmpty
                  ? 'パーティ番号: 未設定（パーティ編集で「使用中」にすると自動設定）'
                  : 'パーティ: $label',
              style: const TextStyle(fontSize: 11, color: Colors.black54),
            ),
          ),
        ],
      ),
    );
  }

  /// パーティ編集ダイアログ：6 枠のポケモンをタップで差し替え。
  Future<void> _editParty(List<BattlePokemon> party, String side) async {
    if (!PokeDb.instance.isOpen) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('DB 未接続のためパーティ編集を利用できません')));
      return;
    }
    final chosen = side == '自分' ? _myChosen : _oppChosen;
    await showDialog<void>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (context, setDlg) => AlertDialog(
          titlePadding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          contentPadding: const EdgeInsets.fromLTRB(12, 0, 12, 0),
          title: Text('$side のパーティ編集（枠をタップで変更）',
              style: const TextStyle(fontSize: 14)),
          content: SizedBox(
            width: 348,
            child: SingleChildScrollView(
              child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // 自分パーティのみ：番号/連番/タイトル（対戦記録の絞り込みキー）。
                if (side == '自分') _partyMetaRow(),
                Wrap(
              spacing: 6,
              runSpacing: 6,
              alignment: WrapAlignment.center,
              children: [
                for (int i = 0; i < party.length; i++)
                  GestureDetector(
                    onTap: () async {
                      final pid = await pickPokemon(context);
                      if (pid == null) return;
                      final p = await PokeDb.instance.buildPokemon(pid);
                      if (p != null) {
                        await _fillFromHome(p); // HOME使用率から技/性格/持物/特性/努力値
                        party[i] = p;
                        chosen.remove(i); // 登録した枠は選出から外す（明示タップで選出）
                        setDlg(() {});
                      }
                    },
                    child: Container(
                      width: 104,
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: typeColorOf(party[i].type1)
                            .withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.black12),
                      ),
                      child: Column(
                        children: [
                          Image.asset(party[i].imageAsset,
                              width: 40,
                              height: 40,
                              errorBuilder: (_, __, ___) =>
                                  const SizedBox(height: 40)),
                          Text(party[i].name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 9)),
                        ],
                      ),
                    ),
                  ),
              ],
                ),
              ],
            ),
            ),
          ),
          actions: [
            // クリア（6枠すべて空に）。
            TextButton.icon(
              icon: const Icon(Icons.clear_all, size: 18),
              label: const Text('クリア'),
              onPressed: () {
                party
                  ..clear()
                  ..addAll(_ensure6(const []));
                chosen.clear(); // クリアで選出も解除
                setDlg(() {});
                _autosaveLast();
              },
            ),
            TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('完了')),
          ],
        ),
      ),
    );
    setState(() {});
  }

  /// 努力値配列 → HOME 形式の文字列（"H2A32S32"。0は省略）。
  static String _evToStr(List<int> ev) {
    const letters = ['H', 'A', 'B', 'C', 'D', 'S'];
    final b = StringBuffer();
    for (var i = 0; i < 6 && i < ev.length; i++) {
      if (ev[i] > 0) b.write('${letters[i]}${ev[i]}');
    }
    return b.toString();
  }

  /// 各カテゴリの現在値（HOME 表示でのハイライト/トグル判定に使う）。
  String _homeCurrent(BattlePokemon t, HomeCategory cat) {
    switch (cat) {
      case HomeCategory.item:
        return t.item;
      case HomeCategory.ability:
        return t.ability;
      case HomeCategory.nature:
        return t.nature;
      case HomeCategory.ev:
        return _evToStr(t.ev);
      case HomeCategory.waza:
        return '';
    }
  }

  /// HOME 使用率（相手の選択ポケモン）を表示。行タップでそのポケモンへ適用。
  /// 既に選択中の値をタップすると未選択（既定値）に戻す。
  /// 旧 champ-edge の HomeFrame（相手＝player1 専用）に相当。
  Future<void> _showHomeInfo(BattlePokemon target) async {
    await HomeStats.instance.load();
    if (!mounted) return;
    final stats = HomeStats.instance;
    if (target.name.isEmpty) return;

    void apply(HomeCategory cat, String value) {
      final isCurrent = _homeCurrent(target, cat) == value;
      switch (cat) {
        case HomeCategory.item:
          target.item = isCurrent ? 'なし' : value;
        case HomeCategory.ability:
          target.ability = isCurrent ? target.abilityOptions.first : value;
        case HomeCategory.nature:
          target.nature = isCurrent ? 'まじめ' : value;
        case HomeCategory.ev:
          target.ev =
              isCurrent ? List<int>.filled(6, 0) : HomeStats.parseDoryoku(value);
        case HomeCategory.waza:
          break;
      }
      _refresh();
    }

    // 画面いっぱいのポップアップ。カテゴリ（持ち物/特性/性格/努力値）を横並びに、
    // 各カテゴリ内は使用率順に縦へ。現在値はハイライト、再タップで解除。
    final cats =
        HomeCategory.values.where((c) => c != HomeCategory.waza).toList();
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => Dialog(
          insetPadding: const EdgeInsets.all(10),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            child: Column(
              children: [
                Row(
                  children: [
                    const Icon(Icons.home_filled, size: 20),
                    const SizedBox(width: 6),
                    Expanded(
                        child: Text('HOME 使用率：${target.name}（タップで反映/解除）',
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold))),
                    IconButton(
                      icon: const Icon(Icons.close),
                      tooltip: '閉じる',
                      onPressed: () => Navigator.of(ctx).pop(),
                    ),
                  ],
                ),
                const Divider(height: 8),
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (final cat in cats) ...[
                        Expanded(
                          child: _homeColumn(
                            cat,
                            stats.entries(target.name, cat),
                            _homeCurrent(target, cat),
                            (v) {
                              apply(cat, v);
                              setLocal(() {});
                            },
                          ),
                        ),
                        if (cat != cats.last) const VerticalDivider(width: 10),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// HOME 1カテゴリ分の縦並び（ラベル＋使用率順の行）。現在値は塗りつぶしで強調。
  Widget _homeColumn(HomeCategory cat, List<HomeEntry> entries,
      String currentValue, ValueChanged<String> onTap) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Colors.blueGrey.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(cat.label,
              style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.blueGrey)),
        ),
        const SizedBox(height: 4),
        Expanded(
          child: entries.isEmpty
              ? const Center(
                  child: Text('データなし',
                      style: TextStyle(fontSize: 13, color: Colors.black38)))
              : ListView.builder(
                  padding: EdgeInsets.zero,
                  itemCount: entries.length,
                  itemBuilder: (ctx, i) {
                    final e = entries[i];
                    final selected =
                        currentValue.isNotEmpty && e.value == currentValue;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 3),
                      child: Material(
                        color: selected
                            ? Colors.blue.withValues(alpha: 0.22)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(5),
                        child: InkWell(
                          onTap: () => onTap(e.value),
                          borderRadius: BorderRadius.circular(5),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 9),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.baseline,
                              textBaseline: TextBaseline.alphabetic,
                              children: [
                                SizedBox(
                                  width: 18,
                                  child: Text('${i + 1}',
                                      style: const TextStyle(
                                          fontSize: 12, color: Colors.black38)),
                                ),
                                Expanded(
                                  child: Text(e.value,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: selected
                                              ? FontWeight.bold
                                              : FontWeight.normal,
                                          color: selected
                                              ? Colors.blue.shade900
                                              : Colors.black87)),
                                ),
                                const SizedBox(width: 3),
                                Text('${e.pct.toStringAsFixed(1)}%',
                                    style: const TextStyle(
                                        fontSize: 12, color: Colors.black45)),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  /// ドロワーメニューの項目タップ。実装済みの項目は実処理、未実装はスナックバー。
  /// パーティ編集を開き、「使用中」にしたパーティを自分パーティ（Top）へ即時反映する。
  /// 番号/連番/タイトルもそのパーティのものを引き継ぐ（対戦記録の絞り込みキー）。
  Future<void> _openPartyManager() async {
    final used = await Navigator.of(context).push<SavedParty>(
      MaterialPageRoute(builder: (_) => const PartyManagerScreen()),
    );
    if (used == null || !mounted) return;
    _applyUsedParty(used);
  }

  /// 使用中パーティを Top へ反映（パーティ本体＋番号/連番/タイトル）。
  void _applyUsedParty(SavedParty used) {
    setState(() {
      _myParty = _ensure6(
          [for (final p in used.party) BattlePokemon.fromJson(p.toJson())]);
      _myActive = 0;
      _myChosen.clear();
      _myPartyNum = used.num;
      _myPartySubnum = used.subnum;
      _myPartyTitle = used.title;
    });
    PartyStore.instance.saveMyPartyMeta(_myPartyNum, _myPartySubnum, _myPartyTitle);
    _autosaveLast();
  }

  /// ボックス（個別ポケモンの保管庫）を開く。
  Future<void> _openBox() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const BoxScreen()),
    );
  }

  void _onMenuTap(String label) {
    switch (label) {
      case '素早さ比較':
        final mine = _myParty[_myActive];
        final opp = _oppParty[_oppActive];
        if (mine.name.isEmpty || opp.name.isEmpty) {
          _snack('素早さ比較は両者のポケモンを選択してから開いてください');
          return;
        }
        showSpeedCompareDialog(context, mine, opp);
      case '重さ比較':
        final mine = _myParty[_myActive];
        final opp = _oppParty[_oppActive];
        if (mine.name.isEmpty || opp.name.isEmpty) {
          _snack('重さ比較は両者のポケモンを選択してから開いてください');
          return;
        }
        showWeightCompareDialog(context, mine, opp);
      case '対戦履歴':
        Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => const BattleHistoryScreen()));
      case '対戦分析':
        Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => const BattleAnalysisScreen()));
      case 'パーティ編集':
        _openPartyManager();
      case 'ボックス編集':
        _openBox();
      case '設定':
        Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const SettingsScreen()));
      default:
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          duration: const Duration(seconds: 1),
          content: Text('「$label」は今後実装予定です'),
        ));
    }
  }

  Widget _buildMenuDrawer() {
    return Drawer(
      width: 260,
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: 8),
          children: [
            // 区切り線で4グループ：比較 / パーティ / 戦績 / 設定。
            for (final (gi, group) in const [
              [
                ['素早さ比較', Icons.speed],
                ['重さ比較', Icons.scale],
              ],
              [
                ['パーティ編集', Icons.edit],
                ['ボックス編集', Icons.inventory_2],
              ],
              [
                ['対戦履歴', Icons.history],
                ['対戦分析', Icons.analytics],
              ],
              [
                ['設定', Icons.settings],
              ],
            ].indexed) ...[
              for (final m in group)
                ListTile(
                  dense: true,
                  leading: Icon(m[1] as IconData, size: 20),
                  title: Text(m[0] as String),
                  onTap: () {
                    Navigator.of(context).pop();
                    _onMenuTap(m[0] as String);
                  },
                ),
              if (gi < 3) const Divider(height: 8, indent: 12, endIndent: 12),
            ],
          ],
        ),
      ),
    );
  }
}

/// 片側（自分 or 相手）のパネル。
class _SidePanel extends StatelessWidget {
  const _SidePanel({
    required this.title,
    required this.accent,
    required this.isTablet,
    required this.moveCount,
    required this.party,
    required this.activeIndex,
    required this.chosen,
    required this.active,
    required this.opponentActive,
    required this.field,
    required this.onChanged,
    required this.onTapPoke,
    required this.onLongPoke,
    required this.onEdit,
    this.footer,
  });

  final String title;
  final Color accent;
  final bool isTablet;
  final int moveCount;
  final Widget? footer; // iPad: 自分側の技の下に天候/フィールド/カウンタを置く
  final List<BattlePokemon> party;
  final int activeIndex;
  final List<int> chosen;
  final BattlePokemon active;
  final BattlePokemon opponentActive;
  final FieldState field;
  final VoidCallback onChanged;
  final ValueChanged<int> onTapPoke;
  final ValueChanged<int> onLongPoke;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(width: 8, height: 16, color: accent),
              const SizedBox(width: 6),
              Text(title,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 14)),
            ],
          ),
          const SizedBox(height: 4),
          // パーティ6体＋編集ボタンをパネル幅いっぱいに等間隔配置。編集ボタンの
          // 右端が下の基本情報カードの右端と揃い、間隔も均等になる。
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              for (int i = 0; i < party.length; i++)
                _PokeIcon(
                  pokemon: party[i],
                  selected: i == activeIndex,
                  chosenNo: chosen.contains(i) ? chosen.indexOf(i) + 1 : 0,
                  size: isTablet ? 74 : 42,
                  onTap: () => onTapPoke(i),
                  onLongPress: () => onLongPoke(i),
                ),
              _MiniBtn(
                icon: Icons.edit,
                tooltip: 'パーティ編集',
                onTap: onEdit,
              ),
            ],
          ),
          SizedBox(height: isTablet ? 10 : 4),
          _SelectedInfo(pokemon: active, onChanged: onChanged),
          SizedBox(height: isTablet ? 8 : 3),
          // 技は moveCount 枠（iPadの相手は10枠）。効果ボタンは各行右端。
          for (int mi = 0; mi < moveCount; mi++) ...[
            _MoveRow(
              pokemon: active,
              moveIndex: mi,
              defender: opponentActive,
              field: field,
              onChanged: onChanged,
              isTablet: isTablet,
            ),
            if (isTablet) const SizedBox(height: 16),
          ],
          if (footer != null) ...[
            SizedBox(height: isTablet ? 10 : 4),
            footer!,
          ],
        ],
      ),
    );
  }
}

class _PokeIcon extends StatelessWidget {
  const _PokeIcon({
    required this.pokemon,
    required this.selected,
    required this.chosenNo,
    required this.onTap,
    this.size = 42,
    this.onLongPress,
  });

  final BattlePokemon pokemon;
  final bool selected;
  final double size;

  /// 選出番号（0=未選出、1〜=選んだ順）。
  final int chosenNo;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    // 空きスロット：アイコンは出さず、白背景＋枠のみ表示する。
    final isEmpty = pokemon.name.isEmpty;
    return GestureDetector(
      onTap: onTap,
      onLongPress: onLongPress,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: isEmpty
              ? Colors.white
              : typeColorOf(pokemon.type1).withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: (selected && !isEmpty) ? Colors.orange : Colors.black12,
            width: (selected && !isEmpty) ? 2.5 : 1,
          ),
        ),
        child: isEmpty
            ? null
            : Stack(
          children: [
            Center(
              child: Image.asset(
                pokemon.imageAsset,
                width: size - 6,
                height: size - 6,
                fit: BoxFit.contain,
                filterQuality: FilterQuality.medium,
                errorBuilder: (_, __, ___) => Center(
                  child: Text(
                      pokemon.name.isEmpty
                          ? ''
                          : pokemon.name.characters.first,
                      style: const TextStyle(fontSize: 12)),
                ),
              ),
            ),
            if (chosenNo > 0)
              Positioned(
                right: 0,
                top: 0,
                child: Container(
                  width: 15,
                  height: 15,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(
                    color: Colors.green,
                    shape: BoxShape.circle,
                  ),
                  child: Text('$chosenNo',
                      style: const TextStyle(
                          fontSize: 10,
                          color: Colors.white,
                          fontWeight: FontWeight.bold)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// パーティ横の小さい操作ボタン。
class _MiniBtn extends StatelessWidget {
  const _MiniBtn(
      {required this.icon, required this.tooltip, required this.onTap});
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          width: 40,
          height: 42,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Colors.blueGrey.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, size: 24, color: Colors.black54),
        ),
      ),
    );
  }
}

/// 選択ポケモンの基本情報カード（タップで各項目編集）。
class _SelectedInfo extends StatelessWidget {
  const _SelectedInfo({required this.pokemon, required this.onChanged});
  final BattlePokemon pokemon;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      child: Padding(
        padding: const EdgeInsets.all(6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 名前行：画像 + （名前／タイプ1／タイプ2 を縦積み） ... 右端に急所
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                GestureDetector(
                  // ポケモンを押すとメガ進化（フォーム切替）。
                  onTap: () async {
                    final ok = await PokeDb.instance.formChange(pokemon);
                    if (ok) onChanged();
                  },
                  child: Image.asset(pokemon.imageAsset,
                      width: 30,
                      height: 30,
                      fit: BoxFit.contain,
                      errorBuilder: (_, __, ___) => const SizedBox(width: 30)),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Flexible(
                        // 名前タップでもフォーム切替（画像タップと同じ）。
                        child: GestureDetector(
                          onTap: () async {
                            final ok =
                                await PokeDb.instance.formChange(pokemon);
                            if (ok) onChanged();
                          },
                          child: Text(pokemon.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontSize: 13, fontWeight: FontWeight.bold)),
                        ),
                      ),
                      const SizedBox(width: 5),
                      // タイプ（名前の横に2列＝縦に2段で表示・タップで変更）
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _EditableType(
                            type: pokemon.type1,
                            onTap: () async {
                              final v = await _pickType(context, pokemon.type1,
                                  allowNone: false);
                              if (v != null) {
                                pokemon.type1 = v;
                                onChanged();
                              }
                            },
                          ),
                          if (pokemon.type2 != PokeType.none) ...[
                            const SizedBox(height: 2),
                            _EditableType(
                              type: pokemon.type2,
                              onTap: () async {
                                final v = await _pickType(
                                    context, pokemon.type2,
                                    allowNone: true);
                                if (v != null) {
                                  pokemon.type2 = v;
                                  onChanged();
                                }
                              },
                            ),
                          ],
                        ],
                      ),
                      // 重さ（kg）：重量比技の参考（旧 champ-edge の基本情報欄相当）
                      if (pokemon.weight > 0) ...[
                        const SizedBox(width: 5),
                        Text('${pokemon.weight}kg',
                            style: const TextStyle(
                                fontSize: 9, color: Colors.black54)),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 4),
                _toggleChip('急所', pokemon.critical, () {
                  pokemon.critical = !pokemon.critical;
                  onChanged();
                }),
              ],
            ),
            const SizedBox(height: 2),
            // 特性 / 持ち物 / 性格
            Wrap(
              spacing: 5,
              runSpacing: 3,
              children: [
                _editChip(
                    context,
                    '特性',
                    // 条件付き特性は現在値を併記（例: マルチスケイル[有効]）
                    pokemon.abilityValue.isEmpty
                        ? pokemon.ability
                        : '${pokemon.ability}[${pokemon.abilityValue}]',
                    () async {
                  // DB 接続時はそのポケモンの特性候補（ability1/2/3）を引く。
                  var opts = pokemon.abilityOptions;
                  if (PokeDb.instance.isOpen) {
                    final dbOpts = await PokeDb.instance.abilitiesOf(pokemon.pid);
                    if (dbOpts.isNotEmpty) opts = dbOpts;
                  }
                  if (!context.mounted) return;
                  final usage = {
                    for (final e in HomeStats.instance
                        .entries(pokemon.name, HomeCategory.ability))
                      e.value: e.pct
                  };
                  final v = await _pickString(
                      context, '特性を選択', opts, pokemon.ability,
                      usage: usage);
                  if (v != null) {
                    pokemon.ability = v;
                    onChanged();
                  }
                },
                    showLabel: false,
                    onDetail: () => _showAbilityDetail(context, pokemon),
                    onLongPress: () =>
                        _toggleAbilityValue(context, pokemon)),
                _editChip(context, '持ち物',
                    pokemon.item == 'なし' ? 'もちものなし' : pokemon.item, () async {
                  final usage = {
                    for (final e in HomeStats.instance
                        .entries(pokemon.name, HomeCategory.item))
                      e.value: e.pct
                  };
                  final v = await _pickSearchable(context, '持ち物を検索',
                      loadedItemOptions, pokemon.item,
                      hint: '持ち物名で検索（例: いのち）', usage: usage);
                  if (v != null) {
                    pokemon.item = v;
                    onChanged();
                  }
                },
                    showLabel: false,
                    onDetail: pokemon.item == 'なし'
                        ? null
                        : () => _showEffectDetail(context, '持ち物: ${pokemon.item}',
                            PokeDb.instance.itemEffect(pokemon.item))),
                _editChip(context, '性格', pokemon.nature, () async {
                  final v = await _pickNature(context, pokemon.nature);
                  if (v != null) {
                    pokemon.nature = v;
                    onChanged();
                  }
                }, showLabel: false),
              ],
            ),
            const SizedBox(height: 2),
            // やけど / じゅうでん / 定数 / 壁
            Wrap(
              spacing: 5,
              runSpacing: 3,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _toggleChip('やけど', pokemon.status == Ailment.burn, () {
                  pokemon.status =
                      pokemon.status == Ailment.burn ? Ailment.none : Ailment.burn;
                  onChanged();
                }),
                _toggleChip('じゅうでん', pokemon.charging, () {
                  pokemon.charging = !pokemon.charging;
                  onChanged();
                }),
                // 定数ダメージ（ステロ＋毎ターンのチップ）。確定数計算に反映。
                _editChip(context, '定数', _constLabel(pokemon),
                    () => _editConstantDamage(context, pokemon, onChanged),
                    showLabel: false),
                _editChip(context, '壁', _wallLabel(pokemon.wall), () async {
                  final v = await _pickEnum<Wall>(context, '壁', Wall.values,
                      pokemon.wall, _wallLabel);
                  if (v != null) {
                    pokemon.wall = v;
                    onChanged();
                  }
                }, showLabel: false),
              ],
            ),
            const SizedBox(height: 3),
            // 種族値・実数値（タップで努力値/ランク編集・長押しでランク一括クリア）
            InkWell(
              onTap: () async {
                await showDialog<void>(
                  context: context,
                  builder: (_) => _StatEditorDialog(pokemon: pokemon),
                );
                onChanged();
              },
              onLongPress: () {
                pokemon.boosts.fillRange(1, 6, 0);
                onChanged();
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                    duration: Duration(milliseconds: 900),
                    content: Text('ランクをクリアしました')));
              },
              child: _StatTable(pokemon: pokemon),
            ),
          ],
        ),
      ),
    );
  }

  Widget _editChip(
      BuildContext context, String label, String value, VoidCallback onTap,
      {bool showLabel = true,
      VoidCallback? onDetail,
      VoidCallback? onLongPress}) {
    // showLabel=false のときは選択値のみ表示（未選択時のみラベルをプレースホルダ表示）。
    final text =
        showLabel ? '$label: $value  ▾' : '${value.isEmpty ? label : value}  ▾';
    return InkWell(
      onTap: onTap,
      // ダブルタップ＝効果詳細。長押し＝特性の有効/無効を即時切替（指定時のみ）。
      onDoubleTap: onDetail,
      onLongPress: onLongPress,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.blueGrey.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Colors.black12),
        ),
        child: Text(text,
            style: const TextStyle(fontSize: 10, color: Colors.black87)),
      ),
    );
  }

  /// 特性チップ長押し：有効/無効（または値）を即時切替する。
  /// - 値を持つ特性（abilityValues）はリストを循環（有効/無効はトグル、多値は順送り）。
  /// - 登場時ランク特性（いかく等）は登場時ランク効果の有効/無効をトグル。
  /// - それ以外は切替値がない旨を表示。結果はスナックバーで知らせる。
  void _toggleAbilityValue(BuildContext context, BattlePokemon p) {
    String msg;
    final values = abilityValues[p.ability];
    if (values != null) {
      final i = values.indexOf(p.abilityValue);
      p.abilityValue = values[(i + 1) % values.length];
      msg = '${p.ability}: ${p.abilityValue}';
    } else if (appearRankAbilities.contains(p.ability)) {
      p.abilityDisabled = !p.abilityDisabled;
      if (p.abilityDisabled) p.appearRankApplied = false;
      msg = '${p.ability}: 登場時ランク効果 ${p.abilityDisabled ? '無効' : '有効'}';
    } else {
      msg = '${p.ability} には有効/無効の切替はありません';
    }
    onChanged();
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        duration: const Duration(milliseconds: 900), content: Text(msg)));
  }

  /// 特性の効果詳細（ダブルタップで起動）。登場時ランク特性（いかく等）には
  /// 自動適用の無効化スイッチ、条件付き特性には値切替チップも出す。
  Future<void> _showAbilityDetail(
      BuildContext context, BattlePokemon p) async {
    final text = await PokeDb.instance.abilityEffect(p.ability);
    if (!context.mounted) return;
    final isRank = appearRankAbilities.contains(p.ability);
    final values = abilityValues[p.ability];
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text('特性: ${p.ability}', style: const TextStyle(fontSize: 15)),
          content: SizedBox(
            width: 320,
            child: SingleChildScrollView(
              child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text((text == null || text.isEmpty) ? '効果情報がありません' : text,
                    style: const TextStyle(fontSize: 13)),
                // 条件付き特性の値切替（旧 champ-edge ABILITY_VALUES）
                if (values != null) ...[
                  const Divider(height: 18),
                  Row(
                    children: [
                      const Text('特性値: ',
                          style:
                              TextStyle(fontSize: 12, color: Colors.black54)),
                      Expanded(
                        child: Wrap(
                          spacing: 4,
                          runSpacing: 4,
                          children: [
                            for (final v in values)
                              InkWell(
                                onTap: () {
                                  setLocal(() => p.abilityValue = v);
                                  onChanged();
                                },
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: p.abilityValue == v
                                        ? Colors.orange.withValues(alpha: 0.25)
                                        : Colors.blueGrey
                                            .withValues(alpha: 0.08),
                                    borderRadius: BorderRadius.circular(4),
                                    border: Border.all(
                                        color: p.abilityValue == v
                                            ? Colors.orange
                                            : Colors.black12),
                                  ),
                                  child: Text(v,
                                      style: const TextStyle(fontSize: 12)),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
                if (isRank) ...[
                  const Divider(height: 18),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    title: const Text('登場時のランク効果を無効化',
                        style: TextStyle(fontSize: 13)),
                    subtitle: const Text('次の選出から反映されます',
                        style: TextStyle(fontSize: 11)),
                    value: p.abilityDisabled,
                    onChanged: (v) {
                      setLocal(() => p.abilityDisabled = v);
                      // 無効化したら適用済みフラグを下ろし、次の選出で再評価させる。
                      if (v) p.appearRankApplied = false;
                      onChanged();
                    },
                  ),
                ],
              ],
              ),
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('閉じる')),
          ],
        ),
      ),
    );
  }

  Future<void> _showEffectDetail(
      BuildContext context, String title, Future<String?> effect) async {
    final text = await effect;
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title, style: const TextStyle(fontSize: 15)),
        content: SizedBox(
          width: 320,
          child: SingleChildScrollView(
            child: Text(
              (text == null || text.isEmpty) ? '効果情報がありません' : text,
              style: const TextStyle(fontSize: 13),
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('閉じる')),
        ],
      ),
    );
  }

  Widget _toggleChip(String label, bool on, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: on
              ? Colors.orange.withValues(alpha: 0.22)
              : Colors.blueGrey.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: on ? Colors.orange : Colors.black12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(on ? Icons.check_box : Icons.check_box_outline_blank,
                size: 12, color: on ? Colors.orange.shade800 : Colors.black38),
            const SizedBox(width: 2),
            Text(label,
                style: const TextStyle(fontSize: 10, color: Colors.black87)),
          ],
        ),
      ),
    );
  }

  /// 定数チップのラベル（ステロ＋毎ターン割合の合計を分数で表示）。
  String _constLabel(BattlePokemon p) {
    final parts = <String>[];
    if (p.hasStealthRock) parts.add('ステロ');
    if (p.spikes > 0) parts.add('まきびし${p.spikes}');
    if (p.constantDamage > 0) parts.add(_fracStr(p.constantDamage));
    // 定数があるときは値のみ（「定数」ラベルは省く）。無いときだけ「定数なし」。
    return parts.isEmpty ? '定数なし' : parts.join('+');
  }

  static int _gcd(int a, int b) => b == 0 ? a : _gcd(b, a % b);

  /// 0.1875 のような割合を既約分数 "3/16" に変換（分母は 480 を基準）。
  static String _fracStr(double v) {
    const base = 480;
    final n = (v * base).round();
    if (n <= 0) return '0';
    final g = _gcd(n, base);
    return '${n ~/ g}/${base ~/ g}';
  }

  /// 定数ダメージ編集ダイアログ（ステロ切替＋毎ターンチップの加算/クリア）。
  /// 旧 champ-edge の「定数ダメージ」一覧を実用化したもの。
  Future<void> _editConstantDamage(
      BuildContext context, BattlePokemon p, VoidCallback onChanged) async {
    // (ラベル, 加算割合)。毎ターンのチップダメージ源。
    const sources = <(String, double)>[
      ('やどりぎ 1/8', 1 / 8),
      ('どく 1/8', 1 / 8),
      ('もうどく +1/16', 1 / 16),
      ('やけど 1/16', 1 / 16),
      ('すなあらし 1/16', 1 / 16),
      ('のろい 1/4', 1 / 4),
      ('あくむ 1/4', 1 / 4),
      ('バインド 1/8', 1 / 8),
      ('しおづけ 1/16', 1 / 16),
      ('ゴツゴツメット 1/6', 1 / 6),
      ('いのちのたま 1/10', 1 / 10),
      ('くろいヘドロ 1/8', 1 / 8),
    ];
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) {
          final entryEff =
              DamageCalc.getTypeEffectiveness(PokeType.rock, p.types);
          return AlertDialog(
            title: const Text('定数ダメージ', style: TextStyle(fontSize: 15)),
            contentPadding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            // 横幅を広げ・チップをコンパクトにしてスクロール無しで収める。
            content: SizedBox(
              width: 460,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                  // ステルスロック（登場時1回）。
                  InkWell(
                    onTap: () {
                      setLocal(() => p.hasStealthRock = !p.hasStealthRock);
                      onChanged();
                    },
                    child: Row(
                      children: [
                        Icon(
                            p.hasStealthRock
                                ? Icons.check_box
                                : Icons.check_box_outline_blank,
                            size: 18,
                            color: p.hasStealthRock
                                ? Colors.orange.shade800
                                : Colors.black38),
                        const SizedBox(width: 4),
                        Text(
                            'ステルスロック（登場時 ${_fracStr(entryEff / 8)}・いわ×$entryEff）',
                            style: const TextStyle(fontSize: 12)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 4),
                  // まきびし（登場時1回・枚数で 1/8・1/6・1/4）。タップで 0→1→2→3 循環。
                  InkWell(
                    onTap: () {
                      setLocal(() => p.spikes = (p.spikes + 1) % 4);
                      onChanged();
                    },
                    child: Row(
                      children: [
                        Icon(
                            switch (p.spikes) {
                              1 => Icons.filter_1,
                              2 => Icons.filter_2,
                              3 => Icons.filter_3,
                              _ => Icons.check_box_outline_blank,
                            },
                            size: 18,
                            color: p.spikes > 0
                                ? Colors.orange.shade800
                                : Colors.black38),
                        const SizedBox(width: 4),
                        Text(
                            'まきびし（登場時${p.spikes == 0 ? "なし" : "${p.spikes}枚 ${_fracStr(p.spikesFraction)}"}・タップで枚数）',
                            style: const TextStyle(fontSize: 12)),
                      ],
                    ),
                  ),
                  const Divider(height: 12),
                  Text('毎ターンのチップを加算',
                      style: TextStyle(
                          fontSize: 11, color: Colors.grey.shade600)),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 5,
                    runSpacing: 5,
                    children: [
                      for (final (label, frac) in sources)
                        InkWell(
                          onTap: () {
                            setLocal(() => p.constantDamage += frac);
                            onChanged();
                          },
                          borderRadius: BorderRadius.circular(4),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.blueGrey.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(label,
                                style: const TextStyle(fontSize: 11)),
                          ),
                        ),
                    ],
                  ),
                  const Divider(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                            '現在の定数: ${p.constantDamage > 0 ? _fracStr(p.constantDamage) : "なし"}',
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                      TextButton(
                        onPressed: () {
                          // 定数だけでなく登場時ハザード（ステロ/まきびし）も一括クリア。
                          setLocal(() {
                            p.constantDamage = 0;
                            p.hasStealthRock = false;
                            p.spikes = 0;
                          });
                          onChanged();
                        },
                        child: const Text('クリア'),
                      ),
                    ],
                  ),
                ],
                ),
              ),
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('閉じる')),
            ],
          );
        },
      ),
    );
  }
}

/// 壁の表示ラベル（物理/特殊/両壁）。エンジンのリフレクター/ひかりのかべ/
/// オーロラベールにマッピングする（挙動は同じ）。
String _wallLabel(Wall w) => switch (w) {
      Wall.none => '壁なし',
      Wall.reflect => '物理壁',
      Wall.lightScreen => '特殊壁',
      Wall.auroraVeil => '両壁',
    };

/// 種族値・実数値のコンパクト表（タップで編集ダイアログ）。
class _StatTable extends StatelessWidget {
  const _StatTable({required this.pokemon});
  final BattlePokemon pokemon;

  static const _labels = ['H', 'A', 'B', 'C', 'D', 'S'];

  /// ランク補正を反映した実数値（pokemon.py get_ranked_stats 準拠）。
  int _rankedStat(int i) {
    final base = pokemon.stats[i];
    final rank = pokemon.boosts[i];
    if (i == 0 || rank == 0) return base;
    if (rank > 0) return (base * (2 + rank)) ~/ 2;
    return (base * 2) ~/ (2 - rank);
  }

  @override
  Widget build(BuildContext context) {
    // 実数値（横にランク）／努力値 を表示
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // 各行を値カラムと同じ高さに合わせ、ラベルを各値のラインに揃える。
            Text(' ', style: TextStyle(fontSize: 9)),
            SizedBox(
              height: 15,
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('実数',
                    style: TextStyle(fontSize: 8, color: Colors.black45)),
              ),
            ),
            Text('努力', style: TextStyle(fontSize: 9, color: Colors.black45)),
          ],
        ),
        for (int i = 0; i < 6; i++)
          Expanded(
            child: Column(
              children: [
                Text(_labels[i],
                    style:
                        const TextStyle(fontSize: 9, color: Colors.black54)),
                // 実数値（ランク反映）＋ ランク表示。横幅に収め一段ずれを防止。
                SizedBox(
                  height: 15,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text('${_rankedStat(i)}',
                            style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: pokemon.boosts[i] > 0
                                    ? Colors.red.shade700
                                    : pokemon.boosts[i] < 0
                                        ? Colors.blue.shade700
                                        : Colors.black)),
                        if (pokemon.boosts[i] != 0)
                          Text(
                              ' ${pokemon.boosts[i] > 0 ? '+' : ''}${pokemon.boosts[i]}',
                              style: TextStyle(
                                  fontSize: 8,
                                  fontWeight: FontWeight.bold,
                                  color: pokemon.boosts[i] > 0
                                      ? Colors.red
                                      : Colors.blue)),
                      ],
                    ),
                  ),
                ),
                Text('${pokemon.ev[i]}',
                    style: const TextStyle(
                        fontSize: 9, color: Colors.blueGrey)),
              ],
            ),
          ),
      ],
    );
  }
}

/// 技のトグル効果（ランク変化/タイプ変更/じこあんじ/スキルスワップ/コートチェンジ）を
/// attacker（技の使用側）/ defender（相手）へ適用/解除する。オーラぐるまは toMoveState 側で処理。
void applyMoveToggle(
    WazaEffect e, BattlePokemon attacker, BattlePokemon defender, bool applied) {
  final sign = applied ? 1 : -1;
  switch (e.kind) {
    case WazaEffectKind.selfRank:
      for (var i = 0; i < 6; i++) {
        attacker.boosts[i] =
            (attacker.boosts[i] + sign * e.rankDelta[i]).clamp(-6, 6);
      }
    case WazaEffectKind.opponentRank:
      for (var i = 0; i < 6; i++) {
        defender.boosts[i] =
            (defender.boosts[i] + sign * e.rankDelta[i]).clamp(-6, 6);
      }
    case WazaEffectKind.typeChange:
      final t = e.targetOpponent ? defender : attacker;
      if (applied) {
        t.typeBackup ??= [t.type1, t.type2];
        if (e.removeType) {
          if (t.type1 == e.changeType) {
            t.type1 = t.type2;
            t.type2 = PokeType.none;
          } else if (t.type2 == e.changeType) {
            t.type2 = PokeType.none;
          }
        } else {
          t.type1 = e.changeType;
          t.type2 = PokeType.none;
        }
      } else if (t.typeBackup != null) {
        t.type1 = t.typeBackup![0];
        t.type2 = t.typeBackup![1];
        t.typeBackup = null;
      }
    case WazaEffectKind.copyBoosts:
      // じこあんじ：相手のランクを自分へコピー（解除で復元）。
      if (applied) {
        attacker.boostsBackup ??= List<int>.from(attacker.boosts);
        for (var i = 0; i < 6; i++) {
          attacker.boosts[i] = defender.boosts[i];
        }
      } else if (attacker.boostsBackup != null) {
        for (var i = 0; i < 6; i++) {
          attacker.boosts[i] = attacker.boostsBackup![i];
        }
        attacker.boostsBackup = null;
      }
    case WazaEffectKind.swapAbility:
      // スキルスワップ：特性入替（自己逆）。
      final a = attacker.ability;
      attacker.ability = defender.ability;
      defender.ability = a;
    case WazaEffectKind.swapField:
      // コートチェンジ：壁・定数ダメージ・ステロを攻守入替（自己逆）。
      final w = attacker.wall;
      attacker.wall = defender.wall;
      defender.wall = w;
      final cd = attacker.constantDamage;
      attacker.constantDamage = defender.constantDamage;
      defender.constantDamage = cd;
      final sr = attacker.hasStealthRock;
      attacker.hasStealthRock = defender.hasStealthRock;
      defender.hasStealthRock = sr;
    default:
      break; // moveTypeChange は toMoveState で反映
  }
}

/// 技1行（タップで差し替え）。
class _MoveRow extends StatelessWidget {
  const _MoveRow({
    required this.pokemon,
    required this.moveIndex,
    required this.defender,
    required this.field,
    required this.onChanged,
    this.isTablet = false,
  });

  final BattlePokemon pokemon;
  final int moveIndex;
  final BattlePokemon defender;
  final FieldState field;
  final VoidCallback onChanged;
  final bool isTablet;

  /// 技詳細（waza_data）を長押しで表示（旧 champ-edge の技右クリック相当）。
  Future<void> _showMoveDetail(BuildContext context) async {
    final move = moveIndex < pokemon.moves.length
        ? pokemon.moves[moveIndex]
        : emptyMove();
    if (move.isEmpty) return;
    final d = await PokeDb.instance.moveDetail(move.name);
    if (!context.mounted) return;
    String onOff(Object? v) => (v == 1 || v == true) ? '○' : '—';
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('技: ${move.name}', style: const TextStyle(fontSize: 15)),
        content: SizedBox(
          width: 320,
          child: SingleChildScrollView(
          child: d == null
              ? const Text('詳細情報がありません', style: TextStyle(fontSize: 13))
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'タイプ: ${d['type'] ?? '—'}   分類: ${d['category'] ?? '—'}\n'
                      '威力: ${d['power'] ?? '—'}   命中: ${d['hit'] ?? '—'}   PP: ${d['pp'] ?? '—'}\n'
                      '接触: ${onOff(d['is_touch'])}   まもる: ${onOff(d['is_guard'])}'
                      '   対象: ${d['target'] ?? '—'}',
                      style: const TextStyle(fontSize: 12, height: 1.5),
                    ),
                    const Divider(height: 14),
                    Text(
                      ((d['description'] as String?)?.trim().isNotEmpty ??
                              false)
                          ? (d['description'] as String).trim()
                          : '説明文がありません',
                      style: const TextStyle(fontSize: 13),
                    ),
                  ],
                ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('閉じる')),
        ],
      ),
    );
  }

  /// 技スロットへ設定（範囲外なら追加）。
  void _setMove(BattleMove v) {
    if (moveIndex < pokemon.moves.length) {
      pokemon.moves[moveIndex] = v;
    } else {
      while (pokemon.moves.length < moveIndex) {
        pokemon.moves.add(emptyMove());
      }
      pokemon.moves.add(v);
    }
  }

  @override
  Widget build(BuildContext context) {
    final move = moveIndex < pokemon.moves.length
        ? pokemon.moves[moveIndex]
        : emptyMove();
    // 未設定スロット：タップで技を選択。
    if (move.isEmpty) {
      final emptyBox = InkWell(
        onTap: () async {
          final v = await _pickMove(context, move, ownerName: pokemon.name);
          if (v != null) {
            _setMove(v);
            onChanged();
          }
        },
        child: Container(
          height: isTablet ? 40 : 28,
          padding: const EdgeInsets.symmetric(horizontal: 6),
          alignment: Alignment.centerLeft,
          decoration: BoxDecoration(
            color: Colors.grey.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(5),
          ),
          child: Text('—',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade400)),
        ),
      );
      return _withEffectButton(emptyBox, move);
    }
    // 相手が未設定（防御側が空＝HP0）ならダメージ計算は無効。技名のみ表示する。
    final hasDefender = defender.name.isNotEmpty && defender.hp > 0;
    final result = hasDefender
        ? DamageCalc.calculateDamage(
            pokemon.toAttacker(),
            defender.toDefender(),
            move.toMoveState(
                critical: pokemon.critical,
                skillLink: pokemon.ability == 'スキルリンク'),
            field,
          )
        : null;
    final hp = defender.hp;
    final minPer = result != null ? result.minDamage / hp * 100 : 0.0;
    final ko = result != null ? _koText(result, defender) : '';
    // 技ラベル（枠）。効果ボタンの分だけ枠を短くし、ボタンは枠の外（右）に置く。
    // タップ＝技変更／長押し＝加算ツール／ダブルタップ＝技詳細（行全体で統一）。
    final box = InkWell(
      onTap: () async {
        final v = await _pickMove(context, move, ownerName: pokemon.name);
        if (v != null) {
          _setMove(v);
          onChanged();
        }
      },
      onLongPress: () => showAdderDialog(context, pokemon, defender, field),
      onDoubleTap: () => _showMoveDetail(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.grey.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(5),
        ),
        child: !hasDefender
            // 相手未設定：ダメージは出さず技名のみ表示。
            ? Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text(move.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        fontSize: isTablet ? 13 : 11,
                        fontWeight: FontWeight.w600)),
              )
            : Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                // 技名（iPadでは枠を広げて省略させない）
                SizedBox(
                  width: isTablet ? 200 : 88,
                  child: Text(move.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          fontSize: isTablet ? 13 : 11,
                          fontWeight: FontWeight.w600)),
                ),
                // 中央：ダメージ（1行固定）
                Expanded(
                  child: Center(
                    child: Text('${result!.minDamage}〜${result.maxDamage}',
                        maxLines: 1,
                        softWrap: false,
                        overflow: TextOverflow.visible,
                        style: TextStyle(
                            fontSize: isTablet ? 14 : 12,
                            fontWeight: FontWeight.bold)),
                  ),
                ),
                // 割合・確定数（右寄せ）
                SizedBox(
                  width: isTablet ? 180 : 140,
                  child: Text(
                    '${minPer.toStringAsFixed(1)}〜${result.percentage.toStringAsFixed(1)}%'
                    '${ko.isEmpty ? '' : ' $ko'}',
                    textAlign: TextAlign.right,
                    maxLines: 1,
                    overflow: TextOverflow.clip,
                    style: TextStyle(
                        fontSize: isTablet ? 10 : 8,
                        fontWeight: FontWeight.w600,
                        color:
                            ko.startsWith('確定') ? Colors.red : Colors.black54),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 1),
            _DamageBar(minPer: minPer, maxPer: result.percentage),
          ],
        ),
      ),
    );
    return _withEffectButton(box, move);
  }

  /// 技ラベル（枠）を短くし、枠の外（右）に効果ボタンを置く。効果の無い技は
  /// 同じ幅の空きスロットで右端を揃える。
  Widget _withEffectButton(Widget box, BattleMove move) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(child: box),
          SizedBox(
            width: 30,
            child: move.hasEffect
                ? Align(
                    alignment: Alignment.center, child: _effectButton(move))
                : null,
          ),
        ],
      ),
    );
  }

  /// 効果ボタンのラベル（×n／＋／−／型）。
  static String _effectLabel(BattleMove m) {
    final e = m.effect;
    switch (e.kind) {
      case WazaEffectKind.selfRank:
      case WazaEffectKind.opponentRank:
        final sum = e.rankDelta.fold<int>(0, (a, b) => a + b);
        return sum >= 0 ? '＋' : '−';
      case WazaEffectKind.typeChange:
      case WazaEffectKind.moveTypeChange:
        return '型';
      case WazaEffectKind.copyBoosts:
        return 'コ';
      case WazaEffectKind.swapAbility:
        return '特';
      case WazaEffectKind.swapField:
        return '場';
      default:
        final v = m.currentEffectValue;
        final s = v == v.roundToDouble() ? v.toInt().toString() : '$v';
        return '×$s';
    }
  }

  /// 効果種別の色。
  static Color _effectColor(WazaEffectKind kind) {
    switch (kind) {
      case WazaEffectKind.multiHit:
        return Colors.teal;
      case WazaEffectKind.selfRank:
        return Colors.green;
      case WazaEffectKind.opponentRank:
        return Colors.deepOrange;
      case WazaEffectKind.typeChange:
      case WazaEffectKind.moveTypeChange:
        return Colors.purple;
      case WazaEffectKind.copyBoosts:
        return Colors.blueGrey;
      case WazaEffectKind.swapAbility:
        return Colors.brown;
      case WazaEffectKind.swapField:
        return Colors.cyan;
      default:
        return Colors.indigo;
    }
  }

  /// 一過性効果（ランク変化/タイプ変更/other_effect）を適用/解除する。
  void _applyToggleEffect(WazaEffect e, bool applied) =>
      applyMoveToggle(e, pokemon, defender, applied);

  /// 技効果ボタン。ランク技（＋/−）はタップで累積適用・長押しでリセット、
  /// その他のトグル（型/コ/特/場）はタップで ON/OFF、×n は循環。
  Widget _effectButton(BattleMove move) {
    final e = move.effect;
    final color = _effectColor(e.kind);
    final isRank = e.kind == WazaEffectKind.selfRank ||
        e.kind == WazaEffectKind.opponentRank;
    final n = move.currentEffectValue.toInt();
    final on = e.isToggle && n >= 1;
    return InkWell(
      onTap: () {
        if (isRank) {
          // 1回分を累積適用。
          _applyToggleEffect(e, true);
          _setMove(move.copyWith(effectValue: n + 1));
        } else if (e.isToggle) {
          final nxt = e.next(move.currentEffectValue);
          _applyToggleEffect(e, nxt == 1);
          _setMove(move.copyWith(effectValue: nxt));
        } else {
          _setMove(move.copyWith(effectValue: e.next(move.currentEffectValue)));
        }
        onChanged();
      },
      onLongPress: !e.isToggle
          ? null
          : () {
              // 長押しで適用分をすべて解除（ランクは n 回分、他は1回）。
              final times = isRank ? n : (n >= 1 ? 1 : 0);
              for (var k = 0; k < times; k++) {
                _applyToggleEffect(e, false);
              }
              _setMove(move.copyWith(effectValue: 0));
              onChanged();
            },
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: on ? 0.85 : 0.15),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: color.withValues(alpha: 0.5)),
        ),
        child: Text(_effectLabel(move),
            style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: on ? Colors.white : color)),
      ),
    );
  }

  /// 確定数（元 champ-edge の ko_text 準拠）。n 発で倒せる乱数を 1→4 の順で探し、
  /// 16/16 なら「確定n発」、それ未満は「乱数n発(k/16)」と分数付きで返す。
  /// 確定数（元 champ-edge の ko_text 準拠）。ステルスロックは登場時1回の entry、
  /// 定数ダメージ（やどりぎ/砂嵐/どく等）は毎ターン constant*n として加算する。
  String _koText(DamageResult r, BattlePokemon def) {
    if (r.damages.isEmpty) return '';
    final hp = def.hp;
    final entryRock = def.hasStealthRock
        ? (hp *
                DamageCalc.getTypeEffectiveness(PokeType.rock, def.types) /
                8)
            .floor()
        : 0;
    final entrySpikes = (hp * def.spikesFraction).floor();
    final entry = entryRock + entrySpikes;
    final effHp = (hp - entry) < 1 ? 1 : hp - entry;
    final constant = (hp * def.constantDamage).floor();
    for (var n = 1; n <= 4; n++) {
      final k = r.damages.where((d) => d * n + constant * n >= effHp).length;
      if (k == 16) return '確定$n発';
      if (k > 0) return '乱数$n発($k/16)';
    }
    return '';
  }
}

/// タップで変更できるタイプ表示（小さめ）。none は「＋タイプ」の薄い表示。
class _EditableType extends StatelessWidget {
  const _EditableType({required this.type, required this.onTap});
  final PokeType type;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: type == PokeType.none
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(3),
                border: Border.all(color: Colors.black26),
              ),
              child: const Text('＋タイプ',
                  style: TextStyle(fontSize: 8, color: Colors.black38)),
            )
          : Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(
                color: typeColorOf(type),
                borderRadius: BorderRadius.circular(3),
              ),
              child: Text(type.jp,
                  style: const TextStyle(
                      fontSize: 9,
                      color: Colors.white,
                      fontWeight: FontWeight.w600)),
            ),
    );
  }
}

class _TypeChip extends StatelessWidget {
  const _TypeChip(this.type);
  final PokeType type;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(left: 2),
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
      decoration: BoxDecoration(
        color: typeColorOf(type),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Text(type.jp,
          style: const TextStyle(
              fontSize: 9, color: Colors.white, fontWeight: FontWeight.w600)),
    );
  }
}

/// 技ごとの残り HP バー（旧 champ-edge HpBarFrame 準拠）。
///
/// 左から「確定で残る HP（明色）」「不確定帯=min〜max（暗色）」「確定で失う HP（灰）」。
/// 色は最大ダメージ割合で 赤(≥80%) / 黄(≥50%) / 緑(<50%)。
class _DamageBar extends StatelessWidget {
  const _DamageBar({required this.minPer, required this.maxPer});
  final double minPer;
  final double maxPer;

  static const _grey = Color(0xFFC8C8C8);

  @override
  Widget build(BuildContext context) {
    final (Color bright, Color dark) = maxPer >= 80
        ? (const Color(0xFFFF3232), const Color(0xFFA43E3E))
        : maxPer >= 50
            ? (const Color(0xFFFBC02D), const Color(0xFF907329))
            : (const Color(0xFF0EDA0E), const Color(0xFF25A425));

    double safe; // 確定で残る（明色）
    double band; // 不確定帯（暗色）
    if (maxPer >= 100) {
      safe = 0;
      band = minPer >= 100 ? 0 : (100 - minPer) / 100;
    } else {
      safe = (100 - maxPer) / 100;
      band = (maxPer - minPer) / 100;
    }
    safe = safe.clamp(0.0, 1.0);
    band = band.clamp(0.0, 1.0 - safe);
    final lost = (1.0 - safe - band).clamp(0.0, 1.0);

    return ClipRRect(
      borderRadius: BorderRadius.circular(2),
      child: SizedBox(
        height: 6,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (safe > 0)
              Expanded(
                  flex: (safe * 1000).round(),
                  child: ColoredBox(color: bright)),
            if (band > 0)
              Expanded(
                  flex: (band * 1000).round(), child: ColoredBox(color: dark)),
            if (lost > 0)
              Expanded(
                  flex: (lost * 1000).round(),
                  child: const ColoredBox(color: _grey)),
          ],
        ),
      ),
    );
  }
}

// ===== 編集用ピッカー =====

/// タイプを選択（18 タイプ＋任意で「なし」）。
Future<PokeType?> _pickType(BuildContext context, PokeType current,
    {required bool allowNone}) {
  final types = <PokeType>[
    if (allowNone) PokeType.none,
    for (final t in PokeType.values)
      if (t.index_ >= 0 && t.index_ <= 17) t, // ノーマル〜フェアリー
  ];
  return showDialog<PokeType>(
    context: context,
    builder: (_) => AlertDialog(
      titlePadding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      contentPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      title: const Text('タイプを選択', style: TextStyle(fontSize: 14)),
      content: SizedBox(
        width: 360,
        child: SingleChildScrollView(
          child: Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final t in types)
              GestureDetector(
                onTap: () => Navigator.of(context).pop(t),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: t == PokeType.none
                        ? Colors.grey.shade300
                        : typeColorOf(t),
                    borderRadius: BorderRadius.circular(4),
                    border: t == current
                        ? Border.all(color: Colors.black, width: 2)
                        : null,
                  ),
                  child: Text(t == PokeType.none ? 'なし' : t.jp,
                      style: TextStyle(
                          fontSize: 12,
                          color: t == PokeType.none
                              ? Colors.black87
                              : Colors.white)),
                ),
              ),
          ],
        ),
        ),
      ),
    ),
  );
}

/// 列挙値を中央ダイアログで選択（少数項目。はみ出し回避）。
Future<T?> _pickEnum<T>(BuildContext context, String title, List<T> options,
    T current, String Function(T) labelOf) {
  return showDialog<T>(
    context: context,
    builder: (_) => SimpleDialog(
      titlePadding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      title: Text(title, style: const TextStyle(fontSize: 14)),
      children: [
        for (final o in options)
          SimpleDialogOption(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            onPressed: () => Navigator.of(context).pop(o),
            child: Row(
              children: [
                Expanded(child: Text(labelOf(o))),
                if (o == current)
                  const Icon(Icons.check, color: Colors.blue, size: 18),
              ],
            ),
          ),
      ],
    ),
  );
}

/// ひらがな→カタカナ（検索用）。
String _toKatakana(String s) {
  final buf = StringBuffer();
  for (final r in s.runes) {
    buf.writeCharCode((r >= 0x3041 && r <= 0x3096) ? r + 0x60 : r);
  }
  return buf.toString();
}

/// カタカナ→ひらがな（検索用）。
String _toHiragana(String s) {
  final buf = StringBuffer();
  for (final r in s.runes) {
    buf.writeCharCode((r >= 0x30A1 && r <= 0x30F6) ? r - 0x60 : r);
  }
  return buf.toString();
}

/// 持ち物名は混在表記（カタカナ/ひらがな）のため、生入力・カタカナ・ひらがなの
/// いずれかを含めばマッチとみなす。
bool _kanaMatch(String option, String query) =>
    option.contains(query) ||
    option.contains(_toKatakana(query)) ||
    option.contains(_toHiragana(query));

/// 文字入力検索つきの選択（持ち物など）。
Future<String?> _pickSearchable(BuildContext context, String title,
    List<String> options, String current,
    {required String hint, Map<String, double>? usage}) {
  String query = '';
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    builder: (_) => StatefulBuilder(
      builder: (context, setSheet) {
        final filtered = query.isEmpty
            ? List<String>.from(options)
            : options.where((o) => _kanaMatch(o, query)).toList();
        if (usage != null) {
          // HOME 使用率の高い順に並べ替え（データの無いものは末尾）。
          filtered.sort((a, b) => (usage[b] ?? -1).compareTo(usage[a] ?? -1));
        }
        return SafeArea(
          child: Padding(
            padding:
                EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
            child: SizedBox(
              height: 380,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                    child: TextField(
                      autofocus: true,
                      decoration: InputDecoration(
                        isDense: true,
                        prefixIcon: const Icon(Icons.search, size: 18),
                        hintText: hint,
                        border: const OutlineInputBorder(),
                      ),
                      onChanged: (v) => setSheet(() => query = v),
                    ),
                  ),
                  Expanded(
                    child: filtered.isEmpty
                        ? const Center(child: Text('該当なし'))
                        : ListView(
                            children: [
                              for (final o in filtered)
                                ListTile(
                                  dense: true,
                                  title: Text(o == 'なし' ? 'もちものなし' : o),
                                  trailing: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      if (usage?[o] != null)
                                        Text(
                                            '${usage![o]!.toStringAsFixed(1)}%',
                                            style: const TextStyle(
                                                fontSize: 12,
                                                color: Colors.blueGrey)),
                                      if (o == current)
                                        const Padding(
                                          padding: EdgeInsets.only(left: 6),
                                          child: Icon(Icons.check,
                                              color: Colors.blue, size: 18),
                                        ),
                                    ],
                                  ),
                                  onTap: () => Navigator.of(context).pop(o),
                                ),
                            ],
                          ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    ),
  );
}

Future<String?> _pickString(BuildContext context, String title,
    List<String> options, String current,
    {Map<String, double>? usage}) {
  final opts = List<String>.from(options);
  if (usage != null) {
    // HOME 使用率の高い順に並べ替え（データの無いものは末尾、元の順序を維持）。
    opts.sort((a, b) => (usage[b] ?? -1).compareTo(usage[a] ?? -1));
  }
  return showModalBottomSheet<String>(
    context: context,
    builder: (_) => SafeArea(
      child: ListView(
        shrinkWrap: true,
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(title,
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
          for (final o in opts)
            ListTile(
              dense: true,
              title: Text(o),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (usage?[o] != null)
                    Text('${usage![o]!.toStringAsFixed(1)}%',
                        style: const TextStyle(
                            fontSize: 12, color: Colors.blueGrey)),
                  if (o == current)
                    const Padding(
                      padding: EdgeInsets.only(left: 6),
                      child:
                          Icon(Icons.check, color: Colors.blue, size: 18),
                    ),
                ],
              ),
              onTap: () => Navigator.of(context).pop(o),
            ),
        ],
      ),
    ),
  );
}

/// 性格を 5×5 表形式（行=↑能力、列=↓能力）で選択する。
Future<String?> _pickNature(BuildContext context, String current) {
  const stat = ['', 'A', 'B', 'C', 'D', 'S'];
  String? natureAt(int up, int down) {
    if (up == down) return up == 3 ? 'まじめ' : null;
    for (final n in allNatures) {
      if (n.up == up && n.down == down) return n.name;
    }
    return null;
  }

  Widget headerCell(String t) => SizedBox(
        width: 54,
        height: 24,
        child: Center(
            child: Text(t,
                style: const TextStyle(fontSize: 11, color: Colors.black54))),
      );

  return showDialog<String>(
    context: context,
    builder: (_) => AlertDialog(
      titlePadding: const EdgeInsets.fromLTRB(16, 12, 16, 2),
      contentPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      title: const Text('性格（↑行 × ↓列）', style: TextStyle(fontSize: 14)),
      content: SingleChildScrollView(
        child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(children: [
            headerCell(''),
            for (int d = 1; d <= 5; d++) headerCell('↓${stat[d]}')
          ]),
          for (int u = 1; u <= 5; u++)
            Row(
              children: [
                headerCell('↑${stat[u]}'),
                for (int d = 1; d <= 5; d++)
                  Builder(builder: (_) {
                    final name = natureAt(u, d);
                    final selected = name != null && name == current;
                    return GestureDetector(
                      onTap: name == null
                          ? null
                          : () => Navigator.of(context).pop(name),
                      child: Container(
                        width: 54,
                        height: 28,
                        margin: const EdgeInsets.all(1),
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: name == null
                              ? Colors.grey.withValues(alpha: 0.08)
                              : selected
                                  ? Colors.blue.withValues(alpha: 0.25)
                                  : Colors.blue.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                              color: selected ? Colors.blue : Colors.black12),
                        ),
                        child: Text(name ?? '—',
                            style: const TextStyle(fontSize: 9),
                            textAlign: TextAlign.center),
                      ),
                    );
                  }),
              ],
            ),
        ],
      ),
      ),
    ),
  );
}

/// 技を文字入力検索で選択する（DB waza_data。未接続時はサンプル moveDex）。
/// 元威力が -1 の攻撃技（カウンター等の可変威力技）はダメージ計算で表示できないため、
/// 変化技と同様に技一覧へ出さない。変化技自体（category==status）はここでは対象外。
bool _isHiddenAttackMove(BattleMove m) =>
    m.power == -1 && m.category != MoveCategory.status;

Future<BattleMove?> _pickMove(BuildContext context, BattleMove current,
    {String ownerName = ''}) {
  String query = '';
  bool started = false;
  List<BattleMove> filtered =
      PokeDb.instance.isOpen ? const [] : List.of(moveDex);
  // HOME 使用率上位の技（owner ポケモン）。検索が空のとき先頭に割合付きで出す。
  final homeMoves = ownerName.isEmpty
      ? const <HomeEntry>[]
      : HomeStats.instance.entries(ownerName, HomeCategory.waza);

  Future<void> runSearch(void Function(void Function()) setSheet) async {
    if (!PokeDb.instance.isOpen) {
      filtered = query.isEmpty
          ? List.of(moveDex)
          : moveDex.where((m) => m.name.contains(query)).toList();
      setSheet(() {});
      return;
    }
    final res = await PokeDb.instance.searchMoves(query);
    setSheet(() => filtered = res);
  }

  return showModalBottomSheet<BattleMove>(
    context: context,
    isScrollControlled: true,
    builder: (_) => StatefulBuilder(
      builder: (context, setSheet) {
        // 初回のみ DB から全件ロード
        if (!started && PokeDb.instance.isOpen) {
          started = true;
          runSearch(setSheet);
        }
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom),
            child: SizedBox(
              height: 380,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                    child: TextField(
                      autofocus: false,
                      decoration: const InputDecoration(
                        isDense: true,
                        prefixIcon: Icon(Icons.search, size: 18),
                        hintText: '技名で検索（例: じしん）',
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (v) {
                        query = v;
                        runSearch(setSheet);
                      },
                    ),
                  ),
                  Expanded(
                    child: () {
                      final showHome =
                          query.isEmpty && homeMoves.isNotEmpty;
                      if (filtered.isEmpty && !showHome) {
                        return const Center(child: Text('該当する技がありません'));
                      }
                      return ListView(
                        children: [
                          if (showHome) ...[
                            Padding(
                              padding:
                                  const EdgeInsets.fromLTRB(12, 6, 12, 2),
                              child: Text('HOME 使用率上位（$ownerName）',
                                  style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blueGrey.shade600)),
                            ),
                            for (final e in homeMoves)
                              ListTile(
                                dense: true,
                                leading: const Icon(Icons.home_filled,
                                    size: 16, color: Colors.blueGrey),
                                title: Text(e.value),
                                trailing: Text(
                                    '${e.pct.toStringAsFixed(1)}%',
                                    style: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.blueGrey)),
                                onTap: () async {
                                  final mv = await PokeDb.instance
                                      .moveByName(e.value);
                                  if (mv != null && context.mounted) {
                                    Navigator.of(context).pop(mv);
                                  }
                                },
                              ),
                            const Divider(height: 8),
                          ],
                          for (final mv in filtered)
                            ListTile(
                              dense: true,
                              leading: _TypeChip(mv.type),
                              title: Text(mv.name),
                              subtitle: Text(
                                  '${mv.category.jp} / 威力${mv.power}',
                                  style: const TextStyle(fontSize: 10)),
                              trailing: mv.name == current.name
                                  ? const Icon(Icons.check,
                                      color: Colors.blue, size: 18)
                                  : null,
                              onTap: () => Navigator.of(context).pop(mv),
                            ),
                        ],
                      );
                    }(),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    ),
  );
}

/// ステータス編集ダイアログ（努力値 0〜32・ランク −6〜+6。スクロール不要）。
class _StatEditorDialog extends StatefulWidget {
  const _StatEditorDialog({required this.pokemon});
  final BattlePokemon pokemon;

  @override
  State<_StatEditorDialog> createState() => _StatEditorDialogState();
}

class _StatEditorDialogState extends State<_StatEditorDialog> {
  static const _labels = ['HP', 'こうげき', 'ぼうぎょ', 'とくこう', 'とくぼう', 'すばやさ'];

  @override
  Widget build(BuildContext context) {
    final p = widget.pokemon;
    final stats = p.stats;
    final evTotal = p.ev.fold<int>(0, (a, b) => a + b);
    return AlertDialog(
      titlePadding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
      contentPadding: const EdgeInsets.fromLTRB(20, 0, 20, 4),
      actionsPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      title: Text('${p.name} のステータス編集',
          style: const TextStyle(fontSize: 15)),
      content: SizedBox(
        width: 460,
        // 端末の縦が短いとはみ出すためスクロール可能に（収まれば動かない）。
        child: SingleChildScrollView(
          child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // ヘッダ
            const Row(
              children: [
                SizedBox(width: 64, child: Text('能力',
                    style: TextStyle(fontSize: 11, color: Colors.black54))),
                SizedBox(width: 36, child: Text('種族',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: Colors.black54))),
                SizedBox(width: 40, child: Text('実数',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: Colors.black54))),
                Expanded(child: Center(child: Text('努力値',
                    style: TextStyle(fontSize: 11, color: Colors.black54)))),
                SizedBox(width: 96, child: Text('  ランク',
                    style: TextStyle(fontSize: 11, color: Colors.black54))),
              ],
            ),
            const Divider(height: 10),
            for (int i = 0; i < 6; i++)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 1),
                child: Row(
                  children: [
                    SizedBox(
                        width: 64,
                        child: Text(_labels[i],
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.w600))),
                    SizedBox(
                        width: 36,
                        child: Text('${p.baseStats[i]}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                fontSize: 12, color: Colors.black54))),
                    SizedBox(
                        width: 40,
                        child: Text('${stats[i]}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                fontSize: 13, fontWeight: FontWeight.bold))),
                    // 努力値：0/32 ワンクリック＋ ±1 ステップ（0〜32）。
                    Expanded(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _evBtn('0', () => setState(() => p.ev[i] = 0)),
                          const SizedBox(width: 2),
                          _stepBtn(
                              Icons.remove,
                              () => setState(() =>
                                  p.ev[i] = (p.ev[i] - 1).clamp(0, 32))),
                          SizedBox(
                              width: 30,
                              child: Text('${p.ev[i]}',
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.bold))),
                          _stepBtn(
                              Icons.add,
                              () => setState(() =>
                                  p.ev[i] = (p.ev[i] + 1).clamp(0, 32))),
                          const SizedBox(width: 2),
                          _evBtn('32', () => setState(() => p.ev[i] = 32)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    // ランク（HP 行はランク無し → クリアボタン）
                    SizedBox(
                      width: 96,
                      child: i == 0
                          ? Align(
                              alignment: Alignment.centerRight,
                              child: TextButton.icon(
                                style: TextButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8),
                                  minimumSize: const Size(0, 28),
                                  tapTargetSize:
                                      MaterialTapTargetSize.shrinkWrap,
                                ),
                                icon: const Icon(Icons.delete_sweep, size: 14),
                                label: const Text('ランククリア',
                                    style: TextStyle(fontSize: 9)),
                                onPressed: () => setState(() {
                                  for (var k = 1; k < 6; k++) {
                                    p.boosts[k] = 0;
                                  }
                                }),
                              ),
                            )
                          : Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                _stepBtn(Icons.remove, () {
                                  setState(() => p.boosts[i] =
                                      (p.boosts[i] - 1).clamp(-6, 6));
                                }),
                                SizedBox(
                                    width: 30,
                                    child: Text(
                                        '${p.boosts[i] > 0 ? '+' : ''}${p.boosts[i]}',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                            fontSize: 13,
                                            fontWeight: p.boosts[i] != 0
                                                ? FontWeight.bold
                                                : FontWeight.normal,
                                            color: p.boosts[i] > 0
                                                ? Colors.red
                                                : p.boosts[i] < 0
                                                    ? Colors.blue
                                                    : Colors.black54))),
                                _stepBtn(Icons.add, () {
                                  setState(() => p.boosts[i] =
                                      (p.boosts[i] + 1).clamp(-6, 6));
                                }),
                              ],
                            ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 4),
            Row(
              children: [
                const SizedBox(width: 64),
                const SizedBox(width: 36),
                const SizedBox(width: 40),
                Expanded(
                  child: Center(
                    child: Text('合計 $evTotal',
                        style: const TextStyle(
                            fontSize: 11,
                            color: Colors.black54,
                            fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(width: 96),
              ],
            ),
          ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('閉じる'),
        ),
      ],
    );
  }

  Widget _stepBtn(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        width: 28,
        height: 28,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.blue.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Icon(icon, size: 16, color: Colors.blue.shade700),
      ),
    );
  }

  /// 努力値の 0/32 ワンクリックボタン。
  Widget _evBtn(String text, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        width: 26,
        height: 28,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.blueGrey.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(text,
            style: const TextStyle(
                fontSize: 11, fontWeight: FontWeight.bold)),
      ),
    );
  }
}
