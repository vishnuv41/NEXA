from typing import Dict, List, Optional, Any, Deque
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib
import logging

from app.config import get_settings
from app.database import get_db_context
from app.models import Session, RequestEvent

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SessionState:
    """In-memory session state for real-time analysis."""
    session_key: str
    source_ip: str
    user_identifier: Optional[str]
    requests: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    risk_timeline: List[Dict[str, Any]] = field(default_factory=list)
    endpoint_sequence: List[str] = field(default_factory=list)
    distinct_endpoints: set = field(default_factory=set)
    distinct_object_ids: set = field(default_factory=set)
    status_codes: List[int] = field(default_factory=list)
    request_times: List[datetime] = field(default_factory=list)
    auth_state: str = "unauthenticated"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)


class SessionAnalyzer:
    """Analyzes session behavior for anomalies."""

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.max_sessions = 10000
        self.cleanup_interval = settings.session_cleanup_interval

    def _get_session_key(self, source_ip: str, session_id: Optional[str], user_id: Optional[str]) -> str:
        """Generate session key."""
        if session_id:
            return session_id
        if user_id:
            return f"user:{user_id}"
        return f"ip:{source_ip}"

    async def analyze(
        self,
        request: Dict[str, Any],
        risk_score: float,
        decision: str,
    ) -> Dict[str, Any]:
        """Analyze request in session context."""
        session_key = self._get_session_key(
            request.get("source_ip", ""),
            request.get("session_id"),
            request.get("user_id"),
        )

        # Get or create session state
        if session_key not in self.sessions:
            await self._load_session_from_db(session_key, request)

        session = self.sessions.get(session_key)
        if not session:
            session = SessionState(
                session_key=session_key,
                source_ip=request.get("source_ip", ""),
                user_identifier=request.get("user_id"),
            )
            self.sessions[session_key] = session

        # Update session with new request
        self._update_session(session, request, risk_score, decision)

        # Calculate session anomaly score
        session_score, reasons = self._calculate_session_score(session)

        # Persist to database periodically
        if len(session.requests) % 10 == 0:
            await self._persist_session(session)

        return {
            "session_id": session_key,
            "session_score": session_score,
            "reasons": reasons,
            "request_count": len(session.requests),
            "risk_timeline": session.risk_timeline[-20:],  # Last 20
        }

    def _update_session(
        self,
        session: SessionState,
        request: Dict[str, Any],
        risk_score: float,
        decision: str,
    ) -> None:
        """Update session with new request."""
        now = datetime.utcnow()
        session.last_seen = now

        req_info = {
            "timestamp": now.isoformat(),
            "method": request.get("method"),
            "path": request.get("path"),
            "risk_score": risk_score,
            "decision": decision,
            "status_code": request.get("status_code"),
        }
        session.requests.append(req_info)

        # Track endpoint sequence
        endpoint = f"{request.get('method')} {request.get('path')}"
        session.endpoint_sequence.append(endpoint)
        session.distinct_endpoints.add(endpoint)

        # Extract object IDs from path (e.g., /users/123 -> 123)
        import re
        ids = re.findall(r"/(\d+)(?:/|$)", request.get("path", ""))
        for id_val in ids:
            session.distinct_object_ids.add(id_val)

        # Track status codes
        if request.get("status_code"):
            session.status_codes.append(request.get("status_code"))

        # Track request timing
        session.request_times.append(now)

        # Update risk timeline
        session.risk_timeline.append({
            "timestamp": now.isoformat(),
            "risk_score": risk_score,
            "decision": decision,
            "endpoint": endpoint,
        })

        # Track auth state transitions
        path = request.get("path", "")
        if "/login" in path and request.get("method") == "POST":
            session.auth_state = "authenticating"
        elif "/dashboard" in path or "/account" in path:
            session.auth_state = "authenticated"

    def _calculate_session_score(self, session: SessionState) -> tuple[float, List[str]]:
        """Calculate session anomaly score."""
        reasons = []
        scores = []

        # 1. Request frequency analysis
        if len(session.request_times) >= 5:
            recent = session.request_times[-5:]
            time_span = (recent[-1] - recent[0]).total_seconds()
            if time_span > 0:
                rate = len(recent) / time_span
                if rate > 10:  # More than 10 req/sec
                    scores.append(0.8)
                    reasons.append(f"High request rate: {rate:.1f} req/s")
                elif rate > 5:
                    scores.append(0.5)
                    reasons.append(f"Elevated request rate: {rate:.1f} req/s")

        # 2. Distinct object ID enumeration
        if len(session.distinct_object_ids) > 20:
            scores.append(0.9)
            reasons.append(f"Object ID enumeration: {len(session.distinct_object_ids)} distinct IDs")
        elif len(session.distinct_object_ids) > 10:
            scores.append(0.6)
            reasons.append(f"Multiple object IDs accessed: {len(session.distinct_object_ids)}")

        # 3. Endpoint diversity
        if len(session.distinct_endpoints) > 15:
            scores.append(0.7)
            reasons.append(f"High endpoint diversity: {len(session.distinct_endpoints)} endpoints")

        # 4. Sequential enumeration pattern
        if self._detect_sequential_enumeration(session):
            scores.append(0.85)
            reasons.append("Sequential resource enumeration detected")

        # 5. Authentication anomalies
        if session.auth_state == "unauthenticated" and any(
            "/dashboard" in r["path"] or "/account" in r["path"] or "/admin" in r["path"]
            for r in session.requests
        ):
            scores.append(0.75)
            reasons.append("Access to authenticated endpoints without login")

        # 6. Status code patterns (many 4xx/5xx)
        if session.status_codes:
            error_rate = sum(1 for c in session.status_codes if c >= 400) / len(session.status_codes)
            if error_rate > 0.5:
                scores.append(0.7)
                reasons.append(f"High error rate: {error_rate:.0%}")

        # 6. Risk escalation
        if len(session.risk_timeline) >= 3:
            recent_risks = [r["risk_score"] for r in session.risk_timeline[-3:]]
            if all(r > 0.5 for r in recent_risks):
                scores.append(0.8)
                reasons.append("Sustained high risk across requests")
            elif recent_risks[-1] > recent_risks[0] + 0.3:
                scores.append(0.6)
                reasons.append("Rapid risk escalation")

        # Calculate final score
        if not scores:
            return 0.0, []

        # Weighted combination
        final_score = max(scores)
        if len(scores) > 1:
            final_score = min(1.0, final_score * 1.15)

        return round(final_score, 3), reasons

    def _detect_sequential_enumeration(self, session: SessionState) -> bool:
        """Detect sequential ID enumeration pattern."""
        if len(session.endpoint_sequence) < 5:
            return False

        # Check last 10 requests for sequential pattern
        recent = session.endpoint_sequence[-10:]
        paths = [e.split(" ", 1)[1] if " " in e else e for e in recent]

        # Look for pattern like /users/1, /users/2, /users/3
        import re
        base_paths = {}
        for path in paths:
            match = re.match(r"^(.+/)(\d+)$", path)
            if match:
                base, num = match.groups()
                if base not in base_paths:
                    base_paths[base] = []
                base_paths[base].append(int(num))

        for base, nums in base_paths.items():
            if len(nums) >= 5:
                # Check if mostly sequential
                diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
                if all(d == 1 for d in diffs) or sum(1 for d in diffs if d == 1) >= len(diffs) * 0.8:
                    return True
        return False

    async def _load_session_from_db(self, session_key: str, request: Dict[str, Any]) -> None:
        """Load session from database."""
        try:
            async with get_db_context() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Session).where(Session.session_key == session_key)
                )
                db_session = result.scalar_one_or_none()
                if db_session:
                    session = SessionState(
                        session_key=db_session.session_key,
                        source_ip=db_session.source_ip,
                        user_identifier=db_session.user_identifier,
                        created_at=db_session.started_at,
                    )
                    if db_session.endpoint_sequence:
                        session.endpoint_sequence = db_session.endpoint_sequence
                        session.distinct_endpoints = set(db_session.endpoint_sequence)
                    if db_session.risk_timeline:
                        session.risk_timeline = db_session.risk_timeline
                    self.sessions[session_key] = session
        except Exception as e:
            logger.debug(f"Could not load session from DB: {e}")

    async def _persist_session(self, session: SessionState) -> None:
        """Persist session to database."""
        try:
            async with get_db_context() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Session).where(Session.session_key == session.session_key)
                )
                db_session = result.scalar_one_or_none()

                if not db_session:
                    db_session = Session(
                        session_key=session.session_key,
                        source_ip=session.source_ip,
                        user_identifier=session.user_identifier,
                    )
                    db.add(db_session)

                db_session.last_seen_at = session.last_seen
                db_session.request_count = len(session.requests)
                db_session.anomaly_score = self._calculate_session_score(session)[0]
                db_session.current_state = session.auth_state
                db_session.endpoint_count = len(session.distinct_endpoints)
                db_session.endpoint_sequence = session.endpoint_sequence[-100:]
                db_session.risk_timeline = session.risk_timeline[-100:]

                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")

    def get_session(self, session_key: str) -> Optional[SessionState]:
        """Get session state."""
        return self.sessions.get(session_key)

    def cleanup_old_sessions(self) -> int:
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired = [
            k for k, v in self.sessions.items()
            if (now - v.last_seen).total_seconds() > settings.session_ttl_seconds
        ]
        for k in expired:
            del self.sessions[k]
        return len(expired)


# Singleton
_session_analyzer: Optional[SessionAnalyzer] = None


def get_session_analyzer() -> SessionAnalyzer:
    global _session_analyzer
    if _session_analyzer is None:
        _session_analyzer = SessionAnalyzer()
    return _session_analyzer