# landxml2tri

English README: [README.en.md](README.en.md)

`landxml2tri` は、LandXML の TIN サーフェスに含まれる `Pnts` と `Faces` をそのまま使い、1 行 1 三角形のテキストへ変換する Python ツールです。補間や再構築は行わず、`Faces` に書かれた点 ID を直接参照して三角形を復元します。

## 特徴

- Python 3 と標準ライブラリ中心で動作します。
- XML 名前空間ありの LandXML に対応します。
- 複数 Surface がある場合は対象 Surface 名を指定できます。
- 点 ID が連番でない LandXML でも、そのまま参照して復元できます。
- 不正な Face は異常終了させずに警告し、最後に件数を集計します。

## 入出力形式

入力は LandXML ファイル、出力は 1 行 1 三角形の txt ファイルです。

各行は次の 9 値です。

```text
x1 y1 z1 x2 y2 z2 x3 y3 z3
```

## 使い方

```bash
python landxml_to_tin_txt.py input.xml output.txt
python landxml_to_tin_txt.py input.xml output.txt --surface "Existing Ground"
python landxml_to_tin_txt.py input.xml output.txt --coord-order xyz
python landxml_to_tin_txt.py input.xml output.txt --precision 3
```

## オプション

- `--surface`: 複数の TIN Surface がある場合に対象名を指定します。
- `--coord-order`: `P` 要素の値の並びを `xyz` または `yxz` として解釈します。出力は常に `x y z` 順です。
- `--precision`: 小数桁数を指定して出力を整形します。デフォルトは小数点以下 3 桁です。

## 動作仕様

- `Surface / Definition / Pnts / Faces` を持つ TIN サーフェスだけを対象にします。
- Surface 名未指定時は、TIN Surface が 1 つだけなら自動選択します。
- Surface 名未指定で TIN Surface が複数ある場合は、候補一覧を表示して終了します。
- `F` 要素が空、3 点以外、重複頂点を含む、未定義点 ID を参照する場合は警告してスキップします。
- 終了時に次を表示します。
- 読み込んだ点数
- 読み込んだ Face 数
- 書き出した三角形数
- スキップした不正 Face 数

## サンプル出力

```text
1.000 2.000 3.000 4.000 5.000 6.000 7.000 8.000 9.000
10.000 11.000 12.000 13.000 14.000 15.000 16.000 17.000 18.000
```

## テスト

```bash
pytest
python -m unittest discover -s tests -v
```

`tests/test_landxml_to_tin_txt.py` では、サンプル XML からの変換結果、複数 Surface の扱い、不正 Face の集計、`--coord-order` と `--precision` を確認しています。

## 同梱ファイル

- `landxml_to_tin_txt.py`: CLI 本体
- `samples/sample_landxml.xml`: 小さなサンプル LandXML
- `tests/test_landxml_to_tin_txt.py`: 最低限の自動テスト
- `pytest.ini`: pytest 設定

## License

MIT License
