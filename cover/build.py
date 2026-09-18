"""SEQUENCE cover object, modelled and rendered in Blender/Cycles.

Three parts, matching the reference art:
  cube    a standalone glass cube, the first term of the sequence
  band    two strands braiding around a common axis. Their radius goes to zero
          at the waists, so they merge into one solid there, and opens up at
          each crossing, which is what makes the lens-shaped holes.
  crystal a dense cluster of small plates and blocks welded into one mass.

Usage: python3 build.py --view portrait --theme dark --w 630 --h 891 --out x.png
"""
import argparse, math, random, sys
import bpy
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- parameters
BAND = dict(
    x0=-2.55, x1=2.30,          # the run along the axis
    n_open=3,                    # how many times it parts
    amp=0.42,                    # how far the strands separate
    sec=0.325,                   # cross-section radius at the waists
    sec_pinch=0.34,              # how much the section thins where they part
    braid=0.62,                  # turns of the braid over the whole run
    sec_twist=0.52,              # turns of the section itself (the ribbon twist)
    sec_a=1.30, sec_b=0.70,      # section is a flattened superellipse
    sec_e=0.62,                  # superellipse exponent: 1 = ellipse, ->0 = rect
    ring=28, steps=320,
)
CRYSTAL = dict(
    cx=2.72, cy=0.12, cz=0.0,
    rx=0.86, ry=0.74, rz=0.72,
    count=210, seed=7,
)
CUBE = dict(x=-3.32, y=-0.42, z=0.08, size=0.55, bevel=0.022)

COL_A = (0.30, 0.93, 0.88)      # cyan, at the cube
COL_B = (0.72, 0.52, 0.99)      # violet, through the head
COL_C = (0.34, 0.92, 0.84)      # cyan again, on the crystal tip

# The camera looks along +Y, so on screen right is +X and up is +Z. The
# diagonal the object lies on is therefore a rotation about Y; rotation about
# Z turns it in depth. ortho is the frame's LONGER side, as Blender measures it.
VIEWS = {
    'portrait':  dict(tilt=49.0, depth=-20.0, pitch=0.0,  scale=0.80, shift=(0.00, 0.05), ortho=8.20),
    'spread':    dict(tilt=49.0, depth=-20.0, pitch=0.0,  scale=0.80, shift=(-3.21, 0.05), ortho=12.01),
    'structure': dict(tilt=0.0,  depth=-24.0, pitch=12.0, scale=1.00, shift=(-0.20, 0.00), ortho=9.80),
}

# ---------------------------------------------------------------- mesh helpers
def new_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob

def activate(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def apply_mod(ob, mod):
    activate(ob)
    bpy.ops.object.modifier_apply(modifier=mod.name)

# ---------------------------------------------------------------- the band
def centreline(t, phase):
    """One strand. amp is zero at the waists, so the two strands coincide
    there and the band reads as a single solid; between waists they swing
    apart and leave a hole."""
    B = BAND
    x = B['x0'] + (B['x1'] - B['x0']) * t
    amp = B['amp'] * abs(math.sin(math.pi * B['n_open'] * t))
    th = B['braid'] * 2.0 * math.pi * t + phase
    return Vector((x, amp * math.cos(th), amp * math.sin(th)))

def section_scale(t):
    B = BAND
    return B['sec'] * (1.0 - B['sec_pinch'] * abs(math.sin(math.pi * B['n_open'] * t)))

def superellipse(a, ax, ay, e):
    c, s = math.cos(a), math.sin(a)
    u = math.copysign(abs(c) ** e, c) * ax
    v = math.copysign(abs(s) ** e, s) * ay
    return u, v

def strand(phase, name):
    B = BAND
    steps, ring = B['steps'], B['ring']
    ts = [i / (steps - 1) for i in range(steps)]
    pts = [centreline(t, phase) for t in ts]

    # parallel-transport frame, so the section does not spin with the curve
    tangents = []
    for i in range(steps):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, steps - 1)]
        tangents.append((b - a).normalized())
    up = Vector((0.0, 0.0, 1.0))
    n = (up - tangents[0] * up.dot(tangents[0])).normalized()
    frames = []
    for i in range(steps):
        T = tangents[i]
        n = (n - T * n.dot(T)).normalized()
        frames.append((n.copy(), T.cross(n).normalized()))

    verts, faces = [], []
    for i, t in enumerate(ts):
        P, (N, Bn) = pts[i], frames[i]
        s = section_scale(t)
        # taper the free end so it closes as a nose rather than a stump
        s *= 0.35 + 0.65 * min(1.0, t / 0.05) if t < 0.05 else 1.0
        rot = B['sec_twist'] * 2.0 * math.pi * t
        cr, sr = math.cos(rot), math.sin(rot)
        for j in range(ring):
            u, v = superellipse(2.0 * math.pi * j / ring, B['sec_a'], B['sec_b'], B['sec_e'])
            uu, vv = u * cr - v * sr, u * sr + v * cr
            verts.append(P + (N * uu + Bn * vv) * s)
    for i in range(steps - 1):
        for j in range(ring):
            a = i * ring + j
            b = i * ring + (j + 1) % ring
            faces.append((a, b, b + ring, a + ring))
    # flat caps
    verts.append(pts[0]); verts.append(pts[-1])
    c0, c1 = len(verts) - 2, len(verts) - 1
    for j in range(ring):
        faces.append((c0, (j + 1) % ring, j))
        base = (steps - 1) * ring
        faces.append((c1, base + j, base + (j + 1) % ring))
    return new_obj(name, [tuple(v) for v in verts], faces)

def build_band():
    a = strand(0.0, 'strandA')
    b = strand(math.pi, 'strandB')
    activate(a); b.select_set(True)
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.join()
    band = bpy.context.view_layer.objects.active
    band.name = 'band'
    # fuse the two strands where they meet into one watertight surface
    rm = band.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'
    rm.voxel_size = 0.012; rm.adaptivity = 0.0
    apply_mod(band, rm)
    sm = band.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = 6
    apply_mod(band, sm)
    activate(band); bpy.ops.object.shade_smooth()
    return band

# ---------------------------------------------------------------- the crystal
def build_crystal():
    C = CRYSTAL
    rng = random.Random(C['seed'])
    verts, faces = [], []
    UNIT = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    QUAD = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    for _ in range(C['count']):
        # a point inside the ellipsoid, biased toward the middle
        while True:
            p = Vector((rng.uniform(-1,1), rng.uniform(-1,1), rng.uniform(-1,1)))
            if p.length <= 1.0:
                break
        p = Vector((p.x*C['rx'], p.y*C['ry'], p.z*C['rz'])) * (0.55 + 0.45*rng.random())
        centre = Vector((C['cx'], C['cy'], C['cz'])) + p
        # a mix of flat plates and chunkier blocks, as in the reference cluster
        if rng.random() < 0.58:
            sc = Vector((rng.uniform(0.16,0.30), rng.uniform(0.035,0.075), rng.uniform(0.14,0.28)))
        else:
            sc = Vector((rng.uniform(0.10,0.19), rng.uniform(0.09,0.17), rng.uniform(0.10,0.19)))
        R = (Matrix.Rotation(rng.uniform(0, math.tau), 3, 'Z')
             @ Matrix.Rotation(rng.uniform(0, math.tau), 3, 'Y')
             @ Matrix.Rotation(rng.uniform(0, math.tau), 3, 'X'))
        base = len(verts)
        for v in UNIT:
            verts.append(tuple(centre + R @ Vector((v[0]*sc.x, v[1]*sc.y, v[2]*sc.z))))
        for q in QUAD:
            faces.append(tuple(base + i for i in q))
    cr = new_obj('crystal', verts, faces)
    rm = cr.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'
    rm.voxel_size = 0.0085; rm.adaptivity = 0.0
    apply_mod(cr, rm)
    # collapse the voxel steps back into flat facets so the cluster stays angular
    dc = cr.modifiers.new('dc', 'DECIMATE'); dc.decimate_type = 'DISSOLVE'
    dc.angle_limit = math.radians(11.0)
    apply_mod(cr, dc)
    activate(cr); bpy.ops.object.shade_flat()
    return cr

# ---------------------------------------------------------------- the cube
def build_cube():
    s = CUBE['size']
    bpy.ops.mesh.primitive_cube_add(size=2*s, location=(CUBE['x'], CUBE['y'], CUBE['z']))
    ob = bpy.context.view_layer.objects.active
    ob.name = 'cube'
    bv = ob.modifiers.new('bv', 'BEVEL')
    bv.width = CUBE['bevel']; bv.segments = 3
    apply_mod(ob, bv)
    activate(ob); bpy.ops.object.shade_flat()
    return ob

# ---------------------------------------------------------------- material
def glass_material(ref_empty):
    mat = bpy.data.materials.new('glass')
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.035
    bsdf.inputs['IOR'].default_value = 1.46
    bsdf.inputs['Transmission Weight'].default_value = 1.0
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)

    # one gradient shared by every part: sample position in the empty's space
    coord = nt.nodes.new('ShaderNodeTexCoord'); coord.object = ref_empty
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    rng = nt.nodes.new('ShaderNodeMapRange')
    rng.inputs['From Min'].default_value = CUBE['x']
    rng.inputs['From Max'].default_value = CRYSTAL['cx'] + 0.5
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    e = ramp.color_ramp.elements
    e[0].position = 0.0;  e[0].color = (*COL_A, 1)
    e[1].position = 0.72; e[1].color = (*COL_B, 1)
    m = ramp.color_ramp.elements.new(0.90); m.color = (*COL_B, 1)
    m2 = ramp.color_ramp.elements.new(1.0); m2.color = (*COL_C, 1)

    # depth-dependent colour: thick parts saturate, thin parts stay pale
    vol = nt.nodes.new('ShaderNodeVolumeAbsorption')
    vol.inputs['Density'].default_value = 2.1

    nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['X'], rng.inputs['Value'])
    nt.links.new(rng.outputs['Result'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], vol.inputs['Color'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
    return mat

# ---------------------------------------------------------------- scene
def build_world(theme):
    w = bpy.data.worlds.new('w'); bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    mix = nt.nodes.new('ShaderNodeMixShader')
    lp = nt.nodes.new('ShaderNodeLightPath')
    lit = nt.nodes.new('ShaderNodeBackground')
    cam = nt.nodes.new('ShaderNodeBackground')
    # the dome that lights the glass is bright even on the dark cover; what the
    # camera sees behind the object is a separate, near-black backdrop
    if theme == 'light':
        lit.inputs['Color'].default_value = (0.62, 0.65, 0.72, 1); lit.inputs['Strength'].default_value = 1.5
        cam.inputs['Color'].default_value = (0.965, 0.969, 0.984, 1)
    else:
        lit.inputs['Color'].default_value = (0.42, 0.46, 0.58, 1); lit.inputs['Strength'].default_value = 1.15
        cam.inputs['Color'].default_value = (0.020, 0.026, 0.040, 1)
    cam.inputs['Strength'].default_value = 1.0
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
    nt.links.new(lit.outputs['Background'], mix.inputs[1])
    nt.links.new(cam.outputs['Background'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])

def add_area(name, loc, rot, size, energy, color=(1,1,1)):
    d = bpy.data.lights.new(name, 'AREA')
    d.size = size; d.energy = energy; d.color = color
    ob = bpy.data.objects.new(name, d)
    ob.location = loc; ob.rotation_euler = rot
    bpy.context.collection.objects.link(ob)
    return ob

def build_lights(theme):
    k = 1.0 if theme == 'dark' else 0.8
    add_area('key',  (-5.0, -5.5, 5.5), (math.radians(52), 0, math.radians(-40)), 9.0, 2200*k)
    add_area('rim',  (5.5, 4.0, 2.0),  (math.radians(78), 0, math.radians(135)), 6.0, 1500*k, (0.80, 0.86, 1.0))
    add_area('fill', (1.0, -6.5, -4.0), (math.radians(-40), 0, math.radians(10)), 8.0, 700*k, (0.72, 0.98, 0.96))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--view', default='portrait')
    ap.add_argument('--theme', default='dark')
    ap.add_argument('--w', type=int, default=630)
    ap.add_argument('--h', type=int, default=891)
    ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    V = VIEWS[a.view]

    bpy.ops.wm.read_factory_settings(use_empty=True)

    band = build_band()
    crystal = build_crystal()
    cube = build_cube()

    ref = bpy.data.objects.new('ref', None)
    bpy.context.collection.objects.link(ref)
    mat = glass_material(ref)
    for ob in (band, crystal, cube):
        ob.data.materials.append(mat)

    # tilt the whole object onto the cover diagonal
    grp = bpy.data.objects.new('root', None)
    bpy.context.collection.objects.link(grp)
    for ob in (band, crystal, cube, ref):
        ob.parent = grp
    grp.rotation_euler = (math.radians(V['pitch']), math.radians(-V['tilt']), math.radians(V['depth']))
    # undo the on-screen tilt on the cube alone, so it still reads as a cube in
    # three-quarter view instead of standing on a corner like a diamond
    cube.rotation_euler = (math.radians(-16.0), math.radians(V['tilt'] + 26.0), 0.0)
    grp.scale = (V['scale'],) * 3

    build_world(a.theme)
    build_lights(a.theme)

    cam_data = bpy.data.cameras.new('cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = V['ortho']
    cam = bpy.data.objects.new('cam', cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (V['shift'][0], -22.0, V['shift'][1])
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam

    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 24
    sc.cycles.transmission_bounces = 20
    sc.cycles.transparent_max_bounces = 20
    sc.cycles.caustics_refractive = True
    sc.cycles.blur_glossy = 1.0                 # keeps fireflies out of the glass
    sc.cycles.sample_clamp_indirect = 8.0
    sc.render.resolution_x = a.w
    sc.render.resolution_y = a.h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = a.out
    bpy.ops.render.render(write_still=True)
    print('wrote', a.out)

main()
