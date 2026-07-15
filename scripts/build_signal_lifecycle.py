import csv
from pathlib import Path


ACTIVE_GROUPS = {"主攻", "试探", "趋势保持"}
EPISODE_FIELDS = (
    "table_type",
    "name",
    "start_date",
    "start_group",
    "main_date",
    "end_date",
    "end_group",
    "signal_observations",
    "false_breakout",
    "status",
)


def build_signal_episodes(signals):
    episodes = []
    active = {}
    for signal in sorted(
        signals,
        key=lambda row: (row["table_type"], row["name"], row["data_date"]),
    ):
        key = (signal["table_type"], signal["name"])
        group = signal["group"]
        episode = active.get(key)
        if group in ACTIVE_GROUPS:
            if episode is None:
                episode = {
                    "table_type": signal["table_type"],
                    "name": signal["name"],
                    "start_date": signal["data_date"],
                    "start_group": group,
                    "main_date": "",
                    "end_date": "",
                    "end_group": "",
                    "signal_observations": 0,
                    "false_breakout": False,
                    "status": "open",
                }
                active[key] = episode
            episode["signal_observations"] += 1
            if group == "主攻" and not episode["main_date"]:
                episode["main_date"] = signal["data_date"]
        elif episode is not None:
            episode["end_date"] = signal["data_date"]
            episode["end_group"] = group
            episode["false_breakout"] = (
                group == "回避" and episode["signal_observations"] <= 2
            )
            episode["status"] = "closed"
            episodes.append(episode)
            del active[key]
    episodes.extend(active.values())
    return sorted(episodes, key=lambda row: (row["start_date"], row["table_type"], row["name"]))


def update_signal_episodes(signals_path, output_path):
    signals_path = Path(signals_path)
    output_path = Path(output_path)
    with signals_path.open(encoding="utf-8", newline="") as handle:
        signals = list(csv.DictReader(handle))
    episodes = build_signal_episodes(signals)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EPISODE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(episodes)
    temporary.replace(output_path)
    return episodes


def main():
    root = Path(__file__).resolve().parents[1]
    episodes = update_signal_episodes(
        root / "data/direction-signals.csv",
        root / "data/signal-episodes.csv",
    )
    print(f"saved {len(episodes)} signal episodes")


if __name__ == "__main__":
    main()
