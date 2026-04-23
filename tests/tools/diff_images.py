import os
import sys

from PIL import Image, ImageChops

# Let environment variable override, but fallback to default
BASE_DIR = os.environ.get("VISUAL_ROOT", "tests/_visual-output")


def highlight_diff(diff):
    """
    Convert a difference image to a red-on-black highlight visualization.
    Non-black pixels in the diff are painted bright red, black pixels remain black.

    Args:
        diff: PIL Image from ImageChops.difference()

    Returns:
        PIL Image with red highlights on black background
    """
    # Convert diff to grayscale mask (non-black pixels become white mask)
    mask = diff.convert('L').point(lambda p: 255 if p > 0 else 0)

    # Create red image and black background
    red = Image.new('RGB', diff.size, (255, 0, 0))
    black = Image.new('RGB', diff.size, (0, 0, 0))

    # Composite: where mask is white, show red; else black
    return Image.composite(red, black, mask)

def main():
    # 1. Find the latest run directory
    try:
        # Get all subdirectories (ignore loose files or global 'diff' folders)
        subdirs =[
            os.path.join(BASE_DIR, d) for d in os.listdir(BASE_DIR)
            if os.path.isdir(os.path.join(BASE_DIR, d)) and d != "diff"
        ]
        if not subdirs:
            raise FileNotFoundError
    except FileNotFoundError:
        print(f"Error: No run directories found in {BASE_DIR}")
        sys.exit(1)

    # Sort by modification time to get the most recent run
    latest_run_dir = max(subdirs, key=os.path.getmtime)
    print(f"> Evaluating latest run: {latest_run_dir}")

    before_dir = os.path.join(latest_run_dir, "before")
    after_dir = os.path.join(latest_run_dir, "after")

    # Store diffs INSIDE the run directory to keep history organized
    out_dir = os.path.join(latest_run_dir, "diff")
    highlights_dir = os.path.join(latest_run_dir, "highlights")

    if not os.path.exists(before_dir) or not os.path.exists(after_dir):
        print(f"Error: 'before' or 'after' directory missing in {latest_run_dir}")
        print("Did Playwright successfully take the screenshots?")
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(highlights_dir, exist_ok=True)

    diff_count = 0
    files_checked = 0

    for file in os.listdir(before_dir):
        if not file.endswith(('.png', '.jpg', '.jpeg')):
            continue

        files_checked += 1
        before_path = os.path.join(before_dir, file)
        after_path = os.path.join(after_dir, file)

        if not os.path.exists(after_path):
            print(f"⚠️  Missing: {file} not found in 'after' directory. Skipping.")
            continue

        img1 = Image.open(before_path)
        img2 = Image.open(after_path)

        # ImageChops crashes if images aren't the exact same dimensions
        if img1.size != img2.size:
            print(f"❌ Size mismatch for {file}: BEFORE {img1.size} vs AFTER {img2.size}")
            diff_count += 1
            continue

        # Calculate the visual difference
        diff = ImageChops.difference(img1, img2)
        # getbbox() returns None if images are completely identical
        if diff.getbbox():
            diff.save(os.path.join(out_dir, file))

            diff_red = highlight_diff(diff)
            diff_red.save(os.path.join(highlights_dir, file))

            print(f"❌ Difference found: {file}")
            diff_count += 1
        else:
            print(f"✅ Match: {file}")

    if files_checked == 0:
        print("Error: No images found in the 'before' directory.")
        sys.exit(1)

    if diff_count > 0:
        print(f"\n❌ {diff_count} visual difference(s) found.")
        print(f"   View diff images in: {out_dir}")
        sys.exit(1)  # Tell Make to FAIL
    else:
        print(f"\n✅ All {files_checked} images matched perfectly!")
        sys.exit(0)  # Tell Make to SUCCEED

if __name__ == "__main__":
    main()