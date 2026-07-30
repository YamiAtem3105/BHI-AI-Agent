import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models.models import User, Conversation, Message, ToolCall, AuditLog
from app.services.messaging_links import list_links, list_pending

router = APIRouter(prefix="/admin")


# --- JWT Auth ---

def create_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(hours=24)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
        return payload["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# --- Login ---

@router.post("/login")
async def login(request: Request):
    body = await request.json()
    if body.get("username") == settings.admin_username and body.get("password") == settings.admin_password:
        return {"token": create_token(body["username"])}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# --- API Endpoints ---

@router.get("/api/users")
async def list_users(admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [{"id": u.id, "display_name": u.display_name, "email": u.email,
             "role": u.role, "department": u.department, "created_at": str(u.created_at)} for u in users]


@router.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request, admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    body = await request.json()
    for field in ["display_name", "email", "role", "department"]:
        if field in body:
            setattr(user, field, body[field])
    db.commit()
    return {"ok": True}


@router.delete("/api/users/{user_id}")
async def delete_user(user_id: int, admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    return {"ok": True}


@router.get("/api/conversations")
async def list_conversations(admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    convs = db.query(Conversation).order_by(Conversation.last_message_at.desc()).limit(50).all()
    results = []
    for c in convs:
        user = db.query(User).filter(User.id == c.user_id).first()
        msg_count = db.query(Message).filter(Message.conversation_id == c.id).count()
        results.append({
            "id": c.id, "user": user.display_name if user else "?",
            "messages": msg_count, "last_message_at": str(c.last_message_at), "is_active": c.is_active
        })
    return results


@router.get("/api/conversations/{conv_id}/messages")
async def get_messages(conv_id: int, admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content, "created_at": str(m.created_at)} for m in msgs]


@router.get("/api/audit-logs")
async def list_audit_logs(admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    results = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        results.append({
            "id": log.id, "user": user.display_name if user else "?",
            "action": log.action, "target_task_id": log.target_task_id,
            "payload": log.payload, "timestamp": str(log.timestamp)
        })
    return results


@router.get("/api/stats")
async def stats(admin: str = Depends(verify_token), db: Session = Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "conversations": db.query(Conversation).count(),
        "messages": db.query(Message).count(),
        "tool_calls": db.query(ToolCall).count(),
        "audit_logs": db.query(AuditLog).count(),
    }


@router.get("/api/messaging-links")
async def admin_messaging_links(admin: str = Depends(verify_token)):
    return {"links": list_links()}


@router.get("/api/messaging-pending")
async def admin_messaging_pending(admin: str = Depends(verify_token)):
    return {"pending": list_pending()}


# --- Dashboard HTML ---

@router.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BHI Agent - Admin</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#f0f2f5;color:#333}
.login{display:flex;justify-content:center;align-items:center;height:100vh}
.login form{background:#fff;padding:2rem;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);width:320px}
.login h2{margin-bottom:1rem;color:#4285f4}
.login input{width:100%;padding:.5rem;margin:.4rem 0;border:1px solid #ddd;border-radius:4px}
.login button{width:100%;padding:.6rem;background:#4285f4;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:.5rem}
.app{display:none}
header{background:#4285f4;color:#fff;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}
header h1{font-size:1.2rem}
.tabs{display:flex;gap:0;background:#fff;border-bottom:1px solid #ddd}
.tab{padding:.8rem 1.5rem;cursor:pointer;border-bottom:2px solid transparent}
.tab.active{border-bottom-color:#4285f4;color:#4285f4;font-weight:600}
.content{padding:1.5rem}
.card{background:#fff;border-radius:8px;padding:1rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin-bottom:1.5rem}
.stat{text-align:center;padding:1rem}.stat .num{font-size:2rem;font-weight:700;color:#4285f4}
table{width:100%;border-collapse:collapse}
th,td{padding:.6rem .8rem;text-align:left;border-bottom:1px solid #eee;font-size:.9rem}
th{background:#f8f9fa;font-weight:600}
.badge{padding:.2rem .5rem;border-radius:3px;font-size:.75rem;font-weight:600}
.badge-admin{background:#e8f5e9;color:#2e7d32}
.badge-super_admin{background:#fce4ec;color:#880e4f}
.badge-manager{background:#fff3e0;color:#e65100}
.badge-member{background:#e3f2fd;color:#1565c0}
#logout{background:none;border:1px solid #fff;color:#fff;padding:.4rem .8rem;border-radius:4px;cursor:pointer}
.msg{margin:.3rem 0;padding:.4rem .6rem;border-radius:4px;font-size:.85rem}
.msg-user{background:#e3f2fd}.msg-assistant{background:#f1f8e9}
.card{opacity:1}
</style>
</head>
<body>
<div class="login" id="loginBox">
<form onsubmit="doLogin(event)">
<h2>🤖 BHI Agent Admin</h2>
<input id="username" placeholder="Username" value="admin">
<input id="password" type="password" placeholder="Password">
<button type="submit">Đăng nhập</button>
<p id="loginErr" style="color:red;margin-top:.5rem;font-size:.85rem"></p>
</form>
</div>
<div class="app" id="app">
<header><h1>🤖 BHI AI Agent - Admin Dashboard</h1><button id="logout" onclick="logout()">Logout</button></header>
<div class="tabs">
<div class="tab active" onclick="showTab('users')">👥 Users</div>
<div class="tab" onclick="showTab('messaging')">📱 Hiện trường</div>
<div class="tab" onclick="showTab('conversations')">💬 Conversations</div>
<div class="tab" onclick="showTab('audit')">📋 Audit Logs</div>
</div>
<div class="content" id="content"></div>
</div>
<script>
let token='';
const API='/admin/api';
function gsapOk(){return typeof gsap!=='undefined';}
function gsapReduce(){return window.matchMedia('(prefers-reduced-motion: reduce)').matches;}
function animateAdminContent(){
  if(!gsapOk()||gsapReduce())return;
  gsap.from('#content .card, #content .stat',{opacity:0,y:14,stagger:.05,duration:.38,ease:'power2.out',clearProps:'opacity'});
  gsap.from('#content table tr',{opacity:0,x:-10,stagger:.02,duration:.3,ease:'power2.out',clearProps:'opacity'});
}

async function doLogin(e){
  e.preventDefault();
  const r=await fetch('/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({username:document.getElementById('username').value,password:document.getElementById('password').value})});
  if(!r.ok){document.getElementById('loginErr').textContent='Sai tài khoản';return}
  const d=await r.json();token=d.token;
  document.getElementById('loginBox').style.display='none';
  document.getElementById('app').style.display='block';
  showTab('users');
}

function logout(){token='';document.getElementById('loginBox').style.display='flex';document.getElementById('app').style.display='none'}

async function api(path){
  const r=await fetch(API+path,{headers:{'Authorization':'Bearer '+token}});
  if(r.status===401){logout();return null}
  return r.json();
}

function showTab(name){
  const tabs=['users','messaging','conversations','audit'];
  document.querySelectorAll('.tab').forEach((t,i)=>{
    t.classList.toggle('active',tabs[i]===name);
    if(gsapOk()&&!gsapReduce()&&tabs[i]===name)gsap.fromTo(t,{scale:1.03},{scale:1,duration:.25,ease:'back.out(1.5)'});
  });
  if(name==='users')loadUsers();
  else if(name==='messaging')loadMessaging();
  else if(name==='conversations')loadConversations();
  else loadAudit();
}

async function loadUsers(){
  const[users,stats]=await Promise.all([api('/users'),api('/stats')]);
  if(!users)return;
  let h=`<div class="stats">
    <div class="stat card"><div class="num">${stats.users}</div>Users</div>
    <div class="stat card"><div class="num">${stats.conversations}</div>Conversations</div>
    <div class="stat card"><div class="num">${stats.messages}</div>Messages</div>
    <div class="stat card"><div class="num">${stats.tool_calls}</div>Tool Calls</div>
  </div><div class="card"><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Department</th></tr>`;
  users.forEach(u=>{
    const badge=`badge-${u.role}`;
    h+=`<tr><td>${u.id}</td><td>${u.display_name}</td><td>${u.email}</td><td><span class="badge ${badge}">${u.role}</span></td><td>${u.department||''}</td></tr>`;
  });
  h+='</table></div>';
  document.getElementById('content').innerHTML=h;
  animateAdminContent();
}

async function loadMessaging(){
  const[status,links,pending]=await Promise.all([
    fetch('/api/messaging/status').then(r=>r.json()),
    api('/messaging-links'),
    api('/messaging-pending'),
  ]);
  if(!links)return;
  let h=`<div class="card"><h3>Kênh Zalo / Telegram</h3>
    <p>Telegram: ${status.telegram&&status.telegram.enabled?'✅':'❌'} · Zalo: ${status.zalo&&status.zalo.enabled?'✅':'❌'}</p>
    <p style="font-size:.85rem;color:#666">Quản lý liên kết chi tiết tại <a href="/dashboard" target="_blank">Dashboard → Hiện trường</a> (đăng nhập email admin).</p></div>`;
  h+=`<div class="card"><h3>Liên kết nhân sự (${(links.links||links).length||0})</h3><table><tr><th>Tên</th><th>Email</th><th>Telegram</th><th>Zalo</th></tr>`;
  const rows=links.links||links||[];
  rows.forEach(l=>{h+=`<tr><td>${l.name||''}</td><td>${l.email}</td><td>${l.telegram_chat_id||'—'}</td><td>${l.zalo_user_id||'—'}</td></tr>`;});
  h+='</table></div>';
  const pend=(pending&&pending.pending)||[];
  if(pend.length){
    h+=`<div class="card"><h3>Chờ liên kết (${pend.length})</h3><ul>`;
    pend.forEach(p=>{h+=`<li>${p.platform}: ${p.platform_id} ${p.display_name||''}</li>`;});
    h+='</ul></div>';
  }
  document.getElementById('content').innerHTML=h;
  animateAdminContent();
}

async function loadConversations(){
  const convs=await api('/conversations');if(!convs)return;
  let h='<div class="card"><table><tr><th>ID</th><th>User</th><th>Messages</th><th>Last Activity</th><th></th></tr>';
  convs.forEach(c=>{
    h+=`<tr><td>${c.id}</td><td>${c.user}</td><td>${c.messages}</td><td>${c.last_message_at}</td><td><a href="#" onclick="viewConv(${c.id})">View</a></td></tr>`;
  });
  h+='</table></div><div id="convDetail"></div>';
  document.getElementById('content').innerHTML=h;
  animateAdminContent();
}

async function viewConv(id){
  const msgs=await api(`/conversations/${id}/messages`);if(!msgs)return;
  let h='<div class="card"><h3>Conversation #'+id+'</h3>';
  msgs.forEach(m=>{h+=`<div class="msg msg-${m.role}"><b>${m.role}:</b> ${m.content}</div>`});
  h+='</div>';
  document.getElementById('convDetail').innerHTML=h;
  animateAdminContent();
}

async function loadAudit(){
  const logs=await api('/audit-logs');if(!logs)return;
  let h='<div class="card"><table><tr><th>Time</th><th>User</th><th>Action</th><th>Task</th><th>Payload</th></tr>';
  logs.forEach(l=>{
    h+=`<tr><td>${l.timestamp}</td><td>${l.user}</td><td>${l.action}</td><td>${l.target_task_id||''}</td><td><code>${JSON.stringify(l.payload||{})}</code></td></tr>`;
  });
  h+='</table></div>';
  document.getElementById('content').innerHTML=h;
  animateAdminContent();
}
</script>
</body>
</html>"""
