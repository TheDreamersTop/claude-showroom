"""Era still-life scenes. Run:
blender -b -P scenes.py -- <era> <shot> <quality: preview|final> <out.png>
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector
import lib
from lib import ASSETS

TEX = lambda n: os.path.join(ASSETS, 'tex', n)
ORANGE = (0.85, 0.30, 0.10)


# ------------------------------------------------------------------ props
def card(name, w, h, tex, loc, rz=0.0, th=0.0006, rough=0.6, coat=0.0, edge=(0.9, 0.88, 0.82)):
    top = lib.plane(name, w, h, loc=(loc[0], loc[1], loc[2] + th + 0.00025), mat=lib.mat_image(name + 'M', TEX(tex), rough=rough, coat=coat))
    top.rotation_euler[2] = rz
    if th > 0:
        b = lib.box(name + '_e', w, h, th, loc=(loc[0], loc[1], loc[2] + th / 2), mat=lib.mat_simple(name + 'E', edge, rough=0.8))
        b.rotation_euler[2] = rz
    return top


def marble(loc, col):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0085, location=(loc[0], loc[1], 0.0085), segments=48, ring_count=24)
    g = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    g.data.materials.append(lib.mat_glass())
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0050, location=(loc[0], loc[1], 0.0085), segments=24, ring_count=12)
    c = bpy.context.active_object
    c.scale = (1.0, 0.25, 1.0)
    c.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
    bpy.ops.object.shade_smooth()
    c.data.materials.append(lib.mat_simple('mcore', col, rough=0.3, sss=0.3))


def straws(n=2, colors=(ORANGE, (0.15, 0.35, 0.7)), spread=0.023):
    out = []
    for k in range(n):
        sgn = 0 if n == 1 else (-1 if k == 0 else 1)
        bx = -sgn * spread if n > 1 else 0.012
        top = Vector((sgn * 0.004 if n > 1 else -0.003, 0.0, 0.200))
        bot = Vector((bx, 0.003 * (1 if k else -1), 0.0075))
        d = (top - bot).normalized()
        s = lib.straw('Straw%d' % k, length=0.235, color=colors[k % len(colors)])
        s.location = bot
        s.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        out.append(s)
    return out


def cap_lying(loc, rz=0.4, tilt=0.18):
    c = lib.crown_cap()
    c.rotation_euler = (math.pi - tilt, 0, rz)
    c.location = (loc[0], loc[1], 0.0064)
    return c


def opener(loc, rz):
    o = lib.box('Opener', 0.105, 0.019, 0.0016, loc=(loc[0], loc[1], 0.0008), mat=lib.mat_simple('steel', (0.75, 0.75, 0.76), rough=0.25, metal=1.0), bevel=0.003)
    o.rotation_euler[2] = rz
    return o


def ring_box(loc, rz):
    velvet = lib.mat_simple('velvet', (0.012, 0.018, 0.07), rough=1.0)
    base = lib.box('RingBase', 0.05, 0.05, 0.028, loc=(loc[0], loc[1], 0.014), mat=velvet, bevel=0.004)
    base.rotation_euler[2] = rz
    lid = lib.box('RingLid', 0.05, 0.016, 0.05, loc=(0, 0, 0), mat=velvet, bevel=0.004)
    lid.parent = base
    lid.location = (0, 0.033, 0.03)
    lid.rotation_euler = (-0.25, 0, 0)
    satin = lib.box('Satin', 0.044, 0.044, 0.002, loc=(0, 0, 0.0142), mat=lib.mat_simple('satin', (0.9, 0.88, 0.85), rough=0.35))
    satin.parent = base
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0095, minor_radius=0.0016, location=(0, 0, 0), major_segments=64, minor_segments=16)
    ring = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    ring.data.materials.append(lib.mat_simple('gold', (1.0, 0.76, 0.33), rough=0.12, metal=1.0))
    ring.parent = base
    ring.location = (0, 0.002, 0.025)
    ring.rotation_euler = (math.pi / 2 - 0.25, 0, 0)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.0028, subdivisions=1, location=(0, 0, 0))
    gem = bpy.context.active_object
    gem.data.materials.append(lib.mat_water())
    gem.parent = base
    gem.location = (0, 0.0045, 0.0365)
    return base


def petals(center, n, radius, seed=3):
    rng = random.Random(seed)
    m = lib.mat_simple('petal', (0.62, 0.03, 0.07), rough=0.45, sss=0.4)
    for i in range(n):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012, segments=20, ring_count=10)
        p = bpy.context.active_object
        a = rng.uniform(0, math.tau); r = rng.uniform(0.3, 1) * radius
        p.location = (center[0] + r * math.cos(a), center[1] + r * math.sin(a), 0.0015)
        p.scale = (rng.uniform(0.8, 1.2), rng.uniform(0.6, 0.9), 0.09)
        p.rotation_euler = (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0, 6.3))
        bpy.ops.object.shade_smooth()
        p.data.materials.append(m)


def baby_bottle(loc):
    plastic = lib.mat_simple('plastic', (0.95, 0.95, 0.97), rough=0.25)
    p = plastic.node_tree.nodes['Principled BSDF']
    p.inputs['Transmission Weight'].default_value = 0.15
    p.inputs['IOR'].default_value = 1.45
    p.inputs['Roughness'].default_value = 0.4
    prof = lib.smooth_profile([(0.0, 0.0), (0.024, 0.0), (0.026, 0.004), (0.026, 0.13), (0.024, 0.136)], 4)
    plastic.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.97, 0.97, 0.99, 1)
    inner = [(r - 0.0015, z) for r, z in reversed(prof) if z > 0.002][:-1]
    body = lib.revolve('BabyBottle', prof + [(0.0225, 0.136)] + inner + [(0.0, 0.002)])
    body.data.materials.append(plastic)
    body.location = (loc[0], loc[1], 0)
    milk = lib.revolve('Milk', [(0.0, 0.0022), (0.0238, 0.0022), (0.0238, 0.075), (0.0, 0.0752)])
    milk.data.materials.append(lib.mat_simple('milk', (1.0, 0.98, 0.93), rough=0.3, sss=0.1))
    milk.parent = body
    collar = lib.revolve('Collar', [(0.0, 0.150), (0.0215, 0.150), (0.0270, 0.146), (0.0270, 0.131), (0.0255, 0.129), (0.0, 0.129)])
    collar.data.materials.append(lib.mat_simple('collar', (0.55, 0.78, 0.95), rough=0.35))
    collar.parent = body
    nip = lib.revolve('Nipple', lib.smooth_profile([(0.0185, 0.150), (0.016, 0.158), (0.0085, 0.168), (0.0055, 0.178), (0.0058, 0.188), (0.0035, 0.196), (0.0, 0.197)], 4))
    nip.data.materials.append(lib.mat_simple('rubber', (0.86, 0.66, 0.38), rough=0.3, sss=0.5))
    nip.parent = body
    return body


def rattle(loc, rz):
    m1 = lib.mat_simple('rat1', (0.95, 0.62, 0.70), rough=0.3, coat=0.5)
    m2 = lib.mat_simple('rat2', (0.98, 0.90, 0.55), rough=0.3, coat=0.5)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=(loc[0], loc[1], 0.022))
    s = bpy.context.active_object; bpy.ops.object.shade_smooth(); s.data.materials.append(m1)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0065, depth=0.075, location=(loc[0] + 0.05 * math.cos(rz), loc[1] + 0.05 * math.sin(rz), 0.009), rotation=(0, math.pi / 2, rz))
    h = bpy.context.active_object; bpy.ops.object.shade_smooth(); h.data.materials.append(m2)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.012, minor_radius=0.004, location=(loc[0] + 0.095 * math.cos(rz), loc[1] + 0.095 * math.sin(rz), 0.004))
    t = bpy.context.active_object; bpy.ops.object.shade_smooth(); t.data.materials.append(m1)


def pill_box(loc, rz):
    base = lib.box('PillBase', 0.21, 0.038, 0.018, loc=(loc[0], loc[1], 0.009), mat=lib.mat_simple('pillbase', (0.96, 0.96, 0.97), rough=0.3, coat=0.3), bevel=0.002)
    base.rotation_euler[2] = rz
    lid = lib.plane('PillLid', 0.208, 0.036, loc=(0, 0, 0.0092), mat=lib.mat_image('pilllid', TEX('pills.png'), rough=0.25, coat=0.6))
    lid.parent = base
    lid.location = (0, 0, 0.0092)
    return base


def curve_obj(name, pts, bevel, mat, closed=False, res=12):
    cd = bpy.data.curves.new(name, 'CURVE')
    cd.dimensions = '3D'
    cd.bevel_depth = bevel
    cd.bevel_resolution = 4
    cd.resolution_u = res
    sp = cd.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_cyclic_u = closed
    sp.use_endpoint_u = not closed
    sp.order_u = 4
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def glasses(name, loc, rz, frame_mat, thick=0.0016):
    """folded reading glasses lying on the table, lenses up-ish. local frame: x across, y depth, z up."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    lw, lh = 0.024, 0.016
    for sx in (-1, 1):
        cx = sx * 0.0285
        pts = [(cx + lw * math.cos(a), 0, 0.017 + lh * math.sin(a)) for a in [i / 16 * math.tau for i in range(16)]]
        rim = curve_obj(name + 'rim', pts, thick, frame_mat, closed=True)
        rim.parent = root
        # lens
        bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=0.0018, vertices=48, location=(cx, 0, 0.017), rotation=(math.pi / 2, 0, 0))
        L = bpy.context.active_object
        L.scale = (lw * 0.98, lh * 0.98, 1)
        L.data.materials.append(lib.mat_glass())
        L.parent = root
        # folded temple: runs behind the lens toward the centre
        ex = sx * 0.0285 + sx * lw
        tp = [(ex, 0, 0.021), (ex, 0.006, 0.021), (ex - sx * 0.02, 0.009, 0.019), (ex - sx * 0.07, 0.009, 0.014), (ex - sx * 0.10, 0.007, 0.006)]
        t = curve_obj(name + 'tmp', tp, thick * 0.8, frame_mat)
        t.parent = root
    br = curve_obj(name + 'br', [(-0.0055, 0, 0.026), (-0.002, 0, 0.030), (0.002, 0, 0.030), (0.0055, 0, 0.026)], thick * 0.9, frame_mat)
    br.parent = root
    root.location = (loc[0], loc[1], 0.0)
    root.rotation_euler = (0, 0, rz)
    return root


def hearing_aid(loc, rz):
    m = lib.mat_simple('aid', (0.80, 0.66, 0.52), rough=0.35, coat=0.4)
    pts = [(-0.014, 0, 0.004), (-0.008, 0.006, 0.0045), (0.004, 0.007, 0.0045), (0.012, 0.002, 0.004), (0.014, -0.004, 0.004)]
    body = curve_obj('aid', pts, 0.0042, m)
    body.location = (loc[0], loc[1], 0)
    body.rotation_euler[2] = rz
    tube = curve_obj('aidtube', [(-0.014, 0, 0.004), (-0.022, -0.004, 0.0015), (-0.030, -0.012, 0.0012), (-0.034, -0.022, 0.0012)], 0.0007, lib.mat_glass())
    tube.parent = body
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0030, location=(-0.034, -0.023, 0.003))
    dome = bpy.context.active_object
    dome.scale = (1, 1, 0.8)
    bpy.ops.object.shade_smooth()
    dome.data.materials.append(lib.mat_simple('dome', (0.9, 0.9, 0.92), rough=0.3))
    dome.parent = body
    return body


def pencil(loc, rz):
    y = lib.mat_simple('pencilY', (0.95, 0.68, 0.10), rough=0.4, coat=0.5)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0036, depth=0.13, vertices=6, location=(loc[0], loc[1], 0.0036), rotation=(0, math.pi / 2, rz))
    p = bpy.context.active_object
    p.data.materials.append(y)
    bpy.ops.mesh.primitive_cone_add(radius1=0.0036, depth=0.016, vertices=6, location=(0.073, 0, 0), rotation=(0, math.pi / 2, 0))
    c = bpy.context.active_object
    c.data.materials.append(lib.mat_simple('wood', (0.85, 0.68, 0.48), rough=0.6))
    c.parent = p
    c.location = (0, 0, 0.073)
    c.rotation_euler = (0, 0, 0)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0037, depth=0.012, location=(0, 0, -0.071))
    e = bpy.context.active_object
    e.data.materials.append(lib.mat_simple('eraser', (0.92, 0.50, 0.52), rough=0.7))
    e.parent = p
    e.location = (0, 0, -0.071)


def doily(r=0.11):
    m = lib.mat_image('doilyM', TEX('doily.png'), rough=0.8, alpha=True)
    m.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.2
    return lib.plane('Doily', 2 * r, 2 * r, loc=(0, 0, 0.0004), mat=m)


def tabletop(tex, size=(7.0, 7.0), rough=0.4, coat=0.0, scale=1.0, rz=0.0, color_mul=None):
    m = lib.mat_image('table', TEX(tex), rough=rough, coat=coat)
    nt = m.node_tree
    texn = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    mp.inputs['Rotation'].default_value[2] = rz
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], texn.inputs['Vector'])
    t = lib.plane('Table', size[0], size[1], mat=m)
    return t


# ------------------------------------------------------------------ cameras
def cam_main(fstop=2.2):
    return lib.camera((0.0, -0.86, 0.19), (0.0, 0.02, 0.112), lens=52, fstop=fstop, focus=0.86)


def finish(quality):
    sc = bpy.context.scene
    sc.cycles.caustics_refractive = False
    sc.cycles.max_bounces = 12
    sc.cycles.transmission_bounces = 10
    sc.cycles.glossy_bounces = 4
    sc.cycles.diffuse_bounces = 3
    sc.cycles.adaptive_threshold = 0.02
    if quality == 'preview':
        sc.cycles.samples = 16
        sc.render.resolution_x, sc.render.resolution_y = 768, 432
    elif quality == 'mid':
        sc.cycles.samples = 32
        sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    else:  # final: headroom for a slow push in post
        sc.cycles.samples = 40
        sc.render.resolution_x, sc.render.resolution_y = 2112, 1188


# ------------------------------------------------------------------ eras
def era_1958(shot):
    lib.world_hdri('veranda_4k.hdr', strength=0.9, rot_z=2.2, bg_strength=1.0)
    tabletop('planks.png', rough=0.7, scale=0.9, rz=math.pi / 2)
    b = lib.bottle(droplets=420, seed=4)
    straws(1, colors=((0.80, 0.12, 0.10),))
    cap_lying((0.075, -0.075), rz=0.6)
    opener((0.12, -0.02), rz=-0.5)
    card('Comic', 0.17, 0.255, 'comic.png', (-0.16, 0.0, 0.0), rz=0.32, th=0.003, rough=0.75)
    random.seed(5)
    for (x, y), c in zip([(-0.07, -0.13), (-0.035, -0.17), (0.165, -0.13)], [(0.1, 0.35, 0.8), (0.9, 0.3, 0.1), (0.1, 0.6, 0.3)]):
        marble((x, y), c)
    lib.light_sun((math.radians(62), 0, math.radians(150)), energy=4.5, color=(1.0, 0.86, 0.66), angle=0.01)
    if shot == 'main':
        cam_main()
    elif shot == 'detail':
        lib.camera((-0.02, -0.30, 0.22), (-0.13, -0.04, 0.0), lens=42, fstop=3.5)


def era_1966(shot):
    lib.world_hdri('comfy_cafe_4k.hdr', strength=0.7, rot_z=0.6 if shot == 'main' else 2.4, bg_strength=0.9 if shot == 'main' else 0.32)
    t = tabletop('formica.png', rough=0.25, coat=0.6, scale=1.4)
    # chrome edge band in front
    lib.box('Chrome', 2.4, 0.02, 0.03, loc=(0, -0.38, -0.014), mat=lib.mat_simple('chrome', (0.9, 0.9, 0.9), rough=0.08, metal=1.0))
    lib.bottle(droplets=0)
    straws(2, colors=((0.85, 0.30, 0.10), (0.85, 0.30, 0.10)))
    cap_lying((-0.08, -0.07), rz=1.9)
    card('T1', 0.09, 0.04, 'ticket1.png', (0.115, -0.08, 0.0), rz=0.35, th=0.0004)
    card('T2', 0.09, 0.04, 'ticket2.png', (0.145, -0.05, 0.0008), rz=0.05, th=0.0004)
    # napkin dispenser, chrome
    lib.box('Napkins', 0.11, 0.07, 0.13, loc=(-0.24, 0.20, 0.065), mat=lib.mat_simple('chrome2', (0.9, 0.9, 0.9), rough=0.12, metal=1.0), bevel=0.01)
    lib.box('Napkin', 0.09, 0.075, 0.10, loc=(-0.24, 0.20, 0.07), mat=lib.mat_simple('paper', (0.95, 0.95, 0.93), rough=0.9))
    lib.light_area((0.45, 0.45, 0.35), (0, 0, 0.1), size=0.25, energy=22, color=(1.0, 0.35, 0.55))   # pink neon rim
    lib.light_area((-0.55, 0.25, 0.30), (0, 0, 0.1), size=0.25, energy=14, color=(0.35, 0.85, 1.0))   # teal rim
    lib.light_area((-0.3, -0.6, 0.7), (0, 0, 0.05), size=0.8, energy=30, color=(1.0, 0.9, 0.75))       # key
    if shot == 'main':
        cam_main()
    if shot == 'detail':   # warm diner neon glow behind the straws
        rr = random.Random(66)
        for i in range(14):
            em = bpy.data.materials.new('neon%d' % i)
            em.use_nodes = True
            nt = em.node_tree
            nt.nodes.clear()
            e = nt.nodes.new('ShaderNodeEmission')
            e.inputs['Color'].default_value = (*rr.choice([(1.0, 0.25, 0.45), (1.0, 0.55, 0.15), (0.2, 0.85, 0.9), (1.0, 0.8, 0.4)]), 1)
            e.inputs['Strength'].default_value = rr.uniform(6, 14)
            o = nt.nodes.new('ShaderNodeOutputMaterial')
            nt.links.new(e.outputs[0], o.inputs[0])
            bpy.ops.mesh.primitive_uv_sphere_add(radius=rr.uniform(0.012, 0.03), location=(rr.uniform(-0.55, 0.55), rr.uniform(1.3, 2.2), rr.uniform(0.12, 0.55)))
            bpy.context.active_object.data.materials.append(em)
        lib.light_area((0.25, 0.9, 0.35), (0, 0, 0.2), size=0.5, energy=30, color=(1.0, 0.35, 0.45))
        lib.light_area((-0.35, 0.9, 0.25), (0, 0, 0.2), size=0.4, energy=18, color=(1.0, 0.65, 0.25))
    if False:
        pass
    elif shot == 'detail':  # low angle up the two straws
        lib.camera((0.06, -0.40, 0.235), (0.0, 0.0, 0.215), lens=100, fstop=2.0)


def era_1974(shot):
    lib.world_hdri('warm_reception_dinner_4k.hdr', strength=0.8, rot_z=3.6, bg_strength=1.0)
    tabletop('linen.png', rough=0.85, scale=3.0)
    b1 = lib.bottle(name='B1', droplets=0)
    b1.location = (-0.035, 0.0, 0)
    b2 = lib.bottle(name='B2', droplets=0)
    b2.location = (0.035, 0.015, 0)
    b2.rotation_euler[2] = 0.15
    cap_lying((0.06, -0.10), rz=0.3)
    cap_lying((-0.09, -0.12), rz=2.0, tilt=-0.1)
    ring_box((0.14, -0.07), rz=-0.35)
    card('JM', 0.12, 0.077, 'justmarried.png', (-0.15, -0.08, 0), rz=0.18, th=0.001)
    petals((0.0, -0.06), 14, 0.2)
    lib.light_area((-0.4, -0.5, 0.6), (0, 0, 0.08), size=0.7, energy=28, color=(1.0, 0.86, 0.68))
    lib.light_area((0.3, 0.6, 0.3), (0, 0, 0.12), size=0.4, energy=18, color=(1.0, 0.75, 0.5))
    if shot == 'main':
        cam_main()
    elif shot == 'detail':
        lib.camera((0.26, -0.32, 0.10), (0.14, -0.07, 0.03), lens=90, fstop=2.0)


def era_1987(shot):
    lib.world_hdri('old_room_4k.hdr', strength=0.25, rot_z=1.0, bg_strength=0.35)
    tabletop('gingham.png', rough=0.8, scale=2.2, rz=0.08)
    lib.bottle(droplets=0)
    cap_lying((0.07, -0.09), rz=2.4)
    baby_bottle((0.105, 0.04))
    rattle((-0.13, -0.10), rz=0.5)
    card('Polaroid', 0.088, 0.106, 'footprints.png' if shot == 'detail' else 'polaroid.png', (-0.14, 0.04, 0), rz=-0.25, th=0.0008)
    lib.light_point((0.0, 0.05, 0.62), energy=9, color=(1.0, 0.72, 0.42), radius=0.06)   # pendant lamp
    lib.light_area((0.0, 0.9, 0.5), (0, 0, 0.1), size=0.8, energy=12, color=(0.45, 0.6, 1.0))  # moonlight from window
    if shot == 'main':
        cam_main()
    elif shot == 'detail':
        lib.camera((-0.06, -0.30, 0.16), (-0.14, 0.02, 0.0), lens=80, fstop=4.0)


def era_2026(shot):
    lib.world_hdri('lythwood_lounge_4k.hdr', strength=0.6, rot_z=4.4, bg_strength=0.85)
    tabletop('walnut.png', rough=0.3, coat=0.5, scale=1.6)
    doily(0.10)
    lib.bottle(droplets=0)
    straws(2, colors=((0.85, 0.30, 0.10), (0.85, 0.30, 0.10)))
    pill_box((0.0, -0.17), rz=0.05)
    hearing_aid((0.17, -0.06), rz=0.8)
    glasses('G1', (-0.15, -0.05), 0.35, lib.mat_simple('tort', (0.22, 0.09, 0.03), rough=0.25, coat=0.8), thick=0.0019)
    glasses('G2', (-0.115, 0.07), -0.25, lib.mat_simple('wire', (0.95, 0.75, 0.40), rough=0.18, metal=1.0), thick=0.0009)
    card('Paper', 0.24, 0.18, 'crossword.png', (0.15, 0.14, 0), rz=-0.22, th=0.0012, rough=0.85)
    pencil((0.10, 0.06), rz=2.6)
    cap_lying((0.075, -0.075), rz=0.9)
    # low golden sun through blinds
    lib.light_sun((math.radians(74), 0, math.radians(215)), energy=3.4, color=(1.0, 0.72, 0.45), angle=0.015)
    for i in range(14):
        sl = lib.box('slat%d' % i, 2.0, 0.02, 0.004, loc=(0.0, 0.0, 0.0), mat=lib.mat_simple('slat', (0.9, 0.85, 0.8), rough=0.6))
        sl.location = Vector((-0.50, 0.72, 0.06 + i * 0.034))
        sl.rotation_euler = (0.0, 0.35, math.radians(35))
        sl.visible_camera = False
        sl.visible_glossy = False
        sl.visible_transmission = False
    lib.light_area((-0.5, -0.6, 0.5), (0, 0, 0.08), size=0.8, energy=10, color=(0.9, 0.92, 1.0))
    if shot == 'main':
        cam_main()
    elif shot == 'detail':  # the two pairs of glasses
        lib.camera((-0.22, -0.31, 0.19), (-0.135, 0.01, 0.012), lens=62, fstop=5.6)
    elif shot == 'straws':
        lib.camera((0.06, -0.40, 0.235), (0.0, 0.0, 0.215), lens=100, fstop=2.0)


def era_hero(shot):
    lib.world_hdri('studio_small_09_4k.hdr', strength=0.10, rot_z=0.0, bg_strength=0.0)
    m = lib.mat_simple('sweep', (0.03, 0.016, 0.011), rough=0.55, coat=0.0)
    lib.plane('Floor', 7, 7, mat=m)
    lib.box('Back', 7, 0.1, 3, loc=(0, 3.0, 1.5), mat=lib.mat_simple('back', (0.03, 0.015, 0.01), rough=0.9))
    b = lib.bottle(droplets=900, seed=8)
    if shot == 'pack2':   # opened, with the couple's two straws
        straws(2, colors=((0.85, 0.30, 0.10), (0.85, 0.30, 0.10)))
        cap_lying((0.07, -0.06), rz=0.7)
    else:
        c = lib.crown_cap(); c.location = (0, 0, 0.2068)
    lib.light_area((-0.35, 0.25, 0.15), (0, 0, 0.11), size=0.06, size_y=0.6, energy=40, color=(1.0, 0.75, 0.5))
    lib.light_area((0.35, 0.25, 0.15), (0, 0, 0.11), size=0.06, size_y=0.6, energy=40, color=(1.0, 0.75, 0.5))
    lib.light_area((0.0, 0.5, 0.06), (0, 0, 0.06), size=0.5, size_y=0.10, energy=2.0, color=(1.0, 0.62, 0.32))  # backlight glow, kept below the neck line
    lib.light_area((-0.3, -0.6, 0.35), (0, 0, 0.1), size=0.5, energy=9, color=(1.0, 0.92, 0.85))
    if shot == 'main':
        lib.camera((0.0, -0.66, 0.10), (0.0, 0.0, 0.112), lens=60, fstop=3.2)
    elif shot == 'pack':
        lib.camera((-0.13, -0.74, 0.10), (-0.13, 0.0, 0.098), lens=55, fstop=4.0)
    elif shot == 'pack2':
        lib.camera((-0.08, -0.85, 0.12), (-0.08, 0.0, 0.12), lens=62, fstop=4.0)
    elif shot == 'macro':
        lib.camera((0.0, -0.30, 0.205), (0.0, 0.0, 0.198), lens=70, fstop=2.8)


ERAS = {'hero': era_hero, '1958': era_1958, '1966': era_1966, '1974': era_1974, '1987': era_1987, '2026': era_2026}

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    era, shot, quality, out = argv
    lib.reset()
    random.seed(1)
    ERAS[era](shot)
    finish(quality)
    import time
    t = time.time()
    lib.render(out)
    print('RENDER_SECONDS', era, shot, round(time.time() - t, 1))
