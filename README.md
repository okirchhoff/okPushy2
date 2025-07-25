## Tool: okPushy v2.1.0

## The Maker
by Oliver Kirchhoff (kirchhoff.oliver@gmail.com)  
IMDB: [http://www.imdb.com/name/nm0456285/](http://www.imdb.com/name/nm0456285/) 

## Description
okPushy is an advanced interactive tool for Autodesk Maya designed to give artists a fast, gizmo-free method for adjusting the depth of a selection. Activated entirely by a press-and-hold hotkey, it allows for the intuitive "pushing" (away from the camera) and "pulling" (toward the camera) of objects and components simply by dragging the mouse.

![Photo Modelling Demo](https://drive.google.com/file/d/1ivaFj8JGuktOS-FraWvWg653Bqs-x0V_/view?usp=drive_link)

## Core Features:
- **Intuitive, Hotkey-Driven Workflow:** The tool is only active while a hotkey is held down. Press to start, drag to push/pull, and release to return instantly to your previous tool.
- **Universal Selection Support:** Works seamlessly in both **Object Mode** and **Component Mode**.
- **Robust Component Handling:** Intelligently handles any selection of vertices, edges, and faces—even mixed selections—by converting them to a unified vertex list to prevent any collapsing or unwanted distortion.
- **Context-Aware View Logic:**
 - In a **Perspective** view, it moves the selection along vectors projected from the camera, creating a natural dolly or zoom effect on the elements.
 - In an **Orthographic** view, it moves all components uniformly along the camera's viewing axis.
- **Perspective Scale Compensation:** When in object mode, hold the Ctrl key while dragging to automatically scale objects as they move. This maintains their apparent size from the camera's point of view, making it an incredibly powerful tool for composition and layout.

## Hotkeys in Maya        
### Copy this to your hotkey-press event:
```python
import sys
import importlib
if 'okPushy2' not in sys.modules:
    script_path = "F:/GitHub/okpushy" # Adjust this path to where okPushy2.py is located
    if script_path not in sys.path:
        sys.path.append(script_path)
import okPushy2
okPushy2.okPushyActivate()
```
### Copy this to your hotkey-release event:
```python
import okPushy2
okPushy2.okPushyDeactivate()
```
