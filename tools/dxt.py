"""DXT1 (BC1) blocks for VTF textures: a small numpy encoder (endpoints on each block's main colour axis, every pixel
on the nearest of the four colours) and a decoder for previews. 4x4 pixels in 8 bytes, a sixth of RGB."""
import numpy as np

BLOCK = np.dtype([('c0', '<u2'), ('c1', '<u2'), ('bits', '<u4')])


def _to565(c):
    c = np.clip(np.rint(c), 0, 255).astype(np.uint16)
    return ((c[..., 0] >> 3) << 11) | ((c[..., 1] >> 2) << 5) | (c[..., 2] >> 3)


def _from565(v):
    v = v.astype(np.uint16)
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.float32)


def encode(img):
    """img: (H, W, 3) uint8 with H and W multiples of 4 -> the DXT1 blocks, row by row, as bytes."""
    h, w, _ = img.shape
    px = img.reshape(h // 4, 4, w // 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3).astype(np.float32)
    mean = px.mean(1, keepdims=True)
    d = px - mean
    cov = np.einsum('npi,npj->nij', d, d)
    axis = np.ones((len(px), 3), np.float32)
    for _ in range(4):  # power iteration: the block's main colour axis
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-6)
    t = np.einsum('npi,ni->np', d, axis)
    c0 = _to565(mean[:, 0] + axis * t.max(1, keepdims=True))
    c1 = _to565(mean[:, 0] + axis * t.min(1, keepdims=True))
    c0, c1 = np.maximum(c0, c1), np.minimum(c0, c1)  # c0 > c1: the four-colour mode
    p0, p1 = _from565(c0), _from565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)
    idx = ((px[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1).argmin(-1).astype(np.uint32)
    idx[c0 == c1] = 0  # one colour: every pixel on c0
    out = np.empty(len(px), BLOCK)
    out['c0'], out['c1'] = c0, c1
    out['bits'] = (idx << (2 * np.arange(16, dtype=np.uint32))).sum(1).astype(np.uint32)
    return out.tobytes()


def decode(data, w, h, offset=0):
    """DXT1 blocks -> (H, W, 3) uint8."""
    b = np.frombuffer(data, BLOCK, (w // 4) * (h // 4), offset)
    p0, p1 = _from565(b['c0']), _from565(b['c1'])
    four = (b['c0'] > b['c1'])[:, None]
    pal = np.stack([p0, p1, np.where(four, (2 * p0 + p1) / 3, (p0 + p1) / 2),
                    np.where(four, (p0 + 2 * p1) / 3, 0)], 1)
    idx = ((b['bits'][:, None] >> (2 * np.arange(16, dtype=np.uint32))) & 3).astype(np.int64)
    px = np.take_along_axis(pal, np.repeat(idx[..., None], 3, -1), 1)
    img = px.reshape(h // 4, w // 4, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, 3)
    return np.clip(np.rint(img), 0, 255).astype(np.uint8)
