# 中間JSONスキーマ（v1サマリ → CRM書き込み）

v1 サマリ Markdown を CRM 書き込み用 JSON に変換する際の中間スキーマ定義。
`scripts/crm_write.py` はこの JSON を入力として受け取り、FreelanceBase の各ドロワーに入力する。

## ファイル配置

- 中間 JSON は `output/{candidate_id}_payload.json` として保存する
- 対応する v1 サマリ Markdown は `output/{候補者名}_サマリ.md`（v1 既存動作を維持）

## スキーマ

```json
{
  "candidate_id": "MJC90451111_TS",
  "basic_info": {
    "gender_id": "1",
    "nationality_type_id": "1",
    "name_sei": "岡村",
    "name_mei": "皓太",
    "name_kana_sei": "おかむら",
    "name_kana_mei": "こうた",
    "birth_date": { "year": 1996, "month": 10, "day": 9 },
    "age": null,
    "station_name": "新宿",
    "prefecture_name": "東京都",
    "recording_url": "https://docs.google.com/document/d/XXXXXXXXXX/edit",
    "contact_method": "LINE"
  },
  "sales_info": {
    "work_styles_ids": ["3"],
    "business_day_ids": ["3", "4", "5"],
    "start_date": { "year": 2026, "month": 5, "day": null },
    "proposed_price_monthly": null,
    "sales_comment": null,
    "proposal_method": "1"
  },
  "skill_exp_info": {
    "occupation_ids": [9, 11, 14, 62],
    "dev_process_ids": [1, 2, 3, 4, 5, 6, 7],
    "career_summary": "[スキルシート]\nhttps://...\n\n[概要]\n・...\n\n[経験スキル]\nサーバーサイド：...",
    "bulk_add_from_info": true,
    "main_skill_name": "PHP"
  },
  "wish_info": {
    "work_location": "埼玉在住、フルリモート希望",
    "work_content": "上流から参画しプロダクト開発に携わりたい",
    "work_time": null,
    "other_wish": "過去参画先のため再参画NG: A社 / B社"
  },
  "management_info": {
    "sales_status": "1"
  },
  "invoice_info": {
    "registration_number_13": "3011401017348"
  },
  "meta": {
    "special_notes": null,
    "unknowns": []
  }
}
```

### フィールド仕様

| パス | 型 | 必須 | 書き込み先（CRM） | 備考 |
|------|----|------|------------------|------|
| `candidate_id` | string | ✔ | （検索キー） | `MJC...` 形式の管理用ID |
| `basic_info.gender_id` | `"0"/"1"/"2"` or null | | radio `gender_id` | |
| `basic_info.nationality_type_id` | `"1"/"2"` or null | | radio `nationality_type_id` | 日本国籍=1 |
| `basic_info.name_sei` | string or null | | text input ph='田中' | **空欄時のみ書き込み**（既存値があればスキップ） |
| `basic_info.name_mei` | string or null | | text input ph='太郎' | **空欄時のみ書き込み**（既存値があればスキップ） |
| `basic_info.name_kana_sei` | string or null | | text input ph='たなか' | フリガナ。**空欄時のみ書き込み** |
| `basic_info.name_kana_mei` | string or null | | text input ph='たろう' | フリガナ。**空欄時のみ書き込み** |
| `basic_info.birth_date.year/month/day` | int or null | | select × 3 (生年月日) | **3 つすべて未選択（"0"）の場合のみ書き込み**。既存値があればスキップ |
| `basic_info.age` | int or null | | 年齢（number） | **生年月日が分かる場合は省略推奨**（CRM 側で自動換算）。指定時も空欄時のみ書き込み |
| `basic_info.station_name` | string or null | | text `station_id`（autocomplete） | "武蔵浦和" のように末尾「駅」を除いた駅名を渡す。入力後 `ul.suggestions` から一致候補をクリックして選択 |
| `basic_info.prefecture_name` | string or null | | select 住所（都道府県） | 駅が存在する都道府県（例: 武蔵浦和駅 → "埼玉県"）。`PREFECTURE_MAP` で value 1〜48 にマップ |
| `basic_info.recording_url` | string or null | | text input `オンライン登録面談 録画URL` | AI議事録 Doc URL でも可。`fetch_meeting_doc.py` の戻り値を使う |
| `basic_info.contact_method` | string or null | | text input `連絡手段` | 自由記述（"LINE" / "メール" / "Slack" 等） |
| `sales_info.work_styles_ids` | string[] | | checkbox `work_styles_ids` | 複数可 |
| `sales_info.business_day_ids` | string[] | | checkbox `business_day_ids` | 稼働可能日数。`"1"=週1日 ... "5"=週5日`。複数可（例: 週3-5日 → `["3","4","5"]`） |
| `sales_info.start_date.year/month/day` | int or null | | select × 3 (稼働開始日) | `day` は null 可（「●月」表記時） |
| `sales_info.business_start_date.year/month/day` | int or null | | select × 3 (営業開始日) | 登録面談スキルでは**対応日（今日）**を自動セット |
| `sales_info.proposed_price_monthly` | int or null | | number `提案単価/月` | 単位は円（売り側の単一値） |
| `sales_info.personal_price_range.min` | int or null | | text `本人希望単価/月` 下限 | 単位は円 |
| `sales_info.personal_price_range.max` | int or null | | text `本人希望単価/月` 上限 | 単位は円 |
| `sales_info.sales_comment` | string or null | | textarea `人材担当コメント` | 100字以内 |
| `sales_info.proposal_method` | `"1"/"2"` or null | | select `提案方法` | `"1"`=先出しOK / `"2"`=案件確認。`masters.aliases.proposal_method` 参照 |
| `skill_exp_info.occupation_ids` | int[] | | checkbox `occupation_ids` | マスタ参照 |
| `skill_exp_info.dev_process_ids` | int[] | | checkbox `dev_process_ids` | マスタ参照 |
| `skill_exp_info.career_summary` | string or null | | textarea 「スキル・経験サマリー」 | v1の同名ブロックをそのまま投入 |
| `skill_exp_info.bulk_add_from_info` | bool | | （ボタン操作） | `true` で `career_summary` 入力後に「情報から一括追加」ボタンを押下しスキルタグを自動追加. 省略時は true |
| `skill_exp_info.main_skill_name` | string or null | | checkbox `thumbtack_*`（メインスキル） | 頻出首位の言語/FW名. 該当タグ行のメインスキル checkbox を ON. null なら無操作 |
| `wish_info.work_location` | string or null | | textarea 希望の作業場所 | |
| `wish_info.work_content` | string or null | | textarea 希望の作業内容 | |
| `wish_info.work_time` | string or null | | textarea 希望の作業時間 | 稼働時間帯の希望（例: コアタイム/時短希望）。無ければ null |
| `wish_info.other_wish` | string or null | | textarea その他希望 | 作業場所・内容に収まらない希望（NG企業＝過去参画先/再参画不可、現場の雰囲気要望、福利厚生等）。**NG条件はここに書く** |
| `management_info.sales_status` | `"1"/"2"/"3"/"4"` or null | | select `営業ステータス` | `"1"`=営業中 / `"2"`=営業終了 / `"3"`=営業不可 / `"4"`=取引停止。**登録面談サマリでは既定で `"1"`（営業中）をセット**。書き込みは上書き（既存値が他ステータスでも `"1"` に変わる）ため、不要な場合のみ明示的に `null` |
| `invoice_info.registration_number_13` | string(13桁数字) or null | | text input ph='13桁半角数字を入力'（独立セクション「適格請求書発行事業者 登録番号」） | インボイス登録番号。**`T` プレフィックスは除いた 13 桁数字のみ**を渡す（例: `T3011401017348` → `"3011401017348"`）。**空欄時のみ書き込み**（既存値があればスキップ） |
| `meta.special_notes` | string or null | | （書き込み対象外） | v1 [特記事項] — 差分プレビューで表示 |
| `meta.unknowns` | string[] | | （書き込み対象外） | v1で「不明」だった項目名リスト。保存スキップ判定に使う |

## 抽出ルール（v1 サマリ → JSON）

Claude 本体がv1サマリMarkdownを読んで以下に従ってJSONを生成する。

### 共通

- v1サマリで「不明」と書かれている項目は **JSONでは `null`** とし、同時に `meta.unknowns` に項目名を追加する
- `null` の項目は CRM 書き込みをスキップ（現状値を上書きしない）

### 基本情報

- `■性別：男性` → `gender_id: "1"`、`女性` → `"2"`、記載なし→`null`
- `■国籍：日本` or 行自体が削除されている → `nationality_type_id: "1"`、`外国籍` → `"2"`
- **氏名・フリガナ**: 面談メモやAI議事録から「岡村皓太（おかむら こうた）」のような表記を抽出して `name_sei`/`name_mei`/`name_kana_sei`/`name_kana_mei` にセット。不明なら `null`
- **生年月日**: 面談メモの「生年月日」項目（例: `1996/10/9`）から `birth_date: { year: 1996, month: 10, day: 9 }` にセット。不明なら `null`。生年月日が取れた場合は `age` は `null` でよい（CRMが自動換算）
- `■年齢：29歳` → `age: 29`（**生年月日があれば不要**。指定時は空欄CRMにのみ書き込まれる）
- `■最寄り駅：新宿駅` → `station_name: "新宿"`（末尾の「駅」は除去）
- 駅が分かれば **その駅が所属する都道府県を `prefecture_name` にセット**（例: 武蔵浦和駅→"埼玉県"、新宿駅→"東京都"）。駅不明時は null
- `recording_url`: 既定で `fetch_meeting_doc.py` が返す AI議事録 Doc URL をセット（録画 mp4 の Drive URL でも可）。URL が無ければ null
- `contact_method`: 面談メモ「連絡手段」項目（"LINE" / "メール" / "Slack" 等）。記載が無ければ null

### 営業情報

- `■稼働形態：フルリモート / 常駐` → `work_styles_ids` に `masters.aliases.work_styles` 経由でマッピング（複数可）
- **稼働可能日数**: 面談メモの「週◯稼働」項目から `business_day_ids` を構築。`週3~5日` → `["3","4","5"]`、`週5日のみ` → `["5"]`。記載なしは null
- `■稼働開始日：5月` → `start_date: { year: <current_year or next>, month: 5, day: null }`
  - 年は「●年●月」指定があればそれを採用。無ければ**直近未来**になるよう現在年を起点に判定
- `提案単価：￥●●●,●●●` → `proposed_price_monthly: null`（テンプレのままなら null）。`￥700,000` のように実値が入っていれば数値化
- `■人材担当コメント：...` → `sales_comment`
- `proposal_method`: 面談メモの「先出し」項目から判定（`OK` / `先出しOK` → `"1"`、`案件確認` / `要確認` → `"2"`）。記載なしは null

### スキル・経験情報

- `■経験職種：PM / PdM / ITコンサルタント` → `masters.aliases.occupation` で正規化し `occupation_ids: [9, 11, 14]`
  - マスタに無いラベルは `meta.unknowns` に追加
- `■担当工程：要件定義 / 基本設計 / 実装 / テスト` → 同様に `dev_process_ids`
- **`career_summary`**: 以下を改行で結合してそのまま格納
  ```
  [スキルシート]
  <URL もしくは「不明」>

  [概要]
  ・...
  ・...

  [経験スキル]
  サーバーサイド：...
  フロントエンド：...
  ```
  `[特記事項]` があれば末尾に続けて記載（CRM の経歴概要 textarea に全量投入）

#### スキルタグ（情報から一括追加）

- `bulk_add_from_info`: 既定 `true`. `career_summary` に `[経験スキル]` がある場合に true にする
- `main_skill_name`: **頻出首位の言語/FW 名**を1つセット. 判定対象とタイブレークルール:
  - [経験スキル] の **サーバーサイド / フロントエンド カテゴリ** のキーワードを対象に頻度カウント
  - 同数首位は **先に書かれた方を優先**（[経験スキル] 本文の出現順）
  - ただし **候補者の職種で例外判断**:
    - **PM / PMO / PdM / ITコンサル** 等、言語保有が主軸でない職種 → `null`
    - **インフラ / SRE / DBA** 等 → サーバーサイド/フロントの代わりに **インフラ系キーワード** （AWS / GCP / Azure / Terraform / Kubernetes 等）の頻出首位を使う
    - 判断に迷う場合は `null`（CRM 側で手動設定）
  - 該当タグが CRM の一括追加で検出されなかった場合、`crm_write.py` が `[WARN]` ログを出しつつ続行（保存は成功）

### 希望条件

- `■希望の作業場所：\n・...` → 箇条書きをそのまま結合して `work_location`
- `■希望の作業内容：\n・...` → `work_content`
- `■その他希望：\n・...`（NG企業＝過去参画先/再参画不可、現場の雰囲気要望 等） → `other_wish`。**NG条件・参画不可企業は work_content に混ぜず、必ず `other_wish`（CRM「その他希望」欄）に入れる**
- 稼働時間帯の希望があれば `work_time`（無ければ null）

### 管理情報

- `sales_status`: 登録面談を経た候補者は営業対象に切り替えるため、**既定で `"1"`（営業中）** をセットする
- 既に CRM 上で `"2"=営業終了` / `"3"=営業不可` / `"4"=取引停止` 等に設定済みの候補者を意図的に維持したい場合のみ `null` にしてスキップ
- 値は select の option（`営業中`/`営業終了`/`営業不可`/`取引停止`）を `masters.management_info.sales_status` 経由でマップ

### インボイス（適格請求書発行事業者 登録番号）

- 面談メモ等に「インボイス T3011401017348」「適格請求書発行事業者 登録番号」のような記載があれば抽出する
- **`T` プレフィックスを除いた 13 桁数字のみ**を `invoice_info.registration_number_13` にセット（例: `T3011401017348` → `"3011401017348"`）
- 13 桁に満たない／記載が無い場合は `null`（`meta.unknowns` に `"インボイス登録番号"` を追加）
- CRM は候補者詳細の独立セクション「適格請求書発行事業者 登録番号」で管理され、**空欄時のみ書き込む**（既存値は上書きしない）

### meta

- `special_notes`: v1 の `[特記事項]` セクション文字列（無ければ null）
- `unknowns`: 不明だった項目名のリスト（例: `["年齢", "最寄り駅"]`）

## マスタ参照

- `masters.json` の `basic_info` / `sales_info` / `skill_exp_info` 配下に value↔label のマップ
- `masters.aliases` に v1 サマリで使われる表記ゆれを吸収するためのエイリアス
- 抽出結果がマスタに無い場合は `meta.unknowns` に記録して書き込みスキップ
