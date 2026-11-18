# Density and slot checks (100um x 100um window, 50um step, after Calibre).

DENSITY_WINDOW_UM = 100
DENSITY_STEP_UM = 50

def ics55_density(rule_prefix, description_name, layer, layer_name, min_d, max_d)
  return unless DENSITY_ON
  window = DENSITY_WINDOW_UM.um
  step = DENSITY_STEP_UM.um
  exclusions = IND + GRID_AREA + WAIVE

  if min_d
    ics55_check("#{rule_prefix}.D.min", "#{description_name} density >= #{min_d}",
                layer_name) do
      layer.with_density(0.0..min_d, tile_size(window), tile_step(step))
           .not_inside(exclusions)
    end
  end
  if max_d
    ics55_check("#{rule_prefix}.D.max", "#{description_name} density <= #{max_d}",
                layer_name) do
      layer.with_density(max_d..1.0, tile_size(window), tile_step(step))
           .not_inside(exclusions)
    end
  end
end

THIN_METAL.times do |idx|
  ics55_density(METAL_NAMES[idx], METAL_NAMES[idx],
                METALS[idx] + METAL_DUMS[idx], METAL_NAMES[idx], 0.10, 0.80)
end

ics55_density("AA", "AA (including dummy)", AA_ALL, "ACT", 0.20, 0.80)
ics55_density("PO", "PO (including dummy)", PO_ALL, "POLY", 0.20, 0.65)

if T4M2_ON
  T4M2_ALL = T4M2 + T4M2_dm
  ics55_density("T4M2", "T4M2 (including dummy)", T4M2_ALL, "T4M2", 0.20, 0.85)

  # Slot rules for the thick top metal (Calibre SL_W_1_L_1/SL_S_1).
  T4M2_SLOT = T4M2_slot
  ics55_check("T4M2.SL.W.1", "T4M2 slot width >= 2.0um", "T4M2") do
    T4M2_SLOT.width(2.0).not_inside(WAIVE)
  end
  ics55_check("T4M2.SL.L.1", "T4M2 slot length >= 4.5um", "T4M2") do
    T4M2_SLOT.with_bbox_max(0.0, 4.5).not_inside(WAIVE)
  end
  ics55_check("T4M2.SL.S.1", "T4M2 slot space >= 3.0um", "T4M2") do
    T4M2_SLOT.space(3.0).not_inside(WAIVE)
  end
end
