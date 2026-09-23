from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "knowledge"
    / "food_ingredient_database.csv"
)


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------

def load_ingredient_dataset(
    dataset_path: str | Path = DATASET_PATH
) -> pd.DataFrame:

    dataset_path = Path(dataset_path)

    if not dataset_path.exists():

        raise FileNotFoundError(
            f"Dataset not found:\n{dataset_path}\n\n"
            "Place the downloaded Kaggle CSV inside:\n"
            "data/knowledge/"
        )

    print(f"Loading dataset: {dataset_path}")

    df = pd.read_csv(
        dataset_path,
        low_memory=False
    )

    print(f"Dataset loaded successfully.")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return df


# ---------------------------------------------------------
# Inspect dataset
# ---------------------------------------------------------

def inspect_dataset(
    df: pd.DataFrame
) -> None:

    print("\n" + "=" * 70)
    print("DATASET INFORMATION")
    print("=" * 70)

    print("\nColumns:")

    for column in df.columns:
        print(f"  - {column}")

    print("\nFirst 5 rows:")

    print(
        df.head().to_string()
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    df = load_ingredient_dataset()

    inspect_dataset(df)