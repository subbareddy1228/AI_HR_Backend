from typing import List
from collections import Counter

def identify_productivity_bottlenecks(activities: List[dict]):
    """
    activities: list of dict {app_name, website_url, productive}
    Returns most common unproductive apps/websites
    """
    unproductive = [a.get("app_name") or a.get("website_url") for a in activities if a.get("productive")=="No"]
    counter = Counter(unproductive)
    return counter.most_common(5)  # Top 5 bottlenecks

def workload_distribution(activities: List[dict]):
    """
    Returns percentage of time spent on productive vs unproductive
    """
    total = len(activities)
    if total == 0:
        return {"productive": 0, "unproductive": 0}
    productive_count = sum(1 for a in activities if a.get("productive")=="Yes")
    unproductive_count = total - productive_count
    return {
        "productive": round(productive_count/total*100,2),
        "unproductive": round(unproductive_count/total*100,2)
    }
