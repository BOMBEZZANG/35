import os
import sys
import json
import re

def _generate_nodes_code(node_data, colors):
    """재귀적으로 MindMapNode 생성 코드를 생성합니다."""
    
    node_counter = 0

    def generate_recursive(node, current_level, start_y):
        nonlocal node_counter
        
        # 1. 현재 노드의 기본 정보 설정
        node_height = 45.0 + float(len(node.get("title", "")) // 20 * 10)
        node_y = start_y + (node_height / 2.0)

        # 2. ID 및 스타일 정의
        node_counter += 1
        base_id = _sanitize_id(node.get("title", "unnamed"))
        node_id = f"{base_id}_{node_counter}"
        
        level_x_positions = [150, 400, 700, 1050]
        node_x = level_x_positions[min(current_level, len(level_x_positions) - 1)]
        color_index = (current_level + int(start_y / 100)) % len(colors)
        color = colors[color_index]
        width = min(160.0, max(100.0, float(len(node.get("title", "")) * 9 + 15)))
        
        children = node.get("children", [])
        is_expandable = "true" if children else "false"

        # 3. 자식들을 먼저 재귀적으로 처리하여 코드와 ID를 얻음
        child_ids = []
        child_codes_list = []
        children_block_height = 0
        y_padding = 0
        
        if children:
            y_padding = {0: 20, 1: 15, 2: 10, 3: 5}.get(current_level, 5)
            running_y_for_child = start_y + node_height + y_padding
            
            for child in children:
                child_codes, child_id, child_subtree_height = generate_recursive(
                    child, current_level + 1, running_y_for_child
                )
                child_codes_list.extend(child_codes)
                child_ids.append(child_id)
                
                height_with_padding = child_subtree_height + y_padding
                running_y_for_child += height_with_padding
                children_block_height += height_with_padding
                
            if children_block_height > 0:
                children_block_height -= y_padding

        # 4. 자식들의 코드가 모두 준비된 후, 부모 노드의 코드를 생성
        node_code = f'''
    final {node_id} = MindMapNode(
      id: '{node_id}',
      text: '{node.get("title", "")}',
      color: {color}[{200 + current_level * 100}]!,
      position: Offset({float(node_x)}, {float(node_y)}),
      width: {width},
      height: {float(node_height)},
      children: [{", ".join(child_ids)}],
      isExpandable: {is_expandable},
    );
    _nodes['{node_id}'] = {node_id};'''

        # 5. 코드 순서 수정: 자식 코드를 먼저, 그 다음 부모 코드를 추가
        all_codes = child_codes_list
        all_codes.append(node_code)
        
        # 6. 이 서브트리의 전체 높이 계산 및 반환
        total_height_of_this_subtree = node_height + (y_padding + children_block_height if children else 0)
        
        return all_codes, node_id, total_height_of_this_subtree

    # --- 재귀 함수 최초 호출 ---
    all_codes, root_id, _ = generate_recursive(node_data, 0, 100.0)
    
    # MindMapData 클래스의 루트 노드 설정
    all_codes.append(f"    _rootNode = _nodes['{root_id}']!;")

    return "\n".join(all_codes)


def _create_flutter_template(json_data):
    """Flutter 코드 템플릿 생성"""
    # 색상 팔레트
    colors = [
        "Colors.green", "Colors.orange", "Colors.purple", "Colors.teal",
        "Colors.indigo", "Colors.amber", "Colors.cyan", "Colors.pink",
        "Colors.red", "Colors.blue", "Colors.brown", "Colors.grey"
    ]

    # 노드 생성 코드 생성
    nodes_code = _generate_nodes_code(json_data["root"], colors)

    flutter_template = f'''import 'package:flutter/material.dart';
import 'dart:math' as math;

class MindMapApp extends StatelessWidget {{
  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: 'Mind Map',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: MindMapScreen(),
    );
  }}
}}

class MindMapScreen extends StatefulWidget {{
  @override
  _MindMapScreenState createState() => _MindMapScreenState();
}}

class _MindMapScreenState extends State<MindMapScreen> with TickerProviderStateMixin {{
  double _scale = 1.0;
  Offset _offset = Offset.zero;
  late MindMapData _mindMapData;
  late AnimationController _animationController;

  @override
  void initState() {{
    super.initState();
    _mindMapData = MindMapData();
    _animationController = AnimationController(
      duration: Duration(milliseconds: 300),
      vsync: this,
    );
  }}

  @override
  void dispose() {{
    _animationController.dispose();
    super.dispose();
  }}

  void _toggleNode(String nodeId) {{
    setState(() {{
      _mindMapData.toggleNode(nodeId);
    }});
    _animationController.forward(from: 0);
  }}

  bool _isPointInNode(Offset point, MindMapNode node) {{
    final nodeRect = Rect.fromCenter(
      center: node.position,
      width: node.width,
      height: node.height,
    );
    return nodeRect.contains(point);
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: Text('마인드맵'),
        backgroundColor: Colors.blue[600],
        actions: [
          IconButton(
            icon: Icon(Icons.zoom_in),
            onPressed: () {{
              setState(() {{
                _scale = (_scale * 1.2).clamp(0.05, 3.0);
              }});
            }},
          ),
          IconButton(
            icon: Icon(Icons.zoom_out),
            onPressed: () {{
              setState(() {{
                _scale = (_scale / 1.2).clamp(0.05, 3.0);
              }});
            }},
          ),
          IconButton(
            icon: Icon(Icons.center_focus_strong),
            onPressed: () {{
              setState(() {{
                _scale = 1.0;
                _offset = Offset.zero;
              }});
            }},
          ),
          IconButton(
            icon: Icon(Icons.unfold_more),
            onPressed: () {{
              setState(() {{
                _mindMapData.expandAll();
              }});
            }},
          ),
          IconButton(
            icon: Icon(Icons.unfold_less),
            onPressed: () {{
              setState(() {{
                _mindMapData.collapseAll();
              }});
            }},
          ),
        ],
      ),
      body: GestureDetector(
        onPanUpdate: (details) {{
          setState(() {{
            _offset += details.delta;
          }});
        }},
        onTapUp: (details) {{
          final adjustedPosition = Offset(
            (details.localPosition.dx - _offset.dx) / _scale,
            (details.localPosition.dy - _offset.dy) / _scale,
          );
          
          for (final node in _mindMapData.getVisibleNodes()) {{
            if (_isPointInNode(adjustedPosition, node)) {{
              if (node.children.isNotEmpty && node.isExpandable) {{
                _toggleNode(node.id);
              }}
              break;
            }}
          }}
        }},
        child: Container(
          width: double.infinity,
          height: double.infinity,
          color: Colors.grey[50],
          child: Transform(
            transform: Matrix4.identity()
              ..translate(_offset.dx, _offset.dy)
              ..scale(_scale),
            child: CustomPaint(
              painter: MindMapPainter(
                mindMapData: _mindMapData,
                onNodeTap: _toggleNode,
                animation: _animationController,
              ),
              size: Size.infinite,
            ),
          ),
        ),
      ),
    );
  }}
}}

class MindMapNode {{
  final String id;
  final String text;
  final Color color;
  final Offset position;
  final List<MindMapNode> children;
  final double width;
  final double height;
  bool isExpanded;
  final bool isExpandable;

  MindMapNode({{
    required this.id,
    required this.text,
    required this.color,
    required this.position,
    this.children = const [],
    this.width = 120,
    this.height = 40,
    this.isExpanded = true,
    this.isExpandable = true,
  }});
}}

class MindMapData {{
  late Map<String, MindMapNode> _nodes;
  late MindMapNode _rootNode;

  MindMapData() {{
    _initializeNodes();
  }}

  Map<String, MindMapNode> get nodes => _nodes;
  MindMapNode get rootNode => _rootNode;

  void toggleNode(String nodeId) {{
    if (_nodes.containsKey(nodeId) && _nodes[nodeId]!.isExpandable) {{
      _nodes[nodeId]!.isExpanded = !_nodes[nodeId]!.isExpanded;
    }}
  }}

  void expandAll() {{
    _nodes.values.forEach((node) {{
      if (node.isExpandable) {{
        node.isExpanded = true;
      }}
    }});
  }}

  void collapseAll() {{
    _nodes.values.forEach((node) {{
      if (node.isExpandable && node.id != 'root') {{
        node.isExpanded = false;
      }}
    }});
  }}

  List<MindMapNode> getVisibleNodes() {{
    List<MindMapNode> visibleNodes = [_rootNode];
    _addVisibleChildren(_rootNode, visibleNodes);
    return visibleNodes;
  }}

  void _addVisibleChildren(MindMapNode parent, List<MindMapNode> visibleNodes) {{
    if (parent.isExpanded) {{
      for (final child in parent.children) {{
        visibleNodes.add(child);
        _addVisibleChildren(child, visibleNodes);
      }}
    }}
  }}

  void _initializeNodes() {{
    _nodes = {{}};
    
{nodes_code}
  }}
}}

class MindMapPainter extends CustomPainter {{
  final MindMapData mindMapData;
  final Function(String) onNodeTap;
  final Animation<double> animation;

  MindMapPainter({{
    required this.mindMapData,
    required this.onNodeTap,
    required this.animation,
  }}) : super(repaint: animation);

  @override
  void paint(Canvas canvas, Size size) {{
    final paint = Paint()
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    final textPainter = TextPainter(
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.center,
    );

    final visibleNodes = mindMapData.getVisibleNodes();

    // 연결선 그리기
    _drawConnections(canvas, paint, visibleNodes);
    
    // 노드 그리기
    _drawNodes(canvas, textPainter, visibleNodes, size);
  }}

  void _drawConnections(Canvas canvas, Paint paint, List<MindMapNode> visibleNodes) {{
    paint.color = Colors.grey[400]!;
    paint.strokeWidth = 2.0;

    for (final node in visibleNodes) {{
      if (node.isExpanded) {{
        for (final child in node.children) {{
          if (visibleNodes.contains(child)) {{
            _drawCurvedLine(canvas, paint, node.position, child.position);
          }}
        }}
      }}
    }}
  }}

  void _drawCurvedLine(Canvas canvas, Paint paint, Offset start, Offset end) {{
    final path = Path();
    path.moveTo(start.dx, start.dy);
    
    final controlPoint1 = Offset(
      start.dx + (end.dx - start.dx) * 0.5,
      start.dy,
    );
    final controlPoint2 = Offset(
      start.dx + (end.dx - start.dx) * 0.5,
      end.dy,
    );
    
    path.cubicTo(
      controlPoint1.dx, controlPoint1.dy,
      controlPoint2.dx, controlPoint2.dy,
      end.dx, end.dy,
    );
    
    canvas.drawPath(path, paint);
  }}

  void _drawNodes(Canvas canvas, TextPainter textPainter, List<MindMapNode> visibleNodes, Size size) {{
    final paint = Paint()
      ..style = PaintingStyle.fill;

    for (final node in visibleNodes) {{
      _drawNode(canvas, textPainter, paint, node, size);
    }}
  }}

  void _drawNode(Canvas canvas, TextPainter textPainter, Paint paint, MindMapNode node, Size size) {{
    // 노드 배경 그리기
    paint.color = node.color;
    final rect = RRect.fromRectAndRadius(
      Rect.fromCenter(center: node.position, width: node.width, height: node.height),
      Radius.circular(20),
    );
    canvas.drawRRect(rect, paint);

    // 테두리 그리기
    paint.style = PaintingStyle.stroke;
    paint.color = node.color.withOpacity(0.8);
    paint.strokeWidth = 2;
    canvas.drawRRect(rect, paint);
    paint.style = PaintingStyle.fill;

    // 확장/축소 아이콘 그리기 (하위 노드가 있는 경우)
    if (node.children.isNotEmpty && node.isExpandable) {{
      _drawExpandIcon(canvas, paint, node);
    }}

    // 텍스트 그리기
    textPainter.text = TextSpan(
      text: node.text,
      style: TextStyle(
        color: Colors.black87,
        fontSize: node.text.length > 8 ? 11 : 12,
        fontWeight: FontWeight.w600,
      ),
    );
    textPainter.layout(maxWidth: node.width - 10);
    
    final textOffset = Offset(
      node.position.dx - textPainter.width / 2,
      node.position.dy - textPainter.height / 2,
    );
    textPainter.paint(canvas, textOffset);
  }}

  void _drawExpandIcon(Canvas canvas, Paint paint, MindMapNode node) {{
    paint.color = Colors.white;
    paint.style = PaintingStyle.fill;
    
    final iconSize = 16.0;
    final iconCenter = Offset(
      node.position.dx + node.width / 2 - iconSize / 2,
      node.position.dy - node.height / 2 + iconSize / 2,
    );
    
    canvas.drawCircle(iconCenter, iconSize / 2, paint);
    
    paint.color = Colors.grey[600]!;
    paint.style = PaintingStyle.stroke;
    paint.strokeWidth = 1;
    canvas.drawCircle(iconCenter, iconSize / 2, paint);
    
    paint.color = Colors.grey[700]!;
    paint.strokeWidth = 2;
    
    canvas.drawLine(
      Offset(iconCenter.dx - 4, iconCenter.dy),
      Offset(iconCenter.dx + 4, iconCenter.dy),
      paint,
    );
    
    if (!node.isExpanded) {{
      canvas.drawLine(
        Offset(iconCenter.dx, iconCenter.dy - 4),
        Offset(iconCenter.dx, iconCenter.dy + 4),
        paint,
      );
    }}
  }}

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}}
'''
    return flutter_template

def _generate_flutter_code(json_data, output_path):
    """JSON 데이터를 기반으로 Flutter 코드 생성"""
    try:
        # Flutter 코드 템플릿 생성
        flutter_code = _create_flutter_template(json_data)

        # Flutter 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(flutter_code)

    except Exception as e:
        raise Exception(f"Flutter 코드 생성 중 오류: {str(e)}")

def _sanitize_id(text):
    """텍스트를 Dart 변수명으로 사용 가능하도록 정리합니다."""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', text)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    if sanitized and sanitized[0].isdigit():
        sanitized = f'v_{sanitized}'
    if not sanitized:
        sanitized = f'unnamed_node_{abs(hash(text)) % 10000}'
    return sanitized.lower()

def main():
    """스크립트의 메인 실행 함수"""
    if len(sys.argv) != 3:
        print("사용법: python 9_OX_Dict_Mindmap.py <selected_folder> <bundle_id>")
        sys.exit(1)
    
    selected_folder = sys.argv[1]
    bundle_id = sys.argv[2]

    print("--- 마인드맵 Dart 파일 생성 시작 ---")
    
    try:
        # 1. 경로 설정
        # --- 수정된 부분: 입력 JSON 파일 경로에서 bundle_id 제거 ---
        json_file_path = os.path.join(selected_folder, "assets", "mindmap.json")
        
        # 출력 Dart 파일 경로는 bundle_id를 포함하는 것이 맞습니다.
        lib_dir = os.path.join(selected_folder, bundle_id, "lib")
        flutter_file_path = os.path.join(lib_dir, "mindmap.dart")

        print(f"입력 JSON 경로: {json_file_path}")
        print(f"출력 Dart 경로: {flutter_file_path}")

        # 2. JSON 파일 존재 확인
        if not os.path.exists(json_file_path):
            print(f"오류: mindmap.json 파일을 찾을 수 없습니다.")
            sys.exit(1)

        # lib 폴더 존재 확인 및 생성
        os.makedirs(lib_dir, exist_ok=True)
        print(f"lib 폴더 확인/생성: {lib_dir}")

        # 3. JSON 파일 읽기
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data_list = json.load(f)
            if not isinstance(json_data_list, list) or len(json_data_list) == 0:
                raise ValueError("JSON 형식이 올바르지 않습니다. 최상위는 리스트여야 합니다.")
            json_data = json_data_list[0]
            if "root" not in json_data:
                raise ValueError("JSON에 'root' 키가 없습니다.")

        # 4. Flutter 코드 생성 및 저장
        _generate_flutter_code(json_data, flutter_file_path)

        print(f"\n✅ 성공: mindmap.dart 파일이 생성되었습니다!")
        print("--- 마인드맵 Dart 파일 생성 완료 ---")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()