#!/usr/bin/env python3
"""録画 mp4 の文字起こしユーティリティ（OpenAI Whisper API）.

使い方:
    python3 transcribe.py <recording.mp4>

事前準備:
    - `export OPENAI_API_KEY=sk-...`
    - `pip3 install openai`
    - ffmpeg が PATH にあること（音声抽出・分割に使用）

挙動:
    1. mp4 から ffmpeg で音声を 16kHz mono mp3 に変換
    2. Whisper API の 25MB 上限を超える場合は 10 分チャンクに分割
    3. 各チャンクを Whisper に投げ、時系列に結合
    4. stdout に全文テキストを出力
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WHISPER_LIMIT_BYTES = 24 * 1024 * 1024  # 余裕を見て24MB
CHUNK_SECONDS = 600  # 10分


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"{name} が PATH にありません")


def extract_audio(src: Path, dst: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            str(dst),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def split_audio(src: Path, out_dir: Path) -> list[Path]:
    pattern = out_dir / "chunk_%03d.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-f",
            "segment",
            "-segment_time",
            str(CHUNK_SECONDS),
            "-c",
            "copy",
            str(pattern),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return sorted(out_dir.glob("chunk_*.mp3"))


def transcribe_file(client, path: Path) -> str:
    with open(path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
        )
    return result.text


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 1

    src = Path(argv[0])
    if not src.exists():
        print(f"!! ファイルが見つかりません: {src}", file=sys.stderr)
        return 2

    if not os.environ.get("OPENAI_API_KEY"):
        print("!! OPENAI_API_KEY が未設定です", file=sys.stderr)
        return 3

    try:
        ensure_tool("ffmpeg")
        from openai import OpenAI
    except Exception as e:
        print(f"!! 前提未整備: {e}", file=sys.stderr)
        return 4

    client = OpenAI()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        audio = tmp_dir / "audio.mp3"
        extract_audio(src, audio)

        if audio.stat().st_size <= WHISPER_LIMIT_BYTES:
            chunks = [audio]
        else:
            chunks = split_audio(audio, tmp_dir)

        parts: list[str] = []
        for chunk in chunks:
            parts.append(transcribe_file(client, chunk))

    print("\n".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
