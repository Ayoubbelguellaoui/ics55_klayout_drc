# Special rules gated by the foundry switches.

if CHIPEDGE_ON
  unless CHIPBLK.is_empty?
    CHIPEDGE_LAYERS = {
      "ACT" => AA, "NW1" => NW, "PSUB" => PSUB, "DGOX" => DG, "TGOX" => TG,
      "POLY" => PO, "NP" => NP, "PP" => PP, "SAB" => SAB, "CT" => CT,
      "MET1" => M1, "MET2" => M2, "MET3" => M3, "MET4" => M4, "MET5" => M5
    }
    CHIPEDGE_LAYERS.each do |name, layer|
      ics55_check("CHIPEDGE.#{name}", "#{name} must be inside CHIPBLK", name) do
        layer.outside(CHIPBLK).not_inside(GRID_AREA + WAIVE)
      end
    end
  end
end

if ics55_bool("latchup", true)
  $ics55_notes << "LATCHUP: connectivity checks require an LVS netlist; deferred to a later phase"
end

if ics55_bool("mom", true)
  $ics55_notes << "MOM: marker-based MOM checks land in a later phase"
end

if ics55_bool("esd", true)
  $ics55_notes << "ESD: marker-based ESD topology checks land in a later phase"
end

if ics55_bool("dup", true)
  $ics55_notes << "DUP: dummy-fill spacing checks land in a later phase"
end

if ics55_bool("poly_efuse", true)
  ics55_check("EFUSE.R.1", "FUSEALL must interact EFUSEALL", "FUSEALL") do
    FUSE.outside(EFUSE)
  end
  ics55_check("EFUSE.R.2", "FUSEALL must fully cover EFUSEALL", "EFUSEALL") do
    EFUSE.outside(FUSE)
  end
  ics55_check("EFUSE.R.3", "EFUSEALL must interact POEFUSEBLK", "EFUSEALL") do
    EFUSE.outside(POEFUSEBLK)
  end
  ics55_check("EFUSE.R.4", "EFUSEALL must fully cover POEFUSEBLK", "POEFUSEBLK") do
    POEFUSEBLK.outside(EFUSE)
  end
end

if ics55_bool("allow_v01", false)
  $ics55_notes << "ALLOW_V01=YES: V0/V1 via doubling checks are relaxed"
end
