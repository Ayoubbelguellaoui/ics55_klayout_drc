# Front-end rules ported from ICsprout_CalDRC_55LLULP1233_REV1_0_OS.drc.

# --- DNW ---------------------------------------------------------------
ics55_check("DNW.W.1", "DNW width >= 3.00um", "DNW") do
  DNWL.width(3.0).not_inside(WAIVE)
end
ics55_check("DNW.S.1", "Space between two DNWs >= 3.50um", "DNW") do
  DNWL.space(3.5).not_inside(WAIVE)
end
ics55_check("DNW.EN.1", "NW enclosure of DNW >= 1.00um", "NW1") do
  NW.enclosing(DNWL, 1.0)
end
ics55_check("DNW.EN.1b", "DNW must be fully inside NW", "DNW") do
  DNWL.outside(NW)
end
ics55_check("DNW.O.1", "Overlap of NW and DNW >= 0.40um", "DNW") do
  (NW & DNWL).width(0.4)
end

# --- ACT ---------------------------------------------------------------
ics55_check("ACT.W.1", "AA width >= 0.08um", "ACT") do
  AA.width(0.08).not_inside(WAIVE)
end
ics55_check("ACT.S.1", "Space between two AAs >= 0.11um", "ACT") do
  AA.space(0.11).not_inside(SRAM).not_inside(IND).not_inside(WAIVE)
end
ics55_check("ACT.A.1", "AA area >= 0.0384um2", "ACT") do
  AA.with_area(0.0, 0.0384).not_inside(WAIVE)
end
ics55_check("ACT.R.1", "AA must be fully covered by (NP OR PP), except NW resistor", "ACT") do
  AA.outside(NP + PP).not_inside(NW1_res).not_inside(WAIVE)
end
ics55_check("ACT.EN.1", "Enclosure of N+AA by NW >= 0.15um", "NW1") do
  NW.enclosing(AA & NP, 0.15)
end
ics55_check("ACT.EN.2", "Enclosure of P+AA by NW >= 0.15um", "NW1") do
  NW.enclosing(AA & PP, 0.15)
end

# --- NW1 ---------------------------------------------------------------
ics55_check("NW1.W.1", "NW1 width >= 0.47um", "NW1") do
  NW.width(0.47).not_inside(WAIVE)
end
ics55_check("NW1.S.1", "Space between two NW1s >= 0.47um", "NW1") do
  NW.space(0.47).not_inside(WAIVE)
end
ics55_check("NW1.A.1", "NW1 area >= 0.30um2", "NW1") do
  NW.with_area(0.0, 0.30).not_inside(WAIVE)
end

# --- PSUB --------------------------------------------------------------
ics55_check("PSUB.W.1", "PSUB width >= 0.47um", "PSUB") do
  PSUB.width(0.47).not_inside(WAIVE)
end
ics55_check("PSUB.S.1", "Space between two PSUBs >= 0.47um", "PSUB") do
  PSUB.space(0.47).not_inside(WAIVE)
end
ics55_check("PSUB.A.1", "PSUB area >= 0.60um2", "PSUB") do
  PSUB.with_area(0.0, 0.60).not_inside(WAIVE)
end

# --- VT layers ---------------------------------------------------------
{
  "NVT1" => NVT1, "PVT1" => PVT1, "NVT3" => NVT3, "PVT3" => PVT3
}.each do |name, layer|
  ics55_check("#{name}.W.1", "#{name} width >= 0.18um", name) do
    layer.width(0.18).not_inside(WAIVE)
  end
  ics55_check("#{name}.S.1", "Space between two #{name}s >= 0.18um", name) do
    layer.space(0.18).not_inside(WAIVE)
  end
  ics55_check("#{name}.A.1", "#{name} area >= 0.18um2", name) do
    layer.with_area(0.0, 0.18).not_inside(WAIVE)
  end
end

# --- DG / TG -----------------------------------------------------------
ics55_check("DG.W.1", "DG width >= 0.47um", "DGOX") do
  DG.width(0.47).not_inside(WAIVE)
end
ics55_check("DG.S.1", "Space between two DGs >= 0.47um", "DGOX") do
  DG.space(0.47).not_inside(WAIVE)
end
ics55_check("TG.W.1", "TG width >= 0.47um", "TGOX") do
  TG.width(0.47).not_inside(WAIVE)
end
ics55_check("TG.S.1", "Space between two TGs >= 0.47um", "TGOX") do
  TG.space(0.47).not_inside(WAIVE)
end
ics55_check("DG.EN.1", "NW extension to DG >= 0.47um", "NW1") do
  NW.enclosing(DG, 0.47)
end
ics55_check("TG.EN.1", "NW extension to TG >= 0.47um", "NW1") do
  NW.enclosing(TG, 0.47)
end
ics55_check("DG.O.1", "Overlap of DG and NW >= 0.47um", "DGOX") do
  (DG & NW).width(0.47)
end
ics55_check("TG.O.1", "Overlap of TG and NW >= 0.47um", "TGOX") do
  (TG & NW).width(0.47)
end

# --- PO ----------------------------------------------------------------
ics55_check("PO.W.1", "PO width >= 0.06um", "POLY") do
  PO.width(0.06).not_inside(WAIVE)
end
ics55_check("PO.S.1", "Space between two POs >= 0.12um", "POLY") do
  PO.space(0.12).not_inside(IND).not_inside(WAIVE)
end
ics55_check("PO.A.1", "PO area >= 0.04um2", "POLY") do
  PO.with_area(0.0, 0.04).not_inside(WAIVE)
end
ics55_check("PO.A.2", "PO enclosed area >= 0.09um2", "POLY") do
  PO.holes.with_area(0.0, 0.09).not_inside(WAIVE)
end
ics55_check("PO.R.2", "PO must be enclosed by NP and/or PP", "POLY") do
  PO.outside(NP + PP).not_inside(WAIVE)
end

# --- NP ----------------------------------------------------------------
ics55_check("NP.W.1", "NP width >= 0.18um", "NP") do
  NP.width(0.18).not_inside(WAIVE)
end
ics55_check("NP.S.1", "Space between two NPs >= 0.18um", "NP") do
  NP.space(0.18).not_inside(WAIVE)
end
ics55_check("NP.A.1", "NP area >= 0.12um2", "NP") do
  NP.with_area(0.0, 0.12).not_inside(WAIVE)
end
ics55_check("NP.EN.1", "AA enclosure by NP >= 0.02um", "NP") do
  NP.enclosing(AA, 0.02).not_inside(SRAM)
end
ics55_check("NP.EN.2", "N+AA enclosure by NP >= 0.12um", "NP") do
  NP.enclosing(AA & NP, 0.12).not_inside(SRAM)
end
ics55_check("NP.EN.3", "NP enclosure of PO >= 0.15um", "NP") do
  NP.enclosing(PO & NP, 0.15)
end

# --- PP ----------------------------------------------------------------
ics55_check("PP.W.1", "PP width >= 0.18um", "PP") do
  PP.width(0.18).not_inside(WAIVE)
end
ics55_check("PP.S.1", "Space between two PPs >= 0.18um", "PP") do
  PP.space(0.18).not_inside(WAIVE)
end
ics55_check("PP.A.1", "PP area >= 0.12um2", "PP") do
  PP.with_area(0.0, 0.12).not_inside(WAIVE)
end
ics55_check("PP.EN.1", "P+AA enclosure by PP >= 0.02um", "PP") do
  PP.enclosing(AA & PP, 0.02).not_inside(SRAM)
end
ics55_check("PP.EN.2", "P+AA inside NW enclosure by PP >= 0.12um", "PP") do
  PP.enclosing(AA & PP & NW, 0.12).not_inside(SRAM)
end
ics55_check("PP.O.1", "PP overlap with NP is not allowed", "PP") do
  (PP & NP).not_inside(WAIVE)
end

# --- SAB ---------------------------------------------------------------
ics55_check("SAB.W.1", "SAB width >= 0.42um", "SAB") do
  SAB.width(0.42).not_inside(WAIVE)
end
ics55_check("SAB.S.1", "Space between two SABs >= 0.42um", "SAB") do
  SAB.space(0.42).not_inside(WAIVE)
end
ics55_check("SAB.S.2", "Space between SAB and AA >= 0.21um", "SAB") do
  SAB.separation(AA, 0.21).not_inside(WAIVE)
end
ics55_check("SAB.EN.1", "SAB extension outside of AA >= 0.21um", "SAB") do
  SAB.enclosing(AA, 0.21).not_inside(WAIVE)
end
ics55_check("SAB.EN.2", "AA extension outside of SAB >= 0.21um", "ACT") do
  AA.enclosing(SAB, 0.21).not_inside(WAIVE)
end
ics55_check("SAB.R.1", "SAB overlap GATE is not allowed except ESD MOS", "SAB") do
  (SAB & PO).not_inside(ESD_EXEMPT).not_inside(WAIVE)
end
ics55_check("SAB.A.1", "SAB area >= 0.8um2", "SAB") do
  SAB.with_area(0.0, 0.8).not_inside(WAIVE)
end

# --- CT ----------------------------------------------------------------
ics55_check("CT.W.1", "Fixed CT width (square shape) = 0.09um", "CT") do
  CT.not_inside(SRAM + EFUSE + GRID_AREA + WAIVE).width(0.09)
end
ics55_check("CT.W.2", "Fixed CT area = 0.09um x 0.09um", "CT") do
  CT.not_inside(SRAM + EFUSE + GRID_AREA + WAIVE).with_area(0.0082, nil)
end
ics55_check("CT.S.1", "Space between two contacts >= 0.11um", "CT") do
  CT.space(0.11).not_inside(SRAM).not_inside(WAIVE)
end
ics55_check("CT.S.3", "Space between AA and contact on POLY >= 0.065um", "CT") do
  (CT & PO).separation(AA, 0.065).not_inside(WAIVE)
end
ics55_check("CT.R.1", "CT is not allowed to land on GATE", "CT") do
  (CT & PO & AA).not_inside(SRAM).not_inside(WAIVE)
end
ics55_check("CT.R.2", "CT is not allowed to interact SAB", "CT") do
  CT.interacting(SAB).not_inside(SRAM + EFUSE).not_inside(WAIVE)
end
ics55_check("CT.R.3", "45 degree CT is not allowed", "CT") do
  # Only orthogonal CT edges are allowed; unlike GEO.ANG.CT a 45 deg edge is
  # not permitted here. Mirrors the deck's angle bands (edges normalize to 0-90).
  edges = CT.edges
  orthogonal = edges.with_angle(0.0..0.1) + edges.with_angle(89.9..90.1)
  (edges - orthogonal).not_inside(SRINGBLK).not_inside(WAIVE)
end
ics55_check("CT.EN.1", "CT must be covered by M1 and (AA OR POLY)", "CT") do
  CT.outside(M1 & (AA + PO)).not_inside(SRAM).not_inside(WAIVE)
end
ics55_check("CT.EN.2", "CT enclosure by AA >= 0.015um", "CT") do
  AA.enclosing(CT & AA, 0.015).not_inside(SRAM).not_inside(WAIVE)
end
ics55_check("CT.EN.3", "CT must be fully covered by M1", "CT") do
  CT.outside(M1).not_inside(SRAM).not_inside(WAIVE)
end
ics55_check("CT.EN.4d", "Enclosure by M1 >= 0.04um when M1 width is > 1um", "CT") do
  # WITH WIDTH > 1: only polygons that survive a 0.5um undersize are wider than 1um.
  wide = M1.interacting(M1.sized(-0.5))
  M1.enclosing(CT.not_outside(wide), 0.04).not_inside(WAIVE)
end
