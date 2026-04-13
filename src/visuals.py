from __future__ import annotations

import hashlib
import textwrap

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.patheffects as pe
from shapely.geometry import Point

from src.cleaning import LOGGER, format_int, format_pct
from src.config import FEASIBILITY_RADIUS_MILES, FIGURES_DIR, REGION_COLORS
from src.mapping import anchor_points


plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.titlesize"] = 20
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["xtick.labelsize"] = 11
plt.rcParams["ytick.labelsize"] = 11


def save_figure(fig: plt.Figure, filename: str) -> str:
    path = FIGURES_DIR / filename
    fig.tight_layout(pad=2.0)
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"figures/{filename}"


def _clean_axes(ax: plt.Axes) -> None:
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)


def _wrap_region_label(label: str) -> str:
    return "\n".join(textwrap.wrap(label, width=26))


def _lighten_hex(color: str, factor: float = 0.75) -> tuple[float, float, float]:
    color = color.lstrip("#")
    channels = [int(color[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    return tuple(channel + (1 - channel) * factor for channel in channels)


def draw_region_map(region_geo: gpd.GeoDataFrame) -> str:
    fig, ax = plt.subplots(figsize=(11.6, 10.8))
    plot_df = region_geo.copy()
    plot_df["fill_color"] = plot_df["region"].map(REGION_COLORS).fillna("#DDDDDD")
    plot_df.plot(ax=ax, color=plot_df["fill_color"], edgecolor="white", linewidth=1.0)
    plot_df.boundary.plot(ax=ax, color="#4A4A4A", linewidth=0.45)

    anchors = anchor_points(plot_df)
    ax.scatter(anchors.geometry.x, anchors.geometry.y, marker="*", s=260, color="#111111", edgecolor="white", linewidth=0.8, zorder=5)
    for _, row in anchors.iterrows():
        ax.annotate(row["county_name"], (row.geometry.x, row.geometry.y), xytext=(5, 5), textcoords="offset points", fontsize=9, weight="bold")

    handles = [
        plt.Line2D([0], [0], marker="s", color=color, linestyle="", markersize=10, label=_wrap_region_label(label))
        for label, color in REGION_COLORS.items()
    ]
    handles.append(plt.Line2D([0], [0], marker="*", color="#111111", linestyle="", markersize=12, label="Anchor county"))
    legend = ax.legend(handles=handles, loc="lower left", frameon=True, title="JACO regions", borderpad=1.0, labelspacing=0.8)
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_edgecolor("#D8E1EA")
    ax.set_title("JACO Regional Grouping Strategy", pad=16)
    ax.text(0.5, -0.05, "Counties are grouped into the five fixed JACO service clusters.", transform=ax.transAxes, ha="center", fontsize=11, color="#444444")
    ax.axis("off")
    return save_figure(fig, "region_map.png")


def draw_county_heatmap(county_geo: gpd.GeoDataFrame, value_col: str, title: str, subtitle: str, filename: str, cmap: str = "Blues") -> str:
    fig, ax = plt.subplots(figsize=(11.6, 10.8))
    county_geo.plot(
        column=value_col,
        ax=ax,
        cmap=cmap,
        linewidth=0.5,
        edgecolor="white",
        legend=True,
        legend_kwds={"shrink": 0.7, "pad": 0.02},
        missing_kwds={"color": "#F0F0F0"},
    )
    county_geo.boundary.plot(ax=ax, color="#4A4A4A", linewidth=0.35)
    ax.set_title(title, pad=16)
    ax.text(0.5, -0.05, subtitle, transform=ax.transAxes, ha="center", fontsize=11, color="#444444")
    ax.axis("off")
    return save_figure(fig, filename)


def draw_horizontal_bar(df: pd.DataFrame, value_col: str, title: str, subtitle: str, filename: str, value_format: str = "int") -> str:
    plot_df = df.sort_values(value_col, ascending=True).copy()
    plot_df["region_label"] = plot_df["region"].map(_wrap_region_label)
    fig, ax = plt.subplots(figsize=(12.2, 6.8))
    bars = ax.barh(plot_df["region_label"], plot_df[value_col], color=plot_df["region"].map(REGION_COLORS), height=0.68)
    _clean_axes(ax)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.set_title(title, pad=16)
    ax.set_xlabel("")
    ax.set_ylabel("")
    max_value = float(plot_df[value_col].max()) if len(plot_df) else 0
    for bar, value in zip(bars, plot_df[value_col]):
        label = format_int(value) if value_format == "int" else format_pct(value)
        ax.text(float(value) + max_value * 0.012, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=11, weight="bold", color="#243B53")
    ax.text(0, -0.14, subtitle, transform=ax.transAxes, fontsize=11, color="#4A4A4A")
    return save_figure(fig, filename)


def draw_high_need_comparison(df: pd.DataFrame) -> str:
    plot_df = df.sort_values("high_need_schools", ascending=True).copy()
    plot_df["region_label"] = plot_df["region"].map(_wrap_region_label)
    fig, ax = plt.subplots(figsize=(12.2, 7.2))
    total_bars = ax.barh(plot_df["region_label"], plot_df["total_schools"], color="#D5DEE8", label="Total schools", height=0.68)
    need_bars = ax.barh(plot_df["region_label"], plot_df["high_need_schools"], color="#E15759", label="High-need schools", height=0.44)
    _clean_axes(ax)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.legend(frameon=False, loc="lower right", fontsize=11)
    ax.set_title("High-Need Schools by Region", pad=16)
    ax.set_xlabel("")
    ax.set_ylabel("")
    max_value = float(plot_df["total_schools"].max()) if len(plot_df) else 0
    for total_bar, need_bar, total, need in zip(total_bars, need_bars, plot_df["total_schools"], plot_df["high_need_schools"]):
        ax.text(float(total) + max_value * 0.012, total_bar.get_y() + total_bar.get_height() / 2, format_int(total), va="center", fontsize=10, color="#5B7083")
        ax.text(float(need) + max_value * 0.012, need_bar.get_y() + need_bar.get_height() / 2, format_int(need), va="center", fontsize=11, weight="bold", color="#912F2F")
    return save_figure(fig, "high_need_by_region.png")


def draw_school_points_placeholder(message: str) -> str:
    fig, ax = plt.subplots(figsize=(11.4, 6.5))
    ax.axis("off")
    ax.text(0.5, 0.62, "School Point Map Not Generated", ha="center", va="center", fontsize=20, weight="bold", color="#1F2D3D")
    ax.text(0.5, 0.42, message, ha="center", va="center", fontsize=12, color="#4A4A4A", wrap=True)
    return save_figure(fig, "school_points_map.png")


def _stable_seed(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _normalize_school_id(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def draw_school_points_map(region_geo: gpd.GeoDataFrame, schools: pd.DataFrame, tracker_matches: pd.DataFrame) -> str:
    plot_schools = schools[schools["region"].notna() & schools["county_name"].notna()].copy()
    if plot_schools.empty:
        raise ValueError("No schools available for plotting after county and region assignment.")

    positive_ids = set(
        tracker_matches.loc[
            tracker_matches["positive_response"].fillna(False) & tracker_matches["NCESSCH"].notna(),
            "NCESSCH",
        ].map(_normalize_school_id)
    )
    unmatched_tracker_rows = int(tracker_matches["NCESSCH"].isna().sum())
    LOGGER.info("School map validation: tracker rows unmatched to schools = %s", unmatched_tracker_rows)

    county_counts = (
        plot_schools.groupby("county_name", as_index=False)
        .agg(school_count=("NCESSCH", "count"))
        .sort_values(["school_count", "county_name"], ascending=[False, True])
    )
    LOGGER.info("School map validation: schools per county\n%s", county_counts.to_string(index=False))

    plot_schools["is_positive_response_school"] = plot_schools["NCESSCH"].map(_normalize_school_id).isin(positive_ids)
    positive_count = int(plot_schools["is_positive_response_school"].sum())
    LOGGER.info("School map validation: positive schools plotted = %s", positive_count)
    if positive_count == 0:
        LOGGER.warning("No positive schools found — check classification logic")

    projected_counties = region_geo.to_crs(3734).copy()
    projected_counties["centroid"] = projected_counties.geometry.centroid
    projected_counties["bounds"] = projected_counties.geometry.bounds.values.tolist()
    county_lookup = projected_counties.set_index("county_name")
    county_positive_counts = plot_schools.groupby("county_name")["is_positive_response_school"].sum().to_dict()

    point_records = []
    for row in plot_schools.itertuples():
        if row.county_name not in county_lookup.index:
            continue
        county = county_lookup.loc[row.county_name]
        centroid = county["centroid"]
        minx, miny, maxx, maxy = county["bounds"]
        width = max(maxx - minx, 1.0)
        height = max(maxy - miny, 1.0)
        positive_multiplier = 1.25 if county_positive_counts.get(row.county_name, 0) >= 2 else 1.0
        small_scale_x = min(width * 0.11 * positive_multiplier, 9000.0)
        small_scale_y = min(height * 0.11 * positive_multiplier, 9000.0)
        seed = _stable_seed(f"{row.SCH_NAME}|{row.county_name}|{row.NCESSCH}")
        ring = 0.65 + (((seed // 100) % 7) / 10.0)
        offset_x = ((seed % 10) - 4.5) * small_scale_x / 4.5 * ring
        offset_y = (((seed // 10) % 10) - 4.5) * small_scale_y / 4.5 * ring
        point_records.append(
            {
                "NCESSCH": row.NCESSCH,
                "SCH_NAME": row.SCH_NAME,
                "region": row.region,
                "county_name": row.county_name,
                "is_positive_response_school": row.is_positive_response_school,
                "geometry": Point(centroid.x + offset_x, centroid.y + offset_y),
            }
        )

    points = gpd.GeoDataFrame(point_records, geometry="geometry", crs=projected_counties.crs).to_crs(region_geo.crs)
    if points.empty:
        raise ValueError("No schools plotted after generating approximate county-based points.")

    fig, ax = plt.subplots(figsize=(12.8, 11.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FBFCFE")
    region_fill = region_geo["region"].map(REGION_COLORS).map(lambda color: _lighten_hex(color, 0.82) if isinstance(color, str) else (0.93, 0.94, 0.96))
    region_geo.plot(ax=ax, color=region_fill, edgecolor="white", linewidth=0.85, alpha=0.95)
    region_geo.boundary.plot(ax=ax, color="#6B7280", linewidth=0.55)
    minx, miny, maxx, maxy = region_geo.total_bounds
    width = maxx - minx
    height = maxy - miny
    ax.set_xlim(minx - width * 0.03, maxx + width * 0.68)
    ax.set_ylim(miny - height * 0.04, maxy + height * 0.04)

    base = points[~points["is_positive_response_school"]]
    positive = points[points["is_positive_response_school"]]
    ax.scatter(base.geometry.x, base.geometry.y, s=9, color="#B8C2CC", alpha=0.34, linewidths=0, label="All schools", zorder=3)
    if not positive.empty:
        ax.scatter(
            positive.geometry.x,
            positive.geometry.y,
            s=42,
            color="#1F9D55",
            alpha=0.99,
            edgecolors="#0F5132",
            linewidths=0.7,
            label="Positive outreach schools",
            zorder=4,
        )
        LOGGER.info("School map styling: positive school labels intentionally omitted for a cleaner presentation view.")

    legend = ax.legend(loc="lower left", frameon=True, borderpad=0.9, labelspacing=0.65, handletextpad=0.7, fontsize=11)
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_edgecolor("#CBD5E1")
    ax.set_title("School Distribution & Outreach Visualization", pad=18, fontsize=22, color="#0F172A")
    ax.text(
        0.5,
        -0.05,
        "School locations are approximate. Positive outreach schools are highlighted in green.",
        transform=ax.transAxes,
        ha="center",
        fontsize=11.5,
        color="#475569",
    )
    ax.axis("off")

    return save_figure(fig, "schools_map.png")


def draw_outreach_map(region_geo: gpd.GeoDataFrame, region_summary: pd.DataFrame, tracker_metadata: dict[str, object]) -> str:
    plot_df = region_geo.merge(region_summary[["region", "outreach_records", "positive_response_rate"]], on="region", how="left")
    fig, ax = plt.subplots(figsize=(11.6, 10.8))
    value_col = "positive_response_rate" if tracker_metadata["suitable_for_school_overlay"] else "outreach_records"
    cmap = "Greens" if tracker_metadata["suitable_for_school_overlay"] else "Oranges"
    plot_df.plot(
        column=value_col,
        ax=ax,
        cmap=cmap,
        linewidth=0.6,
        edgecolor="white",
        legend=True,
        legend_kwds={"shrink": 0.7, "pad": 0.02},
        missing_kwds={"color": "#EFEFEF"},
    )
    plot_df.boundary.plot(ax=ax, color="#4A4A4A", linewidth=0.35)
    ax.set_title("Outreach Activity by Region", pad=16)
    note = (
        "Map is based on positive-response rate because tracker-school matching quality is acceptable."
        if tracker_metadata["suitable_for_school_overlay"]
        else "Map falls back to aggregate outreach counts because school-level overlay quality is not strong enough."
    )
    ax.text(0.5, -0.05, note, transform=ax.transAxes, ha="center", fontsize=11, color="#444444")
    ax.axis("off")
    return save_figure(fig, "outreach_map.png")


def draw_strategy_tradeoff(region_summary: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(11.8, 7.2))
    ax.scatter(region_summary["youth_population"], region_summary["high_need_share"], s=region_summary["total_schools"] * 2.2, color=region_summary["region"].map(REGION_COLORS), alpha=0.9)
    _clean_axes(ax)
    ax.grid(True, linestyle="--", alpha=0.2)
    ax.set_title("Scale vs. Need Tradeoff by Region", pad=16)
    ax.set_xlabel("Youth population")
    ax.set_ylabel("High-need school share")
    for _, row in region_summary.iterrows():
        ax.annotate(row["region"].replace("Group ", "G"), (row["youth_population"], row["high_need_share"]), xytext=(8, 8), textcoords="offset points", fontsize=10, weight="bold")
    return save_figure(fig, "strategy_tradeoff_matrix.png")


def draw_feasibility_check(feasibility_by_region: pd.DataFrame) -> str:
    plot_df = feasibility_by_region.sort_values("max_anchor_distance_miles", ascending=True).copy()
    plot_df["region_label"] = plot_df["region"].map(_wrap_region_label)
    fig, ax = plt.subplots(figsize=(12.2, 6.8))
    colors = plot_df["feasible_1hr_proxy"].map({True: "#2E8B57", False: "#D94841"})
    bars = ax.barh(plot_df["region_label"], plot_df["max_anchor_distance_miles"], color=colors, height=0.68)
    ax.axvline(FEASIBILITY_RADIUS_MILES, color="#243B53", linestyle="--", linewidth=1.6, label=f"{int(FEASIBILITY_RADIUS_MILES)}-mile proxy threshold")
    _clean_axes(ax)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.set_title("1-Hour Radius Feasibility Check", pad=16)
    ax.set_xlabel("Maximum anchor-to-county centroid distance (miles)")
    ax.set_ylabel("")
    for bar, distance, feasible in zip(bars, plot_df["max_anchor_distance_miles"], plot_df["feasible_1hr_proxy"]):
        label = f"{distance:.1f} mi | {'Feasible' if feasible else 'Stretch'}"
        ax.text(float(distance) + FEASIBILITY_RADIUS_MILES * 0.02, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=10, weight="bold", color="#243B53")
    ax.legend(frameon=False, loc="lower right")
    ax.text(
        0,
        -0.14,
        f"Proxy uses county centroid distance from each anchor county. Counties at or below {int(FEASIBILITY_RADIUS_MILES)} miles are treated as broadly feasible for a 1-hour model.",
        transform=ax.transAxes,
        fontsize=11,
        color="#4A4A4A",
    )
    return save_figure(fig, "one_hour_radius_feasibility.png")


def render_html_summary_table(df: pd.DataFrame) -> str:
    display = df.copy()
    for column in ["total_population", "youth_population", "total_schools", "high_need_schools", "outreach_records", "positive_responses"]:
        if column in display.columns:
            display[column] = display[column].map(format_int)
    for column in ["high_need_share", "positive_response_rate", "school_match_rate_within_region"]:
        if column in display.columns:
            display[column] = display[column].map(format_pct)
    return display.to_html(index=False, classes=["summary-table"], border=0)
