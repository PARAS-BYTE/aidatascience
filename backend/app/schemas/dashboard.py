from typing import Optional, Literal, List, Dict, Any, Union
from pydantic import BaseModel, Field


class ChartSpec(BaseModel):
    id: str
    type: Literal["bar", "line", "horizontal_bar", "scatter", "pie", "donut", "area", "bar_stacked", "stacked_bar"]
    metric: str = "value"
    aggregation: Literal["SUM", "AVG", "COUNT", "MIN", "MAX", "sum", "avg", "mean", "count", "min", "max"] = "SUM"
    dimension: str = "category"
    sort: Optional[Literal["asc", "desc"]] = "desc"
    limit: Optional[int] = None
    drillable: bool = False
    drill_path: Optional[List[str]] = None
    listens_to_filters: List[str] = Field(default_factory=list)
    emits_filter_on_click: Optional[str] = None
    title: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    color: Optional[str] = None
    colors: Optional[List[str]] = None


class FilterSpec(BaseModel):
    column: str
    control: Literal["date_range", "multiselect_dropdown", "range_slider", "categorical_select"] = "multiselect_dropdown"
    title: Optional[str] = None
    options: Optional[List[str]] = Field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None


class KPICardSpec(BaseModel):
    id: str
    metric_key: str
    title: str
    value: float
    formatted_value: str
    aggregation: Optional[str] = "sum"
    delta_percentage: float = 0.0
    trend_direction: Literal["up", "down", "neutral"] = "neutral"
    is_positive: bool = True
    sparkline: List[float] = Field(default_factory=list)
    subtitle: Optional[str] = None


class DashboardSpec(BaseModel):
    id: str
    layout: str = "executive_bi"
    title: Optional[str] = "Executive Intelligence Dashboard"
    subtitle: Optional[str] = None
    generated_at: Optional[str] = None
    charts: List[ChartSpec] = Field(default_factory=list)
    filters: List[FilterSpec] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)
    kpi_cards: List[KPICardSpec] = Field(default_factory=list)
    primary_chart: Optional[ChartSpec] = None
    secondary_charts: List[ChartSpec] = Field(default_factory=list)
    drill_downs: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    cross_filtering_enabled: bool = True
    insights_panel: bool = True
    insights: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    anomalies_summary: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    last_modified_prompt: Optional[str] = None
    applied_patches: Optional[List[str]] = None


class DashboardPatch(BaseModel):
    op: Literal["update_chart", "add_filter", "remove_chart", "add_chart"]
    chart_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    filter: Optional[FilterSpec] = None
    chart: Optional[ChartSpec] = None


class ChartQueryRequest(BaseModel):
    chart_id: str
    dimension: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
