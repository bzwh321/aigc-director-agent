#!/usr/bin/env python3
"""人审合同 HTML 生成器 — 只用标准库，不联网，不调模型，不写额外文件。

用法：
    python contract_html.py <state.json> [--project <project.json>] --out <output.html>
退出码：0 成功；2 参数错误或文件不存在。
"""
import argparse
import glob as _glob
import hashlib
import html
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 导入 director_control（与本脚本同目录）
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    from director_control import consistency, contract_state
except ImportError:
    def consistency(state, project):          # noqa: E302
        return []
    def contract_state(state, scope, target_id):  # noqa: E302
        return None

# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def safe(val, default='待定'):
    """None / 空字符串 / 空容器 → default。"""
    if val is None:
        return default
    if isinstance(val, str) and not val.strip():
        return default
    if isinstance(val, (dict, list)) and len(val) == 0:
        return default
    return val


def esc(val, default='待定'):
    return html.escape(str(safe(val, default)))


def fmt_sec(v):
    if v is None:
        return '待定'
    try:
        return f'{float(v):.1f}s'
    except (TypeError, ValueError):
        return str(v)


def sha8(s):
    return str(s)[:8] if s else '待定'


def thumb_html(path, out_dir, label='', role=''):
    """返回缩略图 <img> 或灰底占位框；绝不抛异常。"""
    if not path:
        return _placeholder(label or '（无路径）')
    try:
        base = os.path.abspath(out_dir)
        if os.path.isabs(path):
            abs_p = Path(os.path.abspath(path))
        else:
            abs_p = Path(os.path.join(base, path))
        if abs_p.is_file():
            try:
                rel = os.path.relpath(str(abs_p), base).replace('\\', '/')
                src = rel
            except ValueError:
                # 不同驱动器，改用 file:// 绝对路径
                src = abs_p.as_uri()
            alt = html.escape(str(label or role or abs_p.name))
            badge = (f'<span class="frame-badge">{html.escape(str(role))}</span>'
                     if role else '')
            return (f'<span class="thumb-wrap" onclick="dshZoom(this)" '
                    f'title="点击看大图">{badge}'
                    f'<img src="{html.escape(src)}" alt="{alt}" loading="lazy"></span>')
    except Exception:
        pass
    return _placeholder(os.path.basename(str(path)) if path else (label or '（无路径）'))



# 点资产卡看大图：面板 /view 会把 img src 改写成 /asset?project=…，所以放大时
# 直接取缩略图已经解析好的 currentSrc，不另拼路径。
_ZOOM_BLOCK = """<style>
#dsh-zoom{position:fixed;inset:0;background:rgba(8,10,14,.94);display:none;z-index:9999;
  align-items:center;justify-content:center;cursor:zoom-out;padding:2vh 2vw;}
#dsh-zoom img{max-width:96vw;max-height:96vh;object-fit:contain;border-radius:6px;
  box-shadow:0 12px 48px rgba(0,0,0,.6);background:#fff;}
.asset-card{cursor:zoom-in;}
span.thumb-wrap{cursor:zoom-in;display:inline-block;}
.film-path{display:flex;gap:8px;align-items:center;margin-top:8px;font-size:12px;flex-wrap:wrap}
.film-path-label{color:var(--muted)}
.film-path code{background:rgba(127,127,127,.12);padding:2px 6px;border-radius:4px;
  word-break:break-all;font-size:12px}
.film-copy{font:inherit;font-size:11px;padding:2px 8px;border-radius:4px;cursor:pointer;
  border:1px solid rgba(127,127,127,.35);background:transparent;color:inherit}
.film-copy:hover{border-color:#4d6bfe;color:#4d6bfe}
.film-wrap{max-width:720px}
.film-wrap video{width:100%;max-height:78vh;background:#000;border-radius:6px}
.film-segs{margin-top:6px;font-size:12px;color:var(--muted)}
.film-note{margin-top:4px;font-size:11px;color:var(--muted)}
</style>
<div id="dsh-zoom" onclick="this.style.display='none'"><img alt=""></div>
<script>
function dshZoom(card){
  var img = card.querySelector('img');
  if(!img) return;
  var box = document.getElementById('dsh-zoom');
  var big = box.querySelector('img');
  big.src = img.currentSrc || img.src;
  box.style.display = 'flex';
}
</script>"""

_EDIT_BLOCK = r"""<style>
#dsh-toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:10000;
  background:#1b2130;color:#e7e9ee;border:1px solid #2a2f3a;border-radius:6px;
  padding:8px 14px;font-size:12px;display:none;box-shadow:0 6px 24px rgba(0,0,0,.45)}
#dsh-toast.bad{border-color:#a3504b;color:#ffb3ae}
.ed-box{display:block;width:100%;min-height:64px;font:inherit;font-size:12px;line-height:1.5;
  padding:6px 8px;border-radius:5px;border:1px solid #4d6bfe;background:#11151d;color:#e7e9ee;
  resize:vertical}
</style>
<div id="dsh-toast"></div>
<script>
(function(){
  var TOAST = document.getElementById('dsh-toast');
  function toast(msg, bad){
    if(!TOAST) return;
    TOAST.textContent = msg;
    TOAST.className = bad ? 'bad' : '';
    TOAST.style.display = 'block';
    clearTimeout(TOAST._t);
    TOAST._t = setTimeout(function(){ TOAST.style.display = 'none'; }, bad ? 4200 : 2200);
  }
  function projectPath(){
    var m = location.pathname.match(/^\/aigc-design\/view\/(.+)$/);
    try { return m ? decodeURIComponent(m[1]) : ''; } catch(e){ return ''; }
  }
  function openBox(cell){
    if(cell.querySelector('.ed-box')) return;
    var field = cell.dataset.field, shot = cell.dataset.shot;
    if(!field || !shot) return;
    var raw = cell.dataset.raw !== undefined ? cell.dataset.raw : (cell.textContent || '');
    var ta = document.createElement('textarea');
    ta.className = 'ed-box';
    ta.value = raw;
    if(field === 'duration_seconds'){ ta.rows = 1; }
    cell.textContent = '';
    cell.appendChild(ta);
    ta.focus();
    ta.select();
    var done = false;
    function close(restore){
      if(done) return; done = true;
      if(restore){ ta.value = raw; }
      cell.textContent = ta.value;
      cell.dataset.raw = ta.value;
    }
    function save(){
      var value = ta.value;
      fetch('/api/aigc-design/shot-edit', {
        method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({project: projectPath(), shot_id: shot, field: field, value: value})
      }).then(function(r){
        if(!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function(d){
        if(!d || d.ok !== true) throw new Error((d && d.error) || '保存失败');
        done = true;
        cell.textContent = value;
        cell.dataset.raw = value;
        toast('已保存 ' + String(shot) + ' · 本组 ' + d.group_sum + '/' + d.group_target +
              's · 全长 ' + d.total + 's');
      }).catch(function(err){
        close(true);
        toast(String(err && err.message).indexOf('401') >= 0
          ? 'Host 还没加载编辑路由，重启一次 DSH 后可用'
          : '保存失败：' + (err && err.message ? err.message : '未知错误'), true);
      });
    }
    ta.addEventListener('keydown', function(ev){
      if(ev.key === 'Enter' && (ev.ctrlKey || field === 'duration_seconds')){
        ev.preventDefault(); save();
      } else if(ev.key === 'Escape'){
        ev.preventDefault(); close(true);
      }
    });
    ta.addEventListener('blur', function(){ if(!done) save(); });
  }
  document.addEventListener('dblclick', function(ev){
    var cell = ev.target && ev.target.closest ? ev.target.closest('[data-shot][data-field]') : null;
    if(cell){ ev.preventDefault(); openBox(cell); }
  });
})();
</script>"""

_FILM_JS = """<script>
function dshCopyFilmPath(btn){
  var el = document.getElementById('film-path-text');
  if(!el) return;
  var t = el.textContent || '';
  var done = function(){
    var old = btn.textContent;
    btn.textContent = '已复制';
    setTimeout(function(){ btn.textContent = old; }, 1400);
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(t).then(done, function(){});
    return;
  }
  var ta = document.createElement('textarea');
  ta.value = t;
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch(e) {}
  document.body.removeChild(ta);
  done();
}
</script>"""


def _write_doc(out_path, doc):
    """写合同文件，并把看大图的样式/脚本插到 </body> 前。"""
    doc = doc.replace('</body>', _ZOOM_BLOCK + _EDIT_BLOCK + _FILM_JS + '</body>', 1)
    out_path.write_text(doc, encoding='utf-8')


def _placeholder(name):
    return (f'<span class="thumb-placeholder">'
            f'<span class="placeholder-name">{html.escape(str(name)[:40])}</span></span>')


def decision_badge(decision):
    d = str(decision or 'pending').lower()
    cls = {'approved': 'badge-ok', 'rejected': 'badge-ng', 'pending': 'badge-pending'}.get(d, 'badge-pending')
    label = {'approved': '通过', 'rejected': '拒绝', 'pending': '待审'}.get(d, esc(decision))
    return f'<span class="badge {cls}">{label}</span>'


# ---------------------------------------------------------------------------
# 数据提取
# ---------------------------------------------------------------------------

def build_groups_index(state):
    """group_id → group_dict；来源：units[].groups[] + state.groups[]。"""
    groups = {}
    for unit in (state.get('units') or []):
        for g in (unit.get('groups') or []):
            gid = g.get('group_id')
            if gid:
                groups[gid] = {**g, '_unit': unit}
    for g in (state.get('groups') or []):
        gid = g.get('group_id')
        if gid and gid not in groups:
            groups[gid] = g
    return groups


def shots_by_group(shots, groups):
    """[(gid_or_None, group_dict_or_None, [shots])]，保持原顺序。"""
    seen, group_shots, ungrouped = [], {}, []
    for s in shots:
        gid = s.get('group_id')
        if gid:
            if gid not in group_shots:
                group_shots[gid] = []
                seen.append(gid)
            group_shots[gid].append(s)
        else:
            ungrouped.append(s)
    result = [(gid, groups.get(gid), group_shots[gid]) for gid in seen]
    if ungrouped:
        result.append((None, None, ungrouped))
    return result


def latest_contract(state, scope, target_id):
    try:
        return contract_state(state, scope, target_id)
    except Exception:
        return None


def get_assets(state, project):
    """project 与 state 里的资产合并，按资产号去重（state 覆盖 project）。"""
    merged: dict = {}
    for src in ((project or {}).get('assets') or [], state.get('assets') or []):
        for a in src:
            key = str(a.get('asset_id') or a.get('id') or a.get('name') or id(a))
            merged[key] = a
    return list(merged.values())


# ---------------------------------------------------------------------------
# CSS（深色主题 + 打印）
# ---------------------------------------------------------------------------

_CSS = """
:root{
  --bg:#10171b;--surface:#182026;--surface2:#1e2b32;
  --border:#2a3b44;--text:#e6eeed;--muted:#8aa4ad;--accent:#3b9eba;
  --ok:#4ade80;--ng:#f87171;--pending:#fbbf24;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:"Microsoft YaHei","PingFang SC",sans-serif;font-size:14px;line-height:1.6;}
main{max-width:1400px;margin:0 auto;padding:16px;}
a{color:var(--accent);text-decoration:none;}
a:hover{text-decoration:underline;}
h2{font-size:1.2rem;font-weight:600;margin:28px 0 12px;border-bottom:1px solid var(--border);padding-bottom:6px;}
h3{font-size:.95rem;font-weight:600;margin:14px 0 6px;color:var(--muted);}
code{font-size:11px;background:var(--surface2);padding:1px 4px;border-radius:3px;}
pre{white-space:pre-wrap;font-size:11px;background:var(--surface2);padding:8px;border-radius:4px;margin-top:4px;}

/* top nav */
nav.top-nav{position:sticky;top:0;z-index:100;background:var(--surface);border-bottom:1px solid var(--border);
  padding:8px 16px;display:flex;gap:16px;flex-wrap:wrap;}
nav.top-nav a{color:var(--muted);font-size:13px;}
nav.top-nav a:hover{color:var(--text);}

/* page header */
.pg-header{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start;
  padding:14px;background:var(--surface);border-radius:8px;margin-bottom:12px;}
.pg-title{font-size:1.35rem;font-weight:700;flex:1;min-width:180px;}
.pg-meta{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--muted);}

/* badges */
.badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;}
.badge-ok{background:rgba(74,222,128,.16);color:var(--ok);border:1px solid var(--ok);}
.badge-ng{background:rgba(248,113,113,.16);color:var(--ng);border:1px solid var(--ng);}
.badge-pending{background:rgba(251,191,36,.16);color:var(--pending);border:1px solid var(--pending);}

/* warning */
.warn-bar{background:rgba(248,113,113,.1);border-left:4px solid var(--ng);
  padding:10px 14px;margin-bottom:14px;border-radius:0 6px 6px 0;}
.warn-bar ul{padding-left:18px;margin-top:6px;}
.warn-bar li{font-size:12px;color:var(--ng);}

/* asset cards */
.asset-grid{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px;}
.asset-card{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
  padding:10px;width:190px;display:flex;flex-direction:column;gap:5px;}
.asset-card img{width:100%;height:110px;object-fit:cover;border-radius:4px;}
.asset-id{font-size:10px;color:var(--muted);font-family:monospace;}
.asset-name{font-weight:600;font-size:12px;}
/* 资产卡里的缩略图：整张显示不裁切，点卡片进详情合同 */
.asset-card .thumb-wrap{display:block;margin:0;}
.asset-card .thumb-wrap img{width:100%;height:132px;object-fit:contain;background:#fff;border:1px solid var(--border);}
a.asset-card{color:inherit;text-decoration:none;}
a.asset-card:hover{border-color:var(--accent,#4d6bfe);}
.asset-more{font-size:10px;color:var(--accent,#4d6bfe);}

/* thumbnails */
.thumb-wrap{position:relative;display:inline-block;vertical-align:top;margin-right:4px;}
.thumb-wrap img{width:80px;height:60px;object-fit:cover;border-radius:3px;border:1px solid var(--border);}
.thumb-placeholder{display:inline-flex;align-items:center;justify-content:center;
  width:80px;height:60px;background:var(--surface2);border:1px solid var(--border);border-radius:3px;}
.placeholder-name{font-size:9px;color:var(--muted);word-break:break-all;text-align:center;padding:3px;}
.frame-badge{position:absolute;top:2px;left:2px;background:rgba(0,0,0,.75);color:#fff;
  font-size:9px;padding:1px 4px;border-radius:2px;z-index:1;pointer-events:none;}

/* tables */
.scroll{overflow-x:auto;}
table.wide{min-width:3122px;table-layout:fixed;}
table.wide td,table.wide th{word-break:normal;overflow-wrap:anywhere;line-height:1.6;}
table.wide td:nth-child(1),table.wide td:nth-child(2),table.wide td:nth-child(3),
table.wide td:nth-child(10),table.wide td:nth-child(14){text-align:center;}
table.wide td:nth-child(4),table.wide td:nth-child(7),table.wide td:nth-child(13){font-size:12.5px;}
table.wide td:nth-child(11) img{width:120px;height:90px;object-fit:contain;background:#fff;}
table.wide pre.ed{max-height:260px;overflow:auto;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th{background:var(--surface2);color:var(--muted);padding:6px 8px;text-align:left;
  white-space:nowrap;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10;}
td{padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top;}
tr:hover td{background:rgba(255,255,255,.025);}
td:first-child,th:first-child{position:sticky;left:0;background:var(--surface);z-index:5;}
tr:hover td:first-child{background:var(--surface2);}
.group-row td{background:var(--surface2);color:var(--muted);font-weight:600;
  font-size:11px;border-top:2px solid var(--border);}
.unit-row td{background:rgba(59,158,186,.1);color:var(--text);font-weight:700;
  font-size:12.5px;border-top:3px solid var(--accent);}
tr.rejected td{color:var(--ng);border-left:3px solid var(--ng);background:rgba(248,113,113,.05);}

/* thinking cards */
.think-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:12px;margin-bottom:10px;}
.think-card h4{font-size:12px;font-weight:600;margin-bottom:8px;}
.tf{font-size:12px;margin-bottom:5px;}
.tf .lbl{color:var(--muted);margin-right:6px;}
.assum-list,.opt-list{list-style:none;padding:0;margin:3px 0;}
.assum-list li,.opt-list li{background:var(--surface2);border-radius:4px;
  padding:3px 8px;margin-bottom:3px;font-size:11px;}
.ev-user_confirmed{color:var(--ok);}
.ev-measured{color:var(--accent);}
.ev-inferred{color:var(--pending);}
.opt-chosen{border-left:3px solid var(--ok);}
.opt-other{border-left:3px solid var(--border);opacity:.75;}
details summary{cursor:pointer;color:var(--muted);font-size:12px;user-select:none;}
details[open] summary{color:var(--text);}

/* versions */
.ver-list{list-style:none;padding:0;}
.ver-list li{padding:4px 0;border-bottom:1px solid var(--border);font-size:12px;}

/* footer */
footer{font-size:11px;color:var(--muted);margin-top:28px;padding-top:10px;border-top:1px solid var(--border);}
footer p{margin-bottom:3px;}

@media print{
  :root{--bg:#fff;--surface:#f4f4f4;--surface2:#eaeaea;--border:#ccc;--text:#111;--muted:#555;}
  nav.top-nav{display:none;}
  details,details[open]{display:block;}
  details summary{display:none;}
  .badge{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
}
"""

# ---------------------------------------------------------------------------
# Section: 页头
# ---------------------------------------------------------------------------

def _sec_top(state, project, issues, gen_time, state_path):
    schema = esc(state.get('schema_version'))
    pid = esc(state.get('project_id') or
              (project.get('project_id') if project else None))
    film_c = latest_contract(state, 'film', 'film')
    film_status = film_c.get('decision', 'pending') if film_c else 'pending'

    warn = ''
    if issues:
        li_items = '\n'.join(
            f'<li><code>{esc(i.get("code","?"))}</code> → '
            f'<b>{esc(i.get("target","?"))}</b>：{esc(i.get("detail",""))}</li>'
            for i in issues
        )
        warn = (f'<div class="warn-bar"><b>⚠ 一致性问题 ({len(issues)} 项)</b>'
                f'<ul>{li_items}</ul></div>')

    return f"""
<section id="top">
<div class="pg-header">
  <div class="pg-title">导演制作合同</div>
  <div class="pg-meta">
    <span>项目：{pid}</span>
    <span>Schema：{schema}</span>
    <span>生成时间：{esc(gen_time)}</span>
    <span>整体状态：{decision_badge(film_status)}</span>
    <span>来源：{esc(Path(state_path).name)}</span>
  </div>
</div>
{warn}
</section>
"""

def video_html(path, out_dir, label='', role=''):
    """返回 <video> 播放器；文件不在就返回空串，绝不抛异常。"""
    if not path:
        return ''
    try:
        base = os.path.abspath(out_dir)
        abs_p = Path(path) if os.path.isabs(path) else Path(os.path.join(base, path))
        if not abs_p.is_file():
            return ''
        rel = os.path.relpath(str(abs_p), base).replace(os.sep, '/')
        cap = html.escape(' · '.join(x for x in (str(role or ''), str(label or '')) if x))
        return ('<div class="vid-wrap"><video src="%s" controls preload="metadata" '
                'playsinline></video>%s</div>'
                % (html.escape(rel), ('<div class="vid-cap">%s</div>' % cap) if cap else ''))
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Section: 成片（拼接）
# ---------------------------------------------------------------------------

def _sec_film(state, out_dir):
    """成片段：把 state['artifacts']['film_cut'] 的拼接片放在最上面，可直接播放。"""
    cut = ((state.get('artifacts') or {}).get('film_cut') or {})
    path = cut.get('path') or ''
    player = video_html(path, out_dir, label=cut.get('label') or '',
                        role=('%.2f 秒' % float(cut.get('seconds') or 0))
                        if cut.get('seconds') else '')
    if not player:
        return ''
    segs = cut.get('segments') or []
    note = safe(cut.get('note'))
    seg_line = ('　'.join(str(x) for x in segs)) if segs else ''
    extra = []
    try:
        base_dir = os.path.abspath(out_dir)
        abs_film = (Path(path) if os.path.isabs(path)
                    else Path(os.path.join(base_dir, path)))
        abs_str = str(abs_film.resolve())
    except Exception:
        abs_str = ''
    if abs_str:
        extra.append(
            '<div class="film-path"><span class="film-path-label">本地文件</span>'
            '<code id="film-path-text">%s</code>'
            '<button type="button" class="film-copy" onclick="dshCopyFilmPath(this)">复制路径</button>'
            '</div>' % esc(abs_str))
    if seg_line:
        extra.append('<div class="film-segs">镜头顺序：%s</div>' % esc(seg_line))
    if note:
        extra.append('<div class="film-note">%s</div>' % esc(note))
    return ('<section id="film"><h2>成片</h2>'
            '<div class="film-wrap">%s%s</div></section>'
            % (player, ''.join(extra)))


# ---------------------------------------------------------------------------
# Section: 全局资产
# ---------------------------------------------------------------------------

def _sec_assets(state, project, out_dir):
    assets = get_assets(state, project)
    if not assets:
        return ('<section id="assets"><h2>全局资产</h2>'
                '<p style="color:var(--muted)">（无资产记录）</p></section>')

    _KIND_CN = {'character': '人物', 'scene': '场景', 'prop': '道具',
                'background': '故事背景'}
    by_kind: dict = {}
    for a in assets:
        kind = _KIND_CN.get(str(a.get('kind') or ''), '其他资产')
        by_kind.setdefault(kind, []).append(a)

    parts = ['<section id="assets"><h2>全局资产</h2>']
    for kind, items in by_kind.items():
        parts.append(f'<h3>{esc(kind)}</h3><div class="asset-grid">')
        for a in items:
            aid = esc(a.get('id') or a.get('asset_id'))
            name = esc(safe(a.get('name') or a.get('id') or a.get('asset_id')))
            summary = esc(safe(a.get('summary') or a.get('description')))
            sids = a.get('shot_ids') or []
            shots_str = esc(', '.join(str(s) for s in sids) if sids else '待定')
            images = a.get('images') or []
            sha = sha8((images[0].get('sha256') if images else '')
                       or a.get('sha256') or a.get('fingerprint'))
            img_p = (images[0].get('path') if images else '') or a.get('path') or a.get('thumbnail') or ''
            th = thumb_html(img_p, out_dir, label=str(a.get('name', '')))
            # 资产可以指向自己的详情合同（人物 → 人物设计合同）；有就整张卡片可点。
            detail = str(a.get('contract') or '')
            more = (f'<a class="asset-more" href="{esc(detail)}" title="打开详情合同"'
                    ' onclick="event.stopPropagation()">看完整信息 →</a>') if detail else ''
            parts.append(f"""<div class="asset-card" onclick="dshZoom(this)" title="点击看大图">
  {th}
  <div class="asset-id">{aid}</div>
  <div class="asset-name">{name}</div>
  <div class="tf" style="font-size:11px">{summary}</div>
  <div class="asset-id">镜头：{shots_str}</div>
  <div class="asset-id">sha256：{esc(sha)}</div>
  {more}
</div>""")
        parts.append('</div>')
    parts.append('</section>')
    return '\n'.join(parts)

# ---------------------------------------------------------------------------
# Section: 设计表
# ---------------------------------------------------------------------------

_DESIGN_COLS = 14

# 列宽（px）：按每列内容的典型文字量分配，避免长句被压成一根竖条
_DESIGN_WIDTHS = [70, 70, 58, 400, 220, 300, 420, 150, 230, 80, 150, 380, 520, 74]
_DESIGN_COLS_HTML = '<colgroup>' + ''.join(
    f'<col style="width:{w}px">' for w in _DESIGN_WIDTHS) + '</colgroup>'


def _sec_design(state, groups_idx, out_dir):
    shots = state.get('shots') or []
    grouped = shots_by_group(shots, groups_idx)

    rows = ["""<tr>
  <th>组号</th><th>镜头号</th><th>时长</th><th>镜头描述</th>
  <th>观众应理解</th><th>景别·视角·运镜</th><th>主体动作</th>
  <th>台词/配音</th><th>音效</th><th>状态</th>
  <th>静态帧</th><th>视频提示词</th><th>完整提示词</th><th>入上下文</th>
</tr>"""]

    _last_uid_design = None
    for gid, group, gshots in grouped:
        if gid:
            unit = (group or {}).get('_unit')
            if unit:
                uid = unit.get('unit_id') or unit.get('id')
                if uid and uid != _last_uid_design:
                    _last_uid_design = uid
                    uname = esc(safe(unit.get('name') or unit.get('title')))
                    ugoal = unit.get('goal') or unit.get('objective')
                    ugroups = unit.get('groups') or []
                    goal_part = f' · 目标：{esc(str(ugoal))}' if ugoal else ''
                    rows.append(
                        f'<tr class="unit-row"><td colspan="{_DESIGN_COLS}">'
                        f'单元 {esc(str(uid))} · {uname}{goal_part} · {len(ugroups)} 组'
                        f'</td></tr>'
                    )
            g_target = fmt_sec((group or {}).get('target_seconds'))
            g_c = latest_contract(state, 'group', gid)
            g_st = g_c.get('decision', 'pending') if g_c else 'pending'
            rows.append(
                f'<tr class="group-row"><td colspan="{_DESIGN_COLS}">'
                f'组 {esc(gid)} · 目标时长 {esc(g_target)} · '
                f'{len(gshots)} 镜 · {decision_badge(g_st)}</td></tr>'
            )

        for s in gshots:
            sid = esc(s.get('shot_id'))
            dur = esc(fmt_sec(s.get('duration_seconds')))
            desc = esc(safe(s.get('summary')))
            takeaway = esc(safe(s.get('audience_takeaway')))
            cam_parts = [str(safe(s.get(k), '')) for k in ('framing', 'angle', 'camera_motion')]
            cam = esc(' · '.join(p for p in cam_parts if p and p != '待定') or '待定')
            action = esc(safe(s.get('subject_action')))

            dlg_html = []
            for line in (s.get('dialogue') or []):
                spk = esc(safe(line.get('speaker')))
                txt = esc(safe(line.get('text')))
                src = str(line.get('source', ''))
                cls = f'ev-{src}' if src in ('measured', 'estimated', 'inferred') else ''
                secs_val = line.get('seconds', '')
                suf = f' ({secs_val}s)' if secs_val else ''
                dlg_html.append(f'<span class="{cls}">{spk}：{txt}{esc(suf)}</span>')
            dlg_cell = '<br>'.join(dlg_html) or '—'

            sfx_html = []
            for fx in (s.get('sound_effects') or []):
                cue = str(safe(fx.get('cue')))
                at = fx.get('at_seconds')
                sfx_html.append(html.escape(cue + (f' @{at}s' if at is not None else '')))
            sfx_cell = '<br>'.join(sfx_html) or '—'

            s_c = latest_contract(state, 'shot', s.get('shot_id', ''))
            s_st = s_c.get('decision', 'pending') if s_c else 'pending'

            _sid = str(s.get('shot_id') or '')

            def _ed(field, raw, shown, cls='ed'):
                return (f'<td class="{cls}" data-shot="{html.escape(_sid)}" '
                        f'data-field="{field}" data-raw="{html.escape(str(raw), quote=True)}">'
                        f'{shown}</td>')

            frames = s.get('static_frames') or []
            thumbs_html = ' '.join(
                thumb_html(f.get('path', ''), out_dir,
                           label=str(f.get('revision', '')),
                           role=str(f.get('role', '')))
                for f in frames
            ) if frames else '—'
            vids = s.get('video_files') or []
            vids_html = ' '.join(
                video_html(v.get('path', ''), out_dir,
                           label=str(v.get('revision', '')), role=str(v.get('role', '')))
                for v in vids
            )
            vprompt = esc(safe(s.get('video_prompt')))
            fp = safe(s.get('final_prompt'), None)
            fp_html = (f'<details><summary>展开完整提示词</summary>'
                       f'<pre class="ed" data-shot="{html.escape(_sid)}" data-field="final_prompt" '
                       f'data-raw="{html.escape(str(fp), quote=True)}">{html.escape(str(fp))}</pre>'
                       f'</details>') if fp else '—'
            ctx_ok = bool(s_c and s_c.get('context_eligible')) if s_c else False

            rows.append(f"""<tr>
  <td>{esc(str(gid or '—'))}</td><td>{sid}</td>{_ed('duration_seconds', s.get('duration_seconds'), dur)}
  {_ed('summary', safe(s.get('summary')), desc)}<td>{takeaway}</td><td>{cam}</td>{_ed('subject_action', safe(s.get('subject_action')), action)}
  <td>{dlg_cell}</td><td>{sfx_cell}</td><td>{decision_badge(s_st)}</td>
  <td>{thumbs_html}{vids_html}</td><td>{vprompt}</td><td>{fp_html}</td>
  <td>{'✓' if ctx_ok else '✗'}</td>
</tr>""")

    return (f'<section id="design"><h2>设计与生成表</h2>'
            f'<div class="scroll"><table class="wide">{_DESIGN_COLS_HTML}{"".join(rows)}</table></div></section>')

# ---------------------------------------------------------------------------
# Section: 生成表
# ---------------------------------------------------------------------------

_GEN_COLS = 10


# ---------------------------------------------------------------------------
# Section: 思考记录
# ---------------------------------------------------------------------------

def _sec_thinking(state):
    records = state.get('thinking') or []
    if not records:
        return ('<section id="thinking"><h2>思考记录</h2>'
                '<p style="color:var(--muted)">（无思考记录）</p></section>')

    _SCOPE_CN = {'shot': '单镜级', 'group': '组级', 'unit': '单元级', 'film': '整片级'}
    by_scope: dict = {}
    for t in records:
        sc = _SCOPE_CN.get(str(t.get('scope') or ''), str(t.get('scope') or '未分类'))
        by_scope.setdefault(sc, []).append(t)

    parts = ['<section id="thinking"><h2>思考记录</h2>']
    for scope, items in by_scope.items():
        parts.append(f'<h3>{esc(scope)}</h3>')
        for t in items:
            tid = esc(t.get('thinking_id', ''))
            at = esc(safe(t.get('at')))
            target = esc(safe(t.get('target_id')))
            question = esc(safe(t.get('question')))
            understood = esc(safe(t.get('understood')))
            decision_txt = esc(safe(t.get('decision')))
            revisit = safe(t.get('revisit_when'), None)

            assum_html = ''
            for a in (t.get('assumptions') or []):
                ev = str(a.get('evidence', 'inferred'))
                ev_cls = 'ev-' + ev.replace(' ', '_')
                claim = esc(safe(a.get('claim')))
                note = safe(a.get('note'), None)
                note_part = f' — {esc(str(note))}' if note else ''
                assum_html += (f'<li><span class="{ev_cls}">[{esc(ev)}]</span>'
                               f' {claim}{note_part}</li>')
            if assum_html:
                assum_html = f'<ul class="assum-list">{assum_html}</ul>'

            opts_html = ''
            for o in (t.get('options') or []):
                chosen = bool(o.get('chosen'))
                cls = 'opt-chosen' if chosen else 'opt-other'
                opt_text = esc(safe(o.get('option')))
                cost = safe(o.get('cost'), None)
                risk = safe(o.get('risk'), None)
                why = safe(o.get('why'), None)
                mark = ' <b style="color:var(--ok)">✓ 已选</b>' if chosen else ''
                meta = '  '.join(
                    f'{lbl}：{esc(str(val))}'
                    for lbl, val in [('成本', cost), ('风险', risk), ('理由', why)]
                    if val
                )
                opts_html += (f'<li class="{cls}"><span>{opt_text}</span>{mark}'
                              f'{"  "+meta if meta else ""}</li>')
            if opts_html:
                opts_html = f'<ul class="opt-list">{opts_html}</ul>'

            parts.append(f"""<div class="think-card">
  <h4>{tid} / {esc(scope)} / {target}
    <span style="font-weight:400;color:var(--muted);font-size:11px;margin-left:8px">{at}</span>
  </h4>
  <div class="tf"><span class="lbl">问题：</span>{question}</div>
  <div class="tf"><span class="lbl">理解：</span>{understood}</div>
  {f'<div class="tf"><span class="lbl">假设：</span>{assum_html}</div>' if assum_html else ''}
  {f'<div class="tf"><span class="lbl">方案：</span>{opts_html}</div>' if opts_html else ''}
  <div class="tf"><span class="lbl">决定：</span>{decision_txt}</div>
  {f'<div class="tf"><span class="lbl">重访条件：</span>{esc(str(revisit))}</div>' if revisit else ''}
</div>""")

    parts.append('</section>')
    return '\n'.join(parts)

# ---------------------------------------------------------------------------
# Section: 审核记录
# ---------------------------------------------------------------------------

def _sec_reviews(state):
    contracts = state.get('contracts') or []
    if not contracts:
        return ('<section id="reviews"><h2>审核记录</h2>'
                '<p style="color:var(--muted)">（无合同记录）</p></section>')

    rows = ["""<tr>
  <th>合同ID</th><th>层</th><th>目标</th><th>版本</th>
  <th>结论</th><th>审核人</th><th>时间</th><th>入上下文</th><th>理由</th>
</tr>"""]

    for c in contracts:
        d = str(c.get('decision') or 'pending').lower()
        row_cls = ' class="rejected"' if d == 'rejected' else ''
        ctx = '✗' if d == 'rejected' else ('✓' if c.get('context_eligible') else '✗')
        rows.append(f"""<tr{row_cls}>
  <td><code>{esc(safe(c.get('contract_id')))}</code></td>
  <td>{esc(safe(c.get('scope')))}</td>
  <td>{esc(safe(c.get('target_id')))}</td>
  <td>{esc(str(safe(c.get('revision'))))}</td>
  <td>{decision_badge(d)}</td>
  <td>{esc(safe(c.get('reviewer')))}</td>
  <td>{esc(safe(c.get('decided_at')))}</td>
  <td>{ctx}</td>
  <td>{esc(safe(c.get('reason')))}</td>
</tr>""")

    return (f'<section id="reviews"><h2>审核记录</h2>'
            f'<div class="scroll"><table>{"".join(rows)}</table></div></section>')

# ---------------------------------------------------------------------------
# Section: 版本历史
# ---------------------------------------------------------------------------

def _sec_versions(out_path):
    out = Path(out_path)
    pattern = str(out.parent / f'{out.stem}-v*.html')
    found = sorted(_glob.glob(pattern))
    if not found:
        return ('<section id="versions"><h2>版本历史</h2>'
                '<p style="color:var(--muted)">暂无历史版本</p></section>')
    items = '\n'.join(
        f'<li><a href="{html.escape(Path(p).name)}">{html.escape(Path(p).name)}</a></li>'
        for p in found
    )
    return f'<section id="versions"><h2>版本历史</h2><ul class="ver-list">{items}</ul></section>'

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def _footer(state_path, state, cmd):
    try:
        fp = hashlib.sha256(Path(state_path).read_bytes()).hexdigest()[:16]
    except Exception:
        fp = '（读取失败）'
    schema = esc(state.get('schema_version'))
    return f"""<footer id="footer-sec">
  <p>生成命令：<code>{esc(cmd)}</code></p>
  <p>State 指纹（sha256前16）：<code>{esc(fp)}</code></p>
  <p>Schema：{schema}</p>
</footer>"""

# ---------------------------------------------------------------------------
# 单镜合同（--shot / --shots）
# ---------------------------------------------------------------------------

def _shot_title(state, project):
    """与 main() 中 title 的逻辑一致：state.project_id → project.project_id → 默认。"""
    return html.escape(str(
        state.get('project_id') or
        (project.get('project_id') if project else None) or
        '导演制作合同'
    ))


def render_shot(state, project, shot, groups_idx, out_dir, out_path,
                state_path, gen_time):
    """渲染单镜制作合同页面，返回完整 HTML 字符串。"""
    sid = str(shot.get('shot_id') or '')
    gid = str(shot.get('group_id') or '')
    group = groups_idx.get(gid) or {}
    unit = group.get('_unit') or {}
    unit_name = unit.get('name') or unit.get('title') or ''
    if not unit_name:
        uid = shot.get('unit_id')
        for u in (state.get('units') or []):
            if uid and (u.get('unit_id') or u.get('id')) == uid:
                unit_name = u.get('name') or u.get('title') or ''
                break

    s_c = latest_contract(state, 'shot', sid)
    s_st = s_c.get('decision', 'pending') if s_c else 'pending'

    # 镜头设计
    cam = esc(' · '.join(
        p for p in (str(safe(shot.get(k), ''))
                    for k in ('framing', 'angle', 'camera_motion'))
        if p and p != '待定'
    ) or '待定')

    dlg_items = []
    for line in (shot.get('dialogue') or []):
        src = str(line.get('source', ''))
        cls = f'ev-{src}' if src in ('measured', 'estimated', 'inferred') else ''
        secs = line.get('seconds', '')
        suf = f' ({secs}s)' if secs else ''
        item = (f'{esc(safe(line.get("speaker")))}：'
                f'{esc(safe(line.get("text")))}{esc(suf)}')
        dlg_items.append(f'<li class="{cls}">{item}</li>')
    dlg_html = (f'<ul class="assum-list">{"".join(dlg_items)}</ul>'
                if dlg_items else '—')

    sfx_items = []
    for fx in (shot.get('sound_effects') or []):
        at = fx.get('at_seconds')
        txt = str(safe(fx.get('cue'))) + (f' @{at}s' if at is not None else '')
        sfx_items.append(f'<li>{html.escape(txt)}</li>')
    sfx_html = (f'<ul class="assum-list">{"".join(sfx_items)}</ul>'
                if sfx_items else '—')

    # 静态帧
    frames = shot.get('static_frames') or []
    frames_html = (' '.join(
        thumb_html(f.get('path', ''), out_dir,
                   label=str(f.get('revision', '')),
                   role=str(f.get('role', '')))
        for f in frames
    ) if frames else '<span style="color:var(--muted)">（无静态帧记录）</span>')
    vids = shot.get('video_files') or []
    videos_section = ''
    if vids:
        inner = ' '.join(video_html(v.get('path', ''), out_dir,
                                    label=str(v.get('revision', '')),
                                    role=str(v.get('role', ''))) for v in vids)
        videos_section = ('<section id="videos"><h2>视频产出</h2>'
                          '<div style="display:flex;flex-wrap:wrap;gap:8px">'
                          + inner + '</div></section>')

    # 视频生成
    fp = safe(shot.get('final_prompt'), None)
    fp_html = ('<details><summary>展开完整提示词</summary>'
               f'<pre>{html.escape(str(fp))}</pre></details>') if fp else '—'

    # 本镜合同记录
    recs = [c for c in (state.get('contracts') or [])
            if c.get('scope') == 'shot' and str(c.get('target_id')) == sid]
    if recs:
        rows = ['<tr><th>版本</th><th>结论</th><th>审核人</th><th>时间</th>'
                '<th>理由</th><th>指纹</th><th>入上下文</th></tr>']
        for c in recs:
            rows.append(f"""<tr>
  <td>{esc(str(safe(c.get('revision'))))}</td>
  <td>{decision_badge(c.get('decision'))}</td>
  <td>{esc(safe(c.get('reviewer')))}</td>
  <td>{esc(safe(c.get('decided_at')))}</td>
  <td>{esc(safe(c.get('reason')))}</td>
  <td><code>{esc(sha8(c.get('fingerprint')))}</code></td>
  <td>{'✓' if c.get('context_eligible') else '✗'}</td>
</tr>""")
        recs_html = f'<div class="scroll"><table>{"".join(rows)}</table></div>'
    else:
        recs_html = '<p style="color:var(--muted)">（暂无单镜合同记录）</p>'

    # 相关一致性告警（本镜号或所属组号）
    try:
        issues = consistency(state, project) or []
    except Exception as e:
        issues = [{'code': 'consistency-error', 'target': '—', 'detail': str(e)}]
    related = [i for i in issues
               if str(i.get('target', '')) == sid
               or (gid and str(i.get('target', '')) == gid)]
    if related:
        rows = ['<tr><th>代码</th><th>详情</th></tr>']
        for i in related:
            rows.append(f'<tr><td><code>{esc(i.get("code"), "")}</code></td>'
                        f'<td>{esc(i.get("detail"), "")}</td></tr>')
        issues_html = f'<div class="scroll"><table>{"".join(rows)}</table></div>'
    else:
        issues_html = ('<p style="color:var(--muted)">'
                       '（本镜与所属组无一致性告警）</p>')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_shot_title(state, project)} — 镜头 {esc(sid)}</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<header class="pg-header" id="top">
  <div class="pg-title">导演制作合同 · 单镜</div>
  <div class="pg-meta">
    <span>项目：{_shot_title(state, project)}</span>
    <span>镜号：{esc(sid)}</span>
    <span>单元：{esc(unit_name)}</span>
    <span>组号：{esc(gid)}</span>
    <span>时长：{esc(fmt_sec(shot.get('duration_seconds')))}</span>
    <span>合同状态：{decision_badge(s_st)}</span>
    <span>生成时间：{esc(gen_time)}</span>
  </div>
</header>
<h2>镜号 {esc(sid)} · 单镜合同</h2>

<section id="design">
<h2>镜头设计</h2>
<div class="think-card">
  <div class="tf"><span class="lbl">镜头描述：</span>{esc(safe(shot.get('summary')))}</div>
  <div class="tf"><span class="lbl">观众应理解：</span>{esc(safe(shot.get('audience_takeaway')))}</div>
  <div class="tf"><span class="lbl">景别·视角·运镜：</span>{cam}</div>
  <div class="tf"><span class="lbl">主体动作：</span>{esc(safe(shot.get('subject_action')))}</div>
  <div class="tf"><span class="lbl">台词/配音：</span>{dlg_html}</div>
  <div class="tf"><span class="lbl">音效：</span>{sfx_html}</div>
</div>
</section>

<section id="frames">
<h2>静态帧</h2>
<div style="display:flex;flex-wrap:wrap;gap:8px">{frames_html}</div>
</section>
{videos_section}

<section id="generate">
<h2>视频生成</h2>
<div class="think-card">
  <div class="tf"><span class="lbl">视频节点：</span>{esc(safe(shot.get('video_node')))}</div>
  <div class="tf"><span class="lbl">生成模式：</span>{esc(safe(shot.get('video_mode')))}</div>
  <div class="tf"><span class="lbl">视频提示词：</span>{esc(safe(shot.get('video_prompt')))}</div>
  <div class="tf"><span class="lbl">完整提示词：</span>{fp_html}</div>
</div>
</section>

<section id="shot-contracts">
<h2>本镜合同记录</h2>
{recs_html}
</section>

<section id="shot-issues">
<h2>相关一致性告警</h2>
{issues_html}
</section>

<p style="margin:24px 0"><a href="导演制作合同.html">返回主合同</a></p>

<footer id="footer-sec">
  <p>来源：<code>{esc(Path(state_path).name)}</code></p>
  <p>本页：<code>{esc(Path(out_path).name)}</code></p>
  <p>生成时间：{esc(gen_time)}</p>
</footer>
</main>
</body>
</html>"""


def _shot_mode(args, state, project):
    """--shot / --shots 分支：逐镜渲染，返回退出码。"""
    if args.shot is not None and args.shots:
        print('错误：--shot 与 --shots 不能同时使用', file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    if not out_dir.is_dir():
        print(f'错误：输出目录不存在：{out_dir}', file=sys.stderr)
        return 2

    shots = state.get('shots') or []
    groups_idx = build_groups_index(state)
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    state_path = Path(args.state)

    if args.shot is not None:
        shot = next((s for s in shots
                     if str(s.get('shot_id')) == str(args.shot)), None)
        if shot is None:
            print(f'错误：state 中找不到镜头：{args.shot}', file=sys.stderr)
            return 2
        targets = [shot]
    else:
        targets = shots

    for shot in targets:
        sid = str(shot.get('shot_id') or '')
        # 被拒的最新合同在文件名里带 -rejected：面板按名字隐藏，人不会误看到失败版。
        decision = str((latest_contract(state, 'shot', sid) or {}).get('decision') or '').lower()
        suffix = '-rejected' if decision == 'rejected' else ''
        out_path = out_dir / f'导演制作合同-镜头{sid}{suffix}.html'
        stale = out_dir / f'导演制作合同-镜头{sid}{"" if suffix else "-rejected"}.html'
        if stale.is_file() and stale != out_path:
            try:
                stale.unlink()
            except OSError:
                pass
        doc = render_shot(state, project, shot, groups_idx, str(out_dir),
                          out_path, state_path, gen_time)
        _write_doc(out_path, doc)
        print(str(out_path.resolve()))
        if args.shot is not None:
            print(f'镜头 {sid}')

    if args.shots:
        print(f'共 {len(targets)} 个镜头合同')
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog='contract_html.py',
        description='人审合同 HTML 生成器',
    )
    parser.add_argument('state', help='state.json 路径')
    parser.add_argument('--project', default=None, help='project.json 路径（可选）')
    parser.add_argument('--out', required=True, help='输出 HTML 路径（必填）')
    parser.add_argument('--shot', default=None, metavar='SHOT_ID',
                        help='只渲染该镜头，输出到 --out 目录')
    parser.add_argument('--shots', action='store_true',
                        help='渲染全部镜头，每镜一个文件，输出到 --out 目录')

    if len(sys.argv) < 2:
        parser.print_usage(sys.stderr)
        sys.exit(2)

    args = parser.parse_args()
    out_path = Path(args.out)

    if not out_path.parent.exists():
        print(f'错误：输出目录不存在：{out_path.parent}', file=sys.stderr)
        sys.exit(2)

    state_path = Path(args.state)
    if not state_path.exists():
        print(f'错误：state 文件不存在：{state_path}', file=sys.stderr)
        sys.exit(2)

    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f'错误：解析 state.json 失败：{e}', file=sys.stderr)
        sys.exit(2)

    project = None
    if args.project:
        p_path = Path(args.project)
        if not p_path.exists():
            print(f'错误：project 文件不存在：{p_path}', file=sys.stderr)
            sys.exit(2)
        try:
            project = json.loads(p_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'错误：解析 project.json 失败：{e}', file=sys.stderr)
            sys.exit(2)

    out_dir = str(out_path.parent.resolve())
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cmd = ' '.join(sys.argv)

    if args.shot is not None or args.shots:
        sys.exit(_shot_mode(args, state, project))

    try:
        issues = consistency(state, project)
    except Exception as e:
        issues = [{'code': 'consistency-error', 'target': '—', 'detail': str(e)}]

    shots = state.get('shots') or []
    groups_idx = build_groups_index(state)
    title = html.escape(str(
        state.get('project_id') or
        (project.get('project_id') if project else None) or
        '导演制作合同'
    ))

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — 制作合同</title>
<style>{_CSS}</style>
</head>
<body>
<nav class="top-nav">
  <a href="#top">页头</a>
  <a href="#film">成片</a>
  <a href="#assets">资产</a>
  <a href="#design">设计与生成表</a>
  <a href="#thinking">思考</a>
  <a href="#reviews">审核</a>
  <a href="#versions">历史</a>
  <a href="#footer-sec">页脚</a>
</nav>
<main>
{_sec_top(state, project, issues, gen_time, str(state_path))}
{_sec_film(state, out_dir)}
{_sec_assets(state, project, out_dir)}
{_sec_design(state, groups_idx, out_dir)}
{_sec_thinking(state)}
{_sec_reviews(state)}
{_sec_versions(str(out_path))}
{_footer(str(state_path), state, cmd)}
</main>
</body>
</html>"""

    _write_doc(out_path, doc)
    print(str(out_path.resolve()))
    print(f'{len(shots)} 个镜头')
    sys.exit(0)


if __name__ == '__main__':
    main()
