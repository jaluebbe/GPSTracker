# based on https://github.com/aleksandrbazhin/ellipsoid_fit_python
import numpy as np
import math


def data_regularize(data, type="spherical", divs=10):
    limits = np.array(
        [
            [min(data[:, 0]), max(data[:, 0])],
            [min(data[:, 1]), max(data[:, 1])],
            [min(data[:, 2]), max(data[:, 2])],
        ]
    )

    regularized = []

    if type == "cubic":  # take mean from points in the cube

        X = np.linspace(*limits[0], num=divs)
        Y = np.linspace(*limits[1], num=divs)
        Z = np.linspace(*limits[2], num=divs)

        for i in range(divs - 1):
            for j in range(divs - 1):
                for k in range(divs - 1):
                    points_in_sector = []
                    for point in data:
                        if (
                            point[0] >= X[i]
                            and point[0] < X[i + 1]
                            and point[1] >= Y[j]
                            and point[1] < Y[j + 1]
                            and point[2] >= Z[k]
                            and point[2] < Z[k + 1]
                        ):
                            points_in_sector.append(point)
                    if len(points_in_sector) > 0:
                        regularized.append(
                            np.mean(np.array(points_in_sector), axis=0)
                        )

    elif type == "spherical":  # take mean from points in the sector
        divs_u = divs
        divs_v = divs * 2

        center = np.array(
            [
                0.5 * (limits[0, 0] + limits[0, 1]),
                0.5 * (limits[1, 0] + limits[1, 1]),
                0.5 * (limits[2, 0] + limits[2, 1]),
            ]
        )
        d_c = data - center

        # spherical coordinates around center
        r_s = np.sqrt(d_c[:, 0] ** 2.0 + d_c[:, 1] ** 2.0 + d_c[:, 2] ** 2.0)
        d_s = np.array(
            [r_s, np.arccos(d_c[:, 2] / r_s), np.arctan2(d_c[:, 1], d_c[:, 0])]
        ).T

        u = np.linspace(0, np.pi, num=divs_u)
        v = np.linspace(-np.pi, np.pi, num=divs_v)

        for i in range(divs_u - 1):
            for j in range(divs_v - 1):
                points_in_sector = []
                for k, point in enumerate(d_s):
                    if (
                        point[1] >= u[i]
                        and point[1] < u[i + 1]
                        and point[2] >= v[j]
                        and point[2] < v[j + 1]
                    ):
                        points_in_sector.append(data[k])

                if len(points_in_sector) > 0:
                    regularized.append(
                        np.mean(np.array(points_in_sector), axis=0)
                    )
    return np.array(regularized)


# http://www.mathworks.com/matlabcentral/fileexchange/24693-ellipsoid-fit
# for arbitrary axes
def ellipsoid_fit(X):
    x = X[:, 0]
    y = X[:, 1]
    z = X[:, 2]
    D = np.array(
        [
            x * x + y * y - 2 * z * z,
            x * x + z * z - 2 * y * y,
            2 * x * y,
            2 * x * z,
            2 * y * z,
            2 * x,
            2 * y,
            2 * z,
            1 - 0 * x,
        ]
    )
    d2 = np.array(x * x + y * y + z * z).T  # rhs for LLSQ
    u = np.linalg.solve(D.dot(D.T), D.dot(d2))
    a = np.array([u[0] + 1 * u[1] - 1])
    b = np.array([u[0] - 2 * u[1] - 1])
    c = np.array([u[1] - 2 * u[0] - 1])
    v = np.concatenate([a, b, c, u[2:]], axis=0).flatten()
    A = np.array(
        [
            [v[0], v[3], v[4], v[6]],
            [v[3], v[1], v[5], v[7]],
            [v[4], v[5], v[2], v[8]],
            [v[6], v[7], v[8], v[9]],
        ]
    )

    center = np.linalg.solve(-A[:3, :3], v[6:9])

    translation_matrix = np.eye(4)
    translation_matrix[3, :3] = center.T

    R = translation_matrix.dot(A).dot(translation_matrix.T)

    evals, evecs = np.linalg.eig(R[:3, :3] / -R[3, 3])
    evecs = evecs.T

    radii = np.sqrt(1.0 / np.abs(evals))
    radii *= np.sign(evals)

    return center, evecs, radii, v
