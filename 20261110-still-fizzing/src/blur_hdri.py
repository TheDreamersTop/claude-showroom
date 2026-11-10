"""Blender-run: write pre-blurred copies of HDRIs (for camera-visible background, avoids DOF noise)."""
import bpy, numpy as np, os, sys
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'hdri')
names = sys.argv[sys.argv.index('--') + 1:]
def blur_axis(a, sigma, axis):
    n = a.shape[axis]
    f = np.fft.rfftfreq(n) if False else None
    k = np.fft.fftfreq(n)
    g = np.exp(-2 * (np.pi * k * sigma) ** 2)
    shape = [1, 1, 1]; shape[axis] = n
    return np.real(np.fft.ifft(np.fft.fft(a, axis=axis) * g.reshape(shape), axis=axis))
for nm in names:
    img = bpy.data.images.load(os.path.join(H, nm))
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rgb = a[..., :3]
    rgb = blur_axis(rgb, 10, 1)  # wraps horizontally: correct for equirect
    pad = np.concatenate([rgb[:40][::-1], rgb, rgb[-40:][::-1]], 0)
    rgb = blur_axis(pad, 10, 0)[40:-40]
    a[..., :3] = np.maximum(rgb, 0)
    out = bpy.data.images.new('b', w, h, float_buffer=True)
    out.pixels = a.ravel()
    out.filepath_raw = os.path.join(H, nm.replace('.hdr', '_blur.hdr'))
    out.file_format = 'HDR'
    out.save()
    print('blurred', nm)
