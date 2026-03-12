"""Minimal PDF drawing helpers for workflow-generated figures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PdfCanvas:
    width: int = 612
    height: int = 396
    commands: list[str] = field(default_factory=list)

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 1.0) -> None:
        self.commands.append(f"{width} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(self, x: float, y: float, width: float, height: float, rgb: tuple[float, float, float]) -> None:
        r, g, b = rgb
        self.commands.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f")

    def text(self, x: float, y: float, value: str, size: int = 11) -> None:
        escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        self.commands.append(f"BT /F1 {size} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def write(self, path: Path) -> None:
        content = "\n".join(self.commands).encode("utf-8")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width} {self.height}] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>".encode(
                "utf-8"
            ),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Length {len(content)} >>\nstream\n".encode("utf-8") + content + b"\nendstream",
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, payload in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode("utf-8"))
            pdf.extend(payload)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
        pdf.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
                "utf-8"
            )
        )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf)
