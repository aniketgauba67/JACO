from __future__ import annotations

import pandas as pd
from jinja2 import Template

from src.cleaning import format_int, format_pct
from src.config import REPORT_PATH
from src.visuals import render_html_summary_table


HTML_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>JACO Regional Strategy Report</title>
  <style>
    body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f6f8fb; color: #1f2933; }
    .page { max-width: 1120px; margin: 0 auto; padding: 36px 28px 72px; }
    h1, h2, h3 { color: #12344d; margin: 0 0 10px; }
    h1 { font-size: 34px; }
    h2 { font-size: 24px; }
    h3 { font-size: 18px; margin-top: 24px; }
    p, li { font-size: 15px; line-height: 1.6; }
    .hero, .section { background: white; border-radius: 16px; padding: 28px 32px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }
    .section { margin-top: 22px; }
    .hero-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-top: 24px; }
    .metric { background: #f6f9fc; border: 1px solid #e1e7ef; border-radius: 12px; padding: 16px; }
    .metric .value { font-size: 24px; font-weight: 700; color: #0b5d7a; }
    .section-header { display: flex; align-items: baseline; justify-content: space-between; gap: 18px; border-bottom: 1px solid #d8e1ea; padding-bottom: 10px; margin-bottom: 14px; }
    .section-kicker { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #627d98; font-weight: 700; }
    .callout { background: #eef6fb; border-left: 4px solid #0b5d7a; padding: 14px 16px; border-radius: 8px; }
    .bullets { margin: 14px 0 0; padding-left: 20px; }
    .bullets li { margin-bottom: 8px; }
    .figure-card { margin-top: 24px; }
    .figure-card img { width: 100%; display: block; border-radius: 12px; border: 1px solid #dde5ee; background: white; }
    .caption { color: #52606d; margin-top: 10px; }
    .summary-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
    .summary-table th { background: #0b5d7a; color: white; padding: 10px; text-align: left; }
    .summary-table td { padding: 10px; border-bottom: 1px solid #e6edf3; vertical-align: top; }
    .summary-table tr:nth-child(even) td { background: #f8fbfd; }
    .audit { display: grid; grid-template-columns: 220px 110px 110px 1fr; gap: 10px; margin-top: 14px; font-size: 14px; }
    .audit div { padding: 10px 12px; border-radius: 10px; background: #f8fbfd; border: 1px solid #e6edf3; }
    .small { color: #6b7c93; font-size: 13px; }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>Junior Achievement of Central Ohio Regional Strategy Report</h1>
      <p>This report translates the five required JACO service regions into a concise strategy view of youth reach, school density, need concentration, outreach performance, and anchor feasibility.</p>
      <div class="hero-grid">
        <div class="metric"><div class="value">{{ scale_region }}</div><div>Largest youth reach region</div></div>
        <div class="metric"><div class="value">{{ need_region }}</div><div>Highest high-need concentration</div></div>
        <div class="metric"><div class="value">{{ outreach_region }}</div><div>Best outreach opportunity</div></div>
        <div class="metric"><div class="value">{{ tracker_match_rate }}</div><div>Tracker school-match rate</div></div>
      </div>
      <div class="callout" style="margin-top: 20px;">
        <strong>Executive Summary.</strong> {{ executive_summary }}
      </div>
      <ul class="bullets">
        {% for finding in executive_findings %}
        <li>{{ finding }}</li>
        {% endfor %}
      </ul>
    </section>

    <section class="section">
      <div class="section-header">
        <div>
          <div class="section-kicker">Overview</div>
          <h2>Project Overview</h2>
        </div>
      </div>
      <p>The analysis answers six planning questions for JACO: how to group counties around anchor counties, which clusters maximize youth reach, where the school inventory is deepest, where high-need schools are concentrated, what the cold-call tracker says about outreach traction, whether the anchor model looks feasible on a one-hour proxy, and how to turn all of that into a practical priority order.</p>
      <p>Data sources used: county population data from <code>JACO.csv</code>, Ohio school inventory from the NCES file, ZIP-to-tract mapping from <code>ZIP_TRACT_122025.xlsx</code>, high-need school data from the FY25 SSI workbook, and school outreach activity from the JA cold-call tracker.</p>
    </section>

    <section class="section">
      <div class="section-header">
        <div>
          <div class="section-kicker">Quality Checks</div>
          <h2>Methodology and Join Validation</h2>
        </div>
      </div>
      <ul>
        <li>Population analysis uses the latest county-level <code>YEAR</code> code in the source and youth AGEGRP values {{ youth_age_groups }}.</li>
        <li>School assignment uses ZIP-to-county mapping with the strongest available ratio field, then maps counties into the five fixed JACO service regions.</li>
        <li>High-need matching prioritizes exact Ohio building IRN matches, then exact unique normalized-name matches, before using cautious normalized-name fallback logic.</li>
        <li>Cold-call matching standardizes organization names and counties, then defines positive outreach schools strictly as tracker rows where <code>Outcome = Interested</code>.</li>
        <li>The 1-hour screen uses county centroid distance from each anchor county as a transparent proxy because no drive-time API is used.</li>
      </ul>
      <div class="audit">
        <div><strong>Step</strong></div><div><strong>Matched</strong></div><div><strong>Rate</strong></div><div><strong>Notes</strong></div>
        {% for row in join_audit_rows %}
        <div>{{ row.step }}</div><div>{{ row.matched }}</div><div>{{ row.rate }}</div><div>{{ row.notes }}</div>
        {% endfor %}
      </div>
      <p class="small">High-need match summary: {{ high_need_match_summary }}. Tracker match summary: {{ tracker_match_summary }}.</p>
      <p class="small">{{ limitations_summary }}</p>
    </section>

    <section class="section">
      <div class="section-header">
        <div>
          <div class="section-kicker">Tracker Audit</div>
          <h2>Positive-Response Classification Audit</h2>
        </div>
      </div>
      <p>Positive outreach schools are defined as tracker rows where <code>Outcome = Interested</code>. The audit below shows all observed normalized outcome values, their counts, and which value is treated as positive.</p>
      <div class="figure-card">
        <h3>Observed Outcome Values</h3>
        {{ tracker_value_audit_html }}
      </div>
      <div class="figure-card">
        <h3>Positive-Response Rule</h3>
        {{ tracker_response_rules_html }}
      </div>
    </section>

    {% for section in sections %}
    <section class="section">
      <div class="section-header">
        <div>
          <div class="section-kicker">{{ section.kicker }}</div>
          <h2>{{ section.title }}</h2>
        </div>
      </div>
      <p>{{ section.intro }}</p>
      {% for figure in section.figures %}
      <div class="figure-card">
        <h3>{{ figure.title }}</h3>
        <img src="{{ figure.path }}" alt="{{ figure.title }}">
        <p class="caption">{{ figure.caption }}</p>
      </div>
      {% endfor %}
      {% if section.table_html %}
      <div class="figure-card">
        <h3>{{ section.table_title }}</h3>
        {{ section.table_html }}
      </div>
      {% endif %}
      {% if section.limitations %}
      <p class="small"><strong>Limitations.</strong> {{ section.limitations }}</p>
      {% endif %}
    </section>
    {% endfor %}

    <section class="section">
      <div class="section-header">
        <div>
          <div class="section-kicker">Recommendation</div>
          <h2>Final Recommendations</h2>
        </div>
      </div>
      <p>{{ recommendation }}</p>
      <ul>
        <li><strong>Best region for scale:</strong> {{ scale_region }} with {{ scale_youth }} youth and {{ scale_schools }} schools.</li>
        <li><strong>Best region for concentrated need:</strong> {{ need_region }} with a {{ need_share }} high-need school share.</li>
        <li><strong>Best region for outreach opportunity:</strong> {{ outreach_region }} with a {{ outreach_rate }} Interested-response rate.</li>
        <li><strong>1-hour proxy feasibility:</strong> {{ feasibility_status }}</li>
      </ul>
      <p class="small">Report generated automatically by <code>python run_pipeline.py</code>.</p>
    </section>
  </div>
</body>
</html>
"""
)


def render_report(region_summary: pd.DataFrame, figure_paths: dict[str, str], metadata: dict[str, object]) -> None:
    scale_leader = region_summary.sort_values("youth_population", ascending=False).iloc[0]
    need_leader = region_summary.sort_values("high_need_share", ascending=False).iloc[0]
    outreach_leader = region_summary[region_summary["outreach_records"].fillna(0) > 0].sort_values(
        ["positive_response_rate", "outreach_records"], ascending=[False, False]
    ).iloc[0]
    tracker_match_rate = format_pct(metadata["tracker"]["school_match_rate"])
    tracker_region_rate = format_pct(metadata["tracker"]["region_assignment_rate"])

    matched_high_need = (
        metadata["high_need_match_summary"]["school_records"].sum()
        - metadata["high_need_match_summary"].loc[
            metadata["high_need_match_summary"]["match_method"] == "unmatched", "school_records"
        ].sum()
    )
    total_high_need_base = metadata["high_need_match_summary"]["school_records"].sum()
    high_need_total_match_rate = format_pct(matched_high_need / total_high_need_base)

    feasibility_pairs = [
        f"{row.region}: {'feasible' if bool(row.feasible_1hr_proxy) else 'stretch'}"
        for row in region_summary[["region", "feasible_1hr_proxy"]].itertuples(index=False)
    ]
    feasibility_status = "; ".join(feasibility_pairs)

    executive_summary = (
        f"{scale_leader['region']} is the clear scale leader with {format_int(scale_leader['youth_population'])} youth and "
        f"{format_int(scale_leader['total_schools'])} mapped schools, while {need_leader['region']} has the highest "
        f"high-need share at {format_pct(need_leader['high_need_share'])}. {outreach_leader['region']} currently shows the strongest "
        f"outreach opportunity at {format_pct(outreach_leader['positive_response_rate'])}. Positive outreach is defined only as tracker rows where Outcome equals Interested."
    )
    executive_findings = [
        f"{scale_leader['region']} leads on youth reach with {format_int(scale_leader['youth_population'])} youth.",
        f"{scale_leader['region']} also has the largest school inventory at {format_int(scale_leader['total_schools'])} schools.",
        f"{need_leader['region']} has the highest identified high-need concentration at {format_pct(need_leader['high_need_share'])}.",
        f"{outreach_leader['region']} has the strongest outreach opportunity based on Interested outcomes at {format_pct(outreach_leader['positive_response_rate'])}.",
        f"Tracker-to-school matching is {tracker_match_rate}, strong enough for region-level outreach interpretation.",
        f"High-need matching is more limited at {high_need_total_match_rate}, so those results should be read as directional rather than exhaustive.",
    ]
    recommendation = (
        f"Start with {scale_leader['region']} as the flagship region because it leads both on reachable youth and school inventory. "
        f"Pair that with a focused second-wave strategy in {need_leader['region']} to concentrate on high-need school partnerships. "
        f"For near-term outreach opportunity, {outreach_leader['region']} stands out on Interested-response rate. "
        f"Feasibility proxy status: {feasibility_status}."
    )
    limitations_summary = (
        f"Limitations: the NCES extract does not provide usable school coordinates, so the school-point map uses approximate county-centroid placement rather than true school locations. "
        f"Tracker rows were assigned to JACO regions at a {tracker_region_rate} rate, and rows outside the grouped counties remain visible as unmatched limitations rather than being forced into a school-level view."
    )

    join_audit_rows = [
        {
            "step": row.step,
            "matched": f"{int(row.matched_records):,} / {int(row.total_records):,}",
            "rate": format_pct(row.match_rate),
            "notes": row.notes,
        }
        for row in metadata["join_audit_summary"].itertuples()
    ]
    tracker_value_audit_html = metadata["tracker_value_audit"].to_html(index=False, classes=["summary-table"], border=0)
    tracker_response_rules_html = metadata["tracker_response_rules"].to_html(index=False, classes=["summary-table"], border=0)

    sections = [
        {
            "kicker": "Footprint",
            "title": "JACO Regional Grouping Strategy",
            "intro": "This map shows the five fixed county clusters and their anchor counties. It defines the service geography used throughout the rest of the analysis.",
            "figures": [
                {
                    "title": "Ohio County Map with JACO Regions",
                    "path": figure_paths["region_map"],
                    "caption": "Each county is assigned to one of the five required JACO regions, and stars identify the anchor counties. This is the operating footprint for mobile-unit planning.",
                },
            ],
            "table_title": "",
            "table_html": None,
            "limitations": "The regions are fixed to the five required JACO groupings rather than optimized algorithmically from drive-time data.",
        },
        {
            "kicker": "Reach",
            "title": "Youth Population and Reach",
            "intro": "These figures show where the largest youth and total population bases sit. Together they identify which regions maximize potential mobile-unit reach.",
            "figures": [
                {
                    "title": "County Population Heatmap",
                    "path": figure_paths["county_population_heatmap"],
                    "caption": "This county choropleth shows the statewide population pattern and provides context for where the JACO counties sit inside Ohio.",
                },
                {
                    "title": "County Youth Population Heatmap",
                    "path": figure_paths["youth_population_heatmap"],
                    "caption": "Youth population uses AGEGRP 2-4, corresponding to ages 5-19 in the source layout. This is the clearest county-level view of potential student reach.",
                },
                {
                    "title": "Youth Population by Region",
                    "path": figure_paths["youth_by_region"],
                    "caption": "Group 1 is much larger than the rest of the portfolio on youth reach, making it the strongest first market if broad exposure is the priority.",
                },
            ],
            "table_title": "",
            "table_html": None,
            "limitations": "Population estimates rely on the latest YEAR code present in the source file and the AGEGRP structure available there, rather than a labeled calendar year field.",
        },
        {
            "kicker": "Schools",
            "title": "Schools and Outreach Potential",
            "intro": f"School inventory matters because the mobile-unit strategy also depends on partnership targets. Positive outreach schools are defined as tracker rows where Outcome = Interested, and {format_int(metadata['tracker']['positive_matched_schools'])} matched positive schools are highlighted on the map below.",
            "figures": [
                {
                    "title": "Total Schools by Region",
                    "path": figure_paths["schools_by_region"],
                    "caption": "The Columbus Core dominates school count, which matters for both outreach capacity and partnership depth.",
                },
                {
                    "title": "School Distribution & Outreach Visualization",
                    "path": figure_paths["schools_map"],
                    "caption": metadata["school_points_caption"],
                },
                {
                    "title": "Outreach Activity Map",
                    "path": figure_paths["outreach_map"],
                    "caption": metadata["outreach_map_caption"],
                },
            ],
            "table_title": "Schools and Outreach Summary",
            "table_html": render_html_summary_table(
                region_summary[
                    ["region", "anchor_county", "total_schools", "outreach_records", "positive_responses", "school_match_rate_within_region"]
                ]
            ),
            "limitations": "Because the NCES file does not include usable latitude/longitude fields, the school map uses approximate county-centroid placement with deterministic jitter instead of true school coordinates. Outreach highlighting depends on school-name matching from the tracker and therefore reflects matched Interested rows only.",
        },
        {
            "kicker": "Feasibility",
            "title": "1-Hour Radius Feasibility Check",
            "intro": "This section checks whether each anchor county appears to cover its assigned counties within a reasonable one-hour proxy. Because no drive-time API is used, the test relies on centroid-to-centroid distance and should be read as a planning screen rather than a route model.",
            "figures": [
                {
                    "title": "Anchor Feasibility by Region",
                    "path": figure_paths["one_hour_radius_feasibility"],
                    "caption": "Each bar shows the farthest county-centroid distance from the anchor county inside that region. Regions entirely below the 50-mile proxy threshold appear more feasible for a one-hour anchor model.",
                },
            ],
            "table_title": "Feasibility Summary",
            "table_html": render_html_summary_table(
                region_summary[
                    ["region", "anchor_county", "max_anchor_distance_miles", "avg_anchor_distance_miles", "counties_outside_proxy_radius", "feasible_1hr_proxy"]
                ]
            ),
            "limitations": "The feasibility screen uses centroid distance rather than true road-network travel time, so it is best treated as a transparent proxy rather than a definitive operating test.",
        },
        {
            "kicker": "Need",
            "title": "High-Need Analysis",
            "intro": "The FY25 SSI workbook highlights a subset of high-need schools. These charts show where that need is most concentrated across the five required regions.",
            "figures": [
                {
                    "title": "High-Need Schools by Region",
                    "path": figure_paths["high_need_by_region"],
                    "caption": "This compares total schools against the number of high-need schools identified through the SSI building allocation file.",
                },
                {
                    "title": "High-Need Share by Region",
                    "path": figure_paths["high_need_share_by_region"],
                    "caption": "The share view controls for size and makes Southern Corridor stand out most clearly on concentration of identified need.",
                },
            ],
            "table_title": "Region Summary Table",
            "table_html": render_html_summary_table(
                region_summary[
                    ["region", "anchor_county", "counties_in_region", "youth_population", "total_schools", "high_need_schools", "high_need_share", "priority_label"]
                ]
            ),
            "limitations": "High-need results come from the FY25 SSI building allocation file and currently match only a subset of Ohio schools, so the need analysis should be treated as directional rather than exhaustive.",
        },
        {
            "kicker": "Tradeoff",
            "title": "Final Tradeoff View",
            "intro": "The final tradeoff chart positions each region by scale and need at the same time. It is the clearest bridge from descriptive analysis to planning recommendation.",
            "figures": [
                {
                    "title": "Scale vs Need Tradeoff",
                    "path": figure_paths["strategy_tradeoff_matrix"],
                    "caption": "Bubble size represents total schools, the x-axis captures youth reach, and the y-axis captures high-need concentration.",
                },
            ],
            "table_title": "",
            "table_html": None,
            "limitations": "The tradeoff view combines the available reach and high-need measures, but it does not yet model travel time, staffing constraints, or partnership conversion rates.",
        },
    ]

    html = HTML_TEMPLATE.render(
        scale_region=scale_leader["region"],
        scale_youth=format_int(scale_leader["youth_population"]),
        scale_schools=format_int(scale_leader["total_schools"]),
        need_region=need_leader["region"],
        need_share=format_pct(need_leader["high_need_share"]),
        outreach_region=outreach_leader["region"],
        outreach_rate=format_pct(outreach_leader["positive_response_rate"]),
        feasibility_status=feasibility_status,
        tracker_match_rate=tracker_match_rate,
        executive_summary=executive_summary,
        executive_findings=executive_findings,
        recommendation=recommendation,
        youth_age_groups=", ".join(str(code) for code in metadata["population"]["selected_youth_age_groups"]),
        high_need_match_summary=", ".join(f"{row.match_method}: {int(row.school_records)}" for row in metadata["high_need_match_summary"].itertuples()),
        tracker_match_summary=", ".join(f"{row.match_method}: {int(row.rows)}" for row in metadata["tracker_match_summary"].itertuples()),
        join_audit_rows=join_audit_rows,
        limitations_summary=limitations_summary,
        tracker_value_audit_html=tracker_value_audit_html,
        tracker_response_rules_html=tracker_response_rules_html,
        sections=sections,
    )
    REPORT_PATH.write_text(html, encoding="utf-8")
