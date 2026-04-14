from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template
from plotly.offline import get_plotlyjs

from src.analysis import PipelineArtifacts
from src.cleaning import format_int, format_pct
from src.config import FIGURES_DIR, OUTPUTS_DIR, REGION_COLORS, REPORT_PATH


HTML_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JACO Ohio Regional Analysis</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --card: #ffffff;
      --ink: #172b3a;
      --muted: #5b7083;
      --line: #d9e2ec;
      --brand: #0b5d7a;
      --brand-soft: #e7f2f7;
      --accent: #1f9d55;
      --danger: #d94841;
      --shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); font-family: "Segoe UI", Tahoma, sans-serif; }
    .page { max-width: 1280px; margin: 0 auto; padding: 28px 24px 56px; }
    .hero, .section { background: var(--card); border-radius: 18px; box-shadow: var(--shadow); }
    .hero { padding: 30px 32px; }
    .section { margin-top: 22px; padding: 28px 30px; scroll-margin-top: 24px; }
    h1, h2, h3 { margin: 0; color: #12344d; }
    h1 { font-size: 34px; line-height: 1.2; }
    h2 { font-size: 24px; line-height: 1.3; }
    h3 { font-size: 17px; margin-bottom: 10px; }
    p, li { font-size: 15px; line-height: 1.65; color: var(--ink); }
    .lede { max-width: 980px; color: var(--muted); margin-top: 12px; }
    .kicker { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #627d98; font-weight: 700; margin-bottom: 10px; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-top: 22px; }
    .metric-card { padding: 16px; border: 1px solid var(--line); border-radius: 14px; background: #f9fbfd; }
    .metric-card .label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #627d98; font-weight: 700; }
    .metric-card .value { font-size: 25px; font-weight: 700; margin-top: 8px; color: var(--brand); }
    .metric-card .note { font-size: 13px; color: var(--muted); margin-top: 6px; }
    .callout { margin-top: 22px; padding: 16px 18px; background: var(--brand-soft); border-left: 4px solid var(--brand); border-radius: 10px; }
    .section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; padding-bottom: 12px; border-bottom: 1px solid var(--line); margin-bottom: 16px; }
    .section-intro { color: var(--muted); max-width: 1000px; margin-bottom: 18px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    .section-nav { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
    .section-nav a { text-decoration: none; color: var(--brand); background: #f7fafc; border: 1px solid var(--line); padding: 8px 12px; border-radius: 999px; font-size: 13px; font-weight: 700; }
    .figure-grid { display: grid; gap: 16px; }
    .figure-grid.grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .figure-grid.grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .figure-card, .table-card, .note-card { border: 1px solid var(--line); border-radius: 16px; background: #ffffff; padding: 16px; margin-top: 16px; }
    .figure-card:first-child, .table-card:first-child, .note-card:first-child { margin-top: 0; }
    .figure-caption { margin-top: 10px; font-size: 13px; color: var(--muted); }
    .figure-wrap { min-height: 420px; }
    .tab-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .tab-button { border: 1px solid var(--line); background: #f8fbfd; color: var(--ink); padding: 8px 12px; border-radius: 999px; cursor: pointer; font-size: 13px; font-weight: 600; }
    .tab-button.active { background: var(--brand); color: white; border-color: var(--brand); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 14px; }
    .summary-pill { border: 1px solid var(--line); border-radius: 12px; background: #fbfdff; padding: 12px 14px; }
    .summary-pill .name { font-size: 12px; color: #627d98; text-transform: uppercase; font-weight: 700; }
    .summary-pill .value { font-size: 20px; font-weight: 700; margin-top: 6px; color: #102a43; }
    .audit-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 14px; }
    .audit-card { border: 1px solid var(--line); border-radius: 14px; padding: 14px; background: #fbfdff; }
    .audit-card .value { font-size: 24px; font-weight: 700; margin-top: 8px; color: #102a43; }
    .audit-card .small { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.5; }
    table.data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    table.data-table thead th { position: sticky; top: 0; background: #f4f8fb; color: #12344d; font-weight: 700; border-bottom: 1px solid var(--line); padding: 10px 8px; text-align: left; cursor: pointer; }
    table.data-table tbody td { padding: 9px 8px; border-bottom: 1px solid #edf2f7; vertical-align: top; }
    table.data-table tbody tr:nth-child(even) td { background: #fbfdff; }
    .table-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
    .table-toolbar input { padding: 9px 10px; border: 1px solid var(--line); border-radius: 10px; min-width: 260px; font-size: 14px; }
    .table-scroll { overflow-x: auto; overflow-y: auto; max-height: 560px; border-radius: 12px; }
    .notes-wrap details { margin-top: 10px; }
    details { margin-top: 14px; border: 1px solid var(--line); border-radius: 12px; background: #fbfdff; padding: 10px 14px; }
    details summary { cursor: pointer; font-weight: 700; color: #12344d; }
    .small { font-size: 13px; color: var(--muted); }
    .footnote { margin-top: 24px; font-size: 12px; color: var(--muted); text-align: right; }
    @media (max-width: 1100px) {
      .metric-grid, .grid-2, .grid-3, .summary-grid, .audit-grid, .figure-grid.grid-2, .figure-grid.grid-3 { grid-template-columns: 1fr; }
      .page { padding: 18px 14px 40px; }
      .hero, .section { padding: 22px 18px; }
    }
  </style>
</head>
<body>
  <script>{{ plotly_js|safe }}</script>
  <div class="page">
    <section class="hero">
      <div class="kicker">Interactive Regional Analysis</div>
      <h1>JACO Ohio Expansion Analysis</h1>
      <p class="lede">This interactive report organizes the JACO Ohio expansion analysis into an exploratory, decision-support view of regional footprint, population reach, school distribution, outreach activity, high-need concentration, and join quality. The report is intentionally analytical rather than prescriptive.</p>
      <div class="metric-grid">
        {% for card in summary_cards %}
        <div class="metric-card">
          <div class="label">{{ card.label }}</div>
          <div class="value">{{ card.value }}</div>
          <div class="note">{{ card.note }}</div>
        </div>
        {% endfor %}
      </div>
      <div class="callout">
        <strong>Data context.</strong> {{ summary_note }}
      </div>
      <div class="section-nav">
        {% for nav in section_nav %}
        <a href="#{{ nav.id }}">{{ nav.label }}</a>
        {% endfor %}
      </div>
    </section>

    <section class="section" id="overview">
      <div class="section-head">
        <div>
          <div class="kicker">Overview</div>
          <h2>Report Scope</h2>
        </div>
      </div>
      <p class="section-intro">The analysis uses the fixed five-region JACO footprint and combines county population data, the Ohio NCES school inventory, ZIP-to-county matching, the FY25 SSI high-need file, and cold-call tracker activity. Each section below is interactive and meant to support exploration, comparison, and validation.</p>
      <div class="summary-grid">
        {% for item in overview_pills %}
        <div class="summary-pill">
          <div class="name">{{ item.name }}</div>
          <div class="value">{{ item.value }}</div>
        </div>
        {% endfor %}
      </div>
    </section>

    {% for section in sections %}
    <section class="section" id="{{ section.id }}">
      <div class="section-head">
        <div>
          <div class="kicker">{{ section.kicker }}</div>
          <h2>{{ section.title }}</h2>
        </div>
      </div>
      <p class="section-intro">{{ section.intro }}</p>

      {% if section.figures %}
      <div class="figure-grid {{ section.figure_grid_class }}">
      {% for figure in section.figures %}
      <div class="figure-card">
        <h3>{{ figure.title }}</h3>
        <div class="figure-wrap">{{ figure.html|safe }}</div>
        <div class="figure-caption">{{ figure.caption }}</div>
      </div>
      {% endfor %}
      </div>
      {% endif %}

      {% if section.tabs %}
      <div class="tab-bar" data-tab-group="{{ section.tab_group }}">
        {% for tab in section.tabs %}
        <button class="tab-button{% if loop.first %} active{% endif %}" data-tab-target="{{ section.tab_group }}-{{ loop.index0 }}">{{ tab.title }}</button>
        {% endfor %}
      </div>
      {% for tab in section.tabs %}
      <div class="tab-panel{% if loop.first %} active{% endif %}" id="{{ section.tab_group }}-{{ loop.index0 }}">
        {% for figure in tab.figures %}
        <div class="figure-card">
          <h3>{{ figure.title }}</h3>
          <div class="figure-wrap">{{ figure.html|safe }}</div>
          <div class="figure-caption">{{ figure.caption }}</div>
        </div>
        {% endfor %}
      </div>
      {% endfor %}
      {% endif %}

      {% for table in section.tables %}
      <div class="table-card">
        <div class="table-toolbar">
          <h3>{{ table.title }}</h3>
          {% if table.search_id %}
          <input type="text" id="{{ table.search_id }}" placeholder="Search table..." onkeyup="filterTable('{{ table.table_id }}', '{{ table.search_id }}')">
          {% endif %}
        </div>
        <div class="table-scroll">
          {{ table.html|safe }}
        </div>
      </div>
      {% endfor %}

      {% if section.notes %}
      <div class="notes-wrap">
        {% for note in section.notes %}
        <details>
          <summary>{{ note.title }}</summary>
          <div class="small">{{ note.body|safe }}</div>
        </details>
        {% endfor %}
      </div>
      {% endif %}
    </section>
    {% endfor %}

    <section class="section">
      <div class="section-head">
        <div>
          <div class="kicker">Method Notes</div>
          <h2>Caveats and Data Constraints</h2>
        </div>
      </div>
      {% for item in caveats %}
      <details>
        <summary>{{ item.title }}</summary>
        <p class="small">{{ item.body }}</p>
      </details>
      {% endfor %}
      <div class="footnote">Generated automatically by <code>python run_pipeline.py</code>.</div>
    </section>
  </div>

  <script>
    document.querySelectorAll('.tab-bar').forEach(function(tabBar) {
      tabBar.querySelectorAll('.tab-button').forEach(function(button) {
        button.addEventListener('click', function() {
          const group = button.getAttribute('data-tab-target').split('-').slice(0, -1).join('-');
          document.querySelectorAll('[id^="' + group + '-"]').forEach(function(panel) {
            panel.classList.remove('active');
          });
          tabBar.querySelectorAll('.tab-button').forEach(function(btn) { btn.classList.remove('active'); });
          document.getElementById(button.getAttribute('data-tab-target')).classList.add('active');
          button.classList.add('active');
          window.dispatchEvent(new Event('resize'));
        });
      });
    });

    function filterTable(tableId, inputId) {
      const filter = document.getElementById(inputId).value.toLowerCase();
      const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
      rows.forEach(function(row) {
        row.style.display = row.textContent.toLowerCase().indexOf(filter) > -1 ? '' : 'none';
      });
    }

    function sortTable(tableId, columnIndex) {
      const table = document.getElementById(tableId);
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const current = table.getAttribute('data-sort-dir') || 'asc';
      const next = current === 'asc' ? 'desc' : 'asc';
      rows.sort(function(a, b) {
        const aText = a.children[columnIndex].innerText.trim();
        const bText = b.children[columnIndex].innerText.trim();
        const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));
        const bothNumeric = !Number.isNaN(aNum) && !Number.isNaN(bNum);
        let comparison = 0;
        if (bothNumeric) {
          comparison = aNum - bNum;
        } else {
          comparison = aText.localeCompare(bText);
        }
        return next === 'asc' ? comparison : -comparison;
      });
      rows.forEach(function(row) { tbody.appendChild(row); });
      table.setAttribute('data-sort-dir', next);
    }
  </script>
</body>
</html>
"""
)


def _format_nullable_pct(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    return format_pct(value)


def _format_nullable_int(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    return format_int(value)


def _format_compact_int(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return f"{int(round(value))}"


def _plotly_html(fig: go.Figure) -> str:
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Segoe UI, Tahoma, sans-serif", "size": 13, "color": "#172b3a"},
        margin={"l": 32, "r": 24, "t": 54, "b": 36},
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})


def _write_plotly_figure(fig: go.Figure, output_path: Path) -> None:
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Segoe UI, Tahoma, sans-serif", "size": 13, "color": "#172b3a"},
        margin={"l": 32, "r": 24, "t": 54, "b": 36},
    )
    output_path.write_text(
        fig.to_html(full_html=True, include_plotlyjs=True, config={"displayModeBar": False, "responsive": True}),
        encoding="utf-8",
    )


def _render_outreach_map_png(outreach_schools: pd.DataFrame, county_geo: gpd.GeoDataFrame) -> bytes:
    import matplotlib.pyplot as plt

    region_fill = {
        "Group 1 - Columbus Core": "#CFE7EF",
        "Group 2 - Newark / East-Central": "#FDE0C5",
        "Group 3 - Southeast Cluster": "#D8EACF",
        "Group 4 - Southern Corridor": "#F6D2D3",
        "Group 5 - Eastern Edge": "#D8E3F3",
    }

    map_geo = county_geo[county_geo["region"].notna()].to_crs(4326).copy()
    fig, ax = plt.subplots(figsize=(10.5, 8.5), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    map_geo.plot(
        ax=ax,
        color=map_geo["region"].map(region_fill),
        edgecolor="#AAB9C6",
        linewidth=0.9,
    )

    neutral_outreach = outreach_schools[~outreach_schools["is_interested_school"]].copy()
    interested_outreach = outreach_schools[outreach_schools["is_interested_school"]].copy()

    if not neutral_outreach.empty:
        ax.scatter(
            neutral_outreach["plot_longitude"],
            neutral_outreach["plot_latitude"],
            s=28,
            c="#94A3B8",
            alpha=0.78,
            edgecolors="white",
            linewidths=0.45,
            label="Other outreach schools",
            zorder=3,
        )

    if not interested_outreach.empty:
        ax.scatter(
            interested_outreach["plot_longitude"],
            interested_outreach["plot_latitude"],
            s=54,
            c="#1F9D55",
            alpha=0.98,
            edgecolors="#0F5132",
            linewidths=0.8,
            label="Interested outreach schools",
            zorder=4,
        )

    ax.set_title("Outreach-Matched Schools", fontsize=18, pad=16, color="#12344d")
    ax.text(
        0.0,
        1.01,
        "Tracker-matched outreach schools only. Green points indicate Outcome = Interested.",
        transform=ax.transAxes,
        fontsize=10.5,
        color="#5b7083",
        va="bottom",
    )
    ax.text(
        0.0,
        -0.04,
        "Exact coordinates are used where available; remaining schools use transparent county-based fallback placement.",
        transform=ax.transAxes,
        fontsize=9.5,
        color="#5b7083",
        va="top",
    )
    ax.legend(
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#D9E2EC",
    )
    ax.set_axis_off()
    plt.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buffer.getvalue()


def _outreach_map_png_html(outreach_schools: pd.DataFrame, county_geo: gpd.GeoDataFrame) -> str:
    encoded = base64.b64encode(_render_outreach_map_png(outreach_schools, county_geo)).decode("ascii")
    return (
        "<div style='display:flex; justify-content:center;'>"
        f"<img src='data:image/png;base64,{encoded}' alt='Outreach school map' "
        "style='width:100%; max-width:980px; height:auto; border-radius:14px; border:1px solid #d9e2ec;'>"
        "</div>"
    )


def _write_outreach_map_png(outreach_schools: pd.DataFrame, county_geo: gpd.GeoDataFrame, output_path: Path) -> None:
    output_path.write_bytes(_render_outreach_map_png(outreach_schools, county_geo))


def _table_html(df: pd.DataFrame, table_id: str) -> str:
    display = df.copy()
    for column in display.columns:
        if display[column].dtype == bool:
            display[column] = display[column].map({True: "Yes", False: "No"})
    html = display.to_html(index=False, classes=["data-table"], border=0, table_id=table_id)
    return html.replace("<th>", lambda *_: "")


def _build_sortable_table(df: pd.DataFrame, table_id: str) -> str:
    html = df.to_html(index=False, classes=["data-table"], border=0, table_id=table_id)
    for idx, column in enumerate(df.columns):
        html = html.replace(f"<th>{column}</th>", f'<th onclick="sortTable(\'{table_id}\', {idx})">{column}</th>', 1)
    return html


def _geojson_from_gdf(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    columns = [column for column in gdf.columns if column != "geometry"]
    return json.loads(gdf[columns + ["geometry"]].to_json())


def _county_metrics(artifacts: PipelineArtifacts, county_geo: gpd.GeoDataFrame) -> pd.DataFrame:
    schools = artifacts.schools_clean.copy()
    schools = schools[schools["is_regular_or_cte"]].copy()
    tracker = artifacts.tracker_match_detail.copy()

    school_counts = (
        schools.groupby("county_name", as_index=False)
        .agg(
            total_schools=("NCESSCH", "nunique"),
            elementary_schools=("school_level", lambda values: values.fillna("").str.contains("Elementary", case=False).sum()),
            secondary_schools=("school_level", lambda values: values.fillna("").str.contains("High|Secondary", case=False).sum()),
            school_types=("school_type", lambda values: ", ".join(sorted(pd.Series(values).dropna().astype(str).unique()[:3]))),
        )
    )
    high_need_counts = (
        schools.groupby("county_name", as_index=False)
        .agg(
            high_need_schools=("high_need", lambda values: int(values.fillna(False).astype(int).sum())),
            title_students_served=("students_served", "sum"),
        )
    )
    tracker_counts = (
        tracker.groupby("county_name", dropna=False, as_index=False)
        .agg(
            outreach_records=("organization_name", "count"),
            interested_outcomes=("positive_response", "sum"),
            matched_tracker_rows=("NCESSCH", lambda values: values.notna().sum()),
            unmatched_tracker_rows=("NCESSCH", lambda values: values.isna().sum()),
        )
    )
    county_metrics = county_geo.merge(school_counts, on="county_name", how="left")
    county_metrics = county_metrics.merge(high_need_counts, on="county_name", how="left")
    county_metrics = county_metrics.merge(tracker_counts, on="county_name", how="left")

    fill_zero = [
        "total_schools",
        "elementary_schools",
        "secondary_schools",
        "high_need_schools",
        "title_students_served",
        "outreach_records",
        "interested_outcomes",
        "matched_tracker_rows",
        "unmatched_tracker_rows",
    ]
    for column in fill_zero:
        if column in county_metrics.columns:
            county_metrics[column] = county_metrics[column].fillna(0)

    county_metrics["high_need_share"] = county_metrics["high_need_schools"] / county_metrics["total_schools"].replace(0, pd.NA)
    county_metrics["school_density_per_10k_youth"] = county_metrics["total_schools"] / county_metrics["youth_population"].replace(0, pd.NA) * 10000
    county_metrics["outreach_per_100_schools"] = county_metrics["outreach_records"] / county_metrics["total_schools"].replace(0, pd.NA) * 100
    county_metrics["interested_per_100_schools"] = county_metrics["interested_outcomes"] / county_metrics["total_schools"].replace(0, pd.NA) * 100
    county_metrics["county_area_sq_miles"] = county_metrics.to_crs(3734).geometry.area / 2_589_988.11
    county_metrics["schools_per_100_sq_miles"] = county_metrics["total_schools"] / county_metrics["county_area_sq_miles"].replace(0, pd.NA) * 100
    county_metrics["is_jaco_county"] = county_metrics["region"].notna()
    return county_metrics


def _region_metrics(artifacts: PipelineArtifacts) -> pd.DataFrame:
    region_df = artifacts.region_summary.copy()
    region_df["outreach_per_100_schools"] = region_df["outreach_records"] / region_df["total_schools"].replace(0, pd.NA) * 100
    region_df["interested_per_100_schools"] = region_df["positive_responses"] / region_df["total_schools"].replace(0, pd.NA) * 100
    region_df["schools_per_10k_youth"] = region_df["total_schools"] / region_df["youth_population"].replace(0, pd.NA) * 10000
    return region_df


def _school_points(artifacts: PipelineArtifacts) -> tuple[pd.DataFrame, bool]:
    schools = artifacts.schools_clean.copy()
    schools = schools[schools["region"].notna() & schools["is_regular_or_cte"]].copy()
    if schools.empty:
        return schools, False

    has_exact = schools["latitude"].notna().any() and schools["longitude"].notna().any()
    schools["plot_latitude"] = schools["latitude"].where(schools["latitude"].notna(), schools["approx_latitude"])
    schools["plot_longitude"] = schools["longitude"].where(schools["longitude"].notna(), schools["approx_longitude"])
    schools["location_precision"] = "Approximate county-based placement"
    schools.loc[schools["coordinate_match_method"] == "source_file_exact", "location_precision"] = "Exact source coordinates"
    schools.loc[schools["coordinate_match_method"] == "supplement_name_county", "location_precision"] = "Exact coordinates from supplemental workbook (name + county match)"
    schools.loc[schools["coordinate_match_method"] == "supplement_unique_name", "location_precision"] = "Exact coordinates from supplemental workbook (unique name match)"
    schools.loc[schools["coordinate_match_method"] == "supplement_phone_county", "location_precision"] = "Exact coordinates from supplemental workbook (phone + county match)"
    schools.loc[schools["coordinate_match_method"] == "supplement_address_county", "location_precision"] = "Exact coordinates from supplemental workbook (address + county match)"

    positive_ids = set(
        artifacts.tracker_match_detail.loc[
            artifacts.tracker_match_detail["positive_response"].fillna(False) & artifacts.tracker_match_detail["NCESSCH"].notna(),
            "NCESSCH",
        ].astype(str)
    )
    schools["is_interested_school"] = schools["NCESSCH"].astype(str).isin(positive_ids)
    return schools, has_exact


def _outreach_school_points(artifacts: PipelineArtifacts) -> tuple[pd.DataFrame, bool]:
    schools, _ = _school_points(artifacts)
    if schools.empty:
        return schools, False

    tracker_matches = artifacts.tracker_match_detail.copy()
    tracker_matches = tracker_matches[tracker_matches["NCESSCH"].notna()].copy()
    if tracker_matches.empty:
        return tracker_matches, False

    tracker_matches["NCESSCH"] = tracker_matches["NCESSCH"].astype(str)
    outreach_summary = (
        tracker_matches.groupby("NCESSCH", as_index=False)
        .agg(
            outreach_records=("organization_name", "count"),
            interested_records=("positive_response", "sum"),
        )
    )
    outreach_summary["is_interested_outreach"] = outreach_summary["interested_records"] > 0

    outreach_schools = schools.drop(columns=["is_interested_school"], errors="ignore").copy()
    outreach_schools["NCESSCH"] = outreach_schools["NCESSCH"].astype(str)
    outreach_schools = outreach_schools.merge(outreach_summary, on="NCESSCH", how="inner")
    outreach_schools["is_interested_school"] = outreach_schools["is_interested_outreach"].fillna(False)
    has_exact = outreach_schools["latitude"].notna().any() and outreach_schools["longitude"].notna().any()
    return outreach_schools, has_exact


def _build_region_map(county_geo: gpd.GeoDataFrame) -> go.Figure:
    map_geo = county_geo.to_crs(4326).copy()
    map_geo["region_id_fill"] = map_geo["region_id"].fillna(0).astype(int)
    geojson = _geojson_from_gdf(map_geo)
    colorscale = [
        [0.0, "#E6EBF1"],
        [0.001, "#0B5D7A"],
        [0.20, "#0B5D7A"],
        [0.201, "#F28E2B"],
        [0.40, "#F28E2B"],
        [0.401, "#59A14F"],
        [0.60, "#59A14F"],
        [0.601, "#E15759"],
        [0.80, "#E15759"],
        [0.801, "#4E79A7"],
        [1.0, "#4E79A7"],
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=map_geo["county_fips"],
            z=map_geo["region_id_fill"],
            featureidkey="properties.county_fips",
            colorscale=colorscale,
            marker_line_color="white",
            marker_line_width=0.7,
            showscale=False,
            customdata=map_geo[["county_name", "region", "anchor_county"]].fillna("Outside fixed JACO regions").to_numpy(),
            hovertemplate="<b>%{customdata[0]} County</b><br>Region: %{customdata[1]}<br>Anchor: %{customdata[2]}<extra></extra>",
        )
    )
    anchors = map_geo[map_geo["is_anchor"]].copy()
    anchors_projected = anchors.to_crs(3734).copy()
    anchors_projected["centroid"] = anchors_projected.geometry.centroid
    anchors_centroids = anchors_projected.set_geometry("centroid").to_crs(4326)
    fig.add_trace(
        go.Scattergeo(
            lon=anchors_centroids.geometry.x,
            lat=anchors_centroids.geometry.y,
            mode="markers+text",
            text=anchors_centroids["county_name"],
            textposition="top center",
            marker={"symbol": "star", "size": 12, "color": "#111827", "line": {"color": "white", "width": 1}},
            name="Anchor county",
            hovertemplate="<b>%{text} County</b><br>Anchor county<extra></extra>",
        )
    )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(title="Fixed JACO Regions and Anchor Counties", height=620)
    return fig


def _build_county_heatmap(county_geo: gpd.GeoDataFrame, metric: str, title: str, colorscale: str, value_label: str) -> go.Figure:
    map_geo = county_geo.to_crs(4326).copy()
    geojson = _geojson_from_gdf(map_geo)
    customdata = map_geo[
        [
            "county_name",
            "region",
            "total_population",
            "youth_population",
            "total_schools",
            "high_need_schools",
            "high_need_share",
            "outreach_records",
            "interested_outcomes",
        ]
    ].copy()
    customdata["region"] = customdata["region"].fillna("Outside fixed JACO regions")

    hover_templates = {
        "total_population": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "Total population: %{z:,.0f}<br>"
            "Youth population: %{customdata[3]:,.0f}<br>"
            "Schools: %{customdata[4]:,.0f}<extra></extra>"
        ),
        "youth_population": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "Youth population: %{z:,.0f}<br>"
            "Total population: %{customdata[2]:,.0f}<br>"
            "Schools: %{customdata[4]:,.0f}<extra></extra>"
        ),
        "school_density_per_10k_youth": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "Schools per 10k youth: %{z:,.1f}<br>"
            "Schools: %{customdata[4]:,.0f}<br>"
            "Youth population: %{customdata[3]:,.0f}<extra></extra>"
        ),
        "high_need_schools": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "High-need schools: %{z:,.0f}<br>"
            "High-need share: %{customdata[6]:.1%}<br>"
            "Schools: %{customdata[4]:,.0f}<extra></extra>"
        ),
        "high_need_share": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "High-need share: %{z:.1%}<br>"
            "High-need schools: %{customdata[5]:,.0f}<br>"
            "Schools: %{customdata[4]:,.0f}<extra></extra>"
        ),
        "outreach_records": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "Outreach records: %{z:,.0f}<br>"
            "Interested outcomes: %{customdata[8]:,.0f}<br>"
            "Schools: %{customdata[4]:,.0f}<extra></extra>"
        ),
        "interested_outcomes": (
            "<b>%{customdata[0]} County</b><br>"
            "Region: %{customdata[1]}<br>"
            "Interested outcomes: %{z:,.0f}<br>"
            "Outreach records: %{customdata[7]:,.0f}<br>"
            "Schools: %{customdata[4]:,.0f}<extra></extra>"
        ),
    }

    fig = go.Figure()
    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=map_geo["county_fips"],
            z=map_geo[metric].fillna(0),
            featureidkey="properties.county_fips",
            colorscale=colorscale,
            marker_line_color="white",
            marker_line_width=0.5,
            colorbar={"title": value_label},
            customdata=customdata.to_numpy(),
            hovertemplate=hover_templates.get(metric, "<b>%{customdata[0]} County</b><br>Region: %{customdata[1]}<br>" + f"{value_label}: %{{z:,.2f}}<extra></extra>"),
        )
    )
    jaco = map_geo[map_geo["is_jaco_county"]].copy()
    if not jaco.empty:
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=jaco["county_fips"],
                z=[1] * len(jaco),
                featureidkey="properties.county_fips",
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                marker_line_color="#102A43",
                marker_line_width=1.5,
                showscale=False,
                hoverinfo="skip",
            )
        )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(title=title, height=600, margin={"l": 20, "r": 20, "t": 52, "b": 16})
    return fig


def _build_horizontal_bar(df: pd.DataFrame, value_col: str, title: str, value_type: str = "int") -> go.Figure:
    return _build_horizontal_bar_advanced(df, value_col, title, value_type=value_type)


def _short_region_label(value: str) -> str:
    if not value:
        return value
    return (
        value.replace("Group 1 - ", "G1: ")
        .replace("Group 2 - ", "G2: ")
        .replace("Group 3 - ", "G3: ")
        .replace("Group 4 - ", "G4: ")
        .replace("Group 5 - ", "G5: ")
    )


def _build_horizontal_bar_advanced(
    df: pd.DataFrame,
    value_col: str,
    title: str,
    value_type: str = "int",
    use_short_labels: bool = False,
    show_bar_text: bool = True,
    height: int = 460,
    compact_text: bool = False,
) -> go.Figure:
    plot_df = df.sort_values(value_col, ascending=True).copy()
    plot_df["region_display"] = plot_df["region"].map(_short_region_label if use_short_labels else (lambda x: x))
    if show_bar_text:
        if value_type == "int":
            formatter = _format_compact_int if compact_text else format_int
        else:
            formatter = format_pct
        text = plot_df[value_col].map(formatter)
    else:
        text = None
    hover_value = "%{x:,.0f}" if value_type == "int" else "%{x:.1%}"
    fig = go.Figure(
        go.Bar(
            x=plot_df[value_col],
            y=plot_df["region_display"],
            orientation="h",
            marker={"color": plot_df["region"].map(REGION_COLORS)},
            text=text,
            textposition="outside" if show_bar_text else "none",
            cliponaxis=False,
            customdata=plot_df[["region"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>" + hover_value + "<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        height=height,
        xaxis_title="",
        yaxis_title="",
        margin={"l": 150 if use_short_labels else 200, "r": 24 if not show_bar_text else 40, "t": 54, "b": 36},
        xaxis={"tickformat": ",.0f" if value_type == "int" else ".0%"},
    )
    return fig


def _build_bubble(df: pd.DataFrame, x: str, y: str, size: str, title: str, x_label: str, y_label: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="markers+text",
            text=df["region"],
            textposition="top center",
            marker={
                "size": (df[size] / max(df[size].max(), 1) * 48).clip(lower=18),
                "color": df["region"].map(REGION_COLORS),
                "opacity": 0.86,
                "line": {"color": "#ffffff", "width": 1.2},
            },
            customdata=df[["anchor_county", "total_schools", "positive_responses", "high_need_share"]].to_numpy(),
            hovertemplate="<b>%{text}</b><br>Anchor: %{customdata[0]}<br>Schools: %{customdata[1]:,.0f}<br>Interested outcomes: %{customdata[2]:,.0f}<br>High-need share: %{customdata[3]:.1%}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=520, xaxis_title=x_label, yaxis_title=y_label)
    return fig


def _build_outcome_distribution(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=df["outcome_clean"],
            y=df["count"],
            marker={"color": ["#1F9D55" if value else "#7B8794" for value in df["is_positive"]]},
            customdata=df["is_positive"],
            hovertemplate="<b>%{x}</b><br>Rows: %{y:,.0f}<br>Interested classification: %{customdata}<extra></extra>",
        )
    )
    fig.update_layout(title="Cold-Call Outcome Distribution", height=430, xaxis_title="Outcome", yaxis_title="Rows")
    return fig


def _build_match_summary(df: pd.DataFrame, value_col: str, title: str) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=df.iloc[:, 0],
            y=df[value_col],
            marker={"color": "#0B5D7A"},
            hovertemplate="<b>%{x}</b><br>Count: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=420, xaxis_title="", yaxis_title="Count")
    return fig


def _build_school_map(schools: pd.DataFrame, county_geo: gpd.GeoDataFrame, has_exact_coords: bool) -> go.Figure:
    fig = go.Figure()
    map_geo = county_geo[county_geo["region"].notna()].to_crs(4326).copy()
    map_geo["region_id_fill"] = map_geo["region_id"].astype(int)
    geojson = _geojson_from_gdf(map_geo)
    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=map_geo["county_fips"],
            z=map_geo["region_id_fill"],
            featureidkey="properties.county_fips",
            colorscale=[
                [0.0, "#F8FAFC"],
                [0.001, "rgba(207,231,239,0.55)"],
                [0.20, "rgba(207,231,239,0.55)"],
                [0.201, "rgba(253,224,197,0.55)"],
                [0.40, "rgba(253,224,197,0.55)"],
                [0.401, "rgba(216,234,207,0.55)"],
                [0.60, "rgba(216,234,207,0.55)"],
                [0.601, "rgba(246,210,211,0.55)"],
                [0.80, "rgba(246,210,211,0.55)"],
                [0.801, "rgba(216,227,243,0.55)"],
                [1.0, "rgba(216,227,243,0.55)"],
            ],
            marker_line_color="#AAB9C6",
            marker_line_width=0.9,
            showscale=False,
            customdata=map_geo[["county_name", "region"]].fillna("Outside fixed JACO regions").to_numpy(),
            hovertemplate="<b>%{customdata[0]} County</b><br>Region: %{customdata[1]}<extra></extra>",
            name="JACO regions",
        )
    )
    exact_neutral = schools[(~schools["is_interested_school"]) & schools["latitude"].notna() & schools["longitude"].notna()].copy()
    approx_neutral = schools[(~schools["is_interested_school"]) & ~(schools["latitude"].notna() & schools["longitude"].notna())].copy()
    interested = schools[schools["is_interested_school"]].copy()

    fig.add_trace(
        go.Scattergeo(
            lon=approx_neutral["plot_longitude"],
            lat=approx_neutral["plot_latitude"],
            mode="markers",
            marker={"size": 4.5, "color": "#CBD5E1", "opacity": 0.36},
            name="Approximate schools",
            customdata=approx_neutral[["SCH_NAME", "county_name", "region", "school_level", "school_type", "location_precision"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>County: %{customdata[1]}<br>Region: %{customdata[2]}<br>Level: %{customdata[3]}<br>Type: %{customdata[4]}<br>Location: %{customdata[5]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lon=exact_neutral["plot_longitude"],
            lat=exact_neutral["plot_latitude"],
            mode="markers",
            marker={"size": 6.5, "color": "#475569", "opacity": 0.8, "line": {"color": "#E2E8F0", "width": 0.5}},
            name="Exact-coordinate schools",
            customdata=exact_neutral[["SCH_NAME", "county_name", "region", "school_level", "school_type", "location_precision"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>County: %{customdata[1]}<br>Region: %{customdata[2]}<br>Level: %{customdata[3]}<br>Type: %{customdata[4]}<br>Location: %{customdata[5]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lon=interested["plot_longitude"],
            lat=interested["plot_latitude"],
            mode="markers",
            marker={"size": 9, "color": "#1F9D55", "opacity": 0.95, "line": {"color": "#0F5132", "width": 0.8}},
            name="Interested schools",
            customdata=interested[["SCH_NAME", "county_name", "region", "school_level", "school_type", "location_precision"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>County: %{customdata[1]}<br>Region: %{customdata[2]}<br>Level: %{customdata[3]}<br>Type: %{customdata[4]}<br>Location: %{customdata[5]}<extra></extra>",
        )
    )

    exact_count = int((schools["latitude"].notna() & schools["longitude"].notna()).sum())
    approx_count = int(len(schools) - exact_count)
    fig.update_layout(
        title="School Locations and Interested Schools",
        height=720,
        geo={"scope": "usa", "projection": {"type": "mercator"}, "fitbounds": "locations", "visible": False},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "left",
            "x": 0.0,
            "bgcolor": "rgba(255,255,255,0.85)",
        },
    )
    title_note = (
        f"Exact coordinates are used for {format_int(exact_count)} mapped school rows; the remaining {format_int(approx_count)} rows use transparent county-based fallback placement."
        if has_exact_coords
        else "Exact school coordinates were not available in the source files; school points use transparent approximate placement within matched counties."
    )
    fig.add_annotation(
        x=0.0,
        y=1.12,
        xref="paper",
        yref="paper",
        text=title_note,
        showarrow=False,
        font={"size": 12, "color": "#5b7083"},
        align="left",
        xanchor="left",
    )
    return fig


def _build_outreach_map(outreach_schools: pd.DataFrame, county_geo: gpd.GeoDataFrame, has_exact_coords: bool) -> go.Figure:
    fig = go.Figure()
    map_geo = county_geo[county_geo["region"].notna()].to_crs(4326).copy()
    map_geo["region_id_fill"] = map_geo["region_id"].astype(int)
    geojson = _geojson_from_gdf(map_geo)

    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=map_geo["county_fips"],
            z=map_geo["region_id_fill"],
            featureidkey="properties.county_fips",
            colorscale=[
                [0.0, "#F8FAFC"],
                [0.001, "rgba(207,231,239,0.55)"],
                [0.20, "rgba(207,231,239,0.55)"],
                [0.201, "rgba(253,224,197,0.55)"],
                [0.40, "rgba(253,224,197,0.55)"],
                [0.401, "rgba(216,234,207,0.55)"],
                [0.60, "rgba(216,234,207,0.55)"],
                [0.601, "rgba(246,210,211,0.55)"],
                [0.80, "rgba(246,210,211,0.55)"],
                [0.801, "rgba(216,227,243,0.55)"],
                [1.0, "rgba(216,227,243,0.55)"],
            ],
            marker_line_color="#AAB9C6",
            marker_line_width=0.9,
            showscale=False,
            customdata=map_geo[["county_name", "region"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]} County</b><br>Region: %{customdata[1]}<extra></extra>",
            name="JACO regions",
        )
    )

    neutral_outreach = outreach_schools[~outreach_schools["is_interested_school"]].copy()
    interested_outreach = outreach_schools[outreach_schools["is_interested_school"]].copy()

    fig.add_trace(
        go.Scattergeo(
            lon=neutral_outreach["plot_longitude"],
            lat=neutral_outreach["plot_latitude"],
            mode="markers",
            marker={"size": 7, "color": "#94A3B8", "opacity": 0.72, "line": {"color": "#E2E8F0", "width": 0.5}},
            name="Other outreach schools",
            customdata=neutral_outreach[
                ["SCH_NAME", "county_name", "region", "outreach_records", "interested_records", "location_precision"]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "County: %{customdata[1]}<br>"
                "Region: %{customdata[2]}<br>"
                "Outreach rows: %{customdata[3]:,.0f}<br>"
                "Interested rows: %{customdata[4]:,.0f}<br>"
                "Location: %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lon=interested_outreach["plot_longitude"],
            lat=interested_outreach["plot_latitude"],
            mode="markers",
            marker={"size": 10, "color": "#1F9D55", "opacity": 0.98, "line": {"color": "#0F5132", "width": 0.9}},
            name="Interested outreach schools",
            customdata=interested_outreach[
                ["SCH_NAME", "county_name", "region", "outreach_records", "interested_records", "location_precision"]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "County: %{customdata[1]}<br>"
                "Region: %{customdata[2]}<br>"
                "Outreach rows: %{customdata[3]:,.0f}<br>"
                "Interested rows: %{customdata[4]:,.0f}<br>"
                "Location: %{customdata[5]}<extra></extra>"
            ),
        )
    )

    exact_count = int((outreach_schools["latitude"].notna() & outreach_schools["longitude"].notna()).sum())
    approx_count = int(len(outreach_schools) - exact_count)
    fig.update_layout(
        title="Outreach-Matched Schools",
        height=700,
        geo={"scope": "usa", "projection": {"type": "mercator"}, "fitbounds": "locations", "visible": False},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "left",
            "x": 0.0,
            "bgcolor": "rgba(255,255,255,0.88)",
        },
    )
    title_note = (
        f"This map shows only tracker-matched outreach schools. Exact coordinates are used for {format_int(exact_count)} rows and transparent county-based fallback placement is used for the remaining {format_int(approx_count)}."
        if has_exact_coords
        else "This map shows only tracker-matched outreach schools, using transparent county-based placement because exact coordinates were unavailable."
    )
    fig.add_annotation(
        x=0.0,
        y=1.11,
        xref="paper",
        yref="paper",
        text=title_note,
        showarrow=False,
        font={"size": 12, "color": "#5b7083"},
        align="left",
        xanchor="left",
    )
    return fig


def _build_school_type_chart(schools: pd.DataFrame) -> go.Figure:
    plot_df = (
        schools.groupby(["region", "school_type"], as_index=False)
        .agg(school_count=("NCESSCH", "nunique"))
        .sort_values(["region", "school_count"], ascending=[True, False])
    )
    top_types = plot_df.groupby("school_type")["school_count"].sum().sort_values(ascending=False).head(6).index
    plot_df["school_type_grouped"] = plot_df["school_type"].where(plot_df["school_type"].isin(top_types), "Other")
    plot_df = plot_df.groupby(["region", "school_type_grouped"], as_index=False)["school_count"].sum()

    fig = go.Figure()
    for school_type in sorted(plot_df["school_type_grouped"].unique()):
        subset = plot_df[plot_df["school_type_grouped"] == school_type]
        fig.add_trace(
            go.Bar(
                x=subset["region"],
                y=subset["school_count"],
                name=school_type,
                hovertemplate="<b>%{x}</b><br>School type: " + school_type + "<br>Count: %{y:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(title="School Type Breakdown by Region", barmode="stack", height=470, xaxis_title="", yaxis_title="Schools")
    return fig


def render_report(artifacts: PipelineArtifacts, county_geo: gpd.GeoDataFrame, metadata: dict[str, object]) -> None:
    county_geo = county_geo.to_crs(4326).copy()
    county_metrics = _county_metrics(artifacts, county_geo)
    region_metrics = _region_metrics(artifacts)
    school_points, has_exact_coords = _school_points(artifacts)
    outreach_points, outreach_has_exact = _outreach_school_points(artifacts)

    region_map_fig = _build_region_map(county_geo)
    total_population_heatmap_fig = _build_county_heatmap(
        county_metrics, "total_population", "Ohio County Total Population", "Blues", "Population"
    )
    youth_population_heatmap_fig = _build_county_heatmap(
        county_metrics, "youth_population", "Ohio County Youth Population", "YlGnBu", "Youth population"
    )
    school_density_heatmap_fig = _build_county_heatmap(
        county_metrics, "school_density_per_10k_youth", "Schools per 10,000 Youth", "Oranges", "Schools per 10k youth"
    )
    high_need_count_heatmap_fig = _build_county_heatmap(
        county_metrics, "high_need_schools", "High-Need School Count", "Reds", "High-need schools"
    )
    high_need_share_heatmap_fig = _build_county_heatmap(
        county_metrics, "high_need_share", "High-Need School Share", "RdPu", "High-need share"
    )
    outreach_activity_heatmap_fig = _build_county_heatmap(
        county_metrics, "outreach_records", "Outreach Records by County", "PuBuGn", "Outreach records"
    )
    interested_outcomes_heatmap_fig = _build_county_heatmap(
        county_metrics, "interested_outcomes", "Interested Outcomes by County", "Greens", "Interested outcomes"
    )
    youth_by_region_fig = _build_horizontal_bar_advanced(
        region_metrics,
        "youth_population",
        "Youth Population by Region",
        use_short_labels=True,
        compact_text=True,
    )
    schools_by_region_fig = _build_horizontal_bar(region_metrics, "total_schools", "Mapped Schools by Region")
    school_type_chart_fig = _build_school_type_chart(school_points)
    outcome_distribution_fig = _build_outcome_distribution(artifacts.tracker_value_audit)
    tracker_match_summary_fig = _build_match_summary(artifacts.tracker_match_summary, "rows", "Tracker Match Summary")
    interested_rate_by_region_fig = _build_horizontal_bar(
        region_metrics.fillna({"positive_response_rate": 0}),
        "positive_response_rate",
        "Interested Response Rate by Region",
        value_type="pct",
    )
    outreach_records_by_region_fig = _build_horizontal_bar(
        region_metrics.fillna({"outreach_records": 0}),
        "outreach_records",
        "Outreach Records by Region",
    )
    high_need_match_methods_fig = _build_match_summary(
        artifacts.high_need_match_summary,
        "school_records",
        "High-Need Match Methods",
    )
    high_need_by_region_fig = _build_horizontal_bar(region_metrics, "high_need_schools", "High-Need Schools by Region")
    high_need_share_by_region_fig = _build_horizontal_bar(
        region_metrics,
        "high_need_share",
        "High-Need School Share by Region",
        value_type="pct",
    )
    scale_vs_need_fig = _build_bubble(
        region_metrics,
        "youth_population",
        "high_need_share",
        "total_schools",
        "Scale vs High-Need Concentration",
        "Youth population",
        "High-need school share",
    )
    scale_vs_outreach_fig = _build_bubble(
        region_metrics.fillna({"outreach_records": 0, "positive_responses": 0, "high_need_share": 0}),
        "youth_population",
        "outreach_per_100_schools",
        "total_schools",
        "Youth Reach vs Outreach Intensity",
        "Youth population",
        "Outreach records per 100 schools",
    )
    anchor_distance_fig = _build_horizontal_bar(
        region_metrics,
        "max_anchor_distance_miles",
        "Maximum Anchor-to-County Distance by Region",
    )

    school_map_report_html = (
        _outreach_map_png_html(outreach_points, county_geo)
        if not outreach_points.empty
        else _plotly_html(_build_outreach_map(outreach_points, county_geo, outreach_has_exact))
    )

    grouped_counties = county_metrics[county_metrics["is_jaco_county"]].copy()
    interested_matched = int(metadata["tracker"]["positive_matched_schools"])
    exact_school_points = int((outreach_points["latitude"].notna() & outreach_points["longitude"].notna()).sum()) if not outreach_points.empty else 0
    interested_exact_points = int(
        (outreach_points["is_interested_school"] & outreach_points["latitude"].notna() & outreach_points["longitude"].notna()).sum()
    ) if not outreach_points.empty else 0
    outreach_mapped_schools = int(len(outreach_points))
    summary_cards = [
        {"label": "Fixed regions", "value": "5", "note": "JACO county groupings used throughout the analysis."},
        {"label": "Grouped counties", "value": format_int(grouped_counties["county_name"].nunique()), "note": "Counties assigned to the five fixed regions."},
        {"label": "Youth in grouped counties", "value": format_int(grouped_counties["youth_population"].sum()), "note": "Youth population using AGEGRP 2–4 in the latest county-level source year."},
        {"label": "Mapped schools in grouped counties", "value": format_int(region_metrics["total_schools"].sum()), "note": "Open Ohio schools mapped into the JACO footprint."},
        {"label": "Outreach-matched schools", "value": format_int(outreach_mapped_schools), "note": "Unique matched tracker schools shown on the outreach map."},
        {"label": "Exact outreach coordinates", "value": format_int(exact_school_points), "note": "Outreach-matched school rows using exact coordinates from the coordinate supplement."},
        {"label": "Interested matched schools", "value": format_int(interested_matched), "note": "Tracker rows where Outcome = Interested and a school match was found."},
    ]
    summary_note = (
        (
            f"The current source files support extensive regional, county, outreach, and high-need analysis. "
            f"The report uses the primary analytical tables directly and keeps the heavier audit tables available in <code>outputs/tables</code> rather than crowding the main narrative. "
            f"The map section now shows only the {format_int(outreach_mapped_schools)} outreach-matched schools rather than the full school inventory. "
            f"Within that subset, {format_int(exact_school_points)} rows use exact coordinates, including {format_int(interested_exact_points)} of the "
            f"{format_int(metadata['tracker']['positive_matched_schools'])} Interested schools."
        )
        if outreach_has_exact
        else "The current source files support extensive regional, county, outreach, and high-need analysis. The report uses the primary analytical tables directly and keeps the heavier audit tables available in outputs/tables rather than crowding the main narrative."
    )

    overview_pills = [
        {"name": "Latest population YEAR code", "value": str(metadata["population"]["latest_year_code"])},
        {"name": "Youth AGEGRP logic", "value": ", ".join(map(str, metadata["population"]["selected_youth_age_groups"]))},
        {"name": "Tracker positive rule", "value": "Outcome = Interested"},
        {"name": "Coordinate method", "value": "Hybrid exact + approximate" if outreach_has_exact else "Approximate"},
    ]

    heatmap_figures = [
        {
            "title": "Total Population",
            "html": _plotly_html(total_population_heatmap_fig),
            "caption": "Hover for county, region membership, and supporting context. Dark outlines identify counties inside the fixed JACO footprint.",
        },
        {
            "title": "Youth Population",
            "html": _plotly_html(youth_population_heatmap_fig),
            "caption": "Youth population is derived from the inspected AGEGRP structure in the source file rather than assumed blindly.",
        },
        {
            "title": "School Density",
            "html": _plotly_html(school_density_heatmap_fig),
            "caption": "This view helps distinguish high-volume counties from counties with smaller school inventories relative to youth population.",
        },
        {
            "title": "High-Need Count",
            "html": _plotly_html(high_need_count_heatmap_fig),
            "caption": "Counts reflect schools linked to the FY25 SSI file through the current exact and fallback match logic.",
        },
        {
            "title": "High-Need Share",
            "html": _plotly_html(high_need_share_heatmap_fig),
            "caption": "The share view controls for county size and highlights concentration rather than raw volume.",
        },
        {
            "title": "Outreach Activity",
            "html": _plotly_html(outreach_activity_heatmap_fig),
            "caption": "This map uses tracker rows after county cleaning and reflects activity volume, not only positive outcomes.",
        },
        {
            "title": "Interested Outcomes",
            "html": _plotly_html(interested_outcomes_heatmap_fig),
            "caption": "Interested outcomes use only the exact rule Outcome = Interested.",
        },
    ]

    region_table = region_metrics[
        [
            "region",
            "anchor_county",
            "county_count",
            "youth_population",
            "total_schools",
            "high_need_schools",
            "high_need_share",
            "outreach_records",
            "positive_responses",
            "positive_response_rate",
            "max_anchor_distance_miles",
        ]
    ].copy()
    region_table["youth_population"] = region_table["youth_population"].map(format_int)
    region_table["total_schools"] = region_table["total_schools"].map(format_int)
    region_table["high_need_schools"] = region_table["high_need_schools"].map(format_int)
    region_table["high_need_share"] = region_table["high_need_share"].map(_format_nullable_pct)
    region_table["outreach_records"] = region_table["outreach_records"].fillna(0).map(format_int)
    region_table["positive_responses"] = region_table["positive_responses"].fillna(0).map(format_int)
    region_table["positive_response_rate"] = region_table["positive_response_rate"].map(_format_nullable_pct)
    region_table["max_anchor_distance_miles"] = region_table["max_anchor_distance_miles"].map(lambda value: "N/A" if pd.isna(value) else f"{value:.1f}")

    county_table = county_metrics[
        [
            "county_name",
            "region",
            "total_population",
            "youth_population",
            "total_schools",
            "high_need_schools",
            "high_need_share",
            "outreach_records",
            "interested_outcomes",
            "school_density_per_10k_youth",
        ]
    ].copy()
    county_table["region"] = county_table["region"].fillna("Outside fixed JACO regions")
    for column in ["total_population", "youth_population", "total_schools", "high_need_schools", "outreach_records", "interested_outcomes"]:
        county_table[column] = county_table[column].map(_format_nullable_int)
    county_table["high_need_share"] = county_table["high_need_share"].map(_format_nullable_pct)
    county_table["school_density_per_10k_youth"] = county_table["school_density_per_10k_youth"].map(lambda value: "N/A" if pd.isna(value) else f"{value:.1f}")

    interested_table = (
        artifacts.tracker_match_detail.loc[
            artifacts.tracker_match_detail["positive_response"].fillna(False),
            ["organization_name", "county_name", "final_region", "NCESSCH", "match_method", "match_score"],
        ]
        .copy()
        .rename(
            columns={
                "organization_name": "Organization",
                "county_name": "County",
                "final_region": "Region",
                "NCESSCH": "Matched School ID",
                "match_method": "Match Method",
                "match_score": "Match Score",
            }
        )
    )
    if not interested_table.empty:
        interested_table["Match Score"] = interested_table["Match Score"].map(lambda value: "" if pd.isna(value) else f"{float(value):.1f}")

    join_audit_cards = []
    for row in artifacts.join_audit_summary.itertuples():
        join_audit_cards.append(
            {
                "label": row.step,
                "value": f"{int(row.matched_records):,} / {int(row.total_records):,}",
                "rate": format_pct(row.match_rate),
                "notes": row.notes,
            }
        )

    sections = [
        {
            "id": "regional-footprint",
            "kicker": "Regional Footprint",
            "title": "Fixed JACO Groupings",
            "intro": "The project uses the fixed five-region JACO grouping structure provided for this work. The interactive map highlights anchor counties and allows hover inspection of each county’s assigned region.",
            "tabs": [],
            "tab_group": "",
            "figure_grid_class": "",
            "figures": [
                {
                    "title": "Interactive Regional Footprint",
                    "html": _plotly_html(region_map_fig),
                    "caption": "The fixed regional structure is shown analytically rather than treated as an optimization output.",
                }
            ],
            "tables": [
                {
                    "title": "Region Comparison Table",
                    "html": _build_sortable_table(region_table, "region-comparison-table"),
                    "table_id": "region-comparison-table",
                    "search_id": "region-comparison-search",
                }
            ],
            "notes": [{"title": "Footprint note", "body": "Anchor counties and grouped counties remain fixed to the JACO-defined footprint throughout the report."}],
        },
        {
            "id": "population-and-reach",
            "kicker": "Population and Reach",
            "title": "County and Region Reach Explorer",
            "intro": "These views combine statewide county context with the fixed JACO footprint to show where youth and total population are concentrated, and how school density relates to reach.",
            "tabs": [
                {
                    "title": "Region Reach",
                    "figures": [
                        {
                            "title": "Youth Population by Region",
                            "html": _plotly_html(youth_by_region_fig),
                            "caption": "This regional view uses shorter region labels and compact bar labels so the scale stays readable while still showing population values. Hover for exact youth counts.",
                        }
                    ],
                },
                *[{"title": figure["title"], "figures": [figure]} for figure in heatmap_figures]
            ],
            "tab_group": "heatmaps",
            "figure_grid_class": "",
            "figures": [],
            "tables": [],
            "notes": [{"title": "Hover guidance", "body": "County heatmaps now show only the most relevant supporting context for the active metric so the section stays easier to read."}],
        },
        {
            "id": "school-distribution",
            "kicker": "School Distribution",
            "title": "School Inventory and Outreach Location Explorer",
            "intro": "The school views focus on distribution, volume, and visibility. The map now shows only tracker-matched outreach schools so the geography stays readable and directly tied to outreach activity.",
            "tabs": [],
            "tab_group": "",
            "figure_grid_class": "",
            "figures": [
                {
                    "title": "Outreach School Map",
                    "html": school_map_report_html,
                    "caption": (
                        f"This map shows only the {format_int(outreach_mapped_schools)} tracker-matched outreach schools. Exact coordinates are used for "
                        f"{format_int(exact_school_points)} of those rows, including {format_int(interested_exact_points)} of the "
                        f"{format_int(metadata['tracker']['positive_matched_schools'])} Interested schools; the rest use clearly labeled county-based fallback placement."
                    ),
                }
            ],
            "tabs": [
                {
                    "title": "Schools by Region",
                    "figures": [
                        {
                            "title": "Mapped Schools by Region",
                            "html": _plotly_html(schools_by_region_fig),
                            "caption": "This view compares school inventory across the five fixed JACO regions.",
                        }
                    ],
                },
                {
                    "title": "School Types",
                    "figures": [
                        {
                            "title": "School Type Breakdown",
                            "html": _plotly_html(school_type_chart_fig),
                            "caption": "The stacked view helps distinguish whether regional school inventories are concentrated in similar or different school types.",
                        }
                    ],
                },
            ],
            "tab_group": "school-views",
            "tables": [],
            "notes": [
                {
                    "title": "Coordinate coverage",
                    "body": (
                        f"The original NCES extract still does not expose usable school latitude/longitude fields, but the added "
                        f"<code>ohio_schools_coordinates_v2.xlsx</code> workbook supplies exact coordinates for a subset of matched schools. "
                        f"Those exact points are used wherever available on the outreach-only map; only the remaining unmatched outreach schools fall back to transparent county-based placement. "
                        f"This keeps the map geographically useful without loading the full school inventory."
                    ),
                },
                {
                    "title": "Map interaction",
                    "body": "Hover tooltips show school name, county, region, outreach row count, interested row count, and whether the point comes from exact coordinates or approximate fallback placement.",
                },
            ],
        },
        {
            "id": "outreach-activity",
            "kicker": "Outreach Activity",
            "title": "Cold-Call Tracker Analysis",
            "intro": "Positive outreach is defined strictly as tracker rows where Outcome = Interested. The charts below show outcome mix, match quality, regional differences, and the matched interested-school subset.",
            "tabs": [
                {
                    "title": "Outcome Mix",
                    "figures": [
                        {
                            "title": "Outcome Distribution",
                            "html": _plotly_html(outcome_distribution_fig),
                            "caption": "Only the Interested category is treated as positive in the rest of the analysis.",
                        }
                    ],
                },
                {
                    "title": "Match Quality",
                    "figures": [
                        {
                            "title": "Tracker Match Methods",
                            "html": _plotly_html(tracker_match_summary_fig),
                            "caption": "This chart separates primary normalized-name county matches from unique-name fallback and unmatched rows.",
                        }
                    ],
                },
                {
                    "title": "Region Rates",
                    "figures": [
                        {
                            "title": "Interested Response Rate by Region",
                            "html": _plotly_html(interested_rate_by_region_fig),
                            "caption": "Rates are calculated as Interested outcomes divided by outreach records within each region.",
                        },
                        {
                            "title": "Outreach Records by Region",
                            "html": _plotly_html(outreach_records_by_region_fig),
                            "caption": "This volume view complements the response-rate view by showing where tracker activity is concentrated.",
                        },
                    ],
                },
            ],
            "tab_group": "outreach-views",
            "figure_grid_class": "",
            "figures": [],
            "tables": [
                {
                    "title": "Interested Outcome Records",
                    "html": _build_sortable_table(interested_table if not interested_table.empty else pd.DataFrame({"Note": ["No Interested rows were found."]}), "interested-table"),
                    "table_id": "interested-table",
                    "search_id": "interested-search",
                }
            ],
            "notes": [
                {"title": "Tracker match rate", "body": f"Tracker school-match rate: {format_pct(metadata['tracker']['school_match_rate'])}."},
                {"title": "Region assignment", "body": f"Tracker rows assigned to JACO regions: {format_pct(metadata['tracker']['region_assignment_rate'])}."},
                {"title": "Unmatched audit", "body": "Unmatched rows remain visible in the audit rather than being forced into a region or school view."},
            ],
        },
        {
            "id": "high-need-analysis",
            "kicker": "High-Need Analysis",
            "title": "High-Need Concentration and Match Coverage",
            "intro": "The high-need section separates raw high-need counts from proportional concentration and keeps the match diagnostics visible so coverage is not overstated.",
            "tabs": [
                {
                    "title": "Match Methods",
                    "figures": [
                        {
                            "title": "High-Need Match Summary",
                            "html": _plotly_html(high_need_match_methods_fig),
                            "caption": "Exact IRN and exact unique-name matching are shown separately from the district-level fallback pass.",
                        }
                    ],
                },
                {
                    "title": "Regional Counts",
                    "figures": [
                        {
                            "title": "High-Need Schools by Region",
                            "html": _plotly_html(high_need_by_region_fig),
                            "caption": "Counts are based on schools linked to the FY25 SSI workbook through the current match logic.",
                        }
                    ],
                },
                {
                    "title": "Regional Share",
                    "figures": [
                        {
                            "title": "High-Need Share by Region",
                            "html": _plotly_html(high_need_share_by_region_fig),
                            "caption": "The share view controls for school-volume differences across regions.",
                        }
                    ],
                },
            ],
            "tab_group": "high-need-views",
            "figure_grid_class": "",
            "figures": [],
            "tables": [],
            "notes": [
                {
                    "title": "Coverage note",
                    "body": f"Overall high-need match coverage: {format_pct((artifacts.high_need_match_summary['school_records'].sum() - artifacts.high_need_match_summary.loc[artifacts.high_need_match_summary['match_method'] == 'unmatched', 'school_records'].sum()) / artifacts.high_need_match_summary['school_records'].sum())}.",
                },
                {
                    "title": "Interpretation",
                    "body": "High-need results should be interpreted within the coverage limits of the FY25 SSI file and the current match logic.",
                },
            ],
        },
        {
            "id": "comparative-explorer",
            "kicker": "Comparative Explorer",
            "title": "Region Tradeoff Views",
            "intro": "These comparative charts are meant to help stakeholders inspect scale, need, and outreach together without turning the analysis into a prescriptive decision rule.",
            "tabs": [
                {
                    "title": "Scale vs Need",
                    "figures": [
                        {
                            "title": "Scale vs High-Need Concentration",
                            "html": _plotly_html(scale_vs_need_fig),
                            "caption": "Bubble size reflects total schools, allowing scale and concentration to be compared at the same time.",
                        }
                    ],
                },
                {
                    "title": "Scale vs Outreach",
                    "figures": [
                        {
                            "title": "Scale vs Outreach Activity",
                            "html": _plotly_html(scale_vs_outreach_fig),
                            "caption": "This view helps compare scale against current outreach intensity, normalized by school volume.",
                        }
                    ],
                },
                {
                    "title": "Anchor Distance",
                    "figures": [
                        {
                            "title": "Anchor Distance Summary",
                            "html": _plotly_html(anchor_distance_fig),
                            "caption": "Distances use county centroids and are intended as a transparent proximity screen, not a road-network model.",
                        }
                    ],
                },
            ],
            "tab_group": "tradeoff-views",
            "figure_grid_class": "",
            "figures": [],
            "tables": [],
            "notes": [{"title": "Interpretive note", "body": "These views are analytical and comparative only; they do not impose a preferred region or rank order."}],
        },
        {
            "id": "county-explorer",
            "kicker": "County Explorer",
            "title": "County-Level Interactive Table",
            "intro": "The county explorer makes it easier to inspect how reach, school inventory, outreach activity, and high-need concentration stack up at the county level across and beyond the JACO footprint.",
            "tabs": [],
            "tab_group": "",
            "figure_grid_class": "",
            "figures": [],
            "tables": [
                {
                    "title": "County Metrics",
                    "html": _build_sortable_table(county_table, "county-table"),
                    "table_id": "county-table",
                    "search_id": "county-search",
                }
            ],
            "notes": [{"title": "Table interaction", "body": "The search box and sortable columns make it easier to isolate specific counties or compare counties on one metric at a time."}],
        },
        {
            "id": "validation",
            "kicker": "Validation",
            "title": "Join Validation and Data Quality",
            "intro": "Join quality is intentionally kept visible because the report combines multiple public and operational data sources. The cards and audit tables below separate exact matches from fallback logic and show unmatched counts directly.",
            "tabs": [],
            "tab_group": "",
            "figure_grid_class": "",
            "figures": [],
            "tables": [
                {
                    "title": "Join Audit Summary",
                    "html": _build_sortable_table(
                        artifacts.join_audit_summary.assign(
                            match_rate=artifacts.join_audit_summary["match_rate"].map(format_pct),
                            matched_records=artifacts.join_audit_summary["matched_records"].map(format_int),
                            total_records=artifacts.join_audit_summary["total_records"].map(format_int),
                        ),
                        "join-audit-table",
                    ),
                    "table_id": "join-audit-table",
                    "search_id": "join-audit-search",
                },
                {
                    "title": "School Coordinate Match Summary",
                    "html": _build_sortable_table(
                        artifacts.school_coordinate_match_summary.rename(
                            columns={"coordinate_match_method": "Coordinate Match Method", "school_records": "School Records"}
                        ),
                        "coordinate-match-table",
                    ),
                    "table_id": "coordinate-match-table",
                    "search_id": "coordinate-match-search",
                }
            ],
            "notes": [],
        },
    ]

    validation_section = sections[-1]
    validation_section["notes"] = [
        {"title": "Exact vs fallback joins", "body": "Exact and fallback joins are separated in the audit rather than pooled together into a single match-rate number."},
        {"title": "Unmatched handling", "body": "Rows that cannot be mapped confidently remain visible as unmatched rather than being imputed into analytical sections."},
        {"title": "Interested rule", "body": "Cold-call positivity is defined narrowly and transparently as Outcome = Interested."},
        {
            "title": "Coordinate matching",
            "body": (
                f"School coordinate matching now uses the added <code>ohio_schools_coordinates_v2.xlsx</code> workbook. Within the JACO footprint, "
                f"{format_pct(metadata['schools']['exact_coordinate_match_rate_within_region'])} of mapped school rows now have exact coordinates from the source file or supplement. "
                f"The remaining rows stay visible on the map through a clearly labeled county-based fallback."
            ),
        },
        {
            "title": "Report table usage",
            "body": "The main report surfaces the cleaned summary tables that directly support interpretation. Intermediate technical tables are still written to <code>outputs/tables</code> for auditability without overwhelming the main report layout.",
        },
    ]

    validation_cards_html = "<div class='audit-grid'>" + "".join(
        [
            (
                f"<div class='audit-card'><div class='kicker'>{card['label']}</div>"
                f"<div class='value'>{card['value']}</div>"
                f"<div class='small'>Rate: {card['rate']}<br>{card['notes']}</div></div>"
            )
            for card in join_audit_cards
        ]
    ) + "</div>"
    sections[-1]["notes"].insert(0, {"title": "Join audit cards", "body": validation_cards_html})

    section_nav = [{"id": section["id"], "label": section["title"]} for section in sections]

    caveats = [
        {
            "title": "School coordinates",
            "body": "The NCES source file still does not expose usable school latitude and longitude fields, but the added school-coordinate workbook supplies exact coordinates for a matched subset of schools. The map uses those exact coordinates wherever available and uses transparent county-based fallback placement only for the remaining unmatched schools.",
        },
        {
            "title": "High-need coverage",
            "body": "High-need analysis is limited by the coverage of the FY25 SSI workbook and by match quality across identifiers and school names. Exact IRN matches are prioritized, exact unique-name matches are kept distinct, and the fallback district-level normalized-name match is shown separately in diagnostics.",
        },
        {
            "title": "Outreach interpretation",
            "body": "Interested outcomes are defined only as tracker rows where Outcome equals Interested. No additional stages or outcomes are counted as positive. Match-rate diagnostics are shown so the interested-school subset can be interpreted with the correct level of caution.",
        },
        {
            "title": "Anchor feasibility",
            "body": "The anchor feasibility screen uses county centroid distance from each anchor county rather than road-network travel time. It should be interpreted as a transparent spatial proxy, not as a final operating-time model.",
        },
    ]

    figure_exports: list[tuple[str, go.Figure]] = [
        ("region_map.html", region_map_fig),
        ("county_total_population_heatmap.html", total_population_heatmap_fig),
        ("county_youth_population_heatmap.html", youth_population_heatmap_fig),
        ("county_school_density_heatmap.html", school_density_heatmap_fig),
        ("county_high_need_count_heatmap.html", high_need_count_heatmap_fig),
        ("county_high_need_share_heatmap.html", high_need_share_heatmap_fig),
        ("county_outreach_activity_heatmap.html", outreach_activity_heatmap_fig),
        ("county_interested_outcomes_heatmap.html", interested_outcomes_heatmap_fig),
        ("youth_by_region.html", youth_by_region_fig),
        ("schools_by_region.html", schools_by_region_fig),
        ("school_type_breakdown.html", school_type_chart_fig),
        ("tracker_outcome_distribution.html", outcome_distribution_fig),
        ("tracker_match_summary.html", tracker_match_summary_fig),
        ("interested_response_rate_by_region.html", interested_rate_by_region_fig),
        ("outreach_records_by_region.html", outreach_records_by_region_fig),
        ("high_need_match_methods.html", high_need_match_methods_fig),
        ("high_need_schools_by_region.html", high_need_by_region_fig),
        ("high_need_share_by_region.html", high_need_share_by_region_fig),
        ("scale_vs_need.html", scale_vs_need_fig),
        ("scale_vs_outreach.html", scale_vs_outreach_fig),
        ("anchor_distance_summary.html", anchor_distance_fig),
    ]
    for filename, figure in figure_exports:
        _write_plotly_figure(figure, FIGURES_DIR / filename)
    if not outreach_points.empty:
        _write_outreach_map_png(outreach_points, county_geo, FIGURES_DIR / "outreach_school_map.png")

    html = HTML_TEMPLATE.render(
        plotly_js=get_plotlyjs(),
        summary_cards=summary_cards,
        summary_note=summary_note,
        overview_pills=overview_pills,
        section_nav=section_nav,
        sections=sections,
        caveats=caveats,
    )
    REPORT_PATH.write_text(html, encoding="utf-8")
