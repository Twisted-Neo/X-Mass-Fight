"""GPU multi-pass Bloom post-processor for Arcade 3.x."""

from contextlib import contextmanager
import arcade
from arcade.gl import geometry

import config
from config import WINDOW_HEIGHT, WINDOW_WIDTH

_VERT_SHADER = """
#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 uv;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    uv = in_uv;
}
"""

_BRIGHT_PASS_FRAG = """
#version 330
uniform sampler2D u_scene;
uniform float u_threshold;
uniform float u_knee;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec3 col = texture(u_scene, uv).rgb;
    float luma = dot(col, vec3(0.2126, 0.7152, 0.0722));
    float peak = max(col.r, max(col.g, col.b));
    float brightness = mix(luma, peak, 0.55);

    float soft = brightness - u_threshold + u_knee;
    soft = clamp(soft, 0.0, 2.0 * u_knee);
    soft = (soft * soft) / max(4.0 * u_knee, 0.0001);

    float contrib = max(soft, brightness - u_threshold) / max(brightness, 0.0001);
    contrib = clamp(contrib, 0.0, 1.0);
    fragColor = vec4(col * contrib, 1.0);
}
"""

_BLUR_FRAG = """
#version 330
uniform sampler2D u_tex;
uniform vec2 u_direction;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_tex, 0));
    vec2 step_uv = u_direction * texel;

    vec3 result = texture(u_tex, uv).rgb * 0.2270270270;
    result += texture(u_tex, uv + step_uv * 1.3846153846).rgb * 0.3162162162;
    result += texture(u_tex, uv - step_uv * 1.3846153846).rgb * 0.3162162162;
    result += texture(u_tex, uv + step_uv * 3.2307692308).rgb * 0.0702702703;
    result += texture(u_tex, uv - step_uv * 3.2307692308).rgb * 0.0702702703;

    fragColor = vec4(result, 1.0);
}
"""

_COMPOSITE_FRAG = """
#version 330
uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_intensity;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec3 base_col = texture(u_scene, uv).rgb;
    vec3 glow_col = texture(u_bloom, uv).rgb * u_intensity;
    // Soft highlight roll-off so intense overlapping effects don't clip harshly
    vec3 combined = base_col + glow_col * (1.0 - base_col * 0.22);
    fragColor = vec4(clamp(combined, 0.0, 1.0), 1.0);
}
"""


class BloomRenderer:
    """Offscreen virtual-resolution FBO + separable Gaussian bloom post-processor."""

    def __init__(self, ctx: arcade.ArcadeContext):
        self.ctx = ctx
        self.available = False
        self._capturing = False

        try:
            self.quad = geometry.quad_2d_fs()
            self.prog_bright = ctx.program(vertex_shader=_VERT_SHADER, fragment_shader=_BRIGHT_PASS_FRAG)
            self.prog_blur = ctx.program(vertex_shader=_VERT_SHADER, fragment_shader=_BLUR_FRAG)
            self.prog_comp = ctx.program(vertex_shader=_VERT_SHADER, fragment_shader=_COMPOSITE_FRAG)

            self.scene_tex = ctx.texture(
                (WINDOW_WIDTH, WINDOW_HEIGHT),
                components=4,
                dtype="f1",
                filter=(ctx.LINEAR, ctx.LINEAR),
                wrap_x=ctx.CLAMP_TO_EDGE,
                wrap_y=ctx.CLAMP_TO_EDGE,
            )
            self.scene_fbo = ctx.framebuffer(color_attachments=[self.scene_tex])

            bw = max(1, WINDOW_WIDTH // 4)
            bh = max(1, WINDOW_HEIGHT // 4)
            self.blur_tex_a = ctx.texture(
                (bw, bh),
                components=4,
                dtype="f1",
                filter=(ctx.LINEAR, ctx.LINEAR),
                wrap_x=ctx.CLAMP_TO_EDGE,
                wrap_y=ctx.CLAMP_TO_EDGE,
            )
            self.blur_tex_b = ctx.texture(
                (bw, bh),
                components=4,
                dtype="f1",
                filter=(ctx.LINEAR, ctx.LINEAR),
                wrap_x=ctx.CLAMP_TO_EDGE,
                wrap_y=ctx.CLAMP_TO_EDGE,
            )
            self.blur_fbo_a = ctx.framebuffer(color_attachments=[self.blur_tex_a])
            self.blur_fbo_b = ctx.framebuffer(color_attachments=[self.blur_tex_b])

            self.prog_bright["u_scene"] = 0
            self.prog_blur["u_tex"] = 0
            self.prog_comp["u_scene"] = 0
            self.prog_comp["u_bloom"] = 1
            self.available = True
        except Exception:
            self.available = False

    @contextmanager
    def capture(self):
        """Captures subsequent draw calls into the 1920x1080 virtual scene FBO."""
        if not self.available:
            self._capturing = False
            yield False
            return

        self._capturing = True
        with self.scene_fbo:
            self.scene_fbo.clear(color=(0, 0, 0, 255))
            yield True
        self._capturing = False

    def render(self):
        """Extracts bright highlights, blurs them, and composites onto the active viewport."""
        if not self.available:
            return

        threshold = float(getattr(config, "BLOOM_THRESHOLD", 0.62))
        knee = float(getattr(config, "BLOOM_KNEE", 0.22))
        intensity = float(getattr(config, "BLOOM_INTENSITY", 0.68))

        self.ctx.disable(self.ctx.BLEND)
        try:
            # 1. Bright-pass downsample -> blur_fbo_a
            self.prog_bright["u_threshold"] = threshold
            self.prog_bright["u_knee"] = knee
            with self.blur_fbo_a:
                self.scene_tex.use(0)
                self.quad.render(self.prog_bright)

            # 2. Dual-iteration separable 9-tap Gaussian blur
            for spread in (1.0, 1.85):
                self.prog_blur["u_direction"] = (spread, 0.0)
                with self.blur_fbo_b:
                    self.blur_tex_a.use(0)
                    self.quad.render(self.prog_blur)

                self.prog_blur["u_direction"] = (0.0, spread)
                with self.blur_fbo_a:
                    self.blur_tex_b.use(0)
                    self.quad.render(self.prog_blur)

            # 3. Composite scene + bloom into the active target framebuffer & viewport
            self.prog_comp["u_intensity"] = intensity
            self.scene_tex.use(0)
            self.blur_tex_a.use(1)
            self.quad.render(self.prog_comp)
        finally:
            self.ctx.enable(self.ctx.BLEND)
            self.ctx.blend_func = self.ctx.BLEND_DEFAULT


def get_bloom_renderer(window: arcade.Window | None) -> BloomRenderer | None:
    """Returns a cached BloomRenderer attached to the Arcade window."""
    if window is None:
        return None
    renderer = getattr(window, "_bloom_renderer", None)
    if renderer is None:
        renderer = BloomRenderer(window.ctx)
        window._bloom_renderer = renderer
    return renderer