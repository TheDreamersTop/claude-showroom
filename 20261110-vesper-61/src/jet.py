"""Procedural business jet 'VESPER 61' for Blender (bpy 5.x).
Axes: +X forward (nose), +Y left wing, +Z up. Origin near wing root, fuselage centreline z=0.
"""
import bpy, bmesh, math
import numpy as np

R = 1.25           # fuselage max radius
L = 26.0           # fuselage length
XN = 11.0          # nose tip x  (tail end at XN - L = -15)

# ---------------------------------------------------------------- helpers
def mesh_from(name, verts, faces, smooth=True, subsurf=1):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(); me.update()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if subsurf:
        m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = subsurf; m.render_levels = subsurf
    return ob

def grid_faces(nr, nc, close_cols=True):
    f = []
    cc = nc if close_cols else nc - 1
    for i in range(nr - 1):
        for j in range(cc):
            j2 = (j + 1) % nc
            f.append((i*nc+j, i*nc+j2, (i+1)*nc+j2, (i+1)*nc+j))
    return f

def airfoil(n=40, t=0.12, camber=0.02):
    """closed loop of (xc, yc), xc 0..1 from TE over upper to LE back lower to TE"""
    beta = np.linspace(0, math.pi, n)
    xc = 0.5*(1-np.cos(beta))
    yt = 5*t*(0.2969*np.sqrt(xc)-0.1260*xc-0.3516*xc**2+0.2843*xc**3-0.1036*xc**4)
    p = 0.4
    yc = np.where(xc < p, camber/p**2*(2*p*xc-xc**2), camber/(1-p)**2*((1-2*p)+2*p*xc-xc**2))
    up = np.stack([xc, yc+yt], 1)[::-1]      # TE -> LE
    lo = np.stack([xc, yc-yt], 1)[1:-1]      # LE -> TE (skip duplicates)
    return np.concatenate([up, lo])

def loft_surface(name, path, chords, xle, thick, camber=0.0, n=36, cap=True, subsurf=1):
    """path: list of (y,z) points; chords/xle/thick per point. Airfoil chord along -X from leading edge."""
    path = np.array(path, float)
    verts = []
    m = None
    for i, (py, pz) in enumerate(path):
        a = path[min(i+1, len(path)-1)] - path[max(i-1, 0)]
        a = a/np.linalg.norm(a)
        N = np.array([-a[1], a[0]])          # rotate tangent 90deg in yz
        af = airfoil(n, thick[i], camber)
        m = len(af)
        c = chords[i]
        for xc, yc in af:
            verts.append((xle[i] - xc*c, py + N[0]*yc*c, pz + N[1]*yc*c))
    faces = grid_faces(len(path), m, True)
    if cap:  # close last section with a centre fan
        base = (len(path)-1)*m
        cen = np.mean(np.array(verts[base:base+m]), 0)
        verts.append(tuple(cen)); ci = len(verts)-1
        for j in range(m): faces.append((base+j, ci, base+(j+1) % m)[::-1])
        cen0 = np.mean(np.array(verts[0:m]), 0)
        verts.append(tuple(cen0)); c0 = len(verts)-1
        for j in range(m): faces.append((j, (j+1) % m, c0)[::-1])
    return mesh_from(name, verts, faces, True, subsurf)

def lathe(name, profile, n=48, axis_pos=(0, 0, 0), subsurf=1):
    """profile: list of (x, r) along X axis."""
    verts = []
    for x, r in profile:
        for j in range(n):
            th = 2*math.pi*j/n
            verts.append((axis_pos[0]+x, axis_pos[1]+r*math.cos(th), axis_pos[2]+r*math.sin(th)))
    faces = grid_faces(len(profile), n, True)
    faces = [f[::-1] for f in faces]
    return mesh_from(name, verts, faces, True, subsurf)

# ---------------------------------------------------------------- fuselage
def fuselage_section(s):
    """returns top, bottom, halfwidth at param s in [0,1] (nose->tail)"""
    if s < 0.16:
        t = s/0.16
        g = (1-(1-t)**2.4)**0.5
        gt = (1-(1-t)**1.7)**0.62      # top rises slower -> windscreen slope
        top = -0.32*R + 1.32*R*gt
        bot = -0.32*R - 0.68*R*g
        w = R*g
    elif s < 0.64:
        top, bot, w = R, -R, R
    else:
        t = (s-0.64)/0.36
        top = R - 0.30*R*t**2.2
        bot = -R + 1.50*R*t**1.25
        w = R*((1-t)**0.85*0.93 + 0.07)
    return top, bot, w

def build_fuselage():
    ns, nt = 140, 56
    verts = []
    ss = np.linspace(0, 1, ns)**1.0
    ss = 0.5 - 0.5*np.cos(np.pi*np.linspace(0, 1, ns))*0  # placeholder
    ss = np.concatenate([np.linspace(0, 0.16, 50)**1.0, np.linspace(0.16, 1, ns-50+1)[1:]])
    ss = np.array([0.16*((i/49)**1.8) for i in range(50)] + list(np.linspace(0.16, 1, ns-49)[1:]))
    for s in ss:
        top, bot, w = fuselage_section(s)
        cz = (top+bot)/2; hz = (top-bot)/2
        x = XN - s*L
        for j in range(nt):
            th = 2*math.pi*j/nt
            c, sn = math.cos(th), math.sin(th)
            # slight superellipse for a fuller cabin
            e = 2.3
            cy = math.copysign(abs(c)**(2/e), c); sz = math.copysign(abs(sn)**(2/e), sn)
            verts.append((x, w*cy, cz + hz*sz))
    faces = grid_faces(len(ss), nt, True)
    # tail cap
    base = (len(ss)-1)*nt
    cen = np.mean(np.array(verts[base:]), 0); verts.append(tuple(cen)); ci = len(verts)-1
    for j in range(nt): faces.append((base+(j+1) % nt, base+j, ci))
    ob = mesh_from('fuselage', verts, faces, True, 1)
    return ob

# ---------------------------------------------------------------- materials
def _n(nt, typ, loc=(0, 0), **kw):
    n = nt.nodes.new(typ); n.location = loc
    for k, v in kw.items(): setattr(n, k, v)
    return n

def math_node(nt, op, a=None, b=None, loc=(0, 0), clamp=False):
    n = _n(nt, 'ShaderNodeMath', loc); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def principled(name, color, rough=0.3, metal=0.0, coat=0.0, coat_rough=0.03):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    return m

WHITE = (0.80, 0.79, 0.76)
NAVY = (0.010, 0.016, 0.040)
GOLD = (0.75, 0.52, 0.25)

def fuselage_material(livery_img=None):
    m = bpy.data.materials.new('fuselage_paint')
    nt = m.node_tree; L_ = nt.links
    b = nt.nodes['Principled BSDF']; b.location = (900, 0)
    tc = _n(nt, 'ShaderNodeTexCoord', (-1400, 0))
    sep = _n(nt, 'ShaderNodeSeparateXYZ', (-1200, 0)); L_.new(tc.outputs['Object'], sep.inputs[0])
    x, y, z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    # --- livery boundary: z_b(x) rising toward the tail
    xn = math_node(nt, 'MULTIPLY', x, -1/L)                     # tail positive
    zb = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', xn, 0.55*R), -0.30*R)
    d = math_node(nt, 'SUBTRACT', z, zb)                        # >0 above boundary
    lower = math_node(nt, 'LESS_THAN', d, 0.0)
    stripe = math_node(nt, 'MULTIPLY', math_node(nt, 'GREATER_THAN', d, 0.05), math_node(nt, 'LESS_THAN', d, 0.085))
    # --- cabin windows (ovals)
    sp, x0, x1, zc, a, bb = 1.12, -5.4, 4.6, 0.18*R, 0.21, 0.29
    u = math_node(nt, 'DIVIDE', math_node(nt, 'SUBTRACT', x, x0), sp)
    f = math_node(nt, 'SUBTRACT', math_node(nt, 'FRACT', u), 0.5)
    dx = math_node(nt, 'DIVIDE', math_node(nt, 'MULTIPLY', f, sp), a)
    dz = math_node(nt, 'DIVIDE', math_node(nt, 'SUBTRACT', z, zc), bb)
    rr = math_node(nt, 'ADD', math_node(nt, 'POWER', dx, 2.0), math_node(nt, 'POWER', dz, 2.0))
    win = math_node(nt, 'LESS_THAN', rr, 1.0)
    inx = math_node(nt, 'MULTIPLY', math_node(nt, 'GREATER_THAN', x, x0), math_node(nt, 'LESS_THAN', x, x1))
    side = math_node(nt, 'GREATER_THAN', math_node(nt, 'ABSOLUTE', y), 0.6)
    win = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', win, inx), side)
    # --- windscreen band near the nose
    xs = math_node(nt, 'SUBTRACT', x, XN)                       # 0 at tip, negative aft
    nx = math_node(nt, 'MULTIPLY', xs, -1.0)                    # distance aft of tip
    zr = math_node(nt, 'SUBTRACT', z, 0.22)
    zlo = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', nx, 1.7), 0.10), 0.22)
    ws = math_node(nt, 'GREATER_THAN', z, zlo)
    front = math_node(nt, 'GREATER_THAN', nx, math_node(nt, 'ADD', 1.75, math_node(nt, 'MULTIPLY', zr, 0.55)))
    rear = math_node(nt, 'LESS_THAN', nx, math_node(nt, 'ADD', 3.05, math_node(nt, 'MULTIPLY', zr, 0.75)))
    post = math_node(nt, 'GREATER_THAN', math_node(nt, 'ABSOLUTE', y), 0.10)
    ws = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', ws, front), math_node(nt, 'MULTIPLY', rear, post))
    div = math_node(nt, 'GREATER_THAN', math_node(nt, 'ABSOLUTE', math_node(nt, 'SUBTRACT', nx, math_node(nt, 'ADD', 2.42, math_node(nt, 'MULTIPLY', zr, 0.65)))), 0.04)
    ws = math_node(nt, 'MULTIPLY', ws, div)
    glass = math_node(nt, 'MAXIMUM', win, ws)
    # colors
    def rgb(c, loc):
        n = _n(nt, 'ShaderNodeRGB', loc); n.outputs[0].default_value = (*c, 1); return n.outputs[0]
    def mixc(fac, a_, b_, loc):
        n = _n(nt, 'ShaderNodeMix', loc); n.data_type = 'RGBA'
        L_.new(fac, n.inputs['Factor']); L_.new(a_, n.inputs[6]); L_.new(b_, n.inputs[7]); return n.outputs[2]
    col = mixc(lower, rgb(WHITE, (0, 300)), rgb(NAVY, (0, 200)), (300, 200))
    col = mixc(stripe, col, rgb(GOLD, (0, 100)), (450, 200))
    col = mixc(glass, col, rgb((0.004, 0.005, 0.007), (0, 0)), (600, 200))
    L_.new(col, b.inputs['Base Color'])
    metal = math_node(nt, 'MAXIMUM', math_node(nt, 'MULTIPLY', lower, 0.55), stripe)
    L_.new(metal, b.inputs['Metallic'])
    rough = math_node(nt, 'ADD', 0.32, math_node(nt, 'MULTIPLY', glass, -0.30))
    L_.new(rough, b.inputs['Roughness'])
    b.inputs['Coat Weight'].default_value = 1.0
    b.inputs['Coat Roughness'].default_value = 0.025
    if livery_img:
        img = bpy.data.images.load(livery_img)
        # project lettering onto the side: U from x, V from z
        mp = _n(nt, 'ShaderNodeCombineXYZ', (-800, -400))
        uu = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', x, 5.9), math_node(nt, 'MULTIPLY', math_node(nt, 'SIGN', y), -1.0)), 0.0)
        L_.new(math_node(nt, 'ADD', math_node(nt, 'DIVIDE', uu, 3.2), 0.5), mp.inputs[0])
        L_.new(math_node(nt, 'ADD', math_node(nt, 'DIVIDE', math_node(nt, 'SUBTRACT', z, 0.55*R), 0.8), 0.5), mp.inputs[1])
        it = _n(nt, 'ShaderNodeTexImage', (-500, -400)); it.image = img; it.extension = 'CLIP'
        L_.new(mp.outputs[0], it.inputs[0])
        a2 = math_node(nt, 'MULTIPLY', it.outputs['Alpha'], side)
        col2 = mixc(a2, col, rgb(NAVY, (300, -200)), (750, 100))
        L_.new(col2, b.inputs['Base Color'])
    return m

# ---------------------------------------------------------------- assembly
def build_jet(livery_img=None, fin_img=None, gear=True):
    objs = []
    fus = build_fuselage(); objs.append(fus)
    fus.data.materials.append(fuselage_material(livery_img))
    paint = principled('paint_white', WHITE, 0.32, 0, 1.0, 0.025)
    navy = principled('paint_navy', NAVY, 0.3, 0.55, 1.0, 0.025)
    chrome = principled('chrome', (0.9, 0.9, 0.9), 0.08, 1.0)
    dark = principled('intake_dark', (0.01, 0.01, 0.012), 0.45, 0.6)
    rubber = principled('rubber', (0.015, 0.015, 0.015), 0.6)
    strut = principled('strut', (0.6, 0.6, 0.62), 0.25, 1.0)

    # wing: path in (y,z); straight then winglet bend
    ys, zs = [], []
    dih = math.radians(4.5)
    n_main = 14; span = 11.6
    for i in range(n_main):
        yy = 0.2 + span*i/(n_main-1)
        ys.append(yy); zs.append(-0.62*R + (yy-0.2)*math.tan(dih))
    yt, zt = ys[-1], zs[-1]
    for k in range(1, 9):
        a = (math.pi/2-0.18)*k/8
        rad = 0.6
        ys.append(yt + rad*math.sin(a)); zs.append(zt + rad*(1-math.cos(a)))
    for k in range(1, 5):
        ys.append(ys[-1] + 0.06); zs.append(zs[-1] + 0.45)
    npnt = len(ys)
    sweep = math.tan(math.radians(31))
    chords, xle, th = [], [], []
    for i in range(npnt):
        if i < n_main:
            t = i/(n_main-1)
            c = 4.9*(1-t) + 1.45*t
            if i < 3: c += (3-i)*0.55   # root fillet/yehudi
            xl = 1.6 - (ys[i]-0.2)*sweep
            tk = 0.13*(1-t) + 0.09*t
        else:
            k = i - n_main + 1; tt = k/(npnt-n_main)
            c = 1.45*(1-tt) + 0.62*tt
            xl = 1.6 - span*sweep - 0.25*k
            tk = 0.09
        chords.append(c); xle.append(xl); th.append(tk)
    wl = loft_surface('wing_L', list(zip(ys, zs)), chords, xle, th, 0.02, 34)
    wr = loft_surface('wing_R', list(zip([-v for v in ys], zs)), chords, xle, th, 0.02, 34)
    for w in (wl, wr): w.data.materials.append(paint); objs.append(w)
    # mirrored normals fix for right wing
    bpy.context.view_layer.objects.active = wr
    me = wr.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()

    # vertical fin
    xf = XN - 0.80*L
    fz = [R*0.62 + 4.3*i/11 for i in range(12)]
    fy = [0.0]*12
    fsw = math.tan(math.radians(46))
    fch = [4.6*(1-i/11) + 2.3*i/11 for i in range(12)]
    fxl = [xf + 0.9 - (fz[i]-fz[0])*fsw for i in range(12)]
    fin = loft_surface('fin', list(zip(fy, fz)), fch, fxl, [0.11]*12, 0.0, 34)
    fin.data.materials.append(navy); objs.append(fin)
    # horizontal stabiliser (T-tail)
    ztop = fz[-1] - 0.15; xt = fxl[-1]
    hs_y = [0.0 + 4.3*i/9 for i in range(10)]
    hs_z = [ztop + yy*math.tan(math.radians(2)) for yy in hs_y]
    hs_c = [2.5*(1-i/9) + 1.1*i/9 for i in range(10)]
    hs_x = [xt + 0.3 - yy*math.tan(math.radians(34)) for yy in hs_y]
    hl = loft_surface('hstab_L', list(zip(hs_y, hs_z)), hs_c, hs_x, [0.10]*10, 0.0, 30)
    hr = loft_surface('hstab_R', list(zip([-v for v in hs_y], hs_z)), hs_c, hs_x, [0.10]*10, 0.0, 30)
    me = hr.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    for h in (hl, hr): h.data.materials.append(navy); objs.append(h)
    # fin livery image
    if fin_img:
        mat = bpy.data.materials.new('fin_livery'); nt = mat.node_tree; L_ = nt.links
        b = nt.nodes['Principled BSDF']
        b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.025
        tc = _n(nt, 'ShaderNodeTexCoord'); sep = _n(nt, 'ShaderNodeSeparateXYZ'); L_.new(tc.outputs['Object'], sep.inputs[0])
        cmb = _n(nt, 'ShaderNodeCombineXYZ')
        uu = math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', sep.outputs[0], xf - 3.3), math_node(nt, 'MULTIPLY', math_node(nt, 'SIGN', sep.outputs[1]), -1.0))
        L_.new(math_node(nt, 'ADD', math_node(nt, 'DIVIDE', uu, 4.4), 0.5), cmb.inputs[0])
        L_.new(math_node(nt, 'DIVIDE', math_node(nt, 'SUBTRACT', sep.outputs[2], R*0.62 + 0.4), 3.6), cmb.inputs[1])
        it = _n(nt, 'ShaderNodeTexImage'); it.image = bpy.data.images.load(fin_img); it.extension = 'CLIP'
        L_.new(cmb.outputs[0], it.inputs[0])
        mix = _n(nt, 'ShaderNodeMix'); mix.data_type = 'RGBA'
        L_.new(it.outputs['Alpha'], mix.inputs['Factor'])
        mix.inputs[6].default_value = (*NAVY, 1); L_.new(it.outputs['Color'], mix.inputs[7])
        L_.new(mix.outputs[2], b.inputs['Base Color'])
        L_.new(math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, it.outputs['Alpha']), 0.55), b.inputs['Metallic'])
        b.inputs['Roughness'].default_value = 0.3
        fin.data.materials.clear(); fin.data.materials.append(mat)

    # engines
    ex = XN - 0.73*L
    prof = [(0.00, 0.50), (0.04, 0.585), (0.15, 0.64), (0.6, 0.68), (1.6, 0.68), (2.6, 0.60), (3.3, 0.50), (3.42, 0.47)]
    for sgn in (1, -1):
        ey, ez = sgn*(R + 1.05), 0.30*R
        nac = lathe(f'nacelle_{sgn}', [(ex + 1.7 - px, r) for px, r in prof], 56, (0, ey, ez))
        nac.data.materials.append(paint); objs.append(nac)
        lip = lathe(f'lip_{sgn}', [(ex + 1.7 + 0.005, 0.45), (ex + 1.7 + 0.02, 0.52), (ex + 1.7 - 0.06, 0.60), (ex + 1.7 - 0.16, 0.645)], 56, (0, ey, ez))
        lip.data.materials.append(chrome); objs.append(lip)
        fan = lathe(f'fan_{sgn}', [(ex + 1.45, 0.001), (ex + 1.45, 0.50), (ex + 1.7, 0.50)], 48, (0, ey, ez), 0)
        fan.data.materials.append(dark); objs.append(fan)
        cone = lathe(f'cone_{sgn}', [(ex - 1.70, 0.44), (ex - 1.95, 0.30), (ex - 2.15, 0.05), (ex - 2.16, 0.001)], 32, (0, ey, ez))
        cone.data.materials.append(strut); objs.append(cone)
        # pylon
        py_ = [sgn*0.6, sgn*(R+0.5)]
        pz = [0.30*R, 0.30*R]
        pyl = loft_surface(f'pylon_{sgn}', list(zip(py_, pz)), [2.1, 1.9], [ex + 0.9, ex + 0.85], [0.12, 0.12], 0, 24, True)
        if sgn < 0:
            me = pyl.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
        pyl.data.materials.append(paint); objs.append(pyl)

    gear_objs = []
    if gear:
        gz = -R - 1.25  # ground contact z = gz - wheel radius
        def wheel(name, x, y, rad, width):
            prof = [(-width/2, rad*0.55), (-width/2, rad*0.9), (-width/2+0.03, rad), (width/2-0.03, rad), (width/2, rad*0.9), (width/2, rad*0.55)]
            ob = lathe(name, prof, 40, (0, 0, 0))
            ob.rotation_euler = (0, 0, math.pi/2); ob.location = (x, y, gz)
            ob.data.materials.append(rubber)
            hub = lathe(name+'_hub', [(-width/2+0.02, 0.001), (-width/2+0.02, rad*0.56), (width/2-0.02, rad*0.56), (width/2-0.02, 0.001)], 24, (0, 0, 0), 0)
            hub.rotation_euler = (0, 0, math.pi/2); hub.location = (x, y, gz); hub.data.materials.append(strut)
            return [ob, hub]
        def leg(name, x, y, z0, z1, r=0.09):
            ob = lathe(name, [(0, r), (z0-z1, r)], 16, (0, 0, 0), 0)
            ob.rotation_euler = (0, -math.pi/2, 0); ob.location = (x, y, z1)
            ob.data.materials.append(strut); return ob
        xm = 0.2
        for sgn in (1, -1):
            gear_objs += wheel(f'mw_{sgn}a', xm, sgn*2.35, 0.48, 0.32)
            gear_objs += wheel(f'mw_{sgn}b', xm, sgn*1.85, 0.48, 0.32)
            gear_objs.append(leg(f'mleg_{sgn}', xm, sgn*2.1, -0.75*R, gz))
        xnw = XN - 2.6
        gear_objs += wheel('nw_a', xnw, 0.17, 0.30, 0.2)
        gear_objs += wheel('nw_b', xnw, -0.17, 0.30, 0.2)
        gear_objs.append(leg('nleg', xnw, 0, -0.6*R, gz, 0.07))
        objs += gear_objs

    root = bpy.data.objects.new('VESPER', None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs: o.parent = root
    root['ground_offset'] = (-R - 1.25 - 0.48) if gear else 0
    return root, gear_objs
