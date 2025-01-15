#!/usr/bin/env python3

"""
A Single-File, Conceptual "Fusion-Like" Clone for Python

Features:
- Basic 2D engine with:
  * Frames (scenes)
  * Events (conditions + actions)
  * Minimal objects for demonstration
- A Tkinter-based Editor with:
  * Scene Editor (drag objects on a canvas)
  * Event Editor (conditions & actions in a table)
  * "Run" button to launch the game in a Pygame window

Disclaimer:
This code is educational and not a full Clickteam Fusion 2.5 replacement.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox
import pygame
from pygame.locals import *

################################################################################
#                               ENGINE SECTION
################################################################################

# -------------------------------------------------------------------------------
# Configuration for the runtime
# -------------------------------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0,   0,   0)
RED   = (255,   0,   0)
GREEN = (  0, 255,   0)
BLUE  = (  0,   0, 255)


# -------------------------------------------------------------------------------
# Basic Engine Classes
# -------------------------------------------------------------------------------
class EngineObject(pygame.sprite.Sprite):
    """
    A generic 'engine object' – can be similar to 'Active Objects' in Fusion.
    """
    def __init__(self, name, x, y, w, h, color=RED):
        super().__init__()
        self.name = name
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

    def update(self, delta_time):
        # For advanced behaviors, override this
        pass


class Frame:
    """
    A "Frame" or scene containing objects and events.
    """
    def __init__(self, name, bg_color=BLACK):
        self.name = name
        self.bg_color = bg_color
        self.objects = pygame.sprite.Group()  # all EngineObject
        self.events = []  # list of Event

    def add_object(self, obj: EngineObject):
        self.objects.add(obj)

    def remove_object(self, obj: EngineObject):
        self.objects.remove(obj)

    def get_object_by_name(self, name):
        for obj in self.objects:
            if obj.name == name:
                return obj
        return None

    def update(self, delta_time):
        # Update objects
        for obj in self.objects:
            obj.update(delta_time)
        # Check events
        for evt in self.events:
            evt.run(self)

    def draw(self, surface):
        surface.fill(self.bg_color)
        self.objects.draw(surface)


# -------------------------------------------------------------------------------
# Event System
# -------------------------------------------------------------------------------
class Condition:
    def check(self, frame):
        raise NotImplementedError

class Action:
    def execute(self, frame):
        raise NotImplementedError

class Event:
    """
    If all conditions pass, execute all actions.
    """
    def __init__(self, conditions, actions):
        self.conditions = conditions
        self.actions = actions

    def run(self, frame):
        if all(cond.check(frame) for cond in self.conditions):
            for act in self.actions:
                act.execute(frame)

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
    def __init__(self, obj_name_a, obj_name_b):
        self.obj_name_a = obj_name_a
        self.obj_name_b = obj_name_b

    def check(self, frame):
        a = frame.get_object_by_name(self.obj_name_a)
        b = frame.get_object_by_name(self.obj_name_b)
        if not a or not b:
            return False
        return a.rect.colliderect(b.rect)

# Example Actions
class ChangeObjectColor(Action):
    def __init__(self, obj_name, color):
        self.obj_name = obj_name
        # color expected as a string, e.g. "(255,0,0)"
        self.color_str = color

    def execute(self, frame):
        obj = frame.get_object_by_name(self.obj_name)
        if obj:
            try:
                # e.g. parse "(255,0,0)" -> (255,0,0)
                color_tuple = eval(self.color_str)
                obj.image.fill(color_tuple)
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
        # We'll just store the desired frame to switch on engine
        global ENGINE_CURRENT_FRAME
        ENGINE_CURRENT_FRAME = self.frame_name


# -------------------------------------------------------------------------------
# The Engine
# -------------------------------------------------------------------------------
class FusionCloneEngine:
    def __init__(self):
        self.frames = {}
        self.current_frame = None
        self.running = True

    def load_project(self, project_data):
        """
        project_data is a dict that might look like:
        {
          "frames": [
            {
              "name": "Menu",
              "bg_color": [40,40,40],
              "objects": [
                { "name": "Title", "x":200, "y":100, "w":400, "h":80, "color":"(0,0,255)" },
                ...
              ],
              "events": [
                {
                  "conditions": [
                    {"type": "KeyPressed", "params":{"key":"K_SPACE"}}
                  ],
                  "actions": [
                    {"type": "GoToFrame", "params":{"frame_name":"Level1"}}
                  ]
                },
                ...
              ]
            },
            ...
          ]
        }
        """
        # Build frames
        for fdata in project_data.get("frames", []):
            name = fdata.get("name", "Untitled")
            bg_color = tuple(fdata.get("bg_color", [0, 0, 0]))
            frame = Frame(name, bg_color)

            # Add objects
            for obj_data in fdata.get("objects", []):
                o = EngineObject(
                    name=obj_data.get("name", "Unnamed"),
                    x=obj_data.get("x", 0),
                    y=obj_data.get("y", 0),
                    w=obj_data.get("w", 50),
                    h=obj_data.get("h", 50),
                    color=eval(obj_data.get("color", "(255,0,0)"))
                )
                frame.add_object(o)

            # Add events
            for evt_data in fdata.get("events", []):
                cond_list = []
                for c_data in evt_data.get("conditions", []):
                    cond_type = c_data["type"]
                    params = c_data["params"]
                    if cond_type == "KeyPressed":
                        cond_list.append(KeyPressed(params.get("key", "K_SPACE")))
                    elif cond_type == "ObjectCollision":
                        cond_list.append(ObjectCollision(params.get("obj_name_a", ""), params.get("obj_name_b", "")))
                    # ... add more as needed

                act_list = []
                for a_data in evt_data.get("actions", []):
                    act_type = a_data["type"]
                    params = a_data["params"]
                    if act_type == "ChangeObjectColor":
                        act_list.append(ChangeObjectColor(params.get("obj_name", ""), params.get("color", "(255,0,0)")))
                    elif act_type == "DestroyObject":
                        act_list.append(DestroyObject(params.get("obj_name", "")))
                    elif act_type == "GoToFrame":
                        act_list.append(GoToFrame(params.get("frame_name", "")))
                    # ... add more as needed

                event = Event(cond_list, act_list)
                frame.events.append(event)

            self.frames[name] = frame

    def change_frame(self, frame_name):
        if frame_name in self.frames:
            self.current_frame = self.frames[frame_name]

    def main_loop(self):
        global ENGINE_CURRENT_FRAME
        # The engine will read ENGINE_CURRENT_FRAME to decide if we switch frames.

        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Fusion-Like Engine Runtime")
        clock = pygame.time.Clock()

        while self.running:
            dt = clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False

            # Check if we need to switch frame
            if ENGINE_CURRENT_FRAME is not None and ENGINE_CURRENT_FRAME != self.current_frame.name:
                self.change_frame(ENGINE_CURRENT_FRAME)
                ENGINE_CURRENT_FRAME = None

            if self.current_frame:
                self.current_frame.update(dt)
                self.current_frame.draw(screen)

            pygame.display.flip()

        pygame.quit()

################################################################################
#                           EDITOR (TKINTER) SECTION
################################################################################

# A global variable to hold which frame we are on (for the engine side).
# The engine will watch for changes and switch frames accordingly.
ENGINE_CURRENT_FRAME = None

# -------------------------------------------------------------------------------
# Editor Data Structures
# -------------------------------------------------------------------------------
"""
We store project data in a Python dict, which the engine can load:

project_data = {
  "frames": [
    {
      "name": "Menu",
      "bg_color": [40,40,40],
      "objects": [
        { "name": "Title", "x":200, "y":100, "w":400, "h":80, "color":"(0,0,255)" },
        ...
      ],
      "events": [
        {
          "conditions": [
            {"type": "KeyPressed", "params":{"key":"K_SPACE"}}
          ],
          "actions": [
            {"type": "GoToFrame", "params":{"frame_name":"Level1"}}
          ]
        }
      ]
    },
    ...
  ]
}
"""

# We'll store the entire data in-memory. The user can save/load to JSON if desired.
project_data = {
    "frames": []
}

def find_frame_data(frame_name):
    for f in project_data["frames"]:
        if f["name"] == frame_name:
            return f
    return None

# -------------------------------------------------------------------------------
# Editor: Scene Editor
# -------------------------------------------------------------------------------
class SceneEditor(tk.Frame):
    """
    Shows a canvas where you can add objects, move them around, etc.
    """
    def __init__(self, master, parent_editor):
        super().__init__(master)
        self.parent_editor = parent_editor
        self.current_frame_name = None
        self.canvas = tk.Canvas(self, width=400, height=300, bg="gray")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_click)

        # Label with instructions
        tk.Label(self, text="Scene Editor:\nClick to add or select objects.\nDrag to move (simple approach).").pack()

        self.dragging_item = None
        self.offset_x = 0
        self.offset_y = 0

        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def load_frame(self, frame_name):
        self.current_frame_name = frame_name
        self.canvas.delete("all")
        fdata = find_frame_data(frame_name)
        if not fdata:
            return
        # Draw objects on the canvas
        for obj in fdata["objects"]:
            self.draw_object(obj)

    def draw_object(self, obj):
        # We'll just draw a rectangle with a text label
        x, y, w, h = obj["x"], obj["y"], obj["w"], obj["h"]
        color = obj["color"]
        rect_id = self.canvas.create_rectangle(x, y, x+w, y+h, fill="white", outline="black")
        text_id = self.canvas.create_text(x + w//2, y + h//2, text=obj["name"], fill="blue")
        # Store references so we know which object is which
        self.canvas.itemconfig(rect_id, tags=("obj", obj["name"]))
        self.canvas.itemconfig(text_id, tags=("obj_text", obj["name"]))

    def on_click(self, event):
        fdata = find_frame_data(self.current_frame_name)
        if not fdata:
            return

        clicked = self.canvas.find_closest(event.x, event.y)
        if clicked:
            tags = self.canvas.gettags(clicked)
            if "obj" in tags or "obj_text" in tags:
                # We clicked on an existing object -> select it
                # We store that for possible dragging
                self.dragging_item = clicked[0]
                # figure out offset
                coords = self.canvas.coords(self.dragging_item)
                if len(coords) >= 4:
                    x1, y1, x2, y2 = coords
                    self.offset_x = event.x - x1
                    self.offset_y = event.y - y1
            else:
                # We clicked empty area -> create a new object
                obj_name = f"Obj{len(fdata['objects'])+1}"
                new_obj = {
                    "name": obj_name,
                    "x": event.x,
                    "y": event.y,
                    "w": 50,
                    "h": 50,
                    "color": "(255,0,0)"
                }
                fdata["objects"].append(new_obj)
                self.draw_object(new_obj)
        else:
            # clicked empty area? possibly create a new object
            pass

    def on_drag(self, event):
        # If dragging an existing item, move it
        if self.dragging_item:
            # Move rect or text
            coords = self.canvas.coords(self.dragging_item)
            if len(coords) >= 2:
                w = 0
                h = 0
                if len(coords) == 4:
                    # It's a rectangle
                    w = coords[2] - coords[0]
                    h = coords[3] - coords[1]
                new_x1 = event.x - self.offset_x
                new_y1 = event.y - self.offset_y
                self.canvas.coords(self.dragging_item, new_x1, new_y1, new_x1+w, new_y1+h)

    def on_release(self, event):
        # If we were dragging, update the object data in project_data
        if self.dragging_item:
            tags = self.canvas.gettags(self.dragging_item)
            if len(tags) >= 2:
                obj_name = tags[1]
                coords = self.canvas.coords(self.dragging_item)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    w = x2 - x1
                    h = y2 - y1
                    # update the object in data
                    fdata = find_frame_data(self.current_frame_name)
                    if fdata:
                        for obj in fdata["objects"]:
                            if obj["name"] == obj_name:
                                obj["x"] = int(x1)
                                obj["y"] = int(y1)
                                obj["w"] = int(w)
                                obj["h"] = int(h)
            self.dragging_item = None


# -------------------------------------------------------------------------------
# Editor: Event Editor
# -------------------------------------------------------------------------------
CONDITION_TYPES = ["KeyPressed", "ObjectCollision"]
ACTION_TYPES = ["ChangeObjectColor", "DestroyObject", "GoToFrame"]

CONDITION_PARAMS_TEMPLATE = {
    "KeyPressed": ["key"],               # e.g. K_SPACE
    "ObjectCollision": ["obj_name_a", "obj_name_b"],
}

ACTION_PARAMS_TEMPLATE = {
    "ChangeObjectColor": ["obj_name", "color"],  # color like "(255,0,0)"
    "DestroyObject": ["obj_name"],
    "GoToFrame": ["frame_name"],
}

class EventEditor(tk.Frame):
    def __init__(self, master, parent_editor):
        super().__init__(master)
        self.parent_editor = parent_editor
        self.current_frame_name = None

        self.events_data = []  # local copy of the events in the current frame

        # Treeview
        self.columns = ("Conditions", "Actions")
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=10)
        self.tree.heading("Conditions", text="Conditions")
        self.tree.heading("Actions", text="Actions")
        self.tree.column("Conditions", width=300)
        self.tree.column("Actions", width=300)
        self.tree.pack(side="top", fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(side="bottom", fill="x")

        tk.Button(btn_frame, text="Add Event", command=self.add_event).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Edit Event", command=self.edit_event).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Delete Event", command=self.delete_event).pack(side="left", padx=5, pady=5)

    def load_frame_events(self, frame_name):
        self.current_frame_name = frame_name
        self.tree.delete(*self.tree.get_children())
        self.events_data = []

        fdata = find_frame_data(frame_name)
        if fdata is None:
            return

        self.events_data = fdata.get("events", [])
        for evt in self.events_data:
            c_str = self.conditions_to_str(evt["conditions"])
            a_str = self.actions_to_str(evt["actions"])
            self.tree.insert("", "end", values=(c_str, a_str))

    def conditions_to_str(self, conds):
        parts = []
        for c in conds:
            t = c["type"]
            ps = ", ".join(f"{k}={v}" for k,v in c["params"].items())
            parts.append(f"{t}({ps})")
        return " AND ".join(parts) if parts else "No Conditions"

    def actions_to_str(self, acts):
        parts = []
        for a in acts:
            t = a["type"]
            ps = ", ".join(f"{k}={v}" for k,v in a["params"].items())
            parts.append(f"{t}({ps})")
        return ", ".join(parts) if parts else "No Actions"

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for evt in self.events_data:
            c_str = self.conditions_to_str(evt["conditions"])
            a_str = self.actions_to_str(evt["actions"])
            self.tree.insert("", "end", values=(c_str, a_str))

    def add_event(self):
        dlg = EventDialog(self)
        self.wait_window(dlg)
        if dlg.result is not None:
            self.events_data.append(dlg.result)
            self.refresh_tree()
            self.save_back()

    def edit_event(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        evt_data = self.events_data[idx]

        dlg = EventDialog(self, existing_event=evt_data)
        self.wait_window(dlg)
        if dlg.result is not None:
            self.events_data[idx] = dlg.result
            self.refresh_tree()
            self.save_back()

    def delete_event(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        del self.events_data[idx]
        self.refresh_tree()
        self.save_back()

    def save_back(self):
        # Write self.events_data back into the project_data
        fdata = find_frame_data(self.current_frame_name)
        if fdata:
            fdata["events"] = self.events_data


class EventDialog(tk.Toplevel):
    """
    A dialog to add/edit one event (list of conditions & actions).
    """
    def __init__(self, parent, existing_event=None):
        super().__init__(parent)
        self.title("Event Editor")
        self.resizable(False, False)

        self.parent = parent
        self.result = None

        if existing_event:
            self.conditions = [dict(c) for c in existing_event["conditions"]]
            self.actions = [dict(a) for a in existing_event["actions"]]
        else:
            self.conditions = []
            self.actions = []

        # Layout
        label_frame = tk.Frame(self)
        label_frame.pack(fill="x")
        tk.Label(label_frame, text="Conditions").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(label_frame, text="Actions").grid(row=0, column=1, padx=5, pady=5)

        self.cond_list = tk.Listbox(label_frame, height=10, width=35)
        self.cond_list.grid(row=1, column=0, padx=5, pady=5)
        self.act_list = tk.Listbox(label_frame, height=10, width=35)
        self.act_list.grid(row=1, column=1, padx=5, pady=5)

        cond_btns = tk.Frame(label_frame)
        cond_btns.grid(row=2, column=0)
        tk.Button(cond_btns, text="Add", command=self.add_condition).pack(side="left", padx=2)
        tk.Button(cond_btns, text="Edit", command=self.edit_condition).pack(side="left", padx=2)
        tk.Button(cond_btns, text="Del", command=self.del_condition).pack(side="left", padx=2)

        act_btns = tk.Frame(label_frame)
        act_btns.grid(row=2, column=1)
        tk.Button(act_btns, text="Add", command=self.add_action).pack(side="left", padx=2)
        tk.Button(act_btns, text="Edit", command=self.edit_action).pack(side="left", padx=2)
        tk.Button(act_btns, text="Del", command=self.del_action).pack(side="left", padx=2)

        # OK/Cancel
        bottom = tk.Frame(self)
        bottom.pack(pady=5)
        tk.Button(bottom, text="OK", command=self.on_ok).pack(side="left", padx=10)
        tk.Button(bottom, text="Cancel", command=self.on_cancel).pack(side="left", padx=10)

        self.refresh_lists()

    def refresh_lists(self):
        self.cond_list.delete(0, tk.END)
        for c in self.conditions:
            txt = self.cond_str(c)
            self.cond_list.insert(tk.END, txt)

        self.act_list.delete(0, tk.END)
        for a in self.actions:
            txt = self.act_str(a)
            self.act_list.insert(tk.END, txt)

    def cond_str(self, c):
        ps = ", ".join(f"{k}={v}" for k,v in c["params"].items())
        return f"{c['type']}({ps})"

    def act_str(self, a):
        ps = ", ".join(f"{k}={v}" for k,v in a["params"].items())
        return f"{a['type']}({ps})"

    def add_condition(self):
        dlg = ConditionActionEditor(self, "condition")
        self.wait_window(dlg)
        if dlg.result:
            self.conditions.append(dlg.result)
            self.refresh_lists()

    def edit_condition(self):
        sel = self.cond_list.curselection()
        if not sel:
            return
        idx = sel[0]
        cdata = self.conditions[idx]
        dlg = ConditionActionEditor(self, "condition", cdata)
        self.wait_window(dlg)
        if dlg.result:
            self.conditions[idx] = dlg.result
            self.refresh_lists()

    def del_condition(self):
        sel = self.cond_list.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.conditions[idx]
        self.refresh_lists()

    def add_action(self):
        dlg = ConditionActionEditor(self, "action")
        self.wait_window(dlg)
        if dlg.result:
            self.actions.append(dlg.result)
            self.refresh_lists()

    def edit_action(self):
        sel = self.act_list.curselection()
        if not sel:
            return
        idx = sel[0]
        adata = self.actions[idx]
        dlg = ConditionActionEditor(self, "action", adata)
        self.wait_window(dlg)
        if dlg.result:
            self.actions[idx] = dlg.result
            self.refresh_lists()

    def del_action(self):
        sel = self.act_list.curselection()
        if not sel:
            return
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
    """
    A small dialog to pick a Condition/Action type and fill out its params.
    """
    def __init__(self, parent, mode, current=None):
        """
        mode: "condition" or "action"
        current: dict {type:..., params:{...}}
        """
        super().__init__(parent)
        self.mode = mode
        self.result = None

        if mode == "condition":
            self.type_options = CONDITION_TYPES
            self.template_map = CONDITION_PARAMS_TEMPLATE
        else:
            self.type_options = ACTION_TYPES
            self.template_map = ACTION_PARAMS_TEMPLATE

        self.cur_type = None
        self.cur_params = {}
        if current:
            self.cur_type = current["type"]
            self.cur_params = dict(current["params"])

        self.title(f"Edit {mode.capitalize()}")
        self.resizable(False, False)

        # Type dropdown
        tk.Label(self, text="Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.type_var = tk.StringVar(value=self.cur_type or self.type_options[0])
        type_dd = ttk.Combobox(self, textvariable=self.type_var, values=self.type_options, state="readonly")
        type_dd.grid(row=0, column=1, padx=5, pady=5)
        type_dd.bind("<<ComboboxSelected>>", self.on_type_change)

        # param frame
        self.params_frame = tk.Frame(self)
        self.params_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        # Buttons
        bottom = tk.Frame(self)
        bottom.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(bottom, text="OK", command=self.on_ok).pack(side="left", padx=5)
        tk.Button(bottom, text="Cancel", command=self.on_cancel).pack(side="left", padx=5)

        self.build_params_ui()

    def on_type_change(self, event):
        self.build_params_ui()

    def build_params_ui(self):
        for w in self.params_frame.winfo_children():
            w.destroy()

        t = self.type_var.get()
        param_names = self.template_map.get(t, [])
        self.param_vars = {}

        for idx, pname in enumerate(param_names):
            tk.Label(self.params_frame, text=pname+":").grid(row=idx, column=0, sticky="e")
            val = self.cur_params.get(pname, "")
            var = tk.StringVar(value=val)
            ent = tk.Entry(self.params_frame, textvariable=var, width=20)
            ent.grid(row=idx, column=1, padx=5, pady=3)
            self.param_vars[pname] = var

    def on_ok(self):
        t = self.type_var.get()
        params = {}
        for pname, var in self.param_vars.items():
            params[pname] = var.get()

        self.result = {"type": t, "params": params}
        self.destroy()

    def on_cancel(self):
        self.destroy()

# -------------------------------------------------------------------------------
# Editor: Main Application
# -------------------------------------------------------------------------------
class FusionCloneEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fusion-Like Editor (Demo)")

        # We'll pick a default frame name or create one
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

        # Left side: Frame list
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="y")

        tk.Label(left_frame, text="Frames").pack(anchor="nw")
        self.frame_listbox = tk.Listbox(left_frame)
        self.frame_listbox.pack(fill="y", expand=True)

        # Buttons for frame management
        tk.Button(left_frame, text="Add Frame", command=self.add_frame).pack(fill="x")
        tk.Button(left_frame, text="Edit BG Color", command=self.edit_bg_color).pack(fill="x")
        tk.Button(left_frame, text="Run Game", command=self.run_game).pack(fill="x")

        # Populate the listbox
        self.load_frame_list()

        # Middle: Scene Editor
        self.scene_editor = SceneEditor(self, self)
        self.scene_editor.pack(side="left", fill="both", expand=True)

        # Right: Event Editor
        self.event_editor = EventEditor(self, self)
        self.event_editor.pack(side="right", fill="both", expand=True)

        # Bind frame selection
        self.frame_listbox.bind("<<ListboxSelect>>", self.on_frame_select)
        self.frame_listbox.select_set(0)
        self.on_frame_select(None)

    def load_frame_list(self):
        self.frame_listbox.delete(0, tk.END)
        for f in project_data["frames"]:
            self.frame_listbox.insert(tk.END, f["name"])

    def on_frame_select(self, event):
        idx = self.frame_listbox.curselection()
        if not idx:
            return
        fname = self.frame_listbox.get(idx[0])
        self.scene_editor.load_frame(fname)
        self.event_editor.load_frame_events(fname)

    def add_frame(self):
        new_name = f"Frame{len(project_data['frames'])+1}"
        project_data["frames"].append({
            "name": new_name,
            "bg_color": [0,0,0],
            "objects": [],
            "events": []
        })
        self.load_frame_list()

    def edit_bg_color(self):
        # Let user input "R,G,B"
        idx = self.frame_listbox.curselection()
        if not idx:
            return
        fname = self.frame_listbox.get(idx[0])
        fdata = find_frame_data(fname)
        if not fdata:
            return
        c = fdata["bg_color"]
        init_str = f"{c[0]},{c[1]},{c[2]}"
        color_str = tk.simpledialog.askstring("BG Color", "Enter color as R,G,B", initialvalue=init_str)
        if color_str:
            try:
                parts = [int(x.strip()) for x in color_str.split(",")]
                if len(parts) == 3:
                    fdata["bg_color"] = parts
            except:
                messagebox.showerror("Error", "Invalid color format")

    def run_game(self):
        # Export project_data, run in Pygame
        eng = FusionCloneEngine()
        eng.load_project(project_data)

        # Start with whichever frame is selected
        idx = self.frame_listbox.curselection()
        if idx:
            fname = self.frame_listbox.get(idx[0])
            eng.change_frame(fname)
        else:
            if project_data["frames"]:
                eng.change_frame(project_data["frames"][0]["name"])
        eng.main_loop()

################################################################################
#                               MAIN
################################################################################

def main():
    # If user runs "fusion_clone.py" from the terminal, launch the editor
    app = FusionCloneEditorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
