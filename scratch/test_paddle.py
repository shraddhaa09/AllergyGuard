import os
os.environ["FLAGS_enable_pir_api"] = "0"
from pathlib import Path
from paddleocr import PaddleOCR

ocr = PaddleOCR(lang="en", enable_mkldnn=False)

res = ocr.ocr("data/raw/food_ingredients.webp")

out_lines = []
out_lines.append(f"Type of res: {type(res)}")
out_lines.append(f"Len of res: {len(res) if res else 0}")

if res and res[0]:
    out_lines.append(f"Type of res[0]: {type(res[0])}")
    out_lines.append(f"Len of res[0]: {len(res[0])}")
    for idx, item in enumerate(res[0]):
        out_lines.append(f"--- Item {idx} ---")
        out_lines.append(f"Type: {type(item)}")
        out_lines.append(f"Content: {repr(item)}")

out_path = Path("scratch/ocr_out.txt")
out_path.write_text("\n".join(out_lines), encoding="utf-8")
print(f"Wrote inspection to {out_path}")
