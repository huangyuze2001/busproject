"""
Shared real-timetable data for the route-77 Partick case study and RV monitor.

Single source of truth: all three scripts (real_data_case.py, plot_real_data.py,
rv_monitor.py) import DEP from here, so the data only ever needs editing in one
place.

Real bus departure times for First Glasgow route 77 (Glasgow Buchanan -
Glasgow Airport, operator First Greater Glasgow) at "Partick Bus Station
(stance 1)", towards Glasgow Airport, for Tuesday 23 June 2026.
Source: bustimes.org (timetable data from the Traveline National Dataset,
TNDS), retrieved 2026-06-23. Departure times manually verified against the
operator timetable.
"""

# Full 24h of real departures (00:17 wraps from the 23:19 of the previous day).
DEP = ["00:17","01:17","02:17","03:17","04:17","05:18","05:48","06:19","06:34",
       "06:49","07:04","07:22","07:37","07:52","08:07","08:26","08:41","08:56",
       "09:11","09:22","09:36","09:51","10:06","10:19","10:33","10:46","10:59",
       "11:16","11:33","11:47","12:02","12:17","12:32","12:47","13:02","13:17",
       "13:33","13:48","14:03","14:14","14:27","14:39","14:52","15:04","15:19",
       "15:35","15:50","16:05","16:20","16:33","16:47","17:00","17:11","17:27",
       "17:42","17:56","18:11","18:26","18:36","18:49","19:06","19:23","19:54",
       "20:14","20:43","21:12","21:52","22:22","23:19"]


def to_min(s):
    """'HH:MM' -> minutes since midnight."""
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def dep_minutes():
    """Sorted list of departure times in minutes since midnight."""
    return sorted(to_min(x) for x in DEP)
