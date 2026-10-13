from datetime import datetime as Datetime

from repository.connection import fmt_dt, get_connection


class AuditRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def add(self, user_id, action, target_type=None, target_id=None, detail=None, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        conn.execute(
            """INSERT INTO audit_log(user_id, action, target_type, target_id, detail, created_at)
               VALUES(?,?,?,?,?,?)""",
            [user_id, action, target_type, target_id, detail, fmt_dt(Datetime.now())],
        )
        if close_after:
            conn.commit()
            conn.close()

    def list_by_action(self, action, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        rows = conn.execute(
            "SELECT id, user_id, action, target_type, target_id, detail, created_at FROM audit_log WHERE action=?",
            (action,),
        ).fetchall()
        if close_after:
            conn.close()
        return rows

    def list_recent(self, limit=200, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        try:
            rows = conn.execute(
                """SELECT a.id, a.user_id, u.username, a.action, a.target_type, a.target_id,
                          a.detail, a.created_at
                   FROM audit_log a
                   LEFT JOIN Users u ON u.user_id = a.user_id
                   ORDER BY a.id DESC
                   LIMIT ?""",
                (int(limit) if limit else 200,),
            ).fetchall()
        finally:
            if close_after:
                conn.close()
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "username": row[2],
                "action": row[3],
                "target_type": row[4],
                "target_id": row[5],
                "detail": row[6],
                "created_at": row[7],
            }
            for row in rows
        ]
