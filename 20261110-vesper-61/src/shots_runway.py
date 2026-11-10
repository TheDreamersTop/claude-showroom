"""Runway takeoff at sunset, runway ends at the sea. usage: SHOT=r1 python shots_runway.py"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import jet, env, bpy
from jet import _n, math_node
from mathutils import Vector, Euler

SHOT = os.environ.get('SHOT', 'r1')
def lerp(a, b, t): return a + (b - a)*t
def ease(t): t = min(1, max(0, t)); return t*t*(3 - 2*t)

sc = reset()
sc.cycles.samples = int(os.environ.get('SPP', 40))
sc.render.resolution_percentage = int(os.environ.get('PCT', 100))
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
ELEV, ROT = 1.0, 90.0
w, skies = env.sunset_world(ELEV, ROT, altitude=200, dust=2.5)
lamp = env.add_sun_lamp(3.0, ROT, 55, (1.0, 0.42, 0.15), angle=1.0)
root, gear = jet.build_jet(os.path.join(TEX, 'side.png'), os.path.join(TEX, 'fin.png'), gear=True)
G = root['ground_offset']

def haze(nt, shader_out, start=300.0, dist=6000.0):
    """mix a surface shader toward the horizon sky colour by camera distance"""
    L = nt.links
    geo = _n(nt, 'ShaderNodeNewGeometry'); dv = _n(nt, 'ShaderNodeVectorMath'); dv.operation = 'SCALE'; dv.inputs['Scale'].default_value = -1
    L.new(geo.outputs['Incoming'], dv.inputs[0])
    sp = _n(nt, 'ShaderNodeSeparateXYZ'); L.new(dv.outputs[0], sp.inputs[0])
    cb = _n(nt, 'ShaderNodeCombineXYZ'); L.new(sp.outputs[0], cb.inputs[0]); L.new(sp.outputs[1], cb.inputs[1]); cb.inputs[2].default_value = 0.01
    sk = _n(nt, 'ShaderNodeTexSky')
    for a in ('sky_type', 'sun_elevation', 'sun_rotation', 'altitude', 'aerosol_density', 'air_density', 'ozone_density'):
        setattr(sk, a, getattr(skies[1], a))
    sk.sun_disc = False; L.new(cb.outputs[0], sk.inputs['Vector'])
    em = _n(nt, 'ShaderNodeEmission'); L.new(sk.outputs[0], em.inputs['Color'])
    cd = _n(nt, 'ShaderNodeCameraData')
    dd = math_node(nt, 'MAXIMUM', math_node(nt, 'SUBTRACT', cd.outputs['View Distance'], start), 0.0)
    hz = math_node(nt, 'SUBTRACT', 1.0, math_node(nt, 'EXPONENT', math_node(nt, 'DIVIDE', dd, -dist)))
    mx = _n(nt, 'ShaderNodeMixShader'); L.new(hz, mx.inputs[0]); L.new(shader_out, mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
    return mx.outputs[0]

# ground: runway + grass, with markings
gm = bpy.data.materials.new('ground'); nt = gm.node_tree; L = nt.links
b = nt.nodes['Principled BSDF']; out = nt.nodes['Material Output']
tc = _n(nt, 'ShaderNodeTexCoord'); sep = _n(nt, 'ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
x, y = sep.outputs[0], sep.outputs[1]
ay = math_node(nt, 'ABSOLUTE', y)
onrw = math_node(nt, 'LESS_THAN', ay, 23.0)
centre = math_node(nt, 'MULTIPLY', math_node(nt, 'LESS_THAN', ay, 0.45), math_node(nt, 'LESS_THAN', math_node(nt, 'FRACT', math_node(nt, 'DIVIDE', x, 50.0)), 0.6))
edge = math_node(nt, 'MULTIPLY', math_node(nt, 'GREATER_THAN', ay, 21.5), math_node(nt, 'LESS_THAN', ay, 22.4))
paint = math_node(nt, 'MAXIMUM', centre, edge)
nz = _n(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.08; nz.inputs['Detail'].default_value = 8
L.new(tc.outputs['Object'], nz.inputs['Vector'])
c1 = _n(nt, 'ShaderNodeMix'); c1.data_type = 'RGBA'; L.new(onrw, c1.inputs['Factor'])
grass = _n(nt, 'ShaderNodeMix'); grass.data_type = 'RGBA'; L.new(nz.outputs['Fac'], grass.inputs['Factor'])
grass.inputs[6].default_value = (0.03, 0.035, 0.015, 1); grass.inputs[7].default_value = (0.06, 0.055, 0.025, 1)
L.new(grass.outputs[2], c1.inputs[6]); c1.inputs[7].default_value = (0.035, 0.035, 0.037, 1)
c2 = _n(nt, 'ShaderNodeMix'); c2.data_type = 'RGBA'; L.new(paint, c2.inputs['Factor']); L.new(c1.outputs[2], c2.inputs[6]); c2.inputs[7].default_value = (0.7, 0.7, 0.68, 1)
L.new(c2.outputs[2], b.inputs['Base Color'])
L.new(math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', onrw, -0.35), 0.85), b.inputs['Roughness'])
L.new(haze(nt, b.outputs[0], 1500, 14000), out.inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=1, location=(-500, 0, G)); grd = bpy.context.active_object
grd.scale = (5000, 8000, 1); grd.data.materials.append(gm)   # x from -3000 to 2000
# sea beyond the runway end
sm = bpy.data.materials.new('sea'); nt = sm.node_tree; L = nt.links
b = nt.nodes['Principled BSDF']; out = nt.nodes['Material Output']
b.inputs['Base Color'].default_value = (0.01, 0.015, 0.02, 1); b.inputs['Roughness'].default_value = 0.06
wv = _n(nt, 'ShaderNodeTexNoise'); wv.inputs['Scale'].default_value = 0.05; wv.inputs['Detail'].default_value = 10
tc = _n(nt, 'ShaderNodeTexCoord'); mp = _n(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 4, 1)
L.new(tc.outputs['Object'], mp.inputs[0]); L.new(mp.outputs[0], wv.inputs['Vector'])
bm = _n(nt, 'ShaderNodeBump'); bm.inputs['Strength'].default_value = 0.25; L.new(wv.outputs['Fac'], bm.inputs['Height']); L.new(bm.outputs[0], b.inputs['Normal'])
L.new(haze(nt, b.outputs[0], 1500, 30000), out.inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=1, location=(2000 + 200000, 0, G - 6)); sea = bpy.context.active_object
sea.scale = (400000, 800000, 1); sea.data.materials.append(sm)

# runway edge lights
lm = bpy.data.materials.new('rwlight'); ln = lm.node_tree
for n in list(ln.nodes):
    if n.bl_idname == 'ShaderNodeBsdfPrincipled': ln.nodes.remove(n)
e = ln.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (1.0, 0.8, 0.55, 1); e.inputs['Strength'].default_value = 60
ln.links.new(e.outputs[0], ln.nodes['Material Output'].inputs['Surface'])
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, segments=12, ring_count=6, location=(0, 0, G + 0.3)); proto = bpy.context.active_object
proto.data.materials.append(lm)
for i in range(-50, 34):
    for sy in (-24, 24):
        o = proto.copy(); o.location = (i*60.0, sy, G + 0.3); sc.collection.objects.link(o)

cd = bpy.data.cameras.new('cam'); cd.sensor_width = 36; cd.clip_start = 0.1; cd.clip_end = 900000; cd.lens = 40
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
dur = 6.5; nf = int(dur*24)
CAMP = Vector((50.0, -36.0, G + 0.9))
for f in range(1, nf + 1):
    t = (f - 1)/24.0
    v0, a = 68.0, 3.0
    xj = -130 + v0*t + 0.5*a*t*t
    rot = ease((t - 1.9)/1.4)                    # rotation
    climb = max(0.0, t - 2.8)
    zj = 0.0 + 2.0*climb**2 + 4.0*climb
    pitch = math.radians(9.0*rot)
    root.location = (xj, 0, zj); root.rotation_euler = (0, -pitch, 0)
    root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)
    for g in gear:
        g.hide_render = False
    aim = Vector((xj + 6 + 20*ease((t - 2.5)/3.0), 0, zj*0.8 + 1.0))
    cam.location = CAMP + Vector((0, 0, 0.0))
    cam.rotation_euler = (aim - CAMP).to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)

sc.frame_start, sc.frame_end = 1, nf
outdir = os.path.join(ROOT, 'renders', SHOT)
f0 = int(os.environ.get('F0', 1)); f1 = int(os.environ.get('F1', nf)); step = int(os.environ.get('STEP', 1))
for f in range(f0, f1 + 1, step):
    path = os.path.join(outdir, f'{f:04d}.png')
    if os.path.exists(path) and not os.environ.get('FORCE'): continue
    sc.frame_set(f); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('FRAME', SHOT, f, flush=True)
