"""
3D toolpath and stock renderer using PyOpenGL.
Draws polyline toolpath and tri-dexel stock mesh.
"""

import math
import numpy as np
from nextcnc.qt_compat import Qt, QSurfaceFormat, QOpenGLWidget

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_LINES,
    GL_LINE_STRIP,
    GL_FLOAT,
    GL_VERTEX_SHADER,
    GL_FRAGMENT_SHADER,
    GL_TRIANGLES,
    GL_CULL_FACE,
    GL_FRONT,
    GL_BACK,
)
from OpenGL.GL import (
    glClear,
    glClearColor,
    glDrawArrays,
    glEnableVertexAttribArray,
    glDisableVertexAttribArray,
    glVertexAttribPointer,
    glViewport,
    glUseProgram,
    glGetUniformLocation,
    glUniformMatrix4fv,
    glUniform4f,
    glGetAttribLocation,
    glLineWidth,
    glEnable,
    glDisable,
)

# Default XYZ axes: 3 lines from origin (length 40 mm)
AXES_VERTICES = np.array([
    0, 0, 0,  40, 0, 0,   # X
    0, 0, 0,  0, 40, 0,   # Y
    0, 0, 0,  0, 0, 40,   # Z
], dtype=np.float32)


def _compile_shader(src: str, shader_type: int) -> int:
    from OpenGL.GL import (
        GL_COMPILE_STATUS,
        glCompileShader,
        glCreateShader,
        glGetShaderInfoLog,
        glGetShaderiv,
        glShaderSource,
    )
    sid = glCreateShader(shader_type)
    glShaderSource(sid, src)
    glCompileShader(sid)
    status = glGetShaderiv(sid, GL_COMPILE_STATUS)
    if not status:
        log = glGetShaderInfoLog(sid)
        raise RuntimeError(f"Shader compile failed: {log}")
    return sid


def _link_program(vertex_id: int, fragment_id: int) -> int:
    from OpenGL.GL import (
        GL_LINK_STATUS,
        glAttachShader,
        glCreateProgram,
        glGetProgramInfoLog,
        glGetProgramiv,
        glLinkProgram,
    )
    pid = glCreateProgram()
    if not pid:
        raise RuntimeError("glCreateProgram failed")
    glAttachShader(pid, vertex_id)
    glAttachShader(pid, fragment_id)
    glLinkProgram(pid)
    status = glGetProgramiv(pid, GL_LINK_STATUS)
    if not status:
        log = glGetProgramInfoLog(pid)
        raise RuntimeError(f"Program link failed: {log}")
    return int(pid)


VERTEX_SHADER_SRC = """
#version 120
attribute vec3 position;
uniform mat4 mvp;
void main() {
    gl_Position = mvp * vec4(position, 1.0);
}
"""

FRAGMENT_SHADER_SRC = """
#version 120
uniform vec4 color;
void main() {
    gl_FragColor = color;
}
"""


def _ortho(left: float, right: float, bottom: float, top: float, near: float, far: float) -> np.ndarray:
    """Column-major 4x4 orthographic projection."""
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = 2.0 / (right - left)
    m[1, 1] = 2.0 / (top - bottom)
    m[2, 2] = -2.0 / (far - near)
    m[0, 3] = -(right + left) / (right - left)
    m[1, 3] = -(top + bottom) / (top - bottom)
    m[2, 3] = -(far + near) / (far - near)
    return m


def _rotate_x(deg: float) -> np.ndarray:
    c = math.cos(math.radians(deg))
    s = math.sin(math.radians(deg))
    m = np.eye(4, dtype=np.float32)
    m[1, 1], m[1, 2] = c, -s
    m[2, 1], m[2, 2] = s, c
    return m


def _rotate_y(deg: float) -> np.ndarray:
    c = math.cos(math.radians(deg))
    s = math.sin(math.radians(deg))
    m = np.eye(4, dtype=np.float32)
    m[0, 0], m[0, 2] = c, s
    m[2, 0], m[2, 2] = -s, c
    return m


def _translate(x: float, y: float, z: float) -> np.ndarray:
    m = np.eye(4, dtype=np.float32)
    m[0, 3], m[1, 3], m[2, 3] = x, y, z
    return m


class SimulationWidget(QOpenGLWidget):
    """
    OpenGL widget that displays 3D toolpath and stock.
    Uses Compatibility Profile. Set points via set_points().
    Camera: left-drag orbit, right-drag pan, wheel zoom.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: np.ndarray = np.zeros((0, 3), dtype=np.float32)
        self._stock_vertices: np.ndarray = np.zeros((0, 3), dtype=np.float32)
        self._stock_indices: np.ndarray = np.zeros((0, 3), dtype=np.int32)
        self._show_stock: bool = False
        
        self._program: int = 0
        self._attr_position: int = -1
        self._uniform_mvp: int = -1
        self._uniform_color: int = -1
        self._gl_initialized: bool = False

        self._default_rot_x = -20.0
        self._default_rot_y = 30.0
        self._default_zoom = 1.0
        self._default_pan_x = 0.0
        self._default_pan_y = 0.0
        
        self._rot_x = self._default_rot_x
        self._rot_y = self._default_rot_y
        self._zoom = self._default_zoom
        self._pan_x = self._default_pan_x
        self._pan_y = self._default_pan_y
        self._last_pos = None

        fmt = QSurfaceFormat()
        fmt.setVersion(2, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.NoProfile)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(4)
        self.setFormat(fmt)

    def set_points(self, points: np.ndarray) -> None:
        """Set toolpath points."""
        if points is None or len(points) == 0:
            self._points = np.zeros((0, 3), dtype=np.float32)
        else:
            self._points = np.asarray(points, dtype=np.float32)
            if self._points.ndim != 2 or self._points.shape[1] != 3:
                self._points = np.zeros((0, 3), dtype=np.float32)
        self.update()

    def set_stock_mesh(self, vertices: np.ndarray, indices: np.ndarray) -> None:
        """Set stock mesh for rendering."""
        if vertices is not None and len(vertices) > 0:
            self._stock_vertices = np.asarray(vertices, dtype=np.float32)
            self._stock_indices = np.asarray(indices, dtype=np.int32)
            self._show_stock = True
        else:
            self._stock_vertices = np.zeros((0, 3), dtype=np.float32)
            self._stock_indices = np.zeros((0, 3), dtype=np.int32)
            self._show_stock = False
        self.update()

    def show_stock(self, show: bool) -> None:
        """Toggle stock visibility."""
        self._show_stock = show and len(self._stock_vertices) > 0
        self.update()

    def reset_view(self) -> None:
        """Reset camera to default view."""
        self._rot_x = self._default_rot_x
        self._rot_y = self._default_rot_y
        self._zoom = self._default_zoom
        self._pan_x = self._default_pan_x
        self._pan_y = self._default_pan_y
        self.update()

    def initializeGL(self) -> None:
        glClearColor(0.12, 0.12, 0.14, 1.0)

    def _ensure_gl_resources(self) -> None:
        """Create shaders when context is current."""
        if self._gl_initialized:
            return
        self._gl_initialized = True
        try:
            vs = _compile_shader(VERTEX_SHADER_SRC, GL_VERTEX_SHADER)
            fs = _compile_shader(FRAGMENT_SHADER_SRC, GL_FRAGMENT_SHADER)
            self._program = _link_program(vs, fs)
            if not self._program:
                return
            self._uniform_mvp = glGetUniformLocation(self._program, "mvp")
            self._uniform_color = glGetUniformLocation(self._program, "color")
            self._attr_position = glGetAttribLocation(self._program, "position")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._program = 0

    def resizeGL(self, w: int, h: int) -> None:
        glViewport(0, 0, w, h)

    def _build_mvp(self) -> np.ndarray:
        """Build model-view-projection matrix."""
        w, h = max(1, self.width()), max(1, self.height())
        aspect = w / h
        
        # Calculate bounds from all visible geometry
        all_points = []
        if len(self._points) > 0:
            all_points.append(self._points)
        if self._show_stock and len(self._stock_vertices) > 0:
            all_points.append(self._stock_vertices)
        
        if all_points:
            combined = np.concatenate(all_points, axis=0)
            mn = combined.min(axis=0)
            mx = combined.max(axis=0)
            size = float(np.max(mx - mn))
            if size < 1e-6:
                size = 10.0
            half = size / 2.0 + 10.0
            cen = (mn + mx) / 2.0
        else:
            half = 50.0
            cen = np.zeros(3, dtype=np.float32)
        
        left = -aspect * half * self._zoom + self._pan_x
        right = aspect * half * self._zoom + self._pan_x
        bottom = -half * self._zoom + self._pan_y
        top = half * self._zoom + self._pan_y
        
        P = _ortho(left, right, bottom, top, -1000.0, 1000.0)
        T_pan = _translate(self._pan_x, self._pan_y, 0.0)
        Rx = _rotate_x(self._rot_x)
        Ry = _rotate_y(self._rot_y)
        T_cent = _translate(-float(cen[0]), -float(cen[1]), -float(cen[2]))
        V = T_pan @ Rx @ Ry @ T_cent
        return (P @ V).astype(np.float32)

    def paintGL(self) -> None:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self._ensure_gl_resources()
        
        if not self._program or self._attr_position < 0:
            return
        
        glUseProgram(self._program)
        mvp = self._build_mvp()
        glUniformMatrix4fv(self._uniform_mvp, 1, True, mvp)
        
        # Draw stock mesh first (if enabled)
        if self._show_stock and len(self._stock_vertices) > 0 and len(self._stock_indices) > 0:
            self._draw_stock()
        
        # Draw toolpath
        if len(self._points) >= 2:
            self._draw_toolpath()
        else:
            self._draw_axes()
        
        glUseProgram(0)

    def _draw_stock(self) -> None:
        """Draw stock mesh as wireframe."""
        glUniform4f(self._uniform_color, 0.6, 0.4, 0.2, 1.0)  # Brown-ish
        
        # Draw as wireframe lines between vertices
        try:
            glLineWidth(1.0)
        except Exception:
            pass
        
        # Flatten indices to draw triangles as line loops
        lines = []
        for tri in self._stock_indices:
            lines.extend([tri[0], tri[1], tri[1], tri[2], tri[2], tri[0]])
        
        if lines:
            line_indices = np.array(lines, dtype=np.int32)
            vertices = self._stock_vertices.flatten()
            
            for i in range(0, len(line_indices), 2):
                idx0, idx1 = line_indices[i], line_indices[i+1]
                if idx0 < len(self._stock_vertices) and idx1 < len(self._stock_vertices):
                    pts = np.array([
                        self._stock_vertices[idx0],
                        self._stock_vertices[idx1]
                    ], dtype=np.float32).flatten()
                    
                    glEnableVertexAttribArray(self._attr_position)
                    glVertexAttribPointer(self._attr_position, 3, GL_FLOAT, False, 0, pts)
                    glDrawArrays(GL_LINES, 0, 2)
                    glDisableVertexAttribArray(self._attr_position)

    def _draw_toolpath(self) -> None:
        """Draw toolpath polyline."""
        glUniform4f(self._uniform_color, 0.2, 0.7, 0.9, 1.0)  # Cyan
        try:
            glLineWidth(2.0)
        except Exception:
            pass
        
        pts = np.ascontiguousarray(self._points, dtype=np.float32)
        glEnableVertexAttribArray(self._attr_position)
        glVertexAttribPointer(self._attr_position, 3, GL_FLOAT, False, 0, pts)
        glDrawArrays(GL_LINE_STRIP, 0, len(self._points))
        glDisableVertexAttribArray(self._attr_position)

    def _draw_axes(self) -> None:
        """Draw XYZ axes when no toolpath loaded."""
        # X axis - Red
        glUniform4f(self._uniform_color, 0.9, 0.25, 0.2, 1.0)
        axes = np.ascontiguousarray(AXES_VERTICES[:6], dtype=np.float32)
        glEnableVertexAttribArray(self._attr_position)
        glVertexAttribPointer(self._attr_position, 3, GL_FLOAT, False, 0, axes)
        glDrawArrays(GL_LINES, 0, 2)
        glDisableVertexAttribArray(self._attr_position)
        
        # Y axis - Green
        glUniform4f(self._uniform_color, 0.2, 0.85, 0.3, 1.0)
        axes = np.ascontiguousarray(AXES_VERTICES[6:12], dtype=np.float32)
        glEnableVertexAttribArray(self._attr_position)
        glVertexAttribPointer(self._attr_position, 3, GL_FLOAT, False, 0, axes)
        glDrawArrays(GL_LINES, 0, 2)
        glDisableVertexAttribArray(self._attr_position)
        
        # Z axis - Blue
        glUniform4f(self._uniform_color, 0.25, 0.5, 0.95, 1.0)
        axes = np.ascontiguousarray(AXES_VERTICES[12:], dtype=np.float32)
        glEnableVertexAttribArray(self._attr_position)
        glVertexAttribPointer(self._attr_position, 3, GL_FLOAT, False, 0, axes)
        glDrawArrays(GL_LINES, 0, 2)
        glDisableVertexAttribArray(self._attr_position)

    def mousePressEvent(self, event):
        self._last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._last_pos is None:
            return
        pos = event.position()
        dx = pos.x() - self._last_pos.x()
        dy = pos.y() - self._last_pos.y()
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._rot_y += dx * 0.5
            self._rot_x += dy * 0.5
            self._rot_x = max(-90, min(90, self._rot_x))
        elif event.buttons() & Qt.MouseButton.RightButton:
            self._pan_x -= dx * 0.5
            self._pan_y += dy * 0.5
        self._last_pos = pos
        self.update()

    def mouseReleaseEvent(self, event):
        self._last_pos = None

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom *= 0.9
        else:
            self._zoom *= 1.1
        self._zoom = max(0.01, min(100.0, self._zoom))
        self.update()
