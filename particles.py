"""Lightweight particle system for juicy event feedback.

Each particle is a vector + lifetime + draw spec. Emitters add particles in
batches keyed to gameplay events: pair-match (gold sparks), declare (wide
slow burst), penalty (red embers), achievement (white shimmer). Capped at
~400 live particles to keep frame budget honest.
"""
import math
import random
import pygame


MAX_PARTICLES = 400


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "ax", "ay", "life", "max_life",
                 "size", "color", "spin", "rot", "kind", "drag")

    def __init__(self, x, y, vx, vy, life, color, size=4, ax=0.0, ay=0.0,
                 kind="dot", spin=0.0, drag=0.92):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.ax = ax
        self.ay = ay
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.spin = spin
        self.rot = random.uniform(0, math.pi * 2)
        self.kind = kind
        self.drag = drag

    def update(self, dt):
        self.vx += self.ax * dt
        self.vy += self.ay * dt
        self.vx *= self.drag ** (60 * dt)
        self.vy *= self.drag ** (60 * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rot += self.spin * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    @property
    def t(self):
        return max(0.0, min(1.0, 1.0 - self.life / self.max_life))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        if len(self.particles) > MAX_PARTICLES:
            self.particles = self.particles[-MAX_PARTICLES:]

    def draw(self, screen):
        for p in self.particles:
            self._draw_one(screen, p)

    def _draw_one(self, screen, p):
        alpha = int(255 * (1.0 - p.t))
        if alpha <= 0:
            return
        color = (*p.color, alpha)
        if p.kind == "spark":
            tail_x = p.x - p.vx * 0.02
            tail_y = p.y - p.vy * 0.02
            surf = pygame.Surface((max(2, int(p.size * 2)), max(2, int(p.size * 2))), pygame.SRCALPHA)
            pygame.draw.line(surf, color, (0, surf.get_height() // 2),
                             (surf.get_width() - 1, surf.get_height() // 2),
                             max(1, int(p.size / 2)))
            screen.blit(surf, (int(tail_x), int(tail_y)))
            pygame.draw.circle(screen, color, (int(p.x), int(p.y)), max(1, int(p.size)))
        elif p.kind == "ring":
            r = int(p.size + 30 * p.t)
            ring_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, color, (r + 2, r + 2), r, 2)
            screen.blit(ring_surf, (int(p.x - r - 2), int(p.y - r - 2)))
        elif p.kind == "ember":
            size = max(1, int(p.size * (1.0 - p.t)))
            pygame.draw.circle(screen, color, (int(p.x), int(p.y)), size)
        elif p.kind == "shimmer":
            size = max(1, int(p.size))
            sx, sy = int(p.x), int(p.y)
            pygame.draw.line(screen, color, (sx - size, sy), (sx + size, sy), 1)
            pygame.draw.line(screen, color, (sx, sy - size), (sx, sy + size), 1)
        elif p.kind == "mote":
            # Soft parlor dust mote: low-alpha core + softer outer halo.
            base_a = max(0, alpha // 4)
            if base_a <= 0:
                return
            sz = max(1, int(p.size))
            outer = int(p.size * 2 + 2)
            # Direct draws instead of per-particle Surface allocation.
            pygame.draw.circle(screen, (*p.color, base_a), (int(p.x), int(p.y)), outer)
            pygame.draw.circle(screen, (*p.color, min(255, base_a * 3)),
                               (int(p.x), int(p.y)), sz)
        else:
            size = max(1, int(p.size * (1.0 - 0.7 * p.t)))
            pygame.draw.circle(screen, color, (int(p.x), int(p.y)), size)

    def clear(self):
        self.particles = []

    def burst_pair(self, x, y, color=(232, 195, 110), n=18):
        for _ in range(n):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(120, 320)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life=random.uniform(0.4, 0.7),
                color=color,
                size=random.uniform(2.5, 4.5),
                ay=300,
                kind="spark",
                drag=0.9,
            ))
        self.particles.append(Particle(
            x, y, 0, 0,
            life=0.5, color=color, size=20, kind="ring", drag=1.0,
        ))

    def burst_declare(self, x, y, color=(232, 195, 110), n=40):
        for _ in range(n):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(60, 220)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life=random.uniform(0.8, 1.4),
                color=color,
                size=random.uniform(2, 5),
                ay=180,
                kind="spark",
                drag=0.92,
            ))
        self.particles.append(Particle(
            x, y, 0, 0,
            life=0.9, color=color, size=30, kind="ring", drag=1.0,
        ))

    def burst_penalty(self, x, y, color=(212, 72, 72), n=16):
        for _ in range(n):
            angle = random.uniform(-math.pi, 0)
            speed = random.uniform(140, 280)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life=random.uniform(0.5, 0.9),
                color=color,
                size=random.uniform(2, 4),
                ay=420,
                kind="ember",
                drag=0.88,
            ))

    def burst_achievement(self, x, y, color=(255, 240, 180), n=24):
        for _ in range(n):
            angle = random.uniform(0, math.pi * 2)
            radius = random.uniform(20, 60)
            ex = x + math.cos(angle) * radius
            ey = y + math.sin(angle) * radius
            self.particles.append(Particle(
                ex, ey,
                math.cos(angle) * 30,
                math.sin(angle) * 30 - 60,
                life=random.uniform(0.8, 1.6),
                color=color,
                size=random.uniform(3, 5),
                ay=80,
                kind="shimmer",
                drag=0.94,
            ))

    def burst_power(self, x, y, color=(111, 207, 227), n=14):
        for _ in range(n):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(80, 200)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life=random.uniform(0.5, 0.9),
                color=color,
                size=random.uniform(2, 4),
                ay=120,
                kind="spark",
                drag=0.92,
            ))
        self.particles.append(Particle(
            x, y, 0, 0,
            life=0.6, color=color, size=18, kind="ring", drag=1.0,
        ))

    def trail(self, x, y, vx=0, vy=0, color=(232, 195, 110)):
        self.particles.append(Particle(
            x + random.uniform(-2, 2),
            y + random.uniform(-2, 2),
            vx * 0.2 + random.uniform(-20, 20),
            vy * 0.2 + random.uniform(-30, -10),
            life=random.uniform(0.3, 0.5),
            color=color,
            size=random.uniform(1.5, 3),
            ay=80,
            kind="dot",
            drag=0.9,
        ))

    def ambient_dust(self, screen_w, screen_h, color=(180, 150, 90)):
        if random.random() < 0.04:
            self.particles.append(Particle(
                random.uniform(0, screen_w),
                screen_h + 5,
                random.uniform(-6, 6),
                random.uniform(-25, -10),
                life=random.uniform(2.5, 4.0),
                color=color,
                size=random.uniform(0.8, 1.4),
                ay=-2,
                kind="dot",
                drag=0.99,
            ))

    def ambient_parlor_motes(self, cx, cy, rx, ry, color=(255, 215, 130)):
        """Slow warm dust motes drifting up through the lamp pool — a quieter,
        more period-appropriate ambient than the bottom-rising ambient_dust.

        Spawns inside the lit oval, motes drift upward at 8-14 px/s with a faint
        horizontal sway induced by the per-particle drag-asymmetric vx. Cap is
        ~10 visible at any time."""
        live = sum(1 for p in self.particles if p.kind == "mote")
        if live >= 12:
            return
        if random.random() >= 0.06:
            return
        # Bias spawn to inside the bright pool: pick a random angle and a
        # squared-rolled radius so most motes spawn near center.
        angle = random.uniform(0, math.tau)
        r_t = random.random() ** 1.6
        sx = cx + math.cos(angle) * rx * 0.55 * r_t
        sy = cy + math.sin(angle) * ry * 0.55 * r_t + random.uniform(-20, 80)
        self.particles.append(Particle(
            sx, sy,
            random.uniform(-3, 3),
            random.uniform(-14, -8),
            life=random.uniform(3.5, 5.5),
            color=color,
            size=random.uniform(0.9, 1.6),
            ay=random.uniform(-1.0, 1.0),
            kind="mote",
            drag=0.995,
        ))
