import { useEffect, useRef } from "react";
import type { Plane, Frame } from "./types";
import type { CatalogMarker } from "./surveys";
interface Props {
  plane: Plane;
  frame: Frame;
  zoom: number;
  pan: number[];
  stretch: number;
  overlays: string[];
  onPan: (p: number[]) => void;
  onInspect: (x: number, y: number) => void;
  canvasRef?: React.RefObject<HTMLCanvasElement | null>;
  catalogMarkers?:CatalogMarker[];
  onCatalogSelect?:(key:string)=>void;
}
export function SkyCanvas({
  plane,
  frame,
  zoom,
  pan,
  stretch,
  overlays,
  onPan,
  onInspect,
  canvasRef,
  catalogMarkers=[],
  onCatalogSelect,
}: Props) {
  const local = useRef<HTMLCanvasElement>(null);
  const ref = canvasRef || local;
  const drag = useRef<{ x: number; y: number; pan: number[] } | null>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const renderStarted=performance.now();
    const context = canvas.getContext("2d")!;
    const [height, width] = plane.shape;
    const small = document.createElement("canvas");
    small.width = width;
    small.height = height;
    const data = small.getContext("2d")!.createImageData(width, height);
    for (let y = 0; y < height; y++)
      for (let x = 0; x < width; x++) {
        const i = ((height - 1 - y) * width + x) * 4;
        const value = plane.pixels[y][x];
        let color =
          value === null
            ? [16, 24, 32]
            : Array(3).fill(Math.round(255 * Math.pow(value, 1 / stretch)));
        if (overlays.includes("coverage") && !plane.coverage[y][x])
          color = (x + y) % 4 < 2 ? [45, 63, 76] : [17, 29, 40];
        if (
          overlays.includes("quality") &&
          plane.coverage[y][x] &&
          !plane.quality[y][x]
        )
          color = [Math.max(color[0], 140), 90, 25];
        if (overlays.includes("spectral") && plane.joint[y][x])
          color = [
            color[0] * 0.45,
            Math.max(color[1], 150),
            Math.max(color[2], 170),
          ];
        data.data.set([...color, 255], i);
      }
    small.getContext("2d")!.putImageData(data, 0, 0);
    context.fillStyle = "#090d12";
    context.fillRect(0, 0, 800, 800);
    context.save();
    context.translate(400 + pan[0], 400 + pan[1]);
    context.scale(zoom, zoom);
    context.imageSmoothingEnabled = false;
    context.drawImage(small, -350, -350, 700, 700);
    if (overlays.includes("prediction") && frame.prediction_pixel) {
      const [x, y] = frame.prediction_pixel;
      context.strokeStyle = "#f2b760";
      context.lineWidth = 1.5 / zoom;
      context.beginPath();
      context.arc(
        -350 + ((x + 0.5) * 700) / width,
        350 - ((y + 0.5) * 700) / height,
        10 / zoom,
        0,
        Math.PI * 2,
      );
      context.stroke();
    }
    for(const marker of catalogMarkers){
      const [x,y]=marker.pixel;
      if(!Number.isFinite(x)||!Number.isFinite(y)||x<-.5||y<-.5||x>=width-.5||y>=height-.5)continue;
      const cx=-350+(x+.5)*700/width,cy=350-(y+.5)*700/height;
      const r=(marker.selected?9:5)/zoom;
      context.globalAlpha=marker.opacity;
      context.strokeStyle=marker.selected?'#ffffff':marker.survey==='gaia'?'#a9c7ee':'#f2b760';
      context.lineWidth=(marker.selected?2:1.2)/zoom;
      context.beginPath();
      if(marker.survey==='gaia')context.arc(cx,cy,r,0,Math.PI*2);
      else{context.moveTo(cx,cy-r);context.lineTo(cx+r,cy);context.lineTo(cx,cy+r);context.lineTo(cx-r,cy);context.closePath();}
      context.stroke();
    }
    context.restore();
    canvas.dataset.renderStarted=String(renderStarted);
    canvas.dataset.renderMs=String(performance.now()-renderStarted);
    canvas.dataset.renderFinished=String(performance.now());
    canvas.dataset.ready = frame.obs_id;
  }, [plane, frame, zoom, pan, stretch, overlays, ref,catalogMarkers]);
  function inspect(clientX: number, clientY: number) {
    const rect = ref.current!.getBoundingClientRect();
    const wx=(((clientX-rect.left)*800/rect.width)-400-pan[0])/zoom;
    const wy=(((clientY-rect.top)*800/rect.height)-400-pan[1])/zoom;
    const candidates=catalogMarkers.map(m=>({marker:m,distance:Math.hypot(wx-(-350+(m.pixel[0]+.5)*700/plane.shape[1]),wy-(350-(m.pixel[1]+.5)*700/plane.shape[0]))})).sort((a,b)=>a.distance-b.distance);
    if(candidates[0]&&candidates[0].distance*zoom<14*800/rect.width)onCatalogSelect?.(candidates[0].marker.key);
    const x = Math.floor(
      ((((clientX - rect.left) * 800) / rect.width - 400 - pan[0]) /
        zoom /
        700) *
        plane.shape[1] +
        plane.shape[1] / 2,
    );
    const y = Math.floor(
      plane.shape[0] / 2 -
        ((((clientY - rect.top) * 800) / rect.height - 400 - pan[1]) /
          zoom /
          700) *
          plane.shape[0],
    );
    if (x >= 0 && y >= 0 && x < plane.shape[1] && y < plane.shape[0])
      onInspect(x, y);
  }
  return (
    <canvas
      ref={ref}
      width={800}
      height={800}
      tabIndex={0}
      role="img"
      aria-label="Infrared sky. Drag to pan. Arrow keys pan, Enter inspects the central pixel. Zoom controls are below."
      onKeyDown={(e) => {
        const moves: Record<string, number[]> = {
          ArrowLeft: [20, 0],
          ArrowRight: [-20, 0],
          ArrowUp: [0, 20],
          ArrowDown: [0, -20],
        };
        if (moves[e.key]) {
          e.preventDefault();
          onPan([pan[0] + moves[e.key][0], pan[1] + moves[e.key][1]]);
        }
        if (e.key === "Enter")
          onInspect(
            Math.floor(plane.shape[1] / 2),
            Math.floor(plane.shape[0] / 2),
          );
      }}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        drag.current = { x: e.clientX, y: e.clientY, pan: [...pan] };
      }}
      onPointerMove={(e) => {
        if (drag.current) {
          const scale = 800 / e.currentTarget.getBoundingClientRect().width;
          onPan([
            drag.current.pan[0] + (e.clientX - drag.current.x) * scale,
            drag.current.pan[1] + (e.clientY - drag.current.y) * scale,
          ]);
        }
      }}
      onPointerUp={(e) => {
        if (
          drag.current &&
          Math.hypot(e.clientX - drag.current.x, e.clientY - drag.current.y) < 4
        )
          inspect(e.clientX, e.clientY);
        drag.current = null;
      }}
      onPointerCancel={() => {
        drag.current = null;
      }}
    />
  );
}
