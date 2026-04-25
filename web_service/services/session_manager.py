"""
Session Manager
Manages upload sessions and video frame extraction
"""
import os
import uuid
import cv2
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from web_service.config import SESSION_DIR, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


class SessionData:
    """Data structure for a session"""
    def __init__(self, session_id: str, session_dir: Path):
        self.id = session_id
        self.dir = session_dir
        self.files: List[Dict] = []
        self.frames: Dict[str, List[str]] = {}
        self.created_at = datetime.now()


class SessionManager:
    """Manages upload sessions"""

    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}

    def create_session(self) -> str:
        """Create a new upload session"""
        session_id = str(uuid.uuid4())
        session_dir = SESSION_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        self.sessions[session_id] = SessionData(session_id, session_dir)
        return session_id

    def create_session_with_id(self, session_id: str) -> str:
        """Create a session with a specific ID"""
        session_dir = SESSION_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        self.sessions[session_id] = SessionData(session_id, session_dir)
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its files"""
        session = self.sessions.pop(session_id, None)
        if session:
            shutil.rmtree(session.dir, ignore_errors=True)
            return True
        return False

    def add_file(self, session_id: str, filename: str, content: bytes) -> Dict:
        """Save uploaded file to session directory"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        file_path = session.dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        file_type = self._get_file_type(filename)
        file_info = {
            "name": filename,
            "path": str(file_path),
            "type": file_type,
            "size": len(content)
        }
        session.files.append(file_info)

        return file_info

    def _get_file_type(self, filename: str) -> str:
        """Determine file type from extension"""
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return "image"
        elif ext in VIDEO_EXTENSIONS:
            return "video"
        return "unknown"

    def extract_video_frames(
        self,
        session_id: str,
        video_path: str,
        frame_interval: int = 1
    ) -> List[str]:
        """Extract frames from video file"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        frames_dir = session.dir / "frames" / Path(video_path).stem
        frames_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        frame_paths = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                frame_path = frames_dir / f"frame_{frame_idx:06d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                frame_paths.append(str(frame_path))

            frame_idx += 1

        cap.release()

        # Cache frame paths for session
        session.frames[video_path] = frame_paths

        return frame_paths

    def get_files(self, session_id: str) -> List[Dict]:
        """Get all files in a session"""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.files

    def get_images(self, session_id: str) -> List[Dict]:
        """Get only image files in a session"""
        return [f for f in self.get_files(session_id) if f["type"] == "image"]

    def get_videos(self, session_id: str) -> List[Dict]:
        """Get only video files in a session"""
        return [f for f in self.get_files(session_id) if f["type"] == "video"]


# Global session manager instance
session_manager = SessionManager()
