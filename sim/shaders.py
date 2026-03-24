"""
shaders.py — GLSL shader source strings + compile/link utilities.
GLSL 1.20 (OpenGL 2.1 compatibility profile).

Shaders included
----------------
EARTH_VERT / EARTH_FRAG  — day/night blend, specular ocean glint
PHONG_VERT / PHONG_FRAG  — Phong shading for planets, moons, satellites
RING_VERT  / RING_FRAG   — Saturn-style ring disc, alpha-blended
ATMO_VERT  / ATMO_FRAG   — additive rim-glow atmosphere shell
UNLIT_VERT / UNLIT_FRAG  — skybox, sun (no lighting)
"""
from OpenGL.GL import *


def _compile(src: str, shader_type) -> int:
    shader = glCreateShader(shader_type)
    glShaderSource(shader, src)
    glCompileShader(shader)
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        raise RuntimeError(f"Shader compile:\n{glGetShaderInfoLog(shader).decode()}")
    return shader


def link_program(vert_src: str, frag_src: str) -> int:
    vert = _compile(vert_src, GL_VERTEX_SHADER)
    frag = _compile(frag_src, GL_FRAGMENT_SHADER)
    prog = glCreateProgram()
    glAttachShader(prog, vert); glAttachShader(prog, frag)
    glLinkProgram(prog)
    if not glGetProgramiv(prog, GL_LINK_STATUS):
        raise RuntimeError(f"Program link:\n{glGetProgramInfoLog(prog).decode()}")
    glDeleteShader(vert); glDeleteShader(frag)
    return prog


# ── Earth (day/night, specular, soft terminator) ──────────────────────────────

EARTH_VERT = """
#version 120
varying vec3 vWorldNormal;
varying vec2 vTexCoord;
varying vec3 vWorldPos;
uniform mat4 u_modelRot;
uniform vec3 u_earthPos;
void main() {
    vec4 rot     = u_modelRot * gl_Vertex;
    vWorldPos    = u_earthPos + rot.xyz;
    vWorldNormal = normalize(mat3(u_modelRot) * gl_Normal);
    vTexCoord    = gl_MultiTexCoord0.xy;
    gl_Position  = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

EARTH_FRAG = """
#version 120
uniform sampler2D u_dayTex;
uniform sampler2D u_nightTex;
uniform vec3      u_sunPos;
uniform vec3      u_camPos;
varying vec3 vWorldNormal;
varying vec2 vTexCoord;
varying vec3 vWorldPos;
void main() {
    vec3  N      = normalize(vWorldNormal);
    vec3  sunDir = normalize(u_sunPos - vWorldPos);
    float NdotL  = dot(N, sunDir);

    float dayBlend   = smoothstep(-0.15, 0.20, NdotL);
    float nightBlend = 1.0 - smoothstep(-0.20, 0.15, NdotL);

    vec3 dayCol   = texture2D(u_dayTex,   vTexCoord).rgb;
    vec3 nightCol = texture2D(u_nightTex, vTexCoord).rgb * 1.4;

    vec3  viewDir = normalize(u_camPos - vWorldPos);
    vec3  halfVec = normalize(sunDir + viewDir);
    float spec    = pow(max(dot(N, halfVec), 0.0), 120.0) * max(NdotL, 0.0);

    // Subtle terminator orange glow
    float terminator = smoothstep(-0.08, 0.05, NdotL) * (1.0 - smoothstep(0.05, 0.20, NdotL));

    vec3 color = dayCol * dayBlend + nightCol * nightBlend;
    color += vec3(0.40, 0.60, 1.0) * spec * 0.8;
    color += vec3(1.0, 0.55, 0.2) * terminator * 0.25;
    color += dayCol * 0.03;
    gl_FragColor = vec4(color, 1.0);
}
"""

# ── Generic Phong (planets, moons, 3-D satellite models) ─────────────────────

PHONG_VERT = """
#version 120
varying vec3 vNormal;
varying vec3 vViewPos;
varying vec2 vTexCoord;
void main() {
    vViewPos    = vec3(gl_ModelViewMatrix * gl_Vertex);
    vNormal     = normalize(gl_NormalMatrix * gl_Normal);
    vTexCoord   = gl_MultiTexCoord0.xy;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

PHONG_FRAG = """
#version 120
uniform sampler2D u_tex;
uniform vec3      u_lightDir;
uniform vec3      u_color;
uniform float     u_specPow;
uniform float     u_hasTexture;
uniform float     u_ambientBoost;
varying vec3 vNormal;
varying vec3 vViewPos;
varying vec2 vTexCoord;
void main() {
    vec3  N     = normalize(vNormal);
    vec3  L     = normalize(u_lightDir);
    float NdotL = max(dot(N, L), 0.0);

    vec3 baseCol = (u_hasTexture > 0.5)
                 ? texture2D(u_tex, vTexCoord).rgb
                 : u_color;

    float amb  = 0.06 + u_ambientBoost;
    vec3 color = baseCol * amb + baseCol * NdotL;

    vec3  viewDir = normalize(-vViewPos);
    vec3  halfVec = normalize(L + viewDir);
    float spec    = pow(max(dot(N, halfVec), 0.0), u_specPow) * NdotL;
    color += vec3(spec) * 0.5;

    gl_FragColor = vec4(color, 1.0);
}
"""

# ── Ring disc (Saturn) ────────────────────────────────────────────────────────

RING_VERT = """
#version 120
varying vec2 vTexCoord;
varying vec3 vWorldPos;
void main() {
    vTexCoord   = gl_MultiTexCoord0.xy;
    vWorldPos   = vec3(gl_ModelMatrix * gl_Vertex);
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

# Simplified ring frag — uses only MVP, no extra matrix uniform needed
RING_VERT = """
#version 120
varying vec2 vTexCoord;
void main() {
    vTexCoord   = gl_MultiTexCoord0.xy;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

RING_FRAG = """
#version 120
uniform sampler2D u_ringTex;
uniform float     u_hasTexture;
uniform vec3      u_ringColor;
varying vec2 vTexCoord;
void main() {
    float r = vTexCoord.x;   // 0=inner edge, 1=outer edge
    vec4 texCol = (u_hasTexture > 0.5)
                ? texture2D(u_ringTex, vTexCoord)
                : vec4(u_ringColor, 0.6 * (1.0 - abs(r - 0.5) * 1.5));
    if (texCol.a < 0.02) discard;
    gl_FragColor = texCol;
}
"""

# ── Atmosphere rim-glow ───────────────────────────────────────────────────────

ATMO_VERT = """
#version 120
varying float vRim;
void main() {
    vec3 viewDir = normalize(-vec3(gl_ModelViewMatrix * gl_Vertex));
    vec3 normal  = normalize(gl_NormalMatrix * gl_Normal);
    vRim         = 1.0 - abs(dot(viewDir, normal));
    gl_Position  = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

ATMO_FRAG = """
#version 120
uniform vec3  u_color;
uniform float u_alpha;
varying float vRim;
void main() {
    float glow = pow(vRim, 3.2);
    gl_FragColor = vec4(u_color, glow * u_alpha);
}
"""

# ── Unlit (skybox, sun) ───────────────────────────────────────────────────────

UNLIT_VERT = """
#version 120
varying vec2 vTexCoord;
void main() {
    vTexCoord   = gl_MultiTexCoord0.xy;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

UNLIT_FRAG = """
#version 120
uniform sampler2D u_tex;
uniform vec4      u_color;
uniform float     u_hasTexture;
varying vec2      vTexCoord;
void main() {
    if (u_hasTexture > 0.5)
        gl_FragColor = texture2D(u_tex, vTexCoord) * u_color;
    else
        gl_FragColor = u_color;
}
"""
