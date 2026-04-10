import { useEffect, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { select } from "d3-selection";
import { zoom, zoomIdentity } from "d3-zoom";
import { polygonHull } from "d3-polygon";
import type {
  NetworkCluster,
  NetworkEdge,
  NetworkNode,
  NetworkResponse,
} from "../api/types";
import BookTooltip from "./BookTooltip";

interface SimNode extends SimulationNodeDatum {
  id: string;
  data: NetworkNode;
  cluster: number;
}

interface SimLink extends SimulationLinkDatum<SimNode> {
  weight: number;
}

interface Props {
  data: NetworkResponse;
}

export default function NetworkGraph({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const [tooltip, setTooltip] = useState<{
    node: NetworkNode;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    const svg = svgRef.current;
    const g = gRef.current;
    if (!svg || !g) return;

    const width = svg.clientWidth;
    const height = svg.clientHeight;

    // Build simulation data.
    const clusterMap = new Map(data.clusters.map((c) => [c.id, c]));

    const nodes: SimNode[] = data.nodes.map((n) => ({
      id: n.id,
      data: n,
      cluster: n.cluster,
    }));

    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    const links: SimLink[] = data.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        weight: e.weight,
      }));

    // Force simulation.
    const sim = forceSimulation(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .strength((d) => d.weight * 0.5)
      )
      .force("charge", forceManyBody().strength(-120))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide(14));

    // Zoom behavior.
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 5])
      .on("zoom", (event) => {
        select(g).attr("transform", event.transform);
      });

    select(svg)
      .call(zoomBehavior)
      .call(zoomBehavior.transform, zoomIdentity)
      .on("click", (event) => {
        // Click on background dismisses tooltip.
        if (event.target === svg) {
          setTooltip(null);
        }
      });

    const gSel = select(g);

    // Clear previous render.
    gSel.selectAll("*").remove();

    // Cluster hull layer (behind everything).
    const hullGroup = gSel.append("g").attr("class", "hulls");

    // Edge layer.
    const linkSel = gSel
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", (d) => Math.min(d.weight, 0.8))
      .attr("stroke-width", (d) => 1 + d.weight * 2);

    // Node layer.
    const nodeSel = gSel
      .append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 8)
      .attr("fill", (d) => clusterMap.get(d.cluster)?.color ?? "#6b7280")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .attr("cursor", "pointer")
      .on("mouseenter", function (_, d) {
        select(this).attr("r", 11).attr("stroke-width", 2.5);
        // Highlight connected edges.
        linkSel
          .attr("stroke", (l) => {
            const s = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
            const t = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
            return s === d.id || t === d.id
              ? clusterMap.get(d.cluster)?.color ?? "#6366f1"
              : "#94a3b8";
          })
          .attr("stroke-opacity", (l) => {
            const s = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
            const t = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
            return s === d.id || t === d.id ? 1 : 0.15;
          });
      })
      .on("mouseleave", function () {
        select(this).attr("r", 8).attr("stroke-width", 1.5);
        linkSel
          .attr("stroke", "#94a3b8")
          .attr("stroke-opacity", (d) => Math.min(d.weight, 0.8));
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        const rect = svg.getBoundingClientRect();
        setTooltip({
          node: d.data,
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        });
      });

    // Tick handler — update positions every frame.
    sim.on("tick", () => {
      linkSel
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      nodeSel.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!);

      // Update cluster hulls.
      hullGroup.selectAll("path").remove();
      const clusterIds = [...new Set(nodes.map((n) => n.cluster))];
      for (const cid of clusterIds) {
        const members = nodes.filter((n) => n.cluster === cid);
        if (members.length < 3) continue;
        const points: [number, number][] = members.map((n) => [n.x!, n.y!]);
        const hull = polygonHull(points);
        if (!hull) continue;
        const color = clusterMap.get(cid)?.color ?? "#6b7280";
        hullGroup
          .append("path")
          .attr("d", `M${hull.map((p) => p.join(",")).join("L")}Z`)
          .attr("fill", color)
          .attr("fill-opacity", 0.08)
          .attr("stroke", color)
          .attr("stroke-opacity", 0.25)
          .attr("stroke-width", 1.5)
          .attr("stroke-linejoin", "round");
      }
    });

    return () => {
      sim.stop();
    };
  }, [data]);

  return (
    <div className="relative h-[calc(100vh-8rem)] w-full overflow-hidden rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <svg ref={svgRef} className="h-full w-full">
        <g ref={gRef} />
      </svg>
      {tooltip && (
        <BookTooltip
          node={tooltip.node}
          x={tooltip.x}
          y={tooltip.y}
          onClose={() => setTooltip(null)}
        />
      )}
    </div>
  );
}
