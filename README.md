# Galaxy Annotator v0.5

## 概要

天体写真上の銀河のアノテーションを行うツールです。以下を入力するとアノテーション付きの SVG 画像ファイルを出力します。

- 銀河データファイル(JSON形式、後述)
- スタイル指定ファイル(JSON形式、後述)
- Astrometry.net の出力した wcs.fits (FITS形式)
- Astrometry.net に入力した画像ファイル(オプション)

最終出力は SVG 編集ツール(Inkscape等)で調整できます。

銀河データファイルは手で書いてもいいですが、同梱のツールで HyperLeda から取得できます。

## 動作環境

- Python 3
- astropy
- svgwrite

Anaconda 環境の場合 astropy は標準で入っています。svgwrite は 'conda install -c conda-forge svgwrite' でインストールしてください。

## 