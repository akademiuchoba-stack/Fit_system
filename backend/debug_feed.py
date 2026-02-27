import os
import sys
import json
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
except ImportError:
    print("Ошибка: Установите библиотеку rich (pip install rich)")
    raise

# root -> чтобы работали imports "backend.*"
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from backend import database, models, logic

console = Console()
BASE_DIR = ROOT
USERS_FILE = Path(__file__).resolve().parent / "users.json"


def load_users():
    if not USERS_FILE.exists():
        console.print(f"[red]Файл {USERS_FILE} не найден![/red]")
        sys.exit(1)
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_buyer_from_user(u: dict):
    # buyer measurements are full circumferences; engine does half conversions internally where needed
    return {
        "gender": (u.get("gender") or "male").lower(),
        "measurements": {
            "chest": u.get("chest"),
            "waist_top": u.get("waist_top"),
            "belly": u.get("belly"),
            "hips": u.get("hips"),
            "waist_bottom": u.get("waist_bottom"),
            "high_hip": u.get("high_hip"),
            "thigh": u.get("thigh"),
            "bicep": u.get("bicep"),
            "shoulders": u.get("shoulders"),
            "arm_length": u.get("arm_length"),
            "sleeve": u.get("arm_length"),
            "inseam": u.get("inseam"),
            "outseam": u.get("leg_length"),
        },
        "problem_zones": u.get("problem_zones") or [],
        "comfort_C": u.get("comfort_C") or {},
    }


def fetch_products(db):
    items = (
        db.query(models.Garment)
        .filter(models.Garment.in_stock == True)
        .order_by(models.Garment.id.desc())
        .all()
    )

    out = []
    for g in items:
        metrics = g.metrics or {}
        if isinstance(metrics, dict) and metrics.get("schema_version") == "v3.1" and isinstance(metrics.get("v31"), dict):
            out.append(g)
    return out


def pick_product(products):
    table = Table(title="Товары v3.1 (in_stock)")
    table.add_column("#", style="bold")
    table.add_column("SKU", style="cyan")
    table.add_column("Name")
    table.add_column("Type", style="magenta")
    table.add_column("Sizes", style="green")

    for i, g in enumerate(products, start=1):
        v31 = (g.metrics or {}).get("v31", {})
        prod = v31.get("product", {}) or {}
        table.add_row(
            str(i),
            str(g.sku),
            str(g.name or ""),
            str(prod.get("garment_type") or ""),
            ", ".join((prod.get("available_sizes") or []))
        )
    console.print(table)

    idx = Prompt.ask("Выберите товар (#)", default="1")
    try:
        n = int(idx)
        return products[n - 1]
    except Exception:
        return products[0]


def pick_user(users):
    table = Table(title="Покупатели (users.json)")
    table.add_column("#", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Gender", style="magenta")
    table.add_column("Chest", style="green")
    table.add_column("Belly", style="yellow")
    table.add_column("Hips", style="green")

    for i, u in enumerate(users, start=1):
        table.add_row(
            str(i),
            str(u.get("name", "")),
            str(u.get("gender", "")),
            str(u.get("chest", "")),
            str(u.get("belly", "")),
            str(u.get("hips", "")),
        )
    console.print(table)

    idx = Prompt.ask("Выберите пользователя (#)", default="1")
    try:
        n = int(idx)
        return users[n - 1]
    except Exception:
        return users[0]


def render_result(fit: dict):
    best = fit.get("best_size")
    score = fit.get("score")
    conf = fit.get("confidence")
    mode = fit.get("mode")

    console.print(Panel(f"✅ best_size: [bold]{best}[/bold]\nscore: [bold]{score:.1f}%[/bold]\nconfidence: [bold]{conf:.1f}%[/bold]\nmode: [bold]{mode}[/bold]", title="Итог"))

    allr = fit.get("all_results") or []
    if not allr:
        console.print("[yellow]Нет all_results[/yellow]")
        return

    t = Table(title="X-Ray по размерам")
    t.add_column("Size", style="bold")
    t.add_column("Score", style="green")
    t.add_column("Conf", style="cyan")
    t.add_column("HardFail", style="red")
    t.add_column("Warnings")

    for r in allr:
        t.add_row(
            str(r.get("size_label")),
            f"{float(r.get('score') or 0):.1f}",
            f"{float(r.get('confidence') or 0):.1f}",
            "YES" if r.get("hard_fail") else "no",
            "; ".join((r.get("warnings") or [])[:2]),
        )

    console.print(t)

    # show details for best
    best_node = None
    for r in allr:
        if str(r.get("size_label")) == str(best):
            best_node = r
            break
    if not best_node:
        return

    details = best_node.get("details") or []
    if details:
        dt = Table(title=f"Детали по зонам (size={best})")
        dt.add_column("Zone", style="bold")
        dt.add_column("Body")
        dt.add_column("Garment")
        dt.add_column("Δ")
        dt.add_column("Status")
        dt.add_column("Inferred")

        for d in details:
            dt.add_row(
                str(d.get("label") or d.get("zone") or ""),
                str(d.get("body")),
                str(d.get("garment")),
                str(d.get("delta")),
                str(d.get("status")),
                "yes" if d.get("inferred") else "no",
            )
        console.print(dt)


def main():
    users = load_users()
    if not users:
        console.print("[red]users.json пуст[/red]")
        return

    db = database.SessionLocal()
    try:
        products = fetch_products(db)
        if not products:
            console.print("[red]Нет товаров v3.1 в базе. Сначала создай через Builder или seed_db.py[/red]")
            return

        u = pick_user(users)
        g = pick_product(products)

        buyer = build_buyer_from_user(u)
        v31 = (g.metrics or {}).get("v31")

        console.print(Panel(f"Покупатель: [bold]{u.get('name')}[/bold]\nТовар: [bold]{g.sku}[/bold] — {g.name}", title="Запуск"))

        fit = logic.calculate_fit_v31(buyer, v31)
        render_result(fit)

    finally:
        db.close()


if __name__ == "__main__":
    main()