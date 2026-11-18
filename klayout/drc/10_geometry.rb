# Geometry / DFM checks: only orthogonal and 45 degree edges.

SKEW_LAYERS = {
  "ACT" => AA, "POLY" => PO, "CT" => CT, "NP" => NP, "PP" => PP, "SAB" => SAB,
  "MET1" => M1, "MET2" => M2, "MET3" => M3, "MET4" => M4, "MET5" => M5
}

SKEW_LAYERS.each do |name, layer|
  ics55_check("GEO.ANG.#{name}", "Only 0/45/90 degree edges allowed on #{name}", name) do
    edges = layer.edges
    allowed = edges.with_angle(0.0..0.1) +
              edges.with_angle(44.9..45.1) +
              edges.with_angle(89.9..90.1)
    (edges - allowed).not_inside(WAIVE).not_inside(IND).not_inside(SRAM)
  end
end

# Off-grid vertices (1 nm manufacturing grid).
OFFGRID_LAYERS = {
  "ACT" => AA, "POLY" => PO, "CT" => CT,
  "MET1" => M1, "MET2" => M2, "MET3" => M3, "MET4" => M4, "MET5" => M5
}

OFFGRID_LAYERS.each do |name, layer|
  ics55_check("GEO.OFFGRID.#{name}", "#{name} vertices must be on the 1 nm grid", name) do
    layer.ongrid(0.001)
  end
end
