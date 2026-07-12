from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "src" / "myhome" / "demo_assets"

EXPECTED_FILES = [
    "placeholder-photo-1.png",
    "placeholder-photo-2.png",
    "placeholder-manual.pdf",
    "placeholder-receipt.pdf",
    "placeholder-warranty.pdf",
]


def test_all_expected_assets_exist_and_are_nonempty():
    for name in EXPECTED_FILES:
        path = ASSETS_DIR / name
        assert path.exists(), f"missing {name}"
        assert path.stat().st_size > 0


def test_png_assets_have_valid_signature():
    for name in ["placeholder-photo-1.png", "placeholder-photo-2.png"]:
        data = (ASSETS_DIR / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_pdf_assets_have_valid_signature():
    for name in ["placeholder-manual.pdf", "placeholder-receipt.pdf", "placeholder-warranty.pdf"]:
        data = (ASSETS_DIR / name).read_bytes()
        assert data[:5] == b"%PDF-"
        assert data.rstrip().endswith(b"%%EOF")
