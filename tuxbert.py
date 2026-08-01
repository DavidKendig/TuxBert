"""TUX*BERT -- a 3-D Q*bert-style arcade game starring Tux the Linux penguin.

Classic arcade rules on a 7-row cube pyramid: hop diagonally, repaint every
cube top, dodge red balls and Coily the snake, lure him off the edge with the
flying discs.  Rendered in true 3-D with raylib, played like it's 1982.

Run:      python tuxbert.py
Controls: arrow keys hop diagonally (UP=up-right, LEFT=up-left,
          RIGHT=down-right, DOWN=down-left), P pauses, ENTER starts.
"""

import json
import math
import os
import random
import struct
import sys
import wave

import pyray as rl

# ---------------------------------------------------------------- constants

SCREEN_W, SCREEN_H = 960, 720
CS = 2.0                   # cube size (world units)
PLAYER_HOP = 0.26          # seconds per player hop
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Cube grid: i grows toward the viewer's lower-right, j toward the lower-left;
# i + j is the depth from the top, so any cell set forms a hoppable staircase.
# The set of valid cells comes from the current level's shape map.
DIR_UR = (0, -1)
DIR_DL = (0, 1)
DIR_UL = (-1, 0)
DIR_DR = (1, 0)

CELLS = set()              # active board cells, owned by Board.reset()

# color schemes: cube sides + top color progression (base -> mid -> target)
SCHEMES = [
    dict(side_r=(96, 34, 120, 255), side_l=(150, 60, 180, 255),
         base=(32, 90, 226, 255), mid=(240, 140, 60, 255), target=(250, 210, 50, 255)),
    dict(side_r=(30, 90, 115, 255), side_l=(60, 140, 170, 255),
         base=(220, 70, 60, 255), mid=(250, 200, 90, 255), target=(90, 220, 130, 255)),
    dict(side_r=(140, 80, 40, 255), side_l=(200, 120, 60, 255),
         base=(70, 70, 85, 255), mid=(230, 120, 180, 255), target=(90, 200, 240, 255)),
    dict(side_r=(55, 55, 140, 255), side_l=(90, 90, 200, 255),
         base=(30, 160, 90, 255), mid=(240, 230, 120, 255), target=(245, 120, 200, 255)),
    dict(side_r=(110, 35, 55, 255), side_l=(170, 60, 80, 255),
         base=(235, 220, 200, 255), mid=(110, 190, 80, 255), target=(250, 140, 40, 255)),
    dict(side_r=(40, 105, 80, 255), side_l=(70, 160, 120, 255),
         base=(140, 60, 220, 255), mid=(250, 240, 130, 255), target=(240, 80, 90, 255)),
]

FLASH_PALETTE = [(250, 210, 50, 255), (240, 80, 90, 255), (90, 220, 130, 255),
                 (90, 200, 240, 255), (245, 120, 200, 255), (255, 255, 255, 255)]

# 25 level layouts.  Row = i (down-right), column = j (down-left), '#' = cube.
# Every shape is one orthogonally-connected staircase of cubes.
SHAPES = [
    ("PYRAMID", """
#######
######.
#####..
####...
###....
##.....
#......
"""),
    ("SQUARE", """
#####
#####
#####
#####
#####
"""),
    ("DIAMOND", """
...#...
..###..
.#####.
#######
.#####.
..###..
...#...
"""),
    ("STAIRWAY", """
###....
###....
###....
###....
#######
#######
#######
"""),
    ("T-TOWER", """
#######
#######
..###..
..###..
..###..
..###..
"""),
    ("ARROW", """
...#...
..###..
.#####.
#######
..###..
..###..
..###..
"""),
    ("CROSS", """
..###..
..###..
#######
#######
#######
..###..
..###..
"""),
    ("TWIN PEAKS", """
####.####
###...###
##.....##
#########
"""),
    ("BIG PYRAMID", """
########
#######.
######..
#####...
####....
###.....
##......
#.......
"""),
    ("U-TUBE", """
##...##
##...##
##...##
##...##
##...##
#######
#######
"""),
    ("H-BLOCK", """
##...##
##...##
##...##
#######
##...##
##...##
##...##
"""),
    ("BASTION", """
.####.
######
######
######
######
.####.
"""),
    ("THE Z", """
#######
#######
....##.
...##..
..##...
#######
#######
"""),
    ("PINWHEEL", """
####...
####...
####...
...#...
...####
...####
...####
"""),
    ("HOURGLASS", """
#######
.#####.
..###..
...#...
..###..
.#####.
#######
"""),
    ("WINDOW", """
##.##
##.##
#####
##.##
##.##
"""),
    ("CANYON", """
###.###
###.###
###.###
#######
###.###
###.###
###.###
"""),
    ("BUTTERFLY", """
##...##
###.###
.#####.
...#...
.#####.
###.###
##...##
"""),
    ("SWISS CHEESE", """
#######
###.##.
##.##..
####...
#.#....
##.....
#......
"""),
    ("COMB", """
#######
#######
#.#.#.#
#.#.#.#
#.#.#.#
"""),
    ("RING", """
#######
#.....#
#.....#
#.....#
#.....#
#.....#
#######
"""),
    ("DONUT", """
...#...
..###..
.##.##.
##...##
.##.##.
..###..
...#...
"""),
    ("SERPENT", """
######
.....#
.....#
######
#.....
#.....
######
"""),
    ("SPIRAL", """
#######
......#
#####.#
#...#.#
#.###.#
#.....#
#######
"""),
    ("MOUNT TUX", """
#########
########.
#######..
######...
#####....
####.....
###......
##.......
#........
"""),
]


def parse_shape(text):
    cells = set()
    for i, line in enumerate(text.strip("\n").split("\n")):
        for j, ch in enumerate(line):
            if ch == "#":
                cells.add((i, j))
    return cells

BG_COLOR = (10, 8, 24, 255)
TUX_BLACK = (28, 30, 38, 255)
TUX_WHITE = (240, 240, 235, 255)
TUX_ORANGE = (245, 160, 30, 255)
COILY_PURPLE = (190, 70, 235, 255)
COILY_DARK = (140, 40, 180, 255)


def v3(x, y, z):
    return rl.Vector3(x, y, z)


def on_board(i, j):
    return (i, j) in CELLS


def cube_center(i, j):
    return (i * CS, -(i + j) * CS, j * CS)


def cube_top(i, j):
    x, y, z = cube_center(i, j)
    return (x, y + CS / 2, z)


def lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm3(a):
    m = math.sqrt(dot3(a, a)) or 1.0
    return (a[0] / m, a[1] / m, a[2] / m)


def dist3(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def facing_for(di, dj):
    # model forward is +z; yaw in degrees around Y
    return math.degrees(math.atan2(di, dj))


# ---------------------------------------------------------------- sound synth

def _synth_wav(path, segments, vol=0.4, noise=False, sr=22050):
    """Write a little square-wave chirp: segments = [(f0, f1, dur), ...]."""
    frames = []
    phase = 0.0
    for f0, f1, dur in segments:
        n = int(sr * dur)
        for k in range(n):
            t = k / max(1, n - 1)
            f = f0 + (f1 - f0) * t
            if noise:
                f *= random.uniform(0.6, 1.6)
            phase += f / sr
            s = 1.0 if (phase % 1.0) < 0.5 else -1.0
            env = min(1.0, 8.0 * min(t, 1.0 - t) + 0.15)
            frames.append(int(s * env * vol * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack("<%dh" % len(frames), *frames))


SOUND_DEFS = {
    "hop":     ([(380, 170, 0.09)], 0.28, False),
    "change":  ([(500, 900, 0.09)], 0.30, False),
    "fall":    ([(700, 60, 0.55)], 0.35, False),
    "swear":   ([(300, 900, 0.30)], 0.35, True),
    "coilyfall": ([(900, 50, 0.70)], 0.35, False),
    "disc":    ([(280, 950, 0.35)], 0.30, False),
    "catch":   ([(988, 988, 0.05), (1319, 1319, 0.10)], 0.30, False),
    "clear":   ([(523, 523, 0.09), (659, 659, 0.09), (784, 784, 0.09),
                 (1047, 1047, 0.16)], 0.32, False),
    "extra":   ([(784, 784, 0.08), (988, 988, 0.08), (1175, 1175, 0.08),
                 (1568, 1568, 0.14)], 0.32, False),
}


def load_sounds():
    os.makedirs(ASSETS, exist_ok=True)
    sounds = {}
    try:
        rl.init_audio_device()
        for name, (segs, vol, noise) in SOUND_DEFS.items():
            path = os.path.join(ASSETS, name + ".wav")
            if not os.path.exists(path):
                _synth_wav(path, segs, vol, noise)
            sounds[name] = rl.load_sound(path)
    except Exception:
        sounds = {}
    return sounds


# ---------------------------------------------------------------- draw helpers

def ellipsoid(x, y, z, sx, sy, sz, color):
    rl.rl_push_matrix()
    rl.rl_translatef(x, y, z)
    rl.rl_scalef(sx, sy, sz)
    rl.draw_sphere_ex(v3(0, 0, 0), 1.0, 10, 12, color)
    rl.rl_pop_matrix()


def draw_tux(pos, yaw, squash=1.0):
    """Tux built from primitives, standing on `pos`, facing `yaw` degrees."""
    rl.rl_push_matrix()
    rl.rl_translatef(pos[0], pos[1], pos[2])
    rl.rl_rotatef(yaw, 0, 1, 0)
    sq = squash
    rl.rl_scalef(1.12 * (1.0 + (1.0 - sq) * 0.5), 1.12 * sq,
                 1.12 * (1.0 + (1.0 - sq) * 0.5))
    # feet
    ellipsoid(-0.18, 0.06, 0.12, 0.17, 0.07, 0.26, TUX_ORANGE)
    ellipsoid(0.18, 0.06, 0.12, 0.17, 0.07, 0.26, TUX_ORANGE)
    # body
    ellipsoid(0, 0.56, 0, 0.44, 0.56, 0.42, TUX_BLACK)
    # belly
    ellipsoid(0, 0.46, 0.20, 0.34, 0.42, 0.30, TUX_WHITE)
    # head
    ellipsoid(0, 1.06, 0, 0.30, 0.28, 0.28, TUX_BLACK)
    # eyes
    ellipsoid(-0.12, 1.14, 0.20, 0.085, 0.10, 0.06, TUX_WHITE)
    ellipsoid(0.12, 1.14, 0.20, 0.085, 0.10, 0.06, TUX_WHITE)
    ellipsoid(-0.10, 1.13, 0.26, 0.035, 0.045, 0.03, TUX_BLACK)
    ellipsoid(0.10, 1.13, 0.26, 0.035, 0.045, 0.03, TUX_BLACK)
    # beak
    rl.draw_cylinder_ex(v3(0, 1.02, 0.20), v3(0, 0.97, 0.48), 0.09, 0.01, 8, TUX_ORANGE)
    # flippers
    ellipsoid(-0.46, 0.55, 0.02, 0.09, 0.30, 0.16, TUX_BLACK)
    ellipsoid(0.46, 0.55, 0.02, 0.09, 0.30, 0.16, TUX_BLACK)
    rl.rl_pop_matrix()


BALL_COLORS = {"red": (232, 44, 44, 255), "green": (60, 215, 95, 255),
               "egg": COILY_PURPLE, "slick": (80, 200, 60, 255)}


def draw_ball(pos, kind, t):
    color = BALL_COLORS[kind]
    r = 0.48 if kind == "egg" else 0.42
    rl.draw_sphere_ex(v3(pos[0], pos[1] + r, pos[2]), r, 12, 14, color)
    # cartoon highlight toward the camera
    hl = (pos[0] + r * 0.4, pos[1] + r * 1.35, pos[2] + r * 0.4)
    rl.draw_sphere_ex(v3(*hl), r * 0.22, 6, 8, (255, 255, 255, 200))
    if kind == "slick":  # Slick gets shades
        ellipsoid(pos[0] + 0.16, pos[1] + 0.55, pos[2] + 0.16, 0.13, 0.09, 0.13,
                  (20, 20, 30, 255))
        ellipsoid(pos[0] + 0.30, pos[1] + 0.55, pos[2] - 0.02, 0.13, 0.09, 0.13,
                  (20, 20, 30, 255))


def draw_coily(pos, t, yaw):
    sway = math.sin(t * 9.0) * 0.07
    rl.rl_push_matrix()
    rl.rl_translatef(pos[0], pos[1], pos[2])
    rl.rl_rotatef(yaw, 0, 1, 0)
    rl.draw_sphere_ex(v3(0, 0.36, 0), 0.40, 12, 14, COILY_DARK)
    rl.draw_sphere_ex(v3(sway, 0.80, 0), 0.32, 12, 14, COILY_PURPLE)
    rl.draw_sphere_ex(v3(-sway, 1.14, 0), 0.26, 12, 14, COILY_DARK)
    rl.draw_sphere_ex(v3(sway * 0.5, 1.48, 0.02), 0.30, 12, 14, COILY_PURPLE)
    ellipsoid(-0.13, 1.58, 0.24, 0.09, 0.11, 0.05, TUX_WHITE)
    ellipsoid(0.13, 1.58, 0.24, 0.09, 0.11, 0.05, TUX_WHITE)
    ellipsoid(-0.11, 1.57, 0.29, 0.04, 0.05, 0.03, (10, 10, 10, 255))
    ellipsoid(0.11, 1.57, 0.29, 0.04, 0.05, 0.03, (10, 10, 10, 255))
    rl.rl_pop_matrix()


def draw_disc(pos, t):
    spin = (t * 240.0) % 360.0
    rl.rl_push_matrix()
    rl.rl_translatef(pos[0], pos[1], pos[2])
    rl.rl_rotatef(spin, 0, 1, 0)
    rl.draw_cylinder(v3(0, -0.16, 0), 0.78, 0.78, 0.14, 16, (250, 230, 90, 255))
    rl.draw_cylinder(v3(0, -0.02, 0), 0.62, 0.62, 0.06, 16, (120, 230, 120, 255))
    rl.draw_cube(v3(0, -0.09, 0), 1.62, 0.06, 0.18, (240, 90, 60, 255))
    rl.draw_cube(v3(0, -0.09, 0), 0.18, 0.06, 1.62, (240, 90, 60, 255))
    rl.rl_pop_matrix()


def shade(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f), c[3])


def draw_cube_cell(i, j, top_color, scheme):
    cx, cy, cz = cube_center(i, j)
    t = 0.06
    rl.draw_cube(v3(cx, cy, cz), CS - 0.08, CS - 0.08, CS - 0.08,
                 shade(scheme["side_r"], 0.55))
    # the two faces toward the camera (+x and +z) get distinct shades
    rl.draw_cube(v3(cx + CS / 2 - t / 2, cy, cz), t, CS, CS - 0.02, scheme["side_r"])
    rl.draw_cube(v3(cx, cy, cz + CS / 2 - t / 2), CS - 0.02, CS, t, scheme["side_l"])
    rl.draw_cube(v3(cx, cy + CS / 2 - t / 2, cz), CS, t, CS, top_color)
    rl.draw_cube_wires(v3(cx, cy, cz), CS + 0.01, CS + 0.01, CS + 0.01, (12, 10, 26, 255))


def draw_shadow(entity):
    if not on_board(getattr(entity, "ti", entity.i), getattr(entity, "tj", entity.j)):
        return
    i = entity.ti if entity.jumping else entity.i
    j = entity.tj if entity.jumping else entity.j
    if not on_board(i, j):
        return
    top = cube_top(i, j)
    if entity.pos[1] > top[1] + 0.05:
        rl.draw_cylinder(v3(top[0], top[1] + 0.02, top[2]), 0.34, 0.34, 0.02, 12,
                         (0, 0, 0, 90))


def draw_iso_cube_2d(x, y, s, top, left, right):
    """Tiny 2-D isometric cube for the HUD 'CHANGE TO' indicator."""
    a = rl.Vector2(x, y - s)
    b = rl.Vector2(x + s, y - s // 2)
    c = rl.Vector2(x, y)
    d = rl.Vector2(x - s, y - s // 2)
    e = rl.Vector2(x - s, y + s // 2 + s // 4)
    f = rl.Vector2(x, y + s)
    g = rl.Vector2(x + s, y + s // 2 + s // 4)
    rl.draw_triangle_fan([a, d, c, b], 4, top)
    rl.draw_triangle_fan([d, e, f, c], 4, left)
    rl.draw_triangle_fan([c, f, g, b], 4, right)
    # both windings so culling can't hide a face
    rl.draw_triangle_fan([b, c, d, a], 4, top)
    rl.draw_triangle_fan([c, f, e, d], 4, left)
    rl.draw_triangle_fan([b, g, f, c], 4, right)


# ---------------------------------------------------------------- entities

class Hopper:
    """Anything that lives on the pyramid and hops between cube tops."""

    def __init__(self, i, j, drop_in=False):
        self.i, self.j = i, j
        self.ti, self.tj = i, j
        self.pos = cube_top(i, j)
        self.jumping = False
        self.jt = 0.0
        self.jdur = 0.3
        self.p0 = self.p1 = self.pos
        self.falling = False
        self.fall_vy = 0.0
        self.yaw = 180.0
        self.squash = 0.0
        if drop_in:
            top = cube_top(i, j)
            self.jumping = True
            self.p0 = (top[0], top[1] + 7.0, top[2])
            self.p1 = top
            self.pos = self.p0
            self.jdur = 0.55
            self.jt = 0.0
            self.ti, self.tj = i, j
            self._drop = True
        else:
            self._drop = False

    def start_hop(self, di, dj, dur):
        self.ti, self.tj = self.i + di, self.j + dj
        self.p0 = cube_top(self.i, self.j)
        self.p1 = cube_top(self.ti, self.tj)
        self.jt = 0.0
        self.jdur = dur
        self.jumping = True
        self._drop = False
        self.yaw = facing_for(di, dj)

    def update(self, dt):
        """Returns True on the frame the hopper lands."""
        self.squash = max(0.0, self.squash - dt)
        if self.falling:
            self.fall_vy -= 30.0 * dt
            self.pos = (self.pos[0], self.pos[1] + self.fall_vy * dt, self.pos[2])
            return False
        if self.jumping:
            self.jt += dt
            s = min(1.0, self.jt / self.jdur)
            base = lerp3(self.p0, self.p1, s)
            arc = 0.0 if self._drop else CS * 0.75 * 4.0 * s * (1.0 - s)
            self.pos = (base[0], base[1] + arc, base[2])
            if s >= 1.0:
                self.jumping = False
                self.squash = 0.12
                if on_board(self.ti, self.tj):
                    self.i, self.j = self.ti, self.tj
                    self.pos = cube_top(self.i, self.j)
                    return True
                # jumped off the pyramid
                self.falling = True
                self.fall_vy = 2.0
                return True
        return False

    @property
    def grounded(self):
        return not self.jumping and not self.falling

    def squash_scale(self):
        return 1.0 - (self.squash / 0.12) * 0.25 if self.squash > 0 else 1.0


class Player(Hopper):
    def __init__(self, i=0, j=0, drop_in=True):
        super().__init__(i, j, drop_in=drop_in)
        self.riding = None       # Disc being ridden
        self.ride_t = 0.0
        self.ride_start = self.pos
        self.ride_target = (i, j)
        self.alive = True
        self.yaw = 45.0          # face the camera on spawn


class Ball(Hopper):
    """Red ball (deadly), green ball (freeze), Coily egg, or Slick."""

    def __init__(self, kind, i, j, wait, dur):
        super().__init__(i, j, drop_in=True)
        self.kind = kind
        self.wait = wait
        self.dur = dur
        self.timer = wait
        self.dead = False

    @property
    def deadly(self):
        return self.kind in ("red", "egg")

    def ai(self, game, dt):
        if not self.grounded:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        downs = [d for d in (DIR_DR, DIR_DL)
                 if on_board(self.i + d[0], self.j + d[1])]
        if self.kind == "egg" and not downs:
            return  # timer stays expired; the game turns the egg into Coily
        self.timer = self.wait
        di, dj = random.choice(downs) if downs else random.choice([DIR_DR, DIR_DL])
        self.start_hop(di, dj, self.dur)
        game.play("hop")


class Coily(Hopper):
    def __init__(self, i, j, wait, dur):
        super().__init__(i, j)
        self.wait = wait
        self.dur = dur
        self.timer = wait + 0.5   # transformation pause
        self.dead = False
        self.deadly = True
        self.kind = "coily"

    def ai(self, game, dt):
        if not self.grounded:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        self.timer = self.wait
        target = game.player.pos
        lured = game.player.riding is not None or game.player.falling
        best, best_d = None, 1e9
        for di, dj in (DIR_UR, DIR_UL, DIR_DR, DIR_DL):
            ni, nj = self.i + di, self.j + dj
            if not on_board(ni, nj) and not lured:
                continue
            d = dist3(cube_top(ni, nj), target)
            if d < best_d:
                best, best_d = (di, dj), d
        if best:
            self.start_hop(best[0], best[1], self.dur)
            game.play("hop")


class Disc:
    def __init__(self, spot):
        self.key = spot                        # off-board (i, j) it services
        x, y, z = cube_top(*spot)
        ox = -0.45 if spot[0] < 0 else 0.08
        oz = -0.45 if spot[1] < 0 else 0.08
        self.pos = (x + ox, y + 0.35, z + oz)


# ---------------------------------------------------------------- board

class Board:
    def __init__(self):
        self.cells = {}
        self.scheme = SCHEMES[0]
        self.steps = 1
        self.toggle = False
        self.reset(1)

    def reset(self, difficulty):
        global CELLS
        idx = (difficulty - 1) % len(SHAPES)
        self.name, text = SHAPES[idx]
        shape = parse_shape(text)
        CELLS = shape
        self.cells = {c: 0 for c in shape}
        self.scheme = SCHEMES[(difficulty - 1) % len(SCHEMES)]
        # color rules escalate the way the arcade rounds did
        self.steps = 2 if 9 <= difficulty <= 16 else 1
        self.toggle = difficulty >= 17
        # top cell: shallowest, most central; it's the spawn + disc destination
        self.top_cell = min(shape, key=lambda c: (c[0] + c[1], abs(c[0] - c[1]), c[0]))
        ti, tj = self.top_cell
        self.spawn_cells = [c for c in ((ti + 1, tj), (ti, tj + 1)) if c in shape]
        if not self.spawn_cells:
            self.spawn_cells = [self.top_cell]
        # disc spots: exterior cells one up-hop off the shape's edge
        spots = set()
        for (i, j) in shape:
            for (a, b) in ((i - 1, j), (i, j - 1)):
                if (a, b) not in shape and (a < 0 or b < 0):
                    spots.add((a, b))
        spots -= {(ti - 1, tj), (ti, tj - 1)}   # not right beside the start
        self.disc_spots = sorted(spots)
        self.fall_y = -(max(i + j for (i, j) in shape) * CS) - 8.0

    def is_bottom(self, i, j):
        return not on_board(i + 1, j) and not on_board(i, j + 1)

    def top_color(self, i, j):
        st = self.cells[(i, j)]
        s = self.scheme
        if self.steps == 2:
            return (s["base"], s["mid"], s["target"])[st]
        return (s["base"], s["target"])[st]

    def land(self, i, j):
        """Advance the cube color; returns points scored."""
        st = self.cells[(i, j)]
        if st < self.steps:
            st += 1
            self.cells[(i, j)] = st
            return 25 if st == self.steps else 15
        if self.toggle:
            self.cells[(i, j)] = 0
        return 0

    def revert(self, i, j):
        self.cells[(i, j)] = 0

    def complete(self):
        return all(st == self.steps for st in self.cells.values())


# ---------------------------------------------------------------- game

KEYMAP = [
    (rl.KeyboardKey.KEY_UP, DIR_UR), (rl.KeyboardKey.KEY_DOWN, DIR_DL),
    (rl.KeyboardKey.KEY_LEFT, DIR_UL), (rl.KeyboardKey.KEY_RIGHT, DIR_DR),
    (rl.KeyboardKey.KEY_W, DIR_UR), (rl.KeyboardKey.KEY_S, DIR_DL),
    (rl.KeyboardKey.KEY_A, DIR_UL), (rl.KeyboardKey.KEY_D, DIR_DR),
]

EXTRA_LIFE_AT = [8000, 22000, 36000, 50000, 70000]

MENU, PLAYING, DYING, ROUND_CLEAR, GAME_OVER, ENTER_NAME, HISCORES = range(7)

HISCORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "highscores.json")
DEFAULT_SCORES = [{"name": "TUX", "score": 5000, "level": 2},
                  {"name": "GNU", "score": 3000, "level": 1},
                  {"name": "LNX", "score": 1000, "level": 1}]


def load_hiscores():
    try:
        with open(HISCORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sorted(data, key=lambda e: -e["score"])[:10]
    except (OSError, ValueError, KeyError, TypeError):
        return list(DEFAULT_SCORES)


def save_hiscores(scores):
    try:
        with open(HISCORE_PATH, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass


class Game:
    def __init__(self, sounds):
        self.sounds = sounds
        self.cam = rl.Camera3D()
        self.cam.up = v3(0, 1, 0)
        self.cam.fovy = 21.0
        self.cam.projection = rl.CameraProjection.CAMERA_ORTHOGRAPHIC
        self.board = Board()
        self.fit_camera()
        self.time = 0.0
        self.state = MENU
        self.player = Player()
        self.enemies = []
        self.discs = []
        self.popups = []
        self.buffered = None
        self.paused = False
        self.smoke_moves = []
        self.menu_idx = 0
        self.hiscores = load_hiscores()
        self.name_entry = ""
        self.quit = False
        self.start_level = 1
        self.reset_scores()

    # ---------------- helpers

    def fit_camera(self):
        """Frame the current shape: classic corner angle, size to fit."""
        pts = [cube_center(i, j) for (i, j) in self.board.cells]
        # keep the airspace above the top cube in frame for disc rides
        tx, ty, tz = cube_top(*self.board.top_cell)
        pts.append((tx, ty + 4.5, tz))
        n = len(pts)
        tgt = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n + 0.8,
               sum(p[2] for p in pts) / n)
        off = (22.0, 18.7, 22.0)
        self.cam.target = v3(*tgt)
        self.cam.position = v3(tgt[0] + off[0], tgt[1] + off[1], tgt[2] + off[2])
        fwd = norm3((-off[0], -off[1], -off[2]))
        right = norm3(cross3(fwd, (0, 1, 0)))
        up = cross3(right, fwd)
        xs = [dot3((p[0] - tgt[0], p[1] - tgt[1], p[2] - tgt[2]), right) for p in pts]
        ys = [dot3((p[0] - tgt[0], p[1] - tgt[1], p[2] - tgt[2]), up) for p in pts]
        pad = CS * 1.8
        need_h = (max(ys) - min(ys)) + 2 * pad + 2.5   # head room for the HUD
        need_w = ((max(xs) - min(xs)) + 2 * pad) / (SCREEN_W / SCREEN_H)
        self.cam.fovy = max(17.0, need_h, need_w)

    def play(self, name):
        snd = self.sounds.get(name)
        if snd:
            rl.play_sound(snd)

    def popup(self, text, world_pos, color=(255, 255, 255, 255)):
        sp = rl.get_world_to_screen(v3(*world_pos), self.cam)
        self.popups.append({"text": text, "x": sp.x, "y": sp.y, "t": 1.2, "color": color})

    def add_score(self, pts, world_pos=None, label=None):
        self.score += pts
        if self.extra_idx < len(EXTRA_LIFE_AT) and self.score >= EXTRA_LIFE_AT[self.extra_idx]:
            self.extra_idx += 1
            self.lives += 1
            self.play("extra")
            self.popup("EXTRA LIFE!", self.player.pos, (120, 255, 140, 255))
        if label and world_pos:
            self.popup(label, world_pos, (255, 230, 120, 255))

    def reset_scores(self):
        self.score = 0
        self.lives = 3
        self.difficulty = 1
        self.extra_idx = 0

    def score_qualifies(self):
        if self.score <= 0:
            return False
        return len(self.hiscores) < 10 or self.score > self.hiscores[-1]["score"]

    # ---------------- round / game flow

    @property
    def level(self):
        return self.difficulty

    def start_game(self, start_level=1):
        self.reset_scores()
        self.difficulty = max(1, min(len(SHAPES), start_level))
        self.start_round(first=True)
        self.state = PLAYING

    def start_round(self, first=False):
        self.board.reset(self.difficulty)
        self.fit_camera()
        self.player = Player(*self.board.top_cell, drop_in=True)
        self.enemies = []
        self.popups = []
        self.buffered = None
        self.freeze_t = 0.0
        self.round_intro = 1.6
        self.state_t = 0.0
        d = self.difficulty
        self.ball_interval = max(1.6, 3.4 - 0.12 * d)
        self.ball_timer = self.ball_interval + 1.0
        self.coily_timer = 4.0
        self.slick_timer = 8.0
        self.green_timer = 10.0
        self.ball_wait = max(0.22, 0.55 - 0.02 * d)
        self.ball_dur = max(0.28, 0.45 - 0.012 * d)
        self.coily_wait = max(0.16, 0.42 - 0.02 * d)
        self.coily_dur = max(0.26, 0.42 - 0.012 * d)
        spots = self.board.disc_spots
        self.discs = [Disc(s) for s in random.sample(spots, min(2, len(spots)))]

    def next_round(self):
        self.add_score(50 * len(self.discs))
        self.add_score(750 + 250 * self.difficulty)
        self.difficulty += 1
        self.start_round()
        self.state = PLAYING

    def kill_player(self, cause):
        self.player.alive = False
        self.death_cause = cause
        self.state = DYING
        self.state_t = 0.0
        if cause == "enemy":
            self.play("swear")

    def after_death(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = GAME_OVER
            self.state_t = 0.0
            return
        # arcade style: enemies clear, Tux comes back on the cube he died on
        i, j = self.player.i, self.player.j
        self.enemies = []
        self.coily_timer = 4.0
        self.ball_timer = self.ball_interval + 0.8
        self.player = Player(i, j, drop_in=True)
        self.buffered = None
        self.freeze_t = 0.0
        self.state = PLAYING

    # ---------------- spawning

    def spawn_cell(self):
        return random.choice(self.board.spawn_cells)

    def update_spawns(self, dt):
        if self.round_intro > 0 or self.freeze_t > 0:
            return
        self.ball_timer -= dt
        self.coily_timer -= dt
        self.slick_timer -= dt
        self.green_timer -= dt
        balls = [e for e in self.enemies if isinstance(e, Ball) and e.kind == "red"]
        max_balls = 2 if self.difficulty < 5 else 3
        if self.ball_timer <= 0 and len(balls) < max_balls:
            self.ball_timer = self.ball_interval
            i, j = self.spawn_cell()
            self.enemies.append(Ball("red", i, j, self.ball_wait, self.ball_dur))
        has_coily = any(isinstance(e, Coily) or
                        (isinstance(e, Ball) and e.kind == "egg") for e in self.enemies)
        if self.coily_timer <= 0 and not has_coily:
            i, j = self.spawn_cell()
            self.enemies.append(Ball("egg", i, j, self.ball_wait + 0.08, self.ball_dur))
        has_slick = any(isinstance(e, Ball) and e.kind == "slick" for e in self.enemies)
        if self.slick_timer <= 0 and not has_slick and self.difficulty >= 2:
            self.slick_timer = 14.0
            i, j = self.spawn_cell()
            self.enemies.append(Ball("slick", i, j, self.ball_wait + 0.1, self.ball_dur))
        has_green = any(isinstance(e, Ball) and e.kind == "green" for e in self.enemies)
        if self.green_timer <= 0 and not has_green:
            self.green_timer = 13.0
            i, j = self.spawn_cell()
            self.enemies.append(Ball("green", i, j, self.ball_wait + 0.1, self.ball_dur))

    # ---------------- update

    def queue_move(self, d):
        self.buffered = d

    def update(self, dt):
        self.time += dt
        for p in self.popups:
            p["t"] -= dt
            p["y"] -= 30 * dt
        self.popups = [p for p in self.popups if p["t"] > 0]

        if self.state == MENU:
            n = 3
            if rl.is_key_pressed(rl.KeyboardKey.KEY_DOWN) or \
                    rl.is_key_pressed(rl.KeyboardKey.KEY_S):
                self.menu_idx = (self.menu_idx + 1) % n
                self.play("hop")
            if rl.is_key_pressed(rl.KeyboardKey.KEY_UP) or \
                    rl.is_key_pressed(rl.KeyboardKey.KEY_W):
                self.menu_idx = (self.menu_idx - 1) % n
                self.play("hop")
            if rl.is_key_pressed(rl.KeyboardKey.KEY_ENTER) or \
                    rl.is_key_pressed(rl.KeyboardKey.KEY_SPACE):
                self.play("change")
                if self.menu_idx == 0:
                    self.start_game(self.start_level)
                elif self.menu_idx == 1:
                    self.state = HISCORES
                else:
                    self.quit = True
            return
        if self.state == HISCORES:
            if rl.is_key_pressed(rl.KeyboardKey.KEY_ENTER) or \
                    rl.is_key_pressed(rl.KeyboardKey.KEY_SPACE) or \
                    rl.is_key_pressed(rl.KeyboardKey.KEY_BACKSPACE):
                self.state = MENU
            return
        if self.state == ENTER_NAME:
            ch = rl.get_char_pressed()
            while ch > 0:
                c = chr(ch).upper()
                if c.isalnum() and len(self.name_entry) < 3:
                    self.name_entry += c
                    self.play("hop")
                ch = rl.get_char_pressed()
            if rl.is_key_pressed(rl.KeyboardKey.KEY_BACKSPACE) and self.name_entry:
                self.name_entry = self.name_entry[:-1]
            if rl.is_key_pressed(rl.KeyboardKey.KEY_ENTER) and self.name_entry:
                self.hiscores.append({"name": self.name_entry, "score": self.score,
                                      "level": self.level})
                self.hiscores = sorted(self.hiscores,
                                       key=lambda e: -e["score"])[:10]
                save_hiscores(self.hiscores)
                self.play("extra")
                self.state = HISCORES
            return
        if self.state == GAME_OVER:
            self.state_t += dt
            if self.state_t > 1.5 and self.score_qualifies():
                self.name_entry = ""
                self.state = ENTER_NAME
                return
            if rl.is_key_pressed(rl.KeyboardKey.KEY_ENTER) and self.state_t > 1.0:
                self.state = MENU
            return
        if self.state == ROUND_CLEAR:
            self.state_t += dt
            if self.state_t > 2.6:
                self.next_round()
            return
        if self.state == DYING:
            self.state_t += dt
            if self.death_cause == "fall":
                self.player.update(dt)
            if self.state_t > 1.8:
                self.after_death()
            return

        # ---- PLAYING
        if rl.is_key_pressed(rl.KeyboardKey.KEY_P):
            self.paused = not self.paused
        if self.paused:
            return
        self.round_intro = max(0.0, self.round_intro - dt)
        self.freeze_t = max(0.0, self.freeze_t - dt)

        for key, d in KEYMAP:
            if rl.is_key_pressed(key):
                self.buffered = d
        if self.smoke_moves:
            t, d = self.smoke_moves[0]
            if self.time >= t:
                self.buffered = d
                self.smoke_moves.pop(0)

        p = self.player
        if p.riding is not None:
            self.update_ride(dt)
        else:
            if p.grounded and self.buffered and p.alive:
                di, dj = self.buffered
                self.buffered = None
                ni, nj = p.i + di, p.j + dj
                p.start_hop(di, dj, PLAYER_HOP)
                self.play("hop")
            landed = p.update(dt)
            if landed:
                if not p.falling:       # landed on a real cube
                    pts = self.board.land(p.i, p.j)
                    if pts:
                        self.add_score(pts)
                        self.play("change")
                    if self.board.complete():
                        self.state = ROUND_CLEAR
                        self.state_t = 0.0
                        self.enemies = []
                        self.play("clear")
                        return
                else:
                    disc = next((d for d in self.discs if d.key == (p.ti, p.tj)), None)
                    if disc:
                        self.board_disc(disc)
                    else:
                        self.play("fall")
            if p.falling and p.pos[1] < self.board.fall_y:
                self.kill_player("fall_done")
                self.state_t = 1.2  # already fell; short pause

        # enemies
        self.update_spawns(dt)
        frozen = self.freeze_t > 0
        for e in list(self.enemies):
            if not frozen:
                e.ai(self, dt)
                landed = e.update(dt)
                if landed and not e.falling:
                    if isinstance(e, Ball) and e.kind == "slick":
                        self.board.revert(e.i, e.j)
                    if isinstance(e, Coily) and e.falling:
                        pass
                if isinstance(e, Coily) and e.falling and not e.dead:
                    e.dead = True
                    self.add_score(500, e.pos, "500")
                    self.play("coilyfall")
                    self.coily_timer = 4.5
                if isinstance(e, Ball) and e.kind == "egg" and e.grounded \
                        and self.board.is_bottom(e.i, e.j) and e.timer <= 0:
                    self.enemies.remove(e)
                    c = Coily(e.i, e.j, self.coily_wait, self.coily_dur)
                    self.enemies.append(c)
                    continue
            if e.pos[1] < self.board.fall_y - 10:
                self.enemies.remove(e)

        # collisions
        if p.alive and p.riding is None and not p.falling:
            for e in list(self.enemies):
                if dist3(p.pos, e.pos) < 0.85:
                    if getattr(e, "deadly", False):
                        self.kill_player("enemy")
                        break
                    if isinstance(e, Ball) and e.kind == "green":
                        self.enemies.remove(e)
                        self.freeze_t = 4.0
                        self.add_score(100, e.pos, "100")
                        self.play("catch")
                    elif isinstance(e, Ball) and e.kind == "slick":
                        self.enemies.remove(e)
                        self.add_score(300, e.pos, "300")
                        self.play("catch")

    def board_disc(self, disc):
        """Classic Q*bert disc ride: carries Tux back to the top cube while
        Coily, mid-chase, hops off the edge after him."""
        p = self.player
        p.falling = False
        p.riding = disc
        p.ride_t = 0.0
        p.ride_start = disc.pos
        p.pos = disc.pos
        p.ride_target = self.board.top_cell
        self.discs.remove(disc)
        self.play("disc")

    def update_ride(self, dt):
        p = self.player
        p.ride_t += dt
        dur = 2.0
        s = min(1.0, p.ride_t / dur)
        ease = s * s * (3 - 2 * s)
        top = cube_top(*p.ride_target)
        end = (top[0], top[1] + 3.2, top[2])
        pos = lerp3(p.ride_start, end, ease)
        lift = math.sin(min(1.0, s * 2) * math.pi / 2) * 1.5
        p.riding.pos = (pos[0], pos[1] + lift * (1 - s), pos[2])
        p.pos = (p.riding.pos[0], p.riding.pos[1] + 0.1, p.riding.pos[2])
        if s >= 1.0:
            # hop off onto the top cube
            p.riding = None
            p.jumping = True
            p._drop = True
            p.p0 = p.pos
            p.p1 = top
            p.jt = 0.0
            p.jdur = 0.4
            p.ti, p.tj = p.ride_target

    # ---------------- drawing

    def draw(self):
        rl.clear_background(BG_COLOR)
        rl.begin_mode_3d(self.cam)
        flash = self.state == ROUND_CLEAR
        frame = int(self.time * 14)
        for (i, j) in self.board.cells:
            if flash:
                top = FLASH_PALETTE[(frame + i + j) % len(FLASH_PALETTE)]
            else:
                top = self.board.top_color(i, j)
            draw_cube_cell(i, j, top, self.board.scheme)
        for d in self.discs:
            draw_disc(d.pos, self.time)
        p = self.player
        if p.riding is not None:
            draw_disc(p.riding.pos, self.time)
        if self.state not in (MENU, HISCORES):
            for e in self.enemies:
                draw_shadow(e)
                if isinstance(e, Coily):
                    draw_coily(e.pos, self.time, e.yaw)
                else:
                    draw_ball(e.pos, e.kind, self.time)
            if self.state not in (GAME_OVER, ENTER_NAME):
                draw_shadow(p)
                draw_tux(p.pos, p.yaw, p.squash_scale())
        rl.end_mode_3d()
        self.draw_hud()

    def draw_hud(self):
        white = (240, 240, 240, 255)
        yellow = (255, 220, 80, 255)
        dim = (170, 170, 190, 255)
        if self.state == MENU:
            rl.draw_rectangle(0, 0, SCREEN_W, SCREEN_H, (10, 8, 24, 150))
            self.center_text("TUX*BERT", 120, 72, yellow)
            self.center_text("a 3-D penguin arcade tribute", 200, 20, white)
            options = ["START GAME", "HIGH SCORES", "QUIT"]
            for k, opt in enumerate(options):
                y = 320 + k * 56
                sel = k == self.menu_idx
                color = yellow if sel else white
                self.center_text(opt, y, 34, color)
                if sel and int(self.time * 3) % 2 == 0:
                    w = rl.measure_text(opt, 34)
                    rl.draw_text(">", (SCREEN_W - w) // 2 - 40, y, 34, yellow)
                    rl.draw_text("<", (SCREEN_W + w) // 2 + 18, y, 34, yellow)
            hi = self.hiscores[0]["score"] if self.hiscores else 0
            self.center_text(f"HI-SCORE  {hi}", 260, 22, (140, 240, 160, 255))
            self.center_text(
                "ARROWS HOP DIAGONALLY   .   CHANGE EVERY CUBE   .   AVOID COILY",
                640, 16, dim)
            return
        if self.state == HISCORES:
            rl.draw_rectangle(0, 0, SCREEN_W, SCREEN_H, (10, 8, 24, 190))
            self.center_text("HIGH SCORES", 90, 48, yellow)
            for k, e in enumerate(self.hiscores):
                y = 180 + k * 42
                color = yellow if k == 0 else white
                rl.draw_text(f"{k + 1:2d}.", 300, y, 28, dim)
                rl.draw_text(e["name"][:3], 370, y, 28, color)
                txt = f"{e['score']:>8d}"
                rl.draw_text(txt, 640 - rl.measure_text(txt, 28), y, 28, color)
                rl.draw_text(f"L{e.get('level', 1)}", 620, y, 28, dim)
            if int(self.time * 2) % 2 == 0:
                self.center_text("PRESS ENTER", 630, 24, white)
            return
        if self.state == ENTER_NAME:
            rl.draw_rectangle(0, 0, SCREEN_W, SCREEN_H, (10, 8, 24, 190))
            self.center_text("NEW HIGH SCORE!", 160, 48, (140, 240, 160, 255))
            self.center_text(f"{self.score}", 230, 36, yellow)
            self.center_text("ENTER YOUR INITIALS", 320, 24, white)
            shown = self.name_entry + ("_" if len(self.name_entry) < 3 and
                                       int(self.time * 3) % 2 == 0 else "")
            self.center_text(shown if shown else "_", 380, 52, yellow)
            self.center_text("TYPE 1-3 LETTERS  .  ENTER TO CONFIRM", 470, 18, dim)
            return

        rl.draw_text("SCORE", 24, 16, 20, yellow)
        rl.draw_text(f"{self.score:07d}", 24, 40, 30, white)
        lvl = f"LEVEL {self.level}/{len(SHAPES)}" if self.level <= len(SHAPES) \
            else f"LEVEL {self.level}"
        rl.draw_text(lvl, SCREEN_W - 24 - rl.measure_text(lvl, 20), 16, 20, yellow)
        name = self.board.name
        rl.draw_text(name, SCREEN_W - 24 - rl.measure_text(name, 18), 42, 18, dim)
        # change-to indicator
        rl.draw_text("CHANGE TO", 24, 92, 16, (170, 170, 190, 255))
        s = self.board.scheme
        tgt = s["target"]
        draw_iso_cube_2d(60, 140, 22, tgt, s["side_l"], s["side_r"])
        # lives
        for k in range(max(0, self.lives - 1)):
            x = 30 + k * 34
            rl.draw_circle(x, 210, 11, TUX_BLACK)
            rl.draw_circle(x, 213, 6, TUX_WHITE)
            rl.draw_circle(x, 204, 3, TUX_ORANGE)
        if self.freeze_t > 0:
            self.center_text("FREEZE!", 90, 26, (140, 240, 160, 255))
        if self.round_intro > 0 and self.state == PLAYING:
            self.center_text(f"LEVEL {self.level}", 280, 40, yellow)
            self.center_text(self.board.name, 330, 26, white)
        if self.paused:
            self.center_text("PAUSED", 330, 44, white)

        if self.state == DYING and self.death_cause == "enemy":
            sp = rl.get_world_to_screen(
                v3(self.player.pos[0], self.player.pos[1] + 2.0, self.player.pos[2]),
                self.cam)
            w, h = 120, 40
            rect = rl.Rectangle(sp.x - w / 2, sp.y - h, w, h)
            rl.draw_rectangle_rounded(rect, 0.4, 6, (250, 250, 250, 255))
            rl.draw_triangle(rl.Vector2(sp.x - 10, sp.y - 2),
                             rl.Vector2(sp.x + 10, sp.y - 2),
                             rl.Vector2(sp.x, sp.y + 12), (250, 250, 250, 255))
            rl.draw_text("@!#?@!", int(sp.x - w / 2 + 16), int(sp.y - h + 10), 22,
                         (200, 30, 30, 255))
        if self.state == ROUND_CLEAR:
            self.center_text("LEVEL CLEAR!", 300, 44, yellow)
        if self.state == GAME_OVER:
            self.center_text("GAME OVER", 300, 56, (245, 90, 90, 255))
            self.center_text(f"FINAL SCORE  {self.score}", 380, 26, white)
            if self.state_t > 1.0 and int(self.time * 2) % 2 == 0:
                self.center_text("PRESS ENTER", 560, 26, white)

        for p in self.popups:
            a = int(255 * min(1.0, p["t"] / 0.4))
            c = p["color"]
            rl.draw_text(p["text"], int(p["x"]), int(p["y"]), 22, (c[0], c[1], c[2], a))

    def center_text(self, text, y, size, color):
        w = rl.measure_text(text, size)
        rl.draw_text(text, (SCREEN_W - w) // 2, y, size, color)


# ---------------------------------------------------------------- main

def main():
    smoke = "--smoke" in sys.argv
    start_level = 1
    if "--level" in sys.argv:
        try:
            start_level = int(sys.argv[sys.argv.index("--level") + 1])
        except (ValueError, IndexError):
            pass
    rl.set_config_flags(rl.ConfigFlags.FLAG_MSAA_4X_HINT | rl.ConfigFlags.FLAG_VSYNC_HINT)
    rl.init_window(SCREEN_W, SCREEN_H, "TUX*BERT")
    rl.set_target_fps(60)
    sounds = load_sounds()
    game = Game(sounds)
    game.start_level = max(1, min(len(SHAPES), start_level))
    if smoke:
        game.smoke_moves = [(2.0, DIR_UL), (5.4, DIR_DL), (5.9, DIR_DR),
                            (6.4, DIR_DL)]
    shots = {0.8: "smoke_menu.png", 3.2: "smoke_ride.png", 5.2: "smoke.png"}
    t = 0.0
    started = False
    egg_spawned = False
    while not rl.window_should_close() and not game.quit:
        dt = min(rl.get_frame_time(), 0.05)
        game.update(dt)
        rl.begin_drawing()
        game.draw()
        rl.end_drawing()
        if smoke:
            t += dt
            for when in list(shots):
                if t > when:
                    rl.take_screenshot(shots.pop(when))
            if t > 1.0 and not started:
                started = True
                game.start_game(game.start_level)
                # plant a disc one up-left hop from the start cube
                game.discs = [Disc((-1, 0))] + game.discs[1:]
            if t > 1.4 and not egg_spawned and game.state == PLAYING:
                egg_spawned = True
                game.enemies.append(Coily(5, 1, game.coily_wait, game.coily_dur))
                game.enemies.append(Ball("red", 1, 0, game.ball_wait,
                                         game.ball_dur))
            if t > 9.4:
                break
    rl.close_window()


if __name__ == "__main__":
    main()
