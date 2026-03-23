"""
shaders.py — GLSL shader source strings + compile/link utilities.
All shaders target GLSL 1.20 (OpenGL 2.1 compatibility profile).
"""
from OpenGL.GL import *


# ── Utility ───────────────────────────────────────────────────────────────────

def _compile(src: str, shader_type) -> int:
    shader = glCreateShader(shader_type)
    glShaderSource(shader, src)
    glCompileShader(shader)
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        raise RuntimeError(f"Shader compile error:\n{glGetShaderInfoLog(shader).decode()}")
    return shader


def link_program(vert_src: str, frag_src: str) -> int:
    vert = _compile(vert_src, GL_VERTEX_SHADER)
    frag = _compile(frag_src, GL_FRAGMENT_SHADER)
    prog = glCreateProgram()
    glAttachShader(prog, vert)
    glAttachShader(prog, frag)
    glLinkProgram(prog)
    if not glGetProgramiv(prog, GL_LINK_STATUS):
        raise RuntimeError(f"Program link error:\n{glGetProgramInfoLog(prog).decode()}")
    glDeleteShader(vert)
    glDeleteShader(frag)
    return prog


# ── Earth Shader (day/night blend + specular) ─────────────────────────────────

EARTH_VERT = """
#version 120
varying vec3 vWorldNormal;
varying vec2 vTexCoord;
varying vec3 vWorldPos;

uniform mat4  u_modelRot;   // earth rotation matrix (3×3 in 4×4 wrapper)
uniform vec3  u_earthPos;   // earth world-space position

void main() {
    // World position = earth_pos + rotated vertex
    vec4 rotated  = u_modelRot * gl_Vertex;
    vWorldPos     = u_earthPos + rotated.xyz;
    vWorldNormal  = normalize(mat3(u_modelRot) * gl_Normal);
    vTexCoord     = gl_MultiTexCoord0.xy;
    gl_Position   = gl_ProjectionMatrix * gl_ModelViewMatrix * gl_Vertex;
}
"""

EARTH_FRAG = """
#version 120
uniform sampler2D u_dayTex;
uniform sampler2D u_nightTex;
uniform vec3      u_sunPos;      // world space sun position
uniform vec3      u_camPos;      // world space camera position

varying vec3 vWorldNormal;
varying vec2 vTexCoord;
varying vec3 vWorldPos;

void main() {
    vec3  N       = normalize(vWorldNormal);
    vec3  sunDir  = normalize(u_sunPos - vWorldPos);
    float NdotL   = dot(N, sunDir);

    // Day / night blend with soft terminator
    float dayBlend   = smoothstep(-0.12, 0.18, NdotL);
    float nightBlend = 1.0 - smoothstep(-0.18, 0.12, NdotL);

    vec3 dayCol   = texture2D(u_dayTex,   vTexCoord).rgb;
    vec3 nightCol = texture2D(u_nightTex, vTexCoord).rgb;

    // Specular highlight (ocean glint)
    vec3  viewDir = normalize(u_camPos - vWorldPos);
    vec3  halfVec = normalize(sunDir + viewDir);
    float spec    = pow(max(dot(N, halfVec), 0.0), 90.0) * max(NdotL, 0.0);

    vec3 color = dayCol * dayBlend + nightCol * nightBlend;
    color += vec3(0.45, 0.65, 1.0) * spec * 0.7;  // blue-white ocean shimmer
    color += dayCol * 0.04;                         // minimal ambient

    gl_FragColor = vec4(color, 1.0);
}
"""

# ── Simple Phong Shader (Moon, satellites) ───────────────────────────────────

PHONG_VERT = """
#version 120
varying vec3 vNormal;
varying vec3 vViewPos;

void main() {
    vViewPos    = vec3(gl_ModelViewMatrix * gl_Vertex);
    vNormal     = normalize(gl_NormalMatrix * gl_Normal);
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    gl_TexCoord[0] = gl_MultiTexCoord0;
}
"""

PHONG_FRAG = """
#version 120
uniform sampler2D u_tex;
uniform vec3      u_lightDir;    // eye-space light direction
uniform vec3      u_color;       // fallback tint when no texture
uniform float     u_specPow;     // specular exponent
uniform float     u_hasTexture;  // 1.0 = use texture, 0.0 = use u_color

varying vec3 vNormal;
varying vec3 vViewPos;

void main() {
    vec3 N = normalize(vNormal);
    vec3 L = normalize(u_lightDir);
    float NdotL = max(dot(N, L), 0.0);

    vec3 baseCol = (u_hasTexture > 0.5)
                 ? texture2D(u_tex, gl_TexCoord[0].xy).rgb
                 : u_color;

    vec3 ambient  = baseCol * 0.06;
    vec3 diffuse  = baseCol * NdotL;

    vec3 viewDir  = normalize(-vViewPos);
    vec3 halfVec  = normalize(L + viewDir);
    float spec    = pow(max(dot(N, halfVec), 0.0), u_specPow) * NdotL;
    vec3 specular = vec3(spec) * 0.6;

    gl_FragColor = vec4(ambient + diffuse + specular, 1.0);
}
"""

# ── Unlit Shader (skybox, sun glow rings) ────────────────────────────────────

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

# ── Atmosphere Glow (additive, rim-lighting) ──────────────────────────────────

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
    float glow = pow(vRim, 3.5);
    gl_FragColor = vec4(u_color, glow * u_alpha);
}
"""
