require "json"

begin
  $ics55_violation_file.close if $ics55_violation_file
rescue StandardError
end

rules = $ics55_counts.values.sort_by { |r| r["rule"] }
violations = rules.sum { |r| r["count"].to_i }
rules_with_violations = rules.count { |r| r["count"].to_i.positive? }

summary = {
  "tool" => "ics55_klayout_drc",
  "version" => "0.2.0",
  "input" => $ics55_input,
  "top" => $ics55_top,
  "report" => $ics55_report,
  "violations_file" => $ics55_violations,
  "options" => {
    "total_metal" => TOTAL_METAL,
    "top_metal" => TOP_METAL,
    "recommended" => RECOMMENDED,
    "density" => DENSITY_ON,
    "chipedge" => CHIPEDGE_ON,
    "allow_v01" => ALLOW_V01,
    "io" => IO_VOLTAGE
  },
  "rules_checked" => rules.size,
  "rules_with_violations" => rules_with_violations,
  "violations" => violations,
  "errors" => rules_with_violations,
  "rules" => rules,
  "skipped" => $ics55_skipped,
  "notes" => $ics55_notes
}

begin
  File.write($ics55_summary, JSON.pretty_generate(summary))
rescue StandardError => e
  puts "WARNING: could not write summary #{$ics55_summary}: #{e.class}: #{e.message}"
end

puts "ICS55 DRC: #{rules.size} rules, #{violations} violations, " \
     "#{rules_with_violations} rules with findings"
puts "report: #{$ics55_report}"
puts "summary: #{$ics55_summary}"
puts "violations: #{$ics55_violations}"
