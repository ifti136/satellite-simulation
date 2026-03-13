"""
texture_loader.py — Load image files into OpenGL 2D textures via PIL.
"""
import os
from PIL import Image
from OpenGL.GL import *
import numpy as np


def load_texture(path: str, flip: bool = True) -> int:
    """
    Load *path* into an OpenGL texture and return the texture ID.
    flip=True flips vertically so the image is right-side up on a UV sphere.
    Returns 0 on failure (allows graceful degradation).
    """
    if not os.path.exists(path):
        print(f"[texture] WARNING: file not found – {path}")
        return _placeholder_texture()

    try:
        img = Image.open(path).convert("RGBA")
        if flip:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        data = np.array(img, dtype=np.uint8)

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height,
                     0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)
        return tex_id

    except Exception as e:
        print(f"[texture] ERROR loading {path}: {e}")
        return _placeholder_texture()


def _placeholder_texture() -> int:
    """1×1 white placeholder texture."""
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    data = np.array([255, 255, 255, 255], dtype=np.uint8)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tex_id
