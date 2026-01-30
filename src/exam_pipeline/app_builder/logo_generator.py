"""
Logo Generator - Generate unique geometric app icons.

Creates random geometric patterns with 25+ different designs
and pastel color backgrounds for App Store/Google Play icons.
"""

import logging
import math
import random
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class LogoGenerator:
    """
    Generate unique geometric app logos with random patterns.

    Features:
    - 25+ geometric pattern algorithms
    - 14 pastel background colors
    - 15 color palettes
    - Random pattern selection for uniqueness
    """

    def __init__(self, size: int = 1024, background_color: Optional[Tuple[int, int, int]] = None):
        """
        Initialize logo generator.

        Args:
            size: Square image size (default: 1024x1024)
            background_color: RGB tuple or None for random selection
        """
        self.size = size
        self.center = size // 2

        # Pastel background colors
        self.background_colors = [
            (255, 255, 255),  # Pure white
            (255, 228, 225),  # Misty Rose
            (255, 239, 213),  # Papaya Whip
            (230, 230, 250),  # Lavender
            (240, 255, 255),  # Azure
            (255, 250, 205),  # Lemon Chiffon
            (225, 255, 225),  # Honeydew variant
            (255, 228, 196),  # Bisque
            (224, 255, 255),  # Light Cyan
            (255, 240, 245),  # Lavender Blush
            (240, 248, 255),  # Alice Blue
            (245, 255, 250),  # Mint Cream
            (255, 245, 238),  # Seashell
            (248, 248, 255),  # Ghost White
        ]

        # Set background color
        if background_color is None:
            self.background_color = random.choice(self.background_colors)
        else:
            self.background_color = background_color

        # Vivid color palettes (no red tones - removed for App Store guidelines)
        self.color_palettes = [
            # Blue tones
            [(0, 123, 255), (0, 86, 179), (41, 128, 185)],
            # Green tones
            [(46, 204, 113), (39, 174, 96), (34, 153, 84)],
            # Orange tones (pure orange, not red)
            [(255, 152, 0), (255, 138, 34), (230, 126, 34)],
            # Purple tones
            [(155, 89, 182), (142, 68, 173), (125, 60, 152)],
            # Cyan tones
            [(26, 188, 156), (22, 160, 133), (19, 141, 117)],
            # Yellow tones
            [(255, 193, 7), (255, 179, 0), (255, 160, 0)],
            # Indigo tones
            [(63, 81, 181), (57, 73, 171), (48, 63, 159)],
            # Grey tones
            [(96, 125, 139), (84, 110, 122), (69, 90, 100)],
            # Gradient blue
            [(100, 181, 246), (33, 150, 243), (13, 71, 161)],
            # Gradient green
            [(129, 199, 132), (76, 175, 80), (27, 94, 32)],
            # Gradient purple
            [(186, 104, 200), (171, 71, 188), (106, 27, 154)],
            # Warm palette (no red)
            [(255, 152, 0), (255, 193, 7), (255, 235, 59)],
            # Cool palette
            [(33, 150, 243), (0, 188, 212), (0, 150, 136)],
            # Natural palette
            [(76, 175, 80), (139, 195, 74), (205, 220, 57)],
            # Jewel palette
            [(156, 39, 176), (103, 58, 183), (63, 81, 181)]
        ]

        # All 25 pattern functions
        self.patterns = [
            self.pattern_offset_circles,
            self.pattern_asymmetric_squares,
            self.pattern_scattered_triangles,
            self.pattern_overlapping_offset,
            self.pattern_corner_emphasis,
            self.pattern_diagonal_flow,
            self.pattern_clustered_shapes,
            self.pattern_random_positioning,
            self.pattern_layered_offset,
            self.pattern_spiral_offset,
            self.pattern_grid_variations,
            self.pattern_floating_elements,
            self.pattern_cascade_design,
            self.pattern_orbital_arrangement,
            self.pattern_split_composition,
            self.pattern_intersection_design,
            self.pattern_wave_flow,
            self.pattern_cluster_burst,
            self.pattern_frame_and_center,
            self.pattern_dynamic_balance,
            self.pattern_centered_circle_modified,
            self.pattern_geometric_mix_modified,
            self.pattern_star_shape_modified,
            self.pattern_hexagon_offset,
            self.pattern_cross_asymmetric
        ]

        logger.info(f"LogoGenerator initialized: {len(self.patterns)} patterns, {len(self.background_colors)} backgrounds")

    def _get_random_offset(self, max_offset: int = 150) -> int:
        """Generate random offset for asymmetric positioning."""
        return random.randint(-max_offset, max_offset)

    def _get_random_color_palette(self):
        """Select random color palette."""
        return random.choice(self.color_palettes)

    # === Basic Shape Drawing Functions ===

    def _draw_circle(self, draw: ImageDraw.Draw, center: Tuple[int, int],
                     radius: int, color: Tuple[int, int, int], fill: bool = True):
        """Draw circle."""
        bbox = [
            center[0] - radius, center[1] - radius,
            center[0] + radius, center[1] + radius
        ]
        if fill:
            draw.ellipse(bbox, fill=color)
        else:
            draw.ellipse(bbox, outline=color, width=5)

    def _draw_square(self, draw: ImageDraw.Draw, center: Tuple[int, int],
                     size: int, color: Tuple[int, int, int], rotation: int = 0, fill: bool = True):
        """Draw square with optional rotation."""
        half_size = size // 2
        points = [
            (-half_size, -half_size),
            (half_size, -half_size),
            (half_size, half_size),
            (-half_size, half_size)
        ]

        if rotation != 0:
            angle = math.radians(rotation)
            rotated_points = []
            for x, y in points:
                new_x = x * math.cos(angle) - y * math.sin(angle)
                new_y = x * math.sin(angle) + y * math.cos(angle)
                rotated_points.append((center[0] + new_x, center[1] + new_y))
            points = rotated_points
        else:
            points = [(center[0] + x, center[1] + y) for x, y in points]

        if fill:
            draw.polygon(points, fill=color)
        else:
            draw.polygon(points, outline=color, width=5)

    def _draw_triangle(self, draw: ImageDraw.Draw, center: Tuple[int, int],
                       size: int, color: Tuple[int, int, int], rotation: int = 0, fill: bool = True):
        """Draw equilateral triangle with optional rotation."""
        height = int(size * math.sqrt(3) / 2)
        points = [
            (0, -height * 2/3),
            (-size/2, height * 1/3),
            (size/2, height * 1/3)
        ]

        if rotation != 0:
            angle = math.radians(rotation)
            rotated_points = []
            for x, y in points:
                new_x = x * math.cos(angle) - y * math.sin(angle)
                new_y = x * math.sin(angle) + y * math.cos(angle)
                rotated_points.append((center[0] + new_x, center[1] + new_y))
            points = rotated_points
        else:
            points = [(center[0] + x, center[1] + y) for x, y in points]

        if fill:
            draw.polygon(points, fill=color)
        else:
            draw.polygon(points, outline=color, width=5)

    def _draw_hexagon(self, draw: ImageDraw.Draw, center: Tuple[int, int],
                      size: int, color: Tuple[int, int, int], fill: bool = True):
        """Draw hexagon."""
        points = []
        for i in range(6):
            angle = math.radians(60 * i)
            x = center[0] + size * math.cos(angle)
            y = center[1] + size * math.sin(angle)
            points.append((x, y))

        if fill:
            draw.polygon(points, fill=color)
        else:
            draw.polygon(points, outline=color, width=5)

    def _draw_star(self, draw: ImageDraw.Draw, center: Tuple[int, int],
                   outer_radius: int, inner_radius: int, points_count: int,
                   color: Tuple[int, int, int], rotation: int = 0):
        """Draw star shape."""
        points = []
        for i in range(points_count * 2):
            angle = math.radians(360 / (points_count * 2) * i + rotation)
            radius = outer_radius if i % 2 == 0 else inner_radius
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            points.append((x, y))

        draw.polygon(points, fill=color)

    # === Pattern Functions (25 patterns) ===

    def pattern_offset_circles(self, draw, colors):
        """Pattern 1: Offset circles."""
        main_offset_x = self._get_random_offset(100)
        main_offset_y = self._get_random_offset(100)
        main_center = (self.center + main_offset_x, self.center + main_offset_y)
        self._draw_circle(draw, main_center, 320, colors[0])

        for i in range(2):
            offset_x = self._get_random_offset(200)
            offset_y = self._get_random_offset(200)
            center = (self.center + offset_x, self.center + offset_y)
            radius = random.randint(120, 180)
            self._draw_circle(draw, center, radius, colors[(i + 1) % len(colors)])

    def pattern_asymmetric_squares(self, draw, colors):
        """Pattern 2: Asymmetric squares."""
        offset_x = self._get_random_offset(150)
        offset_y = self._get_random_offset(150)
        main_center = (self.center + offset_x, self.center + offset_y)
        rotation = random.randint(0, 45)
        self._draw_square(draw, main_center, 350, colors[0], rotation)

        for i in range(3):
            offset_x = self._get_random_offset(250)
            offset_y = self._get_random_offset(250)
            center = (self.center + offset_x, self.center + offset_y)
            size = random.randint(80, 150)
            rotation = random.randint(0, 90)
            self._draw_square(draw, center, size, colors[(i + 1) % len(colors)], rotation)

    def pattern_scattered_triangles(self, draw, colors):
        """Pattern 3: Scattered triangles."""
        center_offset_x = self._get_random_offset(80)
        center_offset_y = self._get_random_offset(80)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self._draw_circle(draw, center, 200, colors[0])

        triangle_count = random.randint(4, 7)
        for i in range(triangle_count):
            offset_x = self._get_random_offset(300)
            offset_y = self._get_random_offset(300)
            pos = (self.center + offset_x, self.center + offset_y)
            size = random.randint(60, 120)
            rotation = random.randint(0, 360)
            self._draw_triangle(draw, pos, size, colors[(i + 1) % len(colors)], rotation)

    def pattern_overlapping_offset(self, draw, colors):
        """Pattern 4: Overlapping offset shapes."""
        center1 = (self.center + self._get_random_offset(100), self.center - random.randint(50, 150))
        self._draw_circle(draw, center1, 280, colors[0])

        center2 = (self.center + self._get_random_offset(100), self.center + random.randint(50, 150))
        self._draw_circle(draw, center2, 260, colors[1])

        square_center = (self.center + self._get_random_offset(50), self.center)
        self._draw_square(draw, square_center, 180, colors[2], rotation=45)

    def pattern_corner_emphasis(self, draw, colors):
        """Pattern 5: Corner emphasis."""
        self._draw_hexagon(draw, (self.center, self.center), 150, colors[0])

        corners = [
            (self.center - 200, self.center - 200),
            (self.center + 200, self.center - 200),
            (self.center + 200, self.center + 200),
            (self.center - 200, self.center + 200)
        ]

        for i, corner in enumerate(corners):
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-50, 50)
            pos = (corner[0] + offset_x, corner[1] + offset_y)

            if i % 2 == 0:
                self._draw_circle(draw, pos, 80, colors[(i + 1) % len(colors)])
            else:
                self._draw_square(draw, pos, 120, colors[(i + 1) % len(colors)], rotation=45)

    def pattern_diagonal_flow(self, draw, colors):
        """Pattern 6: Diagonal flow."""
        num_shapes = 5
        for i in range(num_shapes):
            progress = i / (num_shapes - 1)
            base_x = self.center - 300 + (600 * progress)
            base_y = self.center - 300 + (600 * progress)

            offset_x = random.randint(-80, 80)
            offset_y = random.randint(-80, 80)
            pos = (int(base_x + offset_x), int(base_y + offset_y))

            size = random.randint(60, 120)
            shape_type = i % 3

            if shape_type == 0:
                self._draw_circle(draw, pos, size//2, colors[i % len(colors)])
            elif shape_type == 1:
                self._draw_square(draw, pos, size, colors[i % len(colors)], rotation=random.randint(0, 45))
            else:
                self._draw_triangle(draw, pos, size, colors[i % len(colors)], rotation=random.randint(0, 180))

    def pattern_clustered_shapes(self, draw, colors):
        """Pattern 7: Clustered shapes."""
        cluster_centers = [
            (self.center - 150, self.center - 100),
            (self.center + 120, self.center - 80),
            (self.center - 80, self.center + 140),
            (self.center + 100, self.center + 120)
        ]

        for cluster_idx, cluster_center in enumerate(cluster_centers):
            cluster_size = random.randint(2, 4)
            for i in range(cluster_size):
                offset_x = random.randint(-60, 60)
                offset_y = random.randint(-60, 60)
                pos = (cluster_center[0] + offset_x, cluster_center[1] + offset_y)

                size = random.randint(40, 80)
                color = colors[(cluster_idx + i) % len(colors)]

                if i % 2 == 0:
                    self._draw_circle(draw, pos, size//2, color)
                else:
                    self._draw_square(draw, pos, size, color, rotation=random.randint(0, 90))

    def pattern_random_positioning(self, draw, colors):
        """Pattern 8: Random positioning."""
        bg_offset_x = self._get_random_offset(50)
        bg_offset_y = self._get_random_offset(50)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self._draw_circle(draw, bg_center, 350, colors[0])

        num_shapes = random.randint(6, 10)
        for i in range(num_shapes):
            offset_x = self._get_random_offset(250)
            offset_y = self._get_random_offset(250)
            pos = (self.center + offset_x, self.center + offset_y)

            distance = math.sqrt(offset_x**2 + offset_y**2)
            if distance > 280:
                continue

            size = random.randint(30, 100)
            color = colors[(i + 1) % len(colors)]
            shape_type = random.randint(0, 2)

            if shape_type == 0:
                self._draw_circle(draw, pos, size//2, color)
            elif shape_type == 1:
                self._draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
            else:
                self._draw_triangle(draw, pos, size, color, rotation=random.randint(0, 360))

    def pattern_layered_offset(self, draw, colors):
        """Pattern 9: Layered offset."""
        layers = [
            (400, colors[0]),
            (300, colors[1]),
            (200, colors[2]),
            (100, colors[0])
        ]

        for i, (size, color) in enumerate(layers):
            offset_x = self._get_random_offset(50 + i * 20)
            offset_y = self._get_random_offset(50 + i * 20)
            center = (self.center + offset_x, self.center + offset_y)

            if i % 2 == 0:
                self._draw_circle(draw, center, size//2, color)
            else:
                self._draw_square(draw, center, size, color, rotation=45)

    def pattern_spiral_offset(self, draw, colors):
        """Pattern 10: Spiral offset."""
        num_elements = 8
        for i in range(num_elements):
            angle = math.radians(i * 45)
            base_radius = 80 + i * 25

            base_x = self.center + base_radius * math.cos(angle)
            base_y = self.center + base_radius * math.sin(angle)

            offset_x = random.randint(-40, 40)
            offset_y = random.randint(-40, 40)
            pos = (int(base_x + offset_x), int(base_y + offset_y))

            size = random.randint(40, 80)
            color = colors[i % len(colors)]

            if i % 3 == 0:
                self._draw_circle(draw, pos, size//2, color)
            elif i % 3 == 1:
                self._draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
            else:
                self._draw_triangle(draw, pos, size, color, rotation=random.randint(0, 180))

        center_offset_x = self._get_random_offset(30)
        center_offset_y = self._get_random_offset(30)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self._draw_star(draw, center, 60, 25, 6, colors[0])

    def pattern_grid_variations(self, draw, colors):
        """Pattern 11: Grid variations."""
        for i in range(3):
            for j in range(3):
                if i == 1 and j == 1:
                    center_offset_x = self._get_random_offset(50)
                    center_offset_y = self._get_random_offset(50)
                    center = (self.center + center_offset_x, self.center + center_offset_y)
                    self._draw_star(draw, center, 80, 30, 6, colors[0])
                else:
                    base_x = self.center + (i - 1) * 200
                    base_y = self.center + (j - 1) * 200

                    offset_x = random.randint(-60, 60)
                    offset_y = random.randint(-60, 60)
                    pos = (base_x + offset_x, base_y + offset_y)

                    size = random.randint(50, 100)
                    color = colors[(i + j) % len(colors)]

                    shape_type = (i + j) % 3
                    if shape_type == 0:
                        self._draw_circle(draw, pos, size//2, color)
                    elif shape_type == 1:
                        self._draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
                    else:
                        self._draw_triangle(draw, pos, size, color, rotation=random.randint(0, 180))

    def pattern_floating_elements(self, draw, colors):
        """Pattern 12: Floating elements."""
        main_offset_x = self._get_random_offset(60)
        main_offset_y = self._get_random_offset(60)
        main_center = (self.center + main_offset_x, self.center + main_offset_y)
        self._draw_circle(draw, main_center, 200, colors[0])

        for i in range(8):
            angle = math.radians(i * 45)
            distance = random.randint(250, 350)

            base_x = self.center + distance * math.cos(angle)
            base_y = self.center + distance * math.sin(angle)

            offset_x = random.randint(-100, 100)
            offset_y = random.randint(-100, 100)
            pos = (int(base_x + offset_x), int(base_y + offset_y))

            size = random.randint(30, 70)
            color = colors[(i + 1) % len(colors)]

            if i % 4 == 0:
                self._draw_circle(draw, pos, size//2, color)
            elif i % 4 == 1:
                self._draw_square(draw, pos, size, color, rotation=random.randint(0, 90))
            elif i % 4 == 2:
                self._draw_triangle(draw, pos, size, color, rotation=random.randint(0, 360))
            else:
                self._draw_hexagon(draw, pos, size//2, color)

    def pattern_cascade_design(self, draw, colors):
        """Pattern 13: Cascade design."""
        sizes = [350, 250, 150, 80]
        cumulative_offset_x = 0
        cumulative_offset_y = 0

        for i, size in enumerate(sizes):
            offset_x = self._get_random_offset(80)
            offset_y = self._get_random_offset(80)

            cumulative_offset_x += offset_x // (i + 1)
            cumulative_offset_y += offset_y // (i + 1)

            center = (self.center + cumulative_offset_x, self.center + cumulative_offset_y)
            color = colors[i % len(colors)]

            if i % 3 == 0:
                self._draw_circle(draw, center, size//2, color)
            elif i % 3 == 1:
                self._draw_square(draw, center, size, color, rotation=45 * i)
            else:
                self._draw_triangle(draw, center, size, color, rotation=60 * i)

    def pattern_orbital_arrangement(self, draw, colors):
        """Pattern 14: Orbital arrangement."""
        sun_offset_x = self._get_random_offset(50)
        sun_offset_y = self._get_random_offset(50)
        sun_center = (self.center + sun_offset_x, self.center + sun_offset_y)
        self._draw_star(draw, sun_center, 120, 50, 8, colors[0])

        orbits = [150, 220, 290]
        for orbit_idx, orbit_radius in enumerate(orbits):
            num_planets = random.randint(2, 4)
            for planet_idx in range(num_planets):
                angle = math.radians(planet_idx * (360 / num_planets) + orbit_idx * 30)

                base_x = sun_center[0] + orbit_radius * math.cos(angle)
                base_y = sun_center[1] + orbit_radius * math.sin(angle)

                deviation_x = random.randint(-50, 50)
                deviation_y = random.randint(-50, 50)
                pos = (int(base_x + deviation_x), int(base_y + deviation_y))

                size = random.randint(30, 80)
                color = colors[(orbit_idx + planet_idx + 1) % len(colors)]

                if planet_idx % 2 == 0:
                    self._draw_circle(draw, pos, size//2, color)
                else:
                    self._draw_square(draw, pos, size, color, rotation=random.randint(0, 90))

    def pattern_split_composition(self, draw, colors):
        """Pattern 15: Split composition."""
        left_center_x = self.center - 150 + random.randint(-50, 50)
        left_center_y = self.center + random.randint(-100, 100)
        left_center = (left_center_x, left_center_y)

        self._draw_circle(draw, left_center, 180, colors[0])
        self._draw_square(draw, (left_center_x + random.randint(-30, 30),
                               left_center_y + random.randint(-30, 30)),
                        120, colors[1], rotation=45)

        right_center_x = self.center + 150 + random.randint(-50, 50)
        right_center_y = self.center + random.randint(-100, 100)
        right_center = (right_center_x, right_center_y)

        self._draw_triangle(draw, right_center, 200, colors[2], rotation=random.randint(0, 180))
        self._draw_hexagon(draw, (right_center_x + random.randint(-40, 40),
                                right_center_y + random.randint(-40, 40)),
                         60, colors[0])

    def pattern_intersection_design(self, draw, colors):
        """Pattern 16: Intersection design."""
        offset1_x = self._get_random_offset(100)
        offset1_y = self._get_random_offset(100)
        center1 = (self.center - 100 + offset1_x, self.center + offset1_y)

        offset2_x = self._get_random_offset(100)
        offset2_y = self._get_random_offset(100)
        center2 = (self.center + 100 + offset2_x, self.center + offset2_y)

        self._draw_circle(draw, center1, 250, colors[0])
        self._draw_circle(draw, center2, 250, colors[1])

        intersection_x = (center1[0] + center2[0]) // 2 + random.randint(-50, 50)
        intersection_y = (center1[1] + center2[1]) // 2 + random.randint(-50, 50)
        intersection_center = (intersection_x, intersection_y)

        self._draw_star(draw, intersection_center, 80, 30, 6, colors[2])

    def pattern_wave_flow(self, draw, colors):
        """Pattern 17: Wave flow."""
        wave_points = []
        for i in range(7):
            x = self.center - 300 + (i * 100)
            y = self.center + 100 * math.sin(math.radians(i * 60))

            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-50, 50)
            wave_points.append((int(x + offset_x), int(y + offset_y)))

        for i, point in enumerate(wave_points):
            size = random.randint(60, 120)
            color = colors[i % len(colors)]

            if i % 3 == 0:
                self._draw_circle(draw, point, size//2, color)
            elif i % 3 == 1:
                self._draw_square(draw, point, size, color, rotation=random.randint(0, 45))
            else:
                self._draw_triangle(draw, point, size, color, rotation=random.randint(0, 180))

    def pattern_cluster_burst(self, draw, colors):
        """Pattern 18: Cluster burst."""
        center_offset_x = self._get_random_offset(50)
        center_offset_y = self._get_random_offset(50)
        burst_center = (self.center + center_offset_x, self.center + center_offset_y)

        self._draw_star(draw, burst_center, 100, 40, 8, colors[0])

        num_fragments = random.randint(8, 12)
        for i in range(num_fragments):
            angle = math.radians(i * (360 / num_fragments) + random.randint(-30, 30))
            distance = random.randint(150, 300)

            x = burst_center[0] + distance * math.cos(angle)
            y = burst_center[1] + distance * math.sin(angle)
            pos = (int(x), int(y))

            size = random.randint(30, 80)
            color = colors[(i + 1) % len(colors)]

            fragment_type = random.randint(0, 3)
            if fragment_type == 0:
                self._draw_circle(draw, pos, size//2, color)
            elif fragment_type == 1:
                self._draw_square(draw, pos, size, color, rotation=random.randint(0, 90))
            elif fragment_type == 2:
                self._draw_triangle(draw, pos, size, color, rotation=random.randint(0, 360))
            else:
                self._draw_star(draw, pos, size//2, size//4, 5, color, rotation=random.randint(0, 72))

    def pattern_frame_and_center(self, draw, colors):
        """Pattern 19: Frame and center."""
        frame_positions = [
            (self.center, self.center - 250),
            (self.center + 250, self.center),
            (self.center, self.center + 250),
            (self.center - 250, self.center)
        ]

        for i, pos in enumerate(frame_positions):
            offset_x = random.randint(-80, 80)
            offset_y = random.randint(-80, 80)
            actual_pos = (pos[0] + offset_x, pos[1] + offset_y)

            size = random.randint(80, 120)
            color = colors[i % len(colors)]

            if i % 2 == 0:
                self._draw_square(draw, actual_pos, size, color, rotation=45)
            else:
                self._draw_circle(draw, actual_pos, size//2, color)

        center_offset_x = self._get_random_offset(60)
        center_offset_y = self._get_random_offset(60)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self._draw_hexagon(draw, center, 120, colors[0])

    def pattern_dynamic_balance(self, draw, colors):
        """Pattern 20: Dynamic balance."""
        large_x = self.center - 150 + random.randint(-50, 50)
        large_y = self.center + random.randint(-100, 100)
        large_center = (large_x, large_y)
        self._draw_circle(draw, large_center, 200, colors[0])

        small_shapes_base_x = self.center + 150
        small_shapes_base_y = self.center

        for i in range(4):
            offset_x = random.randint(-100, 100)
            offset_y = random.randint(-150, 150)
            pos = (small_shapes_base_x + offset_x, small_shapes_base_y + offset_y)

            size = random.randint(40, 80)
            color = colors[(i + 1) % len(colors)]

            if i % 3 == 0:
                self._draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
            elif i % 3 == 1:
                self._draw_triangle(draw, pos, size, color, rotation=random.randint(0, 180))
            else:
                self._draw_hexagon(draw, pos, size//2, color)

    def pattern_centered_circle_modified(self, draw, colors):
        """Pattern 21: Centered circle modified."""
        main_offset_x = self._get_random_offset(80)
        main_offset_y = self._get_random_offset(80)
        main_center = (self.center + main_offset_x, self.center + main_offset_y)
        size = random.randint(300, 400)
        self._draw_circle(draw, main_center, size//2, colors[0])

        inner_offset_x = main_offset_x + random.randint(-50, 50)
        inner_offset_y = main_offset_y + random.randint(-50, 50)
        inner_center = (self.center + inner_offset_x, self.center + inner_offset_y)
        self._draw_circle(draw, inner_center, size//4, colors[1])

    def pattern_geometric_mix_modified(self, draw, colors):
        """Pattern 22: Geometric mix modified."""
        bg_offset_x = self._get_random_offset(100)
        bg_offset_y = self._get_random_offset(100)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self._draw_circle(draw, bg_center, 350, colors[0])

        sq_offset_x = bg_offset_x + random.randint(-80, 80)
        sq_offset_y = bg_offset_y + random.randint(-80, 80)
        sq_center = (self.center + sq_offset_x, self.center + sq_offset_y)
        self._draw_square(draw, sq_center, 250, colors[1], rotation=45)

        tri_offset_x = sq_offset_x + random.randint(-60, 60)
        tri_offset_y = sq_offset_y + random.randint(-60, 60)
        tri_center = (self.center + tri_offset_x, self.center + tri_offset_y)
        self._draw_triangle(draw, tri_center, 150, colors[2])

    def pattern_star_shape_modified(self, draw, colors):
        """Pattern 23: Star shape modified."""
        bg_offset_x = self._get_random_offset(120)
        bg_offset_y = self._get_random_offset(120)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self._draw_circle(draw, bg_center, 400, colors[0])

        star_offset_x = bg_offset_x + random.randint(-100, 100)
        star_offset_y = bg_offset_y + random.randint(-100, 100)
        star_center = (self.center + star_offset_x, self.center + star_offset_y)
        rotation = random.randint(-90, 90)
        self._draw_star(draw, star_center, 250, 100, 5, colors[1], rotation)

        center_offset_x = star_offset_x + random.randint(-40, 40)
        center_offset_y = star_offset_y + random.randint(-40, 40)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self._draw_circle(draw, center, 80, colors[2])

    def pattern_hexagon_offset(self, draw, colors):
        """Pattern 24: Hexagon offset."""
        outer_offset_x = self._get_random_offset(100)
        outer_offset_y = self._get_random_offset(100)
        outer_center = (self.center + outer_offset_x, self.center + outer_offset_y)
        self._draw_hexagon(draw, outer_center, 300, colors[0])

        inner_offset_x = outer_offset_x + random.randint(-80, 80)
        inner_offset_y = outer_offset_y + random.randint(-80, 80)
        inner_center = (self.center + inner_offset_x, self.center + inner_offset_y)
        self._draw_circle(draw, inner_center, 200, colors[1])

        innermost_offset_x = inner_offset_x + random.randint(-50, 50)
        innermost_offset_y = inner_offset_y + random.randint(-50, 50)
        innermost_center = (self.center + innermost_offset_x, self.center + innermost_offset_y)
        self._draw_hexagon(draw, innermost_center, 100, colors[2])

    def pattern_cross_asymmetric(self, draw, colors):
        """Pattern 25: Asymmetric cross."""
        bg_offset_x = self._get_random_offset(80)
        bg_offset_y = self._get_random_offset(80)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self._draw_circle(draw, bg_center, 400, colors[0])

        cross_offset_x = bg_offset_x + random.randint(-60, 60)
        cross_offset_y = bg_offset_y + random.randint(-60, 60)
        cross_center = (self.center + cross_offset_x, self.center + cross_offset_y)

        draw.rectangle([cross_center[0] - 40, cross_center[1] - 150,
                       cross_center[0] + 40, cross_center[1] + 150], fill=colors[1])
        draw.rectangle([cross_center[0] - 150, cross_center[1] - 40,
                       cross_center[0] + 150, cross_center[1] + 40], fill=colors[1])

        center_offset_x = cross_offset_x + random.randint(-30, 30)
        center_offset_y = cross_offset_y + random.randint(-30, 30)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self._draw_square(draw, center, 100, colors[2], rotation=45)

    def generate(self, output_path: Optional[Path] = None, pattern_index: Optional[int] = None) -> Image.Image:
        """
        Generate logo with random geometric pattern.

        Args:
            output_path: Save path (None for Image object only)
            pattern_index: Specific pattern (None for random)

        Returns:
            PIL Image object
        """
        # Create new image
        img = Image.new('RGB', (self.size, self.size), self.background_color)
        draw = ImageDraw.Draw(img)

        # Select color palette
        colors = self._get_random_color_palette()

        # Select pattern
        if pattern_index is not None and 0 <= pattern_index < len(self.patterns):
            pattern = self.patterns[pattern_index]
            logger.info(f"Using pattern #{pattern_index}: {pattern.__name__}")
        else:
            pattern = random.choice(self.patterns)
            logger.info(f"Using random pattern: {pattern.__name__}")

        # Draw pattern
        pattern(draw, colors)

        # Save to file
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG')
            logger.info(f"Logo saved: {output_path}")

        return img


def generate_logo(
    output_path: Path,
    size: int = 1024,
    background_color: Optional[Tuple[int, int, int]] = None,
    pattern_index: Optional[int] = None
) -> Image.Image:
    """
    Convenience function to generate logo.

    Args:
        output_path: Save path for logo
        size: Image size (default: 1024)
        background_color: RGB tuple or None for random
        pattern_index: Specific pattern or None for random

    Returns:
        PIL Image object

    Example:
        >>> logo = generate_logo(Path("app_icon.png"))
    """
    generator = LogoGenerator(size=size, background_color=background_color)
    return generator.generate(output_path=output_path, pattern_index=pattern_index)
