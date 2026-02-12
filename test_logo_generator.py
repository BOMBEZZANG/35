"""Test Logo Generator."""

from pathlib import Path
from src.exam_pipeline.app_builder import LogoGenerator

def test_logo_generator():
    """Test logo generation with multiple patterns."""
    print("=" * 70)
    print("Testing Logo Generator")
    print("=" * 70)
    print()

    output_dir = Path("test_logos")
    output_dir.mkdir(exist_ok=True)

    print(f"Generating logos in: {output_dir}")
    print()

    # Generate 5 random logos
    generator = LogoGenerator(size=1024)
    print(f"Logo Generator initialized:")
    print(f"  - {len(generator.patterns)} patterns available")
    print(f"  - {len(generator.background_colors)} background colors")
    print(f"  - {len(generator.color_palettes)} color palettes")
    print()

    print("Generating 5 random logos...")
    for i in range(5):
        logo_path = output_dir / f"logo_{i+1}.png"
        logo = generator.generate(output_path=logo_path)
        print(f"  ✓ Generated: {logo_path} ({logo.size[0]}x{logo.size[1]})")

    print()
    print("=" * 70)
    print("✅ Logo Generation Test Complete!")
    print("=" * 70)
    print()
    print(f"Check the generated logos in: {output_dir.absolute()}")


if __name__ == "__main__":
    test_logo_generator()
