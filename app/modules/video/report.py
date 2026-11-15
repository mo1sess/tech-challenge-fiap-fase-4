from typing import Any


def format_video_interval(interval: dict[str, Any]) -> str:
    first, last = interval["first_frame"] + 1, interval["last_frame"] + 1
    frames = f"quadro {first}" if first == last else f"quadros {first}–{last}"
    start, end = interval["start_seconds"], interval["end_seconds"]
    if start is None or end is None:
        return frames
    times = f"{start:g} s" if first == last else f"{start:g}–{end:g} s"
    return f"{times} ({frames})"


def build_video_report(analysis: dict[str, Any], filename: str, job_id: str) -> str:
    anomalies = analysis["anomalies"]
    duration = analysis["duration_seconds"]
    lines = [
        "MedGuard AI | Relatório de desvios em vídeo sintético",
        f"Arquivo: {' '.join(filename.splitlines())}",
        f"Job: {job_id}",
        "",
        f"Quadros analisados: {analysis['analyzed_frame_count']} "
        f"(um a cada {analysis['sample_every_n_frames']})",
        f"Duração estimada do arquivo: {f'{duration:g} s' if duration else 'indisponível'}",
        f"Movimento médio: {analysis['mean_motion_percent']:g}%",
        f"Pico de mudança visual: {analysis['peak_motion_percent']:g}%",
    ]
    coverage = analysis.get("coverage")
    if coverage:
        lines.append(f"Trecho amostrado: {format_video_interval(coverage['sampled_interval'])}")
        if coverage["sample_limit_reached"]:
            lines.append("Limite de amostragem atingido. O restante do vídeo pode não ter sido avaliado.")

    pose = analysis.get("pose_analysis")
    if pose:
        lines.extend(["", f"Modelos de postura: {', '.join(pose['models'])}"])
        if pose["status"] == "unavailable":
            reasons = {
                "model_files_missing": "arquivos dos modelos ausentes",
                "model_load_failed": "falha ao carregar os modelos",
                "model_inference_failed": "falha durante a inferência",
            }
            lines.append(f"Análise de postura indisponível: {reasons[pose['reason']]}.")
        else:
            lines.append(
                f"Quadros comparáveis: {pose['comparable_frames']} de {len(pose['samples'])} amostras de postura."
            )
            if pose["status"] == "insufficient_evidence":
                lines.append("Nenhuma amostra apresentou evidência suficiente dos dois modelos.")
        lines.append(
            f"Limite demonstrativo: {pose['threshold_degrees']:g}° de inclinação do tronco "
            "em relação à vertical da imagem."
        )
        for sample in pose["samples"]:
            if sample["status"] in {"deviation", "within_threshold", "disagreement"}:
                lines.append(
                    f"Quadro {sample['frame'] + 1}: OpenPose {sample['openpose_degrees']:g}°, "
                    f"YOLOv8 Pose {sample['yolov8_degrees']:g}°"
                    f"{' (sem consenso)' if sample['status'] == 'disagreement' else ''}."
                )

    lines.extend(["", f"Desvios detectados no trecho analisado: {len(anomalies)}"])
    for anomaly in anomalies:
        unit = "%" if anomaly["unit"] == "percent_changed_pixels" else "°"
        lines.extend([
            f"- {anomaly['title']}",
            f"  {anomaly['description']}",
            f"  Valor observado: {anomaly['observed_value']:g}{unit}. "
            f"Limite da regra: {anomaly['threshold']:g}{unit}.",
        ])
        lines.extend(f"  Trecho: {format_video_interval(interval)}" for interval in anomaly.get("intervals", []))
    lines.extend(["", analysis["disclaimer"], ""])
    return "\n".join(lines)
