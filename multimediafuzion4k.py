#!/usr/bin/env python3
"""
A Single-File, Greatly Expanded "Conceptual Clone" of Clickteam Fusion 2.5 in Python

IMPORTANT:
- This code is for demonstration/learning only. It is NOT production-ready.
- Real Fusion 2.5 has far more features, advanced exporters, physics, plugin ecosystem, etc.
- Use/modify this code at your own discretion. It's under no special license.

Requires:
- Python 3 (tested on M1 Mac with Python 3.x)
- pygame (for runtime)
- tkinter (usually included on Windows/Mac Python)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pygame
from pygame.locals import *
import sys
import json
import random

################################################################################
#                                ENGINE SECTION
################################################################################

# Screen config
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Some colors
WHITE = (255,255,255)
BLACK = (0,0,0)
RED   = (255,0,0)
GREEN = (0,255,0)
BLUE  = (0,0,255)
GRAY  = (128,128,128)

# We'll track current frame globally so the runtime can jump frames
ENGINE_CURRENT_FRAME = None

# ------------------------------------------------------------------------------
# Base Classes / Engine Architecture
# ------------------------------------------------------------------------------
class EngineObject(pygame.sprite.Sprite):
    """
    A generic object in the engine. In real Fusion, these might be 'Active Objects'.
    We can expand to handle basic animations, collisions, etc.
    """
    def __init__(self, name, x, y, w, h, color=RED):
        super().__init__()
        self.name = name
        self.x, self.y = x, y
        self.width, self.height = w, h
        self.color = color  # string or tuple
        self.angle = 0
        self.anim_frame = 0
        self.anim_speed = 0
        self.anim_frames = []  # could store Surfaces for real animations

        # In real usage, we might load an image here. For now, just a color rect.
        self.image = pygame.Surface((w, h))
        if isinstance(color, tuple):
            self.image.fill(color)
        else:
            self.image.fill(eval(color))

        self.rect = self.image.get_rect(topleft=(x,y))

    def update(self, dt):
        """
        Basic update. A real system might handle animations, movement, etc.
        """
        # If anim_frames is not empty, cycle through
        if self.anim_frames and self.anim_speed > 0:
            self.anim_frame += self.anim_speed * dt
            index = int(self.anim_frame) % len(self.anim_frames)
            self.image = self.anim_frames[index]
            self.rect = self.image.get_rect(topleft=(self.x, self.y))

class TextObject(EngineObject):
    """
    A text object, like the 'String' in Fusion.
    """
    def __init__(self, name, x, y, text="Hello", font_size=24, color=WHITE):
        super().__init__(name, x, y, 10, 10, color)  # dummy w/h
        self.text = text
        self.font_size = font_size
        # We'll generate a surface from the text
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", self.font_size)
        self.update_text_surface()

    def update_text_surface(self):
        """
        Render the text into self.image. Adjust self.rect accordingly.
        """
        self.image = self.font.render(self.text, True, self.color)
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

    def update(self, dt):
        # No animation, but you might implement blinking or color changes
        pass

class CounterObject(EngineObject):
    """
    A numeric counter object, like Fusion's "Counter".
    """
    def __init__(self, name, x, y, initial_value=0, font_size=24, color=WHITE):
        super().__init__(name, x, y, 10, 10, color)
        self.value = initial_value
        self.font_size = font_size
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", self.font_size)
        self.update_text_surface()

    def update_text_surface(self):
        text_surf = self.font.render(str(self.value), True, self.color)
        self.image = text_surf
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

    def set_value(self, val):
        self.value = val
        self.update_text_surface()

    def update(self, dt):
        pass

class Frame:
    """
    A single frame (scene/level).
    """
    def __init__(self, name, bg_color=BLACK):
        self.name = name
        self.bg_color = bg_color
        self.objects = pygame.sprite.Group()
        self.events = []

    def add_object(self, obj):
        self.objects.add(obj)

    def remove_object(self, obj):
        self.objects.remove(obj)

    def get_object_by_name(self, name):
        for o in self.objects:
            if o.name == name:
                return o
        return None

    def update(self, dt):
        for o in self.objects:
            o.update(dt)
        for e in self.events:
            e.run(self)

    def draw(self, screen):
        screen.fill(self.bg_color)
        self.objects.draw(screen)

# ------------------------------------------------------------------------------
# Events: Condition + Action
# ------------------------------------------------------------------------------
class Condition:
    def check(self, frame):
        raise NotImplementedError

class Action:
    def execute(self, frame):
        raise NotImplementedError

class Event:
    def __init__(self, conditions, actions):
        self.conditions = conditions
        self.actions = actions

    def run(self, frame):
        if all(c.check(frame) for c in self.conditions):
            for a in self.actions:
                a.execute(frame)

# Example Conditions
class KeyPressed(Condition):
    def __init__(self, key):
        self.key = key
    def check(self, frame):
        keys = pygame.key.get_pressed()
        try:
            return keys[getattr(pygame, self.key)]
        except:
            return False

class ObjectCollision(Condition):
    def __init__(self, obj_a, obj_b):
        self.obj_a = obj_a
        self.obj_b = obj_b
    def check(self, frame):
        oa = frame.get_object_by_name(self.obj_a)
        ob = frame.get_object_by_name(self.obj_b)
        if not oa or not ob:
            return False
        return oa.rect.colliderect(ob.rect)

class CompareCounter(Condition):
    """
    e.g. CompareCounter('Score','>=',10) => if Score.value >= 10 => True
    """
    def __init__(self, counter_name, operator, value):
        self.counter_name = counter_name
        self.operator = operator
        self.value = float(value) if value else 0
    def check(self, frame):
        c = frame.get_object_by_name(self.counter_name)
        if not c or not isinstance(c, CounterObject):
            return False
        if self.operator == "==":
            return c.value == self.value
        elif self.operator == "!=":
            return c.value != self.value
        elif self.operator == "<":
            return c.value < self.value
        elif self.operator == "<=":
            return c.value <= self.value
        elif self.operator == ">":
            return c.value > self.value
        elif self.operator == ">=":
            return c.value >= self.value
        return False

# Example Actions
class ChangeObjectColor(Action):
    def __init__(self, obj_name, color_str):
        self.obj_name = obj_name
        self.color_str = color_str

    def execute(self, frame):
        obj = frame.get_object_by_name(self.obj_name)
        if obj:
            try:
                c = eval(self.color_str)  # e.g. "(255,0,0)"
                obj.image.fill(c)
            except:
                pass

class DestroyObject(Action):
    def __init__(self, obj_name):
        self.obj_name = obj_name
    def execute(self, frame):
        obj = frame.get_object_by_name(self.obj_name)
        if obj:
            frame.remove_object(obj)

class GoToFrame(Action):
    def __init__(self, frame_name):
        self.frame_name = frame_name
    def execute(self, frame):
        global ENGINE_CURRENT_FRAME
        ENGINE_CURRENT_FRAME = self.frame_name

class SetCounterValue(Action):
    """
    e.g. SetCounterValue('Score','10') => Score.value = 10
    """
    def __init__(self, counter_name, value):
        self.counter_name = counter_name
        self.value = float(value) if value else 0
    def execute(self, frame):
        c = frame.get_object_by_name(self.counter_name)
        if c and isinstance(c, CounterObject):
            c.set_value(self.value)

# ------------------------------------------------------------------------------
# Plugin/Extension Mechanism (super simple placeholder)
# ------------------------------------------------------------------------------
class Plugin:
    """
    Example plugin base. Real engine might dynamically load .py modules.
    """
    def register_conditions(self):
        """
        Return a dict { "ConditionName": ConditionClass, ... }
        """
        return {}
    def register_actions(self):
        """
        Return a dict { "ActionName": ActionClass, ... }
        """
        return {}
    def register_object_types(self):
        """
        Return a dict { "ObjectTypeName": EngineObjectClass, ... }
        """
        return {}

class ExamplePlugin(Plugin):
    def register_conditions(self):
        return {
            "CompareCounter": CompareCounter
        }
    def register_actions(self):
        return {
            "SetCounterValue": SetCounterValue
        }
    def register_object_types(self):
        return {
            "CounterObject": CounterObject,
            "TextObject": TextObject
        }

# ------------------------------------------------------------------------------
# The main engine class
# ------------------------------------------------------------------------------
class FusionCloneEngine:
    def __init__(self):
        self.frames = {}
        self.current_frame = None
        self.running = True

        self.registered_conditions = {
            "KeyPressed": KeyPressed,
            "ObjectCollision": ObjectCollision,
            # We'll add more from plugin
        }
        self.registered_actions = {
            "ChangeObjectColor": ChangeObjectColor,
            "DestroyObject": DestroyObject,
            "GoToFrame": GoToFrame,
            # We'll add more from plugin
        }
        self.registered_object_types = {
            "ActiveObject": EngineObject,  # default
            "TextObject": TextObject,
            "CounterObject": CounterObject,
        }

        # Load plugins (only ExamplePlugin in this demo)
        plugin = ExamplePlugin()
        # Merge plugin classes
        conds = plugin.register_conditions()
        self.registered_conditions.update(conds)
        acts = plugin.register_actions()
        self.registered_actions.update(acts)
        objs = plugin.register_object_types()
        self.registered_object_types.update(objs)

    def load_project(self, data):
        for frame_data in data.get("frames", []):
            fname = frame_data.get("name","Unnamed")
            bgc = tuple(frame_data.get("bg_color",[0,0,0]))
            f = Frame(fname, bgc)
            # Add objects
            for o_data in frame_data.get("objects",[]):
                obj_type = o_data.get("type","ActiveObject")
                cls = self.registered_object_types.get(obj_type, EngineObject)
                name = o_data.get("name","Obj")
                x = o_data.get("x", 100)
                y = o_data.get("y", 100)
                w = o_data.get("w", 50)
                h = o_data.get("h", 50)
                col = o_data.get("color","(255,0,0)")
                # Additional fields for text/counter
                text = o_data.get("text","Hello")
                font_size = o_data.get("font_size",24)
                initial_value = o_data.get("initial_value",0)

                if cls == TextObject:
                    obj = cls(name, x, y, text=text, font_size=font_size, color=eval(col))
                elif cls == CounterObject:
                    obj = cls(name, x, y, initial_value=initial_value, font_size=font_size, color=eval(col))
                else:
                    obj = cls(name, x, y, w, h, eval(col))
                f.add_object(obj)

            # Add events
            for evt_data in frame_data.get("events",[]):
                cond_list = []
                for c_data in evt_data.get("conditions",[]):
                    c_type = c_data["type"]
                    c_params = c_data["params"]
                    cond_class = self.registered_conditions.get(c_type)
                    if cond_class:
                        # build condition instance
                        cond = self.build_class_instance(cond_class, c_params)
                        cond_list.append(cond)
                act_list = []
                for a_data in evt_data.get("actions",[]):
                    a_type = a_data["type"]
                    a_params = a_data["params"]
                    act_class = self.registered_actions.get(a_type)
                    if act_class:
                        act = self.build_class_instance(act_class, a_params)
                        act_list.append(act)
                e = Event(cond_list, act_list)
                f.events.append(e)

            self.frames[fname] = f

    def build_class_instance(self, cls, param_dict):
        """
        A helper to instantiate a condition/action class from param_dict.
        We assume the class __init__ has matching parameter names.
        """
        # We can do something like:
        return cls(**param_dict)

    def change_frame(self, frame_name):
        if frame_name in self.frames:
            self.current_frame = self.frames[frame_name]

    def main_loop(self):
        global ENGINE_CURRENT_FRAME
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Fusion-Like Engine")
        clock = pygame.time.Clock()

        while self.running:
            dt = clock.tick(FPS)/1000.0
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False

            # Check if we need to jump frames
            if ENGINE_CURRENT_FRAME and self.current_frame and ENGINE_CURRENT_FRAME != self.current_frame.name:
                self.change_frame(ENGINE_CURRENT_FRAME)
                ENGINE_CURRENT_FRAME = None

            if self.current_frame:
                self.current_frame.update(dt)
                self.current_frame.draw(screen)

            pygame.display.flip()
        pygame.quit()

################################################################################
#                         EDITOR (Tkinter) SECTION
################################################################################

project_data = {
    "frames": []
}

def find_frame_data(fname):
    for f in project_data["frames"]:
        if f["name"] == fname:
            return f
    return None

# ------------------------------------------------------------------------------
# Scene Editor
# ------------------------------------------------------------------------------
class SceneEditor(tk.Frame):
    def __init__(self, master, parent_app):
        super().__init__(master)
        self.parent_app = parent_app
        self.canvas = tk.Canvas(self, width=400, height=300, bg="lightgray")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.current_frame_name = None
        self.dragging_item = None
        self.offset_x = 0
        self.offset_y = 0

    def load_frame(self, frame_name):
        self.current_frame_name = frame_name
        self.canvas.delete("all")
        fdata = find_frame_data(frame_name)
        if not fdata: return
        for obj_data in fdata["objects"]:
            self.draw_object(obj_data)

    def draw_object(self, obj_data):
        name = obj_data["name"]
        x, y = obj_data["x"], obj_data["y"]
        w, h = obj_data.get("w",50), obj_data.get("h",50)
        # just draw a rectangle + text
        r = self.canvas.create_rectangle(x,y,x+w,y+h, fill="white", outline="black")
        t = self.canvas.create_text(x + w//2, y + h//2, text=name, fill="blue")
        self.canvas.itemconfig(r, tags=("obj", name))
        self.canvas.itemconfig(t, tags=("obj_text", name))

    def on_click(self, event):
        fdata = find_frame_data(self.current_frame_name)
        if not fdata:
            return
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            tags = self.canvas.gettags(item)
            if "obj" in tags or "obj_text" in tags:
                # We are selecting an existing object
                self.dragging_item = item[0]
                coords = self.canvas.coords(item[0])
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    self.offset_x = event.x - x1
                    self.offset_y = event.y - y1
            else:
                # If not an existing object -> create a new one
                name = f"Obj{len(fdata['objects'])+1}"
                new_obj = {
                    "type": "ActiveObject",
                    "name": name,
                    "x": event.x,
                    "y": event.y,
                    "w": 50,
                    "h": 50,
                    "color":"(255,0,0)"
                }
                fdata["objects"].append(new_obj)
                self.draw_object(new_obj)

    def on_drag(self, event):
        if self.dragging_item:
            coords = self.canvas.coords(self.dragging_item)
            if len(coords) == 4:
                w = coords[2]-coords[0]
                h = coords[3]-coords[1]
                nx = event.x - self.offset_x
                ny = event.y - self.offset_y
                self.canvas.coords(self.dragging_item, nx, ny, nx+w, ny+h)
                # If there's a text item linked, we need to move that too
                # find items with the same name tag
                tags = self.canvas.gettags(self.dragging_item)
                if len(tags) >= 2:
                    obj_name = tags[1]
                    # find the text item
                    text_item = None
                    for i in self.canvas.find_withtag("obj_text"):
                        if obj_name in self.canvas.gettags(i):
                            text_item = i
                            break
                    if text_item:
                        self.canvas.coords(text_item, nx+w/2, ny+h/2)

    def on_release(self, event):
        if self.dragging_item:
            tags = self.canvas.gettags(self.dragging_item)
            if len(tags) >= 2:
                obj_name = tags[1]
                coords = self.canvas.coords(self.dragging_item)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    w = x2 - x1
                    h = y2 - y1
                    fdata = find_frame_data(self.current_frame_name)
                    if fdata:
                        for obj in fdata["objects"]:
                            if obj["name"] == obj_name:
                                obj["x"] = int(x1)
                                obj["y"] = int(y1)
                                obj["w"] = int(w)
                                obj["h"] = int(h)
            self.dragging_item = None

# ------------------------------------------------------------------------------
# Property Inspector (very minimal)
# ------------------------------------------------------------------------------
class PropertyInspector(tk.Frame):
    """
    Show properties of the selected object and allow editing.
    """
    def __init__(self, master, parent_app):
        super().__init__(master)
        self.parent_app = parent_app
        self.current_frame_name = None
        self.current_object_name = None

        tk.Label(self, text="Property Inspector", font=("Arial",12,"bold")).pack()

        self.props = {}
        self.fields = ["type","name","x","y","w","h","color","text","font_size","initial_value"]

        self.frame_fields = tk.Frame(self)
        self.frame_fields.pack(fill="x")

        row = 0
        for f in self.fields:
            tk.Label(self.frame_fields, text=f+":").grid(row=row, column=0, sticky="e")
            v = tk.StringVar()
            e = tk.Entry(self.frame_fields, textvariable=v, width=12)
            e.grid(row=row, column=1, padx=5, pady=2)
            self.props[f] = v
            row += 1

        tk.Button(self, text="Apply", command=self.on_apply).pack(pady=5)

    def load_object(self, frame_name, obj_name):
        self.current_frame_name = frame_name
        self.current_object_name = obj_name

        fdata = find_frame_data(frame_name)
        if not fdata:
            return
        # find obj
        obj = None
        for o in fdata["objects"]:
            if o["name"] == obj_name:
                obj = o
                break
        if not obj:
            return

        for f in self.fields:
            val = obj.get(f,"")
            self.props[f].set(val if val is not None else "")

    def on_apply(self):
        # update object in data
        frame_name = self.current_frame_name
        obj_name = self.current_object_name
        fdata = find_frame_data(frame_name)
        if not fdata:
            return
        # find object
        for o in fdata["objects"]:
            if o["name"] == obj_name:
                for f in self.fields:
                    val = self.props[f].get()
                    # convert numeric fields
                    if f in ["x","y","w","h","font_size","initial_value"]:
                        try:
                            val = int(val)
                        except:
                            val = 0
                    o[f] = val
                break

# ------------------------------------------------------------------------------
# Event Editor (like the basic approach from earlier)
# ------------------------------------------------------------------------------
CONDITION_TYPES = [
    "KeyPressed","ObjectCollision","CompareCounter"
]
ACTION_TYPES = [
    "ChangeObjectColor","DestroyObject","GoToFrame","SetCounterValue"
]

class EventEditor(tk.Frame):
    def __init__(self, master, parent_app):
        super().__init__(master)
        self.parent_app = parent_app
        self.current_frame_name = None
        self.events_data = []

        self.columns = ("Conditions","Actions")
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=10)
        self.tree.heading("Conditions", text="Conditions")
        self.tree.heading("Actions", text="Actions")
        self.tree.column("Conditions", width=300)
        self.tree.column("Actions", width=300)
        self.tree.pack(side="top", fill="both", expand=True)

        btn_frame = tk.Frame(self)
        btn_frame.pack(side="bottom", fill="x")
        tk.Button(btn_frame, text="Add Event", command=self.add_event).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Edit Event", command=self.edit_event).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Del Event", command=self.del_event).pack(side="left", padx=2)

    def load_frame_events(self, frame_name):
        self.current_frame_name = frame_name
        self.events_data = []
        self.tree.delete(*self.tree.get_children())

        fdata = find_frame_data(frame_name)
        if not fdata: return
        self.events_data = fdata.get("events",[])
        for e in self.events_data:
            c_str = self.conditions_to_str(e["conditions"])
            a_str = self.actions_to_str(e["actions"])
            self.tree.insert("", "end", values=(c_str, a_str))

    def conditions_to_str(self, conds):
        s = []
        for c in conds:
            t = c["type"]
            p = ", ".join(f"{k}={v}" for k,v in c["params"].items())
            s.append(f"{t}({p})")
        return " AND ".join(s)

    def actions_to_str(self, acts):
        s = []
        for a in acts:
            t = a["type"]
            p = ", ".join(f"{k}={v}" for k,v in a["params"].items())
            s.append(f"{t}({p})")
        return ", ".join(s)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for e in self.events_data:
            c_str = self.conditions_to_str(e["conditions"])
            a_str = self.actions_to_str(e["actions"])
            self.tree.insert("", "end", values=(c_str, a_str))

    def add_event(self):
        dlg = EventDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.events_data.append(dlg.result)
            self.refresh_tree()
            self.save_back()

    def edit_event(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        evt = self.events_data[idx]
        dlg = EventDialog(self, existing=evt)
        self.wait_window(dlg)
        if dlg.result:
            self.events_data[idx] = dlg.result
            self.refresh_tree()
            self.save_back()

    def del_event(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        del self.events_data[idx]
        self.refresh_tree()
        self.save_back()

    def save_back(self):
        fdata = find_frame_data(self.current_frame_name)
        if fdata:
            fdata["events"] = self.events_data

class EventDialog(tk.Toplevel):
    def __init__(self, parent, existing=None):
        super().__init__(parent)
        self.title("Edit Event")
        self.result = None

        self.conditions = []
        self.actions = []
        if existing:
            self.conditions = [dict(c) for c in existing["conditions"]]
            self.actions = [dict(a) for a in existing["actions"]]

        # Layout
        top_frame = tk.Frame(self)
        top_frame.pack(side="top", fill="x")
        tk.Label(top_frame, text="Conditions").grid(row=0,column=0, padx=5)
        tk.Label(top_frame, text="Actions").grid(row=0,column=1, padx=5)

        self.cond_list = tk.Listbox(top_frame, width=40, height=10)
        self.act_list = tk.Listbox(top_frame, width=40, height=10)
        self.cond_list.grid(row=1, column=0, padx=5)
        self.act_list.grid(row=1, column=1, padx=5)

        cond_btn = tk.Frame(top_frame)
        cond_btn.grid(row=2, column=0)
        tk.Button(cond_btn, text="Add", command=self.add_condition).pack(side="left")
        tk.Button(cond_btn, text="Edit", command=self.edit_condition).pack(side="left")
        tk.Button(cond_btn, text="Del", command=self.del_condition).pack(side="left")

        act_btn = tk.Frame(top_frame)
        act_btn.grid(row=2, column=1)
        tk.Button(act_btn, text="Add", command=self.add_action).pack(side="left")
        tk.Button(act_btn, text="Edit", command=self.edit_action).pack(side="left")
        tk.Button(act_btn, text="Del", command=self.del_action).pack(side="left")

        # Bottom
        bot = tk.Frame(self)
        bot.pack(side="bottom", pady=5)
        tk.Button(bot, text="OK", command=self.on_ok).pack(side="left", padx=5)
        tk.Button(bot, text="Cancel", command=self.on_cancel).pack(side="left", padx=5)

        self.refresh_lists()

    def refresh_lists(self):
        self.cond_list.delete(0,tk.END)
        for c in self.conditions:
            self.cond_list.insert(tk.END, self.cond_str(c))

        self.act_list.delete(0,tk.END)
        for a in self.actions:
            self.act_list.insert(tk.END, self.act_str(a))

    def cond_str(self,c):
        ps = ", ".join(f"{k}={v}" for k,v in c["params"].items())
        return f"{c['type']}({ps})"

    def act_str(self,a):
        ps = ", ".join(f"{k}={v}" for k,v in a["params"].items())
        return f"{a['type']}({ps})"

    def add_condition(self):
        cd = ConditionActionEditor(self, "condition")
        self.wait_window(cd)
        if cd.result:
            self.conditions.append(cd.result)
            self.refresh_lists()

    def edit_condition(self):
        sel = self.cond_list.curselection()
        if not sel: return
        idx = sel[0]
        cdata = self.conditions[idx]
        cd = ConditionActionEditor(self, "condition", cdata)
        self.wait_window(cd)
        if cd.result:
            self.conditions[idx] = cd.result
            self.refresh_lists()

    def del_condition(self):
        sel = self.cond_list.curselection()
        if not sel: return
        idx = sel[0]
        del self.conditions[idx]
        self.refresh_lists()

    def add_action(self):
        ad = ConditionActionEditor(self, "action")
        self.wait_window(ad)
        if ad.result:
            self.actions.append(ad.result)
            self.refresh_lists()

    def edit_action(self):
        sel = self.act_list.curselection()
        if not sel: return
        idx = sel[0]
        adata = self.actions[idx]
        ad = ConditionActionEditor(self, "action", adata)
        self.wait_window(ad)
        if ad.result:
            self.actions[idx] = ad.result
            self.refresh_lists()

    def del_action(self):
        sel = self.act_list.curselection()
        if not sel: return
        idx = sel[0]
        del self.actions[idx]
        self.refresh_lists()

    def on_ok(self):
        self.result = {
            "conditions": self.conditions,
            "actions": self.actions
        }
        self.destroy()

    def on_cancel(self):
        self.destroy()

class ConditionActionEditor(tk.Toplevel):
    def __init__(self, parent, mode, existing=None):
        super().__init__(parent)
        self.title(f"Edit {mode.capitalize()}")
        self.result = None

        self.mode = mode
        if mode == "condition":
            self.types = CONDITION_TYPES
        else:
            self.types = ACTION_TYPES

        self.cur_type = None
        self.cur_params = {}

        if existing:
            self.cur_type = existing["type"]
            self.cur_params = dict(existing["params"])
        else:
            self.cur_type = self.types[0]

        tk.Label(self, text="Type:").grid(row=0,column=0, sticky="e")
        self.type_var = tk.StringVar(value=self.cur_type)
        dd = ttk.Combobox(self, textvariable=self.type_var, values=self.types, state="readonly")
        dd.grid(row=0,column=1, padx=5, pady=5)
        dd.bind("<<ComboboxSelected>>", self.on_type_change)

        self.param_frame = tk.Frame(self)
        self.param_frame.grid(row=1, column=0, columnspan=2)

        bot = tk.Frame(self)
        bot.grid(row=2, column=0, columnspan=2, pady=5)
        tk.Button(bot, text="OK", command=self.on_ok).pack(side="left", padx=5)
        tk.Button(bot, text="Cancel", command=self.on_cancel).pack(side="left", padx=5)

        self.build_param_ui()

    def on_type_change(self, event):
        self.build_param_ui()

    def build_param_ui(self):
        for c in self.param_frame.winfo_children():
            c.destroy()

        t = self.type_var.get()
        if self.mode == "condition":
            if t == "KeyPressed":
                fields = ["key"]
            elif t == "ObjectCollision":
                fields = ["obj_a","obj_b"]
            elif t == "CompareCounter":
                fields = ["counter_name","operator","value"]
            else:
                fields = []
        else:
            # action
            if t == "ChangeObjectColor":
                fields = ["obj_name","color_str"]
            elif t == "DestroyObject":
                fields = ["obj_name"]
            elif t == "GoToFrame":
                fields = ["frame_name"]
            elif t == "SetCounterValue":
                fields = ["counter_name","value"]
            else:
                fields = []

        self.entries = {}
        for i, f in enumerate(fields):
            tk.Label(self.param_frame, text=f+":").grid(row=i, column=0, sticky="e")
            val = self.cur_params.get(f,"")
            var = tk.StringVar(value=val)
            e = tk.Entry(self.param_frame, textvariable=var, width=20)
            e.grid(row=i, column=1, padx=3, pady=2)
            self.entries[f] = var

    def on_ok(self):
        t = self.type_var.get()
        p = {}
        for k,v in self.entries.items():
            p[k] = v.get()
        self.result = {"type": t, "params": p}
        self.destroy()

    def on_cancel(self):
        self.destroy()

# ------------------------------------------------------------------------------
# Main Editor App
# ------------------------------------------------------------------------------
class FusionCloneEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fusion-Like Editor (Expanded Demo)")

        # If no frames, create some defaults
        if not project_data["frames"]:
            project_data["frames"].append({
                "name": "Menu",
                "bg_color": [40,40,40],
                "objects": [],
                "events": []
            })
            project_data["frames"].append({
                "name": "Level1",
                "bg_color": [80,80,220],
                "objects": [],
                "events": []
            })

        left = tk.Frame(self)
        left.pack(side="left", fill="y")
        tk.Label(left, text="Frames:").pack()
        self.frame_list = tk.Listbox(left, height=8)
        self.frame_list.pack(fill="y", expand=True)
        tk.Button(left, text="Add Frame", command=self.add_frame).pack(fill="x")
        tk.Button(left, text="Edit BG Color", command=self.edit_bg_color).pack(fill="x")
        tk.Button(left, text="Run Game", command=self.run_game).pack(fill="x")

        # Middle: Scene + property
        mid = tk.Frame(self)
        mid.pack(side="left", fill="both", expand=True)

        self.scene_editor = SceneEditor(mid, self)
        self.scene_editor.pack(side="top", fill="both", expand=True)

        self.prop_inspector = PropertyInspector(mid, self)
        self.prop_inspector.pack(side="bottom", fill="x")

        # Right: Event Editor
        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True)

        self.event_editor = EventEditor(right, self)
        self.event_editor.pack(side="top", fill="both", expand=True)

        # Populate frames
        self.load_frame_list()
        self.frame_list.bind("<<ListboxSelect>>", self.on_frame_select)
        self.frame_list.select_set(0)
        self.on_frame_select(None)

        # Inspector selection hooking:
        self.scene_editor.canvas.bind("<Button-3>", self.on_right_click)

    def load_frame_list(self):
        self.frame_list.delete(0, tk.END)
        for f in project_data["frames"]:
            self.frame_list.insert(tk.END, f["name"])

    def on_frame_select(self, event):
        idx = self.frame_list.curselection()
        if not idx:
            return
        fname = self.frame_list.get(idx[0])
        self.scene_editor.load_frame(fname)
        self.event_editor.load_frame_events(fname)

    def add_frame(self):
        name = f"Frame{len(project_data['frames'])+1}"
        project_data["frames"].append({
            "name": name,
            "bg_color":[0,0,0],
            "objects":[],
            "events":[]
        })
        self.load_frame_list()

    def edit_bg_color(self):
        idx = self.frame_list.curselection()
        if not idx: return
        fname = self.frame_list.get(idx[0])
        fdata = find_frame_data(fname)
        if not fdata: return

        init_str = ",".join(str(c) for c in fdata["bg_color"])
        ans = simpledialog.askstring("BG Color","Enter R,G,B", initialvalue=init_str)
        if ans:
            try:
                parts = [int(x.strip()) for x in ans.split(",")]
                if len(parts)==3:
                    fdata["bg_color"] = parts
            except:
                messagebox.showerror("Error","Invalid color format")

    def run_game(self):
        # Launch engine
        idx = self.frame_list.curselection()
        start_frame = None
        if idx:
            start_frame = self.frame_list.get(idx[0])
        else:
            if project_data["frames"]:
                start_frame = project_data["frames"][0]["name"]
        eng = FusionCloneEngine()
        eng.load_project(project_data)
        if start_frame:
            eng.change_frame(start_frame)
        eng.main_loop()

    def on_right_click(self, event):
        """
        Let's say right-click opens the property inspector for the clicked object.
        """
        item = self.scene_editor.canvas.find_closest(event.x, event.y)
        if item:
            tags = self.scene_editor.canvas.gettags(item)
            if len(tags) >= 2:
                obj_name = tags[1]
                idx = self.frame_list.curselection()
                if not idx: return
                fname = self.frame_list.get(idx[0])
                self.prop_inspector.load_object(fname, obj_name)


################################################################################
# MAIN
################################################################################
def main():
    app = FusionCloneEditorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
