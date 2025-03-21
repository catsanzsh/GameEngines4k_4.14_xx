"""
A Single-File, Conceptual "Fusion-Like" Clone for Python
Windows NT 10 Compatible Version

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
from tkinter import ttk, messagebox, filedialog
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


# -------------------------------------------------------------------------------
# Example Conditions
# -------------------------------------------------------------------------------
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


# -------------------------------------------------------------------------------
# Example Actions
# -------------------------------------------------------------------------------
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
                        cond_list.append(
                            ObjectCollision(
                                params.get("obj_name_a", ""),
                                params.get("obj_name_b", "")
                            )
                        )

                act_list = []
                for a_data in evt_data.get("actions", []):
                    act_type = a_data["type"]
                    params = a_data["params"]
                    if act_type == "ChangeObjectColor":
                        act_list.append(
                            ChangeObjectColor(
                                params.get("obj_name", ""),
                                params.get("color", "(255,0,0)")
                            )
                        )
                    elif act_type == "DestroyObject":
                        act_list.append(DestroyObject(params.get("obj_name", "")))
                    elif act_type == "GoToFrame":
                        act_list.append(GoToFrame(params.get("frame_name", "")))

                event = Event(cond_list, act_list)
                frame.events.append(event)

            self.frames[name] = frame

    def change_frame(self, frame_name):
        if frame_name in self.frames:
            self.current_frame = self.frames[frame_name]

    def main_loop(self):
        global ENGINE_CURRENT_FRAME
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Fusion-Like Engine Runtime")
        clock = pygame.time.Clock()

        # If there's at least one frame, pick the first to start
        if not self.current_frame and self.frames:
            # pick first by insertion order
            first_frame_name = next(iter(self.frames.keys()))
            self.change_frame(first_frame_name)

        while self.running:
            dt = clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False

            # Check if we need to switch frame
            if ENGINE_CURRENT_FRAME is not None:
                if (self.current_frame is None
                        or ENGINE_CURRENT_FRAME != self.current_frame.name):
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
ENGINE_CURRENT_FRAME = None

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
        self.canvas = tk.Canvas(self, width=600, height=400, bg="gray")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_click)

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
                # We clicked on an existing object -> select it for dragging
                self.dragging_item = clicked[0]
                coords = self.canvas.coords(self.dragging_item)
                if len(coords) >= 2:
                    self.offset_x = event.x - coords[0]
                    self.offset_y = event.y - coords[1]
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
            # Possibly empty area; do nothing or create a new object
            pass

    def on_drag(self, event):
        # If dragging an existing item, move it
        if self.dragging_item:
            coords = self.canvas.coords(self.dragging_item)
            if len(coords) >= 2:
                # Determine if it's a rectangle or text
                # If rectangle -> coords = (x1,y1,x2,y2)
                # If text -> coords = (x_center, y_center)
                tags = self.canvas.gettags(self.dragging_item)
                # We'll find the corresponding rectangle if we grabbed the text
                if "obj_text" in tags:
                    # text only has (x_center, y_center)
                    # we need to figure out the rectangle as well
                    text_name = tags[1]
                    rect_id = None
                    for item in self.canvas.find_all():
                        if "obj" in self.canvas.gettags(item):
                            if text_name in self.canvas.gettags(item):
                                rect_id = item
                                break
                    if rect_id:
                        rect_coords = self.canvas.coords(rect_id)
                        if len(rect_coords) == 4:
                            x1, y1, x2, y2 = rect_coords
                            width = x2 - x1
                            height = y2 - y1
                            new_x = event.x - width//2
                            new_y = event.y - height//2
                            self.canvas.coords(rect_id, new_x, new_y, new_x+width, new_y+height)
                            self.canvas.coords(self.dragging_item, new_x + width//2, new_y + height//2)
                else:
                    if len(coords) == 4:
                        x1, y1, x2, y2 = coords
                        width = x2 - x1
                        height = y2 - y1
                        new_x1 = event.x - self.offset_x
                        new_y1 = event.y - self.offset_y
                        self.canvas.coords(self.dragging_item, new_x1, new_y1, new_x1+width, new_y1+height)
                        # Move corresponding text if any
                        item_tags = self.canvas.gettags(self.dragging_item)
                        if len(item_tags) >= 2:
                            obj_name = item_tags[1]
                            # find text item
                            for item in self.canvas.find_all():
                                t_tags = self.canvas.gettags(item)
                                if "obj_text" in t_tags and obj_name in t_tags:
                                    # center text in the rectangle
                                    self.canvas.coords(item, new_x1 + width//2, new_y1 + height//2)

    def on_release(self, event):
        # If we were dragging, update the object data in project_data
        if self.dragging_item:
            tags = self.canvas.gettags(self.dragging_item)
            if len(tags) >= 2:
                obj_name = tags[1]
                # If it's text, we need the rectangle
                if "obj_text" in tags:
                    # find the rectangle
                    rect_id = None
                    for item in self.canvas.find_all():
                        if "obj" in self.canvas.gettags(item):
                            if obj_name in self.canvas.gettags(item):
                                rect_id = item
                                break
                    if rect_id:
                        coords = self.canvas.coords(rect_id)
                    else:
                        coords = None
                else:
                    coords = self.canvas.coords(self.dragging_item)

                if coords and len(coords) == 4:
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

    def conditions_to_str(self, conditions):
        parts = []
        for c in conditions:
            c_type = c["type"]
            params = c["params"]
            if c_type == "KeyPressed":
                parts.append(f"KeyPressed(key={params.get('key','')})")
            elif c_type == "ObjectCollision":
                a = params.get("obj_name_a", "")
                b = params.get("obj_name_b", "")
                parts.append(f"ObjectCollision({a},{b})")
        return "; ".join(parts)

    def actions_to_str(self, actions):
        parts = []
        for a in actions:
            a_type = a["type"]
            params = a["params"]
            if a_type == "ChangeObjectColor":
                parts.append(f"ChangeObjectColor({params.get('obj_name','')},{params.get('color','')})")
            elif a_type == "DestroyObject":
                parts.append(f"DestroyObject({params.get('obj_name','')})")
            elif a_type == "GoToFrame":
                parts.append(f"GoToFrame({params.get('frame_name','')})")
        return "; ".join(parts)

    def add_event(self):
        # Pop up a small dialog to define conditions/actions
        EventDialog(self, new_event=True)

    def edit_event(self):
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        # open dialog with existing data
        EventDialog(self, new_event=False, event_index=index)

    def delete_event(self):
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        if index < len(self.events_data):
            self.events_data.pop(index)

        # Update project_data
        fdata = find_frame_data(self.current_frame_name)
        if fdata:
            fdata["events"] = self.events_data
        self.load_frame_events(self.current_frame_name)


class EventDialog(tk.Toplevel):
    def __init__(self, parent_editor: EventEditor, new_event=True, event_index=None):
        super().__init__(parent_editor)
        self.title("Event Editor")
        self.parent_editor = parent_editor
        self.new_event = new_event
        self.event_index = event_index

        # If editing existing event
        self.orig_conditions = []
        self.orig_actions = []
        if not new_event and event_index is not None:
            evt_data = self.parent_editor.events_data[event_index]
            self.orig_conditions = evt_data["conditions"][:]
            self.orig_actions = evt_data["actions"][:]

        self.conditions = self.orig_conditions[:]
        self.actions = self.orig_actions[:]

        # Condition list
        tk.Label(self, text="Conditions:").grid(row=0, column=0, sticky="w")
        self.conditions_list = tk.Listbox(self, width=50)
        self.conditions_list.grid(row=1, column=0, columnspan=3, sticky="w")
        self.update_conditions_listbox()

        tk.Button(self, text="Add Condition", command=self.add_condition).grid(row=2, column=0, sticky="w")
        tk.Button(self, text="Edit Condition", command=self.edit_condition).grid(row=2, column=1, sticky="w")
        tk.Button(self, text="Delete Condition", command=self.delete_condition).grid(row=2, column=2, sticky="w")

        # Actions list
        tk.Label(self, text="Actions:").grid(row=3, column=0, sticky="w")
        self.actions_list = tk.Listbox(self, width=50)
        self.actions_list.grid(row=4, column=0, columnspan=3, sticky="w")
        self.update_actions_listbox()

        tk.Button(self, text="Add Action", command=self.add_action).grid(row=5, column=0, sticky="w")
        tk.Button(self, text="Edit Action", command=self.edit_action).grid(row=5, column=1, sticky="w")
        tk.Button(self, text="Delete Action", command=self.delete_action).grid(row=5, column=2, sticky="w")

        # OK/Cancel
        tk.Button(self, text="OK", command=self.on_ok).grid(row=6, column=0, pady=5)
        tk.Button(self, text="Cancel", command=self.destroy).grid(row=6, column=1, pady=5)

    def update_conditions_listbox(self):
        self.conditions_list.delete(0, tk.END)
        for c in self.conditions:
            c_type = c["type"]
            params = c["params"]
            if c_type == "KeyPressed":
                display = f"{c_type}(key={params.get('key','')})"
            elif c_type == "ObjectCollision":
                display = f"{c_type}({params.get('obj_name_a','')},{params.get('obj_name_b','')})"
            else:
                display = f"{c_type}(...)"
            self.conditions_list.insert(tk.END, display)

    def update_actions_listbox(self):
        self.actions_list.delete(0, tk.END)
        for a in self.actions:
            a_type = a["type"]
            params = a["params"]
            if a_type == "ChangeObjectColor":
                display = f"{a_type}({params.get('obj_name','')},{params.get('color','')})"
            elif a_type == "DestroyObject":
                display = f"{a_type}({params.get('obj_name','')})"
            elif a_type == "GoToFrame":
                display = f"{a_type}({params.get('frame_name','')})"
            else:
                display = f"{a_type}(...)"
            self.actions_list.insert(tk.END, display)

    # Condition actions
    def add_condition(self):
        ConditionActionDialog(self, "Condition", new_item=True, item_list=self.conditions).wait_window()
        self.update_conditions_listbox()

    def edit_condition(self):
        selection = self.conditions_list.curselection()
        if not selection:
            return
        index = selection[0]
        ConditionActionDialog(self, "Condition", new_item=False,
                              item_index=index, item_list=self.conditions).wait_window()
        self.update_conditions_listbox()

    def delete_condition(self):
        selection = self.conditions_list.curselection()
        if not selection:
            return
        index = selection[0]
        self.conditions.pop(index)
        self.update_conditions_listbox()

    # Action actions
    def add_action(self):
        ConditionActionDialog(self, "Action", new_item=True, item_list=self.actions).wait_window()
        self.update_actions_listbox()

    def edit_action(self):
        selection = self.actions_list.curselection()
        if not selection:
            return
        index = selection[0]
        ConditionActionDialog(self, "Action", new_item=False,
                              item_index=index, item_list=self.actions).wait_window()
        self.update_actions_listbox()

    def delete_action(self):
        selection = self.actions_list.curselection()
        if not selection:
            return
        index = selection[0]
        self.actions.pop(index)
        self.update_actions_listbox()

    def on_ok(self):
        # Save the conditions/actions to the event
        if self.new_event:
            # add a new event to the parent's events_data
            self.parent_editor.events_data.append({
                "conditions": self.conditions,
                "actions": self.actions
            })
        else:
            # update existing
            self.parent_editor.events_data[self.event_index] = {
                "conditions": self.conditions,
                "actions": self.actions
            }

        # Update project_data
        fdata = find_frame_data(self.parent_editor.current_frame_name)
        if fdata:
            fdata["events"] = self.parent_editor.events_data
        self.parent_editor.load_frame_events(self.parent_editor.current_frame_name)
        self.destroy()


class ConditionActionDialog(tk.Toplevel):
    def __init__(self, parent_dialog: EventDialog, mode="Condition",
                 new_item=True, item_index=None, item_list=None):
        super().__init__(parent_dialog)
        self.title(f"Edit {mode}")
        self.parent_dialog = parent_dialog
        self.mode = mode  # "Condition" or "Action"
        self.new_item = new_item
        self.item_index = item_index
        self.item_list = item_list

        if self.mode == "Condition":
            self.type_choices = CONDITION_TYPES
            self.params_template = CONDITION_PARAMS_TEMPLATE
        else:
            self.type_choices = ACTION_TYPES
            self.params_template = ACTION_PARAMS_TEMPLATE

        self.var_type = tk.StringVar(value=self.type_choices[0])
        tk.Label(self, text=f"{mode} Type:").grid(row=0, column=0, sticky="w")
        self.type_menu = ttk.Combobox(self, textvariable=self.var_type, values=self.type_choices, state="readonly")
        self.type_menu.grid(row=0, column=1, sticky="w")

        # We'll create placeholders for param fields
        self.param_entries = {}
        self.params_frame = tk.Frame(self)
        self.params_frame.grid(row=1, column=0, columnspan=2, sticky="w")

        self.update_params_ui()

        # Load existing if editing
        if not self.new_item and self.item_index is not None and 0 <= self.item_index < len(self.item_list):
            existing = self.item_list[self.item_index]
            self.var_type.set(existing["type"])
            self.update_params_ui()  # re-draw fields
            # fill param values
            for k, v in existing["params"].items():
                if k in self.param_entries:
                    self.param_entries[k].delete(0, tk.END)
                    self.param_entries[k].insert(0, str(v))

        # Watch for changes in type
        self.type_menu.bind("<<ComboboxSelected>>", lambda e: self.update_params_ui())

        # OK/Cancel
        tk.Button(self, text="OK", command=self.on_ok).grid(row=2, column=0, pady=5)
        tk.Button(self, text="Cancel", command=self.destroy).grid(row=2, column=1, pady=5)

    def update_params_ui(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()

        sel_type = self.var_type.get()
        param_keys = self.params_template.get(sel_type, [])
        self.param_entries = {}

        row_idx = 0
        for k in param_keys:
            tk.Label(self.params_frame, text=f"{k}:").grid(row=row_idx, column=0, sticky="w")
            e = tk.Entry(self.params_frame, width=20)
            e.grid(row=row_idx, column=1, sticky="w")
            self.param_entries[k] = e
            row_idx += 1

    def on_ok(self):
        sel_type = self.var_type.get()
        param_dict = {}
        for k, e in self.param_entries.items():
            param_dict[k] = e.get()

        if self.new_item:
            self.item_list.append({
                "type": sel_type,
                "params": param_dict
            })
        else:
            self.item_list[self.item_index] = {
                "type": sel_type,
                "params": param_dict
            }

        self.destroy()


# -------------------------------------------------------------------------------
# Main Editor Window
# -------------------------------------------------------------------------------
class FusionCloneEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fusion-Like Clone Editor")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Scenes (Frames) list
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="y")

        self.frame_listbox = tk.Listbox(left_frame, width=20)
        self.frame_listbox.pack(side="top", fill="y", expand=True)

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(side="bottom", fill="x")

        tk.Button(btn_frame, text="Add Frame", command=self.add_frame).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Remove Frame", command=self.remove_frame).pack(side="left", padx=5, pady=5)

        tk.Button(left_frame, text="Run", command=self.run_game).pack(side="bottom", padx=5, pady=5)

        # Scene Editor tab
        self.scene_editor = SceneEditor(self.notebook, self)
        self.notebook.add(self.scene_editor, text="Scene Editor")

        # Event Editor tab
        self.event_editor = EventEditor(self.notebook, self)
        self.notebook.add(self.event_editor, text="Event Editor")

        # Menu bar for saving/loading
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_project)
        filemenu.add_command(label="Open", command=self.open_project)
        filemenu.add_command(label="Save", command=self.save_project)
        filemenu.add_command(label="Save As", command=self.save_project_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

        # Keep track of filename
        self.current_filename = None

        # Auto-refresh selection
        self.frame_listbox.bind("<<ListboxSelect>>", self.on_select_frame)

    def add_frame(self):
        new_name = f"Frame{len(project_data['frames'])+1}"
        frame_data = {
            "name": new_name,
            "bg_color": [0,0,0],
            "objects": [],
            "events": []
        }
        project_data["frames"].append(frame_data)
        self.refresh_frames_list()
        # auto-select it
        self.frame_listbox.selection_clear(0, tk.END)
        self.frame_listbox.selection_set(tk.END)
        self.on_select_frame(None)

    def remove_frame(self):
        sel = self.frame_listbox.curselection()
        if not sel:
            return
        index = sel[0]
        del project_data["frames"][index]
        self.refresh_frames_list()
        self.scene_editor.load_frame(None)
        self.event_editor.load_frame_events(None)

    def refresh_frames_list(self):
        self.frame_listbox.delete(0, tk.END)
        for f in project_data["frames"]:
            self.frame_listbox.insert(tk.END, f["name"])

    def on_select_frame(self, event):
        sel = self.frame_listbox.curselection()
        if not sel:
            return
        index = sel[0]
        f_name = project_data["frames"][index]["name"]
        self.scene_editor.load_frame(f_name)
        self.event_editor.load_frame_events(f_name)

    def run_game(self):
        # Spin up the engine in a separate loop
        engine = FusionCloneEngine()
        engine.load_project(project_data)
        # If there's a selected frame, start there
        sel = self.frame_listbox.curselection()
        if sel:
            index = sel[0]
            start_name = project_data["frames"][index]["name"]
            engine.change_frame(start_name)
        self.withdraw()  # hide editor
        engine.main_loop()
        self.deiconify()  # show editor again

    # Project file operations
    def new_project(self):
        global project_data
        project_data = {"frames": []}
        self.current_filename = None
        self.refresh_frames_list()
        self.scene_editor.load_frame(None)
        self.event_editor.load_frame_events(None)

    def open_project(self):
        filepath = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            with open(filepath, "r") as f:
                data = json.load(f)
            global project_data
            project_data = data
            self.current_filename = filepath
            self.refresh_frames_list()
            self.scene_editor.load_frame(None)
            self.event_editor.load_frame_events(None)

    def save_project(self):
        if not self.current_filename:
            self.save_project_as()
        else:
            with open(self.current_filename, "w") as f:
                json.dump(project_data, f, indent=2)
            messagebox.showinfo("Save", "Project saved.")

    def save_project_as(self):
        filepath = filedialog.asksaveasfilename(
            title="Save Project As",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            self.current_filename = filepath
            self.save_project()


if __name__ == "__main__":
    app = FusionCloneEditor()
    app.mainloop()
