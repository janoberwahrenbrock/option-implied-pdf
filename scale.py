from typing import Callable


def scale_x_value(
    original_x: float,
    original_x_min: float,
    original_x_max: float,
    scaled_bounds: tuple[float, float] = (-1.0, 1.0)
) -> float:
    """
    Skaliert original_x aus [original_x_min, original_x_max] auf [scaled_min, scaled_max].

    Args:
        original_x:         Der Wert im Original-Strike-Intervall.
        original_x_min:     Minimum des Original-Intervalls.
        original_x_max:     Maximum des Original-Intervalls.
        scaled_bounds:      (scaled_min, scaled_max) – Zielinterval, z.B. (-1,1).

    Returns:
        scaled_x:           Lineares Abbilden in das skaliere Intervall.
    """
    scaled_min, scaled_max = scaled_bounds
    return scaled_min + (original_x - original_x_min) * (scaled_max - scaled_min) / (original_x_max - original_x_min)


def unscale_x_value(
    scaled_x: float,
    original_x_min: float,
    original_x_max: float,
    scaled_bounds: tuple[float, float] = (-1.0, 1.0)
) -> float:
    """
    Hebt die Skalierung von scaled_x aus [scaled_min, scaled_max]
    zurück ins Originalintervall [original_x_min, original_x_max].

    Args:
        scaled_x:           Der skalierte Wert im Intervall scaled_bounds.
        original_x_min:     Minimum des Original-Intervalls.
        original_x_max:     Maximum des Original-Intervalls.
        scaled_bounds:      (scaled_min, scaled_max) – das Intervall, in das skaliert wurde.

    Returns:
        original_x:         Rücktransformierter Wert im Originalintervall.
    """
    scaled_min, scaled_max = scaled_bounds
    return original_x_min + (scaled_x - scaled_min) * (original_x_max - original_x_min) / (scaled_max - scaled_min)


def unscale_splines(
    spline_scaled: Callable[[float], float],
    original_x_min: float,
    original_x_max: float,
    scaled_bounds: tuple[float, float] = (-1.0, 1.0)
) -> Callable[[float], float]:
    """
    Verpackt eine Spline-Funktion, die im Skalenraum auf [scaled_min,scaled_max] definiert ist,
    so dass sie im Original-X-Bereich [original_x_min,original_x_max] aufgerufen werden kann.

    Args:
        spline_scaled:     Die im Skalenraum definierte Spline-Funktion f_scaled(x_s).
        original_x_min:    Linke Grenze im Original-Strike-Raum.
        original_x_max:    Rechte Grenze im Original-Strike-Raum.
        scaled_bounds:     (scaled_min, scaled_max) – das Intervall, in das original_x zuvor skaliert wurde.

    Returns:
        spline_original:   Eine Funktion f_original(x_orig), die intern x_orig→x_s skaliert,
                           spline_scaled(x_s) auswertet und das Ergebnis zurückgibt.
    """
    scaled_min, scaled_max = scaled_bounds

    def spline_original(x_orig: float) -> float:
        # 1) X von Original- auf Skalenraum abbilden
        x_s = scaled_min + (x_orig - original_x_min) * (scaled_max - scaled_min) / (original_x_max - original_x_min)
        # 2) Spline im Skalenraum auswerten
        return spline_scaled(x_s)

    return spline_original
