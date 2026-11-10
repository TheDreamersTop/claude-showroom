"""Slow-motion cap pop, macro on the neck. blender -b -P pop_anim.py -- <outdir> [first last] [preview]"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lib, scenes

argv = sys.argv[sys.argv.index('--') + 1:]
outdir = argv[0]
f0, f1 = (int(argv[1]), int(argv[2])) if len(argv) > 2 else (1, 48)
preview = 'preview' in argv
os.makedirs(outdir, exist_ok=True)

lib.reset()
scenes.era_hero('macro')
sc = bpy.context.scene
scenes.finish('mid')
sc.render.resolution_x, sc.render.resolution_y = (640, 360) if preview else (960, 540)
sc.cycles.samples = 12 if preview else 16
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.5
cam = sc.camera
cam.data.dof.aperture_fstop = 3.5

cap = [o for o in bpy.data.objects if o.name.startswith('Cap')][0]
REST = Vector((0, 0, 0.2068))
LIFT = 7  # frame where the cap lets go


def cap_pose(f):
    if f <= LIFT:
        k = max(0, (f - (LIFT - 3)) / 3)
        return REST + Vector((0, 0, 0.0006 * k)), (0.0, 0.0, 0.0)
    u = (f - LIFT) / 24.0  # seconds of slow-mo "time"
    pos = REST + Vector((0.016 * u, -0.008 * u, 0.0006 + 0.05 * u - 0.012 * u * u))
    rot = (2.2 * u, 0.7 * u, 0.5 * u)
    return pos, rot


for f in range(1, 50):
    p, r = cap_pose(f)
    cap.location = p
    cap.rotation_euler = r
    cap.keyframe_insert('location', frame=f)
    cap.keyframe_insert('rotation_euler', frame=f)

# spray: small droplets thrown up from the mouth after release
rnd = random.Random(3)
drop_m = lib.mat_water()
for i in range(26):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.0004, 0.0011), segments=12, ring_count=8)
    d = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    d.data.materials.append(drop_m)
    a = rnd.uniform(0, math.tau)
    v = Vector((math.cos(a) * rnd.uniform(0.005, 0.02), math.sin(a) * rnd.uniform(0.005, 0.02), rnd.uniform(0.03, 0.07)))
    start = LIFT + rnd.uniform(0, 4)
    for f in range(1, 50):
        if f < start:
            pos = Vector((0, 0, 0.203))
            d.scale = (0.001, 0.001, 0.001)
        else:
            u = (f - start) / 24.0
            pos = Vector((0, 0, 0.205)) + v * u + Vector((0, 0, -0.2 * u * u))
            d.scale = (1, 1, 1)
        d.location = pos
        d.keyframe_insert('location', frame=f)
        d.keyframe_insert('scale', frame=f)

for f in range(f0, f1 + 1):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(outdir, '%03d.png' % f)
    bpy.ops.render.render(write_still=True)
    print('POP_FRAME', f, flush=True)
