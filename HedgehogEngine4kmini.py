from ursina import *
from ursina.shaders import basic_lighting_shader, normals_shader
import random
import math
from collections import deque

class HedgehogEngine:
    def __init__(self):
        self.app = Ursina()
        window.title = 'Hedgehog Engine Tech Demo'
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = False
        window.fps_counter.enabled = True
        window.vsync = True
        
        # Engine systems
        self.physics_system = PhysicsSystem()
        self.rendering_system = RenderingSystem()
        self.audio_system = AudioSystem()
        self.input_system = InputSystem()
        self.camera_system = CameraSystem()
        self.level_system = LevelSystem()
        
        # Game state
        self.player = None
        self.time_scale = 1.0
        self.debug_mode = False
        
        self.setup_game()
        self.app.run()
    
    def setup_game(self):
        """Initialize all game systems"""
        self.rendering_system.setup_environment()
        self.player = PlayerCharacter()
        self.camera_system.setup(self.player)
        self.level_system.generate_test_level()
        
        # Debug controls
        def toggle_debug():
            self.debug_mode = not self.debug_mode
            self.rendering_system.toggle_debug(self.debug_mode)
        
        def slow_mo():
            self.time_scale = 0.3 if self.time_scale == 1.0 else 1.0
        
        self.input_system.bind('f1', toggle_debug)
        self.input_system.bind('f2', slow_mo)
        
        self.app.update = self.update
    
    def update(self):
        """Main game loop"""
        dt = time.dt * self.time_scale
        if dt > 0.1: dt = 0.1  # Cap delta time
        
        # Update systems
        self.input_system.update()
        self.physics_system.update(self.player, dt)
        self.camera_system.update(self.player, dt)
        
        # Debug info
        if self.debug_mode:
            self.rendering_system.show_debug_info(
                self.player.position,
                self.player.speed,
                self.player.velocity_y,
                self.player.is_grounded
            )

class PhysicsSystem:
    def __init__(self):
        self.gravity = 25
        self.air_resistance = 0.1
        self.ground_friction = 0.9
        self.slope_factor = 0.5
        
    def update(self, player, dt):
        """Update physics for the player character"""
        # Apply gravity
        if not player.is_grounded:
            player.velocity_y -= self.gravity * dt
        
        # Ground detection
        player.is_grounded = player.y <= 0.1
        if player.is_grounded:
            player.velocity_y = max(0, player.velocity_y)
            player.y = 0.1
        
        # Movement physics
        if player.input_direction.length() > 0:
            # Ground movement
            if player.is_grounded:
                target_speed = player.max_speed * player.input_direction.length()
                player.speed = lerp(player.speed, target_speed, player.acceleration * dt)
            
            # Air control
            else:
                player.rotation_y += player.input_direction.x * player.air_control * dt
        
        # Apply friction
        if player.is_grounded:
            player.speed *= self.ground_friction ** dt
        
        # Apply movement
        move_direction = player.forward
        player.position += move_direction * player.speed * dt
        player.y += player.velocity_y * dt
        
        # Slope handling
        if player.is_grounded and abs(player.speed) > 5:
            player.velocity_y += math.sin(math.radians(player.rotation_x)) * self.slope_factor * dt

class RenderingSystem:
    def __init__(self):
        self.debug_text = None
        self.debug_entities = []
        
    def setup_environment(self):
        """Set up the visual environment"""
        Sky(color=color.rgb(135, 206, 235))
        AmbientLight(color=color.rgba(100, 100, 100, 0.1))
        DirectionalLight(color=color.white, direction=(1, -1, 1))
    
    def toggle_debug(self, enabled):
        """Toggle debug visualization"""
        if enabled and not self.debug_text:
            self.debug_text = Text("", position=window.top_left, origin=(-0.5, 0.5))
        elif not enabled and self.debug_text:
            destroy(self.debug_text)
            self.debug_text = None
            
            for e in self.debug_entities:
                destroy(e)
            self.debug_entities.clear()
    
    def show_debug_info(self, position, speed, velocity_y, grounded):
        """Display debug information"""
        if self.debug_text:
            self.debug_text.text = (
                f"Position: {position}\n"
                f"Speed: {speed:.1f}\n"
                f"Vertical Velocity: {velocity_y:.1f}\n"
                f"Grounded: {grounded}\n"
                f"FPS: {int(1/time.dt)}"
            )
        
        # Show velocity vector
        if len(self.debug_entities) < 1:
            velocity_arrow = Entity(
                model='arrow',
                color=color.red,
                scale=2,
                eternal=True
            )
            self.debug_entities.append(velocity_arrow)
        
        if len(self.debug_entities) > 0:
            self.debug_entities[0].position = position
            self.debug_entities[0].rotation = (0, math.degrees(math.atan2(speed, velocity_y)), 0)
            self.debug_entities[0].scale_y = math.sqrt(speed**2 + velocity_y**2) * 0.2

class AudioSystem:
    def __init__(self):
        # Placeholder for audio functionality
        self.sounds = {
            'jump': None,
            'spin': None,
            'ring': None
        }
    
    def play(self, sound_name, volume=1.0):
        """Play a sound effect"""
        print(f"Playing sound: {sound_name} at volume {volume}")

class InputSystem:
    def __init__(self):
        self.bindings = {}
        self.input_direction = Vec2(0, 0)
        
    def bind(self, key, action):
        """Bind a key to an action"""
        self.bindings[key] = action
    
    def update(self):
        """Update input state"""
        # Movement input
        self.input_direction = Vec2(
            held_keys['d'] - held_keys['a'],
            held_keys['w'] - held_keys['s']
        ).normalized()
        
        # Check bound actions
        for key, action in self.bindings.items():
            if held_keys[key]:
                action()

class CameraSystem:
    def __init__(self):
        self.camera_rig = None
        self.base_distance = 10
        self.base_height = 3
        self.base_angle = 20
        
    def setup(self, target):
        """Set up the camera system"""
        self.camera_rig = Entity()
        camera.parent = self.camera_rig
        camera.position = (0, self.base_height, -self.base_distance)
        camera.rotation_x = self.base_angle
        self.target = target
    
    def update(self, target, dt):
        """Update camera position and rotation"""
        if not self.camera_rig:
            return
            
        # Follow target with smoothing
        target_pos = target.position + Vec3(0, 1, 0)
        self.camera_rig.position = lerp(self.camera_rig.position, target_pos, dt * 5)
        
        # Adjust based on speed
        speed_factor = min(1.0, target.speed / 20)
        camera.z = -lerp(self.base_distance, self.base_distance * 1.5, speed_factor)
        camera.rotation_x = lerp(self.base_angle, self.base_angle - 10, speed_factor)
        
        # Look slightly ahead
        look_ahead = target.forward * min(5, target.speed * 0.3)
        camera.look_at(target.position + look_ahead)

class LevelSystem:
    def __init__(self):
        self.entities = []
        self.rings = []
        self.checkpoints = []
        
    def generate_test_level(self):
        """Generate a test level with various elements"""
        # Ground plane
        ground = Entity(
            model='plane',
            texture='white_cube',
            texture_scale=(50, 50),
            color=color.green.tint(-0.3),
            scale=(100, 1, 200),
            collider='box'
        )
        self.entities.append(ground)
        
        # Platforms
        self.create_platform((0, 0, 0), (20, 0.5, 5))
        self.create_platform((10, 2, 15), (5, 0.5, 10))
        self.create_platform((-5, 4, 25), (8, 0.5, 3))
        
        # Ramps
        self.create_ramp((15, 0, 30), (5, 0.5, 3), -15)
        self.create_ramp((0, 3, 40), (5, 0.5, 3), 15)
        
        # Loop
        self.create_loop((0, 0, 60), 8, 2)
        
        # Rings
        self.create_ring_line((0, 3, 0), (0, 3, 20), 10)
        self.create_ring_circle((0, 5, 30), 5, 12)
        
        # Springs
        self.create_spring((5, 0.5, 25), power=15)
    
    def create_platform(self, position, scale):
        """Create a platform"""
        platform = Entity(
            model='cube',
            position=position,
            scale=scale,
            color=color.gray,
            collider='box'
        )
        self.entities.append(platform)
        return platform
    
    def create_ramp(self, position, scale, angle):
        """Create a ramp"""
        ramp = Entity(
            model='cube',
            position=position,
            scale=scale,
            rotation=(angle, 0, 0),
            color=color.gray.tint(-0.1),
            collider='box'
        )
        self.entities.append(ramp)
        return ramp
    
    def create_loop(self, center, radius, thickness):
        """Create a loop"""
        segments = 24
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle) + radius
            z = center[2]
            
            segment = Entity(
                model='cube',
                position=(x + center[0], y + center[1], z),
                scale=(thickness, thickness, thickness * 2),
                rotation=(0, 0, -math.degrees(angle)),
                color=color.gray.tint(-0.2),
                collider='box'
            )
            self.entities.append(segment)
    
    def create_ring_line(self, start, end, count):
        """Create a line of rings"""
        direction = Vec3(end) - Vec3(start)
        step = direction / (count - 1)
        
        for i in range(count):
            pos = Vec3(start) + step * i
            ring = Entity(
                model='torus',
                color=color.yellow,
                scale=0.5,
                position=pos,
                collider='sphere',
                rotation=(90, 0, 0)
            )
            self.rings.append(ring)
    
    def create_ring_circle(self, center, radius, count):
        """Create a circle of rings"""
        for i in range(count):
            angle = 2 * math.pi * i / count
            x = radius * math.cos(angle) + center[0]
            z = radius * math.sin(angle) + center[2]
            
            ring = Entity(
                model='torus',
                color=color.yellow,
                scale=0.5,
                position=(x, center[1], z),
                collider='sphere',
                rotation=(90, 0, 0)
            )
            self.rings.append(ring)
    
    def create_spring(self, position, power=10):
        """Create a spring object"""
        spring = Entity(
            model='cylinder',
            color=color.orange,
            scale=(0.8, 0.3, 0.8),
            position=position,
            collider='box'
        )
        self.entities.append(spring)
        spring.power = power
        return spring

class PlayerCharacter(Entity):
    def __init__(self):
        super().__init__(
            model='sphere',
            color=color.blue,
            scale=(0.8, 1.5, 0.8),
            collider='box',
            shader=basic_lighting_shader,
            position=(0, 5, 0)
        )
        
        # Physics properties
        self.speed = 0
        self.max_speed = 30
        self.acceleration = 15
        self.deceleration = 20
        self.turn_speed = 200
        self.jump_power = 8
        self.air_control = 100
        self.gravity = 25
        self.velocity_y = 0
        self.is_grounded = False
        self.is_rolling = False
        
        # Visual elements
        self.quills = Entity(
            parent=self,
            model='cone',
            color=color.blue.tint(-0.2),
            scale=(0.5, 1.2, 0.5),
            position=(0, 0.5, -0.3),
            rotation=(15, 0, 0)
        )
        
        # Input
        self.input_direction = Vec2(0, 0)
        
        # Animation state
        self.animation_timer = 0
    
    def update_animation(self, dt):
        """Update character animation"""
        if self.is_grounded and abs(self.speed) > 5:
            self.animation_timer += self.speed * dt * 10
            self.quills.rotation_x = self.animation_timer % 360
        else:
            self.quills.rotation_x = lerp(self.quills.rotation_x, 15, dt * 10)
        
        # Rolling animation
        if self.is_rolling:
            self.scale_y = lerp(self.scale_y, 0.8, dt * 10)
        else:
            self.scale_y = lerp(self.scale_y, 1.5, dt * 10)

if __name__ == '__main__':
    engine = HedgehogEngine()
