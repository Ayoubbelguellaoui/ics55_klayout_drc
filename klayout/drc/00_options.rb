# ICS55 full-mask DRC — options and shared helpers.
# Values come from KLayout -rd switches; defaults match the foundry Calibre deck.

require "json"

def ics55_global(name)
  var = "$#{name}"
  eval("defined?(#{var}) ? #{var} : nil")
end

$ics55_input       = ics55_global("input").to_s
$ics55_top         = ics55_global("top").to_s
$ics55_report      = ics55_global("report").to_s
$ics55_report      = "drc.lyrdb" if $ics55_report.empty?
$ics55_summary     = ics55_global("summary").to_s
$ics55_summary     = "drc_summary.json" if $ics55_summary.empty?
$ics55_violations  = ics55_global("violations").to_s
$ics55_violations  = "drc_violations.jsonl" if $ics55_violations.empty?

ICS55_OPTION_NAMES = %w[
  total_metal top_metal T2V1_T2M1 T2V2_T2M2 T4V1_T4M1 T4V2_T4M2 T8V1_T8M1 T8V2_T8M2
  recommended density latchup dup metal_slot mom esd poly_efuse allow_v01 chipedge io
]
$ics55_opts = {}
ICS55_OPTION_NAMES.each { |name| $ics55_opts[name] = ics55_global(name) }

def ics55_int(name, default)
  raw = $ics55_opts[name]
  raw.nil? || raw.to_s.empty? ? default : raw.to_i
end

def ics55_bool(name, default)
  raw = $ics55_opts[name]
  return default if raw.nil? || raw.to_s.empty?
  %w[1 true yes on].include?(raw.to_s.downcase)
end

TOTAL_METAL  = ics55_int("total_metal", 6)
TOP_METAL    = ics55_int("top_metal", 1)
RECOMMENDED  = ics55_bool("recommended", false)
DENSITY_ON   = ics55_bool("density", true)
ALLOW_V01    = ics55_bool("allow_v01", false)
CHIPEDGE_ON  = ics55_bool("chipedge", true)
IO_VOLTAGE   = ics55_int("io", 1833)

T2M1_ON = ics55_int("T2V1_T2M1", 0) == 1
T2M2_ON = ics55_int("T2V2_T2M2", 0) == 1
T4M1_ON = ics55_int("T4V1_T4M1", 0) == 1
T4M2_ON = ics55_int("T4V2_T4M2", 0) == 1
T8M1_ON = ics55_int("T8V1_T8M1", 0) == 1
T8M2_ON = ics55_int("T8V2_T8M2", 0) == 1

$ics55_counts = {}
$ics55_skipped = []
$ics55_notes = []
$ics55_violation_file = begin
  File.open($ics55_violations, "w")
rescue StandardError => e
  $ics55_notes << "violations file disabled: #{e.class}: #{e.message}"
  nil
end

def ics55_box(shape)
  bb = shape.bbox
  [
    (bb.left.to_f / 1000.0).round(6),
    (bb.bottom.to_f / 1000.0).round(6),
    (bb.right.to_f / 1000.0).round(6),
    (bb.top.to_f / 1000.0).round(6)
  ]
end

# Collects a rule result, writes every marker to the JSONL stream and sends
# the rule to the RDB. layer_name is the PDK layer (MET1, VIA1, ACT, ...).
def ics55_out(rule, description, layer, layer_name)
  count = 0
  samples = []
  begin
    layer.data.each do |shape|
      count += 1
      begin
        box = ics55_box(shape)
        samples << box if samples.size < 20
        if $ics55_violation_file
          $ics55_violation_file.puts(
            JSON.generate("type" => rule, "layer" => layer_name, "bbox" => box)
          )
        end
      rescue StandardError
        # A shape without a bbox (text, malformed edge pair) is still counted.
      end
    end
  rescue StandardError => e
    $ics55_notes << "#{rule}: marker collection failed: #{e.class}: #{e.message}"
  end

  $ics55_counts[rule] = {
    "rule" => rule,
    "description" => description,
    "class" => "error",
    "layer" => layer_name,
    "count" => count,
    "samples" => samples
  }
  begin
    layer.output(rule, description)
  rescue StandardError => e
    $ics55_notes << "#{rule}: report output failed: #{e.class}: #{e.message}"
  end
  count
end

# Runs a rule block and records API errors instead of aborting the deck.
# Clean rules are recorded too, so reports can distinguish "checked and clean"
# from "not checked".
def ics55_check(rule, description, layer_name)
  layer = yield
  ics55_out(rule, description, layer, layer_name)
rescue StandardError => e
  $ics55_skipped << "#{rule}: #{e.class}: #{e.message}"
end
