"""
Library Management GUI — UML activity map.

Mapped from current code (do not invent extra screens):
  main.py -> GUIManager.main / readSqlite
  sign_in / sign_up / open_partition
  costumer_request1/2 -> BorrowService.submit_*
  officer_confirm -> ApprovalService.confirm/deny (one SQLite transaction + audit)
  add_officer / issue_rb

Usage (from project root):
  pip install matplotlib
  python scripts/generate_activity_map.py

Writes: activity-map.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "activity-map.png"

# node id -> (x, y, kind, text)
# kind: start | end | action | decision | bar
NODES = {
    "start": (5.5, 18.6, "start", ""),
    "boot": (5.5, 17.6, "action", "启动 main.py\ninit_database / 加载 Users+Books"),
    "gate": (5.5, 16.2, "decision", "已有账号?"),
    "signup": (2.0, 15.0, "action", "Sign-up\nAuthService.register_costumer\n双写内存+SQLite"),
    "signin": (5.5, 15.0, "action", "Sign-in\nAuthService.login\n(明文密码升级兜底)"),
    "auth_ok": (5.5, 13.8, "decision", "凭证通过?"),
    "auth_fail": (8.8, 15.0, "action", "提示错误文案\n停留登录页"),
    "role": (5.5, 12.5, "decision", "user in\ncostumers 名单?"),
    # reader
    "c_ui": (2.0, 11.2, "action", "读者分区 CostumerWindow"),
    "c_browse": (2.0, 10.0, "action", "BookService.list_books\nAvailable / Borrowed / Reserved"),
    "c_kind": (2.0, 8.7, "decision", "操作类型?"),
    "c_br": (0.55, 7.4, "action", "选书: borrow / reserve\ncostumer_request1"),
    "c_rr": (3.45, 7.4, "action", "我的书: renew / return\ncostumer_request2"),
    "c_guard": (2.0, 6.1, "decision", "可提交?\n(限额/已预约/未选行)"),
    "c_pend": (2.0, 4.7, "action", "BorrowService.submit_*\nrequest PENDING 落库\n不改 Books.state"),
    # officer
    "o_ui": (8.8, 11.2, "action", "管理员分区 OfficerWindow"),
    "o_list": (8.8, 10.0, "action", "待办列表 +\n图书筛选 / 添加管理员"),
    "o_kind": (8.8, 8.7, "decision", "管理员动作?"),
    "o_add": (11.2, 7.4, "action", "add_officer\nAuthService.register_officer"),
    "o_pdf": (11.2, 5.8, "action", "issue_rb\n仅 ACCEPTED 的 RETURN\n生成 Receipt/Bill PDF"),
    "o_pick": (8.8, 7.4, "action", "选中一条 request\nconfirm / deny"),
    "o_txn": (8.8, 6.1, "decision", "accept?"),
    "o_yes": (7.2, 4.7, "action", "ApprovalService.confirm\nBEGIN IMMEDIATE\n改书/借阅/预约 + ACCEPTED\n写 audit CONFIRM\n单事务 commit"),
    "o_no": (10.4, 4.7, "action", "ApprovalService.deny\nDENIED + audit DENY\n单事务 commit"),
    "o_reload": (8.8, 3.4, "action", "回滚则提示已处理\n成功则刷新表/列表"),
    "bar": (5.5, 2.4, "bar", ""),
    "end": (5.5, 1.4, "end", "关闭窗口 / 结束"),
}

EDGES = [
    ("start", "boot"),
    ("boot", "gate"),
    ("gate", "signup", "否"),
    ("gate", "signin", "是"),
    ("signup", "signin"),
    ("signin", "auth_ok"),
    ("auth_ok", "auth_fail", "否"),
    ("auth_fail", "signin"),
    ("auth_ok", "role", "是"),
    ("role", "c_ui", "是 · 读者"),
    ("role", "o_ui", "否 · 管理员"),
    ("c_ui", "c_browse"),
    ("c_browse", "c_kind"),
    ("c_kind", "c_br", "借/预约"),
    ("c_kind", "c_rr", "续借/还"),
    ("c_br", "c_guard"),
    ("c_rr", "c_guard"),
    ("c_guard", "c_browse", "否 · 提示"),
    ("c_guard", "c_pend", "是"),
    ("c_pend", "bar"),
    ("o_ui", "o_list"),
    ("o_list", "o_kind"),
    ("o_kind", "o_add", "注册管理员"),
    ("o_kind", "o_pdf", "开收据/账单"),
    ("o_kind", "o_pick", "审批"),
    ("o_add", "o_list"),
    ("o_pdf", "o_list"),
    ("o_pick", "o_txn"),
    ("o_txn", "o_yes", "Confirm"),
    ("o_txn", "o_no", "Deny"),
    ("o_yes", "o_reload"),
    ("o_no", "o_reload"),
    ("o_reload", "bar"),
    ("bar", "end"),
]


def _box(ax, x, y, text, fc, w=2.35, h=0.85):
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        facecolor=fc,
        edgecolor="#1f2937",
        linewidth=1.1,
        zorder=2,
    )
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=7.2, color="#111827", zorder=3)


def _diamond(ax, x, y, text, s=0.72):
    pts = [(x, y + s * 0.72), (x + s, y), (x, y - s * 0.72), (x - s, y)]
    ax.add_patch(
        Polygon(pts, closed=True, facecolor="#FEF3C7", edgecolor="#1f2937", linewidth=1.1, zorder=2)
    )
    ax.text(x, y, text, ha="center", va="center", fontsize=6.6, color="#111827", zorder=3)


def draw():
    fig, ax = plt.subplots(figsize=(14, 18), dpi=160)
    ax.set_xlim(-0.4, 12.6)
    ax.set_ylim(0.6, 19.4)
    ax.axis("off")
    ax.set_title(
        "Library Management GUI — Activity Map",
        fontsize=14,
        pad=8,
        color="#111827",
    )
    ax.text(
        5.5,
        19.15,
        "分区判断用内存名单，不看 type()；Books.state 仅 Available/Borrowed；Reserved 是筛选",
        ha="center",
        fontsize=8,
        color="#4B5563",
    )

    # swimlanes
    ax.add_patch(FancyBboxPatch(( -0.15, 3.85), 4.5, 8.0, boxstyle="round,pad=0.02",
                                facecolor="#EFF6FF", edgecolor="#93C5FD", linewidth=1, zorder=0))
    ax.add_patch(FancyBboxPatch((6.35, 3.85), 5.9, 8.0, boxstyle="round,pad=0.02",
                                facecolor="#F5F3FF", edgecolor="#C4B5FD", linewidth=1, zorder=0))
    ax.text(2.1, 11.72, "Costumer", ha="center", fontsize=9, color="#1D4ED8", fontweight="medium")
    ax.text(8.9, 11.72, "Officer", ha="center", fontsize=9, color="#6D28D9", fontweight="medium")

    centers = {}
    for nid, (x, y, kind, text) in NODES.items():
        centers[nid] = (x, y)
        if kind == "start":
            ax.add_patch(Circle((x, y), 0.16, facecolor="#111827", zorder=3))
        elif kind == "end":
            ax.add_patch(Circle((x, y), 0.22, facecolor="white", edgecolor="#111827", linewidth=2, zorder=3))
            ax.add_patch(Circle((x, y), 0.12, facecolor="#111827", zorder=4))
            ax.text(x, y - 0.42, text, ha="center", fontsize=8, color="#111827")
        elif kind == "decision":
            _diamond(ax, x, y, text)
        elif kind == "bar":
            ax.add_patch(plt.Rectangle((x - 1.6, y - 0.06), 3.2, 0.12, facecolor="#111827", zorder=3))
        else:
            fc = "#DBEAFE" if x < 5 else ("#EDE9FE" if x > 6 else "#E5E7EB")
            if nid in ("boot", "signin", "signup", "auth_fail"):
                fc = "#E5E7EB"
            _box(ax, x, y, text, fc)

    for edge in EDGES:
        a, b = edge[0], edge[1]
        label = edge[2] if len(edge) > 2 else None
        x1, y1 = centers[a]
        x2, y2 = centers[b]
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=10,
                linewidth=0.9,
                color="#374151",
                zorder=1,
                shrinkA=18,
                shrinkB=18,
            )
        )
        if label:
            ax.text((x1 + x2) / 2 + 0.12, (y1 + y2) / 2 + 0.08, label,
                    fontsize=6.2, color="#B45309", zorder=4)

    ax.text(
        5.5,
        0.85,
        "Source: Code/GUIManager.py · service/auth_service.py · borrow_service.py · approval_service.py",
        ha="center",
        fontsize=7,
        color="#6B7280",
    )
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    draw()
