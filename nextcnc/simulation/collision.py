"""
Collision Detection for CNC simulation.
AABB (Axis-Aligned Bounding Box) broad-phase and basic narrow-phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray


class CollisionType(Enum):
    """Types of collisions in CNC."""
    TOOL_STOCK = auto()      # Tool cutting stock (normal)
    TOOL_HOLDER_STOCK = auto()  # Tool holder hitting stock (bad!)
    TOOL_FIXTURE = auto()    # Tool hitting fixture
    SPINDLE_STOCK = auto()   # Spindle body hitting stock
    AXIS_LIMIT = auto()      # Machine axis limit exceeded


@dataclass
class BoundingBox:
    """Axis-Aligned Bounding Box."""
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0
    
    @property
    def center(self) -> np.ndarray:
        """Box center point."""
        return np.array([
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        ])
    
    @property
    def size(self) -> np.ndarray:
        """Box dimensions."""
        return np.array([
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z,
        ])
    
    @property
    def volume(self) -> float:
        """Box volume."""
        sx, sy, sz = self.size
        return sx * sy * sz
    
    @classmethod
    def from_points(cls, points: NDArray) -> "BoundingBox":
        """Create AABB from point array."""
        if len(points) == 0:
            return cls()
        return cls(
            min_x=float(points[:, 0].min()),
            min_y=float(points[:, 1].min()),
            min_z=float(points[:, 2].min()),
            max_x=float(points[:, 0].max()),
            max_y=float(points[:, 1].max()),
            max_z=float(points[:, 2].max()),
        )
    
    @classmethod
    def from_sphere(cls, center: np.ndarray, radius: float) -> "BoundingBox":
        """Create AABB from sphere."""
        return cls(
            min_x=center[0] - radius,
            max_x=center[0] + radius,
            min_y=center[1] - radius,
            max_y=center[1] + radius,
            min_z=center[2] - radius,
            max_z=center[2] + radius,
        )
    
    @classmethod
    def from_cylinder(cls, p1: np.ndarray, p2: np.ndarray, radius: float) -> "BoundingBox":
        """Create AABB from cylinder."""
        return cls(
            min_x=min(p1[0], p2[0]) - radius,
            max_x=max(p1[0], p2[0]) + radius,
            min_y=min(p1[1], p2[1]) - radius,
            max_y=max(p1[1], p2[1]) + radius,
            min_z=min(p1[2], p2[2]) - radius,
            max_z=max(p1[2], p2[2]) + radius,
        )
    
    def intersects(self, other: "BoundingBox") -> bool:
        """Check if this AABB intersects with another."""
        return (
            self.min_x <= other.max_x and self.max_x >= other.min_x and
            self.min_y <= other.max_y and self.max_y >= other.min_y and
            self.min_z <= other.max_z and self.max_z >= other.min_z
        )
    
    def contains_point(self, point: np.ndarray) -> bool:
        """Check if point is inside this AABB."""
        return (
            self.min_x <= point[0] <= self.max_x and
            self.min_y <= point[1] <= self.max_y and
            self.min_z <= point[2] <= self.max_z
        )
    
    def expand_to_include(self, other: "BoundingBox") -> None:
        """Expand this AABB to include another."""
        self.min_x = min(self.min_x, other.min_x)
        self.max_x = max(self.max_x, other.max_x)
        self.min_y = min(self.min_y, other.min_y)
        self.max_y = max(self.max_y, other.max_y)
        self.min_z = min(self.min_z, other.min_z)
        self.max_z = max(self.max_z, other.max_z)
    
    def expanded(self, margin: float) -> "BoundingBox":
        """Return a new AABB expanded by margin in all directions."""
        return BoundingBox(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            min_z=self.min_z - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin,
            max_z=self.max_z + margin,
        )
    
    def clone(self) -> "BoundingBox":
        """Create a copy of this AABB."""
        return BoundingBox(
            min_x=self.min_x,
            min_y=self.min_y,
            min_z=self.min_z,
            max_x=self.max_x,
            max_y=self.max_y,
            max_z=self.max_z,
        )


@dataclass
class Collider:
    """Base class for collidable objects."""
    name: str
    bbox: BoundingBox
    collision_type: CollisionType
    
    def get_bbox_at_position(self, position: np.ndarray) -> BoundingBox:
        """Get AABB at specific position."""
        # Default: just translate bbox
        offset = position - self.bbox.center
        return BoundingBox(
            min_x=self.bbox.min_x + offset[0],
            max_x=self.bbox.max_x + offset[0],
            min_y=self.bbox.min_y + offset[1],
            max_y=self.bbox.max_y + offset[1],
            min_z=self.bbox.min_z + offset[2],
            max_z=self.bbox.max_z + offset[2],
        )


@dataclass
class ToolCollider(Collider):
    """Tool collider with cylindrical shape approximation."""
    diameter: float = 10.0
    length: float = 50.0
    
    def __post_init__(self):
        """Initialize cylindrical bbox."""
        r = self.diameter / 2
        self.bbox = BoundingBox(
            min_x=-r, max_x=r,
            min_y=-r, max_y=r,
            min_z=-self.length, max_z=0,
        )
    
    def get_tip_position(self, holder_position: np.ndarray) -> np.ndarray:
        """Get tool tip position from holder position."""
        return holder_position - np.array([0, 0, self.length])


@dataclass
class ToolHolderCollider(Collider):
    """Tool holder collider."""
    diameter: float = 40.0
    length: float = 100.0
    
    def __post_init__(self):
        r = self.diameter / 2
        self.bbox = BoundingBox(
            min_x=-r, max_x=r,
            min_y=-r, max_y=r,
            min_z=0, max_z=self.length,
        )


@dataclass
class StockCollider(Collider):
    """Stock material collider."""
    def __init__(self, bbox: BoundingBox):
        super().__init__(
            name="Stock",
            bbox=bbox,
            collision_type=CollisionType.TOOL_STOCK
        )


@dataclass
class FixtureCollider(Collider):
    """Fixture/workholding collider."""
    def __init__(self, bbox: BoundingBox, name: str = "Fixture"):
        super().__init__(
            name=name,
            bbox=bbox,
            collision_type=CollisionType.TOOL_FIXTURE
        )


@dataclass
class CollisionEvent:
    """A detected collision event."""
    collider_a: str
    collider_b: str
    collision_type: CollisionType
    position: np.ndarray  # Collision position
    penetration_depth: float
    block_number: Optional[int] = None
    time_step: float = 0.0
    
    def __repr__(self) -> str:
        return (f"Collision({self.collider_a} vs {self.collider_b}, "
                f"type={self.collision_type.name}, "
                f"depth={self.penetration_depth:.3f}mm)")


class AABBTree:
    """
    Simple AABB tree for broad-phase collision detection.
    Groups colliders spatially for efficient queries.
    """
    
    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.root: Optional[Dict] = None
        self.colliders: List[Collider] = []
    
    def build(self, colliders: List[Collider]) -> None:
        """Build AABB tree from colliders."""
        self.colliders = colliders
        if not colliders:
            self.root = None
            return
        
        # Compute global bounds
        global_bbox = colliders[0].bbox
        for c in colliders[1:]:
            global_bbox.expand_to_include(c.bbox)
        
        # Build tree
        self.root = self._build_node(colliders, global_bbox, 0)
    
    def _build_node(self, colliders: List[Collider], bbox: BoundingBox, depth: int) -> Dict:
        """Recursively build tree node."""
        # Base case: store colliders at this node
        if depth >= self.max_depth or len(colliders) <= 2:
            return {
                "bbox": bbox,
                "colliders": colliders,
                "children": [],
            }
        
        # Split along longest axis
        size = bbox.size
        axis = int(np.argmax(size))
        
        # Sort colliders by center on split axis
        sorted_colliders = sorted(
            colliders,
            key=lambda c: c.bbox.center[axis]
        )
        
        # Split in half
        mid = len(sorted_colliders) // 2
        left_colliders = sorted_colliders[:mid]
        right_colliders = sorted_colliders[mid:]
        
        # Build child bounding boxes
        left_bbox = left_colliders[0].bbox.clone() if left_colliders else bbox
        for c in left_colliders[1:]:
            left_bbox.expand_to_include(c.bbox)
        
        right_bbox = right_colliders[0].bbox.clone() if right_colliders else bbox
        for c in right_colliders[1:]:
            right_bbox.expand_to_include(c.bbox)
        
        # Recursively build children
        children = []
        if left_colliders:
            children.append(self._build_node(left_colliders, left_bbox, depth + 1))
        if right_colliders:
            children.append(self._build_node(right_colliders, right_bbox, depth + 1))
        
        return {
            "bbox": bbox,
            "colliders": [],  # Internal node has no colliders
            "children": children,
        }
    
    def query_collisions(self, moving_bbox: BoundingBox) -> List[Collider]:
        """Query colliders that might collide with moving_bbox."""
        results = []
        self._query_node(self.root, moving_bbox, results)
        return results
    
    def _query_node(self, node: Optional[Dict], bbox: BoundingBox, results: List[Collider]) -> None:
        """Recursively query tree."""
        if node is None:
            return
        
        # Check if bbox intersects node bbox
        if not bbox.intersects(node["bbox"]):
            return
        
        # Add colliders at this node
        results.extend(node["colliders"])
        
        # Query children
        for child in node["children"]:
            self._query_node(child, bbox, results)


class CollisionDetector:
    """
    Main collision detection system.
    Broad-phase (AABB tree) + narrow-phase (specific shapes).
    """
    
    def __init__(self):
        self.static_colliders: List[Collider] = []
        self.dynamic_colliders: List[Collider] = []
        self.aabb_tree = AABBTree()
        self.collision_history: List[CollisionEvent] = []
        
        # Safety margins
        self.tool_holder_margin = 1.0  # mm
        self.spindle_margin = 5.0  # mm
    
    def add_static_collider(self, collider: Collider) -> None:
        """Add a static collider (stock, fixture)."""
        self.static_colliders.append(collider)
    
    def add_dynamic_collider(self, collider: Collider) -> None:
        """Add a dynamic collider (tool)."""
        self.dynamic_colliders.append(collider)
    
    def build(self) -> None:
        """Build acceleration structure."""
        self.aabb_tree.build(self.static_colliders)
    
    def check_tool_at_position(
        self,
        tool: ToolCollider,
        holder: ToolHolderCollider,
        position: np.ndarray,
        block_number: Optional[int] = None,
    ) -> List[CollisionEvent]:
        """
        Check for collisions at specific tool position.
        
        Args:
            tool: Tool collider
            holder: Tool holder collider
            position: Tool tip position [x, y, z]
            block_number: Current G-code block number
        
        Returns:
            List of collision events
        """
        events = []
        
        # Tool AABB at this position (tool tip is reference point)
        tool_bbox = tool.get_bbox_at_position(position)
        
        # Holder is above tool
        holder_pos = position + np.array([0, 0, tool.length])
        holder_bbox = holder.get_bbox_at_position(holder_pos)
        holder_bbox_expanded = holder_bbox.expanded(self.tool_holder_margin)
        
        # Broad-phase: query static colliders
        potential_collisions_tool = self.aabb_tree.query_collisions(tool_bbox)
        potential_collisions_holder = self.aabb_tree.query_collisions(holder_bbox_expanded)
        
        # Check tool collisions (with stock = normal cutting)
        for collider in potential_collisions_tool:
            if isinstance(collider, StockCollider):
                if tool_bbox.intersects(collider.bbox):
                    overlap = self._calculate_penetration(tool_bbox, collider.bbox)
                    # Only report if significantly inside (not just touching)
                    if overlap > 0.01:
                        events.append(CollisionEvent(
                            collider_a=tool.name,
                            collider_b=collider.name,
                            collision_type=CollisionType.TOOL_STOCK,
                            position=position,
                            penetration_depth=overlap,
                            block_number=block_number,
                        ))
        
        # Check holder collisions (BAD - holder should never hit stock!)
        for collider in potential_collisions_holder:
            if isinstance(collider, (StockCollider, FixtureCollider)):
                if holder_bbox_expanded.intersects(collider.bbox):
                    overlap = self._calculate_penetration(holder_bbox_expanded, collider.bbox)
                    if overlap > 0.01:
                        events.append(CollisionEvent(
                            collider_a=holder.name,
                            collider_b=collider.name,
                            collision_type=CollisionType.TOOL_HOLDER_STOCK,
                            position=holder_pos,
                            penetration_depth=overlap,
                            block_number=block_number,
                        ))
        
        return events
    
    def _calculate_penetration(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """Calculate penetration depth between two intersecting AABBs."""
        # Find overlap on each axis
        overlap_x = min(bbox_a.max_x, bbox_b.max_x) - max(bbox_a.min_x, bbox_b.min_x)
        overlap_y = min(bbox_a.max_y, bbox_b.max_y) - max(bbox_a.min_y, bbox_b.min_y)
        overlap_z = min(bbox_a.max_z, bbox_b.max_z) - max(bbox_a.min_z, bbox_b.min_z)
        
        # Return minimum overlap (penetration depth)
        return min(overlap_x, overlap_y, overlap_z)
    
    def check_continuous_motion(
        self,
        tool: ToolCollider,
        holder: ToolHolderCollider,
        start_pos: np.ndarray,
        end_pos: np.ndarray,
        steps: int = 10,
        block_number: Optional[int] = None,
    ) -> List[CollisionEvent]:
        """
        Check for collisions along a continuous motion.
        Uses multiple samples to catch collisions during rapid moves.
        """
        all_events = []
        
        for i in range(steps + 1):
            t = i / steps
            pos = start_pos + t * (end_pos - start_pos)
            events = self.check_tool_at_position(tool, holder, pos, block_number)
            all_events.extend(events)
        
        return all_events
    
    def get_collision_stats(self) -> dict:
        """Get collision statistics."""
        type_counts = {}
        for event in self.collision_history:
            type_name = event.collision_type.name
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "total_collisions": len(self.collision_history),
            "by_type": type_counts,
            "tool_holder_collisions": type_counts.get(CollisionType.TOOL_HOLDER_STOCK.name, 0),
        }


def create_stock_collider_from_bounds(
    min_x: float, min_y: float, min_z: float,
    max_x: float, max_y: float, max_z: float,
) -> StockCollider:
    """Helper to create stock collider from bounds."""
    return StockCollider(BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z))


def create_fixture_collider(
    x: float, y: float, z: float,
    width: float, depth: float, height: float,
    name: str = "Fixture",
) -> FixtureCollider:
    """Helper to create fixture collider."""
    return FixtureCollider(BoundingBox(
        min_x=x - width/2,
        max_x=x + width/2,
        min_y=y - depth/2,
        max_y=y + depth/2,
        min_z=z,
        max_z=z + height,
    ), name)
