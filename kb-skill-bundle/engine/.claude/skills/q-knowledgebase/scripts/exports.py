"""Bounded local exports and a dependency-free offline graph browser."""
from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from core import QError, now, safe_path
from engine import graph_edges, present_node, traverse

VIEWER = r'''<!doctype html>
<html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'">
<title>Q-KnowledgeBase · Offline graph</title>
<style>body{font:15px system-ui;background:#101923;color:#e6eef5;margin:30px}input,select{padding:10px;background:#1e3040;color:inherit;border:1px solid #60788d;border-radius:5px}a{color:#92d3ff}button{background:#21445f;color:white;border:1px solid #779cb8;padding:8px;cursor:pointer}main{display:grid;grid-template-columns:1fr 2fr;gap:24px}li{margin:8px 0}small{color:#adc2d3}.badge{padding:2px 8px;background:#294735}article{border-bottom:1px solid #405361;padding:12px}h1{font-size:26px}.inferred{background:#594821}#nodes{max-height:65vh;overflow:auto}@media(max-width:700px){main{display:block}}</style>
<h1>Q-KnowledgeBase</h1><p>Local snapshot · bounded subsystem view · no network, telemetry or external libraries.</p>
<p id="summary"></p><input id="query" aria-label="Search nodes" placeholder="Tìm node / đường dẫn">
<select id="type" aria-label="Node type"><option value="">Tất cả loại node</option></select>
<main><section><h2>Nodes</h2><div id="nodes"></div></section><section><h2 id="title">Chọn node để xem quan hệ</h2><div id="detail"></div><div id="edges"></div></section></main>
<script>
const data=__DATA__;
const byId=new Map(data.nodes.map(n=>[n.id,n]));
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
document.getElementById('summary').textContent=`${data.nodes.length} nodes · ${data.edges.length} edges · ${data.at}. Snapshot; chạy verify/update trước khi dùng làm bằng chứng.`;
for(const t of [...new Set(data.nodes.map(n=>n.type))].sort()){const o=el('option',t);o.value=t;document.getElementById('type').append(o)}
function select(n){
 document.getElementById('title').textContent=n.label;
 const d=document.getElementById('detail');d.replaceChildren(el('p',`${n.type} · ${n.path} · ${n.source_status} · ${n.status}`));
 if(n.source_status==='CURRENT' && n.source_uri){const a=el('a',`Mở source (dòng ${n.start}–${n.end})`);a.href=n.source_uri;a.rel='noreferrer';d.append(a)}
 const list=document.getElementById('edges');list.replaceChildren();
 for(const e of data.edges.filter(e=>e.source===n.id||e.target===n.id)){
  const a=el('article');const origin=el('span',`${e.origin} · ${e.state}`);origin.className='badge'+(e.origin==='INFERRED'?' inferred':'');a.append(origin);
  a.append(el('p',`${byId.get(e.source)?.label||e.source} → ${e.relation} → ${byId.get(e.target)?.label||e.target}`));
  a.append(el('small',`${e.path||''} · lines ${e.start??'?'}–${e.end??'?'}`));
  if(e.rationale)a.append(el('p',e.rationale));
  if(e.evidence)a.append(el('pre',typeof e.evidence==='string'?e.evidence:JSON.stringify(e.evidence,null,2)));
  const other=byId.get(e.source===n.id?e.target:e.source);if(other){const b=el('button','Đi tới '+other.label);b.onclick=()=>select(other);a.append(b)}list.append(a);
 }
}
function render(){const q=document.getElementById('query').value.toLowerCase(),t=document.getElementById('type').value;const root=document.getElementById('nodes');root.replaceChildren();for(const n of data.nodes.filter(n=>(!t||n.type===t)&&(n.label+' '+n.path).toLowerCase().includes(q))){const a=el('article');const b=el('button',n.label);b.onclick=()=>select(n);a.append(el('small',n.path+' · '+n.type+' · '),b);root.append(a)}}
document.getElementById('query').oninput=render;document.getElementById('type').onchange=render;render();
</script></html>'''


def export_graph(store, format_, node=None, top=100, depth=2):
    if node:
        data = traverse(store, node, depth, "both", top=top)
    else:
        nodes = store.rows("SELECT * FROM nodes ORDER BY path,type,label LIMIT ?", (top,))
        selected = {n["id"] for n in nodes}
        data = {"nodes": [present_node(store, n) for n in nodes],
                "edges": [e for e in graph_edges(store) if e["source"] in selected and e["target"] in selected][:top*3]}
    data.update({"directed": True, "at": now(), "bounded": True})
    for n in data["nodes"]:
        if n["source_status"] == "CURRENT":
            n["source_uri"] = safe_path(store.root, n["path"]).as_uri()
    out = safe_path(store.root, ".qkb/exports/graph." + {"json": "json", "graphml": "graphml", "mermaid": "mmd", "html": "html"}[format_])
    out.parent.mkdir(parents=True, exist_ok=True)
    if format_ == "json":
        content = json.dumps(data, ensure_ascii=False, indent=2)
    elif format_ == "html":
        embedded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        content = VIEWER.replace("__DATA__", embedded)
    elif format_ == "mermaid":
        lines = ["flowchart LR"]
        for n in data["nodes"]:
            # Encode metacharacters rather than allowing Mermaid directive injection.
            label = n["label"][:100]
            label = "".join(c if c.isalnum() or c in " ./_-" else "#"+str(ord(c))+";" for c in label)
            lines.append('  n'+n["id"]+'["'+label+'"]')
        for e in data["edges"]:
            lines.append("  n"+e["source"]+" -->|"+e["relation"]+" / "+e["origin"]+" / "+e["state"]+"| n"+e["target"])
        content = "\n".join(lines)+"\n"
    else:
        ns = "http://graphml.graphdrawing.org/xmlns"
        ET.register_namespace("", ns)
        root = ET.Element("{"+ns+"}graphml")
        for key, scope in (("label", "node"), ("type", "node"), ("relation", "edge"), ("origin", "edge"), ("state", "edge"), ("path", "all")):
            ET.SubElement(root, "{"+ns+"}key", {"id": key, "for": scope, "attr.name": key, "attr.type": "string"})
        graph = ET.SubElement(root, "{"+ns+"}graph", {"id": "QKB", "edgedefault": "directed"})
        for n in data["nodes"]:
            item = ET.SubElement(graph, "{"+ns+"}node", {"id": n["id"]})
            for key in ("label", "type", "path"):
                ET.SubElement(item, "{"+ns+"}data", {"key": key}).text = n[key]
        for e in data["edges"]:
            item = ET.SubElement(graph, "{"+ns+"}edge", {"id": e["id"], "source": e["source"], "target": e["target"]})
            for key in ("relation", "origin", "state", "path"):
                ET.SubElement(item, "{"+ns+"}data", {"key": key}).text = e.get(key, "")
        content = ET.tostring(root, encoding="unicode", xml_declaration=True)
    out.write_text(content, encoding="utf-8")
    return {"output": out.relative_to(store.root).as_posix(), "nodes": len(data["nodes"]), "edges": len(data["edges"]),
            "note": "Sensitive derived data; bounded snapshot, not a full-graph completeness claim"}
