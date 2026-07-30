from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def chat_ui():
    return CHAT_HTML


CHAT_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BHI Agent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#1a1a1a;--surface:#2a2a2a;--border:#3a3a3a;--text:#e8e8e8;--text-secondary:#999;--accent:#d97706;--green:#4ade80;--orange:#fb923c;--red:#f87171}
html,body{height:100%}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden;-webkit-font-smoothing:antialiased}
header{flex-shrink:0;background:#111;border-bottom:1px solid var(--border);padding:.7rem 1.5rem;display:flex;align-items:center;gap:.8rem}
header h1{font-size:1rem;font-weight:600;color:var(--text)}
.badge{background:#333;border:1px solid var(--border);padding:.2rem .5rem;border-radius:3px;font-size:.75rem;color:var(--text-secondary)}
.header-links{margin-left:auto;display:flex;align-items:center;gap:1rem}
.header-links a{color:var(--text-secondary);text-decoration:none;font-size:.85rem;transition:color .2s}
.header-links a:hover{color:var(--text)}
.user-info{font-size:.85rem;color:var(--text-secondary);display:flex;align-items:center;gap:.5rem}
.container{display:flex;flex-direction:column;max-width:900px;width:100%;margin:0 auto;padding:1rem;flex:1;min-height:0}
.messages{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:.5rem;display:flex;flex-direction:column;gap:.6rem;scroll-behavior:smooth}
.messages::-webkit-scrollbar{width:6px}
.messages::-webkit-scrollbar-track{background:transparent}
.messages::-webkit-scrollbar-thumb{background:#444;border-radius:3px}
.messages::-webkit-scrollbar-thumb:hover{background:#555}
.msg{max-width:82%;padding:.7rem 1rem;border-radius:14px;font-size:.9rem;line-height:1.6;white-space:pre-wrap;word-break:break-word;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.msg-user{align-self:flex-end;background:linear-gradient(135deg,#fff,#f0f0f0);color:#111;border-bottom-right-radius:4px}
.msg-bot{align-self:flex-start;background:#2f2f2f;border:1px solid #3a3a3a;border-bottom-left-radius:4px;color:var(--text)}
.msg-bot strong{color:#fff;font-weight:600}
.msg-bot a{color:var(--orange);text-decoration:none;border-bottom:1px dashed var(--orange)}
.msg-bot a:hover{opacity:.8}
.msg-bot code,.msg-user code{font-family:'SF Mono',Consolas,Menlo,monospace;font-size:.82em;background:rgba(217,119,6,.16);color:var(--accent);padding:.08rem .35rem;border-radius:5px;white-space:nowrap}
.msg-user code{background:rgba(0,0,0,.08);color:#7c3a00}
.tool-badge{display:inline-block;background:#222;border:1px solid #444;color:var(--green);padding:.1rem .45rem;border-radius:4px;font-size:.68rem;margin-bottom:.35rem;letter-spacing:.02em}
.typing-dots{display:inline-flex;gap:4px;align-items:center;padding:.3rem 0}
.typing-dots span{width:7px;height:7px;border-radius:50%;background:var(--text-secondary);animation:tdot 1.2s infinite ease-in-out}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}
@keyframes tdot{0%,60%,100%{opacity:.25;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}
.input-area{flex-shrink:0;display:flex;gap:.5rem;padding:.8rem;background:#222;border-top:1px solid var(--border)}
.input-area input{flex:1;padding:.6rem 1rem;border:1px solid var(--border);border-radius:20px;font-size:.9rem;outline:none;background:#333;color:var(--text)}
.input-area input:focus{border-color:#666}
.input-area input::placeholder{color:var(--text-secondary)}
.input-area button{padding:.6rem 1.2rem;background:#fff;color:#111;border:none;border-radius:20px;cursor:pointer;font-size:.9rem;font-weight:600}
.input-area button:hover{background:#ddd}
.suggestions{flex-shrink:0;display:flex;flex-wrap:wrap;gap:.4rem;padding:.5rem .8rem;max-height:80px;overflow-y:auto;border-top:1px solid var(--border);background:#222}
.suggestions button{background:#333;border:1px solid #444;border-radius:14px;padding:.3rem .7rem;font-size:.8rem;cursor:pointer;color:var(--text-secondary);white-space:nowrap}
.suggestions button:hover{background:#444;color:var(--text)}
.suggestions .sug-write{background:#3a2a10;border-color:#5a4420;color:#f0c070}
.suggestions .sug-write:hover{background:#4a3518;color:#ffd690}
.confirm-bar{display:flex;gap:.5rem;padding:.5rem .8rem;flex-shrink:0;background:#222;border-top:1px solid var(--border)}
.confirm-bar button{flex:1;padding:.65rem;border:none;border-radius:10px;font-size:.95rem;font-weight:600;cursor:pointer}
.confirm-ok{background:var(--green);color:#06310f}
.confirm-ok:hover{filter:brightness(1.08)}
.confirm-cancel{background:#444;color:var(--text)}
.confirm-cancel:hover{background:#555}
.typing{flex-shrink:0;color:var(--text-secondary);font-size:.8rem;padding:.3rem .8rem}
#login-screen{display:flex;align-items:center;justify-content:center;flex:1;min-height:0}
.login-box{background:var(--surface);padding:2rem;border-radius:12px;border:1px solid var(--border);width:350px;text-align:center}
.login-box h2{margin-bottom:1rem;color:var(--text);font-size:1.1rem;font-weight:600}
.login-box input{width:100%;padding:.7rem 1rem;border:1px solid var(--border);border-radius:8px;font-size:.95rem;margin-bottom:.8rem;background:#333;color:var(--text);outline:none}
.login-box input:focus{border-color:#666}
.login-box input::placeholder{color:var(--text-secondary)}
.login-box button{width:100%;padding:.7rem;background:#fff;color:#111;border:none;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:600}
.login-box button:hover{background:#ddd}
.login-divider{margin:.8rem 0;color:var(--text-secondary);font-size:.8rem}
.login-google{display:flex;align-items:center;justify-content:center;gap:.6rem;width:100%;padding:.7rem;background:#333;color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:.95rem;text-decoration:none;font-weight:500}
.login-google:hover{background:#444}
.login-error{color:var(--red);font-size:.85rem;margin-top:.5rem}
#chat-screen{display:none;flex-direction:column;flex:1;min-height:0}
.logout-btn{background:#333;border:1px solid var(--border);color:var(--text-secondary);padding:.3rem .6rem;border-radius:4px;cursor:pointer;font-size:.75rem}
.logout-btn:hover{color:var(--text);background:#444}
@media(max-width:640px){
  header{padding:.6rem .9rem}
  header h1{font-size:.95rem}
  .container{padding:.5rem}
  .msg{max-width:92%;font-size:.95rem}
  .input-area{padding:.6rem}
  .input-area input{font-size:16px}
  .input-area button{padding:.6rem 1rem}
  /* Gợi ý cuộn ngang 1 hàng, dễ chạm trên điện thoại */
  .suggestions{flex-wrap:nowrap;overflow-x:auto;max-height:none;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .suggestions::-webkit-scrollbar{display:none}
  .suggestions button{flex:0 0 auto;padding:.4rem .8rem}
  .confirm-bar button{padding:.8rem}
}
</style>
</head>
<body>
<header>
<span style="font-size:1.1rem">●</span>
<h1>BHI Agent</h1>
<span class="badge">QLXD</span>
<div class="header-links">
<a href="/dashboard" id="dashboard-link" style="display:none">📊 Dashboard</a>
<div class="user-info" id="user-info" style="display:none">
  <span id="user-display"></span>
  <button class="logout-btn" onclick="logout()">Đăng xuất</button>
</div>
</div>
</header>

<div id="login-screen">
<div class="login-box">
  <h2>🔐 Đăng nhập</h2>
  <input id="login-email" type="email" placeholder="Email" onkeydown="if(event.key==='Enter')doLogin()">
  <input id="login-password" type="password" placeholder="Mật khẩu" onkeydown="if(event.key==='Enter')doLogin()">
  <button onclick="doLogin()">Đăng nhập</button>
  <div class="login-divider" id="google-divider" style="display:none">— hoặc —</div>
  <a href="/auth/google" class="login-google" id="google-login-btn" style="display:none">
    <img src="https://www.google.com/favicon.ico" width="18" height="18" alt=""> Đăng nhập bằng Google (Gmail)
  </a>
  <div class="login-error" id="login-error"></div>
</div>
</div>

<div id="chat-screen">
<div class="container">
<div class="messages" id="messages"></div>
<div class="suggestions" id="suggestions">
<button onclick="send('Task của tôi')" title="Xem các task được giao cho bạn (PIC/Phối hợp/Kiểm tra)">📌 Task của tôi</button>
<button onclick="send('Task đang làm')" title="Lọc tất cả task có trạng thái Đang làm">⏳ Đang làm</button>
<button onclick="send('Task đã hoàn thành')" title="Lọc task có trạng thái Hoàn thành">🟢 Hoàn thành</button>
<button onclick="send('Task quá hạn')" title="Task chưa hoàn thành nhưng đã qua ngày kết thúc">🔴 Quá hạn</button>
<button onclick="send('Chi tiết task CO-001')" title="Xem đầy đủ 19 fields của 1 task cụ thể">🔍 Chi tiết CO-001</button>
<button onclick="send('Subtask của CO')" title="Xem các task con thuộc 1 hạng mục cha">📂 Subtask CO</button>
<button onclick="send('Báo cáo của tôi')" title="Xem báo cáo từ archive chung của masterplan (data toàn công ty)">📋 Báo cáo chung</button>
<button onclick="send('Log cá nhân của tôi')" title="Đọc từ file Excel cá nhân riêng (chi tiết hơn, có Tiến độ + Ghi chú phát sinh)">📒 Log cá nhân</button>
<button onclick="send('Giờ làm của tôi')" title="Tổng giờ làm theo dự án từ file cá nhân">⏱️ Giờ làm</button>
<button onclick="send('Hiệu quả công việc của Phan Minh Hoàng')" title="Năng lực, hiệu quả, 3P và bể công việc">📊 Hiệu quả PMH</button>
<button class="sug-write" onclick="fill('tạo task lắp PCCC tầng 3 giao Phan Minh Hoàng deadline 20/06/2026')" title="Tạo task mới — gõ: tạo task &lt;tên&gt; giao &lt;người&gt; deadline &lt;dd/mm/yyyy&gt;">🆕 Tạo task</button>
<button class="sug-write" onclick="fill('cập nhật CO-001 hoàn thành')" title="Cập nhật trạng thái: cập nhật &lt;TASK_ID&gt; &lt;trạng thái&gt;">✏️ Cập nhật task</button>
</div>
<div id="confirm-bar-holder"></div>
<div class="input-area">
<input id="input" type="text" placeholder="Hỏi, hoặc: tạo task… / cập nhật CO-001 hoàn thành" onkeydown="if(event.key==='Enter')sendMsg()">
<button onclick="sendMsg()">Gửi</button>
</div>
</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script>
const STORAGE_KEY = 'bhi_user_session';
const SESSION_TTL_MS = 24 * 60 * 60 * 1000; // 24h

let currentUser = null;

function _saveSession(user) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    ...user,
    origin: window.location.origin,
    expires: Date.now() + SESSION_TTL_MS,
  }));
}

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

function _enterChatScreen(user) {
  currentUser = user;
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('chat-screen').style.display = 'flex';
  document.getElementById('user-info').style.display = 'block';
  const roleTag = user.role==='super_admin'?' 👑':(user.role==='admin'?' 🔑':(user.role==='manager'?' 📋':''));
  document.getElementById('user-display').textContent = '👤 ' + user.name + roleTag;
  const dashLink = document.getElementById('dashboard-link');
  if (['super_admin','admin','manager','member'].includes(user.role)) {
    dashLink.style.display = 'inline';
  } else {
    dashLink.style.display = 'none';
  }
  if (window.gsap) {
    gsap.from('#chat-screen .suggestions button', {opacity:0, y:10, duration:.3, stagger:.04, ease:'power2.out', delay:.1});
    gsap.from('.input-area', {opacity:0, y:16, duration:.4, ease:'power2.out'});
  }
}

function showGreeting(user) {
  const tag = user.role === 'admin' ? ' 🔑 (Admin)' : '';
  const msg = `Xin chào **${user.name}**${tag}! 👋\\nBấm nút gợi ý bên dưới hoặc gõ câu hỏi để bắt đầu.`;
  addBotMsg(msg, null);
}

async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';
  if (!email || !password) { errEl.textContent = 'Vui lòng nhập email và mật khẩu.'; return; }
  try {
    const r = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, password})});
    const data = await r.json();
    if (!data.success) { errEl.textContent = data.error || 'Đăng nhập thất bại.'; return; }
    const user = {name: data.name, email: data.email, role: data.role, token: data.token};
    _saveSession(user);
    _enterChatScreen(user);
    showGreeting(user);
  } catch (e) {
    errEl.textContent = 'Lỗi kết nối: ' + e.message;
  }
}

function logout() {
  localStorage.removeItem(STORAGE_KEY);
  currentUser = null;
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('chat-screen').style.display = 'none';
  document.getElementById('user-info').style.display = 'none';
  document.getElementById('messages').innerHTML = '';
  showConfirmBar(false);
}

const msgsEl = document.getElementById('messages');
const inputEl = document.getElementById('input');

// Escape HTML rồi render markdown nhẹ: **bold**, `code`, [text](url)
function _escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function _md(text) {
  return _escapeHtml(text)
    .replace(/`([^`]+?)`/g, '<code>$1</code>')
    .replace(/[*][*](.+?)[*][*]/g, '<strong>$1</strong>')
    .replace(/\\[(.+?)\\]\\((.+?)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

function addMsg(text, role) {
  const d = document.createElement('div');
  d.className = 'msg msg-' + role;
  d.innerHTML = _md(text);
  msgsEl.appendChild(d);
  if (window.gsap) gsap.from(d, {opacity:0, y:12, x:20, duration:.35, ease:'power2.out'});
  msgsEl.scrollTop = msgsEl.scrollHeight;
}

function _renderBotHtml(text, tool) {
  let html = '';
  if (tool) html += `<span class="tool-badge">🔧 ${tool}</span><br>`;
  html += _md(text);
  if (currentUser && currentUser.token) html = html.replace(/(href="\\/api\\/export\\/[^"]+)"/g, '$1?token=' + currentUser.token + '"');
  return html;
}

function addBotMsg(text, tool) {
  const d = document.createElement('div');
  d.className = 'msg msg-bot';
  d.innerHTML = _renderBotHtml(text, tool);
  msgsEl.appendChild(d);
  if (window.gsap) gsap.from(d, {opacity:0, y:12, x:-20, duration:.35, ease:'power2.out'});
  msgsEl.scrollTop = msgsEl.scrollHeight;
}

async function send(text) {
  inputEl.value = '';
  showConfirmBar(false);
  addMsg(text, 'user');
  const typing = document.createElement('div');
  typing.className = 'msg msg-bot';
  typing.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span>';
  msgsEl.appendChild(typing);
  msgsEl.scrollTop = msgsEl.scrollHeight;

  const botEl = document.createElement('div');
  botEl.className = 'msg msg-bot';
  let streamed = '';
  let toolName = null;
  let awaitingConfirm = false;

  try {
    const headers = {'Content-Type':'application/json'};
    if (currentUser && currentUser.token) headers['Authorization'] = 'Bearer ' + currentUser.token;

    const r = await fetch('/api/chat/stream', {method:'POST', headers, body:JSON.stringify({message: text})});
    if (r.status === 401) {
      typing.remove();
      addBotMsg('🔒 Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', null);
      logout();
      return;
    }
    if (!r.ok || !r.body) throw new Error('HTTP ' + r.status);

    typing.remove();
    msgsEl.appendChild(botEl);
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const parts = buffer.split('\\n\\n');
      buffer = parts.pop() || '';
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data:')) continue;
        let evt;
        try { evt = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
        if (evt.type === 'meta') { toolName = evt.tool; awaitingConfirm = !!evt.awaiting_confirm; }
        if (evt.type === 'token') {
          streamed += evt.content || '';
          botEl.innerHTML = _renderBotHtml(streamed, toolName);
          msgsEl.scrollTop = msgsEl.scrollHeight;
        }
        if (evt.type === 'error') {
          streamed = evt.content || 'Có lỗi xảy ra.';
          botEl.innerHTML = _renderBotHtml(streamed, null);
        }
      }
    }
    if (!streamed) botEl.innerHTML = _renderBotHtml('😅 Mình chưa nhận được phản hồi, bạn thử lại nhé.', null);
    if (window.gsap) gsap.from(botEl, {opacity:0, y:12, x:-20, duration:.35, ease:'power2.out'});
    showConfirmBar(awaitingConfirm);
    msgsEl.scrollTop = msgsEl.scrollHeight;
  } catch(e) {
    typing.remove();
    if (botEl.parentNode) botEl.remove();
    try {
      const headers = {'Content-Type':'application/json'};
      if (currentUser && currentUser.token) headers['Authorization'] = 'Bearer ' + currentUser.token;
      const r = await fetch('/api/chat', {method:'POST', headers, body:JSON.stringify({message: text})});
      if (r.status === 401) { addBotMsg('🔒 Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', null); logout(); return; }
      const data = await r.json();
      addBotMsg(data.response, data.tool);
      showConfirmBar(data.awaiting_confirm);
    } catch (e2) {
      addBotMsg('❌ Lỗi: ' + e.message, null);
    }
  }
}

function sendMsg() {
  const text = inputEl.value.trim();
  if (text) send(text);
}

// Đổ sẵn lệnh write vào ô nhập để người dùng sửa tên/người/deadline rồi gửi
function fill(text) {
  inputEl.value = text;
  inputEl.focus();
}

// Thanh xác nhận nhanh ok/hủy (hữu ích trên mobile) khi bot đang chờ xác nhận
function showConfirmBar(show) {
  const holder = document.getElementById('confirm-bar-holder');
  if (!holder) return;
  if (!show) { holder.innerHTML = ''; return; }
  holder.innerHTML =
    '<div class="confirm-bar">' +
    '<button class="confirm-ok" onclick="send(\\'ok\\')">✅ Xác nhận</button>' +
    '<button class="confirm-cancel" onclick="send(\\'hủy\\')">❌ Hủy</button>' +
    '</div>';
}

// Hiện nút Google OAuth khi server đã cấu hình (không lộ secret)
(async function initLogin() {
  try {
    const r = await fetch('/auth/google/status');
    if (r.ok && (await r.json()).configured) {
      document.getElementById('google-divider').style.display = 'block';
      document.getElementById('google-login-btn').style.display = 'flex';
    }
  } catch (e) { /* bỏ qua */ }

  const saved = _loadSession();
  if (saved) {
    _enterChatScreen(saved);
    showGreeting(saved);
  } else if (window.gsap) {
    gsap.from('.login-box', {opacity:0, y:20, scale:.96, duration:.5, ease:'back.out(1.5)'});
  }
})();
</script>
</body>
</html>"""
