import sqlite3
import json
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
except ImportError:
    print("Ошибка: Установите библиотеку rich (pip install rich)")
    sys.exit(1)

# Импортируем нашу математику напрямую
from logic import Profile, calculate_fit, SIZES_ORDER, DESIGN_EASE

console = Console()

# --- УМНЫЕ ПУТИ ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_NAME = BASE_DIR / "shops" / "shop.db"
USERS_FILE = Path(__file__).resolve().parent / "users.json"

def load_users():
    if not USERS_FILE.exists():
        console.print(f"[red]Файл {USERS_FILE} не найден![/red]")
        sys.exit(1)
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_all_products():
    if not DB_NAME.exists():
        console.print(f"[red]База данных {DB_NAME} не найдена.[/red]")
        return []
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT sku, name, metrics, platform FROM garments WHERE in_stock = 1")
    rows = c.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        try:
            metrics = json.loads(row[2]) if row[2] else {}
            products.append({'sku': row[0], 'name': row[1], 'metrics': metrics, 'platform': row[3]})
        except: 
            continue
    return products

def main():
    console.clear()
    console.print(Panel("[bold cyan]FIT SYSTEM: A/B Тестирование (Теория vs Ground Truth)[/bold cyan]", expand=False))

    users_data = load_users()
    products = fetch_all_products()

    if not products:
        console.print("[yellow]В базе нет активных товаров для тестирования.[/yellow]")
        return

    # 1. Выбор пользователя
    console.print("\n[bold]Доступные профили:[/bold]")
    for idx, u in enumerate(users_data):
        console.print(f"[{idx}] {u['name']} (Рост: {u['height']}, Грудь: {u['chest']})")
    
    u_idx = Prompt.ask("\nВыберите номер пользователя", default="0")
    try:
        u_data = users_data[int(u_idx)]
    except (ValueError, IndexError):
        console.print("[red]Неверный выбор![/red]")
        return

    user = Profile(
        height=float(u_data.get('height', 175)),
        chest=float(u_data.get('chest', 100)),
        waist=float(u_data.get('waist', 85)),
        hips=float(u_data.get('hips', 100)),
        shoulders=float(u_data.get('shoulders', 45)),
        arm_length=float(u_data.get('arm_length', 62)),
        outseam=float(u_data.get('leg_length', 105)),
        inseam=float(u_data.get('inseam', 80))
    )

    console.print(f"\n[bold green]✅ Выбран пользователь: {u_data['name']}[/bold green]")

    # 2. Перебор товаров
    for item in products:
        metrics = item['metrics']
        if not metrics: continue
        
        theory = metrics.get('theory', {})
        ground_truth = metrics.get('ground_truth', {})

        if not theory: continue

        cat_type = theory.get('category_type', 'top')
        fit_profile = theory.get('fit_profile', 'regular')
        elastane = theory.get('elastane_pct', 0)
        model_size = theory.get('model_size', 'M')

        console.print("\n" + "="*70)
        console.print(f"[bold cyan]ТОВАР:[/bold cyan] {item['name']} (SKU: {item['sku']} | {item['platform'].upper()})")
        console.print(f"[dim]Категория: {cat_type.upper()}, Силуэт: {fit_profile.upper()}, Эластан: {elastane}%[/dim]")

        # ==========================================
        # РАСЧЕТ А: ТЕОРИЯ (По данным с сайта)
        # ==========================================
        console.print("\n[bold magenta]--- РАСЧЕТ А: ПО ДАННЫМ МАГАЗИНА (ТЕОРИЯ) ---[/bold magenta]")
        best_theory_score = -1
        best_theory_size = None
        
        for target_size in ['S', 'M', 'L', 'XL', 'XXL']:
            res = calculate_fit(user, model_size, theory, target_size)
            if res.score > best_theory_score:
                best_theory_score = res.score
                best_theory_size = target_size
            
            # Выводим только более-менее подходящие размеры для краткости
            if res.score > 30:
                console.print(f"   [bold {res.status_color}]Размер {target_size:<3}[/bold {res.status_color}] | Оценка: {res.score:>3.0f}% | {res.status}")
                if res.score > 60:
                    for warn in res.warnings:
                        console.print(f"      [yellow]! {warn}[/yellow]")

        console.print(f"   [bold]Вывод алгоритма (Теория):[/bold] Рекомендуемый размер [magenta]{best_theory_size}[/magenta] ({best_theory_score:.0f}%)")

        # ==========================================
        # РАСЧЕТ Б: GROUND TRUTH (Реальные замеры)
        # ==========================================
        console.print("\n[bold green]--- РАСЧЕТ Б: ПО РЕАЛЬНЫМ ЗАМЕРАМ РУЛЕТКОЙ ---[/bold green]")
        
        if not ground_truth:
            console.print("   [dim]Реальных замеров для этой вещи пока нет.[/dim]")
            continue

        ideal_ease = DESIGN_EASE.get(fit_profile.lower(), DESIGN_EASE['regular'])
        base_ease_chest = ideal_ease['top'] if cat_type.lower() == 'top' else ideal_ease['bottom']
        base_ease_waist = ideal_ease['bottom']
        base_ease_hips = ideal_ease['bottom']

        best_gt_score = -1
        best_gt_size = None

        for gt_size, gt_meas in ground_truth.items():
            # Реверс-инжиниринг: создаем "fake" модель, которая по габаритам 
            # идеально совпадает с замером рулетки.
            fake_base_data = {
                'category_type': cat_type,
                'fit_profile': fit_profile,
                'elastane_pct': elastane,
                'height': theory.get('height', 175.0), 
            }
            if 'chest' in gt_meas: fake_base_data['chest'] = gt_meas['chest'] - base_ease_chest
            if 'waist' in gt_meas: fake_base_data['waist'] = gt_meas['waist'] - base_ease_waist
            if 'hips' in gt_meas: fake_base_data['hips'] = gt_meas['hips'] - base_ease_hips
            if 'inseam' in gt_meas: fake_base_data['inseam'] = gt_meas['inseam']

            # Считаем посадку (target_size == model_size, чтобы отключить грейдирование)
            res = calculate_fit(user, gt_size, fake_base_data, gt_size)

            if res.score > best_gt_score:
                best_gt_score = res.score
                best_gt_size = gt_size

            console.print(f"   [bold {res.status_color}]Реальный {gt_size:<3}[/bold {res.status_color}] | Оценка: {res.score:>3.0f}% | {res.status}")
            
            # Выводим конкретику, почему оценка такая
            for zone, txt in res.details.items():
                # Убираем rich-теги из txt для красивого вывода
                clean_txt = txt.replace('[green]', '').replace('[/green]', '')\
                               .replace('[yellow]', '').replace('[/yellow]', '')\
                               .replace('[red]', '').replace('[/red]', '')\
                               .replace('[magenta]', '').replace('[/magenta]', '')
                console.print(f"      - {zone}: {clean_txt}")

        console.print(f"   [bold]Истинный размер (по рулетке):[/bold] [green]{best_gt_size}[/green] ({best_gt_score:.0f}%)")

        # АНАЛИТИЧЕСКИЙ ВЫВОД
        if best_theory_size and best_gt_size:
            if best_theory_size == best_gt_size:
                console.print("\n   [bold bg green text white] ИТОГ: ДАННЫЕ МАГАЗИНА ТОЧНЫ. АЛГОРИТМ СОВПАЛ. [/bold bg green text white]")
            else:
                console.print(f"\n   [bold bg red text white] ИТОГ: ОШИБКА ДАННЫХ МАГАЗИНА! [/bold bg red text white]")
                console.print(f"   Магазин продает это как '{best_theory_size}', но по реальным меркам это '{best_gt_size}'.")

    console.print("\n" + "="*70)
    console.print("[bold green]Тестирование завершено.[/bold green]\n")

if __name__ == "__main__":
    main()