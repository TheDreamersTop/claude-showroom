import bpy, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(ROOT, 'tex')
sys.path.insert(0, HERE)

W, H = 1920, 816   # 2.35:1

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    p = bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type = 'OPTIX'; p.get_devices()
    for d in p.devices: d.use = (d.type == 'OPTIX')
    sc.cycles.device = 'GPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 6
    sc.cycles.glossy_bounces = 4
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.fps = 24
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    sc.view_settings.exposure = -2.5
    sc.render.use_persistent_data = True
    return sc

def sky_world(elev_deg=1.5, rot_deg=0.0, strength=1.0, altitude=0.0, sun_int=1.0, air=1.0, dust=1.0, sky_type='MULTIPLE_SCATTERING'):
    w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w
    nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = sky_type
    sky.sun_elevation = math.radians(elev_deg)
    sky.sun_rotation = math.radians(rot_deg)
    sky.altitude = altitude
    sky.sun_intensity = sun_int
    sky.air_density = air
    sky.aerosol_density = dust
    sky.sun_disc = True
    bg.inputs['Strength'].default_value = strength
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    return w, sky

def camera(name='cam', lens=50, loc=(0, 0, 0), target=None, sensor=36):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = sensor
    cd.clip_start = 0.05; cd.clip_end = 200000
    cam = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    bpy.context.scene.camera = cam
    if target is not None:
        c = cam.constraints.new('TRACK_TO'); c.target = target
        c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    return cam

def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e); e.location = loc; return e

def sun_lamp(elev_deg, rot_deg, strength=4.0, angle_deg=0.6, color=(1, 0.75, 0.5)):
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = strength; ld.angle = math.radians(angle_deg); ld.color = color
    o = bpy.data.objects.new('sun', ld); bpy.context.scene.collection.objects.link(o)
    # sun direction: from azimuth rot (measured like the sky texture: 0 -> +Y? ) we set via euler
    o.rotation_euler = (math.radians(90 - elev_deg), 0, math.radians(rot_deg))
    return o

def key(obj, path, frame, value, interp='BEZIER'):
    setattr(obj, path, value) if not isinstance(path, tuple) else None
    obj.keyframe_insert(data_path=path, frame=frame)

def set_linear(obj):
    ad = obj.animation_data
    if not ad or not ad.action: return
    try:
        for fc in ad.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    except AttributeError:
        # Blender 5 layered actions
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for k in fc.keyframe_points: k.interpolation = 'LINEAR'

def render_frames(outdir, f0, f1, step=1):
    sc = bpy.context.scene
    os.makedirs(outdir, exist_ok=True)
    for f in range(f0, f1 + 1, step):
        path = os.path.join(outdir, f'{f:04d}.png')
        if os.path.exists(path): continue
        sc.frame_set(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('FRAME', f, flush=True)

def render_still(path):
    sc = bpy.context.scene; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
