import { useEffect, useRef } from "react";
import L from "leaflet";

function pin(latlng, fill, label) {
  return L.circleMarker(latlng, { radius: 8, color: "#ffffff", weight: 2, fillColor: fill, fillOpacity: 1 })
    .bindTooltip(label, { direction: "top", offset: [0, -6] });
}

const LEGEND = [
  { label: "Planned route", style: { borderTop: "4px solid #334155" } },
  { label: "Route inside hazard zone", style: { borderTop: "4px solid #dc2626" } },
  { label: "Recommended alternative", style: { borderTop: "4px dashed #16a34a" } },
  { label: "Route to backup hub", style: { borderTop: "4px dotted #f97316" } },
];

export default function MapView({ scenario, network, result }) {
  const container = useRef(null);
  const map = useRef(null);
  const dynamic = useRef(null);

  // Base map, fixed route and markers: created once per scenario
  useEffect(() => {
    if (!scenario) return undefined;
    const m = L.map(container.current, { preferCanvas: true, zoomSnap: 0.25 });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m);
    const route = L.polyline(scenario.route, { color: "#334155", weight: 5, opacity: 0.85 }).addTo(m);
    dynamic.current = L.layerGroup().addTo(m);
    pin(scenario.origin, "#0f172a", `Convoy RZ-01 at ${scenario.names.origin}`).addTo(m);
    pin(scenario.destination, "#16a34a", `Destination: ${scenario.names.destination}`).addTo(m);
    pin(scenario.hub, "#f97316", `Backup hub: ${scenario.names.hub}`).addTo(m);
    m.fitBounds(route.getBounds().pad(0.15));
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
      dynamic.current = null;
    };
  }, [scenario]);

  // Faint road network underneath, so the map is readable even if tiles cannot load
  useEffect(() => {
    if (!map.current || !network) return undefined;
    const layer = L.polyline(network, { color: "#64748b", weight: 1, opacity: 0.35, interactive: false }).addTo(
      map.current,
    );
    layer.bringToBack();
    return () => layer.remove();
  }, [scenario, network]);

  // Hazard and route options: redrawn on every simulation result, without moving the view
  useEffect(() => {
    const group = dynamic.current;
    if (!group || !result) return;
    group.clearLayers();
    const hz = result.hazard;
    L.circle([hz.lat, hz.lon], {
      radius: hz.radius_km * 1000,
      color: hz.color,
      weight: 1.5,
      fillColor: hz.color,
      fillOpacity: 0.12 + 0.18 * hz.severity,
    })
      .bindTooltip(`${hz.label} · severity ${hz.severity.toFixed(2)}`)
      .addTo(group);
    if (result.hazard_segments.length) {
      L.polyline(result.hazard_segments, { color: "#dc2626", weight: 6 }).addTo(group);
    }
    if (result.routes.hub) {
      L.polyline(result.routes.hub, { color: "#f97316", weight: 4, dashArray: "2 7" }).addTo(group);
    }
    if (result.routes.alternative) {
      L.polyline(result.routes.alternative, { color: "#16a34a", weight: 5, dashArray: "10 7" }).addTo(group);
    }
  }, [scenario, result]);

  return (
    <div className="relative h-full min-h-[24rem]">
      <div ref={container} className="absolute inset-0" />
      <div className="pointer-events-none absolute top-2 right-2 left-14 z-[1000] flex justify-end">
        <p className="max-w-md rounded-md bg-white/90 px-3 py-1.5 text-[11px] text-slate-700 shadow">
          <span className="font-semibold">{scenario.label}.</span> {scenario.context}{" "}
          {scenario.names.origin} → {scenario.names.destination}, {scenario.route_km} km.
        </p>
      </div>
      <div className="pointer-events-none absolute bottom-6 left-2 z-[1000] hidden rounded-md bg-white/90 px-3 py-2 text-[11px] shadow sm:block">
        {LEGEND.map((item) => (
          <div key={item.label} className="flex items-center gap-2 py-0.5">
            <span className="inline-block w-6" style={item.style} />
            {item.label}
          </div>
        ))}
        {result && (
          <div className="flex items-center gap-2 py-0.5">
            <span
              className="inline-block size-3 rounded-full border"
              style={{ backgroundColor: `${result.hazard.color}55`, borderColor: result.hazard.color }}
            />
            {result.hazard.label} zone
          </div>
        )}
      </div>
    </div>
  );
}
