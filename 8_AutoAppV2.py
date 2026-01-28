import plistlib
import subprocess
import os
import shutil
import yaml
import re
import sqlite3
import json
import time
import datetime
import pickle
from pathlib import Path
from PIL import Image, ImageDraw
from googleapiclient import discovery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import sys
import unicodedata
import socket
import socketserver
import random
import math

# 전역 변수
generated_privacy_policy_url = ""

# 상수 정의
CLIENT_SECRET = '/Users/jongminkim/Desktop/Apps/qcjongmin/client_secret_156950230449-p855cnddrfhl2o7tgs82c7jj9pdshr1j.apps.googleusercontent.com.json'
SCOPES = ['https://www.googleapis.com/auth/blogger']
BLOG_ID = '2760621040889199473'
TOKEN_FILE = "auto_token.pickle"
PORT = 8080

# LogoGenerator 클래스 수정 부분
class LogoGenerator:
    def __init__(self, size=1024, background_color=None):
        """
        로고 생성기 초기화
        :param size: 정사각형 이미지의 크기 (기본 1024x1024)
        :param background_color: 배경색 (None이면 랜덤 선택)
        """
        self.size = size
        self.center = size // 2
        
        # 배경색 팔레트 (파스텔 톤의 다양한 색상)
        self.background_colors = [
            (255, 255, 255),  # 순수 흰색
            (255, 228, 225),  # 연한 분홍 (Misty Rose)
            (255, 239, 213),  # 연한 살구색 (Papaya Whip)
            (230, 230, 250),  # 연한 보라 (Lavender)
            (240, 255, 255),  # 연한 하늘색 (Azure)
            (255, 250, 205),  # 연한 노랑 (Lemon Chiffon)
            (225, 255, 225),  # 연한 민트 (Honeydew 변형)
            (255, 228, 196),  # 연한 베이지 (Bisque)
            (224, 255, 255),  # 연한 청록 (Light Cyan)
            (255, 240, 245),  # 연한 라벤더 핑크 (Lavender Blush)
            (240, 248, 255),  # 앨리스 블루
            (245, 255, 250),  # 민트 크림
            (255, 245, 238),  # 시셸
            (248, 248, 255),  # 고스트 화이트
        ]
        
        # 배경색 이름 매핑 (디버깅/로깅용)
        self.background_color_names = {
            (255, 255, 255): "순수 흰색",
            (255, 228, 225): "연한 분홍",
            (255, 239, 213): "연한 살구색",
            (230, 230, 250): "연한 보라",
            (240, 255, 255): "연한 하늘색",
            (255, 250, 205): "연한 노랑",
            (225, 255, 225): "연한 민트",
            (255, 228, 196): "연한 베이지",
            (224, 255, 255): "연한 청록",
            (255, 240, 245): "연한 라벤더 핑크",
            (240, 248, 255): "앨리스 블루",
            (245, 255, 250): "민트 크림",
            (255, 245, 238): "시셸",
            (248, 248, 255): "고스트 화이트"
        }
        
        # 배경색 설정 (None이면 랜덤 선택)
        if background_color is None:
            self.background_color = random.choice(self.background_colors)
        else:
            self.background_color = background_color
        
        # 사용할 색상 팔레트 (앱 아이콘에 적합한 선명한 색상들 - 붉은색 계열 제거)
        self.color_palettes = [
            # 파란색 계열
            [(0, 123, 255), (0, 86, 179), (41, 128, 185)],
            # 초록색 계열
            [(46, 204, 113), (39, 174, 96), (34, 153, 84)],
            # 주황색 계열 (붉은색이 아닌 순수 주황색)
            [(255, 152, 0), (255, 138, 34), (230, 126, 34)],
            # 보라색 계열
            [(155, 89, 182), (142, 68, 173), (125, 60, 152)],
            # 청록색 계열
            [(26, 188, 156), (22, 160, 133), (19, 141, 117)],
            # 노란색 계열
            [(255, 193, 7), (255, 179, 0), (255, 160, 0)],
            # 남색 계열
            [(63, 81, 181), (57, 73, 171), (48, 63, 159)],
            # 회색 계열
            [(96, 125, 139), (84, 110, 122), (69, 90, 100)],
            # 그라데이션 파란색
            [(100, 181, 246), (33, 150, 243), (13, 71, 161)],
            # 그라데이션 초록색
            [(129, 199, 132), (76, 175, 80), (27, 94, 32)],
            # 그라데이션 보라색
            [(186, 104, 200), (171, 71, 188), (106, 27, 154)],
            # 따뜻한 색상 조합 (붉은색 제외)
            [(255, 152, 0), (255, 193, 7), (255, 235, 59)],
            # 차가운 색상 조합
            [(33, 150, 243), (0, 188, 212), (0, 150, 136)],
            # 자연 색상 조합
            [(76, 175, 80), (139, 195, 74), (205, 220, 57)],
            # 보석 색상 조합
            [(156, 39, 176), (103, 58, 183), (63, 81, 181)]
        ]
        
        # 조합 패턴 정의 (기존 + 새로운 다양한 배치 패턴들)
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
            # 기존 패턴들도 일부 유지 (수정된 버전)
            self.pattern_centered_circle_modified,
            self.pattern_geometric_mix_modified,
            self.pattern_star_shape_modified,
            self.pattern_hexagon_offset,
            self.pattern_cross_asymmetric
        ]
    
    def get_random_offset(self, max_offset=150):
        """랜덤 오프셋 생성"""
        return random.randint(-max_offset, max_offset)
    
    def get_background_color_name(self):
        """현재 배경색의 이름을 반환"""
        return self.background_color_names.get(self.background_color, "Unknown")
    
    def get_random_color_palette(self):
        """랜덤 색상 팔레트 선택"""
        return random.choice(self.color_palettes)
    
    # 기본 도형 그리기 함수들 (기존과 동일)
    def draw_circle(self, draw, center, radius, color, fill=True):
        """원 그리기"""
        bbox = [center[0] - radius, center[1] - radius,
                center[0] + radius, center[1] + radius]
        if fill:
            draw.ellipse(bbox, fill=color)
        else:
            draw.ellipse(bbox, outline=color, width=5)
    
    def draw_square(self, draw, center, size, color, rotation=0, fill=True):
        """정사각형 그리기 (회전 가능)"""
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
    
    def draw_triangle(self, draw, center, size, color, rotation=0, fill=True):
        """정삼각형 그리기 (회전 가능)"""
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
    
    def draw_hexagon(self, draw, center, size, color, fill=True):
        """육각형 그리기"""
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
    
    def draw_star(self, draw, center, outer_radius, inner_radius, points_count, color, rotation=0):
        """별 모양 그리기"""
        points = []
        for i in range(points_count * 2):
            angle = math.radians(360 / (points_count * 2) * i + rotation)
            if i % 2 == 0:
                radius = outer_radius
            else:
                radius = inner_radius
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            points.append((x, y))
        
        draw.polygon(points, fill=color)
    
    # === 새로운 다양한 배치 패턴들 ===
    
    def pattern_offset_circles(self, draw, colors):
        """패턴 1: 오프셋된 원들"""
        # 메인 원
        main_offset_x = self.get_random_offset(100)
        main_offset_y = self.get_random_offset(100)
        main_center = (self.center + main_offset_x, self.center + main_offset_y)
        self.draw_circle(draw, main_center, 320, colors[0])
        
        # 보조 원들
        for i in range(2):
            offset_x = self.get_random_offset(200)
            offset_y = self.get_random_offset(200)
            center = (self.center + offset_x, self.center + offset_y)
            radius = random.randint(120, 180)
            self.draw_circle(draw, center, radius, colors[(i + 1) % len(colors)])
    
    def pattern_asymmetric_squares(self, draw, colors):
        """패턴 2: 비대칭 사각형들"""
        # 큰 사각형 (중앙에서 벗어남)
        offset_x = self.get_random_offset(150)
        offset_y = self.get_random_offset(150)
        main_center = (self.center + offset_x, self.center + offset_y)
        rotation = random.randint(0, 45)
        self.draw_square(draw, main_center, 350, colors[0], rotation)
        
        # 작은 사각형들 (다양한 위치)
        for i in range(3):
            offset_x = self.get_random_offset(250)
            offset_y = self.get_random_offset(250)
            center = (self.center + offset_x, self.center + offset_y)
            size = random.randint(80, 150)
            rotation = random.randint(0, 90)
            self.draw_square(draw, center, size, colors[(i + 1) % len(colors)], rotation)
    
    def pattern_scattered_triangles(self, draw, colors):
        """패턴 3: 흩어진 삼각형들"""
        # 중앙 원
        center_offset_x = self.get_random_offset(80)
        center_offset_y = self.get_random_offset(80)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self.draw_circle(draw, center, 200, colors[0])
        
        # 삼각형들을 다양한 위치에 배치
        triangle_count = random.randint(4, 7)
        for i in range(triangle_count):
            offset_x = self.get_random_offset(300)
            offset_y = self.get_random_offset(300)
            pos = (self.center + offset_x, self.center + offset_y)
            size = random.randint(60, 120)
            rotation = random.randint(0, 360)
            self.draw_triangle(draw, pos, size, colors[(i + 1) % len(colors)], rotation)
    
    def pattern_overlapping_offset(self, draw, colors):
        """패턴 4: 겹치는 오프셋 도형들"""
        # 첫 번째 원 (약간 위쪽)
        center1 = (self.center + self.get_random_offset(100), self.center - random.randint(50, 150))
        self.draw_circle(draw, center1, 280, colors[0])
        
        # 두 번째 원 (약간 아래쪽, 겹침)
        center2 = (self.center + self.get_random_offset(100), self.center + random.randint(50, 150))
        self.draw_circle(draw, center2, 260, colors[1])
        
        # 중앙 사각형 (두 원 사이)
        square_center = (self.center + self.get_random_offset(50), self.center)
        self.draw_square(draw, square_center, 180, colors[2], rotation=45)
    
    def pattern_corner_emphasis(self, draw, colors):
        """패턴 5: 모서리 강조 패턴"""
        # 중앙 도형
        self.draw_hexagon(draw, (self.center, self.center), 150, colors[0])
        
        # 모서리 근처에 도형 배치
        corners = [
            (self.center - 200, self.center - 200),
            (self.center + 200, self.center - 200),
            (self.center + 200, self.center + 200),
            (self.center - 200, self.center + 200)
        ]
        
        for i, corner in enumerate(corners):
            # 각 모서리에서 약간씩 다른 위치에 배치
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-50, 50)
            pos = (corner[0] + offset_x, corner[1] + offset_y)
            
            if i % 2 == 0:
                self.draw_circle(draw, pos, 80, colors[(i + 1) % len(colors)])
            else:
                self.draw_square(draw, pos, 120, colors[(i + 1) % len(colors)], rotation=45)
    
    def pattern_diagonal_flow(self, draw, colors):
        """패턴 6: 대각선 플로우"""
        # 대각선을 따라 도형 배치
        num_shapes = 5
        for i in range(num_shapes):
            # 대각선 위치 계산 (왼쪽 위에서 오른쪽 아래로)
            progress = i / (num_shapes - 1)
            base_x = self.center - 300 + (600 * progress)
            base_y = self.center - 300 + (600 * progress)
            
            # 대각선에서 약간 벗어나게 배치
            offset_x = random.randint(-80, 80)
            offset_y = random.randint(-80, 80)
            pos = (int(base_x + offset_x), int(base_y + offset_y))
            
            size = random.randint(60, 120)
            shape_type = i % 3
            
            if shape_type == 0:
                self.draw_circle(draw, pos, size//2, colors[i % len(colors)])
            elif shape_type == 1:
                self.draw_square(draw, pos, size, colors[i % len(colors)], rotation=random.randint(0, 45))
            else:
                self.draw_triangle(draw, pos, size, colors[i % len(colors)], rotation=random.randint(0, 180))
    
    def pattern_clustered_shapes(self, draw, colors):
        """패턴 7: 클러스터된 도형들"""
        # 여러 클러스터 생성
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
                    self.draw_circle(draw, pos, size//2, color)
                else:
                    self.draw_square(draw, pos, size, color, rotation=random.randint(0, 90))
    
    def pattern_random_positioning(self, draw, colors):
        """패턴 8: 완전 랜덤 포지셔닝"""
        # 배경 원
        bg_offset_x = self.get_random_offset(50)
        bg_offset_y = self.get_random_offset(50)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self.draw_circle(draw, bg_center, 350, colors[0])
        
        # 랜덤 도형들
        num_shapes = random.randint(6, 10)
        for i in range(num_shapes):
            offset_x = self.get_random_offset(250)
            offset_y = self.get_random_offset(250)
            pos = (self.center + offset_x, self.center + offset_y)
            
            # 중심에서 너무 멀면 스킵
            distance = math.sqrt(offset_x**2 + offset_y**2)
            if distance > 280:
                continue
            
            size = random.randint(30, 100)
            color = colors[(i + 1) % len(colors)]
            shape_type = random.randint(0, 2)
            
            if shape_type == 0:
                self.draw_circle(draw, pos, size//2, color)
            elif shape_type == 1:
                self.draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
            else:
                self.draw_triangle(draw, pos, size, color, rotation=random.randint(0, 360))
    
    def pattern_layered_offset(self, draw, colors):
        """패턴 9: 레이어된 오프셋"""
        # 여러 레이어를 다른 위치에 배치
        layers = [
            (400, colors[0]),
            (300, colors[1]),
            (200, colors[2]),
            (100, colors[0])
        ]
        
        for i, (size, color) in enumerate(layers):
            offset_x = self.get_random_offset(50 + i * 20)
            offset_y = self.get_random_offset(50 + i * 20)
            center = (self.center + offset_x, self.center + offset_y)
            
            if i % 2 == 0:
                self.draw_circle(draw, center, size//2, color)
            else:
                self.draw_square(draw, center, size, color, rotation=45)
    
    def pattern_spiral_offset(self, draw, colors):
        """패턴 10: 나선형 오프셋"""
        # 나선형으로 배치하되 각 요소마다 랜덤 오프셋 추가
        num_elements = 8
        for i in range(num_elements):
            angle = math.radians(i * 45)
            base_radius = 80 + i * 25
            
            base_x = self.center + base_radius * math.cos(angle)
            base_y = self.center + base_radius * math.sin(angle)
            
            # 랜덤 오프셋 추가
            offset_x = random.randint(-40, 40)
            offset_y = random.randint(-40, 40)
            pos = (int(base_x + offset_x), int(base_y + offset_y))
            
            size = random.randint(40, 80)
            color = colors[i % len(colors)]
            
            if i % 3 == 0:
                self.draw_circle(draw, pos, size//2, color)
            elif i % 3 == 1:
                self.draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
            else:
                self.draw_triangle(draw, pos, size, color, rotation=random.randint(0, 180))
        
        # 중앙에 작은 도형
        center_offset_x = self.get_random_offset(30)
        center_offset_y = self.get_random_offset(30)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self.draw_star(draw, center, 60, 25, 6, colors[0])
    
    # 기존 패턴들의 수정된 버전들
    def pattern_centered_circle_modified(self, draw, colors):
        """수정된 중앙 원 패턴"""
        # 메인 원을 약간 오프셋
        main_offset_x = self.get_random_offset(80)
        main_offset_y = self.get_random_offset(80)
        main_center = (self.center + main_offset_x, self.center + main_offset_y)
        size = random.randint(300, 400)
        self.draw_circle(draw, main_center, size//2, colors[0])
        
        # 내부 원을 다른 위치에 배치
        inner_offset_x = main_offset_x + random.randint(-50, 50)
        inner_offset_y = main_offset_y + random.randint(-50, 50)
        inner_center = (self.center + inner_offset_x, self.center + inner_offset_y)
        self.draw_circle(draw, inner_center, size//4, colors[1])
    
    def pattern_geometric_mix_modified(self, draw, colors):
        """수정된 기하학적 혼합"""
        # 배경 원 (오프셋)
        bg_offset_x = self.get_random_offset(100)
        bg_offset_y = self.get_random_offset(100)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self.draw_circle(draw, bg_center, 350, colors[0])
        
        # 중앙 사각형 (다른 오프셋)
        sq_offset_x = bg_offset_x + random.randint(-80, 80)
        sq_offset_y = bg_offset_y + random.randint(-80, 80)
        sq_center = (self.center + sq_offset_x, self.center + sq_offset_y)
        self.draw_square(draw, sq_center, 250, colors[1], rotation=45)
        
        # 안쪽 삼각형 (또 다른 오프셋)
        tri_offset_x = sq_offset_x + random.randint(-60, 60)
        tri_offset_y = sq_offset_y + random.randint(-60, 60)
        tri_center = (self.center + tri_offset_x, self.center + tri_offset_y)
        self.draw_triangle(draw, tri_center, 150, colors[2])
    
    def pattern_star_shape_modified(self, draw, colors):
        """수정된 별 모양"""
        # 배경 원 (오프셋)
        bg_offset_x = self.get_random_offset(120)
        bg_offset_y = self.get_random_offset(120)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self.draw_circle(draw, bg_center, 400, colors[0])
        
        # 별 (다른 위치)
        star_offset_x = bg_offset_x + random.randint(-100, 100)
        star_offset_y = bg_offset_y + random.randint(-100, 100)
        star_center = (self.center + star_offset_x, self.center + star_offset_y)
        rotation = random.randint(-90, 90)
        self.draw_star(draw, star_center, 250, 100, 5, colors[1], rotation)
        
        # 중앙 원 (또 다른 위치)
        center_offset_x = star_offset_x + random.randint(-40, 40)
        center_offset_y = star_offset_y + random.randint(-40, 40)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self.draw_circle(draw, center, 80, colors[2])
    
    def pattern_hexagon_offset(self, draw, colors):
        """오프셋된 육각형 패턴"""
        # 외부 육각형
        outer_offset_x = self.get_random_offset(100)
        outer_offset_y = self.get_random_offset(100)
        outer_center = (self.center + outer_offset_x, self.center + outer_offset_y)
        self.draw_hexagon(draw, outer_center, 300, colors[0])
        
        # 내부 원 (다른 위치)
        inner_offset_x = outer_offset_x + random.randint(-80, 80)
        inner_offset_y = outer_offset_y + random.randint(-80, 80)
        inner_center = (self.center + inner_offset_x, self.center + inner_offset_y)
        self.draw_circle(draw, inner_center, 200, colors[1])
        
        # 가장 안쪽 육각형 (또 다른 위치)
        innermost_offset_x = inner_offset_x + random.randint(-50, 50)
        innermost_offset_y = inner_offset_y + random.randint(-50, 50)
        innermost_center = (self.center + innermost_offset_x, self.center + innermost_offset_y)
        self.draw_hexagon(draw, innermost_center, 100, colors[2])
    
    def pattern_cross_asymmetric(self, draw, colors):
        """비대칭 십자가 패턴"""
        # 배경 원
        bg_offset_x = self.get_random_offset(80)
        bg_offset_y = self.get_random_offset(80)
        bg_center = (self.center + bg_offset_x, self.center + bg_offset_y)
        self.draw_circle(draw, bg_center, 400, colors[0])
        
        # 십자가 (다른 위치)
        cross_offset_x = bg_offset_x + random.randint(-60, 60)
        cross_offset_y = bg_offset_y + random.randint(-60, 60)
        cross_center = (self.center + cross_offset_x, self.center + cross_offset_y)
        
        # 세로 막대
        draw.rectangle([cross_center[0] - 40, cross_center[1] - 150,
                       cross_center[0] + 40, cross_center[1] + 150], fill=colors[1])
        # 가로 막대
        draw.rectangle([cross_center[0] - 150, cross_center[1] - 40,
                       cross_center[0] + 150, cross_center[1] + 40], fill=colors[1])
        
        # 중앙 사각형 (또 다른 위치)
        center_offset_x = cross_offset_x + random.randint(-30, 30)
        center_offset_y = cross_offset_y + random.randint(-30, 30)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self.draw_square(draw, center, 100, colors[2], rotation=45)

    # 추가 새로운 패턴들
    def pattern_grid_variations(self, draw, colors):
        """격자 변형 패턴"""
        # 3x3 격자이지만 각 요소가 다른 위치에
        for i in range(3):
            for j in range(3):
                if i == 1 and j == 1:  # 중앙은 특별하게
                    center_offset_x = self.get_random_offset(50)
                    center_offset_y = self.get_random_offset(50)
                    center = (self.center + center_offset_x, self.center + center_offset_y)
                    self.draw_star(draw, center, 80, 30, 6, colors[0])
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
                        self.draw_circle(draw, pos, size//2, color)
                    elif shape_type == 1:
                        self.draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
                    else:
                        self.draw_triangle(draw, pos, size, color, rotation=random.randint(0, 180))

    def pattern_floating_elements(self, draw, colors):
        """떠있는 요소들 패턴"""
        # 메인 중앙 도형
        main_offset_x = self.get_random_offset(60)
        main_offset_y = self.get_random_offset(60)
        main_center = (self.center + main_offset_x, self.center + main_offset_y)
        self.draw_circle(draw, main_center, 200, colors[0])
        
        # 주변에 떠있는 작은 요소들
        for i in range(8):
            angle = math.radians(i * 45)
            distance = random.randint(250, 350)
            
            base_x = self.center + distance * math.cos(angle)
            base_y = self.center + distance * math.sin(angle)
            
            # 각 요소마다 추가 오프셋
            offset_x = random.randint(-100, 100)
            offset_y = random.randint(-100, 100)
            pos = (int(base_x + offset_x), int(base_y + offset_y))
            
            size = random.randint(30, 70)
            color = colors[(i + 1) % len(colors)]
            
            if i % 4 == 0:
                self.draw_circle(draw, pos, size//2, color)
            elif i % 4 == 1:
                self.draw_square(draw, pos, size, color, rotation=random.randint(0, 90))
            elif i % 4 == 2:
                self.draw_triangle(draw, pos, size, color, rotation=random.randint(0, 360))
            else:
                self.draw_hexagon(draw, pos, size//2, color)

    def pattern_cascade_design(self, draw, colors):
        """계단식 디자인"""
        # 크기가 점점 작아지는 도형들을 다양한 위치에 배치
        sizes = [350, 250, 150, 80]
        cumulative_offset_x = 0
        cumulative_offset_y = 0
        
        for i, size in enumerate(sizes):
            offset_x = self.get_random_offset(80)
            offset_y = self.get_random_offset(80)
            
            cumulative_offset_x += offset_x // (i + 1)
            cumulative_offset_y += offset_y // (i + 1)
            
            center = (self.center + cumulative_offset_x, self.center + cumulative_offset_y)
            color = colors[i % len(colors)]
            
            if i % 3 == 0:
                self.draw_circle(draw, center, size//2, color)
            elif i % 3 == 1:
                self.draw_square(draw, center, size, color, rotation=45 * i)
            else:
                self.draw_triangle(draw, center, size, color, rotation=60 * i)

    def pattern_orbital_arrangement(self, draw, colors):
        """궤도 배열 패턴"""
        # 중앙 "태양"
        sun_offset_x = self.get_random_offset(50)
        sun_offset_y = self.get_random_offset(50)
        sun_center = (self.center + sun_offset_x, self.center + sun_offset_y)
        self.draw_star(draw, sun_center, 120, 50, 8, colors[0])
        
        # "행성들" - 각기 다른 궤도와 위치
        orbits = [150, 220, 290]
        for orbit_idx, orbit_radius in enumerate(orbits):
            num_planets = random.randint(2, 4)
            for planet_idx in range(num_planets):
                angle = math.radians(planet_idx * (360 / num_planets) + orbit_idx * 30)
                
                base_x = sun_center[0] + orbit_radius * math.cos(angle)
                base_y = sun_center[1] + orbit_radius * math.sin(angle)
                
                # 궤도에서 벗어나게 배치
                deviation_x = random.randint(-50, 50)
                deviation_y = random.randint(-50, 50)
                pos = (int(base_x + deviation_x), int(base_y + deviation_y))
                
                size = random.randint(30, 80)
                color = colors[(orbit_idx + planet_idx + 1) % len(colors)]
                
                if planet_idx % 2 == 0:
                    self.draw_circle(draw, pos, size//2, color)
                else:
                    self.draw_square(draw, pos, size, color, rotation=random.randint(0, 90))

    def pattern_split_composition(self, draw, colors):
        """분할 구성 패턴"""
        # 화면을 두 영역으로 나누어 각각 다른 스타일로 배치
        # 왼쪽 영역
        left_center_x = self.center - 150 + random.randint(-50, 50)
        left_center_y = self.center + random.randint(-100, 100)
        left_center = (left_center_x, left_center_y)
        
        self.draw_circle(draw, left_center, 180, colors[0])
        self.draw_square(draw, (left_center_x + random.randint(-30, 30), 
                               left_center_y + random.randint(-30, 30)), 
                        120, colors[1], rotation=45)
        
        # 오른쪽 영역
        right_center_x = self.center + 150 + random.randint(-50, 50)
        right_center_y = self.center + random.randint(-100, 100)
        right_center = (right_center_x, right_center_y)
        
        self.draw_triangle(draw, right_center, 200, colors[2], rotation=random.randint(0, 180))
        self.draw_hexagon(draw, (right_center_x + random.randint(-40, 40),
                                right_center_y + random.randint(-40, 40)), 
                         60, colors[0])

    def pattern_intersection_design(self, draw, colors):
        """교차 디자인 패턴"""
        # 두 개의 큰 원이 교차하되 완전히 중앙이 아닌 위치에
        offset1_x = self.get_random_offset(100)
        offset1_y = self.get_random_offset(100)
        center1 = (self.center - 100 + offset1_x, self.center + offset1_y)
        
        offset2_x = self.get_random_offset(100)
        offset2_y = self.get_random_offset(100)
        center2 = (self.center + 100 + offset2_x, self.center + offset2_y)
        
        self.draw_circle(draw, center1, 250, colors[0])
        self.draw_circle(draw, center2, 250, colors[1])
        
        # 교차점 근처에 작은 도형
        intersection_x = (center1[0] + center2[0]) // 2 + random.randint(-50, 50)
        intersection_y = (center1[1] + center2[1]) // 2 + random.randint(-50, 50)
        intersection_center = (intersection_x, intersection_y)
        
        self.draw_star(draw, intersection_center, 80, 30, 6, colors[2])

    def pattern_wave_flow(self, draw, colors):
        """파동 흐름 패턴"""
        # 웨이브 형태로 도형들을 배치
        wave_points = []
        for i in range(7):
            x = self.center - 300 + (i * 100)
            y = self.center + 100 * math.sin(math.radians(i * 60))
            
            # 웨이브에서 벗어나게 배치
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-50, 50)
            wave_points.append((int(x + offset_x), int(y + offset_y)))
        
        for i, point in enumerate(wave_points):
            size = random.randint(60, 120)
            color = colors[i % len(colors)]
            
            if i % 3 == 0:
                self.draw_circle(draw, point, size//2, color)
            elif i % 3 == 1:
                self.draw_square(draw, point, size, color, rotation=random.randint(0, 45))
            else:
                self.draw_triangle(draw, point, size, color, rotation=random.randint(0, 180))

    def pattern_cluster_burst(self, draw, colors):
        """클러스터 폭발 패턴"""
        # 중앙에서 폭발하는 듯한 효과
        center_offset_x = self.get_random_offset(50)
        center_offset_y = self.get_random_offset(50)
        burst_center = (self.center + center_offset_x, self.center + center_offset_y)
        
        # 중앙 핵
        self.draw_star(draw, burst_center, 100, 40, 8, colors[0])
        
        # 폭발하는 파편들
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
                self.draw_circle(draw, pos, size//2, color)
            elif fragment_type == 1:
                self.draw_square(draw, pos, size, color, rotation=random.randint(0, 90))
            elif fragment_type == 2:
                self.draw_triangle(draw, pos, size, color, rotation=random.randint(0, 360))
            else:
                # 작은 별
                self.draw_star(draw, pos, size//2, size//4, 5, color, rotation=random.randint(0, 72))

    def pattern_frame_and_center(self, draw, colors):
        """프레임과 중앙 패턴"""
        # 외곽 프레임 도형들
        frame_positions = [
            (self.center, self.center - 250),  # 상단
            (self.center + 250, self.center),  # 우측
            (self.center, self.center + 250),  # 하단
            (self.center - 250, self.center)   # 좌측
        ]
        
        for i, pos in enumerate(frame_positions):
            offset_x = random.randint(-80, 80)
            offset_y = random.randint(-80, 80)
            actual_pos = (pos[0] + offset_x, pos[1] + offset_y)
            
            size = random.randint(80, 120)
            color = colors[i % len(colors)]
            
            if i % 2 == 0:
                self.draw_square(draw, actual_pos, size, color, rotation=45)
            else:
                self.draw_circle(draw, actual_pos, size//2, color)
        
        # 중앙 요소 (오프셋)
        center_offset_x = self.get_random_offset(60)
        center_offset_y = self.get_random_offset(60)
        center = (self.center + center_offset_x, self.center + center_offset_y)
        self.draw_hexagon(draw, center, 120, colors[0])

    def pattern_dynamic_balance(self, draw, colors):
        """동적 균형 패턴"""
        # 비대칭이지만 시각적으로 균형잡힌 배치
        
        # 큰 도형 하나 (한쪽에)
        large_x = self.center - 150 + random.randint(-50, 50)
        large_y = self.center + random.randint(-100, 100)
        large_center = (large_x, large_y)
        self.draw_circle(draw, large_center, 200, colors[0])
        
        # 반대쪽에 여러 작은 도형들로 균형
        small_shapes_base_x = self.center + 150
        small_shapes_base_y = self.center
        
        for i in range(4):
            offset_x = random.randint(-100, 100)
            offset_y = random.randint(-150, 150)
            pos = (small_shapes_base_x + offset_x, small_shapes_base_y + offset_y)
            
            size = random.randint(40, 80)
            color = colors[(i + 1) % len(colors)]
            
            if i % 3 == 0:
                self.draw_square(draw, pos, size, color, rotation=random.randint(0, 45))
            elif i % 3 == 1:
                self.draw_triangle(draw, pos, size, color, rotation=random.randint(0, 180))
            else:
                self.draw_hexagon(draw, pos, size//2, color)
    
    def generate_logo(self, output_path=None, pattern_index=None):
        """
        로고 생성
        :param output_path: 저장할 파일 경로 (None이면 Image 객체만 반환)
        :param pattern_index: 특정 패턴 지정 (None이면 랜덤)
        :return: PIL Image 객체
        """
        # 새 이미지 생성
        img = Image.new('RGB', (self.size, self.size), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # 색상 팔레트 선택
        colors = self.get_random_color_palette()
        
        # 패턴 선택
        if pattern_index is not None and 0 <= pattern_index < len(self.patterns):
            pattern = self.patterns[pattern_index]
        else:
            pattern = random.choice(self.patterns)
        
        # 패턴 그리기
        pattern(draw, colors)
        
        # 파일로 저장
        if output_path:
            img.save(output_path, 'PNG')
        
        return img
    
    def __init__(self, size=1024, background_color=None):
        """
        로고 생성기 초기화
        :param size: 정사각형 이미지의 크기 (기본 1024x1024)
        :param background_color: 배경색 (None이면 랜덤 선택)
        """
        self.size = size
        self.center = size // 2
        
        # 배경색 팔레트 (파스텔 톤의 다양한 색상)
        self.background_colors = [
            (255, 255, 255),  # 순수 흰색
            (255, 228, 225),  # 연한 분홍 (Misty Rose)
            (255, 239, 213),  # 연한 살구색 (Papaya Whip)
            (230, 230, 250),  # 연한 보라 (Lavender)
            (240, 255, 255),  # 연한 하늘색 (Azure)
            (255, 250, 205),  # 연한 노랑 (Lemon Chiffon)
            (225, 255, 225),  # 연한 민트 (Honeydew 변형)
            (255, 228, 196),  # 연한 베이지 (Bisque)
            (224, 255, 255),  # 연한 청록 (Light Cyan)
            (255, 240, 245),  # 연한 라벤더 핑크 (Lavender Blush)
            (240, 248, 255),  # 앨리스 블루
            (245, 255, 250),  # 민트 크림
            (255, 245, 238),  # 시쉘
            (248, 248, 255),  # 고스트 화이트
        ]
        
        # 배경색 이름 매핑 (디버깅/로깅용)
        self.background_color_names = {
            (255, 255, 255): "순수 흰색",
            (255, 228, 225): "연한 분홍",
            (255, 239, 213): "연한 살구색",
            (230, 230, 250): "연한 보라",
            (240, 255, 255): "연한 하늘색",
            (255, 250, 205): "연한 노랑",
            (225, 255, 225): "연한 민트",
            (255, 228, 196): "연한 베이지",
            (224, 255, 255): "연한 청록",
            (255, 240, 245): "연한 라벤더 핑크",
            (240, 248, 255): "앨리스 블루",
            (245, 255, 250): "민트 크림",
            (255, 245, 238): "시쉘",
            (248, 248, 255): "고스트 화이트"
        }
        
        # 배경색 설정 (None이면 랜덤 선택)
        if background_color is None:
            self.background_color = random.choice(self.background_colors)
        else:
            self.background_color = background_color
        
        # 사용할 색상 팔레트 (앱 아이콘에 적합한 선명한 색상들)
        self.color_palettes = [
            # 파란색 계열
            [(0, 123, 255), (0, 86, 179), (41, 128, 185)],
            # 초록색 계열
            [(46, 204, 113), (39, 174, 96), (34, 153, 84)],
            # 주황색 계열
            [(255, 152, 0), (255, 138, 34), (230, 126, 34)],
            # 보라색 계열
            [(155, 89, 182), (142, 68, 173), (125, 60, 152)],
            # 빨간색 계열
            [(231, 76, 60), (192, 57, 43), (169, 50, 38)],
            # 청록색 계열
            [(26, 188, 156), (22, 160, 133), (19, 141, 117)],
            # 분홍색 계열
            [(236, 64, 122), (216, 27, 96), (194, 24, 91)],
            # 노란색 계열
            [(255, 193, 7), (255, 179, 0), (255, 160, 0)],
            # 남색 계열
            [(63, 81, 181), (57, 73, 171), (48, 63, 159)],
            # 회색 계열
            [(96, 125, 139), (84, 110, 122), (69, 90, 100)],
            # 그라데이션 파란색
            [(100, 181, 246), (33, 150, 243), (13, 71, 161)],
            # 그라데이션 초록색
            [(129, 199, 132), (76, 175, 80), (27, 94, 32)],
            # 그라데이션 보라색
            [(186, 104, 200), (171, 71, 188), (106, 27, 154)],
            # 따뜻한 색상 조합
            [(255, 87, 34), (255, 152, 0), (255, 193, 7)],
            # 차가운 색상 조합
            [(33, 150, 243), (0, 188, 212), (0, 150, 136)]
        ]
        
        # 조합 패턴 정의 (기존 + 새로운 패턴들)
        self.patterns = [
            self.pattern_centered_circle,
            self.pattern_overlapping_circles,
            self.pattern_square_with_circle,
            self.pattern_triangle_composition,
            self.pattern_geometric_mix,
            self.pattern_concentric_shapes,
            self.pattern_diagonal_squares,
            self.pattern_hexagon_center,
            self.pattern_star_shape,
            self.pattern_abstract_combination,
            # 새로운 패턴들
            self.pattern_octagon_layers,
            self.pattern_cross_design,
            self.pattern_diamond_cascade,
            self.pattern_heart_shape,
            self.pattern_ellipse_composition,
            self.pattern_arrow_dynamic,
            self.pattern_plus_symbol,
            self.pattern_ring_layers,
            self.pattern_polygon_mix,
            self.pattern_semicircle_design,
            self.pattern_grid_pattern,
            self.pattern_spiral_arrangement,
            self.pattern_symmetrical_design,
            self.pattern_random_scatter,
            self.pattern_flower_shape,
            self.pattern_shield_design,
            self.pattern_letter_based,
            self.pattern_wave_design,
            self.pattern_gradient_circles,
            self.pattern_mosaic_style
        ]
    
    def get_background_color_name(self):
        """현재 배경색의 이름을 반환"""
        return self.background_color_names.get(self.background_color, "Unknown")
    
    def get_random_color_palette(self):
        """랜덤 색상 팔레트 선택"""
        return random.choice(self.color_palettes)
    
    def draw_circle(self, draw, center, radius, color, fill=True):
        """원 그리기"""
        bbox = [center[0] - radius, center[1] - radius,
                center[0] + radius, center[1] + radius]
        if fill:
            draw.ellipse(bbox, fill=color)
        else:
            draw.ellipse(bbox, outline=color, width=5)
    
    def draw_ellipse(self, draw, center, width, height, color, rotation=0, fill=True):
        """타원 그리기"""
        # 간단한 구현 - 회전은 생략
        bbox = [center[0] - width//2, center[1] - height//2,
                center[0] + width//2, center[1] + height//2]
        if fill:
            draw.ellipse(bbox, fill=color)
        else:
            draw.ellipse(bbox, outline=color, width=5)
    
    def draw_square(self, draw, center, size, color, rotation=0, fill=True):
        """정사각형 그리기 (회전 가능)"""
        half_size = size // 2
        # 꼭짓점 좌표
        points = [
            (-half_size, -half_size),
            (half_size, -half_size),
            (half_size, half_size),
            (-half_size, half_size)
        ]
        
        # 회전 적용
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
    
    def draw_triangle(self, draw, center, size, color, rotation=0, fill=True):
        """정삼각형 그리기 (회전 가능)"""
        height = int(size * math.sqrt(3) / 2)
        points = [
            (0, -height * 2/3),  # 상단 꼭짓점
            (-size/2, height * 1/3),  # 좌하단
            (size/2, height * 1/3)   # 우하단
        ]
        
        # 회전 적용
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
    
    def draw_hexagon(self, draw, center, size, color, fill=True):
        """육각형 그리기"""
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
    
    def draw_octagon(self, draw, center, size, color, fill=True):
        """팔각형 그리기"""
        points = []
        for i in range(8):
            angle = math.radians(45 * i)
            x = center[0] + size * math.cos(angle)
            y = center[1] + size * math.sin(angle)
            points.append((x, y))
        
        if fill:
            draw.polygon(points, fill=color)
        else:
            draw.polygon(points, outline=color, width=5)
    
    def draw_star(self, draw, center, outer_radius, inner_radius, points_count, color, rotation=0):
        """별 모양 그리기"""
        points = []
        for i in range(points_count * 2):
            angle = math.radians(360 / (points_count * 2) * i + rotation)
            if i % 2 == 0:
                radius = outer_radius
            else:
                radius = inner_radius
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            points.append((x, y))
        
        draw.polygon(points, fill=color)
    
    def draw_diamond(self, draw, center, width, height, color, fill=True):
        """다이아몬드 모양 그리기"""
        points = [
            (center[0], center[1] - height//2),  # 상단
            (center[0] + width//2, center[1]),   # 우측
            (center[0], center[1] + height//2),  # 하단
            (center[0] - width//2, center[1])    # 좌측
        ]
        
        if fill:
            draw.polygon(points, fill=color)
        else:
            draw.polygon(points, outline=color, width=5)
    
    def draw_cross(self, draw, center, size, thickness, color):
        """십자가 모양 그리기"""
        # 세로 막대
        draw.rectangle([center[0] - thickness//2, center[1] - size//2,
                       center[0] + thickness//2, center[1] + size//2], fill=color)
        # 가로 막대
        draw.rectangle([center[0] - size//2, center[1] - thickness//2,
                       center[0] + size//2, center[1] + thickness//2], fill=color)
    
    def draw_plus(self, draw, center, size, thickness, color, rotation=0):
        """플러스 기호 그리기"""
        if rotation == 0:
            self.draw_cross(draw, center, size, thickness, color)
        else:
            # 45도 회전된 플러스 (X 모양)
            half_size = size // 2
            thickness_half = thickness // 2
            
            # 대각선 1
            points1 = [
                (center[0] - half_size, center[1] - half_size - thickness_half),
                (center[0] - half_size + thickness, center[1] - half_size + thickness_half),
                (center[0] + half_size, center[1] + half_size + thickness_half),
                (center[0] + half_size - thickness, center[1] + half_size - thickness_half)
            ]
            draw.polygon(points1, fill=color)
            
            # 대각선 2
            points2 = [
                (center[0] + half_size, center[1] - half_size - thickness_half),
                (center[0] + half_size - thickness, center[1] - half_size + thickness_half),
                (center[0] - half_size, center[1] + half_size + thickness_half),
                (center[0] - half_size + thickness, center[1] + half_size - thickness_half)
            ]
            draw.polygon(points2, fill=color)
    
    def draw_ring(self, draw, center, outer_radius, inner_radius, color):
        """링(도넛) 모양 그리기"""
        # 외부 원
        self.draw_circle(draw, center, outer_radius, color)
        # 내부 원을 배경색으로 그려서 구멍 만들기
        self.draw_circle(draw, center, inner_radius, self.background_color)
    
    def draw_semicircle(self, draw, center, radius, color, orientation='top'):
        """반원 그리기"""
        bbox = [center[0] - radius, center[1] - radius,
                center[0] + radius, center[1] + radius]
        
        if orientation == 'top':
            draw.pieslice(bbox, start=180, end=360, fill=color)
        elif orientation == 'bottom':
            draw.pieslice(bbox, start=0, end=180, fill=color)
        elif orientation == 'left':
            draw.pieslice(bbox, start=90, end=270, fill=color)
        elif orientation == 'right':
            draw.pieslice(bbox, start=270, end=450, fill=color)
    
    def draw_heart(self, draw, center, size, color):
        """하트 모양 그리기 (간단한 버전)"""
        # 두 개의 원과 삼각형으로 하트 표현
        circle_radius = size // 4
        # 왼쪽 원
        self.draw_circle(draw, (center[0] - circle_radius, center[1] - circle_radius), circle_radius, color)
        # 오른쪽 원
        self.draw_circle(draw, (center[0] + circle_radius, center[1] - circle_radius), circle_radius, color)
        # 아래 삼각형
        points = [
            (center[0] - size//2, center[1]),
            (center[0] + size//2, center[1]),
            (center[0], center[1] + size//2)
        ]
        draw.polygon(points, fill=color)
    
    def draw_arrow(self, draw, center, size, direction, color):
        """화살표 그리기"""
        if direction == 'up':
            rotation = 0
        elif direction == 'right':
            rotation = 90
        elif direction == 'down':
            rotation = 180
        else:  # left
            rotation = 270
        
        # 화살표 몸통
        body_width = size // 3
        body_height = size * 2 // 3
        
        # 화살표 머리
        head_width = size * 2 // 3
        head_height = size // 3
        
        # 간단히 삼각형으로 화살표 표현
        self.draw_triangle(draw, center, size, color, rotation=rotation)
    
    def draw_polygon(self, draw, center, radius, sides, color, rotation=0, fill=True):
        """다각형 그리기"""
        points = []
        for i in range(sides):
            angle = math.radians(360 / sides * i + rotation)
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            points.append((x, y))
        
        if fill:
            draw.polygon(points, fill=color)
        else:
            draw.polygon(points, outline=color, width=5)
    
    # 기존 패턴들은 그대로 유지...
    def pattern_centered_circle(self, draw, colors):
        """패턴 1: 중앙에 큰 원"""
        size = random.randint(300, 400)
        self.draw_circle(draw, (self.center, self.center), size, colors[0])
        # 내부에 작은 원
        self.draw_circle(draw, (self.center, self.center), size//2, colors[1])
    
    def pattern_overlapping_circles(self, draw, colors):
        """패턴 2: 겹치는 원들"""
        radius = random.randint(150, 200)
        offset = radius // 2
        # 세 개의 원을 삼각형 배치
        centers = [
            (self.center, self.center - offset),
            (self.center - offset, self.center + offset//2),
            (self.center + offset, self.center + offset//2)
        ]
        for i, center in enumerate(centers):
            self.draw_circle(draw, center, radius, colors[i % len(colors)])
    
    def pattern_square_with_circle(self, draw, colors):
        """패턴 3: 사각형과 원의 조합"""
        square_size = random.randint(350, 450)
        rotation = random.choice([0, 45])
        self.draw_square(draw, (self.center, self.center), square_size, colors[0], rotation)
        # 내부에 원
        circle_radius = square_size // 3
        self.draw_circle(draw, (self.center, self.center), circle_radius, colors[1])
    
    def pattern_triangle_composition(self, draw, colors):
        """패턴 4: 삼각형 구성"""
        size = random.randint(300, 400)
        # 큰 삼각형
        self.draw_triangle(draw, (self.center, self.center), size, colors[0])
        # 내부에 반대 방향 삼각형
        self.draw_triangle(draw, (self.center, self.center), size//2, colors[1], rotation=180)
    
    def pattern_geometric_mix(self, draw, colors):
        """패턴 5: 기하학적 혼합"""
        # 배경 원
        self.draw_circle(draw, (self.center, self.center), 350, colors[0])
        # 중앙 사각형
        self.draw_square(draw, (self.center, self.center), 250, colors[1], rotation=45)
        # 가장 안쪽 삼각형
        self.draw_triangle(draw, (self.center, self.center), 150, colors[2])
    
    def pattern_concentric_shapes(self, draw, colors):
        """패턴 6: 동심원 도형들"""
        sizes = [400, 300, 200, 100]
        shapes = [self.draw_circle, self.draw_square, self.draw_circle, self.draw_square]
        for i, (size, shape) in enumerate(zip(sizes, shapes)):
            color = colors[i % len(colors)]
            if shape == self.draw_square:
                shape(draw, (self.center, self.center), size, color, rotation=45*i)
            else:
                shape(draw, (self.center, self.center), size, color)
    
    def pattern_diagonal_squares(self, draw, colors):
        """패턴 7: 대각선 사각형들"""
        base_size = random.randint(200, 250)
        positions = [
            (self.center - 150, self.center - 150),
            (self.center + 150, self.center + 150),
            (self.center - 150, self.center + 150),
            (self.center + 150, self.center - 150)
        ]
        for i, pos in enumerate(positions):
            self.draw_square(draw, pos, base_size, colors[i % len(colors)], rotation=45)
        # 중앙에 큰 사각형
        self.draw_square(draw, (self.center, self.center), base_size * 1.5, colors[0])
    
    def pattern_hexagon_center(self, draw, colors):
        """패턴 8: 육각형 중심"""
        # 외부 육각형
        self.draw_hexagon(draw, (self.center, self.center), 300, colors[0])
        # 내부 원
        self.draw_circle(draw, (self.center, self.center), 200, colors[1])
        # 가장 안쪽 육각형
        self.draw_hexagon(draw, (self.center, self.center), 100, colors[2])
    
    def pattern_star_shape(self, draw, colors):
        """패턴 9: 별 모양"""
        # 배경 원
        self.draw_circle(draw, (self.center, self.center), 400, colors[0])
        # 별
        self.draw_star(draw, (self.center, self.center), 250, 100, 5, colors[1], rotation=-90)
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 80, colors[2])
    
    def pattern_abstract_combination(self, draw, colors):
        """패턴 10: 추상적 조합"""
        # 랜덤한 회전각
        angle = random.randint(0, 360)
        # 여러 도형을 겹쳐서 배치
        self.draw_triangle(draw, (self.center, self.center-50), 300, colors[0], rotation=angle)
        self.draw_square(draw, (self.center, self.center), 280, colors[1], rotation=angle+45)
        self.draw_circle(draw, (self.center, self.center+50), 150, colors[2])
    
    # 새로운 패턴들
    def pattern_octagon_layers(self, draw, colors):
        """패턴 11: 팔각형 레이어"""
        sizes = [350, 250, 150]
        for i, size in enumerate(sizes):
            self.draw_octagon(draw, (self.center, self.center), size, colors[i % len(colors)])
        # 중앙에 원
        self.draw_circle(draw, (self.center, self.center), 80, colors[0])
    
    def pattern_cross_design(self, draw, colors):
        """패턴 12: 십자가 디자인"""
        # 배경 원
        self.draw_circle(draw, (self.center, self.center), 400, colors[0])
        # 십자가
        self.draw_cross(draw, (self.center, self.center), 300, 80, colors[1])
        # 중앙 사각형
        self.draw_square(draw, (self.center, self.center), 100, colors[2], rotation=45)
    
    def pattern_diamond_cascade(self, draw, colors):
        """패턴 13: 다이아몬드 캐스케이드"""
        # 큰 다이아몬드
        self.draw_diamond(draw, (self.center, self.center), 400, 500, colors[0])
        # 중간 다이아몬드
        self.draw_diamond(draw, (self.center, self.center), 250, 350, colors[1])
        # 작은 원
        self.draw_circle(draw, (self.center, self.center), 100, colors[2])
    
    def pattern_heart_shape(self, draw, colors):
        """패턴 14: 하트 모양"""
        # 배경 원
        self.draw_circle(draw, (self.center, self.center), 400, colors[0])
        # 하트
        self.draw_heart(draw, (self.center, self.center), 250, colors[1])
        # 중앙 점
        self.draw_circle(draw, (self.center, self.center), 50, colors[2])
    
    def pattern_ellipse_composition(self, draw, colors):
        """패턴 15: 타원 구성"""
        # 수평 타원
        self.draw_ellipse(draw, (self.center, self.center), 400, 250, colors[0])
        # 수직 타원
        self.draw_ellipse(draw, (self.center, self.center), 250, 400, colors[1])
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 150, colors[2])
    
    def pattern_arrow_dynamic(self, draw, colors):
        """패턴 16: 화살표 다이나믹"""
        # 4방향 화살표
        directions = ['up', 'right', 'down', 'left']
        for i, direction in enumerate(directions):
            offset = 150
            if direction == 'up':
                pos = (self.center, self.center - offset)
            elif direction == 'right':
                pos = (self.center + offset, self.center)
            elif direction == 'down':
                pos = (self.center, self.center + offset)
            else:
                pos = (self.center - offset, self.center)
            self.draw_arrow(draw, pos, 150, direction, colors[i % len(colors)])
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 100, colors[0])
    
    def pattern_plus_symbol(self, draw, colors):
        """패턴 17: 플러스 심볼"""
        # 배경 사각형
        self.draw_square(draw, (self.center, self.center), 400, colors[0], rotation=45)
        # 플러스
        self.draw_plus(draw, (self.center, self.center), 300, 80, colors[1])
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 80, colors[2])
    
    def pattern_ring_layers(self, draw, colors):
        """패턴 18: 링 레이어"""
        # 여러 개의 링
        rings = [(400, 320), (300, 220), (200, 120)]
        for i, (outer, inner) in enumerate(rings):
            self.draw_ring(draw, (self.center, self.center), outer, inner, colors[i % len(colors)])
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 100, colors[0])
    
    def pattern_polygon_mix(self, draw, colors):
        """패턴 19: 다각형 믹스"""
        # 5각형
        self.draw_polygon(draw, (self.center, self.center), 350, 5, colors[0])
        # 7각형
        self.draw_polygon(draw, (self.center, self.center), 250, 7, colors[1], rotation=25)
        # 삼각형
        self.draw_triangle(draw, (self.center, self.center), 150, colors[2])
    
    def pattern_semicircle_design(self, draw, colors):
        """패턴 20: 반원 디자인"""
        # 4개의 반원을 조합
        radius = 300
        self.draw_semicircle(draw, (self.center, self.center - radius//4), radius, colors[0], 'top')
        self.draw_semicircle(draw, (self.center, self.center + radius//4), radius, colors[1], 'bottom')
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 150, colors[2])
    
    def pattern_grid_pattern(self, draw, colors):
        """패턴 21: 격자 패턴"""
        # 3x3 격자로 작은 도형 배치
        grid_size = 150
        shapes = [self.draw_circle, self.draw_square, self.draw_triangle]
        
        for i in range(3):
            for j in range(3):
                x = self.center + (i - 1) * grid_size
                y = self.center + (j - 1) * grid_size
                shape = shapes[(i + j) % 3]
                color = colors[(i + j) % len(colors)]
                
                if shape == self.draw_circle:
                    shape(draw, (x, y), 50, color)
                elif shape == self.draw_square:
                    shape(draw, (x, y), 80, color, rotation=45)
                else:
                    shape(draw, (x, y), 80, color)
    
    def pattern_spiral_arrangement(self, draw, colors):
        """패턴 22: 나선형 배치"""
        # 나선형으로 원 배치
        num_circles = 8
        for i in range(num_circles):
            angle = math.radians(i * 45)
            radius = 100 + i * 30
            x = self.center + radius * math.cos(angle)
            y = self.center + radius * math.sin(angle)
            circle_size = 80 - i * 8
            self.draw_circle(draw, (int(x), int(y)), circle_size, colors[i % len(colors)])
        
        # 중앙 별
        self.draw_star(draw, (self.center, self.center), 100, 40, 6, colors[0])
    
    def pattern_symmetrical_design(self, draw, colors):
        """패턴 23: 대칭 디자인"""
        # 4방향 대칭 패턴
        offset = 200
        positions = [
            (self.center, self.center - offset),
            (self.center + offset, self.center),
            (self.center, self.center + offset),
            (self.center - offset, self.center)
        ]
        
        for i, pos in enumerate(positions):
            self.draw_hexagon(draw, pos, 80, colors[i % len(colors)])
        
        # 대각선 위치
        diagonal_offset = int(offset * 0.7)
        diagonal_positions = [
            (self.center + diagonal_offset, self.center - diagonal_offset),
            (self.center + diagonal_offset, self.center + diagonal_offset),
            (self.center - diagonal_offset, self.center + diagonal_offset),
            (self.center - diagonal_offset, self.center - diagonal_offset)
        ]
        
        for i, pos in enumerate(diagonal_positions):
            self.draw_square(draw, pos, 60, colors[(i + 1) % len(colors)], rotation=45)
        
        # 중앙
        self.draw_octagon(draw, (self.center, self.center), 120, colors[0])
    
    def pattern_random_scatter(self, draw, colors):
        """패턴 24: 랜덤 산포"""
        # 랜덤한 위치에 다양한 도형 배치
        random.seed(42)  # 재현 가능한 랜덤
        
        # 큰 배경 도형
        self.draw_circle(draw, (self.center, self.center), 400, colors[0])
        
        # 랜덤 도형들
        shapes = [self.draw_circle, self.draw_square, self.draw_triangle, self.draw_hexagon]
        for i in range(12):
            shape = random.choice(shapes)
            x = self.center + random.randint(-200, 200)
            y = self.center + random.randint(-200, 200)
            size = random.randint(40, 80)
            color = colors[random.randint(1, len(colors)-1)]
            
            # 중앙에서 너무 멀면 스킵
            if math.sqrt((x - self.center)**2 + (y - self.center)**2) > 300:
                continue
            
            if shape == self.draw_circle:
                shape(draw, (x, y), size//2, color)
            elif shape == self.draw_square:
                shape(draw, (x, y), size, color, rotation=random.randint(0, 90))
            elif shape == self.draw_triangle:
                shape(draw, (x, y), size, color, rotation=random.randint(0, 360))
            else:
                shape(draw, (x, y), size//2, color)
    
    def pattern_flower_shape(self, draw, colors):
        """패턴 25: 꽃 모양"""
        # 꽃잎들
        petal_count = 6
        petal_radius = 120
        center_offset = 150
        
        for i in range(petal_count):
            angle = math.radians(i * 360 / petal_count)
            x = self.center + center_offset * math.cos(angle)
            y = self.center + center_offset * math.sin(angle)
            self.draw_circle(draw, (int(x), int(y)), petal_radius, colors[1])
        
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 150, colors[0])
        self.draw_circle(draw, (self.center, self.center), 80, colors[2])
    
    def pattern_shield_design(self, draw, colors):
        """패턴 26: 방패 디자인"""
        # 방패 모양 (간단히 표현)
        # 위쪽 사각형
        points = [
            (self.center - 200, self.center - 150),
            (self.center + 200, self.center - 150),
            (self.center + 200, self.center + 100),
            (self.center, self.center + 300),
            (self.center - 200, self.center + 100)
        ]
        draw.polygon(points, fill=colors[0])
        
        # 내부 장식
        self.draw_cross(draw, (self.center, self.center), 200, 60, colors[1])
        self.draw_circle(draw, (self.center, self.center), 60, colors[2])
    
    def pattern_letter_based(self, draw, colors):
        """패턴 27: 문자 기반 (추상적)"""
        # 'A' 모양을 추상적으로 표현
        # 두 개의 대각선 사각형
        self.draw_square(draw, (self.center - 100, self.center), 200, colors[0], rotation=30)
        self.draw_square(draw, (self.center + 100, self.center), 200, colors[0], rotation=-30)
        # 가로 막대
        draw.rectangle([self.center - 150, self.center - 20,
                       self.center + 150, self.center + 20], fill=colors[1])
        # 중앙 장식
        self.draw_circle(draw, (self.center, self.center), 50, colors[2])
    
    def pattern_wave_design(self, draw, colors):
        """패턴 28: 파도 디자인"""
        # 여러 개의 반원으로 파도 표현
        wave_count = 3
        for i in range(wave_count):
            y_offset = self.center + (i - 1) * 150
            radius = 200 - i * 30
            self.draw_semicircle(draw, (self.center, y_offset), radius, colors[i % len(colors)], 'top')
        
        # 중앙 장식
        self.draw_star(draw, (self.center, self.center), 100, 50, 8, colors[0])
    
    def pattern_gradient_circles(self, draw, colors):
        """패턴 29: 그라데이션 원"""
        # 크기가 점점 작아지는 원들
        circle_count = 6
        for i in range(circle_count):
            radius = 400 - i * 60
            # 색상 인덱스 순환
            color = colors[i % len(colors)]
            self.draw_circle(draw, (self.center, self.center), radius, color)
        
        # 중앙 별
        self.draw_star(draw, (self.center, self.center), 80, 30, 6, self.background_color)
    
    def pattern_mosaic_style(self, draw, colors):
        """패턴 30: 모자이크 스타일"""
        # 여러 작은 도형들의 조합
        # 중앙 팔각형
        self.draw_octagon(draw, (self.center, self.center), 200, colors[0])
        
        # 주변 삼각형들
        triangle_positions = [
            (self.center, self.center - 250),
            (self.center + 250, self.center),
            (self.center, self.center + 250),
            (self.center - 250, self.center)
        ]
        
        for i, pos in enumerate(triangle_positions):
            rotation = i * 90
            self.draw_triangle(draw, pos, 100, colors[1], rotation=rotation)
        
        # 모서리 사각형들
        square_positions = [
            (self.center - 200, self.center - 200),
            (self.center + 200, self.center - 200),
            (self.center + 200, self.center + 200),
            (self.center - 200, self.center + 200)
        ]
        
        for pos in square_positions:
            self.draw_square(draw, pos, 80, colors[2], rotation=45)
        
        # 중앙 원
        self.draw_circle(draw, (self.center, self.center), 80, colors[1])
    
    def generate_logo(self, output_path=None, pattern_index=None):
        """
        로고 생성
        :param output_path: 저장할 파일 경로 (None이면 Image 객체만 반환)
        :param pattern_index: 특정 패턴 지정 (None이면 랜덤)
        :return: PIL Image 객체
        """
        # 새 이미지 생성
        img = Image.new('RGB', (self.size, self.size), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # 색상 팔레트 선택
        colors = self.get_random_color_palette()
        
        # 패턴 선택
        if pattern_index is not None and 0 <= pattern_index < len(self.patterns):
            pattern = self.patterns[pattern_index]
        else:
            pattern = random.choice(self.patterns)
        
        # 패턴 그리기
        pattern(draw, colors)
        
        # 파일로 저장
        if output_path:
            img.save(output_path, 'PNG')
        
        return img
def update_progress(message):
    """진행 상황 메시지를 콘솔에 출력합니다."""
    print(message)
    sys.stdout.flush()

def get_app_name(app_name=None, selected_folder=None):
    """앱 이름을 폴더명으로부터 가져옵니다."""
    if app_name:
        return app_name
    if not selected_folder:
        return ""
    folder_name = os.path.basename(selected_folder)
    # Mac에서 한글 자소 분리 현상(NFD)을 정상적인 한글(NFC)로 변환
    folder_name = unicodedata.normalize('NFC', folder_name)
    return folder_name

def get_db_count(selected_folder):
    """폴더 내의 db 파일 개수를 셉니다."""
    assets_folder = os.path.join(selected_folder, "assets")
    if not os.path.exists(assets_folder):
        update_progress(f"DB 개수 확인: 'assets' 폴더를 찾을 수 없습니다: {assets_folder}")
        return 0
    try:
        db_files = [f for f in os.listdir(assets_folder)
                    if os.path.isfile(os.path.join(assets_folder, f)) and re.match(r'^question\d+\.db$', f)]
        return len(db_files)
    except Exception as e:
        update_progress(f"DB 파일 개수 확인 중 오류: {e}")
        return 0

def create_privacy_policy(selected_folder=None, app_name=None):
    """개인정보처리방침을 생성하고 블로그에 포스팅합니다."""
    global generated_privacy_policy_url
    update_progress("\n--- 개인정보처리방침 생성 시작 ---")
    app_name_val = get_app_name(app_name=app_name, selected_folder=selected_folder)
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    template = f"""
<p>This privacy policy applies to the {app_name_val} app (hereby referred to as "Application") for mobile devices that was created by Jongmin KIM (hereby referred to as "Service Provider") as a Free service. This service is intended for use "AS IS".</p>
<p><strong>Information Collection and Use</strong></p>
<p>The Application does not collect any personally identifiable information. All data, such as quiz results and study notes, is stored locally on your device and is not transmitted to the Service Provider or any third parties.</p>
<p>The Application uses Google AdMob for advertising, which may collect non-personally identifiable information to serve ads. For more information, please review Google's Privacy Policy.</p>
<p><strong>Third Party Access</strong></p>
<p>The Application utilizes third-party services that have their own Privacy Policy. Below is the link to the Privacy Policy of the third-party service provider used by the Application:<br>
<a href="https://www.google.com/policies/privacy/">Google Play Services & AdMob</a></p>
<p><strong>Opt-Out Rights</strong></p>
<p>You can stop all collection of information by the Application easily by uninstalling it.</p>
<p><strong>Children's Privacy</strong></p>
<p>The Application does not address anyone under the age of 13. The Service Provider does not knowingly collect personally identifiable information from children under 13.</p>
<p><strong>Security</strong></p>
<p>All user data is stored on the device, ensuring that your information remains private and secure.</p>
<p><strong>Changes</strong></p>
<p>This Privacy Policy may be updated from time to time. You are advised to consult this Privacy Policy regularly for any changes.</p>
<p>This privacy policy is effective as of {today}</p>
<p><strong>Contact Us</strong></p>
<p>If you have any questions regarding privacy while using the Application, please contact the Service Provider via email at bombezzang100@gmail.com.</p>
"""
    policy_text = template
    title = f"{app_name_val} - 기출문제 Privacy and Policy"
    hashtags = f"{app_name_val},privacy,policy"
    try:
        response = blog_posting(BLOG_ID, title, policy_text, hashtags, draft=False)
        if response and 'url' in response:
            generated_privacy_policy_url = response['url']
            update_progress("✅ 개인정보처리방침 포스트가 블로그에 업데이트 되었습니다: " + generated_privacy_policy_url)
        else:
            update_progress("⚠️ 개인정보처리방침 포스트 생성에 실패하였습니다.")
            generated_privacy_policy_url = "https://grea.site/2024/10/07/%EC%95%B1-%EC%A7%80%EC%9B%90-%EC%A0%95%EB%B3%B4/" # Fallback URL
    except Exception as e:
        update_progress(f"⚠️ 개인정보처리방침 생성 중 오류 발생: {e}")
        generated_privacy_policy_url = "https://grea.site/2024/10/07/%EC%95%B1-%EC%A7%80%EC%9B%90-%EC%A0%95%EB%B3%B4/" # Fallback URL


def save_config(selected_folder, bundle_id_val, app_name_val):
    """앱 설정을 app_config.json 파일로 저장합니다."""
    update_progress("\n--- app_config.json 생성 시작 ---")
    user_input_id = bundle_id_val
    project_folder = os.path.join(selected_folder, user_input_id)
    # 실제 bundle ID는 com.example.{bundle_id} 형식
    full_bundle_id = f"com.example.{user_input_id}"
    ios_folder = os.path.join(project_folder, "ios")
    if not os.path.exists(ios_folder):
        update_progress(f"⚠️ 오류: iOS 폴더를 찾을 수 없습니다: {ios_folder}")
        return

    config_json_path = os.path.join(ios_folder, "app_config.json")
    pubspec_path = os.path.join(project_folder, "pubspec.yaml")
    
    # pubspec.yaml에서 버전 정보 읽기
    version_str, build_number_str = "1.0.0", "1"
    if os.path.exists(pubspec_path):
        try:
            with open(pubspec_path, "r", encoding="utf-8") as f:
                pubspec_data = yaml.safe_load(f)
                version_line = pubspec_data.get('version', '1.0.0+1')
                version_str, build_number_str = version_line.split('+')
        except Exception as e:
            update_progress(f"⚠️ pubspec.yaml에서 버전 정보 읽기 실패: {e}")
    else:
        update_progress(f"경고: pubspec.yaml 파일이 없습니다: {pubspec_path}")

    db_count = get_db_count(project_folder) # 프로젝트 폴더 내의 assets 폴더 기준

    description_template = (
        f"""{app_name_val} 자격증 합격? 이 앱 하나면 끝!

* 주요 기능*
- 최신 기출문제 {db_count}세트!
- 연도별, 과목별 기출문제 풀기
- 기출문제 음성듣기
- 랜덤 문제 풀기
- 모든 문제 해설 제공
- 오답노트: 틀린 문제만 자동 저장
- 즐겨찾기 기능: 내가 찜한 문제를 다시 복습
- Wifi, 인터넷 없이도 사용 가능
- 완전 무료

지하철 및 이동중에도 , 언제 어디서나 간편하게 기출문제를 풀고, 실력을 완성하세요. 합격에 필요한 모든 것!
이 앱만 있으면 {app_name_val} 자격증을 손에 넣을 수 있습니다.
"""
    )
    
    config = {
        "bundle_id": full_bundle_id,
        "app_name": f"{app_name_val}-기출문제,음성듣기,해설강의",
        "version": version_str,
        "build_number": build_number_str,
        "description": description_template,
        "privacy_url": generated_privacy_policy_url,
        "keywords": [
            f"{app_name_val}", f"{app_name_val} 기출문제", f"{app_name_val} 필기",
            f"{app_name_val} 자격증", f"{app_name_val} 해설", f"{app_name_val} 오답노트",
            "자격증", "기출문제"
        ],
        # ★★★★★ 수정된 부분 시작 ★★★★★
        "categories": ["EDUCATION", "PRODUCTIVITY"],
        # ★★★★★ 수정된 부분 끝 ★★★★★
        "screenshot_folder": os.path.join(selected_folder, "Screenshots"),
        "metadata": {
            "support_url": "https://grea.site/2024/10/07/%EC%95%B1-%EC%A7%80%EC%9B%90-%EC%A0%95%EB%B3%B4/",
            "marketing_url": "https://bangkokwalkerr.blogspot.com/",
            "copyright": f"{datetime.date.today().year} Jongmin Kim",
            "contact_name": "Jongmin KIM",
            "contact_phone": "+821020221026",
            "contact_email": "bombezzang100@gmail.com",
            "requires_login": False,
            "primary_language": "ko",
            # ★★★★★ 수정된 부분 시작 ★★★★★
            "third_party_content": False,
            "age_rating_declaration": {
                "violence_cartoon_or_fantasy": "NONE",
                "violence_realistic": "NONE",
                "violence_prolonged_graphic_or_sadistic": "NONE",
                "profanity_or_crude_humor": "NONE",
                "mature_or_suggestive_themes": "NONE",
                "horror_or_fear_themes": "NONE",
                "medical_or_treatment_information": "NONE",
                "alcohol_tobacco_or_drug_use_or_references": "NONE",
                "simulated_gambling": "NONE",
                "sexual_content_or_nudity": "NONE",
                "graphic_sexual_content_and_nudity": "NONE",
                "unrestricted_web_access": False,
                "gambling_and_contests": False
            },
            # ★★★★★ 수정된 부분 끝 ★★★★★
            "price": 0.0,
            "available_countries": 175,
            "personal_data_collected": False
        }
    }

    try:
        with open(config_json_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        update_progress(f"✅ Step 11: app_config.json 저장 완료 ({config_json_path})")
    except Exception as e:
        update_progress(f"⚠️ app_config.json 저장 오류: {e}")

def create_app(selected_folder=None, bundle_id=None, app_name=None):
    """Flutter 앱 생성을 시작하고 모든 단계를 조율하는 메인 함수."""
    update_progress(f"--- Flutter 프로젝트 생성 시작 ---")
    update_progress(f"선택된 폴더: {selected_folder}")
    update_progress(f"Bundle ID: {bundle_id}")
    update_progress(f"앱 이름: {app_name}")

    if not all([selected_folder, bundle_id, app_name]):
        update_progress("⚠️ 오류: 폴더, Bundle ID, 앱 이름이 모두 필요합니다!")
        return

    # --- Step 1: `flutter create` 실행 ---
    update_progress("\n--- Step 1: Flutter 프로젝트 생성 ---")
    command = f"flutter create --org com.example --project-name {bundle_id} ."
    project_path = os.path.join(selected_folder, bundle_id)
    os.makedirs(project_path, exist_ok=True)
    
    # Step 1에서 Flutter create 실행 후 ios 폴더 확인 추가
    try:
        process = subprocess.Popen(command, cwd=project_path, shell=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            update_progress(f"⚠️ 앱 생성 실패:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            return
        
        # iOS 폴더 생성 확인
        ios_path = os.path.join(project_path, "ios")
        if not os.path.exists(ios_path):
            update_progress("iOS 폴더가 생성되지 않았습니다. 다시 생성 시도...")
            subprocess.run(f"cd {project_path} && flutter create --platforms=ios .", 
                        shell=True, check=True)
        
        update_progress("✅ Step 1: Flutter 프로젝트 생성 완료")
    except Exception as e:
        update_progress(f"⚠️ 앱 생성 중 예외 발생: {e}")
        return

    # --- Step 2 ~ 11: 순차적 프로세스 실행 (의존성 순서에 맞게 재정렬) ---
    # 1. 기본 파일/폴더 준비
    update_lib(selected_folder, bundle_id, app_name)
    update_db_assets(selected_folder, bundle_id, app_name)
    
    # 2. constants.dart 업데이트 (lib, assets 폴더 모두 필요)
    update_date(selected_folder, bundle_id)
    update_category(selected_folder, bundle_id)
    
    # 3. 핵심 강의 파일 업데이트 (완성된 constants.dart 및 assets/output 필요)
    update_summary_files(selected_folder, bundle_id)
    
    # 4. 나머지 설정 진행
    copy_integration_tests(selected_folder, bundle_id)
    edit_pubspec(selected_folder, bundle_id, app_name)
    edit_info_plist(selected_folder, bundle_id, app_name)
    edit_podfile(selected_folder, bundle_id, app_name)
    edit_appname(selected_folder, bundle_id, app_name)
    edit_splash_screen(selected_folder, bundle_id, app_name)
    # ★★★★★ NEW FUNCTION CALL START ★★★★★
    add_imports_to_ox_quiz_page(selected_folder, bundle_id)
    # ★★★★★ NEW FUNCTION CALL END ★★★★★
    insert_logo(selected_folder, bundle_id)
    
    # 5. 최종 단계
    finalize_process(selected_folder, bundle_id, app_name)


def update_lib(selected_folder, bundle_id_val, app_name_val):
    """lib 폴더의 내용을 교체합니다."""
    update_progress("\n--- Step 2: lib 폴더 업데이트 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    lib_folder = os.path.join(project_folder, "lib")
    
    # 소스 폴더 경로 (하드코딩된 경로)
    source_folder = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/lib6"
    
    if not os.path.exists(source_folder):
        update_progress(f"⚠️ 소스 lib 폴더를 찾을 수 없습니다: {source_folder}")
        return

    try:
        if os.path.exists(lib_folder):
            shutil.rmtree(lib_folder)
        shutil.copytree(source_folder, lib_folder)
        update_progress("✅ Step 2: lib 폴더 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ lib 업데이트 오류: {e}")


def update_summary_files(selected_folder, bundle_id_val):
    """
    constants.dart, 2.txt를 기반으로 summary_lectureX.dart 파일들과
    summary_select.dart를 동적으로 생성 및 업데이트합니다.
    """
    update_progress("\n--- Step 2.5: 핵심강의 파일(Summary Lectures) 업데이트 시작 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    lib_folder = os.path.join(project_folder, "lib")
    output_folder = os.path.join(project_folder, "assets", "output")
    constants_path = os.path.join(lib_folder, "constants.dart")

    if not os.path.exists(constants_path):
        update_progress(f"⚠️ '핵심강의 업데이트' 건너뛰기: constants.dart 파일을 찾을 수 없습니다: {constants_path}")
        return
    if not os.path.exists(output_folder):
        update_progress(f"⚠️ '핵심강의 업데이트' 건너뛰기: output 폴더를 찾을 수 없습니다: {output_folder}")
        return

    try:
        update_progress(f"1. '{constants_path}'에서 카테고리 정보 읽기...")
        with open(constants_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        categories_match = re.search(r'final List<String> categories = \[(.*?)\];', content, re.DOTALL)
        if not categories_match:
            update_progress("⚠️ '핵심강의 업데이트' 건너뛰기: constants.dart에서 'categories' 목록을 찾을 수 없습니다.")
            return

        categories_str = categories_match.group(1).strip()
        categories = re.findall(r"['\"]([^'\"]+)['\"]", categories_str)
        
        # ★★★★★ 수정된 부분 시작 ★★★★★
        # 오디오 생성 스크립트(4_StudyNote.py)와의 정렬 순서를 맞추기 위해
        # 카테고리 리스트를 알파벳 순으로 정렬합니다.
        categories.sort()
        update_progress(f"   - 발견된 카테고리 (정렬됨): {categories}")
        # ★★★★★ 수정된 부분 끝 ★★★★★

        if not categories:
            update_progress("⚠️ 카테고리가 비어있어 업데이트를 진행할 수 없습니다.")
            return

        update_progress("2. 카테고리별 summary_lectureX.dart 파일 생성...")
        lecture1_path = os.path.join(lib_folder, "summary_lecture1.dart")
        if not os.path.exists(lecture1_path):
            update_progress(f"⚠️ '핵심강의 업데이트' 건너뛰기: 템플릿 파일(summary_lecture1.dart)이 없습니다.")
            return

        with open(lecture1_path, 'r', encoding='utf-8') as f:
            lecture1_content = f.read()

        for i, category in enumerate(categories, 1):
            if i == 1: 
                continue 
            
            new_lecture_path = os.path.join(lib_folder, f"summary_lecture{i}.dart")
            new_content = lecture1_content.replace("SummaryLecture1Page", f"SummaryLecture{i}Page")
            new_content = re.sub(r"lecture1\.mp3", f"lecture{i}.mp3", new_content)
            with open(new_lecture_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            update_progress(f"   - '{os.path.basename(new_lecture_path)}' 생성 완료.")

        update_progress("3. 각 강의 파일에 studyNotes 내용 업데이트...")
        for i, category in enumerate(categories, 1):
            lecture_path = os.path.join(lib_folder, f"summary_lecture{i}.dart")
            txt_path = os.path.join(output_folder, category, "2.txt")

            if not os.path.exists(txt_path):
                update_progress(f"   - 경고: '{txt_path}' 파일이 없어 '{os.path.basename(lecture_path)}' 업데이트를 건너뜁니다.")
                continue
            
            update_progress(f"   - '{os.path.basename(txt_path)}' 파일 읽는 중...")
            with open(txt_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()

            dart_map_code = parse_txt_to_dart(txt_content)
            
            with open(lecture_path, 'r', encoding='utf-8') as f:
                lecture_content = f.read()

            updated_lecture_content = re.sub(
                r'final Map<String, Map<String, dynamic>> studyNotes = \{.*?\};',
                dart_map_code,
                lecture_content,
                flags=re.DOTALL
            )
            
            with open(lecture_path, 'w', encoding='utf-8') as f:
                f.write(updated_lecture_content)
            update_progress(f"   - ✅ '{os.path.basename(lecture_path)}' 업데이트 완료.")

        update_progress("4. summary_select.dart 파일 업데이트...")
        summary_select_path = os.path.join(lib_folder, "summary_select.dart")
        if os.path.exists(summary_select_path):
            import_statements = "\n".join([f"import 'summary_lecture{i}.dart';" for i in range(1, len(categories) + 1)])
            
            nav_logic = ""
            for i, category in enumerate(categories, 1):
                nav_logic += f"""
    {'else ' if i > 1 else ''}if (category == '{category}') {{
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => SummaryLecture{i}Page(dbPath: 'assets/your_database.db'),
        ),
      );
    }}"""
            
            full_nav_function = f"""void _navigateToSummaryPage(String category) {{
    {nav_logic.strip()}
  }}"""

            with open(summary_select_path, 'r', encoding='utf-8') as f:
                select_content = f.read()
            
            last_import_match = list(re.finditer(r"^(import .*?;\n)", select_content, re.MULTILINE))
            if last_import_match:
                insert_pos = last_import_match[-1].end()
                select_content = select_content[:insert_pos] + import_statements + '\n' + select_content[insert_pos:]
                update_progress("   - Import 구문 추가 완료.")
            else:
                update_progress("   - 경고: summary_select.dart에서 import 위치를 찾지 못했습니다.")

            if "_navigateToSummaryPage" in select_content:
                select_content = re.sub(
                    r"void _navigateToSummaryPage\(String category\)\s*\{[\s\S]*?\}",
                    full_nav_function,
                    select_content,
                    flags=re.DOTALL
                )
                update_progress("   - 네비게이션(_navigateToSummaryPage) 로직 업데이트 완료.")
            else:
                 update_progress("   - 경고: _navigateToSummaryPage 함수를 찾지 못해 업데이트하지 못했습니다.")

            with open(summary_select_path, 'w', encoding='utf-8') as f:
                f.write(select_content)
            update_progress(f"   - ✅ '{os.path.basename(summary_select_path)}' 파일 저장 완료.")

        update_progress("✅ Step 2.5: 핵심강의 파일 업데이트 완료")

    except Exception as e:
        update_progress(f"⚠️ 핵심강의 파일 업데이트 중 심각한 오류 발생: {e}")
        import traceback
        update_progress(traceback.format_exc())

def parse_txt_to_dart(txt_content):
    """2.txt 파일 내용을 파싱하여 Dart 맵 코드로 변환하는 헬퍼 함수"""
    dart_code = "final Map<String, Map<String, dynamic>> studyNotes = {\n"
    topics = txt_content.strip().split('---')

    for topic in topics:
        topic = topic.strip()
        if not topic:
            continue

        lines = topic.split('\n')
        title_line = lines[0].strip()
        
        if not re.match(r'^\d+\.', title_line):
            continue

        description_lines = []
        related_questions = []
        is_question_section = False

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            if "관련 문제:" in line:
                is_question_section = True
                continue

            if is_question_section:
                # 날짜 및 ID 파싱 로직 수정
                date_match = re.search(r'(\d{4})년\s*(\d{1,2})월', line)
                if date_match:
                    year, month = date_match.groups()
                    # Dart 코드와 일관된 형식으로 날짜 생성 ('2022년 4월')
                    date_for_dart = f"{year}년 {int(month)}월"
                    ids_match = re.search(r'Question_id:\s*([\d,\s]+)', line)
                    if ids_match:
                        question_ids = [int(q_id.strip()) for q_id in ids_match.group(1).split(',')]
                        for q_id in question_ids:
                           related_questions.append(f"      {{'date': '{date_for_dart}', 'question_id': {q_id}}},\n")
            else:
                description_lines.append(line.replace("'''", "'' '")) # Dart의 삼중 따옴표 오류 방지

        escaped_title = json.dumps(title_line, ensure_ascii=False)
        description_text = '\n'.join(description_lines)
        
        dart_code += f"  {escaped_title}: {{\n"
        dart_code += f"    'description':\n        '''{description_text}''',\n"
        dart_code += "    'related_questions': [\n"
        
        unique_questions = sorted(list(set(related_questions)))
        dart_code += "".join(unique_questions)
        
        dart_code += "    ],\n"
        dart_code += "  },\n"

    dart_code += "};"
    return dart_code


def copy_integration_tests(selected_folder, bundle_id_val):
    """
    integration_test, test_driver 폴더 및 관련 스크립트를 복사하고,
    Dart 테스트 파일 내의 프로젝트 패키지명만 선택적으로 수정합니다.
    """
    project_folder = os.path.join(selected_folder, bundle_id_val)
    update_progress("\n--- Step 3: 테스트 폴더 및 스크립트 복사 ---")

    def ignore_patterns(path, names):
        return {'mini_integration'}

    try:
        source_test_driver = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/test_driver"
        dst_test_driver = os.path.join(project_folder, "test_driver")
        if os.path.exists(dst_test_driver):
            shutil.rmtree(dst_test_driver)
        shutil.copytree(source_test_driver, dst_test_driver)
        update_progress("test_driver 폴더 복사 완료.")
    except Exception as e:
        update_progress(f"⚠️ test_driver 폴더 복사 오류: {e}")

    try:
        source_integration = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/integration_test"
        dst_integration = os.path.join(project_folder, "integration_test")
        if os.path.exists(dst_integration):
            shutil.rmtree(dst_integration)
        shutil.copytree(source_integration, dst_integration, ignore=ignore_patterns, dirs_exist_ok=True)
        update_progress("integration_test 폴더 복사 완료.")

        ignore_package_names = ['flutter', 'provider', 'flutter_test', 'integration_test']

        for test_file_name in ["main_test.dart", "my_app_test.dart"]:
            test_file_path = os.path.join(dst_integration, test_file_name)
            if os.path.exists(test_file_path):
                try:
                    with open(test_file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    new_lines = []
                    content_changed = False
                    
                    for line in lines:
                        match = re.search(r"import\s+['\"]package:([^/]+)/", line)
                        
                        if match:
                            package_name = match.group(1)
                            if package_name not in ignore_package_names:
                                new_line = re.sub(r"package:[^/]+", f"package:{bundle_id_val}", line)
                                new_lines.append(new_line)
                                if new_line != line:
                                    content_changed = True
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                    
                    if content_changed:
                        with open(test_file_path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                        update_progress(f"{test_file_name}의 패키지명 수정 완료.")
                except Exception as e:
                    update_progress(f"⚠️ {test_file_name} 수정 오류: {e}")
    except Exception as e:
        update_progress(f"⚠️ integration_test 폴더 복사/수정 오류: {e}")

    try:
        source_script = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/run_screenshots.sh"
        dst_script = os.path.join(project_folder, "run_screenshots.sh")
        if os.path.exists(source_script):
            shutil.copy(source_script, dst_script)
            update_progress("run_screenshots.sh 스크립트 복사 완료.")
        else:
            update_progress(f"⚠️ run_screenshots.sh 소스 파일을 찾을 수 없습니다: {source_script}")
    except Exception as e:
        update_progress(f"⚠️ run_screenshots.sh 복사 오류: {e}")



def update_db_assets(selected_folder, bundle_id_val, app_name_val):
    """assets 폴더로 DB 및 기타 에셋 폴더들을 복사합니다."""
    update_progress("\n--- Step 4: DB 및 Asset 파일 복사 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    flutter_assets_folder = os.path.join(project_folder, "assets")
    os.makedirs(flutter_assets_folder, exist_ok=True)
    
    source_assets_folder = os.path.join(selected_folder, "assets")
    if not os.path.exists(source_assets_folder):
        update_progress(f"⚠️ 원본 assets 폴더를 찾을 수 없습니다: {source_assets_folder}")
        return

    try:
        db_copied_count = 0
        for f in os.listdir(source_assets_folder):
            if f.lower().endswith(".db"):
                shutil.copy2(os.path.join(source_assets_folder, f), os.path.join(flutter_assets_folder, f))
                db_copied_count += 1
        if db_copied_count > 0:
            update_progress(f"DB 파일 {db_copied_count}개 복사 완료.")

        def _copy_directory_if_exists(src_parent, dst_parent, folder_name):
            source_path = os.path.join(src_parent, folder_name)
            dest_path = os.path.join(dst_parent, folder_name)
            if os.path.exists(source_path):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
                update_progress(f"✅ '{folder_name}' 폴더 복사 완료.")
            else:
                update_progress(f"ℹ️ '{folder_name}' 소스 폴더가 없어 복사를 건너뜁니다: {source_path}")

        _copy_directory_if_exists(source_assets_folder, flutter_assets_folder, "audio")
        _copy_directory_if_exists(source_assets_folder, flutter_assets_folder, "audio_output")
        _copy_directory_if_exists(source_assets_folder, flutter_assets_folder, "output")

        update_progress("✅ Step 4: DB 및 Asset 파일 복사 완료")
    except Exception as e:
        update_progress(f"⚠️ 파일 복사 오류: {e}")

def edit_pubspec(selected_folder, bundle_id_val, app_name_val):
    """pubspec.yaml 파일을 수정합니다."""
    update_progress("\n--- Step 5: pubspec.yaml 파일 수정 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    pubspec_path = os.path.join(project_folder, "pubspec.yaml")

    if not os.path.exists(pubspec_path):
        update_progress(f"⚠️ pubspec.yaml 파일을 찾을 수 없습니다: {pubspec_path}")
        return

    try:
        with open(pubspec_path, "r", encoding="utf-8") as f:
            pubspec = yaml.safe_load(f)
    except Exception as e:
        update_progress(f"⚠️ pubspec.yaml 읽기 오류: {e}")
        return
    
    pubspec['name'] = bundle_id_val
    pubspec['version'] = "8.8.0+10"
    
    pubspec['dependencies'].update({
        'fluttertoast': '^8.2.8', 'sqflite': '^2.4.0', 'shared_preferences': '^2.3.2',
        'google_mobile_ads': '^6.0.0', 'path': '^1.8.0', 'in_app_purchase': '^3.2.1',
        'provider': '^6.1.2', 'fl_chart': '^0.70.2', 'url_launcher': '^6.3.1',
        'just_audio': '^0.9.46', 'in_app_review': '^2.0.10', 'app_tracking_transparency': '^2.0.4',
        'audioplayers': '^6.4.0', 'table_calendar': '^3.2.0', 'intl': '^0.20.0',
        'vector_math': '^2.1.4','flutter_html': '^3.0.0', 'font_awesome_flutter': '^10.8.0', 
        'gma_mediation_ironsource': '^1.5.0', 'gma_mediation_applovin': '^2.3.2', 
        'gma_mediation_unity': '^1.6.0', 
    })

    if 'dev_dependencies' not in pubspec or pubspec['dev_dependencies'] is None:
        pubspec['dev_dependencies'] = {}
        
    pubspec['dev_dependencies'].update({
        'flutter_launcher_icons': '^0.13.1',
        'integration_test': {
            'sdk': 'flutter'
        }
    })
    
    pubspec['flutter_launcher_icons'] = {
        'android': True, 'ios': True,
        'image_path': "assets/splash_logo.png", 'min_sdk_android': 21
    }
    
    assets_list = []
    db_count = get_db_count(project_folder) 
    for i in range(1, db_count + 1):
        assets_list.append(f"assets/question{i}.db")
    
    assets_list.extend([
        "assets/splash_logo.png", 
        "assets/quiz.db", 
        "assets/audio/",
        "assets/output/",
        "assets/audio/summary/",
        "assets/dictionary.db", 


    ])

    for i in range(1, 8):
        assets_list.append(f"assets/audio/question{i}/")

    if 'flutter' not in pubspec or pubspec['flutter'] is None:
        pubspec['flutter'] = {}
    pubspec['flutter']['assets'] = sorted(list(set(assets_list)))
    
    try:
        with open(pubspec_path, "w", encoding="utf-8") as f:
            yaml.dump(pubspec, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        update_progress("✅ Step 5: pubspec.yaml 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ pubspec.yaml 업데이트 오류: {e}")

def update_date(selected_folder, bundle_id_val):
    """DB 파일의 날짜 정보를 기반으로 constants.dart를 업데이트합니다."""
    update_progress("\n--- Step 6: constants.dart 날짜 정보 업데이트 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    assets_folder = os.path.join(project_folder, "assets")
    
    db_files = [f for f in os.listdir(assets_folder) if re.match(r'^question\d+\.db$', f)]
    if not db_files:
        update_progress("⚠️ assets 폴더에 questionX.db 파일이 없습니다.")
        return

    entries = []
    for file in db_files:
        db_path = os.path.join(assets_folder, file)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Date_information FROM questions WHERE Date_information IS NOT NULL AND Date_information != '' LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월', str(row[0]))
                if match:
                    year, month = match.groups()
                    date_key = f"{year}년 {int(month)}월"
                    order_num = int(re.search(r'(\d+)', file).group(1))
                    entries.append((order_num, date_key))
        except Exception as e:
            update_progress(f"⚠️ {file} 에서 날짜 정보 읽기 실패: {e}")

    if not entries:
        update_progress("⚠️ DB 파일에서 유효한 날짜를 추출할 수 없었습니다.")
        return

    entries.sort(key=lambda x: x[0])
    reverseRoundMapping = {order: date_key for order, (num, date_key) in enumerate(entries, 1)}
    
    reverseRoundMapping_str = "final Map<int, String> reverseRoundMapping = {\n" + \
                              "\n".join([f"  {k}: '{v}'," for k, v in reverseRoundMapping.items()]) + \
                              "\n};"
    
    examSessionToRoundName_str = """
String examSessionToRoundName(dynamic examVal) {
  int? intVal = (examVal is int) ? examVal : int.tryParse(examVal.toString());
  return reverseRoundMapping[intVal] ?? '기타';
}
"""
    color_definitions_str = """import 'package:flutter/material.dart';

const Color primaryColor = Color(0xFF4A90E2);
const Color secondaryColor = Color(0xFF8E9AAF);
const Color favoriteColor = Color(0xFFEC4899);

Color getPrimaryColor(bool isDarkMode) {
  return isDarkMode ? Color(0xFF8E9AAF) : Color(0xFF4A90E2);
}
"""

    constants_content = f"{color_definitions_str}\n{reverseRoundMapping_str}\n\n{examSessionToRoundName_str}"
    constants_path = os.path.join(project_folder, "lib", "constants.dart")
    try:
        with open(constants_path, "w", encoding="utf-8") as f:
            f.write(constants_content)
        update_progress("✅ Step 6: constants.dart 날짜 정보 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ constants.dart 업데이트 중 오류 발생: {e}")

def update_category(selected_folder, bundle_id_val):
    """question1.db에서 카테고리 정보를 읽어 constants.dart에 추가합니다."""
    update_progress("\n--- Step 7: constants.dart 카테고리 정보 업데이트 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    assets_folder = os.path.join(project_folder, "assets")
    question_db_path = os.path.join(assets_folder, "question1.db")
    if not os.path.exists(question_db_path):
        update_progress(f"⚠️ 오류: question1.db 파일이 없습니다: {question_db_path}")
        return

    try:
        conn = sqlite3.connect(question_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Category FROM questions ORDER BY Question_id")
        
        seen = set()
        categories = []
        for row in cursor.fetchall():
            category = row[0]
            if category and category not in seen:
                seen.add(category)
                categories.append(category)
                
        conn.close()
    except Exception as e:
        update_progress(f"⚠️ DB 조회 오류: {e}")
        return

    if categories:
        categories_str = "final List<String> categories = [\n" + ",\n".join([f"  '{cat}'" for cat in categories]) + "\n];"
        constants_path = os.path.join(project_folder, "lib", "constants.dart")
        try:
            with open(constants_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + categories_str)
            update_progress("✅ Step 7: constants.dart 카테고리 정보 업데이트 완료")
        except Exception as e:
            update_progress(f"⚠️ constants.dart 업데이트 중 오류 발생: {e}")

def edit_info_plist(selected_folder, bundle_id_val, app_name_val):
    """Info.plist 파일을 수정합니다."""
    print("\n--- Step 8: Info.plist 파일 수정 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    info_plist_path = os.path.join(project_folder, "ios", "Runner", "Info.plist")
    
    if not os.path.exists(info_plist_path):
        print(f"⚠️ 오류: Info.plist 파일을 찾을 수 없습니다: {info_plist_path}")
        return

    try:
        with open(info_plist_path, "rb") as f:
            plist_data = plistlib.load(f)

        # 수정될 SKAdNetworkItems 목록 (기존 88개 + 추가 65개 = 총 153개)
        skadnetwork_items = [
            # 기존 항목들 (88개)
            {"SKAdNetworkIdentifier": "22mmun2rn5.skadnetwork"}, {"SKAdNetworkIdentifier": "238da6jt44.skadnetwork"},
            {"SKAdNetworkIdentifier": "294l99pt4k.skadnetwork"}, {"SKAdNetworkIdentifier": "2fnua5tdw4.skadnetwork"},
            {"SKAdNetworkIdentifier": "2u9pt9hc89.skadnetwork"}, {"SKAdNetworkIdentifier": "32z4fx6l9h.skadnetwork"},
            {"SKAdNetworkIdentifier": "3qy4746246.skadnetwork"}, {"SKAdNetworkIdentifier": "3rd42ekr43.skadnetwork"},
            {"SKAdNetworkIdentifier": "3sh42y64q3.skadnetwork"}, {"SKAdNetworkIdentifier": "424m5254lk.skadnetwork"},
            {"SKAdNetworkIdentifier": "4468km3ulz.skadnetwork"}, {"SKAdNetworkIdentifier": "44jx6755aq.skadnetwork"},
            {"SKAdNetworkIdentifier": "488r3q3dtq.skadnetwork"}, {"SKAdNetworkIdentifier": "4dzt52r2t5.skadnetwork"},
            {"SKAdNetworkIdentifier": "4fzdc2evr5.skadnetwork"}, {"SKAdNetworkIdentifier": "4pfyvq9l8r.skadnetwork"},
            {"SKAdNetworkIdentifier": "4w7y6s5ca2.skadnetwork"}, {"SKAdNetworkIdentifier": "578prtvx9j.skadnetwork"},
            {"SKAdNetworkIdentifier": "5a6flpkh64.skadnetwork"}, {"SKAdNetworkIdentifier": "5f5u5tfb26.skadnetwork"},
            {"SKAdNetworkIdentifier": "5l3tpt7t6e.skadnetwork"}, {"SKAdNetworkIdentifier": "5lm9lj6jb7.skadnetwork"},
            {"SKAdNetworkIdentifier": "5tjdwbrq8w.skadnetwork"}, {"SKAdNetworkIdentifier": "6yxyv74ff7.skadnetwork"},
            {"SKAdNetworkIdentifier": "7ug5zh24hu.skadnetwork"}, {"SKAdNetworkIdentifier": "8s468mfl3y.skadnetwork"},
            {"SKAdNetworkIdentifier": "97r2b46745.skadnetwork"}, {"SKAdNetworkIdentifier": "9nlqeag3gk.skadnetwork"},
            {"SKAdNetworkIdentifier": "9rd848q2bz.skadnetwork"}, {"SKAdNetworkIdentifier": "9t245vhmpl.skadnetwork"},
            {"SKAdNetworkIdentifier": "a2p9lx4jpn.skadnetwork"}, {"SKAdNetworkIdentifier": "a8cz6cu7e5.skadnetwork"},
            {"SKAdNetworkIdentifier": "av6w8kgt66.skadnetwork"}, {"SKAdNetworkIdentifier": "bvpn9ufa9b.skadnetwork"},
            {"SKAdNetworkIdentifier": "c6k4g5qg8m.skadnetwork"}, {"SKAdNetworkIdentifier": "cstr6suwn9.skadnetwork"},
            {"SKAdNetworkIdentifier": "e5fvkxwrpn.skadnetwork"}, {"SKAdNetworkIdentifier": "f38h382jlk.skadnetwork"},
            {"SKAdNetworkIdentifier": "f73kdq92p3.skadnetwork"}, {"SKAdNetworkIdentifier": "f7s53z58qe.skadnetwork"},
            {"SKAdNetworkIdentifier": "feyaarzu9v.skadnetwork"}, {"SKAdNetworkIdentifier": "g6gcrrvk4p.skadnetwork"},
            {"SKAdNetworkIdentifier": "glqzh8vgby.skadnetwork"}, {"SKAdNetworkIdentifier": "hs6bdukanm.skadnetwork"},
            {"SKAdNetworkIdentifier": "k674qkevps.skadnetwork"}, {"SKAdNetworkIdentifier": "k6y4y55b64.skadnetwork"},
            {"SKAdNetworkIdentifier": "kbd757ywx3.skadnetwork"}, {"SKAdNetworkIdentifier": "klf5c3l5u5.skadnetwork"},
            {"SKAdNetworkIdentifier": "lr83yxwka7.skadnetwork"}, {"SKAdNetworkIdentifier": "m8dbw4sv7c.skadnetwork"},
            {"SKAdNetworkIdentifier": "mj797d8u6f.skadnetwork"}, {"SKAdNetworkIdentifier": "mlmmfzh3r3.skadnetwork"},
            {"SKAdNetworkIdentifier": "mp6xlyr22a.skadnetwork"}, {"SKAdNetworkIdentifier": "mqn7fxpca7.skadnetwork"},
            {"SKAdNetworkIdentifier": "n9x2a789qt.skadnetwork"}, {"SKAdNetworkIdentifier": "p78axxw29g.skadnetwork"},
            {"SKAdNetworkIdentifier": "ppxm28t8ap.skadnetwork"}, {"SKAdNetworkIdentifier": "prcb7njmu6.skadnetwork"},
            {"SKAdNetworkIdentifier": "pwa73g5rt2.skadnetwork"}, {"SKAdNetworkIdentifier": "s39g8k73mm.skadnetwork"},
            {"SKAdNetworkIdentifier": "t38b2kh725.skadnetwork"}, {"SKAdNetworkIdentifier": "tl55sbb4fm.skadnetwork"},
            {"SKAdNetworkIdentifier": "uw77j35x4d.skadnetwork"}, {"SKAdNetworkIdentifier": "v72qych5uu.skadnetwork"},
            {"SKAdNetworkIdentifier": "v79kvwwj4g.skadnetwork"}, {"SKAdNetworkIdentifier": "v9wttpbfk9.skadnetwork"},
            {"SKAdNetworkIdentifier": "vhf287vqwu.skadnetwork"}, {"SKAdNetworkIdentifier": "w9q455wk68.skadnetwork"},
            {"SKAdNetworkIdentifier": "wg4vff78zm.skadnetwork"}, {"SKAdNetworkIdentifier": "wzmmz9fp6w.skadnetwork"},
            {"SKAdNetworkIdentifier": "x44k69ngh6.skadnetwork"}, {"SKAdNetworkIdentifier": "xga6mpmplv.skadnetwork"},
            {"SKAdNetworkIdentifier": "yclnxrl5pm.skadnetwork"}, {"SKAdNetworkIdentifier": "ydx93a7ass.skadnetwork"},
            {"SKAdNetworkIdentifier": "zmvfpc5aq8.skadnetwork"}, {"SKAdNetworkIdentifier": "zq492l623r.skadnetwork"},
            {"SKAdNetworkIdentifier": "ludvb6z3bs.skadnetwork"}, {"SKAdNetworkIdentifier": "cp8zw746q7.skadnetwork"},
            {"SKAdNetworkIdentifier": "v4nxqhlyqp.skadnetwork"}, {"SKAdNetworkIdentifier": "su67r6k2v3.skadnetwork"},
            {"SKAdNetworkIdentifier": "gta9lk7p23.skadnetwork"}, {"SKAdNetworkIdentifier": "vutu7akeur.skadnetwork"},
            {"SKAdNetworkIdentifier": "y5ghdn5j9k.skadnetwork"}, {"SKAdNetworkIdentifier": "n38lu8286q.skadnetwork"},
            {"SKAdNetworkIdentifier": "47vhws6wlr.skadnetwork"}, {"SKAdNetworkIdentifier": "kbmxgpxpgc.skadnetwork"},
            {"SKAdNetworkIdentifier": "c3frkrj4fj.skadnetwork"}, {"SKAdNetworkIdentifier": "8c4e2ghe7u.skadnetwork"},
            {"SKAdNetworkIdentifier": "3qcr597p9d.skadnetwork"}, {"SKAdNetworkIdentifier": "dbu4b84rxf.skadnetwork"},
            
            # 추가 항목들 (65개)
            {"SKAdNetworkIdentifier": "24t9a8vw3c.skadnetwork"}, {"SKAdNetworkIdentifier": "24zw6aqk47.skadnetwork"},
            {"SKAdNetworkIdentifier": "252b5q8x7y.skadnetwork"}, {"SKAdNetworkIdentifier": "275upjj5gd.skadnetwork"},
            {"SKAdNetworkIdentifier": "3l6bd9hu43.skadnetwork"}, {"SKAdNetworkIdentifier": "44n7hlldy6.skadnetwork"},
            {"SKAdNetworkIdentifier": "4mn522wn87.skadnetwork"}, {"SKAdNetworkIdentifier": "523jb4fst2.skadnetwork"},
            {"SKAdNetworkIdentifier": "52fl2v3hgk.skadnetwork"}, {"SKAdNetworkIdentifier": "54nzkqm89y.skadnetwork"},
            {"SKAdNetworkIdentifier": "6964rsfnh4.skadnetwork"}, {"SKAdNetworkIdentifier": "6g9af3uyq4.skadnetwork"},
            {"SKAdNetworkIdentifier": "6p4ks3rnbw.skadnetwork"}, {"SKAdNetworkIdentifier": "6v7lgmsu45.skadnetwork"},
            {"SKAdNetworkIdentifier": "6xzpu9s2p8.skadnetwork"}, {"SKAdNetworkIdentifier": "737z793b9f.skadnetwork"},
            {"SKAdNetworkIdentifier": "74b6s63p6l.skadnetwork"}, {"SKAdNetworkIdentifier": "79pbpufp6p.skadnetwork"},
            {"SKAdNetworkIdentifier": "7fmhfwg9en.skadnetwork"}, {"SKAdNetworkIdentifier": "7rz58n8ntl.skadnetwork"},
            {"SKAdNetworkIdentifier": "84993kbrcf.skadnetwork"}, {"SKAdNetworkIdentifier": "89z7zv988g.skadnetwork"},
            {"SKAdNetworkIdentifier": "8m87ys6875.skadnetwork"}, {"SKAdNetworkIdentifier": "8r8llnkz5a.skadnetwork"},
            {"SKAdNetworkIdentifier": "9b89h5y424.skadnetwork"}, {"SKAdNetworkIdentifier": "9vvzujtq5s.skadnetwork"},
            {"SKAdNetworkIdentifier": "9yg77x724h.skadnetwork"}, {"SKAdNetworkIdentifier": "a7xqa6mtl2.skadnetwork"},
            {"SKAdNetworkIdentifier": "b9bk5wbcq9.skadnetwork"}, {"SKAdNetworkIdentifier": "bxvub5ada5.skadnetwork"},
            {"SKAdNetworkIdentifier": "cg4yq2srnc.skadnetwork"}, {"SKAdNetworkIdentifier": "cj5566h2ga.skadnetwork"},
            {"SKAdNetworkIdentifier": "cs644xg564.skadnetwork"}, {"SKAdNetworkIdentifier": "dkc879ngq3.skadnetwork"},
            {"SKAdNetworkIdentifier": "dzg6xy7pwj.skadnetwork"}, {"SKAdNetworkIdentifier": "ecpz2srf59.skadnetwork"},
            {"SKAdNetworkIdentifier": "eh6m2bh4zr.skadnetwork"}, {"SKAdNetworkIdentifier": "ejvt5qm6ak.skadnetwork"},
            {"SKAdNetworkIdentifier": "g28c52eehv.skadnetwork"}, {"SKAdNetworkIdentifier": "g2y4y55b64.skadnetwork"},
            {"SKAdNetworkIdentifier": "ggvn48r87g.skadnetwork"}, {"SKAdNetworkIdentifier": "gta8lk7p23.skadnetwork"},
            {"SKAdNetworkIdentifier": "hb56zgv37p.skadnetwork"}, {"SKAdNetworkIdentifier": "hdw39hrw9y.skadnetwork"},
            {"SKAdNetworkIdentifier": "krvm3zuq6h.skadnetwork"}, {"SKAdNetworkIdentifier": "m297p6643m.skadnetwork"},
            {"SKAdNetworkIdentifier": "m5mvw97r93.skadnetwork"}, {"SKAdNetworkIdentifier": "mls7yz5dvl.skadnetwork"},
            {"SKAdNetworkIdentifier": "mtkv5xtk9e.skadnetwork"}, {"SKAdNetworkIdentifier": "n66cz3y3bx.skadnetwork"},
            {"SKAdNetworkIdentifier": "n6fk4nfna4.skadnetwork"}, {"SKAdNetworkIdentifier": "nzq8sh4pbs.skadnetwork"},
            {"SKAdNetworkIdentifier": "pwdxu55a5a.skadnetwork"}, {"SKAdNetworkIdentifier": "qqp299437r.skadnetwork"},
            {"SKAdNetworkIdentifier": "qu637u8glc.skadnetwork"}, {"SKAdNetworkIdentifier": "r45fhb6rf7.skadnetwork"},
            {"SKAdNetworkIdentifier": "rvh3l7un93.skadnetwork"}, {"SKAdNetworkIdentifier": "rx5hdcabgc.skadnetwork"},
            {"SKAdNetworkIdentifier": "s69wq72ugq.skadnetwork"}, {"SKAdNetworkIdentifier": "u679fj5vs4.skadnetwork"},
            {"SKAdNetworkIdentifier": "vcra2ehyfk.skadnetwork"}, {"SKAdNetworkIdentifier": "x5l83yy675.skadnetwork"},
            {"SKAdNetworkIdentifier": "x8jxxk4ff5.skadnetwork"}, {"SKAdNetworkIdentifier": "x8uqf25wch.skadnetwork"},
            {"SKAdNetworkIdentifier": "xy9t38ct57.skadnetwork"}, {"SKAdNetworkIdentifier": "y45688jllp.skadnetwork"}
        ]
        
        # plist 파일에 업데이트할 내용
        plist_data.update({
            "CFBundleDisplayName": app_name_val,
            "CFBundleName": bundle_id_val,
            "GADApplicationIdentifier": "ca-app-pub-2598779635969436~4262650072",
            "NSMicrophoneUsageDescription": "이 앱은 오디오 재생 기능만 사용하며, 마이크는 사용하지 않습니다. 이 설명은 외부 라이브러리의 요구 사항을 준수하기 위해 추가되었습니다.",
            "NSUserTrackingUsageDescription": "관심 없는 광고를 보지않기 위해 '허용'을 눌러주세요. '허용'을 눌러도 개인정보가 유출되지 않으니 안심하세요",
            "SKAdNetworkItems": skadnetwork_items,  # 업데이트된 SKAdNetworkItems 목록
        })

        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist_data, f)
        print("✅ Step 8: Info.plist 업데이트 완료")
    except Exception as e:
        print(f"⚠️ Info.plist 수정 중 오류 발생: {e}")


def edit_podfile(selected_folder, bundle_id_val, app_name_val):
    """Podfile을 수정합니다."""
    print("\n--- Step 9: Podfile 파일 수정 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    podfile_path = os.path.join(project_folder, "ios", "Podfile")

    # 디버깅: 실제 경로와 파일 존재 여부 확인
    print(f"프로젝트 폴더: {project_folder}")
    print(f"Podfile 경로: {podfile_path}")
    print(f"ios 폴더 존재 여부: {os.path.exists(os.path.join(project_folder, 'ios'))}")
    
    # ios 폴더 내용 확인
    ios_folder = os.path.join(project_folder, "ios")
    if os.path.exists(ios_folder):
        print(f"ios 폴더 내용: {os.listdir(ios_folder)}")
    
    # Podfile이 없으면 생성
    if not os.path.exists(podfile_path):
        print(f"Podfile이 없습니다. 새로 생성합니다...")
        
        # ios 폴더가 없으면 생성
        os.makedirs(ios_folder, exist_ok=True)
        
        # Flutter 프로젝트에 iOS 플랫폼 추가 시도
        try:
            print("Flutter iOS 플랫폼 생성 중...")
            subprocess.run(
                f"cd {project_folder} && flutter create --platforms=ios .",
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            print("Flutter iOS 플랫폼 생성 완료")
        except subprocess.CalledProcessError as e:
            print(f"Flutter iOS 생성 실패: {e}")
            print(f"stderr: {e.stderr}")
    
    # 다시 Podfile 존재 확인
    if not os.path.exists(podfile_path):
        print(f"⚠️ 여전히 Podfile이 없습니다. 기본 Podfile을 생성합니다.")
        # 기본 Podfile 직접 생성
        os.makedirs(ios_folder, exist_ok=True)

    # 이하 기존 코드와 동일...
    new_podfile_content = r"""# Uncomment this line to define a global platform for your project
platform :ios, '15.0'

# CocoaPods analytics sends network stats synchronously affecting flutter build latency.
ENV['COCOAPODS_DISABLE_STATS'] = 'true'

project 'Runner', {
  'Debug' => :debug,
  'Profile' => :release,
  'Release' => :release,
}

def flutter_root
  generated_xcode_build_settings_path = File.expand_path(File.join('..', 'Flutter', 'Generated.xcconfig'), __FILE__)
  unless File.exist?(generated_xcode_build_settings_path)
    raise "#{generated_xcode_build_settings_path} must exist. If you're running pod install manually, make sure flutter pub get is executed first"
  end

  File.foreach(generated_xcode_build_settings_path) do |line|
    matches = line.match(/FLUTTER_ROOT\=(.*)/)
    return matches[1].strip if matches
  end
  raise "FLUTTER_ROOT not found in #{generated_xcode_build_settings_path}. Try deleting Generated.xcconfig, then run flutter pub get"
end

require File.expand_path(File.join('packages', 'flutter_tools', 'bin', 'podhelper'), flutter_root)

flutter_ios_podfile_setup

target 'Runner' do
  use_frameworks!
  use_modular_headers!

  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))
  
  # Unity Ads 미디에이션 어댑터 추가
  pod 'GoogleMobileAdsMediationUnity', '~> 4.16.0.0'
  pod 'UnityAds'
  target 'RunnerTests' do
    inherit! :search_paths
  end
end

post_install do |installer|
  installer.pods_project.targets.each do |target|
    flutter_additional_ios_build_settings(target)
    
    # iOS 12 최소 버전 설정
    target.build_configurations.each do |config|
      config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '15.0'
    end
  end
end
"""

    try:
        with open(podfile_path, 'w', encoding='utf-8') as f:
            f.write(new_podfile_content)
        print("✅ Step 9: Podfile 업데이트 완료")
    except Exception as e:
        print(f"⚠️ Podfile 수정 중 오류 발생: {e}")
        
def edit_appname(selected_folder, bundle_id_val, app_name_val):
    """Dart 파일 내의 앱 이름을 변경합니다."""
    update_progress("\n--- Step 9: Dart 파일 내 앱 이름 변경 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    home_dart_path = os.path.join(project_folder, "lib", "home.dart")
    if not os.path.exists(home_dart_path):
        update_progress(f"⚠️ home.dart 파일을 찾을 수 없어 건너뜁니다: {home_dart_path}")
        return

    try:
        with open(home_dart_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("'산업안전기사'", f"'{app_name_val}'")
        content = content.replace("'산업안전기사 기출문제'", f"'{app_name_val} 기출문제'")
        with open(home_dart_path, "w", encoding="utf-8") as f:
            f.write(content)
        update_progress("✅ Step 9: home.dart의 앱 이름 변경 완료")
    except Exception as e:
        update_progress(f"⚠️ home.dart 수정 중 오류 발생: {e}")

def edit_splash_screen(selected_folder, bundle_id_val, app_name_val):
    """splash_screen.dart 파일의 앱 이름을 변경합니다."""
    update_progress("\n--- Step 9.5: 스플래시 화면 앱 이름 변경 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    splash_screen_path = os.path.join(project_folder, "lib", "splash_screen.dart")
    
    if not os.path.exists(splash_screen_path):
        update_progress(f"⚠️ splash_screen.dart 파일을 찾을 수 없어 건너뜁니다: {splash_screen_path}")
        return

    try:
        with open(splash_screen_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 정규식을 사용하여 "Text("...", ...)" 패턴을 찾고 내부 텍스트만 교체
        # 이렇게 하면 다른 Text 위젯에 영향을 주지 않고 목표 텍스트만 정확히 변경 가능
        content = re.sub(
            r'Text\(\s*"산업안전기사 기출문제",',
            f'Text(\n              "{app_name_val} 기출문제",',
            content
        )
        
        with open(splash_screen_path, "w", encoding="utf-8") as f:
            f.write(content)
        update_progress(f"✅ Step 9.5: splash_screen.dart의 앱 이름 변경 완료")
    except Exception as e:
        update_progress(f"⚠️ splash_screen.dart 수정 중 오류 발생: {e}")


# ★★★★★ NEW FUNCTION DEFINITION START ★★★★★
def add_imports_to_ox_quiz_page(selected_folder, bundle_id_val):
    """ox_quiz_page.dart 파일에 특정 import 구문을 추가합니다."""
    update_progress("\n--- Step 9.7: ox_quiz_page.dart import 구문 추가 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    ox_quiz_page_path = os.path.join(project_folder, "lib", "ox_quiz_page.dart")

    if not os.path.exists(ox_quiz_page_path):
        update_progress(f"⚠️ ox_quiz_page.dart 파일을 찾을 수 없어 건너뜁니다: {ox_quiz_page_path}")
        return

    imports_to_add_str = (
        f"\nimport 'package:{bundle_id_val}/widgets/common/common_header_widget.dart';"
        f"\nimport 'package:{bundle_id_val}/widgets/common/themed_background_widget.dart';"
    )

    try:
        with open(ox_quiz_page_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 이미 구문이 존재하는지 확인하여 중복 추가 방지
        if f"package:{bundle_id_val}/widgets/common/common_header_widget.dart" in content and \
           f"package:{bundle_id_val}/widgets/common/themed_background_widget.dart" in content:
            update_progress(f"ℹ️ ox_quiz_page.dart에 필요한 import 구문이 이미 존재합니다.")
            return

        # 마지막 import 문을 찾아 그 뒤에 삽입
        last_import_match = list(re.finditer(r"^(import .*?;\n)", content, re.MULTILINE))
        if last_import_match:
            insert_pos = last_import_match[-1].end() -1 # Get position before the newline
            new_content = content[:insert_pos] + imports_to_add_str + content[insert_pos:]
        else:
            # import문이 없는 경우 (매우 드문 경우), 파일 최상단에 추가
            new_content = imports_to_add_str.strip() + '\n\n' + content

        with open(ox_quiz_page_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        update_progress("✅ Step 9.7: ox_quiz_page.dart에 import 구문 추가 완료")

    except Exception as e:
        update_progress(f"⚠️ ox_quiz_page.dart 수정 중 오류 발생: {e}")
# ★★★★★ NEW FUNCTION DEFINITION END ★★★★★


def insert_logo(selected_folder, bundle_id_val):
    """
    로고를 자동으로 생성하고, Flutter 프로젝트에 복사한 후
    flutter_launcher_icons 도구를 실행하여 앱 아이콘을 생성합니다.
    """
    update_progress("\n--- Step 10: 로고 자동 생성 및 아이콘 생성 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    flutter_assets_folder = os.path.join(project_folder, "assets")
    
    # 소스 로고를 저장할 경로 (기존 경로와 동일)
    source_logo_path = os.path.join(selected_folder, "assets", "splash_logo.png")
    
    try:
        # assets 폴더가 없으면 생성
        os.makedirs(os.path.join(selected_folder, "assets"), exist_ok=True)
        
        # 로고 생성기 인스턴스 생성 (랜덤 배경색)
        update_progress("로고를 자동으로 생성하는 중...")
        generator = LogoGenerator()
        
        # 로고 생성 및 저장
        img = generator.generate_logo(source_logo_path)
        update_progress(f"✅ 로고 자동 생성 완료 (배경색: {generator.get_background_color_name()})")
        
        # 이미지가 1024x1024인지 확인 (LogoGenerator가 기본적으로 1024x1024로 생성하므로 이 부분은 안전장치)
        if img.size != (1024, 1024):
            update_progress(f"이미지 리사이즈 중... (원본: {img.size}) -> (1024, 1024)")
            img = img.resize((1024, 1024), Image.LANCZOS)
            img.save(source_logo_path)
            update_progress("✅ splash_logo.png 이미지 리사이즈 완료.")
        
    except Exception as e:
        update_progress(f"⚠️ 로고 생성 중 오류 발생: {e}")
        return

    try:
        os.makedirs(flutter_assets_folder, exist_ok=True)
        dest_logo_path = os.path.join(flutter_assets_folder, "splash_logo.png")
        shutil.copy2(source_logo_path, dest_logo_path)
        update_progress(f"✅ splash_logo.png를 Flutter 프로젝트의 assets 폴더로 복사했습니다.")
    except Exception as e:
        update_progress(f"⚠️ splash_logo.png 복사 중 오류 발생: {e}")
        return

    update_progress("`flutter pub run flutter_launcher_icons` 실행 중...")
    try:
        command = "flutter pub run flutter_launcher_icons:main"
        result = subprocess.run(
            command, 
            cwd=project_folder, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        update_progress("✅ Step 10: 로고 자동 생성 및 아이콘 생성 완료")
    except subprocess.CalledProcessError as e:
        update_progress(f"⚠️ 아이콘 생성 스크립트 실행 중 오류 발생:")
        update_progress(e.stderr)
    except Exception as e:
        update_progress(f"⚠️ insert_logo 작업 중 예측하지 못한 오류 발생: {e}")


def create_app_privacy_json(selected_folder, bundle_id_val):
    """App Privacy 상세 정보 JSON 파일을 생성합니다."""
    update_progress("\n--- App Privacy JSON 파일 생성 시작 ---")
    
    # 저장할 JSON 데이터 정의
    privacy_data = {
      "version": "1",
      "privacy_declarations": [
        {
          "privacy_types": [
            {
              "data_category": "IDENTIFIERS",
              "data_type": "DEVICE_ID",
              "is_linked": False,
              "is_tracked": True,
              "purposes": [
                "THIRD_PARTY_ADVERTISING"
              ]
            },
            {
              "data_category": "USAGE_DATA",
              "data_type": "ADVERTISING_DATA",
              "is_linked": False,
              "is_tracked": True,
              "purposes": [
                "THIRD_PARTY_ADVERTISING"
              ]
            }
          ]
        }
      ]
    }

    # 저장할 경로 설정
    project_folder = os.path.join(selected_folder, bundle_id_val)
    fastlane_folder = os.path.join(project_folder, "ios", "fastlane")
    
    try:
        # fastlane 폴더가 없으면 생성
        os.makedirs(fastlane_folder, exist_ok=True)
    except Exception as e:
        update_progress(f"⚠️ fastlane 폴더 생성 중 오류 발생: {e}")
        return

    # JSON 파일 저장
    file_path = os.path.join(fastlane_folder, "app_privacy_details.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(privacy_data, f, indent=2, ensure_ascii=False)
        update_progress(f"✅ App Privacy JSON 파일 생성 완료: {file_path}")
    except Exception as e:
        update_progress(f"⚠️ app_privacy_details.json 파일 저장 중 오류 발생: {e}")

def create_iap_package(selected_folder, bundle_id_val):
    """제공된 정보를 바탕으로 In-App Purchase(.itmsp) 패키지를 생성합니다."""
    update_progress("\n--- In-App Purchase 패키지 생성 시작 ---")

    # IAP 기본 정보 설정
    product_id = f"ad_remove_{bundle_id_val}"
    reference_name = "광고제거"
    price_tier = "8" # 8,800 KRW는 보통 Tier 8에 해당합니다. (App Store Connect에서 확인 필요)
    
    # 심사 정보 설정
    review_screenshot_path = "/Users/jongminkim/Desktop/Apps/qcjongmin/DbMachine3/FinalDbmachine/35/IMG_6568.PNG"
    review_notes = "본 앱은 비소모성 인앱 구매를 통해 '광고 제거' 기능을 제공합니다. 사용자가 '광고 제거 구매하기'를 선택하여 결제하면, 결제 완료 후 SharedPreferences에 구매 내역이 저장되고 전역 변수(adsRemovedGlobal)가 업데이트되어 앱 내 모든 광고(배너, 전면, 보상형 등)가 제거됩니다. 또한, '구매 복원하기' 기능을 통해 기기 변경이나 앱 재설치 후에도 구매 내역이 복원되어 광고 제거 상태가 유지됩니다. 심사 시, 제공된 샌드박스 테스터 계정을 사용하여 인앱 구매 및 복원 플로우를 테스트해 주시기 바랍니다. 구매 전후 UI에서 광고가 정상적으로 노출되거나 제거되는 것을 확인하실 수 있습니다."
    
    # .itmsp 패키지 경로 설정
    project_folder = os.path.join(selected_folder, bundle_id_val)
    iap_base_folder = os.path.join(project_folder, "in_app_purchases")
    itmsp_path = os.path.join(iap_base_folder, f"{product_id}.itmsp")

    try:
        os.makedirs(itmsp_path, exist_ok=True)
    except Exception as e:
        update_progress(f"⚠️ .itmsp 폴더 생성 중 오류: {e}")
        return

    # metadata.xml 내용 생성
    # 참고: Apple의 Team ID는 12_deliver.py 스크립트에서 가져왔습니다.
    metadata_xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="software5.10" xmlns="http://apple.com/itunes/importer">
    <provider>JongminKIM</provider>
    <team_id>CPHBF5XF4B</team_id>
    <software>
        <vendor_id>{bundle_id_val}</vendor_id>
        <software_metadata>
            <in_app_purchases>
                <in_app_purchase>
                    <product_id>{product_id}</product_id>
                    <reference_name>{reference_name}</reference_name>
                    <type>non-consumable</type>
                    <products>
                        <product>
                            <cleared_for_sale>true</cleared_for_sale>
                            <intervals>
                                <interval>
                                    <start_date>{datetime.date.today().strftime('%Y-%m-%d')}</start_date>
                                    <wholesale_price_tier>{price_tier}</wholesale_price_tier>
                                </interval>
                            </intervals>
                        </product>
                    </products>
                    <locales>
                        <locale name="ko-KR">
                            <title>광고 제거</title>
                            <description>1회 구매로 평생 광고제거 이용</description>
                        </locale>
                    </locales>
                    <review_notes>{review_notes}</review_notes>
                    <review_screenshot>
                        <file_name>review_screenshot.png</file_name>
                        <size>{os.path.getsize(review_screenshot_path)}</size>
                        <checksum type="md5">{subprocess.check_output(['md5', '-q', review_screenshot_path]).decode('utf-8').strip()}</checksum>
                    </review_screenshot>
                </in_app_purchase>
            </in_app_purchases>
        </software_metadata>
    </software>
</package>
"""
    
    # metadata.xml 파일 저장
    try:
        with open(os.path.join(itmsp_path, "metadata.xml"), "w", encoding="utf-8") as f:
            f.write(metadata_xml_content)
        update_progress("✅ metadata.xml 파일 생성 완료.")
    except Exception as e:
        update_progress(f"⚠️ metadata.xml 저장 오류: {e}")

    # 심사 스크린샷 복사
    try:
        if os.path.exists(review_screenshot_path):
            shutil.copy(review_screenshot_path, os.path.join(itmsp_path, "review_screenshot.png"))
            update_progress("✅ 심사 스크린샷 복사 완료.")
        else:
            update_progress(f"⚠️ 심사 스크린샷 원본 파일을 찾을 수 없습니다: {review_screenshot_path}")
    except Exception as e:
        update_progress(f"⚠️ 심사 스크린샷 복사 오류: {e}")
    
    update_progress("✅ In-App Purchase 패키지 생성 완료.")


def finalize_process(selected_folder, bundle_id_val, app_name_val):
    """모든 프로세스를 완료하고 최종 정리 작업을 수행합니다."""
    update_progress("\n--- 최종 정리 및 설정 단계 시작 ---")
    update_ad_remove(selected_folder, bundle_id_val)
    create_privacy_policy(selected_folder, app_name_val)
    create_app_privacy_json(selected_folder, bundle_id_val) # <--- 이 줄을 추가하세요.
    create_iap_package(selected_folder, bundle_id_val) # <--- 이 줄을 추가하세요.
    save_config(selected_folder, bundle_id_val, app_name_val)
    update_progress("\n==============================================")
    update_progress("✅ 모든 자동 생성 프로세스가 완료되었습니다! ✅")
    update_progress("==============================================")

def update_ad_remove(selected_folder, bundle_id_val):
    """ad_remove.dart 파일의 product ID를 bundle_id에 맞게 업데이트합니다."""
    project_folder = os.path.join(selected_folder, bundle_id_val)
    ad_remove_path = os.path.join(project_folder, "lib", "ad_remove.dart")
    
    if not os.path.exists(ad_remove_path):
        return

    try:
        with open(ad_remove_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"final\s+String\s+_adRemovalProductId\s*=\s*'.*?';", f"final String _adRemovalProductId = 'ad_remove_{bundle_id_val}';", content)
        content = re.sub(r"final\s+String\s+_supportProductId\s*=\s*'.*?';", f"final String _supportProductId = 'support_developer_{bundle_id_val}';", content)
        with open(ad_remove_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        update_progress(f"⚠️ ad_remove.dart 수정 중 오류: {e}")

# --- 블로그 포스팅 관련 함수들 ---
def get_blogger_service_obj():
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), TOKEN_FILE)
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                update_progress(f"토큰 갱신 실패: {e}, 인증 재시도")
                creds = run_oauth_flow()
        else:
            creds = run_oauth_flow()

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return discovery.build('blogger', 'v3', credentials=creds)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_oauth_flow():
    secret_path = os.path.join(os.path.dirname(__file__), 'client_secret.json')
    if not os.path.exists(secret_path):
        secret_path = CLIENT_SECRET

    flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
    creds = flow.run_local_server(port=PORT, server_class=ReusableTCPServer)
    return creds

def blog_posting(blog_id, title, content, hashtags, draft=False):
    update_progress("블로그 포스팅 시도...")
    blogger_service = get_blogger_service_obj()
    posts = blogger_service.posts()
    data = {'title': title, 'content': content, 'labels': hashtags.split(',') if hashtags else []}
    response = posts.insert(blogId=blog_id, body=data, isDraft=draft, fetchImages=True).execute()
    update_progress("블로그 포스팅 완료, ID: " + response['id'])
    return response

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("실행 방법: python 8_AutoAppV2.py <selected_folder> <bundle_id>")
        sys.exit(1)

    selected_folder_arg = sys.argv[1]
    bundle_id_arg = sys.argv[2]
    app_name_arg = get_app_name(selected_folder=selected_folder_arg)

    try:
        create_app(
            selected_folder=selected_folder_arg, 
            bundle_id=bundle_id_arg, 
            app_name=app_name_arg
        )
    except Exception as e:
        update_progress(f"\n\nFATAL ERROR: 스크립트 실행 중 치명적인 오류 발생\n{e}")
        import traceback
        update_progress(traceback.format_exc())