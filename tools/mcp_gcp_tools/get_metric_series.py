"""
Fetch metric time series. Uses Cloud Monitoring API when GCP is configured; otherwise synthetic.

Production: set GCP_PROJECT_ID (and optionally GOOGLE_APPLICATION_CREDENTIALS or ADC).
Install: pip install google-cloud-monitoring
"""

import json
import os
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"


def _fetch_from_cloud_monitoring(
    project_id: str,
    metric_name: str | None,
    resource: str | None,
) -> str:
    """Call Cloud Monitoring API via google.cloud.monitoring_v3."""
    try:
        from google.cloud import monitoring_v3
    except ImportError:
        return json.dumps({"error": "google-cloud-monitoring not installed. pip install google-cloud-monitoring"})

    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    # Metric type: use standard GCP metric or allow custom. Default to CPU utilization.
    metric_type = f"compute.googleapis.com/instance/cpu/utilization"
    if metric_name and metric_name.startswith("custom.googleapis.com/"):
        metric_type = metric_name
    elif metric_name:
        # Common shortcuts
        metric_map = {
            "cpu_utilization": "compute.googleapis.com/instance/cpu/utilization",
            "cpu": "compute.googleapis.com/instance/cpu/utilization",
            "memory": "compute.googleapis.com/instance/memory/utilization",
            "disk": "compute.googleapis.com/instance/disk/utilization",
        }
        metric_type = metric_map.get(metric_name.lower(), f"compute.googleapis.com/instance/cpu/utilization")

    filter_str = f'metric.type="{metric_type}"'
    if resource:
        filter_str += f' AND resource.labels.instance_id="{resource}"'

    # Last 5 minutes
    from datetime import datetime, timezone, timedelta
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=5)
    interval = monitoring_v3.TimeInterval(
        {"end_time": {"seconds": int(end.timestamp())}, "start_time": {"seconds": int(start.timestamp())}}
    )

    request = monitoring_v3.ListTimeSeriesRequest(
        name=project_name,
        filter=filter_str,
        interval=interval,
        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
    )
    try:
        results = client.list_time_series(request=request)
        time_series = []
        for ts in results:
            points = []
            for p in (ts.points or [])[:20]:
                val = getattr(p.value, "double_value", None)
                if val is None:
                    val = getattr(p.value, "int64_value", None)
                points.append({"timestamp": p.interval.end_time.seconds if p.interval else None, "value": val})
            time_series.append({
                "metric": dict(ts.metric) if ts.metric else {},
                "resource": dict(ts.resource.labels) if ts.resource and ts.resource.labels else {},
                "points": points,
            })
        return json.dumps({"time_series": time_series, "query_interval": "last 5 minutes"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "time_series": []})


def get_metric_series(
    metric_name: str | None = None,
    resource: str | None = None,
) -> str:
    """
    Fetch metric time series for monitoring analysis.

    When GCP_PROJECT_ID is set and google-cloud-monitoring is installed, calls
    Cloud Monitoring API (timeSeries.list). Otherwise uses synthetic data.

    Args:
        metric_name: Optional filter by metric (e.g. "cpu_utilization", "memory", or full type).
        resource: Optional filter by resource / instance (e.g. instance_id).

    Returns:
        JSON string of time series data.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if project_id:
        return _fetch_from_cloud_monitoring(project_id, metric_name, resource)

    path = _DATA_DIR / "metrics.json"
    if not path.exists():
        return json.dumps({"error": "Metrics data not found. Set GCP_PROJECT_ID for Cloud Monitoring."})

    with open(path, "r") as f:
        data = json.load(f)

    series = data.get("time_series", [])
    if metric_name:
        series = [s for s in series if s.get("metric") == metric_name]
    if resource:
        series = [s for s in series if s.get("resource") == resource]

    result = {
        "time_series": series,
        "query_interval": data.get("query_interval"),
    }
    return json.dumps(result, indent=2)
