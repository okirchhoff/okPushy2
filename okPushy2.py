# okPushy_py v2.1.0
#
# okPushy is a hotkey-driven tool for Autodesk Maya that allows you to interactively 
# push and pull objects or components along the camera's line of sight. Simply press 
# a hotkey and drag your mouse left or right to intuitively control the depth of your 
# selection.
#
# Original MEL by Oliver Kirchhoff (kirchhoff.oliver@gmail.com)
# IMDB: http://www.imdb.com/name/nm0456285/ 
# 
# Python translation, enhancement and refactoring by Google's Gemini
#
# v2.1.0 (25/07/2025):
#   - FIXED Mixed-Component Selection: The script now correctly handles selections
#     containing a mix of vertices, edges, and faces. It inspects the entire
#     selection and converts all components to a unified list of vertices if any
#     edges or faces are present, preventing any component collapsing.
# v2.0.9 (24/07/2025):
#   - FINAL FIX for Component Handling: Face and Edge selections no longer collapse.
#   - Adjusted default orthographic movement speed.
# ... (previous changelog entries)
#
####################################################################################
############ Copy this to your hotkey-press event: (Python)
'''
import sys
import importlib
if 'okPushy2' not in sys.modules:
    script_path = "F:/GitHub/okpushy" # Adjust this path to where okPushy2.py is located
    if script_path not in sys.path:
        sys.path.append(script_path)
import okPushy2
okPushy2.okPushyActivate()
'''
####################################################################################
############ Copy this to your hotkey-release event: (Python)
'''
import okPushy2
okPushy2.okPushyDeactivate()
'''
####################################################################################

import maya.cmds as cmds
import maya.api.OpenMaya as om

class OkPushyTool:
    """
    Manages the state and logic of the okPushy tool in a robust, class-based structure.
    """
    CONTEXT_NAME = "okPushyContext_py"
    SENSITIVITY = 0.005

    def __init__(self):
        """Initializes the tool instance."""
        self.former_context = ""
        self._reset_state()

    def _reset_state(self):
        """Atomically resets all per-drag state variables to ensure a clean start."""
        self.is_ready = False
        self.selection = []
        self.is_ortho = False
        self.is_component_mode = False
        self.scale_compensate = False
        self.initial_positions = []
        self.initial_vectors = []
        self.initial_scales = {}
        self.camera_pos = om.MVector()
        self.initial_avg_pos = om.MVector()
        self.cam_to_avg_vec = om.MVector()
        self.view_direction = om.MVector()
        self.anchor_point = [0.0, 0.0]

    def activate(self):
        """Creates and activates the dragger context."""
        self.former_context = cmds.currentCtx()
        if cmds.draggerContext(self.CONTEXT_NAME, exists=True):
            cmds.deleteUI(self.CONTEXT_NAME)
        cmds.draggerContext(
            self.CONTEXT_NAME,
            pressCommand=self.on_press,
            dragCommand=self.on_drag,
            releaseCommand=self.on_release,
            cursor="dolly",
            space="screen",
            undoMode="none"
        )
        cmds.setToolTo(self.CONTEXT_NAME)

    def deactivate(self):
        """Deactivates the tool and restores the previous context."""
        if cmds.currentCtx() == self.CONTEXT_NAME and self.former_context:
            cmds.setToolTo(self.former_context)

    def on_press(self):
        """
        Gathers all necessary initial data for the drag operation when the mouse is pressed.
        """
        self._reset_state()
        cmds.undoInfo(openChunk=True)

        panel = cmds.getPanel(withFocus=True)
        if not panel or "modelPanel" not in cmds.getPanel(typeOf=panel):
            cmds.undoInfo(closeChunk=True); return

        cam_transform = cmds.modelEditor(panel, query=True, camera=True)
        cam_shape = cmds.listRelatives(cam_transform, shapes=True)[0]
        self.is_ortho = cmds.getAttr(f"{cam_shape}.orthographic")

        selection_raw = cmds.ls(selection=True, long=True, flatten=True)
        if not selection_raw:
            cmds.undoInfo(closeChunk=True); return

        # --- NEW & IMPROVED COMPONENT HANDLING (v2.1.0) ---
        self.is_component_mode = any('.' in item for item in selection_raw)

        if self.is_component_mode:
            # Check the ENTIRE selection for faces or edges, not just the first item.
            has_faces_or_edges = any((".f[" in s or ".e[" in s) for s in selection_raw)

            if has_faces_or_edges:
                # If any faces or edges are found, convert the WHOLE selection to vertices.
                # This correctly handles mixed selections (e.g., vtx + face).
                verts_from_components = cmds.polyListComponentConversion(selection_raw, toVertex=True)
                self.selection = cmds.ls(verts_from_components, flatten=True, long=True)
            else:
                # The selection is only vertices or CVs, which is fine.
                self.selection = selection_raw
        else:
            # Object mode: filter for transforms only
            self.selection = cmds.ls(selection_raw, type='transform', long=True)

        if not self.selection:
            cmds.undoInfo(closeChunk=True); return

        modifier = cmds.draggerContext(self.CONTEXT_NAME, query=True, modifier=True)
        self.scale_compensate = (modifier == "ctrl") or (self.former_context == "scaleSuperContext")

        for item in self.selection:
            pos = cmds.xform(item, query=True, worldSpace=True, translation=True)
            self.initial_positions.append(om.MVector(pos[0], pos[1], pos[2]))

        if not self.initial_positions:
            cmds.undoInfo(closeChunk=True); return

        if self.is_ortho:
            cam_matrix_list = cmds.getAttr(f"{cam_transform}.worldMatrix[0]")
            z_axis_vector = om.MVector(cam_matrix_list[8], cam_matrix_list[9], cam_matrix_list[10])
            self.view_direction = (z_axis_vector * -1.0).normal()
        else:
            # Using xform bounding box for components is more reliable
            bbox_nodes = self.selection if self.is_component_mode else cmds.listRelatives(self.selection, shapes=True, noIntermediate=True, fullPath=True) or self.selection
            bbox = cmds.exactWorldBoundingBox(bbox_nodes, ignoreInvisible=True)
            if not bbox:
                 cmds.undoInfo(closeChunk=True); return

            self.initial_avg_pos = om.MVector((bbox[0]+bbox[3])/2.0, (bbox[1]+bbox[4])/2.0, (bbox[2]+bbox[5])/2.0)
            self.camera_pos = om.MVector(cmds.xform(cam_transform, query=True, worldSpace=True, translation=True))
            self.cam_to_avg_vec = self.initial_avg_pos - self.camera_pos
            self.initial_vectors = [pos - self.initial_avg_pos for pos in self.initial_positions]

            if self.scale_compensate and not self.is_component_mode:
                for item in self.selection:
                    scale_val = cmds.getAttr(f"{item}.scale")[0]
                    self.initial_scales[item] = om.MVector(scale_val[0], scale_val[1], scale_val[2])

        self.anchor_point = cmds.draggerContext(self.CONTEXT_NAME, query=True, anchorPoint=True)
        self.is_ready = True

    def on_drag(self):
        """Calculates and applies new positions (and scales) during a mouse drag."""
        if not self.is_ready:
            return

        drag_point = cmds.draggerContext(self.CONTEXT_NAME, query=True, dragPoint=True)
        change = (drag_point[0] - self.anchor_point[0]) * self.SENSITIVITY

        if self.is_ortho:
            total_move_vector = self.view_direction * change * 2
            for i, item in enumerate(self.selection):
                new_pos = self.initial_positions[i] + total_move_vector
                cmds.move(new_pos.x, new_pos.y, new_pos.z, item, absolute=True, worldSpace=True)
        else:
            change_depth = 1.0 + change
            new_avg_pos = self.camera_pos + (self.cam_to_avg_vec * change_depth)

            for i, item in enumerate(self.selection):
                scale_factor = change_depth if self.scale_compensate else 1.0
                offset_vec = self.initial_vectors[i] * scale_factor
                new_pos = new_avg_pos + offset_vec
                cmds.move(new_pos.x, new_pos.y, new_pos.z, item, absolute=True, worldSpace=True)

                if item in self.initial_scales:
                    initial_scale = self.initial_scales[item]
                    new_scale = initial_scale * scale_factor
                    cmds.scale(new_scale.x, new_scale.y, new_scale.z, item, absolute=True)
        cmds.refresh()

    def on_release(self):
        """Closes the undo chunk and resets state when the mouse is released."""
        cmds.undoInfo(closeChunk=True)
        self._reset_state()

# --- Global Functions for Hotkey Integration ---
ok_pushy_tool_instance = None

def okPushyActivate():
    """Function to be called by a 'press' hotkey."""
    global ok_pushy_tool_instance
    if ok_pushy_tool_instance is None:
        ok_pushy_tool_instance = OkPushyTool()
    ok_pushy_tool_instance.activate()

def okPushyDeactivate():
    """Function to be called by a 'release' hotkey."""
    global ok_pushy_tool_instance
    if ok_pushy_tool_instance:
        ok_pushy_tool_instance.deactivate()