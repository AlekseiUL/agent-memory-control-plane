from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .policy import load_policy


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def emit(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


class PolicyDenied(RuntimeError):
    pass


class NotFound(RuntimeError):
    pass


@dataclass
class ControlPlane:
    db_path: Path
    policy_name: str = "default"

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)
        self.policy = load_policy(self.policy_name)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def init(self) -> dict:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        ddl = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,kind TEXT NOT NULL,owner TEXT NOT NULL,scope TEXT NOT NULL,writeback_target TEXT NOT NULL,priority INTEGER NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY AUTOINCREMENT,key TEXT NOT NULL,content TEXT NOT NULL,class_name TEXT NOT NULL,source_id TEXT NOT NULL,owner TEXT NOT NULL,scope TEXT NOT NULL,confidence REAL NOT NULL,status TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(source_id) REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,key TEXT NOT NULL,content TEXT NOT NULL,class_name TEXT NOT NULL,source_id TEXT NOT NULL,owner TEXT NOT NULL,scope TEXT NOT NULL,confidence REAL NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,supersedes INTEGER,FOREIGN KEY(source_id) REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY AUTOINCREMENT,candidate_id INTEGER NOT NULL,record_id INTEGER NOT NULL,signal TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,actor TEXT NOT NULL,object_type TEXT NOT NULL,object_id TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(content,key,content='records',content_rowid='id');
"""
        with self.connect() as con:
            con.executescript(ddl)
            con.execute("INSERT OR REPLACE INTO settings VALUES('local_only','true')")
            con.execute("INSERT OR REPLACE INTO settings VALUES('llm_write','false')")
            for source in self.policy["sources"]:
                con.execute(
                    "INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?)",
                    (
                        source["id"], source["kind"], source["owner"],
                        source["scope"], source["writeback_target"],
                        source["priority"], now(),
                    ),
                )
        return {"status": "initialized", "database": self.db_path.name, "local_only": True, "llm_write": False}

    def _audit(self, con, event, actor, object_type, object_id, detail) -> None:
        con.execute(
            "INSERT INTO audit_log(event,actor,object_type,object_id,detail,created_at) VALUES(?,?,?,?,?,?)",
            (event, actor, object_type, str(object_id), json.dumps(detail, sort_keys=True), now()),
        )

    def classify(self, content: str, declared_class: str | None = None) -> dict:
        low = content.lower()
        forbidden = [p for p in self.policy["forbidden_patterns"] if re.search(p, content, re.I)]
        if forbidden:
            return {"allowed": False, "class": "forbidden", "reason": "forbidden_pattern", "signals": len(forbidden), "mutation": False}
        if declared_class in self.policy["classes"]:
            class_name, reason = declared_class, "declared_class"
        elif any(x in low for x in ("temporary", "task status", "runtime event")):
            class_name, reason = "non_memory", "ephemeral_evidence"
        elif any(x in low for x in ("procedure", "runbook", "step ")):
            class_name, reason = "procedure", "procedural_signal"
        elif any(x in low for x in ("team policy", "governance", "must ")):
            class_name, reason = "team_policy", "policy_signal"
        else:
            class_name, reason = "stable_fact", "stable_default"
        return {
            "allowed": class_name not in self.policy["non_memory_classes"],
            "class": class_name,
            "reason": reason,
            "writeback_target": self.policy["routing"][class_name],
            "mutation": False,
        }

    def propose(self, key: str, content: str, source_id: str, owner: str, scope: str,
                confidence: float = 0.8, class_name: str | None = None,
                actor: str = "contributor", apply: bool = False) -> dict:
        result = self.classify(content, class_name)
        result.update({"key": key, "source_id": source_id, "owner": owner, "scope": scope, "confidence": confidence, "dry_run": not apply})
        if not result["allowed"]:
            return result
        with self.connect() as con:
            source = con.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            if not source:
                raise NotFound(f"unknown source: {source_id}")
            if scope not in self.policy["scopes"]:
                raise PolicyDenied("unknown scope")
            if not 0 <= confidence <= 1:
                raise PolicyDenied("confidence outside 0..1")
            if not apply:
                return result
            cur = con.execute(
                "INSERT INTO candidates(key,content,class_name,source_id,owner,scope,confidence,status,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (key, content, result["class"], source_id, owner, scope, confidence, "proposed", result["reason"], now()),
            )
            result.update({"candidate_id": cur.lastrowid, "dry_run": False})
            self._audit(con, "candidate_proposed", actor, "candidate", cur.lastrowid, {"key": key, "scope": scope})
        return result

    def promote(self, candidate_id: int, reviewer: str = "reviewer", apply: bool = False) -> dict:
        with self.connect() as con:
            candidate = con.execute(
                "SELECT c.*,s.priority FROM candidates c JOIN sources s ON s.id=c.source_id WHERE c.id=?",
                (candidate_id,),
            ).fetchone()
            if not candidate:
                raise NotFound("candidate not found")
            if candidate["status"] != "proposed":
                raise PolicyDenied("candidate is not promotable")
            if reviewer not in self.policy["promotion"]["reviewer_roles"]:
                raise PolicyDenied("reviewer role denied")
            current = con.execute(
                "SELECT r.*,s.priority FROM records r JOIN sources s ON s.id=r.source_id WHERE r.key=? AND r.status='active' ORDER BY s.priority DESC,r.id DESC LIMIT 1",
                (candidate["key"],),
            ).fetchone()
            receipt = {"candidate_id": candidate_id, "reviewer": reviewer, "dry_run": not apply, "decision": "promote", "supersedes": None, "conflict_id": None, "timestamp": now()}
            if current and current["content"] != candidate["content"] and candidate["priority"] < current["priority"]:
                receipt.update({"decision": "conflict", "reason": "lower_priority_cannot_override"})
                if apply:
                    cur = con.execute(
                        "INSERT INTO conflicts(candidate_id,record_id,signal,status,created_at) VALUES(?,?,?,?,?)",
                        (candidate_id, current["id"], receipt["reason"], "open", now()),
                    )
                    receipt["conflict_id"] = cur.lastrowid
                    self._audit(con, "promotion_blocked", reviewer, "candidate", candidate_id, receipt)
                return receipt
            if current:
                receipt["supersedes"] = current["id"]
            if not apply:
                return receipt
            if current:
                con.execute("UPDATE records SET status='superseded' WHERE id=?", (current["id"],))
                con.execute("DELETE FROM records_fts WHERE rowid=?", (current["id"],))
            cur = con.execute(
                "INSERT INTO records(key,content,class_name,source_id,owner,scope,confidence,status,updated_at,supersedes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (candidate["key"], candidate["content"], candidate["class_name"], candidate["source_id"], candidate["owner"], candidate["scope"], candidate["confidence"], "active", now(), receipt["supersedes"]),
            )
            record_id = cur.lastrowid
            con.execute("INSERT INTO records_fts(rowid,content,key) VALUES(?,?,?)", (record_id, candidate["content"], candidate["key"]))
            con.execute("UPDATE candidates SET status='promoted' WHERE id=?", (candidate_id,))
            receipt.update({"record_id": record_id, "dry_run": False})
            self._audit(con, "candidate_promoted", reviewer, "record", record_id, receipt)
            return receipt

    def _scope_allowed(self, actor: str, scope: str) -> bool:
        return scope in self.policy["access"].get(actor, [])

    def search(self, query: str, actor: str = "public_reader", limit: int = 10) -> list[dict]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT r.*,s.writeback_target FROM records_fts f JOIN records r ON r.id=f.rowid JOIN sources s ON s.id=r.source_id WHERE records_fts MATCH ? AND r.status='active' LIMIT ?",
                (query, limit),
            ).fetchall()
            results = []
            for row in rows:
                if not self._scope_allowed(actor, row["scope"]):
                    continue
                conflicts = con.execute("SELECT COUNT(*) FROM conflicts WHERE record_id=? AND status='open'", (row["id"],)).fetchone()[0]
                results.append({
                    "record_id": row["id"], "key": row["key"], "content": row["content"],
                    "source": row["source_id"], "owner": row["owner"], "scope": row["scope"],
                    "confidence": row["confidence"], "updated_at": row["updated_at"],
                    "retrieval_reason": "fts5_match", "writeback_target": row["writeback_target"],
                    "conflict_signal": bool(conflicts), "staleness_signal": False,
                })
            return results

    def explain(self, record_id: int, actor: str = "public_reader") -> dict:
        with self.connect() as con:
            row = con.execute("SELECT r.*,s.writeback_target FROM records r JOIN sources s ON s.id=r.source_id WHERE r.id=?", (record_id,)).fetchone()
            if not row:
                raise NotFound("record not found")
            if not self._scope_allowed(actor, row["scope"]):
                raise PolicyDenied("scope denied")
            conflicts = con.execute("SELECT COUNT(*) FROM conflicts WHERE record_id=? AND status='open'", (record_id,)).fetchone()[0]
            return {"record_id": record_id, "source": row["source_id"], "owner": row["owner"], "scope": row["scope"], "confidence": row["confidence"], "updated_at": row["updated_at"], "retrieval_reason": "canonical_active_record", "writeback_target": row["writeback_target"], "conflict_signal": bool(conflicts), "staleness_signal": False, "supersedes": row["supersedes"]}

    def conflicts(self) -> list[dict]:
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM conflicts ORDER BY id")]

    def source_get(self, source_id: str) -> dict:
        with self.connect() as con:
            row = con.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            if not row:
                raise NotFound("source not found")
            return dict(row)

    def audit(self) -> dict:
        with self.connect() as con:
            counts = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("sources", "candidates", "records", "conflicts", "audit_log")}
            return {"status": "ok", "counts": counts, "database": self.db_path.name}

    def doctor(self) -> dict:
        checks = {"database_exists": self.db_path.exists(), "local_only": False, "llm_write_disabled": False, "fts5": False, "policy_loaded": bool(self.policy)}
        if checks["database_exists"]:
            with self.connect() as con:
                values = dict(con.execute("SELECT key,value FROM settings"))
                checks["local_only"] = values.get("local_only") == "true"
                checks["llm_write_disabled"] = values.get("llm_write") == "false"
                try:
                    con.execute("SELECT count(*) FROM records_fts").fetchone()
                    checks["fts5"] = True
                except sqlite3.DatabaseError:
                    pass
        return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
