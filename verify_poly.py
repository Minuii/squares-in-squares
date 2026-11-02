"""Independent validator: convex polygon clipping (Sutherland-Hodgman) +
shoelace area. Completely different code path from the SAT test, so agreement
between the two is real evidence that a packing is feasible."""
import numpy as np
import squares_core as sc


def clip(subject, a, b):
    """Keep the part of `subject` on the left of the directed edge a->b."""
    out = []
    m = len(subject)
    if m == 0:
        return out
    ex, ey = b[0] - a[0], b[1] - a[1]

    def side(p):
        return ex * (p[1] - a[1]) - ey * (p[0] - a[0])

    for i in range(m):
        cur = subject[i]
        prv = subject[(i - 1) % m]
        sc_cur, sc_prv = side(cur), side(prv)
        if sc_cur >= 0:
            if sc_prv < 0:
                t = sc_prv / (sc_prv - sc_cur)
                out.append(prv + t * (cur - prv))
            out.append(cur)
        elif sc_prv >= 0:
            t = sc_prv / (sc_prv - sc_cur)
            out.append(prv + t * (cur - prv))
    return out


def poly_area(p):
    if len(p) < 3:
        return 0.0
    p = np.asarray(p)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def pair_intersection_area(c1, c2):
    poly = list(c2)
    for i in range(4):
        poly = clip(poly, c1[i], c1[(i + 1) % 4])
        if not poly:
            return 0.0
    return poly_area(poly)


def max_overlap_area(xy, th, chunk_report=False):
    p = sc.corners(xy, th)
    n = len(xy)
    worst = 0.0
    where = None
    for i in range(n):
        for j in range(i + 1, n):
            a = pair_intersection_area(p[i], p[j])
            if a > worst:
                worst, where = a, (i, j)
    return worst, where


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    # 1. random configs: do SAT and polygon area agree on overlap/no-overlap?
    bad = 0
    for trial in range(300):
        n = int(rng.integers(2, 7))
        xy = rng.random((n, 2)) * 1.6
        th = rng.random(n) * np.pi
        pen = sc.max_penetration(xy, th)
        area, where = max_overlap_area(xy, th)
        sat_says = pen > 1e-12
        area_says = area > 1e-12
        if sat_says != area_says:
            bad += 1
            print(f"DISAGREE trial={trial} pen={pen:.3e} area={area:.3e} where={where}")
    print(f"random cross-check: {bad} disagreements out of 300 configs")

    # 2. known packings
    for n in [1, 5, 9, 16]:
        xy, th = sc.grid(n)
        print(f"grid n={n}: pen={sc.max_penetration(xy, th):.2e} "
              f"area={max_overlap_area(xy, th)[0]:.2e}")
    # 3. deliberately overlapping
    xy = np.array([[0.0, 0.0], [0.5, 0.5]]); th = np.array([0.0, 0.3])
    print("overlap case: sat", sc.max_penetration(xy, th),
          "area", max_overlap_area(xy, th)[0], "(expected 0.25-ish)")
