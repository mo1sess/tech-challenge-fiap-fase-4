"""Anima um avatar sintético com articulação 2D determinística.

A arte de referência deve ser sintética, nunca uma fotografia. A arte utilizada
na validação foi gerada por IA. O vídeo MJPEG é submetido ao Pose Landmarker
real; o gerador não injeta resultados de inferência."""
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def create_avatar(source: Path, output: Path, *, abrupt: bool = False):
    image = cv2.imread(str(source))
    if image is None or image.shape[:2] != (1536, 1024):
        raise ValueError("Expected synthetic 1024x1536 A-pose artwork")
    # Os pontos de controle seguem a arte sintética, sem usar previsões do modelo.
    points = np.float32([
        (0, 0), (1023, 0), (1023, 1535), (0, 1535),
        (512, 90), (440, 190), (580, 190), (512, 300),
        (360, 365), (660, 365), (280, 530), (740, 530),
        (170, 710), (850, 710), (110, 820), (910, 820),
        (400, 730), (620, 730), (410, 960), (610, 960),
        (420, 1120), (610, 1120), (400, 1370), (620, 1370),
        (360, 1430), (650, 1430), (512, 530), (512, 810),
    ])
    subdiv = cv2.Subdiv2D((0, 0, 1024, 1536))
    for p in points:
        subdiv.insert(tuple(map(float, p)))
    triangles = []
    for triangle in subdiv.getTriangleList():
        indices = [int(np.argmin(np.linalg.norm(points - p, axis=1))) for p in triangle.reshape(3, 2)]
        if len(set(indices)) == 3:
            triangles.append(indices)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"MJPG"), 12, (960, 864))
    if not writer.isOpened():
        raise RuntimeError("MJPEG encoder unavailable")
    try:
        for frame_index in range(72):
            phase = 2 * math.pi * frame_index / 36
            dest = points.copy()
            # Flexiona cotovelos e joelhos alternadamente e movimenta as mãos.
            for ids, dx, dy in [([10], -12, -15), ([11], 12, -15),
                                ([12, 14], -15, -105), ([13, 15], 15, -105),
                                ([18, 20], -28, -15), ([19, 21], 28, -15)]:
                wave = (1 + math.sin(phase + (math.pi if ids[0] % 2 else 0))) / 2
                dest[ids] += np.float32([dx * wave, dy * wave])
            warped = np.full_like(image, 255)
            for ids in triangles:
                src, dst = points[ids], dest[ids]
                x, y, w, h = cv2.boundingRect(dst)
                matrix = cv2.getAffineTransform(src, np.float32(dst - (x, y)))
                patch = cv2.warpAffine(image, matrix, (w, h), borderValue=(255, 255, 255))
                mask = np.zeros((h, w), np.uint8)
                cv2.fillConvexPoly(mask, np.int32(dst - (x, y)), 255)
                # Vértices na borda podem exceder o retângulo de recorte em um pixel.
                w, h = min(w, 1024 - x), min(h, 1536 - y)
                cv2.copyTo(patch[:h, :w], mask[:h, :w], warped[y:y+h, x:x+w])
            canvas = np.full((864, 960, 3), 255, np.uint8)
            shift = (-120 if frame_index < 36 else 120) if abrupt else int(18 * math.sin(phase))
            canvas[48:816, 224+shift:736+shift] = cv2.resize(warped, (512, 768))
            cv2.putText(canvas, "100% SYNTHETIC AVATAR - EDUCATIONAL TEST", (140, 842), cv2.FONT_HERSHEY_SIMPLEX, .6, (40, 40, 40), 1)
            writer.write(canvas)
    finally:
        writer.release()
    return {"path": str(output), "frames": 72, "fps": 12, "seconds": 6,
            "width": 960, "height": 864, "abrupt_translation": abrupt,
            "provenance": "Arte de avatar gerada por IA; articulação 2D determinística; sem filmagem real"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--abrupt", action="store_true")
    args = parser.parse_args()
    print(json.dumps(create_avatar(args.source, args.output, abrupt=args.abrupt), indent=2))
