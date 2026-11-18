# Back-end rules: thin metals M1..M5, V1..V4 and the T4M2 thick top metal.
# The stack size comes from TOTAL_METAL/TOP_METAL (default 1P6M + T4M2).

METAL_LIMITS = [
  ["MET1", 0.09, 0.09, 0.042],
  ["MET2", 0.10, 0.10, 0.052],
  ["MET3", 0.10, 0.10, 0.052],
  ["MET4", 0.10, 0.10, 0.052],
  ["MET5", 0.10, 0.10, 0.052],
  ["MET6", 0.10, 0.10, 0.052],
  ["MET7", 0.10, 0.10, 0.052],
  ["MET8", 0.10, 0.10, 0.052]
]

THIN_METAL.times do |idx|
  name, wmin, smin, amin = METAL_LIMITS[idx]
  layer = METALS[idx]
  ics55_check("#{name}.W.1", "#{name} width >= #{wmin}um", name) do
    layer.width(wmin).not_inside(WAIVE)
  end
  ics55_check("#{name}.W.2", "#{name} width <= 12.00um", name) do
    layer.with_bbox_max(12.0, nil).not_inside(WAIVE)
  end
  ics55_check("#{name}.S.1", "#{name} space >= #{smin}um", name) do
    layer.space(smin).not_inside(SRAM).not_inside(IND).not_inside(WAIVE)
  end
  ics55_check("#{name}.A.1", "#{name} area >= #{amin}um2", name) do
    layer.with_area(0.0, amin).not_inside(SRAM).not_inside(WAIVE)
  end
end

# Vias V1..V(n-1) for n thin metals.
VIA_LIMITS = [
  ["VIA1", V1, M1, M2, "MET1", "MET2"],
  ["VIA2", V2, M2, M3, "MET2", "MET3"],
  ["VIA3", V3, M3, M4, "MET3", "MET4"],
  ["VIA4", V4, M4, M5, "MET4", "MET5"],
  ["VIA5", V5, M5, M6, "MET5", "MET6"],
  ["VIA6", V6, M6, M7, "MET6", "MET7"],
  ["VIA7", V7, M7, M8, "MET7", "MET8"]
]

(THIN_METAL - 1).times do |idx|
  name, via, lower, upper, lower_name, upper_name = VIA_LIMITS[idx]
  ics55_check("#{name}.W.1", "Fixed #{name} width (square shape) = 0.09um", name) do
    via.not_inside(GRID_AREA + WAIVE).width(0.09)
  end
  ics55_check("#{name}.W.2", "Fixed #{name} area = 0.09um x 0.09um", name) do
    via.not_inside(GRID_AREA + WAIVE).with_area(0.0082, nil)
  end
  ics55_check("#{name}.S.1", "Space between two #{name}s >= 0.11um", name) do
    via.space(0.11).not_inside(WAIVE)
  end
  ics55_check("#{name}.EN.1", "#{name} must be fully enclosed by #{lower_name}", lower_name) do
    via.outside(lower).not_inside(SRAM + WAIVE)
  end
  ics55_check("#{name}.EN.2", "#{lower_name} enclosure of #{name} >= 0.03um", lower_name) do
    lower.enclosing(via, 0.03).not_inside(SRAM + WAIVE)
  end
  ics55_check("#{name}.EN.3", "#{name} must be fully enclosed by #{upper_name}", upper_name) do
    via.outside(upper).not_inside(SRAM + WAIVE)
  end
  ics55_check("#{name}.EN.4", "#{upper_name} enclosure of #{name} >= 0.005um", upper_name) do
    upper.enclosing(via, 0.005).not_inside(SRAM + WAIVE)
  end
end

# Thick top metal (T4M2 default, 4x option).
if T4M2_ON
  ics55_check("T4M2.W.1", "T4M2 width >= 0.40um", "T4M2") do
    T4M2.width(0.40).not_inside(IND).not_inside(DEUPAD_AREA).not_inside(WAIVE)
  end
  ics55_check("T4M2.W.2", "T4M2 width <= 20um", "T4M2") do
    T4M2.with_bbox_max(20.0, nil).not_inside(IND).not_inside(DEUPAD_AREA).not_inside(WAIVE)
  end
  ics55_check("T4M2.S.1", "T4M2 space >= 0.40um", "T4M2") do
    T4M2.space(0.40).not_inside(IND).not_inside(WAIVE)
  end
  ics55_check("T4M2.A.1", "T4M2 area >= 0.40um2", "T4M2") do
    T4M2.with_area(0.0, 0.40).not_inside(WAIVE)
  end
  ics55_check("T4V2.W.1", "Fixed T4V2 width (square shape) = 0.36um", "T4V2") do
    T4V2.not_inside(GRID_AREA + WAIVE).width(0.36)
  end
  ics55_check("T4V2.W.2", "Fixed T4V2 area = 0.36um x 0.36um", "T4V2") do
    T4V2.not_inside(GRID_AREA + WAIVE).with_area(0.1297, nil)
  end
  ics55_check("T4V2.S.1", "T4V2 space >= 0.34um", "T4V2") do
    T4V2.space(0.34).not_inside(WAIVE)
  end
  ics55_check("T4V2.EN.1", "T4V2 must be fully enclosed by T4M2", "T4M2") do
    T4V2.outside(T4M2).not_inside(WAIVE)
  end
  ics55_check("T4V2.EN.2", "T4M2 enclosure of T4V2 >= 0.02um", "T4M2") do
    T4M2.enclosing(T4V2, 0.02).not_inside(WAIVE)
  end
end

# Pad / RDL rules that are independent of the metal stack.
COVER = L_COVER

ics55_check("CB.W.1", "CB width >= 3.0um", "CB") do
  CB.width(3.0).not_inside(WAIVE)
end
ics55_check("CB.S.1", "Space between two CBs >= 5.0um", "CB") do
  CB.space(5.0).not_inside(WAIVE)
end
ics55_check("RV.W.1", "Fixed RV width = 3.0um", "RV") do
  RV.width(3.0).not_inside(WAIVE)
end
ics55_check("RV.W.2", "Fixed RV area = 3.0um x 3.0um", "RV") do
  RV.with_area(9.0001, nil).not_inside(WAIVE)
end
ics55_check("RV.S.1", "Space between two RVs >= 3.0um", "RV") do
  RV.space(3.0).not_inside(WAIVE)
end
ics55_check("RV.S.2", "Space between RV and CB >= 6.0um", "RV") do
  RV.separation(CB, 6.0).not_inside(WAIVE)
end
ics55_check("RV.EN.1", "RV enclosure by RDL >= 1.5um", "RDL") do
  RDL.enclosing(RV, 1.5).not_inside(WAIVE)
end
ics55_check("RDL.W.1", "RDL width >= 3.0um", "RDL") do
  RDL.width(3.0).not_inside(WAIVE)
end
ics55_check("RDL.W.2", "RDL width <= 35um", "RDL") do
  RDL.with_bbox_max(35.0, nil).not_inside(WAIVE)
end
ics55_check("RDL.S.1", "Space between two (RDL OR ALPAD) >= 2.0um", "RDL") do
  (RDL + ALPAD).space(2.0).not_inside(WAIVE)
end
ics55_check("ALPAD.EN.1", "ALPAD must fully enclose COVER", "ALPAD") do
  COVER.outside(ALPAD).not_inside(WAIVE)
end
ics55_check("ALPAD.EN.2", "COVER enclosure by ALPAD >= 1.5um", "ALPAD") do
  ALPAD.enclosing(COVER, 1.5).not_inside(WAIVE)
end
ics55_check("ALPAD.EN.3", "ALPAD must fully enclose CB", "ALPAD") do
  CB.outside(ALPAD).not_inside(WAIVE)
end
ics55_check("ALPAD.EN.4", "CB enclosure by ALPAD >= 1.5um", "ALPAD") do
  ALPAD.enclosing(CB, 1.5).not_inside(WAIVE)
end
ics55_check("COVER.W.1", "COVER width >= 40.0um", "COVER") do
  COVER.width(40.0).not_inside(WAIVE)
end
ics55_check("COVER.L.1", "COVER length >= 65.0um", "COVER") do
  COVER.with_bbox_max(0.0, 65.0).not_inside(WAIVE)
end
ics55_check("COVER.S.1", "COVER space >= 5.0um", "COVER") do
  COVER.space(5.0).not_inside(WAIVE)
end
