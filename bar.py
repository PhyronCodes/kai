import numpy as np
import pygame

from face import STATES, FaceControl

WIDTH, HEIGHT = 1280, 400          # the shape of a bar LCD
BACKGROUND = (5, 8, 20)
BAR_COLOUR = (190, 235, 255)      # the same pale blue as the mouth in face.py

NUM_BARS = 64
BAR_GAP = 6                        # pixels between bars
MAX_HEIGHT = HEIGHT * 0.8          # tallest a bar can be
MIN_HEIGHT = 6                     # so a "silent" bar is still a visible dot
DOT_SPACING = 9                    # each bar is a column of dots, this far apart

# Every bar gets its own speed and starting point, so they bounce independently
BAR_RNG = np.random.default_rng(7)
BAR_SPEEDS = BAR_RNG.uniform(4, 9, NUM_BARS)
BAR_PHASES = BAR_RNG.uniform(0, 2 * np.pi, NUM_BARS)

# How each state looks. The current look eases towards these, like face.py.
#   speed: how fast the bars bounce        height: how tall they are on their own
#   voice: how much loudness adds          sweep:  strength of the "thinking" pulse
#   glow:  brightness
STATE_LOOKS = {
    "idle":      {"speed": 0.25, "height": 0.30, "voice": 0.0, "sweep": 0.0, "glow": 0.65},
    "listening": {"speed": 0.60, "height": 0.25, "voice": 0.9, "sweep": 0.0, "glow": 1.00},
    "thinking":  {"speed": 0.40, "height": 0.15, "voice": 0.0, "sweep": 1.0, "glow": 0.85},
    "speaking":  {"speed": 1.00, "height": 0.10, "voice": 1.0, "sweep": 0.0, "glow": 1.00},
}
EASING = 0.12
SWEEP_SPEED = 0.7      # how fast the thinking pulse crosses the screen
SWEEP_WIDTH = 0.08     # how wide the pulse is (as a fraction of the screen)


def bar_heights(phase: float, t: float, look: dict, loudness: float) -> np.ndarray:
    """One height per bar, in pixels.

    phase drives the bouncing (it grows faster when look["speed"] is higher);
    t is plain time in seconds, used for the thinking sweep."""
    x = np.linspace(0, 1, NUM_BARS)                     # each bar's position, 0 to 1
    envelope = 0.4 + 0.6 * np.sin(np.pi * x)            # taller in the middle, never 0
    wobble = 0.15 + 0.85 * np.abs(np.sin(BAR_SPEEDS * phase + BAR_PHASES))

    # The bouncing part: a base height, plus whatever the voice adds
    level = look["height"] + look["voice"] * loudness

    # The thinking pulse: a bump that slides left to right, then starts again
    centre = (t * SWEEP_SPEED) % 1.4 - 0.2              # runs from -0.2 to 1.2, so it enters and exits smoothly
    bump = np.exp(-((x - centre) / SWEEP_WIDTH) ** 2)

    size = np.clip(level * wobble + look["sweep"] * bump, 0, 1)
    return MIN_HEIGHT + (MAX_HEIGHT - MIN_HEIGHT) * envelope * size


def draw_bars(screen: pygame.Surface, heights: np.ndarray, glow: float) -> None:
    """Each bar is a column of dots, centred on the middle line, like face.py."""
    colour = [min(255, int(c * glow)) for c in BAR_COLOUR]
    bar_width = (WIDTH - BAR_GAP * (NUM_BARS + 1)) / NUM_BARS
    radius = max(2, int(bar_width * 0.35))
    for i, h in enumerate(heights):
        centre_x = BAR_GAP * (i + 1) + bar_width * i + bar_width / 2
        dots_each_side = int(h / 2 // DOT_SPACING)
        for k in range(-dots_each_side, dots_each_side + 1):
            centre_y = HEIGHT / 2 + k * DOT_SPACING
            pygame.draw.circle(screen, colour, (centre_x, centre_y), radius)


def run_bar(control: FaceControl | None = None) -> None:
    """Run the bar display. With no control, keys 1-4 switch state for testing,
    and speaking fakes a voice so you can see it move."""
    standalone = control is None
    if standalone:
        control = FaceControl()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    look = dict(STATE_LOOKS["idle"])
    t = 0.0
    phase = 0.0
    loudness = 0.0

    keys_to_states = {
        pygame.K_1: "idle",
        pygame.K_2: "listening",
        pygame.K_3: "thinking",
        pygame.K_4: "speaking",
    }

    while control.running:
        dt = clock.tick(30) / 1000
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                control.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                control.press_space()
            elif standalone and event.type == pygame.KEYDOWN and event.key in keys_to_states:
                control.state = keys_to_states[event.key]

        state = control.state
        pygame.display.set_caption(f"KAI - {state}  (space to talk)")

        # Ease the look towards the current state's look
        target = STATE_LOOKS[state]
        for key in look:
            look[key] += (target[key] - look[key]) * EASING

        # Phase grows at the current speed. Adding speed * dt each frame (instead of
        # computing speed * t) means changing speed never makes the bars jump.
        phase += look["speed"] * dt

        # Loudness: the real one from the voice loop, or a fake voice when testing
        if standalone:
            raw = 0.5 + 0.5 * np.sin(t * 7) * np.sin(t * 2.3) if state in ("speaking", "listening") else 0.0
        else:
            raw = control.loudness
        loudness += (raw - loudness) * 0.4

        screen.fill(BACKGROUND)
        draw_bars(screen, bar_heights(phase, t, look, loudness), look["glow"])
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_bar()