import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 01 §4.2：lib 下不允许出现 Material 符号。
/// 用词边界匹配，避免误伤 CupertinoPageScaffold / CupertinoListTile。
void main() {
  const bannedExact = <String>[
    'MaterialApp',
    'InkWell',
    'Ink(',
    'Icons.',
    'showModalBottomSheet',
    'AlertDialog',
    'CircularProgressIndicator',
    'RefreshIndicator',
    'ElevatedButton',
    'ClampingScrollPhysics',
  ];

  final scaffold = RegExp(r'(?<![A-Za-z])Scaffold(?![A-Za-z])');
  final listTile = RegExp(r'(?<![A-Za-z])ListTile(?![A-Za-z])');
  final card = RegExp(r'(?<![A-Za-z])Card[\s<\.\(]');
  final chip = RegExp(r'(?<![A-Za-z])Chip[\s<\.\(]');
  final divider = RegExp(r'(?<![A-Za-z])Divider[\s<\.\(]');
  final material = RegExp(r'(?<![A-Za-z])Material[\s<\.\(]');

  test('lib 下不允许出现 Material 符号', () {
    final lib = Directory('lib');
    expect(lib.existsSync(), isTrue);

    final offenders = <String>[];
    for (final f in lib.listSync(recursive: true).whereType<File>()) {
      if (!f.path.endsWith('.dart')) continue;
      final src = f.readAsStringSync();
      for (final b in bannedExact) {
        if (src.contains(b)) {
          offenders.add('${f.path}: $b');
        }
      }
      if (scaffold.hasMatch(src)) offenders.add('${f.path}: Scaffold');
      if (listTile.hasMatch(src)) offenders.add('${f.path}: ListTile');
      if (card.hasMatch(src)) offenders.add('${f.path}: Card');
      if (chip.hasMatch(src)) offenders.add('${f.path}: Chip');
      if (divider.hasMatch(src)) offenders.add('${f.path}: Divider');
      if (material.hasMatch(src)) offenders.add('${f.path}: Material');
    }
    expect(offenders, isEmpty, reason: offenders.join('\n'));
  });

  test('禁止指定 fontFamily（依赖系统字体）', () {
    final offenders = <String>[];
    for (final f in Directory('lib').listSync(recursive: true).whereType<File>()) {
      if (!f.path.endsWith('.dart')) continue;
      final src = f.readAsStringSync();
      if (src.contains('fontFamily:')) {
        offenders.add(f.path);
      }
    }
    expect(offenders, isEmpty, reason: offenders.join('\n'));
  });
}
