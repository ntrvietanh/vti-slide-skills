#!/usr/bin/env node
/**
 * Custom Mermaid renderer that post-fits each node's rect to its actual
 * rendered text width, so labels never clip.
 *
 * Why: in Mermaid v11, flowchart nodes always wrap labels in
 * `<foreignObject>` regardless of the `htmlLabels:false` flag. The
 * foreignObject width is computed by Mermaid's own measurement pass —
 * which, under mmdc, runs before the Plus Jakarta Sans data URI face is
 * bound — so the rect ends up sized for Arial while the browser later
 * paints Plus Jakarta (wider), clipping the label.
 *
 * This script renders the diagram into a live DOM, waits for fonts to
 * load, then for each node:
 *   1. Measures the actual on-page content width of the foreignObject's
 *      inner HTML (`scrollWidth`).
 *   2. If that exceeds the existing rect.width, expands rect.width +
 *      foreignObject.width symmetrically around the node's centre.
 *
 * Output: self-contained SVG with the cssFile embedded in <defs><style>.
 */
import { readFileSync, writeFileSync, mkdtempSync, rmSync, existsSync, readdirSync } from "node:fs";
import { resolve, basename, join } from "node:path";
import { tmpdir, homedir } from "node:os";
import { pathToFileURL } from "node:url";

// Resolve puppeteer + mermaid + ELK from any npx cache that contains all
// three. Override with VTI_NPX_ROOT env var to pin a specific path.
//
// First-time setup (warms the cache so this script can find them):
//   npx --package=mermaid --package=puppeteer --package=@mermaid-js/layout-elk -c 'echo cached'
function findNpxRoot() {
  if (process.env.VTI_NPX_ROOT) return process.env.VTI_NPX_ROOT;
  const npxDir = join(homedir(), ".npm", "_npx");
  const hint = `Run:  npx --package=mermaid --package=puppeteer --package=@mermaid-js/layout-elk -c 'echo cached'`;
  if (!existsSync(npxDir)) {
    throw new Error(`No npx cache at ${npxDir}.\n${hint}`);
  }
  for (const dir of readdirSync(npxDir)) {
    const root = join(npxDir, dir, "node_modules");
    if (existsSync(join(root, "puppeteer")) &&
        existsSync(join(root, "mermaid")) &&
        existsSync(join(root, "@mermaid-js", "layout-elk"))) {
      return root;
    }
  }
  throw new Error(`No npx cache under ${npxDir} has puppeteer + mermaid + @mermaid-js/layout-elk.\n${hint}`);
}

const NPX_ROOT   = findNpxRoot();
const puppeteer  = (await import(`${NPX_ROOT}/puppeteer/lib/esm/puppeteer/puppeteer.js`)).default;
const mermaidMin = readFileSync(`${NPX_ROOT}/mermaid/dist/mermaid.min.js`, "utf8");
// Absolute file:// URL to ELK plugin entry — chunk imports resolve
// relative to this URL when the host page is also served via file://.
const ELK_URL = pathToFileURL(
  `${NPX_ROOT}/@mermaid-js/layout-elk/dist/mermaid-layout-elk.esm.min.mjs`
).href;

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: render_mermaid.mjs <input.mmd> <output.svg> [--css path]");
  process.exit(1);
}
const inputPath  = resolve(args[0]);
const outputPath = resolve(args[1]);
let cssPath = null;
for (let i = 2; i < args.length; i++) {
  if (args[i] === "--css" && args[i + 1]) { cssPath = resolve(args[i + 1]); i++; }
}

const source  = readFileSync(inputPath, "utf8");
const cssText = cssPath ? readFileSync(cssPath, "utf8") : "";

// Detect diagram type + flow direction. Only flowchart-family diagrams
// participate in the equalisation / strip-border passes; other types
// (sequence, gantt, etc.) ship with their own visual idioms and we just
// pass the SVG through with the font CSS embedded.
const isFlowchart = /^\s*flowchart\b/m.test(source) || /^\s*graph\b/m.test(source);
const isSequence  = /^\s*sequenceDiagram\b/m.test(source);
// Per-file opt-out: when the .mmd source pins itself to dagre via an
// init directive, the renderer skips ELK registration for that file.
// Dagre honours `direction LR` inside subgraphs strictly, while ELK's
// layered crossing-minimisation re-wraps subgraph children into a
// grid — that's the right call for some flows (s10's 7-source row).
const wantsDagre = /defaultRenderer\s*"\s*:\s*"\s*dagre"/i.test(source)
  || /"layout"\s*:\s*"\s*dagre"/i.test(source);
const dirMatch    = source.match(/flowchart\s+(LR|RL|TB|TD|BT)/i);
const flowDir     = dirMatch ? dirMatch[1].toUpperCase() : "LR";
const isHorizontal = flowDir === "LR" || flowDir === "RL";

const browser = await puppeteer.launch({
  args: ["--no-sandbox", "--font-render-hinting=medium", "--allow-file-access-from-files"],
  defaultViewport: { width: 2000, height: 1200, deviceScaleFactor: 2 },
});

// Stage page HTML on disk so we can load it via file:// — required because
// the ELK plugin's entry .mjs uses relative chunk imports that only
// resolve when the host page is also a file:// URL.
const tmpDir   = mkdtempSync(join(tmpdir(), "vti-mermaid-"));
const pagePath = join(tmpDir, "render.html");

try {
  const page = await browser.newPage();

  const html = `<!doctype html>
<html><head><meta charset="utf-8">
<style>${cssText}</style>
<style>html,body{margin:0;padding:0;background:transparent;}
  #host{font-family:'Plus Jakarta Sans','Arial',system-ui,sans-serif;}</style>
<script>${mermaidMin}</script>
<script type="module">
  // Load ELK layout plugin from its absolute file:// URL; the plugin's
  // internal "./chunks/…" imports then resolve relative to that file URL.
  try {
    const mod = await import(${JSON.stringify(ELK_URL)});
    const loaders = mod.default || mod.elkLayouts || mod;
    if (window.mermaid && typeof window.mermaid.registerLayoutLoaders === "function") {
      window.mermaid.registerLayoutLoaders(loaders);
      window.__elkReady = true;
    } else {
      window.__elkError = "mermaid.registerLayoutLoaders missing";
    }
  } catch (e) {
    window.__elkError = String(e);
  }
</script>
</head>
<body>
<div id="host"></div>
<pre id="src" style="display:none"></pre>
</body></html>`;

  writeFileSync(pagePath, html, "utf8");
  await page.goto(pathToFileURL(pagePath).href, { waitUntil: "domcontentloaded" });
  await page.evaluate((src) => { document.getElementById("src").textContent = src; }, source);

  // Wait for ELK module import to settle.
  await page.waitForFunction(() => window.__elkReady === true || window.__elkError, { timeout: 15000 });
  const elkStatus = await page.evaluate(() => ({ ready: window.__elkReady === true, error: window.__elkError || null }));
  if (!elkStatus.ready) {
    console.warn(`[warn] ELK not registered (${elkStatus.error || "unknown"}) — falling back to dagre`);
  }

  // Load font weights explicitly before any measurement happens.
  await page.evaluate(async () => {
    if (document.fonts) {
      await Promise.all([
        document.fonts.load("400 16px 'Plus Jakarta Sans'"),
        document.fonts.load("600 16px 'Plus Jakarta Sans'"),
        document.fonts.load("700 16px 'Plus Jakarta Sans'"),
        document.fonts.ready,
      ]);
    }
  });

  // Render the diagram into the DOM so we can re-measure on real elements.
  await page.evaluate(async (cfg) => {
    const src = document.getElementById("src").textContent;
    const init = {
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      fontFamily: "Plus Jakarta Sans, Arial, system-ui, sans-serif",
      flowchart: { padding: 16, nodeSpacing: 60, rankSpacing: 70, useMaxWidth: false },
    };
    if (cfg.useDagre) {
      init.flowchart.defaultRenderer = "dagre";
    } else {
      init.layout = "elk";
      init.flowchart.defaultRenderer = "elk";
      init.elk = {
        "elk.algorithm": "layered",
        "elk.direction": "DOWN",
        "elk.spacing.nodeNode": 50,
        "elk.layered.spacing.nodeNodeBetweenLayers": 70,
      };
    }
    mermaid.initialize(init);
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    const { svg, bindFunctions } = await mermaid.render("d", src);
    document.getElementById("host").innerHTML = svg;
    if (bindFunctions) bindFunctions(document.getElementById("host"));
  }, { useDagre: wantsDagre });

  // Post-fit pass: walk every flowchart node, compare rect width vs
  // actual rendered label width, equalise on-axis, strip stroke, apply
  // shadow filter. Skipped entirely for non-flowchart diagrams
  // (sequenceDiagram et al.) — those have a different DOM and ship with
  // their own polish via theme variables.
  const fitInfo = isFlowchart ? await page.evaluate(({ isHorizontal }) => {
    const svg = document.querySelector("#host svg");
    if (!svg) return { ok: false };

    const adjustments = [];
    const nodes = svg.querySelectorAll("g.node");
    nodes.forEach((node) => {
      const rect = node.querySelector(":scope > rect.label-container, :scope > rect, :scope > polygon");
      const fo   = node.querySelector("foreignObject");
      if (!fo) return;
      const innerDiv = fo.querySelector("div");
      if (!innerDiv) return;

      // Measure the natural rendered width: take the widest child element
      // in its current layout (no whiteSpace mutation, so wrapping nodes
      // stay wrapped).
      const childRects = Array.from(innerDiv.querySelectorAll("p,span,b"))
        .map((el) => el.getBoundingClientRect().width);
      const naturalW = Math.max(0, ...childRects);

      const currentFoW = parseFloat(fo.getAttribute("width") || "0");
      // Only widen if a child actually overflows the foreignObject. Add a
      // 4px guard for sub-pixel font rendering differences.
      if (naturalW <= currentFoW + 1) return;

      const needFoW = Math.ceil(naturalW + 4);
      const delta   = needFoW - currentFoW;

      fo.setAttribute("width", String(needFoW));
      const foX = parseFloat(fo.getAttribute("x") || "0");
      fo.setAttribute("x", String(foX - delta / 2));

      if (rect && rect.tagName.toLowerCase() === "rect") {
        const rw = parseFloat(rect.getAttribute("width"));
        const rx = parseFloat(rect.getAttribute("x"));
        rect.setAttribute("width", String(rw + delta));
        rect.setAttribute("x", String(rx - delta / 2));
      }

      adjustments.push({ id: node.id, oldFoW: currentFoW, newFoW: needFoW, delta });
    });

    // Brand polish: strip the navy stroke off every node and apply a
    // soft drop-shadow filter instead. Affects all node rects + polygons,
    // including meta (KPI band, fleet box).
    const SHADOW_ID = "vti-soft-shadow";
    let defs = svg.querySelector("defs");
    if (!defs) {
      defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      svg.insertBefore(defs, svg.firstChild);
    }
    if (!svg.querySelector(`#${SHADOW_ID}`)) {
      const f = document.createElementNS("http://www.w3.org/2000/svg", "filter");
      f.setAttribute("id", SHADOW_ID);
      f.setAttribute("x", "-20%"); f.setAttribute("y", "-20%");
      f.setAttribute("width", "140%"); f.setAttribute("height", "140%");
      f.innerHTML =
        '<feGaussianBlur in="SourceAlpha" stdDeviation="2.5"/>' +
        '<feOffset dx="0" dy="2" result="o"/>' +
        '<feComponentTransfer><feFuncA type="linear" slope="0.18"/></feComponentTransfer>' +
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>';
      defs.appendChild(f);
    }

    const stripBorderApplyShadow = (el) => {
      const style = el.getAttribute("style") || "";
      el.setAttribute(
        "style",
        style
          .replace(/stroke\s*:\s*[^;]+(!important)?;?/gi, "stroke:none !important;")
          .replace(/stroke-width\s*:\s*[^;]+(!important)?;?/gi, "stroke-width:0 !important;")
          .replace(/stroke-dasharray\s*:\s*[^;]+(!important)?;?/gi, "")
      );
      el.setAttribute("stroke", "none");
      el.setAttribute("filter", `url(#${SHADOW_ID})`);
    };
    svg.querySelectorAll("g.node > rect, g.node > polygon").forEach(stripBorderApplyShadow);
    // Subgraph wrappers (Mermaid's <g class="cluster"> > <rect>) get the
    // same no-border + soft shadow treatment as inner nodes.
    svg.querySelectorAll("g.cluster > rect").forEach((rect) => {
      stripBorderApplyShadow(rect);
      // Give cluster a subtle fill so the shadow has surface to drop from.
      const s = rect.getAttribute("style") || "";
      if (!/fill\s*:/.test(s)) {
        rect.setAttribute("style", s + ";fill:#EAF2FB !important;");
      }
    });

    // Rebuild orthogonal edge paths from current node positions. After
    // equalisation moves nodes around, ELK's original `d` attribute is
    // stale: lerp-shifting its bend points produced slight diagonals
    // wherever source and target had very different x-deltas (e.g. 7
    // source row → 1 narrow destination = "spider legs"). Cleanest fix
    // is to regenerate each edge as a 4-point right-angle path:
    //   start → down to midY → across to target column → down to target.
    // (Or right→midX→across in LR mode.) Routing is independent of any
    // prior path content, so it always produces a clean rectilinear
    // edge no matter how much its endpoints moved.
    function rebuildEdges(svg, nodeMap, horizontal) {
      svg.querySelectorAll("path.flowchart-link").forEach((edge) => {
        const id = edge.id || "";
        const m  = /L_([A-Za-z0-9_]+)_([A-Za-z0-9_]+)_\d+$/.exec(id);
        if (!m) return;
        const from = nodeMap.get(m[1]);
        const to   = nodeMap.get(m[2]);
        if (!from || !to) return;

        let d;
        if (horizontal) {
          const sx = from.cx + from.rectX + from.rectW; // src right edge
          const sy = from.cy;                            // src centre y
          const tx = to.cx + to.rectX;                   // tgt left edge
          const ty = to.cy;
          const mx = (sx + tx) / 2;
          d = `M${sx},${sy} L${mx},${sy} L${mx},${ty} L${tx},${ty}`;
        } else {
          const sx = from.cx;                                // src centre x
          const sy = from.cy + from.rectY + from.rectH;      // src bottom
          const tx = to.cx;
          const ty = to.cy + to.rectY;                       // tgt top
          const my = (sy + ty) / 2;
          d = `M${sx},${sy} L${sx},${my} L${tx},${my} L${tx},${ty}`;
        }
        edge.setAttribute("d", d);
      });
    }

    // Build short-id → node-info lookup so the rebuilder can map edge
    // endpoints back to current node positions.
    function buildNodeMap(nodes) {
      const map = new Map();
      nodes.forEach((n) => {
        const idMatch = /flowchart-([A-Za-z0-9_]+)-\d+$/.exec(n.node.id || "");
        if (!idMatch) return;
        map.set(idMatch[1], {
          cx: n.cx, cy: n.cy,
          rectX: parseFloat(n.rect.getAttribute("x")),
          rectY: parseFloat(n.rect.getAttribute("y")),
          rectW: parseFloat(n.rect.getAttribute("width")),
          rectH: parseFloat(n.rect.getAttribute("height")),
        });
      });
      return map;
    }

    // ── Consistency rule ────────────────────────────────────────────────
    // LR/RL: all nodes get the SAME height (global max).
    // TB/BT: nodes in the same row (same y) get the SAME height AND the
    //        SAME width (row max for each).
    // Rationale: in a horizontal flow, nodes line up shoulder-to-shoulder
    // and uneven heights look ragged → equalise globally. In a vertical
    // flow there are multiple rows; within each row the boxes still line
    // up shoulder-to-shoulder so the same equal-height rule applies, and
    // equal width as well (matches user's "vertical → equal width" rule).
    // TB equalisation is per-row (not global) because parallel fanout
    // branches sharing one y-rank can overflow the canvas if forced to
    // match a wider single-box row's width — option (a) per user confirm.
    const equalised = { mode: isHorizontal ? "lr-global-height" : "tb-row-width+height", nodes: 0 };

    const nodeData = [];
    svg.querySelectorAll("g.node").forEach((node) => {
      const tx = node.getAttribute("transform") || "";
      const m  = tx.match(/translate\(\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*\)/);
      const cx = m ? parseFloat(m[1]) : 0;
      const cy = m ? parseFloat(m[2]) : 0;
      const rect = node.querySelector(":scope > rect.label-container, :scope > rect");
      if (!rect) return;
      nodeData.push({
        node, rect, cx, cy,
        w: parseFloat(rect.getAttribute("width")),
        h: parseFloat(rect.getAttribute("height")),
      });
    });

    // Snapshot cluster ownership BEFORE equalisation. ELK places clusters
    // and nodes as siblings (not parent/child), so we map by spatial
    // containment of the node centroid against the original ELK cluster
    // bounds. After equalisation we'll re-fit each cluster's rect to the
    // union bbox of its members.
    const clusterInfo = [];
    svg.querySelectorAll("g.cluster").forEach((cluster) => {
      const rect = cluster.querySelector(":scope > rect");
      if (!rect) return;
      const x0 = parseFloat(rect.getAttribute("x"));
      const y0 = parseFloat(rect.getAttribute("y"));
      const w  = parseFloat(rect.getAttribute("width"));
      const h  = parseFloat(rect.getAttribute("height"));
      const labelG = cluster.querySelector(":scope > g.cluster-label");
      clusterInfo.push({
        cluster, rect, labelG,
        bounds:  { x0, y0, x1: x0 + w, y1: y0 + h },
        members: [],
      });
    });
    nodeData.forEach((n) => {
      let owner = null, bestArea = Infinity;
      clusterInfo.forEach((ci) => {
        const { x0, y0, x1, y1 } = ci.bounds;
        if (n.cx >= x0 && n.cx <= x1 && n.cy >= y0 && n.cy <= y1) {
          const a = (x1 - x0) * (y1 - y0);
          if (a < bestArea) { bestArea = a; owner = ci; }
        }
      });
      if (owner) owner.members.push(n);
    });

    // Center-anchored resize (used by LR-global; ELK aligns LR nodes by
    // their centroids so symmetric growth keeps the row visually clean).
    const applyHeightCentered = (n, newH) => {
      n.rect.setAttribute("height", String(newH));
      n.rect.setAttribute("y", String(-newH / 2));
    };
    const applyWidthCentered = (n, newW) => {
      n.rect.setAttribute("width", String(newW));
      n.rect.setAttribute("x", String(-newW / 2));
    };
    // (TB rows do top-anchored resize inline — preserves whichever top
    // edge ELK assigned, since ELK may use either CENTROID or TOP
    // alignment depending on whether the node sits in a subgraph.)

    // Cluster nodes by a coordinate axis with a proximity threshold —
    // ELK shifts same-rank siblings by 10–30 px when their heights
    // differ, so a strict equality bucket would miss them. Threshold
    // 60 px is wider than typical intra-rank offset, narrower than
    // typical inter-rank spacing.
    const clusterByAxis = (nodes, axis, threshold) => {
      const sorted  = [...nodes].sort((a, b) => a[axis] - b[axis]);
      const buckets = [];
      let current   = null;
      for (const n of sorted) {
        if (!current || n[axis] - current.lastVal > threshold) {
          current = { nodes: [n], lastVal: n[axis] };
          buckets.push(current.nodes);
        } else {
          current.nodes.push(n);
          current.lastVal = n[axis];
        }
      }
      return buckets;
    };

    if (isHorizontal) {
      // LR: cluster by cy (one row per rank). Within each row equalise
      // height symmetrically (center-anchored — ELK aligns LR siblings
      // by centroid).
      const rows = clusterByAxis(nodeData, "cy", 60);
      rows.forEach((row) => {
        if (row.length < 2) return;
        const maxH = Math.max(...row.map((n) => n.h));
        row.forEach((n) => {
          if (n.h < maxH) { applyHeightCentered(n, maxH); equalised.nodes++; }
        });
      });
      // Regenerate edges as rectilinear (horizontal-rail variant) so
      // height changes don't leave the edge endpoints offset.
      rebuildEdges(svg, buildNodeMap(nodeData), true /* LR */);
    } else {
      // TB: cluster by cy → each row. Within each row force ALL members
      // to a single (height, top) pair so they line up exactly:
      //   - height = max h in the row
      //   - top    = min top in the row (visually highest edge)
      // We force-set rather than "only-when-smaller" because ELK uses
      // CENTROID alignment for subgraph children (cy identical, tops
      // differ when h differs) but TOP alignment for root-level nodes
      // — equalising by max-only leaves the centroid-aligned cases
      // visually ragged.
      const rows = clusterByAxis(nodeData, "cy", 60);
      const cxDeltas = new Map(); // node-id → horizontal shift applied
      rows.forEach((row) => {
        if (row.length < 2) return;
        const maxW   = Math.max(...row.map((n) => n.w));
        const maxH   = Math.max(...row.map((n) => n.h));
        const minTop = Math.min(...row.map(
          (n) => n.cy + parseFloat(n.rect.getAttribute("y"))
        ));
        row.forEach((n) => {
          let touched = false;
          if (n.w < maxW) { applyWidthCentered(n, maxW); touched = true; n.w = maxW; }
          const currentY  = parseFloat(n.rect.getAttribute("y"));
          const targetY   = minTop - n.cy;
          if (n.h !== maxH || Math.abs(currentY - targetY) > 0.5) {
            n.rect.setAttribute("height", String(maxH));
            n.rect.setAttribute("y", String(targetY));
            touched = true;
            n.h = maxH;
          }
          if (touched) equalised.nodes++;
        });

        // Redistribute cx evenly so horizontal gaps are uniform — width
        // equalisation grows boxes outward from their ELK-given centres,
        // which packs the row unevenly when original widths differed.
        const sorted = [...row].sort((a, b) => a.cx - b.cx);
        const firstLeft = sorted[0].cx + parseFloat(sorted[0].rect.getAttribute("x"));
        const lastN     = sorted[sorted.length - 1];
        const lastRight = lastN.cx + parseFloat(lastN.rect.getAttribute("x")) + lastN.w;
        const totalBox  = sorted.reduce((s, n) => s + n.w, 0);
        const gap       = (lastRight - firstLeft - totalBox) / (sorted.length - 1);
        let cursor = firstLeft;
        sorted.forEach((n) => {
          const newCx = cursor + n.w / 2;
          const dx    = newCx - n.cx;
          if (Math.abs(dx) > 0.5) {
            n.node.setAttribute("transform", `translate(${newCx}, ${n.cy})`);
            cxDeltas.set(n.node.id, dx);
            n.cx = newCx;
          }
          cursor += n.w + gap;
        });
      });

      // Trunk-width consistency: single-node rows in a TB diagram form a
      // visual "spine" (DISCOVER, CLASSIFY, FINALIZE, …). Without this
      // pass each spine box keeps its natural content-fit width and the
      // column looks ragged. Equalise them all to the widest spine box.
      // Multi-node rows are left alone — their per-row widths already
      // match each other and packing more would risk canvas overflow.
      const trunkRows = rows.filter((r) => r.length === 1);
      if (trunkRows.length >= 2) {
        const trunkMaxW = Math.max(...trunkRows.map((r) => r[0].w));
        trunkRows.forEach((r) => {
          const n = r[0];
          if (n.w < trunkMaxW - 0.5) {
            applyWidthCentered(n, trunkMaxW);
            n.w = trunkMaxW;
            equalised.nodes++;
          }
        });
      }

      // Final pass: regenerate every edge as a rectilinear 4-point
      // path against the now-current node positions, so right-angle
      // routing is preserved no matter how far equalisation moved the
      // nodes. Replaces the older lerp approach which slightly skewed
      // edges that crossed large x-deltas (e.g. 7 sources → narrow
      // destination = "spider legs"). Reference cxDeltas to keep the
      // computed-but-unused-in-this-branch map from being flagged.
      void cxDeltas;
      rebuildEdges(svg, buildNodeMap(nodeData), false /* TB */);
    }


    // Re-fit each cluster around its members' post-equalisation bbox.
    // Inner nodes may have grown taller/wider; ELK's original cluster
    // size won't have anticipated that, so without this pass the
    // subgraph rect can clip its children.
    const CLUSTER_PAD_X      = 18;
    const CLUSTER_PAD_TOP    = 36;  // headroom for the cluster label
    const CLUSTER_PAD_BOTTOM = 18;
    clusterInfo.forEach((ci) => {
      if (!ci.members.length) return;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      ci.members.forEach((n) => {
        const rx = parseFloat(n.rect.getAttribute("x"));
        const ry = parseFloat(n.rect.getAttribute("y"));
        const rw = parseFloat(n.rect.getAttribute("width"));
        const rh = parseFloat(n.rect.getAttribute("height"));
        minX = Math.min(minX, n.cx + rx);
        minY = Math.min(minY, n.cy + ry);
        maxX = Math.max(maxX, n.cx + rx + rw);
        maxY = Math.max(maxY, n.cy + ry + rh);
      });
      const newX = minX - CLUSTER_PAD_X;
      const newY = minY - CLUSTER_PAD_TOP;
      const newW = (maxX - minX) + 2 * CLUSTER_PAD_X;
      const newH = (maxY - minY) + CLUSTER_PAD_TOP + CLUSTER_PAD_BOTTOM;
      ci.rect.setAttribute("x", String(newX));
      ci.rect.setAttribute("y", String(newY));
      ci.rect.setAttribute("width", String(newW));
      ci.rect.setAttribute("height", String(newH));
      ci.rect.setAttribute("rx", "14");
      ci.rect.setAttribute("ry", "14");

      // Re-center the cluster label horizontally on the new rect; keep
      // its y at the cluster top edge so the label sits inside the
      // padded headroom.
      if (ci.labelG) {
        const fo = ci.labelG.querySelector("foreignObject");
        const lblW = fo ? parseFloat(fo.getAttribute("width") || "0") : 0;
        const newLabelX = newX + (newW - lblW) / 2;
        const newLabelY = newY + 8; // small inset under the cluster top
        ci.labelG.setAttribute("transform", `translate(${newLabelX}, ${newLabelY})`);
      }
    });

    // Final pass: expand the SVG viewBox to encompass everything we just
    // grew. Equalisation + cluster re-fit may push rects past the
    // viewBox ELK computed before we adjusted anything; without this
    // step, edges of clusters or wide-equalised nodes get clipped.
    const VB_MARGIN = 12;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const swallow = (x, y, w, h) => {
      if (![x, y, w, h].every(Number.isFinite)) return;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x + w > maxX) maxX = x + w;
      if (y + h > maxY) maxY = y + h;
    };
    // Node rects (with their transform offset)
    nodeData.forEach((n) => {
      const rx = parseFloat(n.rect.getAttribute("x"));
      const ry = parseFloat(n.rect.getAttribute("y"));
      const rw = parseFloat(n.rect.getAttribute("width"));
      const rh = parseFloat(n.rect.getAttribute("height"));
      swallow(n.cx + rx, n.cy + ry, rw, rh);
    });
    // Cluster rects (already in absolute coords)
    clusterInfo.forEach((ci) => {
      swallow(
        parseFloat(ci.rect.getAttribute("x")),
        parseFloat(ci.rect.getAttribute("y")),
        parseFloat(ci.rect.getAttribute("width")),
        parseFloat(ci.rect.getAttribute("height")),
      );
    });
    if (Number.isFinite(minX)) {
      const newVB = [
        minX - VB_MARGIN, minY - VB_MARGIN,
        (maxX - minX) + 2 * VB_MARGIN, (maxY - minY) + 2 * VB_MARGIN,
      ];
      svg.setAttribute("viewBox", newVB.map((v) => v.toFixed(2)).join(" "));
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      svg.setAttribute("style",
        (svg.getAttribute("style") || "")
          .replace(/max-width\s*:\s*[\d.]+px\s*;?/i, "") + "; max-width: 100%;");
    }

    return { ok: true, adjustments, equalised, clusters: clusterInfo.length };
  }, { isHorizontal }) : { ok: true, adjustments: [], equalised: { mode: isSequence ? "sequence-passthrough" : "passthrough", nodes: 0 } };

  // Read back the final SVG markup. Use XMLSerializer so foreignObject
  // children are emitted as well-formed XHTML (<br/> not <br>) — viewing
  // a `.svg` file as `image/svg+xml` strictly parses XML and chokes on
  // HTML-style void tags.
  let finalSvg = await page.evaluate(() => {
    const svg = document.querySelector("#host svg");
    if (!svg) return "";
    return new XMLSerializer().serializeToString(svg);
  });

  if (!finalSvg) throw new Error("No SVG produced");

  // Re-embed the cssFile inside the SVG defs so the viewing browser binds
  // the same Plus Jakarta Sans we measured against (self-contained).
  if (cssText) {
    finalSvg = finalSvg.replace(
      /<svg([^>]*)>/,
      `<svg$1><defs><style>${cssText.replace(/<\/style>/g, "<\\/style>")}</style></defs>`
    );
  }

  writeFileSync(outputPath, finalSvg, "utf8");
  const adj = fitInfo?.adjustments || [];
  const eq  = fitInfo?.equalised || { mode: "?", nodes: 0 };
  console.log(
    `[ok] ${basename(inputPath)} → ${basename(outputPath)}  ` +
    `(${adj.length} widened · ${eq.nodes} equalised via ${eq.mode})`
  );
} finally {
  await browser.close();
  try { rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}
