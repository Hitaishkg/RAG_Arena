"""
Generate an interactive collapsible tree visualization of the LlamaIndex Tree Index.
Click nodes to expand/collapse. Starts collapsed at roots.

Usage:
    python scripts/visualize_tree.py
"""
import json
import os
import webbrowser

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "indexes", "tree_index")


def load_hierarchy():
    with open(os.path.join(INDEX_DIR, "index_store.json")) as f:
        store = json.load(f)
    with open(os.path.join(INDEX_DIR, "docstore.json")) as f:
        docstore = json.load(f)

    tree_data = json.loads(list(store["index_store/data"].values())[0]["__data__"])
    nodes = docstore["docstore/data"]
    children_map = tree_data["node_id_to_children_ids"]
    root_ids = list(tree_data["root_nodes"].values())

    def walk(nid):
        n = nodes.get(nid, {}).get("__data__", {})
        text = n.get("text", "")
        meta = n.get("metadata", {})
        ch_ids = children_map.get(nid, [])
        return {
            "id": nid,
            "name": text[:60].replace("\n", " ").strip(),
            "fullText": text[:500].replace("\n", " ").replace('"', "'").strip(),
            "doc": meta.get("doc_id", "summary"),
            "page": meta.get("page", ""),
            "isLeaf": len(ch_ids) == 0,
            "childCount": len(ch_ids),
            "children": [walk(c) for c in ch_ids],
        }

    roots = [walk(r) for r in root_ids]
    if len(roots) == 1:
        return roots[0]
    return {
        "id": "__root__",
        "name": "Tree Index",
        "fullText": "Virtual root — click to expand",
        "doc": "summary",
        "page": "",
        "isLeaf": False,
        "childCount": len(roots),
        "children": roots,
    }


def render_html(hierarchy, out_path):
    data_json = json.dumps(hierarchy)

    # Write HTML without Python f-strings for the JS block to avoid escaping bugs
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RAG Arena — Tree Index</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0f1117; color: #e0e0e0; overflow: hidden; }
#header { padding: 12px 20px; background: #1a1d2e; border-bottom: 1px solid #2a2d3e;
          display: flex; align-items: center; gap: 16px; }
#header h1 { font-size: 16px; font-weight: 700; color: #fff; }
.stat { font-size: 12px; color: #888; }
.stat b { color: #b07aa1; }
#hint { padding: 7px 20px; background: #13151f; border-bottom: 1px solid #2a2d3e;
        font-size: 11px; color: #555; display: flex; gap: 16px; align-items: center; }
kbd { background: #1e2130; border: 1px solid #333; border-radius: 3px;
      padding: 1px 5px; color: #aaa; font-size: 10px; }
#legend { margin-left: auto; display: flex; gap: 10px; }
.leg { display: flex; align-items: center; gap: 5px; font-size: 11px; color: #777; }
.leg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
#canvas { width: 100vw; height: calc(100vh - 78px); }
svg { width: 100%; height: 100%; }
.link { fill: none; stroke: #252840; stroke-width: 1.5px; }
.node { cursor: pointer; }
.node circle { transition: r 0.2s; }
.node:hover circle { filter: brightness(1.5); }
.node text { font-size: 11px; fill: #aaa; pointer-events: none;
             text-shadow: 0 0 4px #000, 0 0 4px #000; }
.badge { font-size: 9px; fill: #555; pointer-events: none; }
#tip { position: fixed; background: #1a1d2e; border: 1px solid #3a3d5e;
       border-radius: 10px; padding: 13px 15px; font-size: 12px; max-width: 360px;
       pointer-events: none; display: none;
       box-shadow: 0 8px 30px rgba(0,0,0,0.7); z-index: 100; line-height: 1.6; }
.tip-type { font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
            color: #555; margin-bottom: 3px; }
.tip-name { font-weight: 600; color: #fff; font-size: 13px; margin-bottom: 5px; }
.tip-meta { color: #777; font-size: 11px; margin-bottom: 8px;
            border-bottom: 1px solid #252840; padding-bottom: 7px; }
.tip-body { color: #bbb; font-size: 12px; }
</style>
</head>
<body>
<div id="header">
  <h1>RAG Arena &middot; LlamaIndex Tree</h1>
  <div class="stat">Visible: <b id="vcnt">—</b></div>
  <div class="stat">Total: <b id="tcnt">—</b></div>
  <div id="legend"></div>
</div>
<div id="hint">
  <kbd>Click</kbd> expand / collapse &nbsp;
  <kbd>Scroll</kbd> zoom &nbsp;
  <kbd>Drag</kbd> pan &nbsp;
  <kbd>Double-click bg</kbd> reset view
  <span style="margin-left:auto">Starts collapsed — drill into branches</span>
</div>
<div id="canvas"><svg id="svg"></svg></div>
<div id="tip"></div>
<script>
""")

    html_parts.append("const RAW = ")
    html_parts.append(data_json)
    html_parts.append(";\n")

    html_parts.append("""
const COLORS = {
  sebi_icdr_2018:       "#4e79a7",
  sebi_lodr_2015:       "#f28e2b",
  sebi_mutual_fund_reg: "#59a14f",
  sebi_pit_2015:        "#e15759",
  sebi_sast_2011:       "#76b7b2",
  summary:              "#b07aa1"
};
const LABELS = {
  sebi_icdr_2018: "ICDR 2018", sebi_lodr_2015: "LODR 2015",
  sebi_mutual_fund_reg: "MF Reg", sebi_pit_2015: "PIT 2015",
  sebi_sast_2011: "SAST 2011", summary: "Summary nodes"
};

// Legend
const legEl = document.getElementById('legend');
Object.entries(COLORS).forEach(([k,c]) => {
  legEl.innerHTML += `<div class="leg"><div class="leg-dot" style="background:${c}"></div>${LABELS[k]}</div>`;
});

// Count total nodes
function countNodes(d) {
  let n = 1;
  (d.children || []).forEach(c => n += countNodes(c));
  return n;
}
document.getElementById('tcnt').textContent = countNodes(RAW);

// Build d3 hierarchy and collapse everything except root
const root = d3.hierarchy(RAW, d => d.children);
root.descendants().slice(1).forEach(d => {
  d._children = d.children;
  d.children = null;
});

// SVG setup
const W = window.innerWidth;
const H = window.innerHeight - 78;
const svg = d3.select('#svg');
const g = svg.append('g');

// Zoom
const zoom = d3.zoom().scaleExtent([0.02, 8]).on('zoom', e => g.attr('transform', e.transform));
svg.call(zoom);
svg.on('dblclick.zoom', null);
svg.on('dblclick', () => fitView());

// Tree layout — horizontal, generous spacing
const tree = d3.tree().nodeSize([22, 260]);

let uid = 0;

function update(source) {
  tree(root);

  const nodes = root.descendants();
  const links = root.links();

  document.getElementById('vcnt').textContent = nodes.length;

  // ── Links ──────────────────────────────
  const link = g.selectAll('path.link')
    .data(links, d => d.target.data.id);

  link.join(
    enter => enter.append('path')
      .attr('class', 'link')
      .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x))
      .attr('opacity', 0)
      .call(s => s.transition().duration(250).attr('opacity', 1)),
    update => update.transition().duration(250)
      .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x)),
    exit => exit.transition().duration(200).attr('opacity', 0).remove()
  );

  // ── Nodes ──────────────────────────────
  const node = g.selectAll('g.node')
    .data(nodes, d => d.data.id);

  const nodeEnter = node.enter().append('g')
    .attr('class', 'node')
    .attr('transform', d => {
      const sx = source ? source.y : d.y;
      const sy = source ? source.x : d.x;
      return 'translate(' + sx + ',' + sy + ')';
    })
    .attr('opacity', 0);

  nodeEnter.append('circle');
  nodeEnter.append('text').attr('class', 'label');
  nodeEnter.append('text').attr('class', 'badge');

  const nodeAll = node.merge(nodeEnter);

  nodeAll.transition().duration(250)
    .attr('transform', d => 'translate(' + d.y + ',' + d.x + ')')
    .attr('opacity', 1);

  nodeAll.select('circle')
    .attr('r', d => d.depth === 0 ? 10 : d.data.isLeaf ? 4 : 7)
    .attr('fill', d => COLORS[d.data.doc] || '#888')
    .attr('fill-opacity', d => d.data.isLeaf ? 0.55 : 1)
    .attr('stroke', d => d._children ? '#ffffff55' : 'rgba(0,0,0,0.3)')
    .attr('stroke-width', d => d._children ? 2 : 1)
    .attr('stroke-dasharray', d => d._children ? '3,2' : 'none');

  nodeAll.select('.label')
    .attr('dy', '0.32em')
    .attr('x', d => (d.children || d._children) ? -13 : 11)
    .attr('text-anchor', d => (d.children || d._children) ? 'end' : 'start')
    .text(d => {
      if (d.data.isLeaf) return d.data.doc !== 'summary' ? 'p.' + d.data.page : '';
      return d.data.name.slice(0, 34);
    });

  nodeAll.select('.badge')
    .attr('dy', '1.5em')
    .attr('x', d => (d.children || d._children) ? -13 : 11)
    .attr('text-anchor', d => (d.children || d._children) ? 'end' : 'start')
    .text(d => d._children ? '▶ ' + d.data.childCount + ' children' : '');

  node.exit().transition().duration(200)
    .attr('opacity', 0)
    .remove();

  // ── Click handler ───────────────────────
  nodeAll.on('click', (event, d) => {
    event.stopPropagation();
    if (d._children) {
      d.children = d._children;
      d._children = null;
    } else if (d.children) {
      d._children = d.children;
      d.children = null;
    }
    update(d);
  });

  // ── Tooltip ─────────────────────────────
  const tip = document.getElementById('tip');
  nodeAll
    .on('mousemove', (event, d) => {
      const nd = d.data;
      const type = nd.isLeaf ? 'Leaf Chunk' : (d.depth === 0 ? 'Root Summary' : 'Summary Node');
      const meta = nd.isLeaf
        ? nd.doc + (nd.page ? ' · page ' + nd.page : '')
        : nd.childCount + ' children · depth ' + d.depth + (d._children ? ' · click to expand' : ' · click to collapse');
      tip.innerHTML =
        '<div class="tip-type">' + type + '</div>' +
        '<div class="tip-name">' + nd.name + '</div>' +
        '<div class="tip-meta">' + meta + '</div>' +
        '<div class="tip-body">' + nd.fullText + '</div>';
      tip.style.display = 'block';
      tip.style.left = Math.min(event.clientX + 16, W - 380) + 'px';
      tip.style.top = Math.min(event.clientY - 10, H - 220) + 'px';
    })
    .on('mouseleave', () => { tip.style.display = 'none'; });
}

function fitView() {
  const bounds = g.node().getBBox();
  if (!bounds.width || !bounds.height) return;
  const scale = Math.min(W / (bounds.width + 80), H / (bounds.height + 40)) * 0.9;
  const tx = W / 2 - scale * (bounds.x + bounds.width / 2);
  const ty = H / 2 - scale * (bounds.y + bounds.height / 2);
  svg.transition().duration(500)
    .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}

// Initial render
update(null);

// Start: root on left-center with comfortable zoom
svg.call(zoom.transform, d3.zoomIdentity.translate(W * 0.1, H / 2).scale(1));
</script>
</body>
</html>""")

    with open(out_path, "w") as f:
        f.write("".join(html_parts))


if __name__ == "__main__":
    print("Loading tree index...")
    hierarchy = load_hierarchy()

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tree_viz.html"))
    print("Rendering...")
    render_html(hierarchy, out_path)
    print(f"Saved: {out_path}")
    webbrowser.open(f"file://{out_path}")
