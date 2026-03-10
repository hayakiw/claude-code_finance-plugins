# Stock Screener Plugin

中長期投資（ファンダメンタルズ分析）向け Claude Code プラグイン。
収益性・安全性・成長性・割安度の **4軸100点満点** で企業を客観評価し、優良銘柄をスクリーニングします。

---

## クイックスタート

### 1. 依存パッケージのインストール

```bash
pip install mcp yfinance
```

### 2. マーケットプレイスの登録

```
/plugin marketplace add ./finance-plugins
```

### 3. プラグインのインストール

```
/plugin install stock-screener@finance-plugins
```

### 4. スキルを使う

```
/stock-screener:recommend おすすめの銘柄を教えて
/stock-screener:analyze 7203.T
/stock-screener:screen 日経225
/stock-screener:compare 7203.T vs 6758.T vs 8035.T
```

> GitHub にリポジトリをプッシュ済みの場合は、リモートから直接登録できます：
> ```
> /plugin marketplace add owner/repo
> ```

---

## ディレクトリ構造

```
claude-code_finance-plugins/                          # マーケットプレイスルート
├── .claude-plugin/
│   └── marketplace.json                  # マーケットプレイスカタログ
└── plugins/
    └── stock-screener/                   # プラグイン本体
        ├── .claude-plugin/
        │   └── plugin.json              # プラグインマニフェスト
        ├── .mcp.json                    # MCPサーバー設定
        ├── skills/
        │   ├── recommend/
        │   │   └── SKILL.md             # 国内おすすめ銘柄レコメンド
        │   ├── analyze/
        │   │   └── SKILL.md             # 単一銘柄分析スキル
        │   ├── screen/
        │   │   └── SKILL.md             # 複数銘柄スクリーニングスキル
        │   └── compare/
        │       └── SKILL.md             # 銘柄横断比較スキル
        ├── mcp_server/
        │   ├── main.py                  # Yahoo Finance MCPサーバー
        │   └── requirements.txt
        └── README.md
```

---

## スキル一覧

| スキル | コマンド | 用途 |
|--------|---------|------|
| recommend | `/stock-screener:recommend おすすめの銘柄を教えて` | 国内主要20銘柄から自動でおすすめTOP5を表示 |
| analyze | `/stock-screener:analyze 7203.T` | 単一銘柄の4軸ファンダメンタルズ分析 |
| screen | `/stock-screener:screen 日経225` | セクター・リストから優良銘柄を選定 |
| compare | `/stock-screener:compare 7203.T vs 7267.T` | 複数銘柄の横断比較 |

---

## 4軸評価フレームワーク

| 軸 | 主要指標 | 満点 |
|----|---------|------|
| **収益性** | ROE・ROIC・営業利益率・粗利率 | 25点 |
| **安全性** | 自己資本比率・ネットキャッシュ・有利子負債倍率・営業CF | 25点 |
| **成長性** | 売上高成長率・EPS成長率・営業利益成長率（3〜5年CAGR） | 25点 |
| **割安度** | PER・PBR・EV/EBITDA・配当利回り | 25点 |
| **合計** | | **100点** |

### 投資グレード

| グレード | スコア | 推奨 |
|---------|--------|------|
| S | 80〜100点 | 積極買い |
| A | 65〜79点 | 買い推奨 |
| B | 50〜64点 | 様子見 |
| C | 35〜49点 | 保有継続のみ |
| D | 0〜34点 | 投資不適格 |

---

## ティッカーコード例

| 銘柄 | ティッカー |
|------|-----------|
| トヨタ自動車 | `7203.T` |
| ソフトバンクG | `9984.T` |
| ソニーグループ | `6758.T` |
| キーエンス | `6861.T` |
| オリエンタルランド | `4661.T` |
| Apple | `AAPL` |
| Microsoft | `MSFT` |
| Alphabet（Google） | `GOOGL` |

---

## MCPサーバー（financial-data）

Yahoo Finance（`yfinance`）から財務データを自動取得します。

### 提供ツール

| ツール | 説明 |
|--------|------|
| `get_stock_fundamentals` | 単一銘柄の全財務指標を取得 |
| `screen_stocks` | 複数銘柄の主要指標を一括取得 |
| `get_price_history` | 株価履歴・52週高値安値を取得 |

### 注意事項

- Yahoo Financeのデータは非公式APIのため、取得できない指標がある場合があります
- 日本株は末尾に `.T` を付けてください（例: `7203.T`）
- MCPサーバーが起動できない場合、スキルはWeb検索にフォールバックします

---

## 免責事項

> ⚠️ 本プラグインが提供する分析はAIによる自動分析であり、財務データの正確性・完全性を保証しません。
> 投資判断は必ず自己責任で行い、最新の有価証券報告書・決算短信・アナリストレポートも参照してください。
