import marimo

__generated_with = "0.19.5"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import geopandas as gpd
    import matplotlib.pyplot as plt
    import plotly.express as px
    import plotly.graph_objects as go
    from pathlib import Path
    import json

    pop_df = pd.read_csv(Path("JACO.csv"))

    mo.vstack([
        mo.md("## Step 1: JACO population data loaded"),
        mo.md(f"**Rows:** {pop_df.shape[0]:,}  \n**Columns:** {pop_df.shape[1]:,}"),
        mo.ui.table(pop_df.head(10))
    ])
    return go, gpd, json, mo, pd, plt, pop_df, px


@app.cell
def _():
    return


@app.cell
def _(mo, pop_df):
    latest_year = pop_df["YEAR"].max()

    ohio_county_pop = (
        pop_df[
            (pop_df["STATE"] == 39) &
            (pop_df["SUMLEV"] == 50) &
            (pop_df["YEAR"] == latest_year) &
            (pop_df["AGEGRP"] == 0)
        ]
        .copy()
    )

    ohio_county_pop["county_name"] = (
        ohio_county_pop["CTYNAME"]
        .astype(str)
        .str.replace(" County", "", regex=False)
        .str.strip()
    )
    ohio_county_pop["county_fips"] = ohio_county_pop["COUNTY"].astype(str).str.zfill(3)
    ohio_county_pop["geoid"] = "39" + ohio_county_pop["county_fips"]

    mo.vstack([
        mo.md("## Step 2: Ohio county population cleaned"),
        mo.md(f"**Latest year in file:** {latest_year}"),
        mo.md(f"**Ohio counties detected:** {len(ohio_county_pop)}"),
        mo.ui.table(
            ohio_county_pop[
                ["CTYNAME", "county_name", "COUNTY", "county_fips", "geoid", "TOT_POP"]
            ].sort_values("TOT_POP", ascending=False).head(15)
        )
    ])
    return latest_year, ohio_county_pop


@app.cell
def _():
    return


@app.cell
def _(gpd, mo, plt):
    shape_url = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"

    us_counties = gpd.read_file(shape_url)
    ohio_county_shapes = us_counties[us_counties["STATEFP"] == "39"].copy()
    ohio_county_shapes = ohio_county_shapes[["GEOID", "NAME", "geometry"]].copy()

    fig_shapes, ax_shapes = plt.subplots(figsize=(8, 8))
    ohio_county_shapes.plot(ax=ax_shapes, edgecolor="black", linewidth=0.6, color="#f7f7f7")
    ax_shapes.set_title("Ohio County Boundaries", fontsize=14)
    ax_shapes.axis("off")
    plt.tight_layout()

    mo.vstack([
        mo.md("## Step 3: Ohio county shapes loaded"),
        mo.md(f"**Ohio county polygons:** {len(ohio_county_shapes)}"),
        mo.as_html(fig_shapes)
    ])
    return (ohio_county_shapes,)


@app.cell
def _():
    return


@app.cell
def _(mo, ohio_county_pop, ohio_county_shapes, plt):
    ohio_pop_map = ohio_county_shapes.merge(
        ohio_county_pop[["geoid", "county_name", "TOT_POP"]],
        left_on="GEOID",
        right_on="geoid",
        how="left"
    )

    matched_counties = int(ohio_pop_map["TOT_POP"].notna().sum())
    missing_counties = int(ohio_pop_map["TOT_POP"].isna().sum())

    fig_pop_static, ax_pop_static = plt.subplots(figsize=(8, 8))
    ohio_pop_map.plot(
        column="TOT_POP",
        ax=ax_pop_static,
        cmap="viridis",
        legend=True,
        edgecolor="black",
        linewidth=0.4,
        missing_kwds={"color": "#dddddd", "label": "Missing"}
    )
    ax_pop_static.set_title("Ohio County Population", fontsize=14)
    ax_pop_static.axis("off")
    plt.tight_layout()

    mo.vstack([
        mo.md("## Step 4: Population joined to county map"),
        mo.md(f"**Matched counties:** {matched_counties}  \n**Missing counties:** {missing_counties}"),
        mo.as_html(fig_pop_static)
    ])
    return (ohio_pop_map,)


@app.cell
def _():
    return


@app.cell
def _(json, ohio_pop_map, px):
    ohio_pop_geojson = json.loads(ohio_pop_map.to_json())

    ohio_pop_plot_df = ohio_pop_map[["GEOID", "NAME", "TOT_POP"]].copy()

    fig_total_population = px.choropleth(
        ohio_pop_plot_df,
        geojson=ohio_pop_geojson,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="TOT_POP",
        hover_name="NAME",
        hover_data={"TOT_POP": ":,"},
        color_continuous_scale="Viridis",
        title="Ohio County Population Heatmap"
    )

    fig_total_population.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig_total_population.update_layout(
        height=750,
        margin={"r": 10, "t": 60, "l": 10, "b": 10},
        title_x=0.5
    )

    fig_total_population
    return


@app.cell
def _():
    return


@app.cell
def _(pd):
    jaco_region_lookup = pd.DataFrame({
        "county_name": [
            "Franklin", "Delaware", "Union", "Fairfield", "Pickaway", "Fayette",
            "Licking", "Knox", "Perry",
            "Athens", "Hocking", "Vinton", "Meigs", "Morgan", "Washington",
            "Jackson", "Gallia", "Pike", "Ross",
            "Guernsey", "Noble", "Monroe", "Belmont", "Harrison", "Jefferson"
        ],
        "region": [
            "Group 1 — Columbus Core", "Group 1 — Columbus Core", "Group 1 — Columbus Core",
            "Group 1 — Columbus Core", "Group 1 — Columbus Core", "Group 1 — Columbus Core",

            "Group 2 — Newark / East-Central", "Group 2 — Newark / East-Central", "Group 2 — Newark / East-Central",

            "Group 3 — Southeast Cluster", "Group 3 — Southeast Cluster", "Group 3 — Southeast Cluster",
            "Group 3 — Southeast Cluster", "Group 3 — Southeast Cluster", "Group 3 — Southeast Cluster",

            "Group 4 — Southern Corridor", "Group 4 — Southern Corridor", "Group 4 — Southern Corridor",
            "Group 4 — Southern Corridor",

            "Group 5 — Eastern Edge", "Group 5 — Eastern Edge", "Group 5 — Eastern Edge",
            "Group 5 — Eastern Edge", "Group 5 — Eastern Edge", "Group 5 — Eastern Edge"
        ],
        "anchor_county": [
            "Franklin", "Franklin", "Franklin", "Franklin", "Franklin", "Franklin",
            "Licking", "Licking", "Licking",
            "Athens", "Athens", "Athens", "Athens", "Athens", "Athens",
            "Jackson", "Jackson", "Jackson", "Jackson",
            "Guernsey", "Guernsey", "Guernsey", "Guernsey", "Guernsey", "Guernsey"
        ]
    })
    return (jaco_region_lookup,)


@app.cell
def _():
    return


@app.cell
def _(jaco_region_lookup, json, ohio_pop_map, px):
    ohio_region_map = ohio_pop_map.copy()
    ohio_region_map["county_name"] = ohio_region_map["NAME"].astype(str).str.strip()

    ohio_region_map = ohio_region_map.merge(
        jaco_region_lookup,
        on="county_name",
        how="left"
    )

    ohio_region_map["is_anchor"] = ohio_region_map["county_name"] == ohio_region_map["anchor_county"]
    ohio_region_map["region_label"] = ohio_region_map["region"].fillna("Other Ohio Counties")

    region_color_map = {
        "Group 1 — Columbus Core": "#1b9e77",
        "Group 2 — Newark / East-Central": "#d95f02",
        "Group 3 — Southeast Cluster": "#7570b3",
        "Group 4 — Southern Corridor": "#e7298a",
        "Group 5 — Eastern Edge": "#66a61e",
        "Other Ohio Counties": "#d9d9d9"
    }

    ohio_region_geojson = json.loads(ohio_region_map.to_json())

    fig_region_map = px.choropleth(
        ohio_region_map,
        geojson=ohio_region_geojson,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="region_label",
        hover_name="NAME",
        hover_data={
            "anchor_county": True,
            "TOT_POP": ":,",
            "GEOID": False,
            "region": False,
            "county_name": False
        },
        color_discrete_map=region_color_map,
        title="JACO County Group Map"
    )

    fig_region_map.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig_region_map.update_layout(
        height=760,
        margin={"r": 10, "t": 60, "l": 10, "b": 10},
        title_x=0.5,
        legend_title_text="JACO Region"
    )

    fig_region_map
    return fig_region_map, ohio_region_map, region_color_map


@app.cell
def _():
    return


@app.cell
def _(fig_region_map, go, ohio_region_map):
    anchor_points = ohio_region_map[ohio_region_map["is_anchor"]].copy()

    anchor_points_proj = anchor_points.to_crs(epsg=3857).copy()
    anchor_points_proj["centroid"] = anchor_points_proj.geometry.centroid
    anchor_points_ll = anchor_points_proj.set_geometry("centroid").to_crs(epsg=4326)

    anchor_points_ll["lon"] = anchor_points_ll.geometry.x
    anchor_points_ll["lat"] = anchor_points_ll.geometry.y

    fig_region_with_anchors = go.Figure(fig_region_map)

    fig_region_with_anchors.add_trace(
        go.Scattergeo(
            lon=anchor_points_ll["lon"],
            lat=anchor_points_ll["lat"],
            text=anchor_points_ll["county_name"],
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=11,
                color="black",
                line=dict(width=1.5, color="white")
            ),
            name="Anchor Counties",
            hovertemplate="<b>Anchor County:</b> %{text}<extra></extra>"
        )
    )

    fig_region_with_anchors.update_layout(
        title="JACO Regions with Anchor Counties",
        title_x=0.5,
        height=780
    )

    fig_region_with_anchors
    return


@app.cell
def _():
    return


@app.cell
def _(mo, ohio_region_map):
    region_summary = (
        ohio_region_map[ohio_region_map["region"].notna()]
        .groupby("region", as_index=False)
        .agg(
            anchor_county=("anchor_county", "first"),
            county_count=("county_name", "count"),
            total_population=("TOT_POP", "sum"),
            avg_population=("TOT_POP", "mean"),
            counties=("county_name", lambda x: ", ".join(sorted(x)))
        )
        .sort_values("total_population", ascending=False)
    )

    region_summary_display = region_summary.copy()
    for col in ["total_population", "avg_population"]:
        region_summary_display[col] = (
            region_summary_display[col]
            .round(0)
            .astype(int)
            .map(lambda x: f"{x:,}")
        )

    mo.vstack([
        mo.md("## Step 9: Executive summary by region"),
        mo.ui.table(region_summary_display)
    ])
    return (region_summary,)


@app.cell
def _():
    return


@app.cell
def _(px, region_summary):
    region_pop_chart_df = region_summary.copy().sort_values("total_population", ascending=True)

    fig_region_population_bar = px.bar(
        region_pop_chart_df,
        x="total_population",
        y="region",
        orientation="h",
        text="total_population",
        title="Total Population by JACO Region",
        color="region"
    )

    fig_region_population_bar.update_traces(
        texttemplate="%{text:,}",
        textposition="outside"
    )

    fig_region_population_bar.update_layout(
        height=520,
        margin={"r": 30, "t": 60, "l": 10, "b": 10},
        showlegend=False,
        title_x=0.5,
        xaxis_title="Population",
        yaxis_title=""
    )

    fig_region_population_bar
    return


@app.cell
def _():
    return


@app.cell
def _(mo, pop_df):
    age_group_preview = pop_df[["AGEGRP"]].drop_duplicates().sort_values("AGEGRP")

    mo.vstack([
        mo.md("## Step 11: AGEGRP codes in source file"),
        mo.ui.table(age_group_preview)
    ])
    return


@app.cell
def _():
    return


@app.cell
def _(latest_year, mo, pop_df):
    youth_age_groups = [2, 3, 4]

    youth_population_rows = (
        pop_df[
            (pop_df["STATE"] == 39) &
            (pop_df["SUMLEV"] == 50) &
            (pop_df["YEAR"] == latest_year) &
            (pop_df["AGEGRP"].isin(youth_age_groups))
        ]
        .copy()
    )

    youth_population_rows["county_name"] = (
        youth_population_rows["CTYNAME"]
        .astype(str)
        .str.replace(" County", "", regex=False)
        .str.strip()
    )

    youth_population_by_county = (
        youth_population_rows
        .groupby("county_name", as_index=False)
        .agg(youth_population=("TOT_POP", "sum"))
    )

    mo.vstack([
        mo.md("## Step 12: Youth population by county"),
        mo.ui.table(
            youth_population_by_county
            .sort_values("youth_population", ascending=False)
            .head(15)
        )
    ])
    return (youth_population_by_county,)


@app.cell
def _():
    return


@app.cell
def _(json, ohio_county_shapes, px, youth_population_by_county):
    ohio_youth_map = ohio_county_shapes.merge(
        youth_population_by_county,
        left_on="NAME",
        right_on="county_name",
        how="left"
    )

    ohio_youth_geojson = json.loads(ohio_youth_map.to_json())

    fig_youth_heatmap = px.choropleth(
        ohio_youth_map,
        geojson=ohio_youth_geojson,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="youth_population",
        hover_name="NAME",
        hover_data={"youth_population": ":,"},
        color_continuous_scale="Viridis",
        title="Ohio Youth Population Heatmap"
    )

    fig_youth_heatmap.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig_youth_heatmap.update_layout(
        height=750,
        margin={"r": 10, "t": 60, "l": 10, "b": 10},
        title_x=0.5
    )

    fig_youth_heatmap
    return


@app.cell
def _():
    return


@app.cell
def _(mo, ohio_region_map, youth_population_by_county):
    ohio_region_youth = ohio_region_map.merge(
        youth_population_by_county,
        on="county_name",
        how="left"
    )

    youth_population_by_region = (
        ohio_region_youth[ohio_region_youth["region"].notna()]
        .groupby("region", as_index=False)
        .agg(
            anchor_county=("anchor_county", "first"),
            county_count=("county_name", "count"),
            youth_population_5_20=("youth_population", "sum")
        )
        .sort_values("youth_population_5_20", ascending=False)
    )

    youth_display = youth_population_by_region.copy()
    youth_display["youth_population_5_20"] = (
        youth_display["youth_population_5_20"]
        .round(0)
        .astype(int)
        .map(lambda x: f"{x:,}")
    )

    mo.vstack([
        mo.md("## Step 14: Youth population by JACO region"),
        mo.ui.table(youth_display)
    ])
    return (youth_population_by_region,)


@app.cell
def _():
    return


@app.cell
def _(px, youth_population_by_region):
    youth_chart_df = youth_population_by_region.copy().sort_values("youth_population_5_20", ascending=True)

    fig_youth_region_bar = px.bar(
        youth_chart_df,
        x="youth_population_5_20",
        y="region",
        orientation="h",
        text="youth_population_5_20",
        title="Youth Population (Ages 5–20 Approx.) by JACO Region",
        color="region"
    )

    fig_youth_region_bar.update_traces(
        texttemplate="%{text:,}",
        textposition="outside"
    )

    fig_youth_region_bar.update_layout(
        height=520,
        margin={"r": 30, "t": 60, "l": 10, "b": 10},
        showlegend=False,
        title_x=0.5,
        xaxis_title="Youth Population",
        yaxis_title=""
    )

    fig_youth_region_bar
    return


@app.cell
def _():
    return


@app.cell
def _(mo, pd):
    nces_raw_df = pd.read_csv("ccd_sch_029_2425_w_1a_073025.csv", low_memory=False)

    title1_raw_df = pd.read_excel(
        "FY25 TI NC SSI Sec 1003i Report FINAL.xlsx",
        sheet_name="Building Allocations",
        header=1
    )

    mo.vstack([
        mo.md("## Step 16: NCES and Title I data loaded"),
        mo.md(f"**NCES rows:** {nces_raw_df.shape[0]:,}  \n**Title I rows:** {title1_raw_df.shape[0]:,}"),
        mo.ui.table(nces_raw_df.head(5)),
        mo.ui.table(title1_raw_df.head(5))
    ])
    return nces_raw_df, title1_raw_df


@app.cell
def _():
    return


@app.cell
def _(mo, nces_raw_df, pd, title1_raw_df):
    ohio_schools_df = nces_raw_df[nces_raw_df["ST"] == "OH"].copy()

    possible_lat_cols = ["LAT", "LATCOD", "latitude", "Latitude"]
    possible_lon_cols = ["LON", "LONCOD", "longitude", "Longitude"]

    lat_col = next((c for c in possible_lat_cols if c in ohio_schools_df.columns), None)
    lon_col = next((c for c in possible_lon_cols if c in ohio_schools_df.columns), None)

    keep_cols = [
        "NCESSCH", "SCH_NAME", "LEA_NAME", "LCITY", "LSTATE", "LZIP", "ST", "STATENAME", "LEVEL"
    ]
    if lat_col:
        keep_cols.append(lat_col)
    if lon_col:
        keep_cols.append(lon_col)

    ohio_schools_df = ohio_schools_df[keep_cols].copy()

    ohio_schools_df["school_name_clean"] = (
        ohio_schools_df["SCH_NAME"].astype(str).str.lower().str.strip()
    )
    ohio_schools_df["district_name_clean"] = (
        ohio_schools_df["LEA_NAME"].astype(str).str.lower().str.strip()
    )
    ohio_schools_df["zip5"] = (
        ohio_schools_df["LZIP"].astype(str).str.extract(r"(\d{5})", expand=False)
    )

    ohio_schools_df["school_lat"] = pd.to_numeric(ohio_schools_df[lat_col], errors="coerce") if lat_col else pd.NA
    ohio_schools_df["school_lon"] = pd.to_numeric(ohio_schools_df[lon_col], errors="coerce") if lon_col else pd.NA

    title1_clean_df = title1_raw_df[
        ["LEA IRN", "LEA Name", "Building IRN", "Building Name", "TI NC SSI Students Served"]
    ].copy()

    title1_clean_df["school_name_clean"] = (
        title1_clean_df["Building Name"].astype(str).str.lower().str.strip()
    )
    title1_clean_df["high_need"] = (
        pd.to_numeric(title1_clean_df["TI NC SSI Students Served"], errors="coerce")
        .fillna(0) > 0
    )

    mo.vstack([
        mo.md("## Step 17: School and Title I data cleaned"),
        mo.md(f"**Latitude column used:** {lat_col}  \n**Longitude column used:** {lon_col}"),
        mo.ui.table(
            ohio_schools_df[
                ["SCH_NAME", "LEA_NAME", "LCITY", "zip5", "school_lat", "school_lon"]
            ].head(10)
        )
    ])
    return ohio_schools_df, title1_clean_df


@app.cell
def _():
    return


@app.cell
def _(mo, ohio_county_shapes, ohio_schools_df, pd):
    zip_tract_df = pd.read_excel("ZIP_TRACT_122025.xlsx", dtype=str)
    zip_tract_df.columns = zip_tract_df.columns.str.strip()

    zip_tract_df["ZIP"] = zip_tract_df["ZIP"].astype(str).str.extract(r"(\d{5})", expand=False)
    zip_tract_df["county_fips"] = zip_tract_df["TRACT"].astype(str).str[:5]

    ratio_col = "RES_RATIO" if "RES_RATIO" in zip_tract_df.columns else "TOT_RATIO"
    zip_tract_df[ratio_col] = pd.to_numeric(zip_tract_df[ratio_col], errors="coerce")

    zip_to_county_best = (
        zip_tract_df
        .sort_values(["ZIP", ratio_col], ascending=[True, False])
        .drop_duplicates(subset=["ZIP"])
        .copy()
    )

    county_lookup = ohio_county_shapes[["GEOID", "NAME"]].copy()
    county_lookup["county_fips"] = county_lookup["GEOID"].str[:5]
    county_lookup = county_lookup.rename(columns={"NAME": "county_name"})

    zip_to_county_best = zip_to_county_best.merge(
        county_lookup[["county_fips", "county_name"]],
        on="county_fips",
        how="left"
    )

    schools_with_county_df = ohio_schools_df.merge(
        zip_to_county_best[["ZIP", "county_name"]].rename(columns={"ZIP": "zip5"}),
        on="zip5",
        how="left"
    )

    mo.vstack([
        mo.md("## Step 18: Schools mapped to counties"),
        mo.md(f"**Schools with county match:** {schools_with_county_df['county_name'].notna().sum():,}"),
        mo.ui.table(
            schools_with_county_df[["SCH_NAME", "LCITY", "zip5", "county_name"]].head(15)
        )
    ])
    return (schools_with_county_df,)


@app.cell
def _(jaco_region_lookup, mo, schools_with_county_df):
    schools_with_region_df = schools_with_county_df.merge(
        jaco_region_lookup,
        on="county_name",
        how="left"
    )

    mo.vstack([
        mo.md("## Step 19: Schools mapped to JACO regions"),
        mo.md(f"**Schools inside JACO regions:** {schools_with_region_df['region'].notna().sum():,}"),
        mo.ui.table(
            schools_with_region_df[["SCH_NAME", "county_name", "region", "anchor_county"]].head(20)
        )
    ])
    return (schools_with_region_df,)


@app.cell
def _():
    return


@app.cell
def _(mo, schools_with_region_df, title1_clean_df):
    schools_with_need_df = schools_with_region_df.merge(
        title1_clean_df[["school_name_clean", "high_need"]],
        on="school_name_clean",
        how="left"
    )

    schools_with_need_df["high_need"] = schools_with_need_df["high_need"].fillna(False)

    mo.vstack([
        mo.md("## Step 20: High-need flag added to schools"),
        mo.ui.table(
            schools_with_need_df[
                ["SCH_NAME", "county_name", "region", "high_need"]
            ].head(20)
        )
    ])
    return (schools_with_need_df,)


@app.cell
def _(mo, pd):
    cold_call_raw_df = pd.read_excel(
        "JA Cold Call Tracker.xlsx",
        sheet_name="Call Log",
        header=1
    )

    cold_call_raw_df = cold_call_raw_df.dropna(how="all").copy()

    mo.vstack([
        mo.md("## Step 21: Cold call tracker loaded"),
        mo.md(f"**Rows after blank-row cleanup:** {cold_call_raw_df.shape[0]:,}"),
        mo.ui.table(cold_call_raw_df.head(10))
    ])
    return (cold_call_raw_df,)


@app.cell
def _():
    return


@app.cell
def _(cold_call_raw_df, mo):
    tracker_df = cold_call_raw_df.copy()

    tracker_df["school_name_clean"] = (
        tracker_df["Organization"].astype(str).str.lower().str.strip()
    )

    tracker_df["tracker_county_clean"] = (
        tracker_df["County"]
        .astype(str)
        .str.replace(" County", "", regex=False)
        .str.strip()
        .str.title()
    )

    tracker_df["outcome_clean"] = tracker_df["Outcome"].astype(str).str.lower().str.strip()
    tracker_df["stage_clean"] = tracker_df["Stage"].astype(str).str.lower().str.strip()

    tracker_df = tracker_df[tracker_df["school_name_clean"].notna()].copy()
    tracker_df = tracker_df[tracker_df["school_name_clean"] != "nan"].copy()

    mo.vstack([
        mo.md("## Step 22: Cold call tracker cleaned"),
        mo.ui.table(
            tracker_df[
                ["Organization", "County", "Outcome", "Stage", "school_name_clean"]
            ].head(20)
        )
    ])
    return (tracker_df,)


@app.cell
def _(mo, tracker_df):
    positive_outcomes = {"interested"}
    positive_stages = {"assessing fit", "contacted", "partnership discussion"}

    tracker_flagged_df = tracker_df.copy()

    tracker_flagged_df["positive_response"] = (
        tracker_flagged_df["outcome_clean"].isin(positive_outcomes) |
        tracker_flagged_df["stage_clean"].isin(positive_stages)
    )

    mo.vstack([
        mo.md("## Step 23: Positive response flag created"),
        mo.md(f"**Positive rows:** {int(tracker_flagged_df['positive_response'].sum())}"),
        mo.ui.table(
            tracker_flagged_df[
                ["Organization", "Outcome", "Stage", "positive_response"]
            ].head(20)
        )
    ])
    return (tracker_flagged_df,)


@app.cell
def _():
    return


@app.cell
def _(mo, pd, tracker_flagged_df):
    tracker_school_summary = (
        tracker_flagged_df
        .groupby("school_name_clean", as_index=False)
        .agg(
            positive_response=("positive_response", "max"),
            outcome_summary=("Outcome", lambda x: " | ".join(sorted(set([str(v) for v in x if pd.notna(v)])))),
            stage_summary=("Stage", lambda x: " | ".join(sorted(set([str(v) for v in x if pd.notna(v)])))),
            tracker_county=("tracker_county_clean", "first"),
            organization_name=("Organization", "first")
        )
    )

    mo.vstack([
        mo.md("## Step 24: Tracker summarized to school level"),
        mo.ui.table(tracker_school_summary.head(20))
    ])
    return (tracker_school_summary,)


@app.cell
def _():
    return


@app.cell
def _(mo, schools_with_need_df, tracker_school_summary):
    schools_tracker_merged_df = schools_with_need_df.merge(
        tracker_school_summary,
        on="school_name_clean",
        how="left"
    )

    schools_tracker_merged_df["positive_response"] = (
        schools_tracker_merged_df["positive_response"].fillna(False)
    )

    mo.vstack([
        mo.md("## Step 25: Tracker merged with school dataset"),
        mo.md(f"**Matched schools from tracker:** {schools_tracker_merged_df['organization_name'].notna().sum():,}"),
        mo.md(f"**Positive-response schools:** {int(schools_tracker_merged_df['positive_response'].sum()):,}"),
        mo.ui.table(
            schools_tracker_merged_df[
                ["SCH_NAME", "county_name", "region", "positive_response", "outcome_summary", "stage_summary"]
            ].head(20)
        )
    ])
    return (schools_tracker_merged_df,)


@app.cell
def _():
    return


@app.cell
def _(mo, schools_tracker_merged_df):
    schools_map_points_df = schools_tracker_merged_df[
        schools_tracker_merged_df["school_lat"].notna() &
        schools_tracker_merged_df["school_lon"].notna()
    ].copy()

    mo.vstack([
        mo.md("## Step 26: Schools available for map points"),
        mo.md(f"**Schools with usable coordinates:** {schools_map_points_df.shape[0]:,}"),
        mo.ui.table(
            schools_map_points_df[
                ["SCH_NAME", "LEA_NAME", "school_lat", "school_lon", "positive_response"]
            ].head(15)
        )
    ])
    return (schools_map_points_df,)


@app.cell
def _(px, schools_map_points_df):
    school_dot_df = schools_map_points_df.copy()
    school_dot_df["response_group"] = school_dot_df["positive_response"].map({
        True: "Positive Response",
        False: "No Positive Response"
    })

    fig_school_dot_map = px.scatter_geo(
        school_dot_df,
        lat="school_lat",
        lon="school_lon",
        color="response_group",
        hover_name="SCH_NAME",
        hover_data={
            "LEA_NAME": True,
            "county_name": True,
            "region": True,
            "high_need": True,
            "school_lat": False,
            "school_lon": False
        },
        color_discrete_map={
            "Positive Response": "green",
            "No Positive Response": "lightgray"
        },
        title="Ohio Schools with Positive Outreach Responses"
    )

    fig_school_dot_map.update_traces(
        marker=dict(size=6, opacity=0.8)
    )

    fig_school_dot_map.update_geos(
        scope="usa",
        fitbounds="locations",
        visible=False,
        showsubunits=True,
        subunitcolor="black"
    )

    fig_school_dot_map.update_layout(
        height=820,
        margin={"r": 10, "t": 60, "l": 10, "b": 10},
        title_x=0.5,
        legend_title_text="Outreach Status"
    )

    fig_school_dot_map
    return


@app.cell
def _():
    return


@app.cell
def _(go, json, ohio_region_map, region_color_map, schools_map_points_df):
    region_geojson = json.loads(ohio_region_map.to_json())

    region_plot_df = ohio_region_map[
        ["GEOID", "NAME", "county_name", "region_label", "anchor_county", "TOT_POP"]
    ].copy()

    fig_school_region_overlay = go.Figure()

    # County fills
    for region_name, color in region_color_map.items():
        region_subset = region_plot_df[region_plot_df["region_label"] == region_name]

        if len(region_subset) == 0:
            continue

        fig_school_region_overlay.add_trace(
            go.Choroplethgeo(
                geojson=region_geojson,
                locations=region_subset["GEOID"],
                z=[1] * len(region_subset),
                featureidkey="properties.GEOID",
                showscale=False,
                showlegend=True,
                name=region_name,
                marker_line_color="white",
                marker_line_width=0.8,
                colorscale=[[0, color], [1, color]],
                hovertemplate="<b>%{location}</b><extra>" + region_name + "</extra>"
            )
        )

    positive_points = schools_map_points_df[schools_map_points_df["positive_response"]].copy()
    other_points = schools_map_points_df[~schools_map_points_df["positive_response"]].copy()

    fig_school_region_overlay.add_trace(
        go.Scattergeo(
            lon=other_points["school_lon"],
            lat=other_points["school_lat"],
            text=other_points["SCH_NAME"],
            customdata=other_points[["LEA_NAME", "county_name", "region"]],
            mode="markers",
            marker=dict(
                size=5,
                color="lightgray",
                opacity=0.65
            ),
            name="No Positive Response",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "District: %{customdata[0]}<br>"
                "County: %{customdata[1]}<br>"
                "Region: %{customdata[2]}<extra></extra>"
            )
        )
    )

    fig_school_region_overlay.add_trace(
        go.Scattergeo(
            lon=positive_points["school_lon"],
            lat=positive_points["school_lat"],
            text=positive_points["SCH_NAME"],
            customdata=positive_points[["LEA_NAME", "county_name", "region", "outcome_summary"]],
            mode="markers",
            marker=dict(
                size=8,
                color="green",
                opacity=0.95,
                line=dict(width=0.8, color="black")
            ),
            name="Positive Response",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "District: %{customdata[0]}<br>"
                "County: %{customdata[1]}<br>"
                "Region: %{customdata[2]}<br>"
                "Tracker Outcome: %{customdata[3]}<extra></extra>"
            )
        )
    )

    fig_school_region_overlay.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig_school_region_overlay.update_layout(
        title="JACO Regions with School Outreach Results",
        title_x=0.5,
        height=860,
        margin={"r": 10, "t": 60, "l": 10, "b": 10},
        legend_title_text="Map Layers / Outreach Status"
    )

    fig_school_region_overlay
    return


@app.cell
def _(mo, schools_map_points_df):

    outreach_region_summary = (
        schools_map_points_df[schools_map_points_df["region"].notna()]
        .groupby("region", as_index=False)
        .agg(
            mapped_schools=("SCH_NAME", "count"),
            positive_response_schools=("positive_response", "sum")
        )
    )

    outreach_region_summary["positive_rate"] = (
        outreach_region_summary["positive_response_schools"] /
        outreach_region_summary["mapped_schools"]
    ).round(3)

    mo.vstack([
        mo.md("## Step 29: Outreach summary by region"),
        mo.ui.table(outreach_region_summary)
    ])
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
