"""Cloud-sea shots. Clouds are static; jet and camera fly through the world.
usage: SHOT=c2 python shots_clouds.py   (env PCT, SPP, STEP, F0, F1 for tests)"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import jet, env, bpy
from mathutils import Vector, Euler, Matrix

SHOT = os.environ.get('SHOT', 'c2')
V = 240.0          # m/s cruise (screen speed)
AMP = 66.0
DECK = -0.6*558 - 110   # cloud deck origin z so the jet clears the 99th-percentile tops

# per-shot: duration (s), sun elevation (sky), sun azimuth rot, lamp elev, lens, camera function
def lerp(a, b, t): return a + (b - a)*t
def ease(t): return t*t*(3 - 2*t)

SHOTS = {
    # establishing wide: high behind-right, jet small over the cloud sea, sun ahead on the horizon
    'c1': dict(dur=6.0, elev=0.9, rot=80, lel=5, lens=40,
               cam=lambda t: (Vector((-250 + 16*t, -70 + 4*t, 32 - 1.5*t)), Vector((2000, 300, -60)))),
    # side track, backlit, sun in frame behind the jet
    'c2': dict(dur=6.0, elev=0.8, rot=150, lel=4, lens=50,
               cam=lambda t: (Vector((-14 + 3.2*t, 52, 3.5)), Vector((-3 + 1.0*t, 0, 0.5)))),
    # wing detail: camera just above the left wing root looking out along the wing toward the sun
    'c3': dict(dur=5.0, elev=0.8, rot=10, lel=4, lens=24,
               cam=lambda t: (Vector((-3.2 - 0.25*t, 1.7 + 0.12*t, 0.9)), Vector((-6.5, 14.0, 0.9 - 0.05*t)))),
    # front three-quarter: jet slowly overtakes camera, front-lit by sun behind camera
    'c4': dict(dur=6.0, elev=0.9, rot=57, lel=5, lens=35,
               cam=lambda t: (Vector((46 - 9.5*t, 30 - 1.5*t, -6 + 0.5*t)), Vector((2 - 1.2*t, 0, 0)))),
    # tele: jet crosses the sun disc; sun rises (animated in script)
    'c5': dict(dur=9.0, elev=0.25, elev1=1.4, rot=90, lel=4, lens=300,
               cam=lambda t: (Vector((-1250, 0, -5.5)), Vector((0, 0, 0)))),
    # hero: jet flies away into the sun
    'c6': dict(dur=6.0, elev=1.9, rot=88, lel=5, lens=32,
               cam=lambda t: (Vector((-28 - 30*ease(t/6), -9, 2.5 - 0.3*t)), Vector((1500, -40, -40)))),
}

S = SHOTS[SHOT]
sc = reset()
sc.cycles.samples = int(os.environ.get('SPP', 40))
sc.render.resolution_percentage = int(os.environ.get('PCT', 100))
sc.render.use_motion_blur = (os.environ.get('PASS', 'bg') == 'fg')
sc.render.motion_blur_shutter = 0.5
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2
PASS = os.environ.get('PASS', 'bg')
SUB = int(os.environ.get('SUB', 3))     # bg: clouds+sky, camera moves; fg: jet static at origin, alpha
w, skies = env.sunset_world(S['elev'], S['rot'], altitude=6000, dust=2.0)
lamp = env.add_sun_lamp(S['lel'], S['rot'], 45, (1.0, 0.45, 0.18))
deck = S.get('deck', DECK)
if PASS == 'bg':
    clouds, mat = env.cloud_sea(z=deck, sky=skies[1], amp=AMP, haze_start=2500, haze_dist=30000)
    if SHOT == 'c5': skies[0].sun_disc = False
else:
    root, gear = jet.build_jet(os.path.join(TEX, 'side.png'), os.path.join(TEX, 'fin.png'), gear=False)
    for g in gear: g.hide_render = True
    # stand-in cloud floor for bounce light and reflections, invisible to camera
    pm = bpy.data.materials.new('floor'); b = pm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.75, 0.62, 0.58, 1); b.inputs['Roughness'].default_value = 1.0
    bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, deck + 200)); fl = bpy.context.active_object
    fl.data.materials.append(pm); fl.visible_camera = False
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = 'RGBA'

cd = bpy.data.cameras.new('cam'); cd.lens = S['lens']; cd.sensor_width = 36; cd.clip_start = 0.1; cd.clip_end = 900000
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
if SHOT == 'c3':
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 2.8; cd.dof.focus_distance = 7.0

nf = int(round(S['dur']*24))
sc.frame_start, sc.frame_end = 1, nf
prev_e = None; prev_old = None; JUMPS = []
for f in range(1, nf + 1):
    t = (f - 1)/24.0
    if SHOT == 'c5':
        jp = Vector((V*t, lerp(-55, 35, t/S['dur']), 0))
    else:
        jp = Vector((V*t, 0, 0.6*math.sin(t*0.9)))
    bank = math.radians(1.2*math.sin(t*0.7 + 0.5))
    pitch = math.radians(2.0 + 0.3*math.sin(t*0.5))
    loc, aim = S['cam'](t)
    if SHOT == 'c3':
        M = Matrix.Translation(jp) @ Euler((bank, -pitch, 0)).to_matrix().to_4x4()
        cl = M @ loc; ca = M @ aim
    elif SHOT == 'c5':
        cl = Vector((V*t, 0, 0)) + loc; ca = Vector((V*t, 0, 0)) + aim
    else:
        cl = jp + loc; ca = jp + aim
    if PASS == 'fg':
        root.location = (0, 0, 0); root.rotation_euler = Euler((bank, -pitch, 0))
        root.keyframe_insert('rotation_euler', frame=f)
        cl = cl - jp; ca = ca - jp
    cam.location = cl
    q_ = (ca - cl).to_track_quat('-Z', 'Y')
    e_old = q_.to_euler()
    e_new = q_.to_euler('XYZ', prev_e) if prev_e is not None else e_old
    if prev_old is not None and max(abs(a_ - b_) for a_, b_ in zip(e_old, prev_old)) > 3.0: JUMPS.append(f)
    prev_old = e_old; prev_e = e_new
    cam.rotation_euler = e_new
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)

print('JUMPS', SHOT, PASS, JUMPS, flush=True)
if os.environ.get('DRYRUN'): sys.exit(0)
outdir = os.path.join(ROOT, 'renders', SHOT + '_' + PASS)
f0 = int(os.environ.get('F0', 1)); f1 = int(os.environ.get('F1', nf)); step = int(os.environ.get('STEP', 1))
for f in range(f0, f1 + 1, step):
    path = os.path.join(outdir, f'{f:04d}.png')
    if os.path.exists(path) and not os.environ.get('FORCE'): continue
    if PASS == 'bg' and SUB > 1:
        import numpy as np
        from PIL import Image
        acc = None
        for k in range(SUB):
            off = -0.25 + 0.5*k/(SUB - 1)          # 180-degree shutter
            ff = f + off; fi = math.floor(ff)
            sc.frame_set(fi, subframe=ff - fi)
            tmp = os.path.join(outdir, f'_sub{k}.png'); sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            a = np.asarray(Image.open(tmp).convert('RGB')).astype(np.float32)
            acc = a if acc is None else acc + a
        Image.fromarray(np.clip(acc/SUB + 0.5, 0, 255).astype(np.uint8)).save(path)
    else:
        sc.frame_set(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
    print('FRAME', SHOT, PASS, f, flush=True)
