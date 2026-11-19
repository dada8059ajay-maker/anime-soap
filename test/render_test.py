# Blender + VRM 5-10s homework test
# One character, two shots, 720p / 12fps, Workbench engine.
# Shot 1 (frames 1-60): slow head turn + blink.
# Shot 2 (frames 61-120): right arm raises into a teaching/point gesture.
# PASS = <10 min runner time + identical face in both shots + smooth motion.
# NOTE: bone-axis signs (head yaw axis, arm raise axis) and facing direction
# are VERIFIED FROM THE RENDERED FRAMES, not assumed -- adjust after frame check.
import argparse
import math
import os
import sys
import time

import bpy
from mathutils import Vector

T0 = time.time()


def log(msg):
    print(f"[TEST {time.time() - T0:7.1f}s] {msg}", flush=True)


ap = argparse.ArgumentParser()
ap.add_argument("--addon-legacy", required=True)
ap.add_argument("--vrm", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

# --- import VRM (extension install is attempted by the workflow first) ---
imported = False
try:
    bpy.ops.import_scene.vrm(filepath=args.vrm)
    imported = True
    log("imported VRM via already-installed add-on")
except Exception as e:
    log(f"direct import failed ({e}); trying legacy add-on install")
    bpy.ops.preferences.addon_install(filepath=args.addon_legacy)
    bpy.ops.preferences.addon_enable(module="io_scene_vrm")
    bpy.ops.import_scene.vrm(filepath=args.vrm)
    imported = True
    log("imported VRM after legacy add-on install")
assert imported

arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
assert arm, "no armature after VRM import"
log(f"armature: {arm.name}")
log(f"scene objects: {[o.name for o in bpy.context.scene.objects]}")

# --- scene setup ---
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.fps = 12
scene.frame_start = 1
scene.frame_end = 120
scene.render.image_settings.file_format = "PNG"
os.makedirs(args.out, exist_ok=True)
scene.render.filepath = os.path.join(args.out, "frame_")

# ground plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
gmat = bpy.data.materials.new("GroundMat")
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.92, 0.92, 0.94, 1)
ground.data.materials.append(gmat)

# bright studio world
world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.88, 0.89, 0.92, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# camera (front, head height)
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
cam.location = (0.0, -2.4, 1.5)
cam.rotation_euler = (Vector((0.0, 0.0, 1.35)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
log(f"camera at {tuple(round(v, 2) for v in cam.location)}")

# sun + front fill
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))

fill_data = bpy.data.lights.new("Fill", "AREA")
fill_data.energy = 300
fill_data.shape = "DISK"
fill_data.size = 1.0
fill = bpy.data.objects.new("Fill", fill_data)
scene.collection.objects.link(fill)
fill.location = (0.0, -2.0, 1.8)
fill.rotation_euler = (Vector((0.0, 0.0, 1.35)) - fill.location).to_track_quat("-Z", "Y").to_euler()

# --- posing ---
pb = arm.pose.bones
for b in pb:
    try:
        b.rotation_mode = "XYZ"
    except Exception:
        pass


def key(bone_name, frame, euler):
    b = pb.get(bone_name)
    if b is None:
        log(f"WARN missing bone {bone_name}")
        return False
    b.rotation_euler = euler
    b.keyframe_insert(data_path="rotation_euler", frame=frame)
    return True


# Shot 1: head turn, frames 1-60 (yaw on local Y; verify from frames)
key("head", 1, (0, -0.35, 0))
key("head", 30, (0, 0.35, 0))
key("head", 60, (0, 0, 0))
key("neck", 1, (0, -0.10, 0))
key("neck", 30, (0, 0.10, 0))
key("neck", 60, (0, 0, 0))

# blink (frames 25-31) if a blink shape key exists
blinked = False
for obj in bpy.context.scene.objects:
    if obj.type != "MESH" or not obj.data.shape_keys:
        continue
    for kb in obj.data.shape_keys.key_blocks:
        if "blink" in kb.name.lower():
            kb.value = 0
            kb.keyframe_insert(data_path="value", frame=25)
            kb.value = 1
            kb.keyframe_insert(data_path="value", frame=28)
            kb.value = 0
            kb.keyframe_insert(data_path="value", frame=31)
            log(f"blink animated on {obj.name} / {kb.name}")
            blinked = True
if not blinked:
    log("no blink shape key found (skipped)")

# Shot 2: right arm teaching gesture, frames 61-120
key("rightUpperArm", 61, (0, 0, 0))
key("rightUpperArm", 75, (-1.1, 0, -0.2))
key("rightUpperArm", 90, (-1.0, 0, -0.15))
key("rightUpperArm", 120, (-1.0, 0, -0.15))
key("rightLowerArm", 61, (0, 0, 0))
key("rightLowerArm", 75, (-0.35, 0, 0))
key("rightLowerArm", 120, (-0.35, 0, 0))
key("head", 75, (-0.08, 0, 0))
key("head", 120, (-0.08, 0, 0))
log("poses keyed: shot1 head turn, shot2 right-arm teach gesture")

# --- render ---
log("rendering 120 frames @ 12fps, 720p, Workbench")
t = time.time()
bpy.ops.render.render(animation=True)
log(f"render done in {time.time() - t:.1f}s")
files = sorted(os.listdir(args.out))
log(f"frames written: {len(files)} (first={files[0] if files else '-'}, last={files[-1] if files else '-'})")
log(f"total script time: {time.time() - T0:.1f}s")
