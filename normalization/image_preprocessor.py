from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def preprocess_image(
    image_path: str | Path,
    output_dir: str | Path = "scratch/ocr_preprocessed",
) -> list[Path]:

    image_path = Path(image_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = Image.open(image_path).convert("RGB")

    # ==========================================
    # RESIZE
    # ==========================================

    max_side = 3600

    width, height = image.size
    largest_side = max(width, height)

    if largest_side > max_side:

        scale = max_side / largest_side

        image = image.resize(
            (
                int(width * scale),
                int(height * scale),
            ),
            Image.Resampling.LANCZOS,
        )

    # ==========================================
    # FULL IMAGE VERSIONS
    # ==========================================

    resized_path = output_dir / "01_resized.png"
    image.save(resized_path)

    gray = ImageOps.grayscale(image)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    gray = ImageEnhance.Sharpness(gray).enhance(1.5)

    gray_path = output_dir / "02_gray_contrast.png"
    gray.save(gray_path)

    sharp = ImageEnhance.Contrast(image).enhance(1.4)
    sharp = ImageEnhance.Sharpness(sharp).enhance(2.0)
    sharp = sharp.filter(ImageFilter.SHARPEN)

    sharp_path = output_dir / "03_sharp.png"
    sharp.save(sharp_path)

    threshold = ImageOps.grayscale(image)
    threshold = ImageOps.autocontrast(threshold)

    threshold = threshold.point(
        lambda pixel: 255 if pixel > 160 else 0
    )

    threshold_path = output_dir / "04_threshold.png"
    threshold.save(threshold_path)

    # ==========================================
    # HORIZONTAL TILES
    # ==========================================

    tile_paths = []

    width, height = image.size

    tile_height = int(height * 0.40)
    overlap = int(height * 0.10)

    start_y = 0
    tile_number = 1

    while start_y < height:

        end_y = min(
            start_y + tile_height,
            height,
        )

        tile = image.crop(
            (
                0,
                start_y,
                width,
                end_y,
            )
        )

        tile_path = (
            output_dir
            / f"tile_{tile_number:02d}.png"
        )

        tile.save(tile_path)

        tile_paths.append(tile_path)

        if end_y >= height:
            break

        start_y = end_y - overlap
        tile_number += 1

    return [
        resized_path,
        gray_path,
        sharp_path,
        threshold_path,
        *tile_paths,
    ]