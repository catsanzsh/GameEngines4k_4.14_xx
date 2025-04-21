from ursina import (
    Ursina, Entity, Sky, DirectionalLight, AmbientLight, Vec3, Vec2, color,
    Text, window, application, raycast, clamp, invoke, destroy, held_keys, lerp
)
from ursina.shaders import lit_with_shadows_shader
import math

# --- Helper Functions ---
def distance_xz(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.z - b.z) ** 2)

def distance_sq(a, b):
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2

# --- Engine Core ---
class HedgehogEngine:
    def __init__(self):
        self.app = Ursina(vsync=True)
        application.target_fps = 60  # Cap at 60 FPS
        window.title = 'Hedgehog Engine - Pure Vibes Demo'
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = False
        window.fps_counter.enabled = True

        # Engine Systems
        self.rendering_system = RenderingSystem()
        self.level_system = LevelSystem(self.rendering_system)
        self.input_system = InputSystem()
        self.physics_system = PhysicsSystem(self.level_system)
        self.camera_system = CameraSystem()
        self.audio_system = AudioSystem()

        # Game State
        self.player = None
        self.collected_rings = 0
        self.debug_text = None

        self.setup_game()
        self.app.run()

    def setup_game(self):
        self.rendering_system.setup_environment()
        self.level_system.generate_test_level()

        self.player = PlayerCharacter(
            position=(0, 2, -5),
            shader=self.rendering_system.default_shader
        )

        self.camera_system.setup(self.player)
        self.physics_system.set_player(self.player)

        # Debug setup
        self.debug_text = Text(
            "",
            position=window.top_left,
            origin=(-0.5, 0.5),
            scale=1.2,
            color=color.azure
        )
        self.app.update = self.update

    def update(self):
        dt = application.time_step
        if dt > 1 / 30:
            dt = 1 / 30

        # 1. Input
        self.input_system.update()

        # 2. Physics & Interactions
        interaction_results = self.physics_system.update(
            self.input_system.move_direction,
            self.input_system.jump_pressed,
            dt
        )
        if interaction_results['rings_collected'] > 0:
            self.collected_rings += interaction_results['rings_collected']
            self.audio_system.play('ring')
        if interaction_results['hit_spring']:
            self.audio_system.play('spring')

        # 3. Player Animation
        self.player.update_animation(dt)

        # 4. Camera
        self.camera_system.update(dt)

        # 5. Rendering / Debug Info
        self.rendering_system.update_debug_info(
            self.player,
            self.collected_rings,
            dt
        )

# --- Rendering System ---
class RenderingSystem:
    def __init__(self):
        self.default_shader = lit_with_shadows_shader
        self.debug_text = None

    def setup_environment(self):
        Sky(color=color.rgb(100, 150, 255))
        sun = DirectionalLight(
            color=color.rgb(255, 255, 230),
            direction=(0.5, -1, 0.8),
            shadows=True,
            shadow_map_resolution=(2048, 2048),
            shadow_bias=0.001
        )
        sun.look_at(Vec3(0, -1, 0))
        AmbientLight(color=color.rgba(100, 100, 120, 0.3))

    def update_debug_info(self, player, rings, dt):
        if not self.debug_text:
            self.debug_text = Text(
                "",
                position=window.top_left + Vec2(0.01, -0.01),
                origin=(-0.5, 0.5),
                scale=1.2,
                color=color.azure
            )

        self.debug_text.text = (
            f"Speed: {player.speed:.1f}\n"
            f"Velocity Y: {player.velocity.y:.1f}\n"
            f"Grounded: {player.is_grounded}\n"
            f"Homing: {player.is_homing}\n"
            f"Rings: {rings}\n"
            f"FPS: {round(1/dt) if dt > 0 else 'inf'}"
        )

# --- Level System ---
class LevelSystem:
    def __init__(self, rendering_system):
        self.entities = []
        self.rings = []
        self.springs = []
        self.targetable_entities = []
        self.renderer = rendering_system

    def generate_test_level(self):
        ground = self._add_entity(
            model='plane',
            scale=(150, 1, 150),
            color=color.color(0.2, 0.7, 0.3, 1),
            collider='box'
        )
        self._make_platform((0, 0.5, 0), (20, 1, 10), color.color(0.5, 0.5, 0.6, 1))
        self._make_platform((15, 2, 20), (8, 1, 15), color.color(0.6, 0.5, 0.5, 1))
        self._make_platform((-10, 4, 35), (12, 1, 5), color.color(0.5, 0.6, 0.5, 1))
        self._add_entity(
            model='cube', position=(25, 1, 40), scale=(8, 1, 5), rotation=(20, 0, 0),
            color=color.color(0.7, 0.7, 0.4, 1), collider='box'
        )
        self._add_entity(
            model='cube', position=(-5, 5, 50), scale=(8, 1, 5), rotation=(-25, 0, 0),
            color=color.color(0.7, 0.7, 0.4, 1), collider='box'
        )
        self._make_loop((0, 0, 70), 10, 3)
        self._make_ring_line((0, 3, 5), (0, 3, 25), 8)
        self._make_ring_circle((15, 4, 30), 6, 10)
        self._make_ring_line((-10, 6, 40), (10, 6, 40), 5)
        self._make_spring((5, 1, 35), power=25)
        self._make_spring((-5, 1, 10), power=35)

    def _add_entity(self, **kwargs):
        if 'shader' not in kwargs:
            kwargs['shader'] = self.renderer.default_shader
        e = Entity(**kwargs)
        self.entities.append(e)
        return e

    def _make_platform(self, pos, scale, col):
        return self._add_entity(model='cube', position=pos, scale=scale, color=col, collider='box')

    def _make_loop(self, center, radius, thickness, segments=24):
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            angle_next = 2 * math.pi * (i + 1) / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle) + radius
            x_next = radius * math.cos(angle_next)
            y_next = radius * math.sin(angle_next) + radius
            pos = Vec3(x + center[0], y + center[1], center[2])
            pos_next = Vec3(x_next + center[0], y_next + center[1], center[2])
            self._add_entity(
                model='cube', position=(pos + pos_next) / 2,
                scale=(thickness * 1.5, thickness, thickness * 2.5),
                look_at=pos_next, rotation_x=0,
                color=color.color(0.4, 0.4, 0.8, 1), collider='box'
            )

    def _make_ring(self, pos):
        ring = self._add_entity(
            model='torus', color=color.gold, scale=1.0, position=pos,
            rotation=(90, 0, 0), collider='sphere', tag='ring'
        )
        self.rings.append(ring)
        self.targetable_entities.append(ring)
        return ring

    def _make_ring_line(self, start, end, count):
        direction = Vec3(end) - Vec3(start)
        if count <= 1:
            self._make_ring(start)
            return
        step = direction / (count - 1)
        for i in range(count):
            self._make_ring(Vec3(start) + step * i)

    def _make_ring_circle(self, center, radius, count):
        for i in range(count):
            angle = 2 * math.pi * i / count
            x = radius * math.cos(angle) + center[0]
            z = radius * math.sin(angle) + center[2]
            self._make_ring((x, center[1], z))

    def _make_spring(self, pos, power=25):
        spring = self._add_entity(
            model='cylinder', color=color.color(1, 0.6, 0, 1), scale=(1, 0.4, 1),
            position=pos, collider='box', tag='spring', power=power
        )
        self._add_entity(
            model='cube', scale=(1.2, 0.1, 1.2), position=Vec3(pos) + Vec3(0, 0.2, 0),
            color=color.red, parent=spring
        )
        self.springs.append(spring)
        return spring

    def remove_targetable(self, entity):
        if entity in self.targetable_entities:
            self.targetable_entities.remove(entity)

# --- Input System ---
class InputSystem:
    def __init__(self):
        self.move_direction = Vec3(0, 0, 0)
        self.jump_pressed = False

    def update(self):
        self.move_direction = Vec3(
            held_keys['d'] - held_keys['a'],
            0,
            held_keys['w'] - held_keys['s']
        ).normalized()
        self.jump_pressed = held_keys['space']

# --- Physics System ---
class PhysicsSystem:
    def __init__(self, level_system):
        self.player = None
        self.level = level_system
        self.gravity = 35
        self.ground_check_dist = 0.5
        self.wall_check_dist = 0.6
        self.homing_range_sq = 15 ** 2
        self.homing_dot_product_threshold = 0.3

    def set_player(self, player_entity):
        self.player = player_entity

    def update(self, input_direction, jump_pressed, dt):
        if not self.player:
            return {'rings_collected': 0, 'hit_spring': False}

        p = self.player

        # --- Ground Check ---
        ground_ray = raycast(
            origin=p.world_position + Vec3(0, 0.1, 0),
            direction=Vec3(0, -1, 0),
            distance=self.ground_check_dist,
            ignore=(p,),
            debug=False
        )
        p.is_grounded = ground_ray.hit

        # --- Homing Attack Logic ---
        if p.is_homing:
            if not p.homing_target or not p.homing_target.enabled:
                p.is_homing = False
            else:
                target_direction = (
                    p.homing_target.world_position - p.world_position
                ).normalized()
                p.velocity = target_direction * p.homing_speed
                if distance_xz(
                    p.world_position, p.homing_target.world_position
                ) < 1.5:
                    p.is_homing = False
                    p.velocity = target_direction * p.speed
                    p.velocity.y = max(0, p.velocity.y)
        else:
            # --- Apply Gravity ---
            if not p.is_grounded:
                p.velocity.y -= self.gravity * dt

            # --- Ground Physics ---
            if p.is_grounded:
                p.can_double_jump = True
                if p.velocity.y < 0:
                    p.velocity.y = 0
                p.y = ground_ray.world_point.y + 0.01

                ground_normal = ground_ray.world_normal
                forward_on_slope = (
                    Vec3(p.forward).cross(ground_normal)
                    .cross(ground_normal)
                    .normalized()
                )

                target_rotation_y = p.rotation_y - input_direction.x * p.turn_speed
                p.rotation_y = lerp(p.rotation_y, target_rotation_y, dt * 10)

                if input_direction.z > 0:
                    slope_effect = -forward_on_slope.y
                    accel = p.acceleration + slope_effect * p.slope_boost_factor
                    p.speed += accel * dt
                else:
                    p.speed -= p.deceleration * dt

                p.speed *= p.friction ** dt
                p.speed = clamp(p.speed, 0, p.max_speed)
                p.velocity.xz = forward_on_slope.xz * p.speed

                if jump_pressed:
                    p.velocity.y = p.jump_power
                    p.is_grounded = False

            # --- Air Physics ---
            else:
                p.rotation_y -= input_direction.x * p.air_turn_speed
                air_control_direction = (
                    p.forward * input_direction.z + p.right * input_direction.x
                )
                p.velocity += air_control_direction * p.air_control_force * dt

                air_speed_xz = p.velocity.xz.length()
                if air_speed_xz > p.max_speed * 0.8:
                    p.velocity.xz = (
                        p.velocity.xz.normalized() * p.max_speed * 0.8
                    )

                if held_keys['space'] and p.can_double_jump:
                    p.can_double_jump = False
                    closest_target = self._find_homing_target()
                    if closest_target:
                        p.homing_target = closest_target
                        p.is_homing = True
                        p.velocity = Vec3(0, 0, 0)

        # --- Collision Detection & Response ---
        if p.velocity.length() > 0:
            wall_ray = raycast(
                p.world_position + Vec3(0, 0.1, 0),
                p.velocity.normalized(),
                distance=self.wall_check_dist,
                ignore=(p,),
                debug=False
            )
            if wall_ray.hit and not p.is_homing:
                normal = wall_ray.world_normal
                p.velocity -= normal * p.velocity.dot(normal)

        # --- Apply Movement ---
        p.position += p.velocity * dt

        # --- Interactions ---
        interaction_results = {'rings_collected': 0, 'hit_spring': False}
        hit_info = p.intersects()
        if hit_info.hit:
            entity = hit_info.entity
            if hasattr(entity, 'tag') and entity.tag == 'ring' and entity.enabled:
                entity.enabled = False
                self.level.remove_targetable(entity)
                interaction_results['rings_collected'] += 1
                invoke(destroy, entity, delay=0.5)
            elif hasattr(entity, 'tag') and entity.tag == 'spring':
                p.velocity.y = entity.power
                p.is_homing = False
                interaction_results['hit_spring'] = True

        return interaction_results

    def _find_homing_target(self):
        closest_target = None
        min_dist_sq = self.homing_range_sq
        for target in self.level.targetable_entities:
            if not target.enabled:
                continue
            dist_sq = distance_sq(self.player.world_position, target.world_position)
            if dist_sq < min_dist_sq:
                to_target = (
                    target.world_position - self.player.world_position
                ).normalized()
                if self.player.forward.dot(to_target) > self.homing_dot_product_threshold:
                    min_dist_sq = dist_sq
                    closest_target = target
        return closest_target

# --- Camera System ---
class CameraSystem:
    def __init__(self):
        self.target = None
        from ursina import camera
        camera.fov = 75
        self.camera = camera

    def setup(self, target_entity):
        self.target = target_entity
        self.camera.parent = None

    def update(self, dt):
        if not self.target:
            return

        p = self.target
        speed_factor = min(1.0, p.speed / p.max_speed)
        target_fov = lerp(75, 90, speed_factor)
        self.camera.fov = lerp(self.camera.fov, target_fov, dt * 3)
        cam_dist = lerp(12, 18, speed_factor)
        cam_height = lerp(4, 6, speed_factor)
        target_cam_pos = (
            p.world_position + (-p.forward * cam_dist) + Vec3(0, cam_height, 0)
        )
        self.camera.position = lerp(self.camera.position, target_cam_pos, dt * 5)
        look_at_point = p.world_position + Vec3(0, 1, 0) + p.velocity * 0.1
        self.camera.look_at(look_at_point, duration=dt * 10)

# --- Audio System (Placeholder) ---
class AudioSystem:
    def __init__(self):
        self.sounds = {
            'jump': None,
            'ring': None,
            'spring': None,
            'homing': None
        }
        print("AudioSystem: Placeholder initialized. No sounds will play.")

    def play(self, sound_name, volume=1.0):
        print(f"AudioSystem: Play '{sound_name}' (Volume: {volume})")

# --- Player Character ---
class PlayerCharacter(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='sphere',
            color=color.blue,
            scale=1.0,
            collider='sphere',
            **kwargs
        )
        self.speed = 0
        self.velocity = Vec3(0, 0, 0)
        self.max_speed = 50
        self.acceleration = 40
        self.deceleration = 30
        self.friction = 0.98
        self.turn_speed = 5
        self.air_turn_speed = 3
        self.jump_power = 15
        self.air_control_force = 50
        self.slope_boost_factor = 20
        self.homing_speed = 60

        self.is_grounded = False
        self.can_double_jump = True
        self.is_homing = False
        self.homing_target = None

        self.quills = Entity(
            parent=self,
            model='cone',
            color=color.blue.tint(-0.2),
            scale=(0.6, 1.5, 0.6),
            position=(0, 0.3, -0.3),
            rotation=(15, 0, 0),
            shader=self.shader,
            always_on_top=True
        )
        self.animation_timer = 0

    def update_animation(self, dt):
        if self.is_grounded:
            self.animation_timer += self.speed * dt * 0.5
            self.quills.rotation_x = self.animation_timer % 360
            self.scale_y = lerp(self.scale_y, 1.0, dt * 10)
        else:
            self.quills.rotation_x = lerp(self.quills.rotation_x, 30, dt * 5)
            if self.velocity.y < -5:
                self.scale_y = lerp(self.scale_y, 0.8, dt * 10)
            else:
                self.scale_y = lerp(self.scale_y, 1.0, dt * 10)

        if self.is_homing:
            self.scale_y = lerp(self.scale_y, 0.8, dt * 20)

# --- Start the Engine ---
if __name__ == '__main__':
    engine = HedgehogEngine()
