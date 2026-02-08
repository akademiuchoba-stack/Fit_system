"""Fit_system backend — Fit Engine facade.

Этот модуль — *единая точка входа* в алгоритм подбора размера.

Зачем он нужен (простыми словами):
Сейчас алгоритм "Идеальный припуск" лежит в logic.py и временно хранится в GitHub,
чтобы ты мог(ла) лично его настраивать.

Позже, когда придёт время защищать алгоритм, мы сможем:
- вынести/спрятать logic.py,
- заменить реализацию на закрытую (или даже на отдельный сервис),
и при этом НЕ переписывать API, main.py и фронт — они продолжат вызывать только этот файл.
"""

from __future__ import annotations

from typing import Any, Dict

from . import logic


def calculate_fit(user_data: Dict[str, Any], garment_payload: Dict[str, Any], *, size_label: str):
    """Посчитать фит-скор и пояснения для пользователя и конкретного размера вещи.

    Важно:
    - В main.py и остальном коде НЕ используем logic.compute_fit_score напрямую.
      Всегда зовём только calculate_fit(...).
    - Возвращаем объект FitResult из logic.py (score/status/explanation/deltas/warnings).
    """

    # Здесь намеренно тонкая обёртка.
    # Позже именно в этом месте можно будет:
    # - добавить скрытую/платную проверку лицензии,
    # - загрузку коэффициентов из БД,
    # - вызов закрытого бинарника/сервиса и т.д.
    return logic.compute_fit_score(user_data, garment_payload, size_label=str(size_label))
