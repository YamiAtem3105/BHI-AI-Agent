from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router_dashboard_ui = APIRouter()


@router_dashboard_ui.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BHI Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#1a1a1a;--surface:#2a2a2a;--border:#3a3a3a;--text:#e8e8e8;--text-secondary:#999;--accent:#d97706;--accent-soft:rgba(217,119,6,.14);--accent-bg:#fef3c7;--green:#4ade80;--orange:#fb923c;--red:#f87171;--gray:#6b7280;--tab-h:44px;--tab-track:#484848;--tab-inactive-bg:#5a5a5a;--tab-inactive-border:#777}
html,body{height:100%;overflow:hidden}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased;display:flex;flex-direction:column}

header{flex-shrink:0;background:#111;border-bottom:1px solid var(--border);padding:.7rem 1.5rem;display:flex;align-items:center;gap:1rem}
header h1{font-size:1rem;font-weight:600;color:var(--text)}
.header-links{margin-left:auto;display:flex;gap:1.2rem}
.header-links a{color:var(--text-secondary);text-decoration:none;font-size:.85rem;transition:color .2s;display:inline-flex;align-items:center;gap:.35rem}
.header-links a:hover{color:var(--text)}
.header-links a.active{color:var(--text);font-weight:500}
.nav-icon{width:1rem;height:1rem;flex-shrink:0;stroke:currentColor;fill:none;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}

/* Tab navigation — segmented control + GSAP sliding indicator */
.tab-nav{margin-bottom:1.25rem;padding:.2rem 0;position:relative}
.tab-nav-wrap{position:relative}
.tab-nav-wrap::before,.tab-nav-wrap::after{content:'';position:absolute;top:0;bottom:0;width:1.25rem;pointer-events:none;z-index:2;opacity:0;transition:opacity .2s}
.tab-nav-wrap::before{left:0;background:linear-gradient(90deg,var(--bg),transparent)}
.tab-nav-wrap::after{right:0;background:linear-gradient(270deg,var(--bg),transparent)}
.tab-nav-wrap.can-scroll-left::before,.tab-nav-wrap.can-scroll-right::after{opacity:1}
.tab-track{position:relative;display:flex;gap:.45rem;padding:.45rem;background:var(--tab-track);border:2px solid #6b6b6b;border-radius:14px;box-shadow:0 6px 24px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.1);overflow-x:auto;scroll-snap-type:x proximity;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.tab-track::-webkit-scrollbar{display:none}
.tab-indicator{position:absolute;top:.45rem;left:0;height:var(--tab-h);border-radius:11px;background:linear-gradient(135deg,#fbbf24 0%,#f59e0b 40%,#d97706 100%);border:1px solid rgba(255,255,255,.4);box-shadow:0 4px 18px rgba(245,158,11,.55),inset 0 1px 0 rgba(255,255,255,.35);pointer-events:none;z-index:0;will-change:transform,width}
.tab-btn{position:relative;z-index:1;flex:0 0 auto;display:inline-flex;align-items:center;gap:.5rem;min-height:var(--tab-h);padding:0 1.05rem;border:1px solid var(--tab-inactive-border);border-radius:11px;background:var(--tab-inactive-bg);color:#f5f5f5;cursor:pointer;font-size:.84rem;font-weight:600;white-space:nowrap;scroll-snap-align:center;transition:color .2s,background .2s,border-color .2s,transform .15s;box-shadow:inset 0 1px 0 rgba(255,255,255,.08)}
.tab-btn:hover{color:#fff;background:#656565;border-color:#999;transform:translateY(-1px)}
.tab-btn:focus-visible{outline:2px solid #fbbf24;outline-offset:2px}
.tab-btn.active{color:#1c1408;font-weight:700;background:transparent;border-color:transparent;box-shadow:none;text-shadow:0 1px 0 rgba(255,255,255,.2)}
.tab-btn.active .tab-icon{color:#1c1408}
.tab-icon{display:flex;align-items:center;justify-content:center;width:20px;height:20px;color:#fafafa;transition:color .25s,transform .25s}
.tab-icon svg{width:20px;height:20px;display:block}
.tab-icon svg path,.tab-icon svg rect,.tab-icon svg circle{stroke:currentColor;fill:none;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}
.tab-btn:hover .tab-icon{color:#fff}
.tab-label{letter-spacing:.02em}
.mobile-chat-fab{display:none;position:fixed;right:1rem;bottom:1rem;z-index:50;align-items:center;gap:.45rem;padding:.7rem 1rem;border-radius:999px;background:linear-gradient(135deg,#f59e0b,#d97706);color:#1a1208;font-size:.82rem;font-weight:700;text-decoration:none;box-shadow:0 6px 20px rgba(217,119,6,.45);border:1px solid rgba(255,255,255,.25)}
.mobile-chat-fab svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2}
.tab-panel{display:none;opacity:1}
.tab-panel.active{display:block}
.taskform-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem}
.tf-card h3{margin-bottom:.8rem}
.tf-label{display:block;font-size:.76rem;color:var(--text-secondary);margin:.55rem 0 .2rem}
.tf-input{width:100%;padding:.55rem .7rem;background:#333;border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:.9rem;outline:none}
.tf-input:focus{border-color:#777}
.tf-row{display:flex;gap:.7rem}.tf-row>div{flex:1;min-width:0}
.tf-btn{width:100%;margin-top:.9rem;padding:.7rem;border:none;border-radius:9px;font-size:.95rem;font-weight:700;cursor:pointer}
.tf-btn-create{background:var(--green);color:#06310f}
.tf-btn-update{background:var(--accent);color:#1a1208}
.tf-btn:hover{filter:brightness(1.08)}
.tf-msg{margin-top:.6rem;font-size:.85rem;min-height:1.1rem;white-space:pre-wrap}
.tf-msg.ok{color:var(--green)}.tf-msg.err{color:var(--red)}
.pool-card,.field-card,.metrics-placeholder,.ai-box{will-change:transform,opacity}
.pool-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}
.pool-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem}
.pool-card h4{font-size:.9rem;margin-bottom:.5rem}
.pool-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:.4rem;margin:.6rem 0;font-size:.75rem}
.pool-metrics span{background:#333;padding:.35rem;border-radius:4px;text-align:center}
.priority-khan{color:var(--red)}.priority-cao{color:var(--orange)}
.ai-box{background:#1f2937;border:1px solid #374151;border-radius:8px;padding:1rem;margin-bottom:1rem}
.ai-box ul{margin:.5rem 0 0 1rem;font-size:.82rem;line-height:1.6}
.pool-toolbar{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;margin-bottom:1rem}
.pool-toolbar select,.pool-toolbar input{background:#333;border:1px solid var(--border);color:var(--text);padding:.45rem .6rem;border-radius:6px;font-size:.82rem}
.pool-detail{margin-top:.6rem;font-size:.75rem;color:var(--text-secondary)}
.pool-detail table{width:100%;margin-top:.4rem}
.pool-detail td,.pool-detail th{padding:.35rem .4rem;border-bottom:1px solid #333}
.role-pill{font-size:.68rem;padding:.15rem .45rem;border-radius:999px;background:#333;color:var(--text-secondary);margin-left:.35rem}
.metrics-placeholder{background:var(--surface);border:1px dashed var(--border);border-radius:8px;padding:2rem;text-align:center;color:var(--text-secondary)}
.field-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}
.field-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem}
.field-card h4{font-size:.88rem;margin-bottom:.5rem}
.field-status{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}
.status-dot{font-size:.75rem;padding:.25rem .5rem;border-radius:4px;background:#333}
.status-dot.on{background:#14532d;color:#86efac}.status-dot.off{background:#3f1d1d;color:#fca5a5}
.field-form{display:grid;gap:.5rem;margin-top:.8rem}
.field-form input,.field-form select{width:100%;background:#333;border:1px solid var(--border);color:var(--text);padding:.45rem .6rem;border-radius:6px;font-size:.82rem}
.field-form button{background:var(--accent);color:#111;border:none;padding:.5rem .8rem;border-radius:6px;cursor:pointer;font-weight:600}
.pending-list{font-size:.78rem;margin-top:.5rem}
.pending-list li{margin:.25rem 0}

.layout{display:grid;grid-template-columns:1fr 380px;grid-template-rows:minmax(0,1fr);flex:1;min-height:0;overflow:hidden}
.main{overflow-y:auto;padding:1.5rem 2rem;min-height:0}
.sidebar{background:#222;border-left:1px solid var(--border);display:flex;flex-direction:column;min-height:0;overflow:hidden}

/* Cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem;margin-bottom:1.5rem}
.card{background:var(--surface);padding:1rem 1.2rem;border-radius:8px;border:1px solid var(--border)}
.card-value{font-size:1.6rem;font-weight:700;color:var(--text)}
.card-label{font-size:.75rem;color:var(--text-secondary);margin-top:.2rem;text-transform:uppercase;letter-spacing:.3px}
.card.warn .card-value{color:var(--red)}
.card.green .card-value{color:var(--green)}
.card.orange .card-value{color:var(--orange)}

/* Charts */
.charts{display:grid;grid-template-columns:1fr 1.5fr;gap:1rem;margin-bottom:1.5rem}
.chart-box{background:var(--surface);padding:1.2rem;border-radius:8px;border:1px solid var(--border)}
.chart-box h3{font-size:.8rem;color:var(--text-secondary);margin-bottom:.8rem;text-transform:uppercase;letter-spacing:.3px}

/* Table */
.table-box{background:var(--surface);padding:1.2rem;border-radius:8px;border:1px solid var(--border);margin-bottom:1.5rem}
.table-box h3{font-size:.8rem;color:var(--text-secondary);margin-bottom:.8rem;text-transform:uppercase;letter-spacing:.3px}
.table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -.2rem;padding:0 .2rem}
.table-scroll table{min-width:540px}
table{width:100%;border-collapse:collapse;font-size:.83rem}
th{padding:.6rem .5rem;text-align:left;border-bottom:1px solid var(--border);color:var(--text-secondary);font-weight:500;font-size:.75rem;text-transform:uppercase}
td{padding:.6rem .5rem;border-bottom:1px solid #333}
tr:hover td{background:#333}
.progress-bar{width:90px;height:18px;background:#333;border-radius:9px;display:inline-block;vertical-align:middle;overflow:hidden;position:relative}
.progress-fill{height:100%;border-radius:9px;background:var(--green);transition:width .6s ease}
.progress-text{position:absolute;top:0;left:0;right:0;text-align:center;font-size:.7rem;line-height:18px;color:#fff;font-weight:600}
.rate-low .progress-fill{background:var(--orange)}
.rate-zero .progress-fill{background:#444}

/* Overdue */
.overdue-item{padding:.5rem 0;border-bottom:1px solid #333;font-size:.82rem;display:flex;gap:.5rem;align-items:baseline}
.overdue-item .task-id{color:var(--red);font-weight:600;font-size:.78rem;min-width:55px}
.overdue-item .task-name{color:var(--text);flex:1}
.overdue-item .task-meta{color:var(--text-secondary);font-size:.75rem;white-space:nowrap}

/* Chatbot sidebar */
.chat-header{flex-shrink:0;padding:.8rem 1rem;border-bottom:1px solid var(--border);font-size:.85rem;font-weight:600;color:var(--text);display:flex;align-items:center;gap:.5rem}
.chat-messages{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:.8rem;display:flex;flex-direction:column;gap:.5rem;scroll-behavior:smooth}
.chat-msg{max-width:92%;padding:.6rem .9rem;border-radius:13px;font-size:.82rem;line-height:1.55;white-space:pre-wrap;word-break:break-word;flex-shrink:0;box-shadow:0 1px 2px rgba(0,0,0,.22)}
.chat-msg-user{align-self:flex-end;background:linear-gradient(135deg,#fff,#eee);color:#111;border-bottom-right-radius:4px}
.chat-msg-bot{align-self:flex-start;background:#2f2f2f;border:1px solid #3a3a3a;border-bottom-left-radius:4px;color:var(--text)}
.chat-msg-bot strong{color:#fff;font-weight:600}
.chat-msg-bot a{color:var(--orange);text-decoration:none;border-bottom:1px dashed var(--orange)}
.chat-msg-bot code,.chat-msg-user code{font-family:'SF Mono',Consolas,Menlo,monospace;font-size:.82em;background:rgba(217,119,6,.16);color:var(--accent);padding:.05rem .32rem;border-radius:5px;white-space:nowrap}
.chat-msg-user code{background:rgba(0,0,0,.08);color:#7c3a00}
.chat-typing{display:inline-flex;gap:4px;align-items:center;padding:.15rem 0}
.chat-typing span{width:6px;height:6px;border-radius:50%;background:var(--text-secondary);animation:ctdot 1.2s infinite ease-in-out}
.chat-typing span:nth-child(2){animation-delay:.2s}
.chat-typing span:nth-child(3){animation-delay:.4s}
@keyframes ctdot{0%,60%,100%{opacity:.25;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}
.chat-input{flex-shrink:0;display:flex;gap:.4rem;padding:.6rem .8rem;border-top:1px solid var(--border)}
.chat-input input{flex:1;padding:.5rem .8rem;border:1px solid var(--border);border-radius:18px;font-size:.82rem;outline:none;background:#333;color:var(--text)}
.chat-input input:focus{border-color:#666}
.chat-input button{padding:.5rem .9rem;background:#fff;color:#111;border:none;border-radius:18px;cursor:pointer;font-size:.82rem;font-weight:600}
.chat-input button:hover{background:#ddd}
.chat-quick{flex-shrink:0;display:flex;flex-wrap:wrap;gap:.3rem;padding:.4rem .8rem;border-top:1px solid var(--border)}
.chat-quick button{background:#333;border:1px solid #444;border-radius:14px;padding:.25rem .6rem;font-size:.72rem;cursor:pointer;color:var(--text-secondary)}
.chat-quick button:hover{background:#444;color:var(--text)}

/* Mobile / tablet */
@media(max-width:900px){
  html,body{overflow-x:hidden}
  .layout{grid-template-columns:1fr}
  .sidebar{display:none}
  .mobile-chat-fab{display:inline-flex}
  .main{padding:1rem .75rem;overflow-x:hidden}
  header{padding:.65rem .75rem;flex-wrap:wrap;row-gap:.35rem}
  header h1{font-size:.92rem}
  .header-links{margin-left:auto;gap:.75rem}
  .header-links a{font-size:.8rem}
  .tab-nav{margin-bottom:1rem;position:sticky;top:0;z-index:10;background:var(--bg);padding:.35rem 0 .5rem}
  .tab-track{padding:.4rem;gap:.4rem;border-radius:12px}
  .tab-btn{min-height:44px;padding:0 .85rem;font-size:.8rem}
  .tab-indicator{top:.4rem;border-radius:10px}
  #user-info{margin-left:0!important;width:100%;justify-content:flex-end;font-size:.78rem!important}
  .cards{grid-template-columns:repeat(2,1fr);gap:.55rem;margin-bottom:1rem}
  .card{padding:.75rem .9rem}
  .card-value{font-size:1.35rem}
  .card-label{font-size:.68rem}
  .charts{grid-template-columns:1fr;gap:.75rem;margin-bottom:1rem}
  .chart-box{padding:.9rem}
  .chart-box canvas{max-height:240px}
  .table-box{padding:.9rem;margin-bottom:1rem}
  .table-scroll::after{content:'← Kéo ngang →';display:block;text-align:center;font-size:.68rem;color:var(--text-secondary);margin-top:.35rem;opacity:.7}
  .overdue-item{flex-wrap:wrap;row-gap:.2rem}
  .overdue-item .task-meta{white-space:normal;width:100%;padding-left:55px}
}
@media(max-width:480px){
  .tab-btn{padding:0 .65rem;font-size:.76rem;gap:.35rem}
  .tab-label{max-width:none}
  .mobile-chat-fab{right:.75rem;bottom:.75rem;padding:.65rem .85rem;font-size:.78rem}
  .cards{grid-template-columns:repeat(2,1fr)}
  .card-value{font-size:1.15rem}
  .progress-bar{width:72px;height:16px}
  .progress-text{font-size:.62rem;line-height:16px}
  th,td{padding:.5rem .35rem;font-size:.78rem}
  .overdue-item .task-name{font-size:.78rem}
  .tf-row{flex-direction:column;gap:.15rem}
  .tf-input{font-size:16px}
}
</style>
</head>
<body>
<header>
<svg class="nav-icon" style="width:1.1rem;height:1.1rem;color:var(--accent)" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/></svg>
<h1>BHI Dashboard</h1>
<div class="header-links">
<a href="/"><svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> Chat</a>
<a href="/dashboard" class="active"><svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10M10 20V4M16 20v-6M22 20H2"/></svg> Dashboard</a>
</div>
<div id="user-info" style="margin-left:1rem;display:none;font-size:.85rem;color:var(--text-secondary)">
  <span id="user-display"></span>
  <button onclick="doLogout()" style="background:#333;border:1px solid var(--border);color:var(--text-secondary);padding:.25rem .6rem;border-radius:4px;cursor:pointer;font-size:.75rem;margin-left:.5rem">Đăng xuất</button>
</div>
</header>

<div id="auth-blocker" style="display:none;position:fixed;inset:0;background:var(--bg);z-index:1000;align-items:center;justify-content:center;flex-direction:column;gap:1rem">
  <div style="font-size:3rem">🔒</div>
  <div id="auth-msg" style="font-size:1rem;color:var(--text)"></div>
  <a href="/" style="color:var(--orange);text-decoration:none;padding:.5rem 1rem;border:1px solid var(--orange);border-radius:6px;font-size:.85rem">← Về trang đăng nhập</a>
</div>

<div class="layout">
<div class="main">
  <nav class="tab-nav" role="tablist" aria-label="Khu vực dashboard">
    <div class="tab-nav-wrap" id="tab-nav-wrap">
    <div class="tab-track" id="tab-track">
      <div class="tab-indicator" id="tab-indicator" aria-hidden="true"></div>
      <button class="tab-btn active" role="tab" aria-selected="true" aria-controls="panel-overview" data-tab="overview" id="tab-btn-overview" onclick="switchTab('overview')">
        <span class="tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-6M22 20H2"/></svg></span>
        <span class="tab-label">Tổng quan</span>
      </button>
      <button class="tab-btn" role="tab" aria-selected="false" aria-controls="panel-workpool" data-tab="workpool" id="tab-btn-workpool" onclick="switchTab('workpool')">
        <span class="tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg></span>
        <span class="tab-label">Bể công việc</span>
      </button>
      <button class="tab-btn" role="tab" aria-selected="false" aria-controls="panel-metrics" data-tab="metrics" id="tab-metrics-btn" onclick="switchTab('metrics')">
        <span class="tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M22 7l-8.5 8.5-4-4L2 17"/><path d="M16 7h6v6"/></svg></span>
        <span class="tab-label">Chỉ số</span>
      </button>
      <button class="tab-btn" role="tab" aria-selected="false" aria-controls="panel-ai" data-tab="ai" id="tab-ai-btn" onclick="switchTab('ai')">
        <span class="tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 2a4 4 0 0 1 4 4c0 1.5-.8 2.8-2 3.4V11h-4V9.4A4 4 0 0 1 12 2z"/><path d="M8 14h8v2a4 4 0 0 1-8 0v-2z"/><path d="M9 18h6M10 21h4"/></svg></span>
        <span class="tab-label">AI Tổ chức</span>
      </button>
      <button class="tab-btn" role="tab" aria-selected="false" aria-controls="panel-field" data-tab="field" id="tab-field-btn" onclick="switchTab('field')">
        <span class="tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M12 18h.01"/></svg></span>
        <span class="tab-label">Hiện trường</span>
      </button>
      <button class="tab-btn" role="tab" aria-selected="false" aria-controls="panel-taskform" data-tab="taskform" id="tab-taskform-btn" onclick="switchTab('taskform')">
        <span class="tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></span>
        <span class="tab-label">Tạo / Sửa task</span>
      </button>
    </div>
    </div>
  </nav>
  <div id="panel-overview" class="tab-panel active" role="tabpanel" aria-labelledby="tab-btn-overview">
  <div class="cards" id="cards"></div>
  <div class="charts">
    <div class="chart-box"><h3>Trạng thái</h3><canvas id="statusChart"></canvas></div>
    <div class="chart-box"><h3>Nhân viên — phân bổ task</h3><canvas id="staffChart"></canvas></div>
  </div>
  <div class="table-box">
    <h3>Hiệu quả nhân viên</h3>
    <div class="table-scroll">
    <table><thead><tr><th>Nhân sự</th><th>Tasks</th><th>Xong</th><th>Đang làm</th><th>Tiến độ</th><th>Báo cáo</th><th>Giờ</th></tr></thead><tbody id="staff-table"></tbody></table>
    </div>
  </div>
  <div class="table-box">
    <h3>⚠️ Tasks quá hạn</h3>
    <div id="overdue-list"></div>
  </div>
  </div>
  <div id="panel-workpool" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-workpool">
    <div class="table-box">
      <h3>Bể công việc nhân viên — Lương 3P · Trình độ · Năng lực · Hiệu quả · So sánh Job</h3>
      <div class="pool-toolbar" id="workpool-toolbar">
        <select id="workpool-filter" onchange="filterWorkPool()"><option value="">Tất cả nhân viên</option></select>
        <span style="font-size:.78rem;color:var(--text-secondary)">Bậc việc · Mức ưu tiên · % phần việc trong job lớn</span>
      </div>
      <div id="workpool-grid" class="pool-grid"><p style="color:var(--text-secondary)">Đang tải...</p></div>
    </div>
  </div>
  <div id="panel-metrics" class="tab-panel" role="tabpanel" aria-labelledby="tab-metrics-btn">
    <div class="table-box">
      <h3>Chỉ số thống kê (đang chờ logic từ team)</h3>
      <div class="metrics-placeholder">
        <p style="font-size:1rem;margin-bottom:.5rem">📈 Khu vực chỉ số KPI tùy chỉnh</p>
        <p style="font-size:.85rem;max-width:520px;margin:0 auto;line-height:1.6">
          Team sẽ cung cấp công thức tính sau. Hiện tại dùng tab <strong>Tổng quan</strong> và <strong>Bể công việc</strong> để theo dõi tiến độ, 3P, năng lực và so sánh job.
        </p>
      </div>
    </div>
  </div>
  <div id="panel-ai" class="tab-panel" role="tabpanel" aria-labelledby="tab-ai-btn">
    <div class="ai-box" id="ai-organize"><p style="color:var(--text-secondary)">Đang phân tích dữ liệu...</p></div>
  </div>
  <div id="panel-field" class="tab-panel" role="tabpanel" aria-labelledby="tab-field-btn">
    <div id="field-panel"><p style="color:var(--text-secondary)">Đang tải kênh hiện trường...</p></div>
  </div>
  <div id="panel-taskform" class="tab-panel" role="tabpanel" aria-labelledby="tab-taskform-btn">
    <div class="taskform-grid">
      <div class="table-box tf-card">
        <h3>🆕 Tạo task mới</h3>
        <label class="tf-label">Tên công việc *</label>
        <input id="tf-name" class="tf-input" placeholder="VD: Lắp đặt PCCC tầng 3">
        <div class="tf-row">
          <div><label class="tf-label">Thực hiện (PIC)</label><input id="tf-pic" class="tf-input" placeholder="VD: Phan Minh Hoàng"></div>
          <div><label class="tf-label">Kiểm tra</label><input id="tf-reviewer" class="tf-input" placeholder="(tuỳ chọn)"></div>
        </div>
        <div class="tf-row">
          <div><label class="tf-label">Bắt đầu</label><input id="tf-start" class="tf-input" type="date"></div>
          <div><label class="tf-label">Kết thúc (deadline)</label><input id="tf-end" class="tf-input" type="date"></div>
        </div>
        <div class="tf-row">
          <div><label class="tf-label">Thời lượng (ngày)</label><input id="tf-duration" class="tf-input" type="number" min="0" placeholder="VD: 3"></div>
          <div><label class="tf-label">Zone / Hạng mục</label><input id="tf-zone" class="tf-input" placeholder="(tuỳ chọn)"></div>
        </div>
        <label class="tf-label">Ghi chú</label>
        <input id="tf-note" class="tf-input" placeholder="(tuỳ chọn)">
        <label class="tf-label">Ghi vào sheet</label>
        <select id="tf-source" class="tf-input">
          <option value="1">Sheet 1 (chính)</option>
          <option value="2">Sheet 2 (Masterplan QLXD)</option>
        </select>
        <button class="tf-btn tf-btn-create" onclick="taskCreate()">Tạo task</button>
        <div class="tf-msg" id="tf-create-msg"></div>
      </div>
      <div class="table-box tf-card">
        <h3>✏️ Cập nhật task</h3>
        <label class="tf-label">Mã task (ID) *</label>
        <input id="tu-id" class="tf-input" placeholder="VD: CO-001" style="text-transform:uppercase">
        <label class="tf-label">Trạng thái</label>
        <select id="tu-status" class="tf-input">
          <option value="">— giữ nguyên —</option>
          <option>Chưa làm</option>
          <option>Đang làm</option>
          <option>Hoàn thành</option>
        </select>
        <div class="tf-row">
          <div><label class="tf-label">Đổi PIC</label><input id="tu-pic" class="tf-input" placeholder="(tuỳ chọn)"></div>
          <div><label class="tf-label">Đổi deadline</label><input id="tu-end" class="tf-input" type="date"></div>
        </div>
        <label class="tf-label">Ghi chú</label>
        <input id="tu-note" class="tf-input" placeholder="(tuỳ chọn)">
        <button class="tf-btn tf-btn-update" onclick="taskUpdate()">Cập nhật task</button>
        <div class="tf-msg" id="tf-update-msg"></div>
      </div>
    </div>
  </div>
</div>

<a href="/" class="mobile-chat-fab" aria-label="Mở chatbot BHI Agent">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
  Chatbot
</a>

<div class="sidebar">
  <div class="chat-header"><span>●</span> BHI Agent</div>
  <div class="chat-messages" id="chat-messages">
    <div class="chat-msg chat-msg-bot">Hỏi tôi về task, nhân viên, tiến độ dự án...</div>
  </div>
  <div class="chat-quick">
    <button onclick="chatSend('Task đang trễ hạn')">Trễ hạn</button>
    <button onclick="chatSend('Task đang làm')">Đang làm</button>
    <button onclick="chatSend('hiệu quả công việc của Phan Minh Hoàng')">Hiệu quả PMH</button>
    <button onclick="chatSend('Báo cáo hôm nay')">Báo cáo</button>
  </div>
  <div class="chat-input">
    <input id="chat-in" placeholder="Hỏi nhanh..." onkeydown="if(event.key==='Enter')chatSendInput()">
    <button onclick="chatSendInput()">→</button>
  </div>
</div>
</div>

<script>
const STORAGE_KEY = 'bhi_user_session';
const DASHBOARD_ROLES = ['super_admin', 'admin', 'manager', 'member'];
const PRIVILEGED_ROLES = ['super_admin', 'admin', 'manager'];

// === Auth check trước khi render dashboard ===
function _loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data.expires || Date.now() >= data.expires) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    if (data.origin && data.origin !== window.location.origin) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return data;
  } catch (e) {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function _showAuthBlocker(msg) {
  document.getElementById('auth-msg').textContent = msg;
  document.getElementById('auth-blocker').style.display = 'flex';
}

function doLogout() {
  localStorage.removeItem(STORAGE_KEY);
  window.location.href = '/';
}

const session = _loadSession();
let workPoolData = [];
if (!session) {
  _showAuthBlocker('Vui lòng đăng nhập để xem Dashboard');
} else if (!DASHBOARD_ROLES.includes(session.role)) {
  _showAuthBlocker(`Vai trò "${session.role}" không có quyền xem Dashboard.`);
} else {
  document.getElementById('user-info').style.display = 'flex';
  const roleIcon = session.role==='super_admin'?'👑':(session.role==='admin'?'🔑':(session.role==='manager'?'📋':'👤'));
  document.getElementById('user-display').textContent = roleIcon + ' ' + session.name;
  const isMember = !PRIVILEGED_ROLES.includes(session.role);
  if (isMember) {
    document.getElementById('tab-ai-btn').style.display = 'none';
    document.getElementById('tab-metrics-btn').style.display = 'none';
    document.querySelector('[data-tab="overview"]').style.display = 'none';
    switchTab('workpool');
  }
  loadWorkPool();
  loadFieldPanel();
  if (!isMember) {
    loadDashboard();
    loadAiOrganize();
  }
  initTabNav();
  if(gsapOk()&&!gsapReduce()){
    gsap.from('header',{y:-12,autoAlpha:0,duration:.45,ease:'power2.out'});
    gsap.from('.tab-btn',{opacity:0,y:10,stagger:.05,duration:.38,delay:.08,ease:'power2.out'});
    gsap.from('.sidebar',{x:24,autoAlpha:0,duration:.5,ease:'power2.out',delay:.15});
  }
}

function gsapOk(){return typeof gsap!=='undefined';}
function gsapReduce(){return window.matchMedia('(prefers-reduced-motion: reduce)').matches;}
if(gsapOk())gsap.defaults({duration:.42,ease:'power2.out'});
function animateIn(sel,opts){
  if(!gsapOk()||gsapReduce())return;
  const els=document.querySelectorAll(sel);
  if(!els.length)return;
  gsap.from(els,Object.assign({opacity:0,y:16,stagger:.05,clearProps:'opacity'},opts||{}));
}
function updateTabIndicator(btn,animate){
  const track=document.getElementById('tab-track');
  const ind=document.getElementById('tab-indicator');
  if(!track||!ind||!btn||btn.style.display==='none')return;
  const x=btn.offsetLeft;
  const w=btn.offsetWidth;
  const top=btn.offsetTop;
  if(gsapOk()&&animate&&!gsapReduce()){
    gsap.to(ind,{x:x,y:top,width:w,duration:.38,ease:'power3.out'});
    gsap.fromTo(btn.querySelector('.tab-icon'),{scale:.88,rotate:-6},{scale:1,rotate:0,duration:.32,ease:'back.out(2)'});
  }else{
    gsap.set(ind,{x:x,y:top,width:w});
  }
}
function updateTabScrollHints(){
  const track=document.getElementById('tab-track');
  const wrap=document.getElementById('tab-nav-wrap');
  if(!track||!wrap)return;
  const sl=track.scrollLeft;
  const max=track.scrollWidth-track.clientWidth-2;
  wrap.classList.toggle('can-scroll-left',sl>4);
  wrap.classList.toggle('can-scroll-right',sl<max);
}
function initTabNav(){
  const track=document.getElementById('tab-track');
  const active=document.querySelector('.tab-btn.active')||document.querySelector('.tab-btn');
  if(active)updateTabIndicator(active,false);
  if(!track)return;
  track.addEventListener('scroll',updateTabScrollHints,{passive:true});
  updateTabScrollHints();
  track.addEventListener('keydown',e=>{
    const tabs=[...track.querySelectorAll('.tab-btn')].filter(b=>b.style.display!=='none');
    const i=tabs.indexOf(document.activeElement);
    if(e.key==='ArrowRight'&&i<tabs.length-1){e.preventDefault();tabs[i+1].focus();switchTab(tabs[i+1].dataset.tab);}
    if(e.key==='ArrowLeft'&&i>0){e.preventDefault();tabs[i-1].focus();switchTab(tabs[i-1].dataset.tab);}
  });
  let resizeTimer;
  window.addEventListener('resize',()=>{
    clearTimeout(resizeTimer);
    resizeTimer=setTimeout(()=>{
      const cur=document.querySelector('.tab-btn.active');
      if(cur)updateTabIndicator(cur,false);
      updateTabScrollHints();
    },120);
  });
}
function switchTab(name){
  const prev=document.querySelector('.tab-panel.active');
  document.querySelectorAll('.tab-btn').forEach(b=>{
    const on=b.dataset.tab===name;
    b.classList.toggle('active',on);
    b.setAttribute('aria-selected',on?'true':'false');
  });
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  const panel=document.getElementById('panel-'+name);
  if(panel)panel.classList.add('active');
  const activeBtn=document.querySelector('.tab-btn.active');
  if(activeBtn){
    updateTabIndicator(activeBtn,true);
    activeBtn.scrollIntoView({behavior:gsapReduce()?'auto':'smooth',inline:'center',block:'nearest'});
  }
  updateTabScrollHints();
  if(gsapOk()&&!gsapReduce()){
    if(prev&&prev!==panel){
      gsap.to(prev,{autoAlpha:0,y:-10,duration:.2,ease:'power2.in',onComplete:()=>{
        gsap.set(prev,{autoAlpha:1,clearProps:'all'});
        gsap.fromTo(panel,{autoAlpha:0,y:14},{autoAlpha:1,y:0,duration:.35,ease:'power2.out'});
        animateIn('#panel-'+name+' .table-box, #panel-'+name+' .card, #panel-'+name+' .pool-card, #panel-'+name+' .field-card, #panel-'+name+' .ai-box, #panel-'+name+' .metrics-placeholder',{y:14,stagger:.06});
      }});
    }else{
      animateIn('#panel-'+name+' .table-box, #panel-'+name+' .card, #panel-'+name+' .pool-card, #panel-'+name+' .field-card, #panel-'+name+' .ai-box, #panel-'+name+' .metrics-placeholder',{y:14,stagger:.06});
    }
  }
}
async function loadWorkPool(){
  try{
    const r=await fetch('/api/dashboard/work-pool',{headers:{'Authorization':'Bearer '+session.token}});
    if(!r.ok){document.getElementById('workpool-grid').innerHTML='<p>Lỗi tải bể công việc</p>';return;}
    const d=await r.json();
    workPoolData=d.employees||[];
    const sel=document.getElementById('workpool-filter');
    if(sel && PRIVILEGED_ROLES.includes(session.role)){
      const names=workPoolData.map(e=>e.employee);
      sel.innerHTML='<option value="">Tất cả nhân viên ('+names.length+')</option>'+names.map(n=>'<option value="'+n+'">'+n+'</option>').join('');
      document.getElementById('workpool-toolbar').style.display='flex';
    } else if(sel){sel.parentElement.style.display='none';}
    renderWorkPool(workPoolData);
    animateIn('#workpool-grid .pool-card',{y:20,stagger:.05});
  }catch(e){document.getElementById('workpool-grid').innerHTML='<p>Lỗi: '+e.message+'</p>';}
}
function filterWorkPool(){
  const v=document.getElementById('workpool-filter').value;
  renderWorkPool(v?workPoolData.filter(e=>e.employee===v):workPoolData);
  animateIn('#workpool-grid .pool-card',{y:16,stagger:.04});
}
function renderWorkPool(employees){
  const el=document.getElementById('workpool-grid');
  if(!employees.length){el.innerHTML='<p>Chưa có dữ liệu bể công việc.</p>';return;}
  el.innerHTML=employees.map(emp=>{
    const p=emp.profile, w=emp.work_pool;
    const s3p=p.salary_3p||{};
    const tasks=(emp.current_tasks||[]).slice(0,6).map(t=>{
      const pc=t.priority==='Khẩn cấp'?'priority-khan':(t.priority==='Cao'?'priority-cao':'');
      return `<tr class="${pc}"><td>${t.id}</td><td>B${t.job_level}</td><td>${t.priority}</td><td>${t.status}</td><td>${t.name.substring(0,40)}</td></tr>`;
    }).join('');
    const cmp=(emp.job_comparisons||[]).map(c=>
      `<div class="pool-detail"><strong>📦 ${c.parent_job_id}</strong> — ${c.parent_job_name||''}<br>
        Việc đang làm: <b>${c.user_active}</b> / Giao: <b>${c.user_assigned}</b> · Pool job: <b>${c.pool_total_tasks}</b> task
        · Bạn gánh <b>${c.user_share_pct}%</b> · Tiến độ chung <b>${c.pool_completion_rate}%</b>
        ${c.coverage_gap?' · Còn <b>'+c.coverage_gap+'</b> việc chưa phân':''}
      </div>`
    ).join('');
    return `<div class="pool-card"><h4>${emp.employee} <span class="role-pill">${p.job_grade} · L${p.skill_level}</span></h4>
      <div class="pool-metrics">
        <span>3P P/Pf/Ps<br><b>${s3p.position||'—'}/${s3p.person||'—'}/${s3p.performance||'—'}</b></span>
        <span>Năng lực<br><b>${p.competency_score}%</b></span>
        <span>Hiệu quả<br><b>${p.efficiency_score}%</b></span>
      </div>
      <div style="font-size:.78rem;color:var(--text-secondary)">Đang làm: <b>${w.active}</b> · Hoàn thành: <b>${w.done}/${w.total}</b> (${w.completion_rate}%) · Ưu tiên mặc định: ${p.default_priority}</div>
      <div class="pool-detail"><table><thead><tr><th>ID</th><th>Bậc</th><th>Ưu tiên</th><th>TT</th><th>Tên việc</th></tr></thead><tbody>${tasks||'<tr><td colspan="5">Chưa có task</td></tr>'}</tbody></table></div>
      ${cmp||'<div class="pool-detail">Chưa có so sánh job lớn.</div>'}
    </div>`;
  }).join('');
}
async function loadAiOrganize(){
  try{
    const r=await fetch('/api/dashboard/ai-organize',{headers:{'Authorization':'Bearer '+session.token}});
    if(!r.ok)return;
    const d=await r.json();
    const el=document.getElementById('ai-organize');
    const alerts=(d.priority_alerts||[]).slice(0,5).map(a=>'<li><b>'+a.name+'</b>: '+a.urgent_count+' việc khẩn — '+((a.tasks||[]).map(t=>t.id).join(', '))+'</li>').join('');
    el.innerHTML=`<h3>🤖 AI gợi ý tổ chức dữ liệu</h3>
      <p style="font-size:.82rem;color:var(--text-secondary)">${d.note||''}</p>
      <p style="font-size:.85rem;margin:.5rem 0">Quá tải: <strong>${d.summary.overloaded}</strong> · Sẵn sàng nhận việc: <strong>${d.summary.underutilized}</strong> · Cảnh báo ưu tiên: <strong>${d.summary.priority_alerts}</strong></p>
      ${alerts?'<ul style="margin:.5rem 0">'+alerts+'</ul>':''}
      <h4 style="font-size:.8rem;margin-top:.8rem;color:var(--text-secondary)">Gợi ý hành động</h4>
      <ul>${(d.suggestions||[]).map(s=>'<li>'+s+'</li>').join('')}</ul>`;
    animateIn('#ai-organize > *',{y:10,stagger:.04});
  }catch(e){}
}
async function loadFieldPanel(){
  const el=document.getElementById('field-panel');
  const isAdmin=['super_admin','admin'].includes(session.role);
  const canPending=['super_admin','admin','manager'].includes(session.role);
  try{
    const [st, linksR, pendingR]=await Promise.all([
      fetch('/api/messaging/status').then(r=>r.json()),
      fetch('/api/messaging/links',{headers:{'Authorization':'Bearer '+session.token}}).then(r=>r.ok?r.json():{links:[]}),
      canPending?fetch('/api/messaging/pending',{headers:{'Authorization':'Bearer '+session.token}}).then(r=>r.ok?r.json():{pending:[]}):Promise.resolve({pending:[]}),
    ]);
    const links=linksR.links||[];
    const myLink=links.find(l=>(l.email||'').toLowerCase()===(session.email||'').toLowerCase());
    let h=`<div class="field-grid">
      <div class="field-card"><h4>📡 Trạng thái kênh</h4>
        <div class="field-status">
          <span class="status-dot ${st.telegram.enabled?'on':'off'}">Telegram ${st.telegram.enabled?'BẬT':'chưa cấu hình'}</span>
          <span class="status-dot ${st.zalo.enabled?'on':'off'}">Zalo ${st.zalo.enabled?'BẬT':'chưa cấu hình'}</span>
        </div>
        <p style="font-size:.78rem;color:var(--text-secondary);line-height:1.5">
          Gửi tin nhắn hoặc <b>voice</b> (Telegram) → chatbot ghi báo cáo / cập nhật task vào sheet sau khi xác nhận <code>ok</code>.
        </p>
        <ul style="font-size:.75rem;margin:.5rem 0 0 1rem;color:var(--text-secondary)">${(st.supported_commands||[]).map(c=>'<li><code>'+c+'</code></li>').join('')}</ul>
      </div>
      <div class="field-card"><h4>🔗 Liên kết của bạn</h4>
        ${myLink?'<p style="font-size:.82rem">Telegram: <code>'+(myLink.telegram_chat_id||'—')+'</code><br>Zalo: <code>'+(myLink.zalo_user_id||'—')+'</code></p>':'<p style="font-size:.82rem;color:var(--orange)">Chưa liên kết. Gửi /start trên Telegram để lấy chat_id, rồi nhờ Admin liên kết.</p>'}
      </div>`;
    if(isAdmin){
      h+=`<div class="field-card" style="grid-column:1/-1"><h4>⚙️ Admin — Liên kết nhân sự</h4>
        <div class="field-form" style="grid-template-columns:1fr 1fr 1fr 1fr auto;align-items:end">
          <input id="link-email" placeholder="Email nhân sự">
          <input id="link-name" placeholder="Tên (tuỳ chọn)">
          <input id="link-tg" placeholder="Telegram chat_id">
          <input id="link-zalo" placeholder="Zalo user_id">
          <button onclick="saveMessagingLink()">Lưu</button>
        </div>
        <p style="font-size:.75rem;color:var(--text-secondary);margin-top:.5rem">Hoặc chạy bootstrap: POST /api/messaging/bootstrap</p>
        <div class="table-scroll" style="margin-top:.8rem"><table><thead><tr><th>Tên</th><th>Email</th><th>Telegram</th><th>Zalo</th></tr></thead><tbody>
          ${links.map(l=>'<tr><td>'+(l.name||'')+'</td><td>'+l.email+'</td><td>'+(l.telegram_chat_id||'—')+'</td><td>'+(l.zalo_user_id||'—')+'</td></tr>').join('')}
        </tbody></table></div>
      </div>`;
    }
    if(canPending && (pendingR.pending||[]).length){
      h+=`<div class="field-card"><h4>⏳ ID chờ liên kết</h4><ul class="pending-list">${pendingR.pending.map(p=>'<li><b>'+p.platform+'</b> '+p.platform_id+(p.display_name?' — '+p.display_name:'')+'</li>').join('')}</ul></div>`;
    }
    h+='</div>';
    el.innerHTML=h;
    animateIn('#field-panel .field-card',{y:18,stagger:.06});
  }catch(e){el.innerHTML='<p>Lỗi tải hiện trường: '+e.message+'</p>';}
}
async function saveMessagingLink(){
  const body={email:document.getElementById('link-email').value,name:document.getElementById('link-name').value,telegram_chat_id:document.getElementById('link-tg').value,zalo_user_id:document.getElementById('link-zalo').value};
  const r=await fetch('/api/messaging/link',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+session.token},body:JSON.stringify(body)});
  if(r.ok){loadFieldPanel();alert('Đã lưu liên kết');}else{const e=await r.json().catch(()=>({}));alert('Lỗi: '+(e.detail||r.status));}
}
async function loadDashboard(){
  try {
    const r = await fetch('/api/dashboard', {headers: {'Authorization': 'Bearer ' + session.token}});
    if (!r.ok) {
      const err = await r.json().catch(() => ({detail: r.statusText}));
      _showAuthBlocker('Lỗi tải Dashboard: ' + (err.detail || 'unknown'));
      return;
    }
    const d = await r.json();
    renderCards(d.summary);renderCharts(d);renderStaffTable(d.staff);renderOverdue(d.overdue_tasks);
  } catch(e) {
    _showAuthBlocker('Lỗi kết nối: ' + e.message);
  }
}
function renderCards(s){
  document.getElementById('cards').innerHTML=`
    <div class="card"><div class="card-value">${s.total_tasks}</div><div class="card-label">Tổng tasks</div></div>
    <div class="card green"><div class="card-value">${s.done}</div><div class="card-label">Hoàn thành</div></div>
    <div class="card orange"><div class="card-value">${s.doing}</div><div class="card-label">Đang làm</div></div>
    <div class="card"><div class="card-value">${s.todo}</div><div class="card-label">Chưa làm</div></div>
    <div class="card warn"><div class="card-value">${s.overdue}</div><div class="card-label">Quá hạn</div></div>
    <div class="card"><div class="card-value">${s.total_staff}</div><div class="card-label">Nhân sự</div></div>`;
  if (window.gsap) {
    gsap.from('.card', {opacity:0, y:18, duration:.4, stagger:.06, ease:'power2.out'});
    document.querySelectorAll('.card-value').forEach(el => {
      const end = parseFloat(el.textContent) || 0;
      gsap.from(el, {textContent:0, duration:1, ease:'power1.out', snap:{textContent:1},
                     onUpdate(){el.textContent = Math.round(this.targets()[0].textContent);}});
    });
  }
}
let _statusChart=null,_staffChart=null;
function renderCharts(d){
  const s=d.summary;
  Chart.defaults.font.family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";
  Chart.defaults.font.size=11;
  // Hủy chart cũ trước khi vẽ lại (tránh 'Canvas is already in use')
  if(_statusChart){_statusChart.destroy();_statusChart=null;}
  if(_staffChart){_staffChart.destroy();_staffChart=null;}
  _statusChart=new Chart(document.getElementById('statusChart'),{
    type:'doughnut',
    data:{labels:['Hoàn thành','Đang làm','Chưa làm'],datasets:[{data:[s.done,s.doing,s.todo],backgroundColor:['#16a34a','#ea580c','#d4d4d4'],borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:true,aspectRatio:window.innerWidth<900?1.3:1.6,cutout:'65%',plugins:{legend:{position:'bottom',labels:{padding:12,usePointStyle:true,pointStyle:'circle',color:'#999'}}}}
  });
  const top=d.staff.slice(0,8);
  _staffChart=new Chart(document.getElementById('staffChart'),{
    type:'bar',
    data:{labels:top.map(s=>s.name.split(' ').slice(-2).join(' ')),datasets:[
      {label:'Xong',data:top.map(s=>s.tasks_done),backgroundColor:'#16a34a'},
      {label:'Đang làm',data:top.map(s=>s.tasks_doing),backgroundColor:'#ea580c'},
      {label:'Chưa',data:top.map(s=>s.tasks_todo),backgroundColor:'#d4d4d4'},
    ]},
    options:{responsive:true,maintainAspectRatio:true,aspectRatio:window.innerWidth<900?1.1:1.8,scales:{x:{stacked:true,grid:{display:false},ticks:{color:'#999',maxRotation:45,minRotation:0}},y:{stacked:true,grid:{color:'#333'},ticks:{color:'#999'}}},plugins:{legend:{position:'bottom',labels:{padding:12,usePointStyle:true,pointStyle:'circle',color:'#999'}}}}
  });
}
function renderStaffTable(staff){
  document.getElementById('staff-table').innerHTML=staff.map(s=>{
    const cls=s.completion_rate===0?'rate-zero':s.completion_rate<50?'rate-low':'';
    return `<tr><td><strong>${s.name}</strong></td><td>${s.tasks_total}</td><td>${s.tasks_done}</td><td>${s.tasks_doing}</td><td><span class="progress-bar ${cls}"><span class="progress-fill" style="width:${s.completion_rate}%"></span><span class="progress-text">${s.completion_rate}%</span></span></td><td>${s.reports}</td><td>${s.hours}h</td></tr>`;
  }).join('');
  if (window.gsap) {
    gsap.from('#staff-table tr', {opacity:0, x:-12, duration:.3, stagger:.03, ease:'power2.out'});
    gsap.from('.progress-fill', {width:0, duration:.9, ease:'power2.out', delay:.2});
    gsap.from('.chart-box', {opacity:0, y:20, duration:.5, stagger:.1, ease:'power2.out'});
  }
}
function renderOverdue(tasks){
  const el=document.getElementById('overdue-list');
  if(!tasks.length){el.innerHTML='<p style="color:var(--green);font-size:.85rem">✓ Không có task quá hạn</p>';return;}
  el.innerHTML=tasks.map(t=>`<div class="overdue-item"><span class="task-id">${t.id}</span><span class="task-name">${t.name.substring(0,45)}</span><span class="task-meta">${t.pic.split(',')[0].split(' ').slice(-1)} · ${t.end_date}</span></div>`).join('');
  if (window.gsap) gsap.from('.overdue-item', {opacity:0, x:14, duration:.3, stagger:.04, ease:'power2.out'});
}
// Chat sidebar — SSE streaming giống trang chat chính
const chatMsgs=document.getElementById('chat-messages');
function _escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function _chatMd(text){let html=_escHtml(text).replace(/`([^`]+?)`/g,'<code>$1</code>').replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>').replace(/\\[(.+?)\\]\\((.+?)\\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');if(session&&session.token)html=html.replace(/(href="\\/api\\/export\\/[^"]+)"/g,'$1?token='+session.token+'"');return html;}
function addChatMsg(text,role){const d=document.createElement('div');d.className='chat-msg chat-msg-'+role;d.innerHTML=_chatMd(text);chatMsgs.appendChild(d);if(window.gsap)gsap.from(d,{opacity:0,y:10,duration:.3,ease:'power2.out'});chatMsgs.scrollTop=chatMsgs.scrollHeight;}
function _renderChatBotHtml(text){return _chatMd(text);}
async function chatSend(text){
  if(!session) return;
  addChatMsg(text,'user');
  const typingEl=document.createElement('div');
  typingEl.className='chat-msg chat-msg-bot';
  typingEl.innerHTML='<span class="chat-typing"><span></span><span></span><span></span></span>';
  chatMsgs.appendChild(typingEl);
  chatMsgs.scrollTop=chatMsgs.scrollHeight;
  const botEl=document.createElement('div');
  botEl.className='chat-msg chat-msg-bot';
  let streamed='';
  try{
    const r=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+session.token},body:JSON.stringify({message:text})});
    if(r.status===401){typingEl.remove();addChatMsg('🔒 Phiên đăng nhập đã hết hạn.','bot');return;}
    if(!r.ok||!r.body)throw new Error('HTTP '+r.status);
    const reader=r.body.getReader();
    const decoder=new TextDecoder();
    let buffer='';
    while(true){
      const {done,value}=await reader.read();
      if(done)break;
      buffer+=decoder.decode(value,{stream:true});
      const parts=buffer.split('\\n\\n');
      buffer=parts.pop()||'';
      for(const part of parts){
        const line=part.trim();
        if(!line.startsWith('data:'))continue;
        let evt;
        try{evt=JSON.parse(line.slice(5).trim());}catch(e){continue;}
        if(evt.type==='token'){
          if(typingEl.parentNode){typingEl.remove();chatMsgs.appendChild(botEl);}
          streamed+=evt.content||'';
          botEl.innerHTML=_renderChatBotHtml(streamed);
          chatMsgs.scrollTop=chatMsgs.scrollHeight;
        }
        if(evt.type==='error'){
          if(typingEl.parentNode){typingEl.remove();chatMsgs.appendChild(botEl);}
          streamed=evt.content||'Có lỗi xảy ra.';
          botEl.innerHTML=_renderChatBotHtml(streamed);
        }
      }
    }
    if(typingEl.parentNode)typingEl.remove();
    if(!streamed){chatMsgs.appendChild(botEl);botEl.innerHTML=_renderChatBotHtml('😅 Mình chưa nhận được phản hồi, bạn thử lại nhé.');}
    if(window.gsap)gsap.from(botEl,{opacity:0,y:10,duration:.3,ease:'power2.out'});
    chatMsgs.scrollTop=chatMsgs.scrollHeight;
  }catch(e){
    if(typingEl.parentNode)typingEl.remove();
    if(botEl.parentNode)botEl.remove();
    try{
      const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+session.token},body:JSON.stringify({message:text})});
      if(r.status===401){addChatMsg('🔒 Phiên đăng nhập đã hết hạn.','bot');return;}
      const data=await r.json();
      addChatMsg(data.response,'bot');
    }catch(e2){
      addChatMsg('❌ Lỗi: '+e.message,'bot');
    }
  }
}
function chatSendInput(){const i=document.getElementById('chat-in');const t=i.value.trim();if(t){chatSend(t);i.value='';}}

// ── Tạo / Cập nhật task (tab Tạo / Sửa task) ──
function _tfMsg(id,text,ok){const e=document.getElementById(id);e.textContent=text;e.className='tf-msg '+(ok?'ok':'err');}
function _val(id){const e=document.getElementById(id);return e?e.value.trim():'';}

async function taskCreate(){
  const name=_val('tf-name');
  if(!name){_tfMsg('tf-create-msg','⚠️ Nhập tên công việc.',false);return;}
  const body={name,pic:_val('tf-pic'),reviewer:_val('tf-reviewer'),
    start_date:_val('tf-start')||null,end_date:_val('tf-end')||null,
    zone:_val('tf-zone'),note:_val('tf-note'),source:_val('tf-source')||'1'};
  const dur=_val('tf-duration'); if(dur) body.duration=parseInt(dur,10);
  _tfMsg('tf-create-msg','⏳ Đang tạo...',true);
  try{
    const r=await fetch('/api/tasks/create',{method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+session.token},
      body:JSON.stringify(body)});
    const d=await r.json().catch(()=>({}));
    if(!r.ok){_tfMsg('tf-create-msg','❌ '+(d.detail||('Lỗi '+r.status)),false);return;}
    _tfMsg('tf-create-msg','✅ '+(d.message||'Đã tạo task.'),true);
    ['tf-name','tf-pic','tf-reviewer','tf-start','tf-end','tf-duration','tf-zone','tf-note'].forEach(i=>{const e=document.getElementById(i);if(e)e.value='';});
    if(typeof loadDashboard==='function')loadDashboard();
  }catch(e){_tfMsg('tf-create-msg','❌ Lỗi kết nối: '+e.message,false);}
}

async function taskUpdate(){
  const task_id=_val('tu-id').toUpperCase();
  if(!task_id){_tfMsg('tf-update-msg','⚠️ Nhập mã task (VD: CO-001).',false);return;}
  const body={task_id};
  const st=_val('tu-status'); if(st) body.status=st;
  const pic=_val('tu-pic'); if(pic) body.pic=pic;
  const end=_val('tu-end'); if(end) body.end_date=end;
  const note=_val('tu-note'); if(note) body.note=note;
  if(Object.keys(body).length<=1){_tfMsg('tf-update-msg','⚠️ Chọn ít nhất 1 trường để cập nhật.',false);return;}
  _tfMsg('tf-update-msg','⏳ Đang cập nhật...',true);
  try{
    const r=await fetch('/api/tasks/update',{method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+session.token},
      body:JSON.stringify(body)});
    const d=await r.json().catch(()=>({}));
    if(!r.ok){_tfMsg('tf-update-msg','❌ '+(d.detail||('Lỗi '+r.status)),false);return;}
    _tfMsg('tf-update-msg','✅ '+(d.message||'Đã cập nhật.'),true);
    if(typeof loadDashboard==='function')loadDashboard();
  }catch(e){_tfMsg('tf-update-msg','❌ Lỗi kết nối: '+e.message,false);}
}
</script>
</body>
</html>"""
