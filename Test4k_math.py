from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random
import math

# ========== DREAMCAST TECH DEMO ENGINE ==========

class DemoPlayer(Entity):
    def __init__(self):
        super().__init__(
            model='sphere',
            color=color.azure,
            scale=(1,1.5,1),
            collider='sphere',
            shader=lit_with_shadows_shader
        )
        self.speed = 7
        self.jump_height = 9
        self.health = 3
        self.invincible = False
        self.spin_speed = 0

    def spin_attack(self):
        self.spin_speed = 360
        invoke(setattr, self, 'spin_speed', 0, delay=0.5)

class DemoPhysics:
    def __init__(self, player):
        self.player = player
        self.gravity = 22
        self.velocity = Vec3(0)
        self.grounded = False
        self.respawn_point = Vec3(0,5,0)

    def move(self, direction, dt):
        self.player.rotation_y += direction.x * 500 * dt
        self.velocity.y += direction.y
        self.velocity = lerp(self.velocity, direction * self.player.speed, dt * 10)
        self.player.position += self.velocity * dt
        self.player.y += self.velocity.y * dt
        if self.player.y < -12:
            self.respawn()

    def apply_gravity(self, dt):
        if not self.grounded:
            self.velocity.y -= self.gravity * dt
        self.grounded = False

    def respawn(self):
        self.player.position = self.respawn_point
        self.velocity = Vec3(0)

class DemoLevel:
    def __init__(self):
        self.platforms = []
        self.rings = []
        self.springs = []
        self.spikes = []
        self.generate()

    def generate(self):
        # Ground
        self.platforms.append(DemoPlatform(position=(0,-2,0), scale=(50,1,50), color=color.gray))
        # Procedural platforms
        for i in range(18):
            pos = Vec3(
                random.uniform(-15,15),
                random.uniform(0,10),
                random.uniform(-15,15)
            )
            self.platforms.append(
                DemoPlatform(position=pos, scale=(random.randint(2,5),1,random.randint(2,5)))
            )
        # Rings
        for _ in range(24):
            self.rings.append(
                DemoRing(position=(random.uniform(-15,15), 3, random.uniform(-15,15)))
            )
        # Obstacles
        self.springs.append(DemoSpring(position=(5,1,5)))
        self.spikes.append(DemoSpikes(position=(-5,1,5)))

class DemoPlatform(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            collider='box',
            color=color.hsv(random.random(),0.7,random.uniform(0.5,1)),
            shader=lit_with_shadows_shader,
            **kwargs
        )

class DemoRing(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='circle',
            color=color.yellow.tint(random.random()),
            scale=0.5,
            collider='sphere',
            **kwargs
        )
        self.animate_scale(1.5, duration=1, curve=curve.out_quad, loop=True)
        self.collected = False

    def update(self):
        self.rotation_y += 120 * time.dt
        self.y += math.sin(time.time() + self.x) * 0.01
        if not self.collected and distance(self, player) < 1.3:
            audio.play('ring')
            self.collected = True
            self.disable()

class DemoSpring(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            color=color.red.tint(random.random()),
            scale=(1,0.3,1),
            collider='box',
            **kwargs
        )

class DemoSpikes(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cone',
            color=color.orange,
            collider='mesh',
            scale=(1,1.5,1),
            **kwargs
        )

# ========== AUDIO ==========
def generate_waveform(wave_type, frequency=440, duration=0.2, sample_rate=44100):
    import numpy as np
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    if wave_type == 'sine':
        wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    elif wave_type == 'square':
        wave = 0.5 * np.sign(np.sin(2 * np.pi * frequency * t))
    elif wave_type == 'noise':
        wave = 0.5 * np.random.uniform(-1, 1, t.shape)
    else:
        wave = np.zeros_like(t)
    audio_data = (wave * 32767).astype(np.int16)
    return audio_data.tobytes()

class DemoAudio:
    def __init__(self):
        self.sounds = {
            'ring': Audio(generate_waveform('sine', frequency=1500, duration=0.12), autoplay=False),
            'spring': Audio(generate_waveform('square', frequency=800, duration=0.22), autoplay=False),
            'hurt': Audio(generate_waveform('noise', duration=0.18), autoplay=False)
        }
    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

# ========== AUTO PATCH SYSTEM ==========
def auto_patch_entity(entity, world_bounds=((-25, 25), (-5, 25), (-25, 25)), min_y=-2):
    # Clamp position to world bounds
    x, y, z = entity.position
    x = max(world_bounds[0][0], min(x, world_bounds[0][1]))
    y = max(world_bounds[1][0], min(y, world_bounds[1][1]))
    z = max(world_bounds[2][0], min(z, world_bounds[2][1]))
    y = max(y, min_y)
    entity.position = (x, y, z)
    # Clamp health if present
    if hasattr(entity, 'health'):
        entity.health = max(0, min(entity.health, 3))
    # Simple overlap correction (push away from other entities)
    if hasattr(entity, 'collider') and entity.collider:
        for other in scene.entities:
            if other is not entity and hasattr(other, 'collider') and other.collider:
                d = distance(entity, other)
                if d < 0.5 and d > 0:
                    direction = (entity.position - other.position).normalized()
                    entity.position += direction * 0.1

# ========== GAME SETUP ==========

app = Ursina(borderless=False)
window.title = "Dreamcast Tech Demo (No PNG, No MP3)"
window.size = (600, 400)
window.borderless = False
window.color = color.rgb(40, 60, 120)
window.fps_counter.enabled = True

player = DemoPlayer()
level = DemoLevel()
physics = DemoPhysics(player)
audio = DemoAudio()
camera.position = (0,13,-22)
camera.look_at(player)

# ========== GAME LOOP ==========

def update():
    # Movement
    direction = Vec3(
        held_keys['d'] - held_keys['a'],
        0,
        held_keys['w'] - held_keys['s']
    ).normalized()
    physics.move(direction, time.dt)
    physics.apply_gravity(time.dt)
    # Spin animation
    player.rotation_y += player.spin_speed * time.dt
    # Camera follow (Dreamcast style: smooth, slightly laggy)
    cam_target = player.position + Vec3(0,13,-22)
    camera.position = lerp(camera.position, cam_target, time.dt * 2.5)
    camera.look_at(player.position + Vec3(0,2,0))
    # Ring update
    for e in scene.entities:
        if isinstance(e, DemoRing):
            e.update()
    # Spring collision
    for e in scene.entities:
        if isinstance(e, DemoSpring) and distance(e, player) < 1.3:
            physics.velocity.y = player.jump_height * 1.6
            audio.play('spring')
    # Spikes collision
    for e in scene.entities:
        if isinstance(e, DemoSpikes) and distance(e, player) < 1.2 and not player.invincible:
            player.health -= 1
            player.invincible = True
            audio.play('hurt')
            invoke(setattr, player, 'invincible', False, delay=1)
            if player.health <= 0:
                physics.respawn()
                player.health = 3
    # Auto patch all entities
    for e in scene.entities:
        auto_patch_entity(e)

def input(key):
    if key == 'space' and physics.grounded:
        physics.velocity.y = player.jump_height
        physics.grounded = False
    if key == 'e':
        player.spin_attack()

# ========== COLLISION PATCH ==========
def late_update():
    # Simple ground check
    physics.grounded = False
    for e in scene.entities:
        if isinstance(e, DemoPlatform):
            if player.intersects(e).hit:
                physics.grounded = True
                physics.velocity.y = 0
                player.y = e.y + e.scale_y/2 + player.scale_y/2 + 0.01

# ========== DREAMCAST VIBE EXTRAS ==========
# Add some floating cubes and color cycling for extra "tech demo" feel
floating_cubes = []
for i in range(12):
    c = Entity(
        model='cube',
        color=color.hsv(i/12, 1, 1),
        position=(random.uniform(-18,18), random.uniform(7,15), random.uniform(-18,18)),
        scale=(1.2,1.2,1.2),
        shader=lit_with_shadows_shader
    )
    floating_cubes.append(c)

def floating_update():
    t = time.time()
    for i, c in enumerate(floating_cubes):
        c.y = 10 + math.sin(t + i) * 2
        c.x += math.sin(t*0.5 + i) * 0.01
        c.z += math.cos(t*0.5 + i) * 0.01
        c.color = color.hsv((t*0.1 + i/12)%1, 1, 1)

# ========== FINAL RUN ==========
def demo_update():
    update()
    floating_update()

app.update = demo_update
app.late_update = late_update
app.run()
