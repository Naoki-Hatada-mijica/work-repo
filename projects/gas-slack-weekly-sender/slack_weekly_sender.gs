// ===========================================
// 週次注力情報 Slack手動一括送信スクリプト
// ===========================================

// ---------- 定数 ----------
const SHEET_CONFIG = '送信設定';
const PROP_TOKENS = 'SLACK_USER_TOKENS';
const DELIMITER = '---';

// ---------- 初回セットアップ（最初に1回だけ実行） ----------
function setupSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();

  // 既存シートを「送信設定」にリネーム
  const firstSheet = ss.getSheets()[0];
  firstSheet.setName('送信設定');

  // ヘッダー設定
  const headers = ['企業名', 'チャンネル名', 'チャンネルID', '担当者', '送信タイプ', 'メンションSlackID', 'メンション有無'];
  firstSheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // ヘッダー行の書式設定
  const headerRange = firstSheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285f4');
  headerRange.setFontColor('#ffffff');

  // 列幅の調整
  firstSheet.setColumnWidth(1, 120); // 企業名
  firstSheet.setColumnWidth(2, 160); // チャンネル名
  firstSheet.setColumnWidth(3, 140); // チャンネルID
  firstSheet.setColumnWidth(4, 80);  // 担当者
  firstSheet.setColumnWidth(5, 100); // 送信タイプ
  firstSheet.setColumnWidth(6, 160); // メンションSlackID
  firstSheet.setColumnWidth(7, 100); // メンション有無

  // サンプルデータ
  const sampleData = [
    ['A社（例）', '#a-sha-mijica', 'C0123456789', '畑田', '全体', 'U0123456789', '○'],
    ['B社（例）', '#b-sha-mijica', 'C0987654321', '畑田', '案件のみ', 'U0987654321', '×'],
    ['C社（例）', '#c-sha-mijica', 'C0111222333', '山田', '人材のみ', 'U0111222333', '○']
  ];
  firstSheet.getRange(2, 1, sampleData.length, sampleData[0].length).setValues(sampleData);

  // 送信タイプのプルダウン設定
  const typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['全体', '案件のみ', '人材のみ'])
    .build();
  firstSheet.getRange('E2:E100').setDataValidation(typeRule);

  // メンション有無のプルダウン設定
  const mentionRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['○', '×'])
    .build();
  firstSheet.getRange('G2:G100').setDataValidation(mentionRule);

  // 行の固定
  firstSheet.setFrozenRows(1);

  // コンテンツシート作成
  const contentSheets = ['全体ver', '案件のみ', '人材のみ'];
  const sampleContent = '新規のエンド直案件5件と、弊社個人事業主5名をご紹介させていただきます。\n見合う人材/案件があればご紹介のほど、よろしくお願いいたします。\n\nその他、注力シートも併せてご覧ください。\n---\n[案件]\n①【PdM/フルリモート/週5日】案件名をここに記載\n②【TypeScript/フルリモート/週5日】案件名をここに記載\n\n[要員]\n①【弊社個人事業主】スキル|勤務条件|開始時期|稼働日数\n②【弊社個人事業主】スキル|勤務条件|開始時期|稼働日数';

  for (const name of contentSheets) {
    let sheet = ss.getSheetByName(name);
    if (!sheet) {
      sheet = ss.insertSheet(name);
    }
    // 使い方の説明
    sheet.getRange('A1').setValue(sampleContent);
    sheet.getRange('A1').setWrap(true);
    sheet.setColumnWidth(1, 800);

    // 注意書き
    sheet.getRange('C1').setValue('← セルA1に内容を記載\n「---」より上が通常テキスト\n「---」より下がコードブロック');
    sheet.getRange('C1').setWrap(true);
    sheet.getRange('C1').setFontColor('#999999');
    sheet.setColumnWidth(3, 250);
  }

  // 送信設定シートをアクティブに
  ss.setActiveSheet(firstSheet);

  ui.alert('セットアップ完了', 'シート構造のセットアップが完了しました。\n\n1. 「送信設定」シートにパートナー情報を入力\n2. 「全体ver」「案件のみ」「人材のみ」シートにコンテンツを記載\n3. 「Slack送信」メニューからトークンを登録\n\nサンプルデータは実際の情報に置き換えてください。', ui.ButtonSet.OK);
}

// ---------- スプレッドシートにカスタムメニュー追加 ----------
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Slack送信')
    .addItem('プレビュー（送信しない）', 'previewMessages')
    .addItem('テスト送信（1社のみ）', 'confirmTestSend')
    .addSeparator()
    .addItem('一括送信', 'confirmBulkSend')
    .addSeparator()
    .addItem('トークン登録', 'setTokens')
    .addItem('トークン確認', 'showTokens')
    .addToUi();
}

// ---------- 確認ダイアログ付き送信 ----------
function confirmBulkSend() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName(SHEET_CONFIG);
  const configData = getConfigData_(configSheet);
  const weekLabel = getWeekLabel_();

  const companyList = configData.map(r => `  - ${r.企業名}（${r.送信タイプ} / ${r.担当者}）`).join('\n');

  const result = ui.alert(
    '一括送信の確認',
    `以下の ${configData.length} 社に「${weekLabel}」の注力情報を送信します。\n\n${companyList}\n\n送信しますか？`,
    ui.ButtonSet.YES_NO
  );

  if (result !== ui.Button.YES) {
    ui.alert('送信をキャンセルしました。');
    return;
  }

  const results = sendWeeklyInfo();
  showResultDialog_(results);
}

function confirmTestSend() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName(SHEET_CONFIG);
  const configData = getConfigData_(configSheet);

  if (configData.length === 0) {
    ui.alert('送信設定にデータがありません。');
    return;
  }

  const row = configData[0];
  const weekLabel = getWeekLabel_();

  const result = ui.alert(
    'テスト送信の確認',
    `「${row.企業名}」（${row.チャンネル名}）に「${weekLabel}」のテスト送信をします。\n\n送信しますか？`,
    ui.ButtonSet.YES_NO
  );

  if (result !== ui.Button.YES) return;

  try {
    testSendSingle();
    ui.alert('テスト送信完了', `${row.企業名} への送信が完了しました。\nSlackを確認してください。`, ui.ButtonSet.OK);
  } catch (e) {
    ui.alert('エラー', e.message, ui.ButtonSet.OK);
  }
}

// ---------- メイン処理 ----------
function sendWeeklyInfo() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName(SHEET_CONFIG);
  if (!configSheet) {
    throw new Error(`「${SHEET_CONFIG}」シートが見つかりません`);
  }

  const tokens = getTokens_();
  const weekLabel = getWeekLabel_();
  const configData = getConfigData_(configSheet);

  const results = [];

  for (const row of configData) {
    try {
      const token = tokens[row.担当者];
      if (!token) {
        results.push({ 企業名: row.企業名, status: 'SKIP', error: `担当者「${row.担当者}」のトークン未設定` });
        continue;
      }

      const contentBlocks = getContentBlocks_(ss, row.送信タイプ);
      if (!contentBlocks) {
        results.push({ 企業名: row.企業名, status: 'SKIP', error: `送信タイプ「${row.送信タイプ}」のシートが見つかりません` });
        continue;
      }

      const parentText = buildParentMessage_(weekLabel, row);
      const parentTs = postMessage_(token, row.チャンネルID, parentText);

      // スレッド返信: 通常テキスト（A1の---より上）
      if (contentBlocks.normalText) {
        postMessage_(token, row.チャンネルID, contentBlocks.normalText, parentTs);
        Utilities.sleep(500);
      }

      // スレッド返信: コードブロック（A1の---より下, A2, A3...）
      for (const block of contentBlocks.codeBlocks) {
        postRichMessage_(token, row.チャンネルID, '', block, parentTs);
        Utilities.sleep(500);
      }

      results.push({ 企業名: row.企業名, status: 'OK' });
      Utilities.sleep(1500);
    } catch (e) {
      results.push({ 企業名: row.企業名, status: 'ERROR', error: e.message });
    }
  }

  logResults_(results);
  return results;
}

// ---------- テスト送信（1社のみ） ----------
function testSendSingle() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName(SHEET_CONFIG);
  const tokens = getTokens_();
  const weekLabel = getWeekLabel_();
  const configData = getConfigData_(configSheet);

  if (configData.length === 0) {
    throw new Error('送信設定にデータがありません');
  }

  const row = configData[0];
  const token = tokens[row.担当者];
  if (!token) throw new Error(`担当者「${row.担当者}」のトークン未設定`);

  const contentBlocks = getContentBlocks_(ss, row.送信タイプ);
  if (!contentBlocks) throw new Error(`送信タイプ「${row.送信タイプ}」のシートが見つかりません`);

  const parentText = buildParentMessage_(weekLabel, row);
  const parentTs = postMessage_(token, row.チャンネルID, parentText);

  if (contentBlocks.normalText) {
    postMessage_(token, row.チャンネルID, contentBlocks.normalText, parentTs);
    Utilities.sleep(500);
  }
  for (const block of contentBlocks.codeBlocks) {
    postRichMessage_(token, row.チャンネルID, '', block, parentTs);
    Utilities.sleep(500);
  }
}

// ---------- プレビュー ----------
function previewMessages() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName(SHEET_CONFIG);
  const weekLabel = getWeekLabel_();
  const configData = getConfigData_(configSheet);

  if (configData.length === 0) {
    ui.alert('送信設定にデータがありません。');
    return;
  }

  let preview = '';
  for (const row of configData) {
    const contentBlocks = getContentBlocks_(ss, row.送信タイプ);
    if (!contentBlocks) {
      preview += `【${row.企業名}】シート「${row.送信タイプ}」が見つかりません\n\n`;
      continue;
    }

    const parentText = buildParentMessage_(weekLabel, row);

    preview += `━━━ ${row.企業名}（${row.チャンネル名} / ${row.担当者}）━━━\n`;
    preview += `[親メッセージ]\n${parentText}\n\n`;
    preview += `[スレッド - 通常テキスト]\n${contentBlocks.normalText}\n\n`;
    for (let i = 0; i < contentBlocks.codeBlocks.length; i++) {
      preview += `[スレッド - コードブロック${i + 1}]\n${contentBlocks.codeBlocks[i].substring(0, 200)}...\n\n`;
    }
  }

  const htmlOutput = HtmlService
    .createHtmlOutput('<pre style="font-size:12px;white-space:pre-wrap;">' + escapeHtml_(preview) + '</pre>')
    .setWidth(600)
    .setHeight(500)
    .setTitle('送信プレビュー');

  ui.showModalDialog(htmlOutput, `送信プレビュー（${weekLabel}）`);
}

function escapeHtml_(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---------- メッセージ構築 ----------
function buildParentMessage_(weekLabel, row) {
  let msg = `:star2: 注力情報のご紹介 ${weekLabel} :star2:`;
  if (row.メンション有無 === '○' && row.メンションSlackID) {
    msg = `<@${row.メンションSlackID}>\n${msg}`;
  }
  return msg;
}

// ---------- コンテンツ取得・分割 ----------
function getContentBlocks_(ss, sendType) {
  const sheetNameMap = {
    '全体': '全体ver',
    '案件のみ': '案件のみ',
    '人材のみ': '人材のみ'
  };

  const sheetName = sheetNameMap[sendType];
  if (!sheetName) return null;

  const sheet = ss.getSheetByName(sheetName);
  if (!sheet) return null;

  // A1のコンテンツを---で分割
  const a1Content = sheet.getRange('A1').getValue().toString();
  const { normalText, codeBlockText } = splitContent_(a1Content);

  const codeBlocks = [];
  if (codeBlockText) {
    const chunks = chunkText_(codeBlockText, 2800);
    for (const chunk of chunks) {
      codeBlocks.push(chunk);
    }
  }

  // A2以降にデータがあれば追加コードブロックとして取得
  const lastRow = sheet.getLastRow();
  for (let row = 2; row <= lastRow; row++) {
    const val = sheet.getRange(row, 1).getValue().toString().trim();
    if (val) {
      const chunks = chunkText_(val, 2800);
      for (const chunk of chunks) {
        codeBlocks.push(chunk);
      }
    }
  }

  return { normalText, codeBlocks };
}

function splitContent_(content) {
  const lines = content.split('\n');
  let splitIndex = -1;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    // 「---」「ーーー」「———」で始まる行、または「以下詳細」を含む行を区切りとして認識
    if (trimmed.match(/^[-ー―—]{2,}/) || trimmed.indexOf('以下詳細') !== -1) {
      splitIndex = i;
      break;
    }
  }

  if (splitIndex === -1) {
    return { normalText: content, codeBlockText: '' };
  }

  const normalText = lines.slice(0, splitIndex).join('\n').trim();
  const codeBlockText = lines.slice(splitIndex + 1).join('\n').trim();

  return { normalText, codeBlockText };
}

// ---------- 長文テキストを区切り線で自動分割 ----------
function chunkText_(text, maxLen) {
  if (text.length <= maxLen) return [text];

  const lines = text.split('\n');
  const chunks = [];
  let current = '';

  for (const line of lines) {
    const trimmed = line.trim();
    const isSeparator = trimmed.match(/^[-ー―—]{3,}/) || trimmed.indexOf('以下詳細') !== -1;

    if (isSeparator && current.length > 500) {
      chunks.push(current.trim());
      current = '';
      continue;
    }

    if (current.length + line.length + 1 > maxLen && current.length > 0) {
      chunks.push(current.trim());
      current = '';
    }
    current += (current ? '\n' : '') + line;
  }
  if (current.trim()) {
    chunks.push(current.trim());
  }

  return chunks;
}

// ---------- URL自動リンク化 ----------
function buildRichTextElements_(text) {
  const urlPattern = /https?:\/\/[^\s<>）」\]]+/g;
  const elements = [];
  let lastIndex = 0;
  let match;

  while ((match = urlPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      elements.push({ type: 'text', text: text.substring(lastIndex, match.index) });
    }
    elements.push({ type: 'link', url: match[0], text: match[0] });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    elements.push({ type: 'text', text: text.substring(lastIndex) });
  }

  if (elements.length === 0) {
    elements.push({ type: 'text', text: text });
  }

  return elements;
}

// ---------- 週ラベル生成 ----------
function getWeekLabel_() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const weekOfMonth = getWeekOfMonth_(now);
  return `${month}月${weekOfMonth}週目`;
}

function getWeekOfMonth_(date) {
  const firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
  const firstMonday = new Date(firstDay);
  const dayOfWeek = firstDay.getDay();
  const diff = dayOfWeek === 0 ? 1 : (dayOfWeek === 1 ? 0 : 8 - dayOfWeek);
  firstMonday.setDate(firstDay.getDate() + diff);

  if (date < firstMonday) return 1;

  const daysSinceFirstMonday = Math.floor((date - firstMonday) / (1000 * 60 * 60 * 24));
  return Math.floor(daysSinceFirstMonday / 7) + (firstDay.getDay() === 1 ? 1 : 2);
}

// ---------- 設定シート読み取り ----------
function getConfigData_(sheet) {
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];

  const headers = data[0];
  const rows = [];

  for (let i = 1; i < data.length; i++) {
    const row = {};
    for (let j = 0; j < headers.length; j++) {
      row[headers[j]] = data[i][j].toString().trim();
    }
    if (!row['チャンネルID'] || !row['担当者']) continue;
    rows.push(row);
  }

  return rows;
}

// ---------- トークン管理 ----------
function getTokens_() {
  const prop = PropertiesService.getScriptProperties().getProperty(PROP_TOKENS);
  if (!prop) {
    throw new Error('Slackトークンが未設定です。メニュー「Slack送信」→「トークン登録」から設定してください。');
  }
  return JSON.parse(prop);
}

function setTokens() {
  const ui = SpreadsheetApp.getUi();

  const nameRes = ui.prompt('トークン登録', '担当者名を入力（例: 畑田）', ui.ButtonSet.OK_CANCEL);
  if (nameRes.getSelectedButton() !== ui.Button.OK) return;

  const tokenRes = ui.prompt('トークン登録', 'Slackユーザートークン (xoxp-...) を入力', ui.ButtonSet.OK_CANCEL);
  if (tokenRes.getSelectedButton() !== ui.Button.OK) return;

  const name = nameRes.getResponseText().trim();
  const token = tokenRes.getResponseText().trim();

  if (!token.startsWith('xoxp-')) {
    ui.alert('エラー', 'トークンは xoxp- で始まる必要があります', ui.ButtonSet.OK);
    return;
  }

  let tokens = {};
  const existing = PropertiesService.getScriptProperties().getProperty(PROP_TOKENS);
  if (existing) {
    tokens = JSON.parse(existing);
  }

  tokens[name] = token;
  PropertiesService.getScriptProperties().setProperty(PROP_TOKENS, JSON.stringify(tokens));
  ui.alert('完了', `「${name}」のトークンを保存しました。`, ui.ButtonSet.OK);
}

function showTokens() {
  const ui = SpreadsheetApp.getUi();
  const existing = PropertiesService.getScriptProperties().getProperty(PROP_TOKENS);

  if (!existing) {
    ui.alert('トークン未設定', '「Slack送信」→「トークン登録」から登録してください。', ui.ButtonSet.OK);
    return;
  }

  const tokens = JSON.parse(existing);
  const lines = Object.keys(tokens).map(name => `${name}: xoxp-****${tokens[name].slice(-6)}`);
  ui.alert('登録済みトークン', lines.join('\n'), ui.ButtonSet.OK);
}

// ---------- Slack API ----------
function postRichMessage_(token, channel, normalText, codeBlockText, threadTs) {
  const elements = buildRichTextElements_(codeBlockText);

  const payload = {
    channel: channel,
    thread_ts: threadTs,
    text: codeBlockText.substring(0, 200) + '...',
    unfurl_links: false,
    unfurl_media: false,
    blocks: [{
      type: 'rich_text',
      elements: [{
        type: 'rich_text_preformatted',
        elements: elements
      }]
    }]
  };

  const options = {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
  const result = JSON.parse(response.getContentText());
  Logger.log('Slack API response: ' + JSON.stringify(result));

  if (!result.ok) {
    throw new Error(`Slack API エラー: ${result.error}`);
  }

  return result.ts;
}

function postMessage_(token, channel, text, threadTs) {
  const payload = {
    channel: channel,
    text: text,
    unfurl_links: false,
    unfurl_media: false
  };

  if (threadTs) {
    payload.thread_ts = threadTs;
  }

  const options = {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
  const result = JSON.parse(response.getContentText());

  if (!result.ok) {
    throw new Error(`Slack API エラー: ${result.error}`);
  }

  return result.ts;
}

// ---------- 結果表示 ----------
function showResultDialog_(results) {
  const ui = SpreadsheetApp.getUi();

  const okCount = results.filter(r => r.status === 'OK').length;
  const skipCount = results.filter(r => r.status === 'SKIP').length;
  const errorCount = results.filter(r => r.status === 'ERROR').length;

  let msg = `送信完了: ${okCount}社\n`;
  if (skipCount > 0) msg += `スキップ: ${skipCount}社\n`;
  if (errorCount > 0) msg += `エラー: ${errorCount}社\n`;

  msg += '\n--- 詳細 ---\n';
  for (const r of results) {
    const icon = r.status === 'OK' ? '✅' : r.status === 'SKIP' ? '⏭️' : '❌';
    msg += `${icon} ${r.企業名}: ${r.status}`;
    if (r.error) msg += ` (${r.error})`;
    msg += '\n';
  }

  ui.alert('送信結果', msg, ui.ButtonSet.OK);
}

function logResults_(results) {
  Logger.log('=== 送信結果 ===');
  for (const r of results) {
    Logger.log(`${r.企業名}: ${r.status}${r.error ? ' - ' + r.error : ''}`);
  }
}

// ---------- デバッグ ----------
function debugSplit() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('全体ver');
  const content = sheet.getRange('A1').getValue().toString();

  Logger.log('=== A1 先頭500文字 ===');
  Logger.log(content.substring(0, 500));

  const lines = content.split('\n');
  Logger.log('=== 全行数: ' + lines.length + ' ===');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.indexOf('以下') !== -1 || line.match(/^[-ー―—]{2,}/)) {
      Logger.log('区切り候補 行' + i + ': [' + line + ']');
      Logger.log('文字コード: ' + Array.from(line).map(c => c.charCodeAt(0)).join(','));
    }
  }
}
