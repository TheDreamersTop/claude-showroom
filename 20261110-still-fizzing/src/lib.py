"""Shared Blender helpers: bottle, cap, straws, materials, world, camera, render settings."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ASSETS = os.path.join(ROOT, 'assets')


# ---------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 16
    sc.cycles.transmission_bounces = 16
    sc.cycles.glossy_bounces = 8
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = True
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.fps = 24
    return sc


def world_hdri(name, strength=1.0, rot_z=0.0, bg_strength=None, blur=0.0):
    w = bpy.data.worlds.new('W')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(os.path.join(ASSETS, 'hdri', name))
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value[2] = rot_z
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    if bg_strength is None:
        nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    else:  # separate camera-ray strength, from a pre-blurred copy of the HDRI
        bg2 = nt.nodes.new('ShaderNodeBackground')
        bg2.inputs['Strength'].default_value = bg_strength
        env2 = nt.nodes.new('ShaderNodeTexEnvironment')
        bp = os.path.join(ASSETS, 'hdri', name.replace('.hdr', '_blur.hdr'))
        env2.image = bpy.data.images.load(bp if os.path.exists(bp) else os.path.join(ASSETS, 'hdri', name))
        nt.links.new(mp.outputs['Vector'], env2.inputs['Vector'])
        nt.links.new(env2.outputs['Color'], bg2.inputs['Color'])
        lp = nt.nodes.new('ShaderNodeLightPath')
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
        nt.links.new(bg.outputs['Background'], mix.inputs[1])
        nt.links.new(bg2.outputs['Background'], mix.inputs[2])
        nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return w


def camera(loc, target, lens=70, fstop=2.0, focus=None, name='Cam'):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.dof.focus_distance = focus if focus else d.length
    bpy.context.scene.camera = cam
    return cam


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def light_area(loc, target, size=1.0, energy=100, color=(1, 1, 1), shape='SQUARE', size_y=None):
    ld = bpy.data.lights.new('A', 'AREA')
    ld.energy = energy
    ld.color = color
    ld.shape = 'RECTANGLE' if size_y else shape
    ld.size = size
    if size_y:
        ld.size_y = size_y
    o = bpy.data.objects.new('A', ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    return o


def light_sun(rot, energy=3.0, color=(1, 0.95, 0.85), angle=0.02):
    ld = bpy.data.lights.new('S', 'SUN')
    ld.energy = energy
    ld.color = color
    ld.angle = angle
    o = bpy.data.objects.new('S', ld)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = rot
    return o


def light_point(loc, energy=10, color=(1, 0.8, 0.6), radius=0.05):
    ld = bpy.data.lights.new('P', 'POINT')
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    o = bpy.data.objects.new('P', ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


# ---------------------------------------------------------------- mesh helpers
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def revolve(name, prof, segs=96, smooth=True):
    """prof: list of (r, z). Revolved around Z. r==0 points become single pole vertices."""
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        if r <= 1e-7:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for i in range(segs):
                bm.faces.new((a[0], b[i], b[(i + 1) % segs]))
        elif len(b) == 1:
            for i in range(segs):
                bm.faces.new((a[i], b[0], a[(i + 1) % segs]))
        else:
            for i in range(segs):
                bm.faces.new((a[i], b[i], b[(i + 1) % segs], a[(i + 1) % segs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return link(bpy.data.objects.new(name, me))


def smooth_profile(pts, n=6):
    """Catmull-Rom subdivide a (r,z) polyline for a smooth lathe profile."""
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(pts[-1])
    return out


# outer profile of the Larkin's bottle (metres). 20.5 cm tall, 6 cm wide.
OUTER = [(0.0262, 0.0), (0.0290, 0.0025), (0.0300, 0.008), (0.0300, 0.060), (0.0300, 0.112),
         (0.0292, 0.124), (0.0262, 0.138), (0.0205, 0.153), (0.0150, 0.166), (0.0128, 0.178),
         (0.0124, 0.192), (0.0127, 0.199), (0.0146, 0.2015), (0.0148, 0.2045), (0.0138, 0.2068), (0.0105, 0.2072)]


def outer_r(z):
    """radius of outer profile at height z (linear interp)."""
    for (r0, z0), (r1, z1) in zip(OUTER[:-1], OUTER[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / max(z1 - z0, 1e-9)
    return OUTER[-1][0]


def bottle(name='Bottle', fill=0.180, with_label=True, droplets=0, seed=1, empty=False):
    outer = smooth_profile(OUTER[:-2], 6) + OUTER[-2:]
    t = 0.0024
    inner = []
    for r, z in reversed(outer):
        if z < 0.006:
            continue
        inner.append((max(r - t, 0.0005), z))
    # mouth: top inner radius
    inner[0] = (0.0094, 0.2072)
    prof = [(0.0, 0.0)] + outer[:] + inner + [(0.0, 0.0062)]
    # remove last OUTER point that duplicated mouth
    glass = revolve(name, prof)
    glass.data.materials.append(mat_glass())
    parts = [glass]
    if not empty and fill > 0:
        li = [(0.0, 0.0064)]
        for r, z in outer:
            zz = z
            if zz < 0.0064:
                continue
            if zz > fill:
                break
            li.append((max(r - t - 0.00015, 0.0004), zz))
        rr = max(outer_r(fill) - t - 0.00015, 0.0004)
        li.append((rr, fill))
        li.append((rr * 0.97, fill + 0.0006))  # meniscus
        li.append((0.0, fill + 0.0004))
        liq = revolve(name + '_Cola', li)
        liq.data.materials.append(mat_cola())
        liq.parent = glass
        parts.append(liq)
    if with_label:
        lab = label_band(name + '_Label')
        lab.parent = glass
        parts.append(lab)
    if droplets:
        add_droplets(glass, droplets, seed)
    return glass


def label_band(name, z0=0.034, z1=0.098, r=0.03018, segs=128):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    ring0 = [bm.verts.new((r * math.cos(2 * math.pi * i / segs - math.pi / 2), r * math.sin(2 * math.pi * i / segs - math.pi / 2), z0)) for i in range(segs + 1)]
    ring1 = [bm.verts.new((r * math.cos(2 * math.pi * i / segs - math.pi / 2), r * math.sin(2 * math.pi * i / segs - math.pi / 2), z1)) for i in range(segs + 1)]
    for i in range(segs):
        f = bm.faces.new((ring0[i], ring0[i + 1], ring1[i + 1], ring1[i]))
        # u: 0.5 faces -Y (camera). vertex angle a = 2pi*i/segs - pi/2 ; at i = 0 the vertex is at -Y. shift so -Y -> 0.5
        u0 = i / segs + 0.5
        u1 = u0 + 1.0 / segs
        us = [u0, u1, u1, u0]
        for loop, u, v in zip(f.loops, us, (0, 0, 1, 1)):
            loop[uv].uv = (u, v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = link(bpy.data.objects.new(name, me))
    o.data.materials.append(mat_label())
    o.visible_shadow = False
    return o


def add_droplets(glass, count, seed):
    # emitter skin, not rendered
    em = revolve(glass.name + '_skin', [(0.0302, 0.010), (0.0302, 0.118), (0.0296, 0.124), (0.0266, 0.137)], segs=64)
    em.parent = glass
    em.hide_render = True
    em.visible_camera = False
    drop = revolve('Drop', smooth_profile([(0.0, -0.4), (0.7, -0.25), (1.0, 0.0), (0.9, 0.25), (0.0, 0.42)], 4), segs=16)
    drop.scale = (1, 1, 1)
    drop.data.materials.append(mat_water())
    drop.location = (10, 10, -10)
    ps = em.modifiers.new('drops', 'PARTICLE_SYSTEM').particle_system
    s = ps.settings
    s.type = 'HAIR'
    s.use_advanced_hair = True
    s.count = count
    s.hair_length = 1
    s.render_type = 'OBJECT'
    s.instance_object = drop
    s.particle_size = 0.0011
    s.size_random = 0.75
    s.use_rotations = True
    s.rotation_mode = 'NOR'
    s.phase_factor_random = 0
    s.distribution = 'RAND'
    ps.seed = seed
    em.show_instancer_for_render = False
    return em


def crown_cap(name='Cap', color=(0.85, 0.30, 0.10)):
    segs = 168
    crimps = 21
    prof = [(0.0, 0.0062), (0.0135, 0.0062), (0.0146, 0.0055), (0.0152, 0.0040), (0.0160, 0.0005), (0.0158, 0.0)]
    o = revolve(name, prof, segs=segs)
    me = o.data
    for v in me.vertices:
        x, y, z = v.co
        r = math.hypot(x, y)
        if r > 0.0144:
            a = math.atan2(y, x)
            k = (0.0062 - z) / 0.0062
            f = 1 + 0.055 * k * math.cos(a * crimps)
            v.co.x, v.co.y = x * f, y * f
    o.data.materials.append(mat_cap(color))
    return o


def straw(name, length=0.24, r=0.0031, color=(0.85, 0.30, 0.10)):
    o = revolve(name, [(0.0, 0.0), (r, 0.0), (r, length), (r - 0.0004, length), (r - 0.0004, 0.002), (0.0, 0.002)], segs=40)
    o.data.materials.append(mat_straw(color))
    return o


# ---------------------------------------------------------------- materials
def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF']


def mat_glass():
    if 'Glass' in bpy.data.materials:
        return bpy.data.materials['Glass']
    m, nt, p = _mat('Glass')
    p.inputs['Base Color'].default_value = (0.93, 0.98, 0.95, 1)
    p.inputs['Transmission Weight'].default_value = 1.0
    p.inputs['Roughness'].default_value = 0.015
    p.inputs['IOR'].default_value = 1.52
    return m


def mat_water():
    if 'Water' in bpy.data.materials:
        return bpy.data.materials['Water']
    m, nt, p = _mat('Water')
    p.inputs['Base Color'].default_value = (1, 1, 1, 1)
    p.inputs['Transmission Weight'].default_value = 1.0
    p.inputs['Roughness'].default_value = 0.0
    p.inputs['IOR'].default_value = 1.33
    return m


def mat_cola():
    if 'Cola' in bpy.data.materials:
        return bpy.data.materials['Cola']
    m, nt, p = _mat('Cola')
    p.inputs['Base Color'].default_value = (1, 1, 1, 1)
    p.inputs['Transmission Weight'].default_value = 1.0
    p.inputs['Roughness'].default_value = 0.0
    p.inputs['IOR'].default_value = 1.345
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = (0.62, 0.22, 0.06, 1)
    va.inputs['Density'].default_value = 420.0
    nt.links.new(va.outputs['Volume'], nt.nodes['Material Output'].inputs['Volume'])
    return m


def mat_label():
    if 'Label' in bpy.data.materials:
        return bpy.data.materials['Label']
    m, nt, p = _mat('Label')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(os.path.join(ASSETS, 'tex', 'label.png'))
    tex.interpolation = 'Cubic'
    nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
    nt.links.new(tex.outputs['Alpha'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = 0.35
    p.inputs['Coat Weight'].default_value = 0.3
    m.blend_method = 'HASHED'
    return m


def mat_cap(color):
    m, nt, p = _mat('Cap')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = 0.6
    p.inputs['Roughness'].default_value = 0.32
    p.inputs['Coat Weight'].default_value = 0.6
    return m


def mat_straw(color):
    """paper straw with a helical stripe"""
    m, nt, p = _mat('Straw')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    at = nt.nodes.new('ShaderNodeMath'); at.operation = 'ARCTAN2'
    nt.links.new(sep.outputs['Y'], at.inputs[0]); nt.links.new(sep.outputs['X'], at.inputs[1])
    a2 = nt.nodes.new('ShaderNodeMath'); a2.operation = 'MULTIPLY'; a2.inputs[1].default_value = 1 / (2 * math.pi)
    nt.links.new(at.outputs[0], a2.inputs[0])
    z = nt.nodes.new('ShaderNodeMath'); z.operation = 'MULTIPLY'; z.inputs[1].default_value = 55.0
    nt.links.new(sep.outputs['Z'], z.inputs[0])
    ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'
    nt.links.new(a2.outputs[0], ad.inputs[0]); nt.links.new(z.outputs[0], ad.inputs[1])
    fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'
    nt.links.new(ad.outputs[0], fr.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
    nt.links.new(fr.outputs[0], gt.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (0.92, 0.89, 0.82, 1)
    mix.inputs[7].default_value = (*color, 1)
    nt.links.new(gt.outputs[0], mix.inputs[0])
    nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.65
    return m


def mat_simple(name, color, rough=0.5, metal=0.0, coat=0.0, sss=0.0):
    m, nt, p = _mat(name)
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = coat
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
    return m


def mat_image(name, path, rough=0.5, coat=0.0, alpha=False):
    m, nt, p = _mat(name)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(path)
    nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
    if alpha:
        nt.links.new(tex.outputs['Alpha'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = coat
    return m


def plane(name, size_x, size_y, loc=(0, 0, 0), mat=None, uv_scale=1.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size_x, size_y, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    return o


def box(name, sx, sy, sz, loc=(0, 0, 0), mat=None, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new('bev', 'BEVEL')
        b.width = bevel
        b.segments = 3
    if mat:
        o.data.materials.append(mat)
    return o


def render(path, samples=None, res=None, pct=100):
    sc = bpy.context.scene
    if samples:
        sc.cycles.samples = samples
    if res:
        sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = pct
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
