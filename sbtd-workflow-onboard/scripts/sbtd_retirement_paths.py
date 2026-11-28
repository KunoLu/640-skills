"""Paths that remain private after retirement; none is an executable entry point."""

HISTORICAL_GRAPH = "graft"
HISTORICAL_GRAPH_STATE = ".graft"
HISTORY_DIRS = (HISTORICAL_GRAPH, HISTORICAL_GRAPH_STATE)
HISTORY_IGNORE_PROBES = (HISTORICAL_GRAPH, f"{HISTORICAL_GRAPH}/index.json",
                         HISTORICAL_GRAPH_STATE, f"{HISTORICAL_GRAPH_STATE}/state.json")
LEGACY_LAUNCHER_RELATIVE = "scripts/sbtd_graft_entry.py"
