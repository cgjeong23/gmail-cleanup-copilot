from pathlib import Path
import pandas as pd


def save_sender_summary(summary: list[dict], path: Path):

    df = pd.DataFrame(summary)

    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(path, index=False)