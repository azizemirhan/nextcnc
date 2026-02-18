"""
Tri-Dexel Stock Model for CNC material removal simulation.

Tri-Dexel = 3 directional Z-buffers (XY, XZ, YZ planes)
Provides fast, accurate material removal simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum

import numpy as np
from numpy.typing import NDArray


class ToolType(Enum):
    """Supported tool types."""
    FLAT_ENDMILL = "flat"
    BALL_ENDMILL = "ball"
    BULLNOSE = "bullnose"


@dataclass
class Tool:
    """CNC Tool definition."""
    tool_id: int
    name: str
    tool_type: ToolType
    diameter: float  # mm
    length: float    # mm
    corner_radius: float = 0.0  # For bullnose
    
    @property
    def radius(self) -> float:
        """Tool radius."""
        return self.diameter / 2.0


@dataclass
class StockConfig:
    """Stock material configuration."""
    # Dimensions (mm)
    width: float = 100.0   # X
    depth: float = 100.0   # Y
    height: float = 50.0   # Z
    
    # Resolution (mm per cell) - higher = faster but less detailed
    resolution: float = 2.0  # Changed from 0.5 to 2.0 for performance
    
    # Origin position (lower-left-bottom corner)
    origin_x: float = -50.0
    origin_y: float = -50.0
    origin_z: float = 0.0
    
    # Max grid size for performance protection
    max_grid_cells: int = 100_000  # ~316x316 grid max
    
    @property
    def nx(self) -> int:
        """Number of cells in X direction."""
        return min(int(self.width / self.resolution) + 1, 500)
    
    @property
    def ny(self) -> int:
        """Number of cells in Y direction."""
        return min(int(self.depth / self.resolution) + 1, 500)
    
    @property
    def nz(self) -> int:
        """Number of cells in Z direction."""
        return min(int(self.height / self.resolution) + 1, 200)
    
    def estimate_performance(self) -> dict:
        """Estimate performance impact."""
        total_cells = self.nx * self.ny
        estimated_memory_mb = (total_cells * 8) / (1024 * 1024)
        status = "OK" if total_cells < 50_000 else "WARNING" if total_cells < 200_000 else "HEAVY"
        return {
            "total_xy_cells": total_cells,
            "estimated_memory_mb": estimated_memory_mb,
            "status": status,
        }


@dataclass
class DexelColumn:
    """
    Single Dexel column.
    Stores top Z height of material at this (x, y) position.
    """
    x_idx: int
    y_idx: int
    z_top: float  # Top surface height
    z_bottom: float = 0.0  # Bottom of stock
    
    def remove_material(self, new_z: float) -> float:
        """
        Remove material down to new_z level.
        Returns amount of material removed.
        """
        if new_z >= self.z_top:
            return 0.0  # No material removed
        
        removed = self.z_top - max(new_z, self.z_bottom)
        self.z_top = max(new_z, self.z_bottom)
        return removed


class TriDexelBoard:
    """
    Tri-Dexel board for material representation.
    Uses 3 orthogonal Z-buffers for better accuracy.
    """
    
    def __init__(self, config: StockConfig):
        self.config = config
        
        # XY-board: Z height at each (x, y)
        # Stores top Z value
        self.xy_board: NDArray[np.float64] = np.full(
            (config.nx, config.ny), 
            config.origin_z + config.height,
            dtype=np.float64
        )
        
        # XZ-board: Y depth at each (x, z) - for side visibility
        self.xz_board: NDArray[np.float64] = np.full(
            (config.nx, config.nz),
            config.origin_y + config.depth,
            dtype=np.float64
        )
        
        # YZ-board: X depth at each (y, z)
        self.yz_board: NDArray[np.float64] = np.full(
            (config.ny, config.nz),
            config.origin_x + config.width,
            dtype=np.float64
        )
        
        # Material removal tracking
        self.total_removed_volume: float = 0.0
        self.cut_points: List[Tuple[float, float, float]] = []
    
    def world_to_grid(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """Convert world coordinates to grid indices."""
        gx = int((x - self.config.origin_x) / self.config.resolution)
        gy = int((y - self.config.origin_y) / self.config.resolution)
        gz = int((z - self.config.origin_z) / self.config.resolution)
        return (
            np.clip(gx, 0, self.config.nx - 1),
            np.clip(gy, 0, self.config.ny - 1),
            np.clip(gz, 0, self.config.nz - 1),
        )
    
    def grid_to_world(self, gx: int, gy: int, gz: int) -> Tuple[float, float, float]:
        """Convert grid indices to world coordinates."""
        return (
            self.config.origin_x + gx * self.config.resolution,
            self.config.origin_y + gy * self.config.resolution,
            self.config.origin_z + gz * self.config.resolution,
        )
    
    def get_height_at(self, x: float, y: float) -> float:
        """Get material height at world (x, y) position."""
        gx, gy, _ = self.world_to_grid(x, y, 0)
        return self.xy_board[gx, gy]
    
    def remove_at_xy(self, x: float, y: float, new_z: float) -> float:
        """
        Remove material at (x, y) position down to new_z.
        Returns volume removed.
        """
        gx, gy, _ = self.world_to_grid(x, y, 0)
        
        old_z = self.xy_board[gx, gy]
        if new_z < old_z:
            removed = old_z - new_z
            self.xy_board[gx, gy] = new_z
            self.total_removed_volume += removed * self.config.resolution ** 2
            return removed
        return 0.0
    
    def apply_cutter(self, x: float, y: float, z: float, tool: Tool) -> float:
        """
        Apply cylindrical cutter at position.
        Removes material within tool radius.
        
        Returns: Volume of material removed
        """
        if z >= self.config.origin_z + self.config.height:
            return 0.0  # Tool above stock
        
        radius = tool.radius
        z_cut = z - tool.length  # Tool tip Z
        
        # Grid range for tool
        gx, gy, _ = self.world_to_grid(x, y, 0)
        grid_radius = int(radius / self.config.resolution) + 1
        
        total_removed = 0.0
        
        # Iterate over grid cells within tool radius
        # Use squared distance to avoid sqrt calculation
        radius_sq = radius * radius
        
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                cx, cy = gx + dx, gy + dy
                
                # Check bounds
                if cx < 0 or cx >= self.config.nx or cy < 0 or cy >= self.config.ny:
                    continue
                
                # Calculate world distance from tool center (squared)
                wx, wy, _ = self.grid_to_world(cx, cy, 0)
                dist_sq = (wx - x) ** 2 + (wy - y) ** 2
                
                if dist_sq <= radius_sq:
                    # Remove material at this column
                    if tool.tool_type == ToolType.BALL_ENDMILL:
                        # Ball endmill: tool tip is spherical
                        dist = np.sqrt(dist_sq)
                        h_adjust = np.sqrt(max(0, radius_sq - dist_sq))
                        effective_z = z_cut + h_adjust
                    else:
                        # Flat endmill: constant height
                        effective_z = z_cut
                    
                    old_z = self.xy_board[cx, cy]
                    if effective_z < old_z:
                        self.xy_board[cx, cy] = max(effective_z, self.config.origin_z)
                        removed = old_z - self.xy_board[cx, cy]
                        total_removed += removed
        
        removed_volume = total_removed * self.config.resolution ** 2
        self.total_removed_volume += removed_volume
        
        if total_removed > 0:
            self.cut_points.append((x, y, z))
        
        return removed_volume
    
    def is_air_cut(self, x: float, y: float, z: float, tool: Tool) -> bool:
        """
        Check if tool at position would be air cutting.
        Returns True if tool is not touching material.
        """
        z_cut = z - tool.length
        
        # Sample a few points within tool radius
        radius = tool.radius
        angles = [0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 5*np.pi/4, 3*np.pi/2, 7*np.pi/4]
        
        for angle in angles:
            sx = x + radius * 0.5 * np.cos(angle)
            sy = y + radius * 0.5 * np.sin(angle)
            height = self.get_height_at(sx, sy)
            
            if z_cut <= height:
                return False  # Tool is cutting material
        
        return True  # Air cut
    
    def get_stock_mesh(self) -> Tuple[NDArray[np.float64], NDArray[np.int32]]:
        """
        Generate optimized mesh for rendering.
        Uses LOD (Level of Detail) based on grid size.
        Returns (vertices, indices) for triangle mesh.
        """
        # Use step size for LOD - larger grids = bigger steps
        total_cells = (self.config.nx - 1) * (self.config.ny - 1)
        if total_cells > 100_000:
            step = 4
        elif total_cells > 25_000:
            step = 2
        else:
            step = 1
        
        vertices = []
        indices = []
        
        # Generate vertices with step size
        for gy in range(0, self.config.ny - 1, step):
            for gx in range(0, self.config.nx - 1, step):
                # Get heights at corners (use current cell)
                z00 = self.xy_board[gx, gy]
                
                # Next cells (clamp to bounds)
                gx_next = min(gx + step, self.config.nx - 1)
                gy_next = min(gy + step, self.config.ny - 1)
                
                z10 = self.xy_board[gx_next, gy]
                z01 = self.xy_board[gx, gy_next]
                z11 = self.xy_board[gx_next, gy_next]
                
                # World positions
                x0, y0, _ = self.grid_to_world(gx, gy, 0)
                x1, y1, _ = self.grid_to_world(gx_next, gy_next, 0)
                
                # Create two triangles per cell
                base_idx = len(vertices)
                
                # Vertices (x, y, z)
                vertices.extend([
                    [x0, y0, z00],
                    [x1, y0, z10],
                    [x1, y1, z11],
                    [x0, y1, z01],
                ])
                
                # Triangle indices
                indices.extend([
                    [base_idx, base_idx + 1, base_idx + 2],
                    [base_idx, base_idx + 2, base_idx + 3],
                ])
        
        return np.array(vertices, dtype=np.float64), np.array(indices, dtype=np.int32)
    
    def get_stats(self) -> dict:
        """Get simulation statistics."""
        total_volume = (self.config.width * self.config.depth * self.config.height)
        removed_volume = self.total_removed_volume
        remaining_volume = total_volume - removed_volume
        
        return {
            "total_volume_mm3": total_volume,
            "removed_volume_mm3": removed_volume,
            "remaining_volume_mm3": remaining_volume,
            "removal_percent": (removed_volume / total_volume * 100) if total_volume > 0 else 0,
            "cut_points": len(self.cut_points),
        }


class StockSimulator:
    """
    High-level stock simulation controller.
    Manages toolpath simulation and material removal.
    """
    
    def __init__(self, config: Optional[StockConfig] = None):
        self.config = config or StockConfig()
        self.board = TriDexelBoard(self.config)
        self.current_tool: Optional[Tool] = None
        
        # Simulation state
        self.is_simulating = False
        self.current_position = np.zeros(3)
        self.air_cut_segments: List[Tuple[np.ndarray, np.ndarray]] = []
        self.cut_segments: List[Tuple[np.ndarray, np.ndarray]] = []
    
    def set_tool(self, tool: Tool) -> None:
        """Set current tool."""
        self.current_tool = tool
    
    def reset(self) -> None:
        """Reset stock to initial state."""
        self.board = TriDexelBoard(self.config)
        self.air_cut_segments = []
        self.cut_segments = []
    
    def simulate_move(self, start: NDArray, end: NDArray, feed: float = 0) -> dict:
        """
        Simulate a linear tool move.
        
        Args:
            start: Start position [x, y, z]
            end: End position [x, y, z]
            feed: Feed rate (mm/min)
        
        Returns:
            Simulation stats for this move
        """
        if self.current_tool is None:
            return {"error": "No tool set"}
        
        # Interpolate along move
        distance = np.linalg.norm(end - start)
        if distance < 0.001:
            return {"removed_volume": 0, "is_air_cut": True}
        
        # Calculate steps - use larger step size for performance
        # Minimum 2 steps, maximum 50 steps per move for performance
        steps = min(max(int(distance / self.config.resolution), 2), 50)
        
        total_removed = 0.0
        was_air_cut = True
        
        for i in range(steps + 1):
            t = i / steps
            pos = start + t * (end - start)
            
            # Check air cut
            if self.board.is_air_cut(pos[0], pos[1], pos[2], self.current_tool):
                if not was_air_cut:
                    # Transition to air cut
                    pass
            else:
                was_air_cut = False
                # Remove material
                removed = self.board.apply_cutter(
                    pos[0], pos[1], pos[2], self.current_tool
                )
                total_removed += removed
        
        # Track segment type
        if was_air_cut:
            self.air_cut_segments.append((start.copy(), end.copy()))
        else:
            self.cut_segments.append((start.copy(), end.copy()))
        
        return {
            "removed_volume": total_removed,
            "is_air_cut": was_air_cut,
            "steps": steps,
        }
    
    def simulate_toolpath(
        self, 
        segments: list,
        tool: Tool,
        on_progress: Optional[callable] = None
    ) -> dict:
        """
        Simulate complete toolpath.
        
        Args:
            segments: List of toolpath segments from parser
            tool: Tool to use
            on_progress: Callback(progress_pct)
        
        Returns:
            Final simulation stats
        """
        self.reset()
        self.set_tool(tool)
        
        total_segments = len(segments)
        
        for i, seg in enumerate(segments):
            start = np.array(seg["start"])
            end = np.array(seg["end"])
            feed = seg.get("feedrate", 0)
            
            self.simulate_move(start, end, feed)
            
            if on_progress:
                on_progress((i + 1) / total_segments * 100)
        
        return self.get_stats()
    
    def get_stats(self) -> dict:
        """Get simulation statistics."""
        stats = self.board.get_stats()
        stats["air_cut_segments"] = len(self.air_cut_segments)
        stats["cut_segments"] = len(self.cut_segments)
        return stats
    
    def get_mesh_for_render(self) -> Optional[Tuple[NDArray, NDArray]]:
        """Get mesh data for OpenGL rendering."""
        return self.board.get_stock_mesh()
