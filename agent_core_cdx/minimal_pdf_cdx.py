from __future__ import annotations # Codex

import math # Codex
from pathlib import Path # Codex
from typing import Tuple # Codex


Color = Tuple[float, float, float] # Codex


class Colors: # Codex
    black: Color = (0.0, 0.0, 0.0) # Codex
    red: Color = (1.0, 0.0, 0.0) # Codex
    blue: Color = (0.0, 0.0, 1.0) # Codex
    green: Color = (0.0, 0.5, 0.0) # Codex

    @staticmethod # Codex
    def HexColor(value: str) -> Color: # Codex
        cleaned = value.lstrip("#") # Codex
        return tuple(int(cleaned[index:index + 2], 16) / 255.0 for index in (0, 2, 4)) # Codex


colors = Colors() # Codex


class PdfPath: # Codex
    def __init__(self) -> None: # Codex
        self.commands: list[str] = [] # Codex

    def moveTo(self, x: float, y: float) -> None: # Codex
        self.commands.append(f"{x:.4f} {y:.4f} m") # Codex

    def lineTo(self, x: float, y: float) -> None: # Codex
        self.commands.append(f"{x:.4f} {y:.4f} l") # Codex


class Canvas: # Codex
    def __init__(self, filename: str, pagesize: tuple[float, float]) -> None: # Codex
        self.filename = Path(filename) # Codex
        self.width, self.height = pagesize # Codex
        self.commands: list[str] = [] # Codex
        self.font_size = 10.0 # Codex

    def setFillColorRGB(self, red: float, green: float, blue: float) -> None: # Codex
        self.commands.append(f"{red:.4f} {green:.4f} {blue:.4f} rg") # Codex

    def setStrokeColorRGB(self, red: float, green: float, blue: float) -> None: # Codex
        self.commands.append(f"{red:.4f} {green:.4f} {blue:.4f} RG") # Codex

    def setFillColor(self, color: Color) -> None: # Codex
        self.setFillColorRGB(*color) # Codex

    def setStrokeColor(self, color: Color) -> None: # Codex
        self.setStrokeColorRGB(*color) # Codex

    def setDash(self, pattern: list[float]) -> None: # Codex
        values = " ".join(f"{value:g}" for value in pattern) # Codex
        self.commands.append(f"[{values}] 0 d") # Codex

    def setFont(self, name: str, size: float) -> None: # Codex
        self.font_size = float(size) # Codex

    def rect(self, x: float, y: float, width: float, height: float, fill: int = 0, stroke: int = 1) -> None: # Codex
        self.commands.append(f"{x:.4f} {y:.4f} {width:.4f} {height:.4f} re {paint_operator(fill, stroke)}") # Codex

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None: # Codex
        self.commands.append(f"{x1:.4f} {y1:.4f} m {x2:.4f} {y2:.4f} l S") # Codex

    def circle(self, x: float, y: float, radius: float, fill: int = 0, stroke: int = 1) -> None: # Codex
        control = radius * 0.5522847498 # Codex
        command = f"{x + radius:.4f} {y:.4f} m {x + radius:.4f} {y + control:.4f} {x + control:.4f} {y + radius:.4f} {x:.4f} {y + radius:.4f} c {x - control:.4f} {y + radius:.4f} {x - radius:.4f} {y + control:.4f} {x - radius:.4f} {y:.4f} c {x - radius:.4f} {y - control:.4f} {x - control:.4f} {y - radius:.4f} {x:.4f} {y - radius:.4f} c {x + control:.4f} {y - radius:.4f} {x + radius:.4f} {y - control:.4f} {x + radius:.4f} {y:.4f} c {paint_operator(fill, stroke)}" # Codex
        self.commands.append(command) # Codex

    def drawString(self, x: float, y: float, text: str) -> None: # Codex
        self.commands.append(text_command(x, y, text, self.font_size)) # Codex

    def drawCentredString(self, x: float, y: float, text: str) -> None: # Codex
        self.drawString(x - approximate_text_width(text, self.font_size) / 2.0, y, text) # Codex

    def drawRightString(self, x: float, y: float, text: str) -> None: # Codex
        self.drawString(x - approximate_text_width(text, self.font_size), y, text) # Codex

    def saveState(self) -> None: # Codex
        self.commands.append("q") # Codex

    def restoreState(self) -> None: # Codex
        self.commands.append("Q") # Codex

    def translate(self, x: float, y: float) -> None: # Codex
        self.commands.append(f"1 0 0 1 {x:.4f} {y:.4f} cm") # Codex

    def rotate(self, angle: float) -> None: # Codex
        radians = math.radians(angle) # Codex
        cosine, sine = math.cos(radians), math.sin(radians) # Codex
        self.commands.append(f"{cosine:.6f} {sine:.6f} {-sine:.6f} {cosine:.6f} 0 0 cm") # Codex

    def beginPath(self) -> PdfPath: # Codex
        return PdfPath() # Codex

    def drawPath(self, path: PdfPath, fill: int = 0, stroke: int = 1) -> None: # Codex
        self.commands.append(" ".join(path.commands + [paint_operator(fill, stroke)])) # Codex

    def save(self) -> None: # Codex
        stream = ("\n".join(self.commands) + "\n").encode("latin-1", errors="replace") # Codex
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:g} {self.height:g}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode("ascii"), b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream"] # Codex
        document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n") # Codex
        offsets = [0] # Codex
        for number, body in enumerate(objects, start=1): # Codex
            offsets.append(len(document)) # Codex
            document.extend(f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n") # Codex
        xref = len(document) # Codex
        document.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")) # Codex
        for offset in offsets[1:]: # Codex
            document.extend(f"{offset:010d} 00000 n \n".encode("ascii")) # Codex
        document.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")) # Codex
        self.filename.write_bytes(document) # Codex


class CanvasModule: # Codex
    Canvas = Canvas # Codex


canvas = CanvasModule() # Codex


def paint_operator(fill: int, stroke: int) -> str: # Codex
    if fill and stroke: # Codex
        return "B" # Codex
    if fill: # Codex
        return "f" # Codex
    return "S" if stroke else "n" # Codex


def approximate_text_width(text: str, size: float) -> float: # Codex
    return len(text) * size * 0.52 # Codex


def text_command(x: float, y: float, text: str, size: float) -> str: # Codex
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") # Codex
    return f"BT /F1 {size:g} Tf 1 0 0 1 {x:.4f} {y:.4f} Tm ({escaped}) Tj ET" # Codex
