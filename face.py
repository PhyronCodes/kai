import numpy as np
import pygame

WIDTH, HEIGHT = 800, 600
CAMERA_DISTANCE = 3.0
FOCAL_LENGTH = 400
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))

# Head
NUM_POINTS = 1200
HEAD_COLOUR = (60, 160, 255)

# Movement
SWAY_SPEED = 0.02        # how fast time moves each frame
SWAY_AMOUNT = 0.3        # how far the head turns either side (radians)

# Eyes (particle iris around a dark pupil)
LEFT_EYE_POS = (-0.35, 0.25)
RIGHT_EYE_POS = (0.35, 0.25)
PUPIL_RADIUS = 0.06
IRIS_RADIUS = 0.17
IRIS_POINTS = 220        # particles per eye
IRIS_SPIN = 0.3          # how fast the iris slowly swirls
EYE_WIDTH = 1.4         # stretch sideways (1 = round)
EYE_HEIGHT = 0.9         # squash vertically (1 = round)
IRIS_INNER_COLOUR = (150, 230, 255)   # bright cyan at the pupil edge
IRIS_OUTER_COLOUR = (40, 110, 230)    # deeper blue at the rim

# Mouth (sound-wave bars)
MOUTH_Y = -0.35
MOUTH_HALF_WIDTH = 0.45
MOUTH_BARS = 21
DOTS_PER_BAR = 14
MOUTH_COLOUR = (190, 235, 255)
IDLE_BAR = 0.012         # bar half-height when quiet
SPEAKING_BAR = 0.14      # tallest bar half-height when speaking

SURFACE_OFFSET = 1.01    # features sit just above the head's surface


def fibonacci_sphere(n: int) -> np.ndarray:
    i = np.arange(n)
    y = 1 - 2 * (i + 0.5) / n
    radius = np.sqrt(1 - y ** 2)
    theta = GOLDEN_ANGLE * i
    x = np.cos(theta) * radius
    z = np.sin(theta) * radius
    return np.column_stack((x, y, z))


def front_points(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Place (x, y) positions onto the front (negative z) of the sphere."""
    z = -np.sqrt(1 - x ** 2 - y ** 2)
    return np.column_stack((x, y, z)) * SURFACE_OFFSET


EYE_RNG = np.random.default_rng(3)
IRIS_U = EYE_RNG.random(IRIS_POINTS) ** 1.6              # bunched towards the pupil
IRIS_ANGLES = EYE_RNG.uniform(0, 2 * np.pi, IRIS_POINTS)
IRIS_SPARKLE = EYE_RNG.uniform(0.45, 1.0, IRIS_POINTS)    # each particle's own brightness


def make_eye(centre: tuple[float, float], t: float) -> tuple[np.ndarray, np.ndarray]:
    """A swirling oval of particles around a dark pupil, laid onto the sphere.
    Returns the points and a colour for each one."""
    r = PUPIL_RADIUS + (IRIS_RADIUS - PUPIL_RADIUS) * IRIS_U
    # Inner particles swirl faster than outer ones, like a vortex
    angle = IRIS_ANGLES + IRIS_SPIN * t * (1.5 - IRIS_U)
    x = centre[0] + r * np.cos(angle) * EYE_WIDTH
    y = centre[1] + r * np.sin(angle) * EYE_HEIGHT

    inner = np.array(IRIS_INNER_COLOUR, dtype=float)
    outer = np.array(IRIS_OUTER_COLOUR, dtype=float)
    colours = inner + (outer - inner) * IRIS_U[:, None]   # fade from cyan to blue
    colours *= IRIS_SPARKLE[:, None]
    return front_points(x, y), colours


def hide_eye_area(head: np.ndarray) -> np.ndarray:
    """Remove head dots that sit where the eyes are, so the pupils stay dark."""
    keep = np.ones(len(head), dtype=bool)
    for cx, cy in (LEFT_EYE_POS, RIGHT_EYE_POS):
        # Distance measured in "stretched" units, so the hidden area is an ellipse too
        distance = np.hypot((head[:, 0] - cx) / EYE_WIDTH, (head[:, 1] - cy) / EYE_HEIGHT)
        keep &= ~((distance < IRIS_RADIUS * 1.15) & (head[:, 2] < 0))
    return head[keep]


BAR_RNG = np.random.default_rng(7)
BAR_SPEEDS = BAR_RNG.uniform(4, 9, MOUTH_BARS)        # each bar moves at its own speed
BAR_PHASES = BAR_RNG.uniform(0, 2 * np.pi, MOUTH_BARS)  # and starts at its own point


def make_mouth(t: float, loudness: float) -> np.ndarray:
    """Vertical bars of dots, like a voice-recorder waveform, laid onto the sphere."""
    bar_x = np.linspace(-MOUTH_HALF_WIDTH, MOUTH_HALF_WIDTH, MOUTH_BARS)

    # Each bar's height: its own wobble, taller in the middle, scaled by loudness
    wobble = 0.15 + 0.85 * np.abs(np.sin(BAR_SPEEDS * t + BAR_PHASES))
    envelope = 0.4 + 0.6 * np.sin(np.pi * np.linspace(0, 1, MOUTH_BARS))
    half_height = IDLE_BAR + (SPEAKING_BAR - IDLE_BAR) * loudness * wobble * envelope

    # Stack dots from the bottom to the top of each bar
    steps = np.linspace(-1, 1, DOTS_PER_BAR)
    x = np.repeat(bar_x, DOTS_PER_BAR)
    y = MOUTH_Y + np.outer(half_height, steps).ravel()
    return front_points(x, y)


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


def draw_frame(screen, head, t: float, loudness: float) -> None:
    left_eye, left_colours = make_eye(LEFT_EYE_POS, t)
    right_eye, right_colours = make_eye(RIGHT_EYE_POS, t)
    mouth = make_mouth(t, loudness)

    # Put every dot in one array, with a colour and size adjustment for each
    points = np.vstack((head, left_eye, right_eye, mouth))
    colours = np.vstack((
        np.tile(np.array(HEAD_COLOUR, dtype=float), (len(head), 1)),
        left_colours,
        right_colours,
        np.tile(np.array(MOUTH_COLOUR, dtype=float), (len(mouth), 1)),
    ))
    size_boost = np.concatenate((
        np.zeros(len(head)),
        np.full(len(left_eye) + len(right_eye), -0.9),
        np.full(len(mouth), -1.2),
    ))

    angle = SWAY_AMOUNT * np.sin(t)
    rotated = points @ rotation_y(angle).T
    screen_x, screen_y, z = project(rotated)

    nearness = np.clip((1 - z) / 2, 0, 1)
    radius = np.maximum(1 + 2 * nearness + size_boost, 1)
    brightness = 0.2 + 0.8 * nearness
    order = np.argsort(z)[::-1]

    screen.fill((0, 0, 0))
    for i in order:
        colour = (colours[i] * brightness[i]).astype(int)
        pygame.draw.circle(screen, colour, (int(screen_x[i]), int(screen_y[i])), int(round(radius[i])))
    pygame.display.flip()


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("KAI")
    clock = pygame.time.Clock()

    head = hide_eye_area(fibonacci_sphere(NUM_POINTS))

    t = 0.0
    loudness = 0.0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # For testing: hold SPACE to pretend KAI is speaking
        target = 1.0 if pygame.key.get_pressed()[pygame.K_SPACE] else 0.0
        loudness += (target - loudness) * 0.2  # ease towards the target smoothly

        t += SWAY_SPEED
        draw_frame(screen, head, t, loudness)
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()