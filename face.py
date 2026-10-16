import numpy as np
import pygame

WIDTH, HEIGHT = 800, 600
NUM_POINTS = 400
CAMERA_DISTANCE = 3.0
FOCAL_LENGTH = 400
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))
DOT_COLOUR = (60, 160, 255)


def fibonacci_sphere(n: int) -> np.ndarray:
    i = np.arange(n)
    y = 1 - 2 * (i + 0.5) / n
    radius = np.sqrt(1 - y ** 2)
    theta = GOLDEN_ANGLE * i
    x = np.cos(theta) * radius
    z = np.sin(theta) * radius
    return np.column_stack((x, y, z))


def rotation_y(angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array([
        [c, 0, s],
        [0, 1, 0],
        [-s, 0, c],
    ])


def project(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    scale = FOCAL_LENGTH / (z + CAMERA_DISTANCE)
    screen_x = WIDTH / 2 + x * scale
    screen_y = HEIGHT / 2 - y * scale
    return screen_x, screen_y, z


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("KAI")
    clock = pygame.time.Clock()

    points = fibonacci_sphere(NUM_POINTS)
    angle = 0.0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        angle += 0.0075
        rotated = points @ rotation_y(angle).T
        screen_x, screen_y, z = project(rotated)

        nearness = (1 - z) / 2
        radius = 1 + 3 * nearness
        brightness = 0.25 + 0.75 * nearness
        order = np.argsort(z)[::-1]

        screen.fill((0, 0, 0))
        for i in order:
            r, g, b = DOT_COLOUR
            colour = (int(r * brightness[i]), int(g * brightness[i]), int(b * brightness[i]))
            pygame.draw.circle(screen, colour, (int(screen_x[i]), int(screen_y[i])), int(round(radius[i])))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()