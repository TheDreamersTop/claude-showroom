"""Hangar shots: h1 macro light sweep along the nose, h2 fin reveal, h3 doors open onto the sunset.
usage: SHOT=h1 python shots_hangar.py"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import jet, env, bpy
from jet import _n, math_node
from mathutils import Vector, Euler

SHOT = os.environ.get('SHOT', 'h1')
def lerp(a, b, t): return a + (b - a)*t
def ease(t): t = min(1, max(0, t)); return t*t*(3 - 2*t)

sc = reset()
sc.cycles.samples = int(os.environ.get('SPP', 64))
sc.render.resolution_percentage = int(os.environ.get('PCT', 100))
sc.cycles.max_bounces = 6

ELEV, ROT = 1.4, 90.0
w, skies = env.sunset_world(ELEV, ROT, altitude=300, dust=2.0)
lamp = env.add_sun_lamp(3.0, ROT, 60, (1.0, 0.42, 0.15), angle=1.0)

root, gear = jet.build_jet(os.path.join(TEX, 'side.png'), os.path.join(TEX, 'fin.png'), gear=True)
G = root['ground_offset']     # floor z

def mat(name, col, rough, metal=0.0):
    m = bpy.data.materials.new(name); b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m

def box(name, x0, x1, y0, y1, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1)/2, (y0 + y1)/2, (z0 + z1)/2))
    o = bpy.context.active_object; o.name = name; o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.data.materials.append(m); return o

# floor: polished concrete with a yellow guide line
fm = bpy.data.materials.new('floor'); nt = fm.node_tree; L = nt.links
b = nt.nodes['Principled BSDF']
tc = _n(nt, 'ShaderNodeTexCoord'); sep = _n(nt, 'ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
nz = _n(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.4; nz.inputs['Detail'].default_value = 6
L.new(tc.outputs['Object'], nz.inputs['Vector'])
rough = math_node(nt, 'ADD', 0.08, math_node(nt, 'MULTIPLY', nz.outputs['Fac'], 0.22))
L.new(rough, b.inputs['Roughness'])
line = math_node(nt, 'LESS_THAN', math_node(nt, 'ABSOLUTE', sep.outputs[1]), 0.07)
line = math_node(nt, 'MULTIPLY', line, math_node(nt, 'LESS_THAN', sep.outputs[0], 22.0))
mix = _n(nt, 'ShaderNodeMix'); mix.data_type = 'RGBA'; L.new(line, mix.inputs['Factor'])
mix.inputs[6].default_value = (0.045, 0.045, 0.048, 1); mix.inputs[7].default_value = (0.6, 0.42, 0.05, 1)
L.new(mix.outputs[2], b.inputs['Base Color'])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, G)); floor = bpy.context.active_object
floor.scale = (3000, 3000, 1); floor.data.materials.append(fm)

wall = mat('wall', (0.035, 0.035, 0.038), 0.85)
door_m = mat('door', (0.05, 0.052, 0.055), 0.45, 0.6)
XD, HY, HZ, DH = 22.0, 26.0, 17.0, 13.5   # door plane x, half width, height, door opening height
box('back', -32, -31, -HY, HY, G, G + HZ, wall)
box('sideL', -32, XD, HY, HY + 1, G, G + HZ, wall)
box('sideR', -32, XD, -HY - 1, -HY, G, G + HZ, wall)
box('roof', -32, XD + 1, -HY - 1, HY + 1, G + HZ, G + HZ + 1, wall)
box('lintel', XD, XD + 1, -HY, HY, G + DH, G + HZ, wall)
box('jambL', XD, XD + 1, 19, HY, G, G + DH, wall)
box('jambR', XD, XD + 1, -HY, -19, G, G + DH, wall)
dL = box('doorL', XD + 1.0, XD + 1.4, 0, 19.2, G, G + DH + 0.2, door_m)
dR = box('doorR', XD + 1.6, XD + 2.0, -19.2, 0, G, G + DH + 0.2, door_m)
# ceiling practicals (dim)
pm = bpy.data.materials.new('practical'); pn = pm.node_tree
for n in list(pn.nodes):
    if n.bl_idname == 'ShaderNodeBsdfPrincipled': pn.nodes.remove(n)
em = pn.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.85, 0.7, 1); em.inputs['Strength'].default_value = 6.0
pn.links.new(em.outputs[0], pn.nodes['Material Output'].inputs['Surface'])
for xx in (-24, -12, 0, 12):
    for yy in (-14, 0, 14):
        box(f'pr{xx}{yy}', xx - 2.5, xx + 2.5, yy - 0.12, yy + 0.12, G + HZ - 0.3, G + HZ - 0.1, pm)
practicals = [o for o in bpy.data.objects if o.name.startswith('pr')]

def strip_light(name, size=(0.12, 9.0), energy=2500, color=(1, 0.96, 0.92)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size; ld.energy = energy; ld.color = color
    o = bpy.data.objects.new(name, ld); sc.collection.objects.link(o)
    return o

cd = bpy.data.cameras.new('cam'); cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 900000
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam

def look(cl, ca, f, roll=0.0):
    cam.location = cl
    e = (Vector(ca) - Vector(cl)).to_track_quat('-Z', 'Y').to_euler()
    cam.rotation_euler = e
    if roll: cam.rotation_euler.rotate_axis('Z', math.radians(roll))
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)

if SHOT in ('h1', 'h2'):
    # doors closed, practicals off: only the travelling strip light
    for p in practicals: p.hide_render = True
    lamp.hide_render = True
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    sl = strip_light('strip', (0.10, 10.0), 900)
    soft = strip_light('soft', (14.0, 3.0), 140, (0.7, 0.8, 1.0))
    soft.location = (2, 12, 10); soft.rotation_euler = Euler((math.radians(-50), 0, 0))
    soft.location = (2, 14, 6); soft.rotation_euler = (Vector((0, 0, 0)) - Vector((2, 14, 6))).to_track_quat('-Z', 'Y').to_euler()

if SHOT == 'h1':
    dur = 7.0; cd.lens = 45
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 4.0
    nf = int(dur*24)
    for f in range(1, nf + 1):
        t = (f - 1)/(nf - 1)
        # light glides over the nose from front to back, a few metres above the fuselage
        sl.location = (lerp(14.0, 0.0, ease(t)*0.6 + t*0.4), 1.5, 4.2)
        sl.rotation_euler = (math.radians(-12), 0, 0)
        sl.keyframe_insert('location', frame=f); sl.keyframe_insert('rotation_euler', frame=f)
        cl = Vector((lerp(17.0, 13.0, ease(t)), lerp(5.0, 7.2, ease(t)), lerp(0.1, 0.5, t))); ca = Vector((lerp(9.0, 6.5, ease(t)), 0.6, 0.1))
        look(cl, ca, f)
        cd.dof.focus_distance = (ca - cl).length*0.98
        cd.keyframe_insert('dof.focus_distance', frame=f)
elif SHOT == 'h2':
    dur = 4.5; cd.lens = 42
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 2.8
    nf = int(dur*24)
    fx = jet.XN - 0.80*jet.L
    for f in range(1, nf + 1):
        t = (f - 1)/(nf - 1)
        sl.location = (lerp(fx + 6, fx - 7, t), 3.0, 5.2)
        sl.rotation_euler = (math.radians(-20), 0, 0)
        sl.keyframe_insert('location', frame=f); sl.keyframe_insert('rotation_euler', frame=f)
        cl = Vector((lerp(fx + 2.0, fx + 1.0, ease(t)), 7.5, lerp(1.0, 1.6, ease(t)))); ca = Vector((fx - 3.3, 0.2, 3.3))
        look(cl, ca, f, roll=lerp(-4, 2, ease(t)))
        cd.dof.focus_distance = (ca - cl).length
        cd.keyframe_insert('dof.focus_distance', frame=f)
elif SHOT == 'h3':
    dur = 8.0; cd.lens = 24
    nf = int(dur*24)
    # haze inside the hangar for light shafts
    if not os.environ.get('NOVOL'):
        vm = bpy.data.materials.new('haze'); vn = vm.node_tree
        for n in list(vn.nodes):
            if n.bl_idname == 'ShaderNodeBsdfPrincipled': vn.nodes.remove(n)
        pv = vn.nodes.new('ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = float(os.environ.get('DENS', 0.0006))
        pv.inputs['Anisotropy'].default_value = 0.6
        vn.links.new(pv.outputs[0], vn.nodes['Material Output'].inputs['Volume'])
        vbox = box('vol', -31, XD + 30, -HY, HY, G + 0.01, G + HZ, vm)
        sc.cycles.volume_step_rate = 4.0
    for f in range(1, nf + 1):
        t = (f - 1)/24.0
        u = ease((t - 0.6)/5.0)
        dL.location.y = 9.6 + 19.4*u; dR.location.y = -9.6 - 19.4*u
        dL.keyframe_insert('location', frame=f); dR.keyframe_insert('location', frame=f)
        cl = Vector((lerp(-27.0, -23.5, t/dur), 9.0, G + 1.7)); ca = Vector((22, -1.5, G + 5.2))
        look(cl, ca, f)

sc.frame_start, sc.frame_end = 1, nf
outdir = os.path.join(ROOT, 'renders', SHOT)
f0 = int(os.environ.get('F0', 1)); f1 = int(os.environ.get('F1', nf)); step = int(os.environ.get('STEP', 1))
for f in range(f0, f1 + 1, step):
    path = os.path.join(outdir, f'{f:04d}.png')
    if os.path.exists(path) and not os.environ.get('FORCE'): continue
    sc.frame_set(f); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('FRAME', SHOT, f, flush=True)
