// ============================================================
// BHI AI Agent - Google Apps Script Web App API (multi-sheet)
// Deploy: Deploy > New deployment > Web app > Execute as: Me > Access: Anyone
// BẢO MẬT: Project Settings > Script Properties > thêm key APPS_SCRIPT_SECRET
//          (giá trị phải khớp APPS_SCRIPT_SECRET trong .env của app).
// GỘP 2 SHEET: đọc gộp cả 2; ghi theo body.source ('1' = sheet gắn script,
//              '2' = SECOND_PLAN_ID). Tài khoản chạy app phải có quyền cả 2 sheet.
// LƯU Ý: hàm là apiGet/apiPost (be.gs delegate sang khi có ?action=).
// ============================================================

const MASTER_PLAN_ID = SpreadsheetApp.getActiveSpreadsheet().getId();
const SECOND_PLAN_ID = '1IChKyDyGUUHW-rPWNbh1galfiPFhPgnmrAysuikUuP8';
const SHEET_KE_HOACH = 'KẾ HOẠCH CHUYỂN ĐỔI SỐ';
const SHEET_ARCHIVE = '_ARCHIVE_LOG';
const HEADER_ROW = 2;

// KẾ HOẠCH columns (0-indexed). Sheet 2 đủ 19 cột; sheet 1 ~14 cột đầu trùng.
const COL = {
  ID: 0, NAME: 1, START_DATE: 2, END_DATE: 3, DURATION: 4, PREDECESSOR: 5,
  STATUS: 6, ELAPSED: 7, PIC: 8, SUPPORT: 9, REVIEWER: 10, NOTE: 11,
  CHECK_PREP_DATE: 12, CHECK_PREP: 13, CHECK_EXEC_DATE: 14, CHECK_EXEC: 15,
  CHECK_ACCEPT_DATE: 16, CHECK_ACCEPT: 17, ZONE: 18
};

const COL_ARCHIVE = {
  REPORT_DATE: 0, USER: 1, EMPLOYEE_ID: 2, ROLE: 3, PROJECT: 4, TASK_CONTENT: 5,
  HOURS: 6, STATUS: 7, DEADLINE: 8, EVALUATION: 9, REPORT_NOTE: 10
};

// ============================================================
// ROUTING
// ============================================================

function checkSecret(provided) {
  const expected = PropertiesService.getScriptProperties().getProperty('APPS_SCRIPT_SECRET');
  return expected && provided === expected;
}

function apiGet(e) {
  try {
    if (!checkSecret(e.parameter.secret)) return jsonResponse({ error: 'unauthorized' });
    const action = e.parameter.action;
    switch (action) {
      case 'search': return jsonResponse(searchTasks(e.parameter));
      case 'detail': return jsonResponse(getTaskDetail(e.parameter.taskId));
      case 'subtasks': return jsonResponse(getSubtasks(e.parameter.parentId));
      case 'archive': return jsonResponse(searchArchive(e.parameter));
      case 'meta': return jsonResponse(getMeta());
      default: return jsonResponse({ error: 'Unknown action: ' + action });
    }
  } catch (err) { return jsonResponse({ error: err.message }); }
}

function apiPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (!checkSecret(body.secret)) return jsonResponse({ error: 'unauthorized' });
    switch (body.action) {
      case 'create': return jsonResponse(createTasks(body.tasks, body.source));
      case 'update': return jsonResponse(updateTask(body.taskId, body.fields, body.source));
      case 'report': return jsonResponse(appendArchive(body.report, body.source));
      default: return jsonResponse({ error: 'Unknown action: ' + body.action });
    }
  } catch (err) { return jsonResponse({ error: err.message }); }
}

// ============================================================
// MULTI-SHEET DATA ACCESS
// ============================================================

function _ssId(source) {
  return (String(source) === '2') ? SECOND_PLAN_ID : MASTER_PLAN_ID;
}

// Đọc 1 sheet theo id — an toàn nếu thiếu tab / không quyền (trả [])
function getSheetDataFrom(planId, sheetName) {
  try {
    const ss = SpreadsheetApp.openById(planId);
    const ws = ss.getSheetByName(sheetName);
    if (!ws) return [];
    const data = ws.getDataRange().getValues();
    return sheetName === SHEET_ARCHIVE ? data.slice(1) : data.slice(HEADER_ROW);
  } catch (e) { return []; }
}

// Gộp cả 2 sheet, gắn nguồn (1|2) cho từng dòng
function getMergedData(sheetName) {
  const out = [];
  getSheetDataFrom(MASTER_PLAN_ID, sheetName).forEach(function (r) { out.push({ row: r, src: 1 }); });
  getSheetDataFrom(SECOND_PLAN_ID, sheetName).forEach(function (r) { out.push({ row: r, src: 2 }); });
  return out;
}

// ============================================================
// SEARCH TASKS (gộp 2 sheet)
// ============================================================

function searchTasks(params) {
  const data = getMergedData(SHEET_KE_HOACH);
  let results = [];

  for (let i = 0; i < data.length; i++) {
    const row = data[i].row;
    if (!row[COL.ID]) continue;

    if (params.hasReviewer === 'true' && !str(row[COL.REVIEWER])) continue;

    if (params.user) {
      const pic = str(row[COL.PIC]);
      const support = str(row[COL.SUPPORT]);
      const reviewer = str(row[COL.REVIEWER]);
      if (params.role === 'pic') {
        if (!pic.includes(params.user)) continue;
      } else if (params.role === 'support') {
        if (!support.includes(params.user)) continue;
      } else if (params.role === 'reviewer') {
        if (!reviewer.includes(params.user)) continue;
      } else if (!pic.includes(params.user) && !support.includes(params.user) && !reviewer.includes(params.user)) {
        continue;
      }
    }

    if (params.status && str(row[COL.STATUS]) !== params.status) continue;

    if (params.dateTo && row[COL.END_DATE]) {
      if (new Date(row[COL.END_DATE]) > new Date(params.dateTo)) continue;
    }
    if (params.dateFrom && row[COL.END_DATE]) {
      if (new Date(row[COL.END_DATE]) < new Date(params.dateFrom)) continue;
    }

    if (params.keyword) {
      const text = (str(row[COL.NAME]) + ' ' + str(row[COL.NOTE]) + ' ' + str(row[COL.ZONE])).toLowerCase();
      if (!text.includes(params.keyword.toLowerCase())) continue;
    }

    if (params.zone) {
      if (!str(row[COL.ZONE]).toLowerCase().includes(params.zone.toLowerCase())) continue;
    }

    results.push(taskRowToObject(row, data[i].src));
  }

  return { tasks: results.slice(0, 5000), count: results.length };
}

// ============================================================
// GET TASK DETAIL (gộp)
// ============================================================

function getTaskDetail(taskId) {
  const data = getMergedData(SHEET_KE_HOACH);
  for (let i = 0; i < data.length; i++) {
    if (str(data[i].row[COL.ID]) === taskId) {
      return { task: taskRowToObject(data[i].row, data[i].src) };
    }
  }
  return { error: 'Task not found: ' + taskId };
}

// ============================================================
// GET SUBTASKS (gộp — lọc theo prefix, không phụ thuộc thứ tự dòng)
// ============================================================

function getSubtasks(parentId) {
  const data = getMergedData(SHEET_KE_HOACH);
  let subtasks = [];
  for (let i = 0; i < data.length; i++) {
    const id = str(data[i].row[COL.ID]);
    if (id && id.startsWith(parentId + '-')) {
      subtasks.push(taskRowToObject(data[i].row, data[i].src));
    }
  }
  return { parent_id: parentId, subtasks: subtasks, count: subtasks.length };
}

// ============================================================
// SEARCH ARCHIVE LOG (gộp)
// ============================================================

function searchArchive(params) {
  const data = getMergedData(SHEET_ARCHIVE);
  let results = [];

  for (let i = 0; i < data.length; i++) {
    const row = data[i].row;
    if (!row[COL_ARCHIVE.USER]) continue;

    if (params.user && !str(row[COL_ARCHIVE.USER]).includes(params.user)) continue;
    if (params.project && !str(row[COL_ARCHIVE.PROJECT]).toLowerCase().includes(params.project.toLowerCase())) continue;
    if (params.dateFrom && row[COL_ARCHIVE.REPORT_DATE]) {
      if (new Date(row[COL_ARCHIVE.REPORT_DATE]) < new Date(params.dateFrom)) continue;
    }
    if (params.dateTo && row[COL_ARCHIVE.REPORT_DATE]) {
      if (new Date(row[COL_ARCHIVE.REPORT_DATE]) > new Date(params.dateTo)) continue;
    }

    results.push(archiveRowToObject(row, data[i].src));
  }

  return { reports: results.slice(0, 5000), count: results.length };
}

// ============================================================
// CREATE TASKS (ghi vào sheet theo source: '1' mặc định | '2')
// ============================================================

function createTasks(tasks, source) {
  const ss = SpreadsheetApp.openById(_ssId(source));
  const ws = ss.getSheetByName(SHEET_KE_HOACH);
  if (!ws) return { error: 'Sheet not found: ' + SHEET_KE_HOACH };
  let created = [];

  for (const task of tasks) {
    const newId = task.id || generateId(task.parent_id);
    const row = [
      newId, task.name || '',
      task.start_date ? new Date(task.start_date) : '',
      task.end_date ? new Date(task.end_date) : '',
      task.duration || '', task.predecessor || '',
      task.status || 'Chưa làm', '',
      task.pic || '', task.support || '', task.reviewer || '', task.note || '',
      '', '', '', '', '', '', task.zone || ''
    ];
    ws.appendRow(row);
    created.push({ task_id: newId, name: task.name });
  }

  return { created: created.length, tasks: created, source: String(source || '1') };
}

// ============================================================
// APPEND ARCHIVE (ghi vào sheet theo source)
// ============================================================

function appendArchive(report, source) {
  if (!report) return { error: 'Missing report payload' };
  const ss = SpreadsheetApp.openById(_ssId(report.source || source));
  const ws = ss.getSheetByName(SHEET_ARCHIVE);
  if (!ws) return { error: 'Sheet not found: ' + SHEET_ARCHIVE };

  const row = [
    report.report_date ? new Date(report.report_date) : new Date(),
    report.user || '', report.employee_id || '',
    report.role || 'Thực hiện', report.project || 'Hiện trường',
    report.task_content || '',
    (report.hours === undefined || report.hours === null) ? '' : report.hours,
    report.status || 'Đang làm', report.deadline || '',
    report.evaluation || '', report.report_note || ''
  ];
  ws.appendRow(row);
  return { success: true, appended: true, user: report.user || '', message: 'Đã ghi báo cáo vào _ARCHIVE_LOG' };
}

// ============================================================
// UPDATE TASK (source chỉ định, hoặc tự tìm trên cả 2 sheet)
// ============================================================

function _updateInSheet(planId, taskId, fields) {
  let ss;
  try { ss = SpreadsheetApp.openById(planId); } catch (e) { return false; }
  const ws = ss.getSheetByName(SHEET_KE_HOACH);
  if (!ws) return false;
  const data = ws.getDataRange().getValues();
  for (let i = HEADER_ROW; i < data.length; i++) {
    if (str(data[i][COL.ID]) === taskId) {
      const rowNum = i + 1;
      if (fields.status !== undefined) ws.getRange(rowNum, COL.STATUS + 1).setValue(fields.status);
      if (fields.note !== undefined) ws.getRange(rowNum, COL.NOTE + 1).setValue(fields.note);
      if (fields.pic !== undefined) ws.getRange(rowNum, COL.PIC + 1).setValue(fields.pic);
      if (fields.support !== undefined) ws.getRange(rowNum, COL.SUPPORT + 1).setValue(fields.support);
      if (fields.reviewer !== undefined) ws.getRange(rowNum, COL.REVIEWER + 1).setValue(fields.reviewer);
      if (fields.duration !== undefined) ws.getRange(rowNum, COL.DURATION + 1).setValue(fields.duration);
      if (fields.predecessor !== undefined) ws.getRange(rowNum, COL.PREDECESSOR + 1).setValue(fields.predecessor);
      if (fields.start_date !== undefined) ws.getRange(rowNum, COL.START_DATE + 1).setValue(new Date(fields.start_date));
      if (fields.end_date !== undefined) ws.getRange(rowNum, COL.END_DATE + 1).setValue(new Date(fields.end_date));
      if (fields.zone !== undefined) ws.getRange(rowNum, COL.ZONE + 1).setValue(fields.zone);
      return true;
    }
  }
  return false;
}

function updateTask(taskId, fields, source) {
  const ids = source ? [_ssId(source)] : [MASTER_PLAN_ID, SECOND_PLAN_ID];
  for (let j = 0; j < ids.length; j++) {
    if (_updateInSheet(ids[j], taskId, fields)) {
      return { success: true, task_id: taskId, updated_fields: Object.keys(fields), source: (j === 0 && !source) ? '1' : String(source || (j === 0 ? '1' : '2')) };
    }
  }
  return { error: 'Task not found: ' + taskId };
}

// ============================================================
// META — liệt kê tab + tiêu đề của cả 2 sheet
// ============================================================

function getMeta() {
  function describe(id) {
    try {
      const ss = SpreadsheetApp.openById(id);
      return {
        ok: true,
        spreadsheet_name: ss.getName(),
        sheets: ss.getSheets().map(function (sh) {
          const lastRow = sh.getLastRow();
          const lastCol = sh.getLastColumn();
          const sample = lastRow >= 1
            ? sh.getRange(1, 1, Math.min(3, lastRow), lastCol).getValues() : [];
          return { name: sh.getName(), rows: lastRow, cols: lastCol, first_rows: sample };
        }),
      };
    } catch (e) { return { ok: false, error: e.message }; }
  }
  return { sheet1: describe(MASTER_PLAN_ID), sheet2: describe(SECOND_PLAN_ID) };
}

// ============================================================
// HELPERS
// ============================================================

function taskRowToObject(row, src) {
  return {
    id: str(row[COL.ID]), name: str(row[COL.NAME]),
    start_date: fmtDate(row[COL.START_DATE]), end_date: fmtDate(row[COL.END_DATE]),
    duration_days: row[COL.DURATION] || null, predecessor: str(row[COL.PREDECESSOR]),
    status: str(row[COL.STATUS]).trim(), elapsed: row[COL.ELAPSED] || null,
    pic: str(row[COL.PIC]), support: str(row[COL.SUPPORT]), reviewer: str(row[COL.REVIEWER]),
    note: str(row[COL.NOTE]),
    check_prep_date: fmtDate(row[COL.CHECK_PREP_DATE]), check_prep: str(row[COL.CHECK_PREP]),
    check_exec_date: fmtDate(row[COL.CHECK_EXEC_DATE]), check_exec: str(row[COL.CHECK_EXEC]),
    check_accept_date: fmtDate(row[COL.CHECK_ACCEPT_DATE]), check_accept: str(row[COL.CHECK_ACCEPT]),
    zone: str(row[COL.ZONE]), source: String(src || 1)
  };
}

function archiveRowToObject(row, src) {
  return {
    report_date: fmtDateTime(row[COL_ARCHIVE.REPORT_DATE]), user: str(row[COL_ARCHIVE.USER]),
    employee_id: str(row[COL_ARCHIVE.EMPLOYEE_ID]), role: str(row[COL_ARCHIVE.ROLE]),
    project: str(row[COL_ARCHIVE.PROJECT]), task_content: str(row[COL_ARCHIVE.TASK_CONTENT]),
    hours: row[COL_ARCHIVE.HOURS] || null, status: str(row[COL_ARCHIVE.STATUS]).trim(),
    deadline: fmtDate(row[COL_ARCHIVE.DEADLINE]), evaluation: str(row[COL_ARCHIVE.EVALUATION]),
    report_note: str(row[COL_ARCHIVE.REPORT_NOTE]), source: String(src || 1)
  };
}

function str(v) { return (v || '').toString(); }

function fmtDate(d) {
  if (!d || !(d instanceof Date)) return null;
  return d.toISOString().split('T')[0];
}

function fmtDateTime(d) {
  if (!d || !(d instanceof Date)) return null;
  return d.toISOString().replace('T', ' ').substring(0, 19);
}

function generateId(parentId) {
  const ts = Date.now().toString(36).slice(-4).toUpperCase();
  return parentId ? parentId + '-' + ts : 'T-' + ts;
}

function jsonResponse(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
