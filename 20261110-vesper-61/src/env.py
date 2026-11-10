"""Environments: sunset sky with camera-only sun disc, cloud sea, sun lamp."""
import bpy, math, os
from mathutils import Vector
from jet import _n, math_node

def sunset_world(elev=1.5, rot=90.0, altitude=9000.0, strength=1.0, dust=1.0, air=1.0, ozone=1.0):
    w = bpy.data.worlds.new('sunset'); bpy.context.scene.world = w
    nt = w.node_tree; L = nt.links
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = _n(nt, 'ShaderNodeOutputWorld', (900, 0))
    skies = []
    for disc in (True, False):
        s = _n(nt, 'ShaderNodeTexSky', (0, 300 if disc else 0))
        s.sky_type = 'MULTIPLE_SCATTERING'
        s.sun_elevation = math.radians(elev); s.sun_rotation = math.radians(rot)
        s.altitude = altitude; s.sun_disc = disc
        s.aerosol_density = dust; s.air_density = air; s.ozone_density = ozone
        s.sun_size = math.radians(0.545*1.15)
        skies.append(s)
    skies[0].sun_intensity = float(os.environ.get('DISC', 0.02))
    lp = _n(nt, 'ShaderNodeLightPath', (0, 600))
    mix = _n(nt, 'ShaderNodeMix', (300, 200)); mix.data_type = 'RGBA'
    L.new(lp.outputs['Is Camera Ray'], mix.inputs['Factor'])
    L.new(skies[1].outputs[0], mix.inputs[6]); L.new(skies[0].outputs[0], mix.inputs[7])
    bg = _n(nt, 'ShaderNodeBackground', (600, 0)); bg.inputs['Strength'].default_value = strength
    L.new(mix.outputs[2], bg.inputs[0]); L.new(bg.outputs[0], out.inputs[0])
    return w, skies

def sun_dir(elev, rot):
    """direction toward the sun, matching Blender's sky texture convention"""
    e, r = math.radians(elev), math.radians(rot)
    return Vector((math.sin(r)*math.cos(e), math.cos(r)*math.cos(e), math.sin(e)))

def add_sun_lamp(elev, rot, energy=4.0, color=(1.0, 0.58, 0.32), angle=4.0):
    ld = bpy.data.lights.new('sunlamp', 'SUN'); ld.energy = energy; ld.color = color; ld.angle = math.radians(angle)
    o = bpy.data.objects.new('sunlamp', ld); bpy.context.scene.collection.objects.link(o)
    d = sun_dir(elev, rot)
    o.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    return o

def _fbm(n, beta, seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[:, None]; ky = np.fft.fftfreq(n)[None, :]
    k = np.sqrt(kx**2 + ky**2); k[0, 0] = 1
    spec = (rng.normal(size=(n, n)) + 1j*rng.normal(size=(n, n))) / k**beta
    spec[0, 0] = 0
    f = np.real(np.fft.ifft2(spec)); f /= f.std()
    return f

def cloud_heights(n=2048, seed=3, tile=12000.0, count=0):
    """cumulus field built in passes: big domes, then medium and small billows sitting on the surface (metres)."""
    import numpy as np, os
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'_clouds3_{n}_{seed}_{int(tile)}.npy')
    if os.path.exists(cache): return np.load(cache)
    rng = np.random.default_rng(seed)
    px = tile / n
    base = _fbm(n, 2.0, seed)
    dens = _fbm(n, 1.8, seed + 5)
    h = (-30 + 15*_fbm(n, 2.2, seed + 9)).astype(np.float32)
    def stamp(cx, cy, rm, top):
        rp = rm/px; R = int(rp) + 1
        xi = np.arange(int(cx) - R, int(cx) + R + 1); yi = np.arange(int(cy) - R, int(cy) + R + 1)
        d2 = ((xi - cx)[:, None]**2 + (yi - cy)[None, :]**2)/rp**2
        cap = np.where(d2 < 1, top - rm*(1 - np.sqrt(np.clip(1 - d2, 0, 1))), -1e9)
        ii = (xi % n)[:, None]; jj = (yi % n)[None, :]
        h[ii, jj] = np.maximum(h[ii, jj], cap)
    def place(count, rmin, rmax, on_surface, lift, thresh):
        k = 0
        while k < count:
            cx, cy = rng.uniform(0, n, 2)
            dd = dens[int(cx), int(cy)]
            if rng.uniform() > 1/(1 + np.exp(-3.0*(dd - thresh))): continue
            rm = rmin*np.exp(rng.uniform()**1.4*np.log(rmax/rmin))
            if on_surface:
                hc = h[int(cx) % n, int(cy) % n]
                if hc < 0: continue
                top = hc + rm*lift
            else:
                top = 90.0*base[int(cx), int(cy)] + rm*lift + 30
            stamp(cx, cy, rm, top); k += 1
    place(2600, 160, 480, False, 0.62, -0.3)
    place(14000, 45, 170, True, 0.42, -0.6)
    place(30000, 28, 60, True, 0.40, -0.8)
    # soften: separable gaussian blur (sigma ~2 px) to kill aliasing
    k = np.exp(-0.5*(np.arange(-6, 7)/2.0)**2); k /= k.sum()
    for ax in (0, 1):
        h = sum(np.roll(h, s_, axis=ax)*w_ for s_, w_ in zip(range(-6, 7), k)).astype(np.float32)
    np.save(cache, h)
    return h

def cloud_sea(size=24000.0, res=1600, z=0.0, haze_start=1200.0, haze_dist=9000.0, amp=230.0, seed=3, sky=None):
    import numpy as np
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=res, size=size, location=(0, 0, z))
    o = bpy.context.active_object; o.name = 'clouds'
    me = o.data
    co = np.zeros(len(me.vertices)*3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    n = 2048
    tile = 12000.0
    hm = cloud_heights(n, seed, tile)
    u = (co[:, 0] / tile * n) % n; v = (co[:, 1] / tile * n) % n
    i0 = np.floor(u).astype(int); j0 = np.floor(v).astype(int); fu = u - i0; fv = v - j0
    i1 = (i0 + 1) % n; j1 = (j0 + 1) % n
    hv = (hm[i0, j0]*(1-fu)*(1-fv) + hm[i1, j0]*fu*(1-fv) + hm[i0, j1]*(1-fu)*fv + hm[i1, j1]*fu*fv)
    co[:, 2] = hv*(amp/110.0)
    me.vertices.foreach_set('co', co.ravel()); me.update()
    me.shade_smooth() if hasattr(me, 'shade_smooth') else None
    for p in me.polygons: p.use_smooth = True
    mat = bpy.data.materials.new('cloud'); nt = mat.node_tree; L = nt.links
    for nn in list(nt.nodes): nt.nodes.remove(nn)
    out = _n(nt, 'ShaderNodeOutputMaterial', (1600, 0))
    tc = _n(nt, 'ShaderNodeTexCoord', (-1400, 0))
    n2 = _n(nt, 'ShaderNodeTexNoise', (-900, 0)); n2.inputs['Scale'].default_value = 1/60.0; n2.inputs['Detail'].default_value = 7; n2.inputs['Roughness'].default_value = 0.62
    L.new(tc.outputs['Object'], n2.inputs['Vector'])
    bump = _n(nt, 'ShaderNodeBump', (200, 0)); bump.inputs['Strength'].default_value = 0.25; bump.inputs['Distance'].default_value = 6.0
    L.new(n2.outputs['Fac'], bump.inputs['Height'])
    # height tint: low = cool shadowy, high = bright
    sep = _n(nt, 'ShaderNodeSeparateXYZ', (-900, 400)); L.new(tc.outputs['Object'], sep.inputs[0])
    ht = math_node(nt, 'DIVIDE', math_node(nt, 'ADD', sep.outputs[2], 20.0), amp*3.0)
    ht = math_node(nt, 'MINIMUM', math_node(nt, 'MAXIMUM', ht, 0.0), 1.0)
    cr = _n(nt, 'ShaderNodeMix', (300, 400)); cr.data_type = 'RGBA'
    L.new(ht, cr.inputs['Factor']); cr.inputs[6].default_value = (0.50, 0.55, 0.68, 1); cr.inputs[7].default_value = (0.95, 0.94, 0.95, 1)
    dif = _n(nt, 'ShaderNodeBsdfDiffuse', (600, 300)); L.new(cr.outputs[2], dif.inputs['Color'])
    dif.inputs['Roughness'].default_value = 1.0
    tr = _n(nt, 'ShaderNodeBsdfTranslucent', (600, 150)); tr.inputs['Color'].default_value = (1.0, 0.85, 0.75, 1)
    L.new(bump.outputs[0], dif.inputs['Normal'])
    mx = _n(nt, 'ShaderNodeMixShader', (850, 200)); mx.inputs[0].default_value = 0.22
    L.new(dif.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2])
    # haze = the sky itself seen just above the horizon in this direction
    geo = _n(nt, 'ShaderNodeNewGeometry', (0, -300))
    dirn = _n(nt, 'ShaderNodeVectorMath', (200, -300)); dirn.operation = 'SCALE'; dirn.inputs['Scale'].default_value = -1.0
    L.new(geo.outputs['Incoming'], dirn.inputs[0])
    sp = _n(nt, 'ShaderNodeSeparateXYZ', (350, -300)); L.new(dirn.outputs[0], sp.inputs[0])
    cb = _n(nt, 'ShaderNodeCombineXYZ', (500, -300))
    L.new(sp.outputs[0], cb.inputs[0]); L.new(sp.outputs[1], cb.inputs[1]); cb.inputs[2].default_value = 0.004
    hzsky = _n(nt, 'ShaderNodeTexSky', (650, -300))
    if sky is not None:
        for a in ('sky_type', 'sun_elevation', 'sun_rotation', 'altitude', 'aerosol_density', 'air_density', 'ozone_density'):
            setattr(hzsky, a, getattr(sky, a))
    hzsky.sun_disc = False
    L.new(cb.outputs[0], hzsky.inputs['Vector'])
    cd = _n(nt, 'ShaderNodeCameraData', (300, -100))
    dd = math_node(nt, 'MAXIMUM', math_node(nt, 'SUBTRACT', cd.outputs['View Distance'], haze_start), 0.0)
    hz = math_node(nt, 'SUBTRACT', 1.0, math_node(nt, 'EXPONENT', math_node(nt, 'DIVIDE', dd, -haze_dist)))
    em = _n(nt, 'ShaderNodeEmission', (900, -150)); em.inputs['Strength'].default_value = 1.0
    L.new(hzsky.outputs[0], em.inputs['Color'])
    mx2 = _n(nt, 'ShaderNodeMixShader', (1300, 100))
    L.new(hz, mx2.inputs[0]); L.new(mx.outputs[0], mx2.inputs[1]); L.new(em.outputs[0], mx2.inputs[2])
    L.new(mx2.outputs[0], out.inputs['Surface'])
    o.data.materials.append(mat)
    # second user of the mesh -> Cycles keeps it as an instance (BVH built once, transforms cheap)
    twin = bpy.data.objects.new('clouds_twin', o.data); bpy.context.scene.collection.objects.link(twin)
    twin.location = (0, 0, z - 50000)
    bpy.ops.mesh.primitive_plane_add(size=800000, location=(0, 0, 0))
    far = bpy.context.active_object; far.name = 'clouds_far'
    far.data.materials.append(mat)
    far.parent = o; far.location = (0, 0, -15.0)
    return o, mat
