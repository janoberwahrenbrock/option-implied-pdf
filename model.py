from typing import List, Tuple, Callable, Optional
import numpy as np
import cvxpy as cv
import matplotlib.pyplot as plt




def fit_parameter(
    points: List[Tuple[float, float]],
    support_points: List[float],
    konvex_until: float,
    bounds: Tuple[float, float],
    degree_of_spline: int = 3,
    sampling_interval: float = 1,
):
    """
    Schätzt die Koeffizienten eines stückweisen Polynom-Splines unter Konvexitäts- und Konkavitätsbedingungen.

    Diese Funktion löst ein konvexes Optimierungsproblem mittels CVXPY und bestimmt eine
    Koeffizientenmatrix, die die stückweise Polynome bis zu Grad 'degree_of_spline'
    auf Intervalle definiert durch 'support_points' und 'bounds' minimiert.

    Args:
        points (List[Tuple[float, float]]):
            Liste von Messpunkten als (x, y)-Paare, für die der Spline angepasst wird.
        support_points (List[float]):
            Aufsteigende Liste von Knoten x0 < x1 < ... < x_{M-2} im Definitionsbereich.
            Es entstehen M-1 Teilintervalle zwischen Bounds und Knoten.
        konvex_until (float):
            Knotenwert, bis zu dem die dritte Ableitung ≥ 0 (Konvexität) gelten muss.
            Für x > konvex_until muss die dritte Ableitung ≤ 0 (Konkavität) sein.
        bounds (Tuple[float, float]):
            Tupel (left_bound, right_bound) des Gesamt-Definitionsbereichs.
        degree_of_spline (int):
            Grad d des Polynoms pro Segment. Muss ≥ 3 sein, da die dritte Ableitung
            im Constraint genutzt wird.
        sampling_interval (float):
            Schrittweite Δx, in der das Intervall jedes Segments abgetastet wird, um
            die Vorzeichenbedingung der dritten Ableitung punktweise durchzusetzen.

    Returns:
        Tuple[str, float, np.ndarray]:
            - status (str): Solver-Status (z.B. 'optimal').
            - value (float): Minimaler Zielfunktionswert (Summe der quadrierten Abweichungen).
            - matrix (np.ndarray): Gelöste Koeffizientenmatrix der Form (d+1, M).
    """

    # --- Validation 1: bounds[0] < bounds[1]
    if bounds[0] >= bounds[1]:
        raise ValueError(f"Ungültige bounds: {bounds}. Es muss gelten: bounds[0] < bounds[1].")

    # --- Validation 2: support_points aufsteigend sortiert
    if support_points != sorted(support_points):
        raise ValueError("Die support_points müssen streng aufsteigend sortiert sein.")

    # --- Validation 3: support_points innerhalb der bounds
    if not all(bounds[0] <= x <= bounds[1] for x in support_points):
        raise ValueError("Alle support_points müssen innerhalb der bounds liegen.")

    # --- Validation 4: keine Duplikate in support_points
    if len(set(support_points)) != len(support_points):
        raise ValueError("support_points dürfen keine doppelten Werte enthalten.")

    # --- Validation 5: alle x-Werte der Punkte müssen innerhalb der bounds liegen
    for x, _ in points:
        if not (bounds[0] <= x <= bounds[1]):
            raise ValueError(f"Punkt mit x={x} liegt außerhalb der bounds {bounds}.")

    # --- Validation 6: konvex_until ∈ support_points
    if konvex_until not in support_points:
        raise ValueError(f"konvex_until = {konvex_until} ist kein Element der support_points.")

    # --- Validation 7: degree_of_spline muss mindestens 3 sein
    if degree_of_spline < 3:
        raise ValueError(f"degree_of_spline muss mindestens 3 sein, aber ist {degree_of_spline}.")

    matrix = cv.Variable((degree_of_spline + 1, len(support_points) + 1))

    constraints = []

    for index_of_support_point in range(len(support_points)):
        i = index_of_support_point
        x = support_points[i]

        # Funktion muss an support_points gleich sein
        expr_left = sum(
            matrix[j, i] * x**(degree_of_spline - j)
            for j in range(degree_of_spline + 1)
        )
        expr_right = sum(
            matrix[j, i + 1] * x**(degree_of_spline - j)
            for j in range(degree_of_spline + 1)
        )
        constraints.append(expr_left == expr_right)

        # 1. Ableitung: ∑_{j=0}^{d-1} a_{j,i}·(d–j)·x^(d–j–1)  muss gleich sein
        expr_der1_left = sum(
            matrix[j, i] * (degree_of_spline - j) * x**(degree_of_spline - j - 1)
            for j in range(degree_of_spline)
        )
        expr_der1_right = sum(
            matrix[j, i + 1] * (degree_of_spline - j) * x**(degree_of_spline - j - 1)
            for j in range(degree_of_spline)
        )
        constraints.append(expr_der1_left == expr_der1_right)

        # 2. Ableitung: ∑_{j=0}^{d-2} a_{j,i}·(d–j)·(d–j–1)·x^(d–j–2)  muss gleich sein
        expr_der2_left = sum(
            matrix[j, i] * (degree_of_spline - j) * (degree_of_spline - j - 1) * x**(degree_of_spline - j - 2)
            for j in range(degree_of_spline - 1)
        )
        expr_der2_right = sum(
            matrix[j, i + 1] * (degree_of_spline - j) * (degree_of_spline - j - 1) * x**(degree_of_spline - j - 2)
            for j in range(degree_of_spline - 1)
        )
        constraints.append(expr_der2_left == expr_der2_right)


    d = degree_of_spline

    # Für alle Segmente i = 0 … len(support_points)
    for i in range(len(support_points) + 1):
        # 1. Segment-Grenzen bestimmen
        if i == 0:
            x_start, x_end = bounds[0], support_points[0]
        elif i < len(support_points):
            x_start, x_end = support_points[i-1], support_points[i]
        else:
            x_start, x_end = support_points[-1], bounds[1]

        # 2. Gitter im Segment
        x_tests = np.arange(x_start, x_end, sampling_interval)

        for x0 in x_tests:
            # --- Zweite Ableitung: ∑_{j=0}^{d-2} a_{j,i}·(d−j)·(d−j−1)·x0^(d−j−2)
            expr_der2 = sum(
                matrix[j, i]
                * (d - j)
                * (d - j - 1)
                * x0 ** (d - j - 2)
                for j in range(d - 1)
            )
            # Constraint: f''(x0) ≥ 0  (Konvexität im gesamten Segment) bzw die Wahrscheinlichkeitsverteilung ist überall größer 0
            constraints.append(expr_der2 >= 0)

            # Konvexität bzw Konkavität der ersten Ableitung:
            # --- Dritte Ableitung: ∑_{j=0}^{d-3} a_{j,i}·(d−j)·(d−j−1)·(d−j−2)·x0^(d−j−3)
            expr_der3 = sum(
                matrix[j, i]
                * (d - j) * (d - j - 1) * (d - j - 2)
                * x0 ** (d - j - 3)
                for j in range(d - 2)
            )
            if x0 < konvex_until:
                constraints.append(expr_der3 >= 0)
            elif x0 > konvex_until:
                constraints.append(expr_der3 <= 0)

    
    def get_location(point: Tuple[float, float]) -> Tuple[float | None, float | None]:
        """
        Bestimmt, in welchem Teil­intervall (zwischen den global definierten support_points)
        der x-Wert eines Punktes liegt.

        Die extern definierte Liste `support_points` muss streng aufsteigend sein.

        - Liegt x ≤ support_points[0], so wird (None, 0) zurückgegeben.
        - Liegt x ≥ support_points[-1], so wird (len(support_points)-1, None) zurückgegeben.
        - Ansonsten (i, i+1), sodass support_points[i] ≤ x ≤ support_points[i+1].

        Args:
            point (Tuple[float, float]):
                Ein Tupel (x, y) mit den Koordinaten des Abfrage-Punktes.

        Returns:
            Tuple[Optional[int], Optional[int]]:
                Ein Paar (i_left, i_right):
                - `i_left` ist der Index des linken Stützpunkts (oder None, wenn x am oder vor
                dem ersten Stützpunkt liegt).
                - `i_right` ist der Index des rechten Stützpunkts (oder None, wenn x am oder nach
                dem letzten Stützpunkt liegt).

        Example:
            >>> support_points = [0.0, 1.0, 2.0, 3.0]
            >>> get_location((0.5, 2.1))
            (0, 1)
            >>> get_location((0.0, 5.0))
            (None, 0)
            >>> get_location((4.2, -1.5))
            (3, None)
        """
        if point[0] <= support_points[0]:
            return None, 0
        elif point[0] >= support_points[-1]:
            return len(support_points) - 1, None
        else:
            for i in range(len(support_points) - 1):
                if support_points[i] <= point[0] <= support_points[i + 1]:
                    return i, i+1
                

    differences = []

    for point in points:
        x, y = point
        _, right_index = get_location(point)
        # Index des zugehörigen Segments
        i = right_index if right_index is not None else len(support_points)

        # Residuum: f_i(x) - y mit beliebigem degree_of_spline
        expr = sum(
            matrix[j, i] * x**(degree_of_spline - j)
            for j in range(degree_of_spline + 1)
        ) - y

        differences.append(expr)

    diff_vec = cv.vstack(differences)

    objective = cv.Minimize(cv.sum_squares(diff_vec))


    # solve the problem
    problem = cv.Problem(objective, constraints)
    problem.solve(verbose=True) # solver=cv.CLARABEL

    return problem.status, problem.value, matrix.value





def assemble_splines(
    matrix: np.ndarray,
    support_points: List[float],
    bounds: Tuple[float, float],
    derivative: int = 0
) -> Callable[[float], float]:
    """
    Erzeugt aus der Koeffizienten-Matrix, den Stütz­punkten und den
    Randwerten eine stückweise-polynomielle Spline-Funktion oder deren
    erste beiden Ableitungen.

    Die Matrix hat Form (d+1, M), wobei d = matrix.shape[0]−1 der
    Polynom­grad pro Segment ist und M = matrix.shape[1] die Anzahl
    der Segmente (gleich Anzahl support_points + 1).

    Args:
        matrix (np.ndarray):
            Array der Form (d+1, M). Spalte i enthält die Koeffizienten
            [a0, a1, …, ad] des Polynoms vom Grad d im i-ten Segment.
        support_points (List[float]):
            Aufsteigend sortierte Knoteninien [sp0, sp1, …, spM-2].
            Es entstehen M Segmente:
              - Segment 0: von bounds[0] bis sp0
              - Segment i: von sp_{i-1} bis sp_i  (i=1…M-2)
              - Segment M−1: von sp_{M-2} bis bounds[1]
        bounds (Tuple[float, float]):
            (left_bound, right_bound) des gesamten Definitionsbereichs.
        derivative (int, optional):
            Gibt an, welchen Ableitungsgrad die zurückgegebene Funktion
            liefert:
              - 0 → Originalfunktion f(x)
              - 1 → Erste Ableitung f '(x)
              - 2 → Zweite Ableitung f ''(x)
            Andere Werte führen zu einem ValueError.

    Returns:
        Callable[[float], float]:
            Eine Funktion, die für ein beliebiges x∈[left_bound, right_bound]
            automatisch das richtige Polynom-Segment wählt und f(x)
            bzw. f '(x) oder f ''(x) auswertet.
    """
    left_bound, right_bound = bounds
    num_rows, num_segments = matrix.shape
    degree = num_rows - 1  # Grad d

    if derivative not in (0, 1, 2):
        raise ValueError("Nur derivative=0, 1 oder 2 sind erlaubt.")

    def f(x: float) -> float:
        # Domain-Check
        if not (left_bound <= x <= right_bound):
            raise ValueError(f"x={x} liegt außerhalb der Bounds {bounds}.")

        # Segment-Index bestimmen
        if x <= support_points[0]:
            seg = 0
        elif x >= support_points[-1]:
            seg = num_segments - 1
        else:
            seg = None
            for i in range(len(support_points) - 1):
                if support_points[i] <= x <= support_points[i + 1]:
                    seg = i + 1
                    break
            if seg is None:
                seg = num_segments - 1

        # Auswertung je nach Ableitungsgrad
        result = 0.0
        if derivative == 0:
            # f(x) = ∑ a_{j,seg} * x^(d-j)
            for j in range(num_rows):
                coeff = matrix[j, seg]
                exponent = degree - j
                result += coeff * x**exponent

        elif derivative == 1:
            # f'(x) = ∑ a_{j,seg} * (d-j) * x^(d-j-1)
            for j in range(num_rows - 1):
                coeff = matrix[j, seg]
                power = degree - j
                result += coeff * power * x**(power - 1)

        else:  # derivative == 2
            # f''(x) = ∑ a_{j,seg} * (d-j)*(d-j-1) * x^(d-j-2)
            for j in range(num_rows - 2):
                coeff = matrix[j, seg]
                power = degree - j
                result += coeff * power * (power - 1) * x**(power - 2)

        return result

    return f
    




def plot_func(
    func: Callable[[float], float],
    bounds: Tuple[float, float],
    points: Optional[List[Tuple[float, float]]] = None,
    num_samples: int = 400
) -> None:
    """
    Zeichnet eine gegebene Funktion und optional die Originaldatenpunkte.

    Args:
        func:        Die Funktion f(x) → y, z.B. von build_spline_function zurückgegeben.
        bounds:      (left_bound, right_bound) des Definitionsbereichs für den Plot.
        points:      Optional Liste der (x, y)-Datenpunkte zum Überlagern.
                    Wenn None, werden keine Punkte gezeichnet.
        num_samples: Anzahl der Abtastpunkte für den glatten Funktionsplot.
    """
    left, right = bounds
    # dichtes Raster im Definitionsbereich
    xs = np.linspace(left, right, num_samples)
    ys = [func(x) for x in xs]

    # Funktionskurve
    plt.plot(xs, ys, label="f(x)")

    # Optional: Originaldatenpunkte
    if points is not None and len(points) > 0:
        px, py = zip(*points)
        plt.scatter(px, py, color="red", label="Datenpunkte")

    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("Funktionsplot")
    plt.legend()
    plt.show()




if __name__ == "__main__":

    # Testdaten
    points = [(-3, 15), (-2, 9), (-1, 6), (0, 4), (1, 2.5), (2, 1.5), (3, 1)]
    support_points = [-1.5, 0, 1.5]
    konvex_until = 0
    bounds = (-4, 4)

    status, value, matrix = fit_parameter(points=points, support_points=support_points, konvex_until=konvex_until, bounds=bounds, degree_of_spline=4, sampling_interval=0.1)

    print(f"Status: {status}")
    print(f"Zielfunktionswert: {value}")
    print("Koeffizientenmatrix:")
    print(matrix)


    # Baue die Funktion
    spline_func = assemble_splines(
        matrix=matrix,
        support_points=support_points,
        bounds=bounds
    )

    plot_func(func=spline_func, bounds=bounds, points=points)



    # Baue die erste Ableitung
    first_derivative = assemble_splines(
        matrix=matrix,
        support_points=support_points,
        bounds=bounds,
        derivative=1
    )

    plot_func(func=first_derivative, bounds=bounds)


    # Baue die zweite Ableitung
    second_derivative = assemble_splines(
        matrix=matrix,
        support_points=support_points,
        bounds=bounds,
        derivative=2
    )

    plot_func(func=second_derivative, bounds=bounds)
