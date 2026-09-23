from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# Path
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VOCABULARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "knowledge"
    / "ingredient_vocabulary.csv"
)


# ---------------------------------------------------------
# Load vocabulary
# ---------------------------------------------------------

def load_vocabulary(
    path: str | Path = VOCABULARY_PATH
) -> pd.DataFrame:

    path = Path(path)

    if not path.exists():

        raise FileNotFoundError(
            f"\nIngredient vocabulary not found:\n"
            f"{path}\n\n"
            "Run:\n"
            "python -m normalization.build_ingredient_vocabulary"
        )

    df = pd.read_csv(
        path
    )

    return df


# ---------------------------------------------------------
# Get terms
# ---------------------------------------------------------

def get_vocabulary_terms(
    path: str | Path = VOCABULARY_PATH
) -> list[str]:

    df = load_vocabulary(
        path
    )

    return (
        df["raw_term"]
        .dropna()
        .astype(str)
        .tolist()
    )


# ---------------------------------------------------------
# Main test
# ---------------------------------------------------------

if __name__ == "__main__":

    df = load_vocabulary()

    print(
        f"Vocabulary entries: {len(df)}"
    )

    print("\nFirst 30 terms:")

    for term in df[
        "raw_term"
    ].head(30):

        print(
            f"  - {term}"
        )