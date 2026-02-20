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
from logic import Profile, calculate_fit, SIZES_ORDER

console = Console()

# --- УМНЫЕ ПУТИ ---
# Вычисляем корень проекта (на один уровень выше папки backend)
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
        console.print(f"[red]База данных {DB_NAME} не найдена. Добавьте товары через Builder.[/red]")
        return []
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT sku, name, metrics FROM garments WHERE in_stock = 1")
    rows = c.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        try:
            metrics = json.loads(row[2]) if row[2] else {}
            products.append({'sku': row[0], 'name': row[1], 'metrics': metrics})
        except: 
            continue
    return products

# --- ЛОГИКА ИЗВЛЕЧЕНИЯ ДАННЫХ (как в main.py) ---
def get_best_value(field, metrics, is_biometry=False):
    main_key = None
    for k in metrics.keys():
        if k not in ['size_chart', 'sources'] and isinstance(metrics[k], dict):
            main_key = k
            break
            
    if not main_key: return None
    work_zone = metrics[main_key]
    
    sources = [work_zone]
    if is_biometry:
        sources = [work_zone.get('model_metrics', {})]

    for src in sources:
        if not isinstance(src, dict): continue
        val = src.get(field)
        if val:
            if is_biometry or field == 'elastane_pct':
                try: return float(val)
                except: pass
            else:
                return str(val)
    return None

def extract_smart_model(metrics: dict):
    model_size = get_best_value('model_size', metrics) or 'M'
    smart_data = {
        'chest': get_best_value('chest', metrics, True) or 90.0,
        'waist': get_best_value('waist', metrics, True) or 70.0,
        'hips': get_best_value('hips', metrics, True) or 95.0,
        'height': get_best_value('height', metrics, True) or 175.0,
        'fit_profile': get_best_value('fit_profile', metrics) or 'regular',
        'category_type': get_best_value('category_type', metrics) or 'top',
        'elastane_pct': get_best_value('elastane_pct', metrics) or 0.0,
    }
    return model_size, smart_data


def main():
    console.clear()
    console.print(Panel("[bold cyan]FIT SYSTEM: Локальный полигон тестирования ядра[/bold cyan]", expand=False))

    users_data = load_users()
    products = fetch_all_products()

    if not products:
        console.print("[yellow]В базе нет активных товаров для тестирования.[/yellow]")
        return

    # 1. Выбор пользователя
    console.print("\n[bold]Доступные пользователи:[/bold]")
    for idx, u in enumerate(users_data):
        console.print(f"[{idx}] {u['name']} (Рост: {u['height']}, Грудь: {u['chest']})")
    
    u_idx = Prompt.ask("\nВыберите номер пользователя", default="0")
    try:
        u_data = users_data[int(u_idx)]
    except (ValueError, IndexError):
        console.print("[red]Неверный выбор![/red]")
        return

    # Собираем профиль пользователя под формат logic.Profile
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
        if not metrics:
            continue
            
        model_size, base_data = extract_smart_model(metrics)
        cat_type = base_data['category_type']

        console.print("\n" + "="*60)
        console.print(f"[bold cyan]ТОВАР:[/bold cyan] {item['name']} (SKU: {item['sku']})")
        console.print(f"[dim]Силуэт: {base_data['fit_profile']}, Эластан: {base_data['elastane_pct']}%[/dim]")

        console.print("\n[bold]1. АНАТОМИЯ (БАЗА):[/bold]")
        if cat_type == 'bottom':
            console.print(f"   Модель (НИЗ): Размер {model_size}, Рост {base_data['height']}, Талия {base_data['waist']}, Бедра {base_data['hips']}")
            console.print(f"   Покупатель: Рост {user.height}, Талия {user.waist}, Бедра {user.hips}")
        else:
            console.print(f"   Модель (ВЕРХ): Размер {model_size}, Рост {base_data['height']}, Грудь {base_data['chest']}, Талия {base_data['waist']}")
            console.print(f"   Покупатель: Рост {user.height}, Грудь {user.chest}, Талия {user.waist}")

        console.print("\n[bold]2. ПРИМЕРКА И ОЦЕНКА:[/bold]")
        
        # Перебираем размеры, которые реально есть у товара в базе
        available_sizes = [s for s in SIZES_ORDER if s in metrics]
        if not available_sizes:
            # Если конкретные размеры не указаны, прогоняем стандартную сетку
            available_sizes = ['S', 'M', 'L', 'XL']
            
        for target_size in available_sizes:
            res = calculate_fit(user, model_size, base_data, target_size)
            
            color = res.status_color
            console.print(f"   [bold {color}]Размер {target_size:<3}[/bold {color}] | Оценка: {res.score:>3.0f}% | {res.status}")
            
            if res.score > 10:
                for zone, txt in res.details.items():
                    console.print(f"      - {zone}: {txt}")
                for warn in res.warnings:
                    console.print(f"      [yellow]! ПРЕДУПРЕЖДЕНИЕ: {warn}[/yellow]")

    console.print("\n" + "="*60)
    console.print("[bold green]Тестирование завершено.[/bold green]\n")

if __name__ == "__main__":
    main()