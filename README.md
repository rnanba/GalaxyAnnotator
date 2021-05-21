# Galaxy Annotator v0.5

## 概要

天体写真上の銀河のアノテーションを行うツールです。以下を入力するとアノテーション付きの SVG 画像ファイルを出力します。

- 銀河データファイル(JSON形式、後述)
- スタイル設定ファイル(JSON形式、後述)
- Astrometry.net の出力した `wcs.fits` (FITS形式)
- Astrometry.net に入力した画像ファイル

最終出力は SVG 編集ツール(Inkscape等)で調整できます。

銀河データファイルは手で書いてもいいですが、同梱のツールで HyperLeda から取得できます。

## 動作環境

- Python 3
- astropy
- svgwrite

Anaconda 環境の場合 astropy は標準で入っています。svgwrite は 'conda install -c conda-forge svgwrite' でインストールしてください。

以下、コマンドライン操作についての記述は Linux 環境を例にしています。Windows, macOS 環境での操作については適宣読み替えてください。

## アノテーション付き画像の生成

`galaxy-annotator.py` を使用します。

例:
```
./galaxy-annotator.py sample-galaxies.json sample-style.json test-data/test-wcs.fits test-data/test-in.jpg out.svg
```

- `sample-galaxies.json`: 銀河データファイルです。
- `sample-style.json`: スタイル設定ファイルです。
- `test-data/test-wcs.fits`: `test-data/test-in.jpg` を Astrometry.net でプレートソルブした際に生成された 'wcs.fits' です。
- `test-data/test-in.jpg`: Astrometry.net に入力した元画像ファイルです。
- `out.svg`: 出力先のSVGファイルです。

マーカーは銀河を囲む楕円形として描画されます。銀河の名前がその右上に描画されます。説明文がある場合は名前の下に描画されます。

出力されるSVG画像には元の画像(第4引数でしていしたもの)が埋め込まれます。SVGを扱うツールによっては元の画像が表示されない場合があります。

- GIMP 2.8, Photoshop, eog (GNOMEの画像ビューア)では元画像が表示されませんでした。
- Firefox, Chrome, Edge (Chromium版)では正しく表示されました。
- Inkscape では正しく表示でき、編集可能です。

## 銀河データファイル

銀河データファイル(JSON)の書式は以下の通りです。これは同梱のスクリプトで HyperLeda のデータから生成することができます(後述)。

```sample-galaxies.json
{
  "galaxies": [
    {
      "name": "PGC 1651721",
      "al2000": 12.9409511,
      "de2000": 21.5214739,
      "pa": 36.24,
      "logd25": 0.549,
      "logr25":  0.14,
      "descs": [
        "10億4200万光年"
      ]
    }
  ]
}
```

- `galaxies`: 銀河のデータを記述したオブジェクトの配列です。
   - 銀河オブジェクト:
      - `name`: 銀河の名前です。
      - `al2000`: 銀河の赤経(J2000元期)です。単位は時。分以下は少数で表します。
      - `de2000`: 銀河の赤緯(J2000元期)です。単位は度。分以下は少数で表します。
      - `pa`: 銀河の長軸の傾きで、北から東向きに(反時計回りに)測った角度です。
      	単位は度。分以下は少数で表します。
	
      - `logd25`: 対数で表した銀河の視直径(長軸)です。
         log(0.1分角単位の長軸の長さ)。視直径10分角なら2.0。
      - `logr25`: 対数で表した銀河の長軸と短軸の長さの比です。
      	log(長軸の長さ/短軸の長さ)。
      - `descs`: 説明文の行の配列です。配列要素は任意の文字列です。

`al2000`〜`logr25` は HyperLeda の同名のカラムと同じものです。

## スタイル設定ファイル

```sample-style.json
{
  "marker": {
    "stroke": "yellow",
    "stroke-width": 3,
    "stroke-opacity": 0.5,
    "size": 1.5,
    "x-margin": 4,
    "y-margin": 0,
    "min-r": 15
  },
  "name": {
    "font-size": 40,
    "font-family": "Ubuntu Mono",
    "fill": "yellow"
  },
  "desc": [
    {
      "font-family": "源真ゴシックP Light",
      "font-size": 40,
      "fill": "gray"
    }
  ]
}
```

- `marker`: マーカー(銀河を囲む楕円)のスタイル設定です。
  - `stroke`: 線の色です。書式はCSSと同じです。
  - `stroke-width`: 線の太さです。単位はピクセルです。
  - `stroke-opacity`: 線の不透明度です。書式はCSSと同じです。
  - `size`: マーカーのサイズです。銀河の大きさ(`logd25` から計算されるもの)
    の何倍かを指定します。
  - `x-margin`: 名前とマーカーの間のX軸方向のマージンです。単位はピクセルです。
  - `y-margin`: 名前とマーカーの間のY軸方向のマージンです。単位はピクセルです。
  - `min-r`: マーカーの最小半径です。単位はピクセルです。
- `desc`: 説明文のスタイル指定です。行毎のスタイルを指定するオブジェク
  トの配列です。
  - `font-family`: フォント名です。書式はCSSと同じです。
  - `font-size`: フォントサイズです。単位はピクセルです。
  - `fill`: 文字の色です。書式はCSSと同じです。

## 銀河情報ファイルの生成

同梱のスクリプトを使って、HyperLeda のデータから銀河情報ファイルを生成する方法を説明します。

### VOTABLE 形式(XML)のデータの取得

以下は `leda-get-votable.py` を使って `wcs.fits` から画像の写野を読み取ってその範囲に存在する銀河のデータを HyperLeda から取得する例です(現在はミラーサイトを使うようにしています)。

```
./leda-get-votable.py test-data/test-wcs.fits > votable.xml
```

引数には Astrometry.net の出力した `wcs.fits` を指定します。結果は標準出力に出力されますが、ここではシェルのリダイレクトで `votable.xml` に保存しています。

### VOTABLE 形式(XML)からの銀河情報ファイルの生成

以下は `leda-votable-to-galaxy.py` を使って、上で取得した `votable.xml` から銀河情報ファイルを生成する例です。

```
./leda-votable-to-galaxy.py votable.xml > galaxy.json
```

結果は標準出力に出力されますが、ここではシェルのリダイレクトで `galaxy.json` に保存しています。

以下は `-m` オプションを指定して 17.5 等より明るい銀河のみを銀河情報ファイルに出力しています。

```
./leda-votable-to-galaxy.py -m 17.5 votable.xml > galaxy-17_5.json
```

以下は `-d` オプションを追加して 17.5 等より明るい銀河のみを、距離情報(Gly (ギガ光年)表記の光路距離)を説明文として付加した銀河情報ファイルに出力しています。

```
./leda-votable-to-galaxy.py -m 17.5 -d votable.xml > galaxy-17_5-d.json
```

以下はさらに `-j` オプションを追加して距離情報を日本語表記(光年)で出力する例です。

```
./leda-votable-to-galaxy.py -m 17.5 -d -j votable.xml > galaxy-17_5-d-ja.json
```

距離情報(光路距離)は赤方偏移で測定された視線速度データを元に算出しています。比較的近距離の銀河については誤差が大きい場合があります。宇宙モデルとしてはΛ-CDMモデルを、宇宙論パラメータとしては H<sub>0</sub> = 67.3 km/s/Mpc、Ω<sub>m</sub> = 0.315、Ω<sub>Λ</sub> = 0.685 を使用しています(これらは国立天文台が一般向けに遠方天体の距離に言及する際に使用しているものです)。

## 告知、開発状況等

Galaxy Annotator に関する告知や開発状況については https://rna.hatenablog.com/archive/category/galaxyannotator を参照してください。

## ライセンス

MIT ライセンスです。
