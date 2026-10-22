"""Qwen Image 2.1 Prompt Builder node and its editor routes.

Assembles Qwen Image 2.1 prompts from presets for MiniMax H3 video pre-production assets (character
4-view sheets, 3D character cards, environment-only scene cards, product anchors, co-op game menus,
RGBA cutouts). For a short brief, turn on refine_prompt in the official workflow.
"""

import re

from aiohttp import web

from comfy_api.latest import io as cio
from server import PromptServer

from .csrf_guard import require_same_origin


def orientation(width, height):
    if width is None or height is None:
        return ""
    return "wide " if width > height else "vertical " if width < height else "square "


STYLE_PRESETS = {
    "realistic_photo": (
        ("写实摄影", "Realistic Photograph"),
        "photorealistic high-definition",
        "natural surface micro-textures, authentic material grain, crisp structural details, and physically accurate light falloff",
    ),
    "cinematic_film": (
        ("电影级剧照", "Cinematic Film Still"),
        "cinematic anamorphic film-still",
        "rich cinematic color grading, subtle film grain, natural depth of field, and atmospheric spatial depth",
    ),
    "stylized_3d_pixar": (
        ("皮克斯/迪士尼3D动画", "Stylized 3D Animation"),
        "3D-rendered stylized animation",
        "appealing stylized proportions, tactile material shaders, soft global illumination, and physically based surfaces",
    ),
    "eastern_3d_fantasy": (
        ("国风半写实3D动画", "Eastern Semi-Realistic 3D"),
        "semi-realistic 3D-rendered",
        "refined classical Eastern craftsmanship, flowing silk and carved wood textures, subtle metallic sheen, and soft atmospheric shading",
    ),
    "minimalist_product": (
        ("极简商业产品摄影", "Minimalist Commercial Studio"),
        "minimalist editorial commercial",
        "ultra-clean industrial design fidelity, crisp machined edges, controlled specular highlights, and zero-clutter negative space",
    ),
    "paper_collage": (
        ("复古网点纸拼贴", "Halftone Paper Collage"),
        "handcrafted halftone cut-paper collage",
        "visible torn paper edges, vintage newspaper print textures, CMYK halftone dots, and subtle drop shadows between stacked paper layers",
    ),
    "papercraft_diorama": (
        ("立体折纸定格沙盘", "3D Papercraft Diorama"),
        "tactile handmade papercraft diorama",
        "layered cardstock construction, crisp folded creases, matte craft-paper fiber texture, and miniature tabletop stop-motion staging",
    ),
    "handdrawn_live_mix": (
        ("实拍融合发光手绘涂鸦", "Glowing Sketch + Live Action"),
        "hybrid live-action and rough glowing hand-drawn",
        "photorealistic real-world environment contrasted with rough, jittery, luminous neon chalk and colored-pencil sketch lines with visible stroke texture",
    ),
    "coop_game_art": (
        ("风格化游戏概念与UI", "Stylized Game Concept & UI"),
        "stylized video-game key-art",
        "bold readable silhouettes, vibrant color separation, clean UI overlay hierarchy, and expressive game-ready rendering",
    ),
    "anime_cel": (
        ("二次元赛璐璐插画", "2D Anime Illustration"),
        "clean 2D anime cel-shaded",
        "crisp linework, clean cel-shaded shadow planes, detailed background art, and harmonious color blocking",
    ),
    "watercolor_storybook": (
        ("手绘水彩绘本", "Watercolor & Colored Pencil"),
        "hand-painted watercolor and colored-pencil",
        "cold-press cotton paper grain, translucent pigment washes, soft blooming edges, and delicate colored-pencil hatching",
    ),
}

# Qwen Image 2.1 draws whatever the description names, so a framing sentence describes what fills the frame;
# a description that mentions trousers or shoes still turns a bust or waist-up shot into a full-length one.
MEDIUM_SHOT_PRESETS = {
    "auto_by_asset": (("自动 (按资产类型，不另加取景句)", "Auto (by asset type, no framing sentence)"), "image", ""),
    "bust_headroom": (
        ("胸像近景 (胸口以上)", "Bust close-up (chest up)"),
        "chest-up portrait",
        "The subject is framed from the chest up: the head and shoulders fill most of the frame, the face is large and close to the camera, and the bottom edge of the frame crosses the upper chest, with a clear band of background above the hair.",
    ),
    "medium_waist": (
        ("半身中景 (腰部以上)", "Medium shot (waist up)"),
        "waist-up medium shot",
        "The subject is framed from the waist up: the head, shoulders, arms and torso fill the frame, and the bottom edge of the frame crosses the waist.",
    ),
    "full_body": (
        ("全身 (头到脚完整)", "Full body (head to toe)"),
        "full-length shot",
        "The framing is a full-length shot showing the whole figure from the top of the head down to the shoes, with a little space above the head and below the feet.",
    ),
    "wide_establishing": (
        ("广角全景 (环境为主，人物较小)", "Wide establishing (surroundings first, small figure)"),
        "wide establishing shot",
        "The framing is a wide establishing shot: the surroundings fill most of the frame and any figure appears small within the scene.",
    ),
    "macro_closeup": (
        ("微距特写 (材质细节，适合产品/道具)", "Macro close-up (surface detail, for products and props)"),
        "macro close-up",
        "The framing is an extreme close-up that fills the frame with fine surface detail and texture, cropping away everything around it.",
    ),
}

CAMERA_ANGLE_PRESETS = {
    "eye_level": (("平视正拍", "Eye-Level Straight-On"), "captured at a straight-on eye-level camera angle"),
    "three_quarter": (("微侧三分之四视角", "Three-Quarter Angle"), "captured from a balanced three-quarter camera angle"),
    "side_profile": (("正侧面", "Side Profile"), "captured from directly beside the subject, showing the figure in a clean 90-degree side profile facing right"),
    "from_behind": (("背后视角", "From Behind"), "captured from directly behind the subject, showing the back of the head and body, with the face not visible"),
    "low_angle": (("低机位仰拍", "Low-Angle"), "captured from a low camera near knee height looking upward, so the figure rises above the viewer against the sky"),
    "worms_eye": (("贴地极限仰拍", "Worm's-Eye View"), "captured from a worm's-eye view with the camera on the ground looking steeply upward, so the figure towers overhead with strong upward perspective"),
    "high_angle": (("高机位俯拍", "High-Angle Look-Down"), "captured from an elevated high-angle perspective looking slightly downward"),
    "birds_eye": (("高空鸟瞰", "Bird's-Eye Aerial"), "captured from a high aerial bird's-eye view far above the scene, looking down at a steep angle so the figure appears small within the scene below"),
    "top_down": (("垂直俯拍平铺", "Top-Down Flat Lay"), "captured from a direct 90-degree overhead top-down perspective"),
    "dutch_angle": (("倾斜构图", "Dutch Angle"), "captured with a tilted Dutch angle, the whole frame rotated about fifteen degrees so the horizon and vertical lines lean diagonally"),
    "telephoto_dof": (("长焦浅景深", "Telephoto Shallow DOF"), "captured with a medium-telephoto lens with creamy shallow depth of field and soft background bokeh"),
}

# An environment-only scene card must not mention a figure anywhere: the model draws what the prompt names.
# These replace the person-centred wording, and the person-only options are not offered for it.
SCENE_WORDING = {
    "wide_establishing": "The framing is a wide establishing shot: the surroundings fill the whole frame.",
    "low_angle": "captured from a low camera near the ground looking upward, so the architecture and tall features rise above the viewer",
    "worms_eye": "captured from a worm's-eye view with the camera on the ground looking steeply upward, with strong upward perspective",
    "birds_eye": "captured from a high aerial bird's-eye view far above, looking down at a steep angle over the whole scene",
}
PERSON_ONLY = ("bust_headroom", "medium_waist", "full_body", "side_profile", "from_behind")

LIGHTING_PRESETS = {
    "soft_window_left": (
        ("左侧柔和自然窗光", "Soft Diffused Window Light"),
        "The lighting is soft, diffused natural daylight entering from the left side of the frame, casting gentle graduated shadows to the right and warm highlights across surfaces.",
    ),
    "studio_flat": (
        ("均匀无影棚拍光 - 适合四视图/设定卡", "Flat Even Studio Light - for 4-view and character sheets"),
        "The lighting is flat, even, shadowless studio illumination from the front, keeping every surface, colour, and detail clearly legible without dramatic contrast or colour cast.",
    ),
    "golden_hour": (
        ("夕阳暖金逆侧光", "Warm Golden-Hour Rim & Side Light"),
        "The lighting is warm low-angle golden-hour sunlight from the upper right, creating luminous amber highlights and soft warm shadows.",
    ),
    "overcast_diffused": (
        ("阴天漫射柔光 - 适合室外/雨景", "Soft Overcast Daylight - for outdoor and rain scenes"),
        "The lighting is soft, even overcast sky light from above, producing subtle shadow transitions, damp surface reflections, and natural true-to-life tones.",
    ),
    "commercial_rim": (
        ("商业棚拍轮廓光 - 适合极简产品", "Commercial Rim & Key Light - for minimalist products"),
        "The lighting is sculpted studio key light paired with crisp dual rim lights that trace the exact silhouette and material edges, casting a soft grounded contact shadow beneath the base.",
    ),
    "cyber_neon": (
        ("电影感霓虹冷暖对比光", "Cinematic Cyan & Warm Neon"),
        "The lighting combines cool cyan ambient night light with warm amber and magenta neon reflections from the side, creating high-contrast specular highlights on damp surfaces.",
    ),
    "warm_lantern": (
        ("室内暖调灯笼/台灯氛围光", "Warm Indoor Lantern Glow"),
        "The lighting is warm amber tungsten and paper-lantern light radiating from within the room, casting soft inviting highlights and deep tranquil shadows in the far corners.",
    ),
}

ASSET_TYPES = {
    "none": {
        "label": ("📷 通用生图 (不套用特定版式)", "📷 General image (no fixed layout)"),
        "default_medium": "auto_by_asset",
        "default_lighting": "soft_window_left",
        "negative": (
            "low quality, blurry, deformed anatomy, extra fingers, watermark, oversaturated, "
            "garbled text, duplicate subject"
        ),
    },
    "character_4view": {
        "label": ("👤 人物四视图设定卡 (供 H3 <Picture N> 角色锚定)", "👤 Character 4-View Sheet (character anchor for H3 <Picture N>)"),
        "noun": "character reference sheet",
        "default_medium": "auto_by_asset",
        "default_lighting": "studio_flat",
        "negative": (
            "split borders, black dividing lines, grid frames, text labels, letters, watermarks, "
            "cropped head, cropped feet, inconsistent outfit between views, different people, "
            "extra limbs, dramatic dark shadows, cluttered background, low quality, blurry"
        ),
    },
    "scene_empty_card": {
        "label": ("🏠 无人物纯场景空镜卡 (供 H3 场景锚定)", "🏠 Environment-Only Scene Card (scene anchor for H3)"),
        "default_medium": "wide_establishing",
        "default_lighting": "soft_window_left",
        "negative": (
            "people, person, human figure, woman, man, girl, boy, crowd, pedestrians, silhouettes, "
            "hands, limbs, faces, portrait, character sheet, text watermarks, blurry foreground, distorted architecture"
        ),
    },
    "character_3view_card": {
        "label": ("🧒 3D动画带名牌角色三视图卡 (左胸像+右正侧背三视图)", "🧒 3D Character Card (bust on the left, front/side/back views on the right)"),
        "noun": "character design sheet",
        "default_medium": "auto_by_asset",
        "default_lighting": "studio_flat",
        "negative": (
            "inconsistent clothing across views, cropped feet, cropped head, cluttered background, "
            "harsh shadows, extra characters, deformed hands, unreadable garbled text"
        ),
    },
    "product_anchor": {
        "label": ("💎 极简商业产品锚点图 (主视觉/微距材质/英文标题)", "💎 Minimalist Product Anchor (key visual, macro texture, English title)"),
        "default_medium": "macro_closeup",
        "default_lighting": "commercial_rim",
        "negative": (
            "cluttered background, human hands, distorted product geometry, warped logo, "
            "messy reflections, cheap plastic look, misspelled text"
        ),
    },
    "coop_game_menu": {
        "label": ("🎮 双人合作游戏开场菜单图 (左右双角色+1P/2P状态卡+中央UI)", "🎮 Co-op Game Menu (two characters, 1P/2P status cards, centre UI)"),
        "noun": "video game menu screen",
        "default_medium": "auto_by_asset",
        "default_lighting": "cyber_neon",
        "negative": (
            "missing second character, merged bodies, garbled UI text, crooked buttons, "
            "muddy colors, cropped heads, watermark"
        ),
    },
    "rgba_cutout_asset": {
        "label": ("🔲 RGBA 透明背景独立资产 (Alpha 通道抠图)", "🔲 RGBA Transparent Cutout (prop or character with alpha channel)"),
        "default_medium": "full_body",
        "default_lighting": "studio_flat",
        "negative": (
            "solid background, room interior, landscape background, checkerboard pattern painted as pixels, "
            "cropped edges, heavy drop shadow on wall, blurry silhouette"
        ),
    },
}


def _clean_sentence(text):
    s = (text or "").strip()
    if not s:
        return ""
    return s.rstrip(".。").strip()


def build_direct_prompt(
    asset_type,
    width,
    height,
    style_preset,
    medium_shot,
    camera_angle,
    lighting_preset,
    subject,
):
    """Assemble a single-paragraph Qwen Image 2.1 prompt from the selected presets."""
    _, style_adj, style_surface = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["realistic_photo"])
    asset_info = ASSET_TYPES.get(asset_type, ASSET_TYPES["none"])

    no_people = asset_type == "scene_empty_card"
    if no_people:
        # A saved workflow can still hold a person-only choice from before the asset type was switched.
        medium_shot = "auto_by_asset" if medium_shot in PERSON_ONLY else medium_shot
        camera_angle = "eye_level" if camera_angle in PERSON_ONLY else camera_angle
    medium_key = asset_info["default_medium"] if medium_shot == "auto_by_asset" else medium_shot
    _, medium_noun, framing_sentence = MEDIUM_SHOT_PRESETS.get(medium_key, MEDIUM_SHOT_PRESETS["auto_by_asset"])
    if medium_key == "auto_by_asset":
        medium_noun = asset_info.get("noun", medium_noun)
    _, angle_clause = CAMERA_ANGLE_PRESETS.get(camera_angle, CAMERA_ANGLE_PRESETS["eye_level"])
    if no_people:
        framing_sentence = SCENE_WORDING.get(medium_key, framing_sentence)
        angle_clause = SCENE_WORDING.get(camera_angle, angle_clause)
    _, lighting_sentence = LIGHTING_PRESETS.get(
        lighting_preset, LIGHTING_PRESETS[asset_info.get("default_lighting", "soft_window_left")]
    )

    subj_clean = _clean_sentence(subject) or "a clearly defined subject or environment positioned in the frame"

    # Rules that belong to the asset type; on-off switches for ordinary frames showed no visible effect.
    rules = []
    if asset_type == "scene_empty_card":
        rules.append("The scene is completely uninhabited with zero people, zero human figures, zero silhouettes, and zero body parts anywhere in the frame.")
    elif asset_type in ("character_4view", "character_3view_card"):
        rules.append("All panels depict the exact same single character with identical facial structure, hairstyle, and outfit, with no border lines and no extra figures.")
        rules.append("Every panel keeps the entire head, hair, headwear, and shoes completely inside the top and bottom edges of the frame with clear margin above the crown and below the soles.")

    opening_bg = "set against a clean, well-structured environment"
    if asset_type == "character_4view":
        opening_bg = (
            "set on a plain off-white background (#F5F4F0) arranged as four equal-height side-by-side vertical panels with no dividing border lines"
        )
    elif asset_type == "character_3view_card":
        opening_bg = (
            "set on a solid neutral medium-grey studio background (#7A7A7A) combining a left close-up bust portrait and three full-body turnaround views on the right"
        )
    elif asset_type == "scene_empty_card":
        opening_bg = "depicting an uninhabited environment with clear foreground, midground, and background spatial depth"
    elif asset_type == "rgba_cutout_asset":
        opening_bg = "isolated cleanly in the centre of the frame with crisp outer edges"

    opening = f"The image is a {orientation(width, height)}{style_adj} {medium_noun} of {subj_clean}, {opening_bg}, {angle_clause}."

    body_sentences = [framing_sentence]
    if asset_type == "character_4view":
        body_sentences.append(
            "On the far left panel is a large front head-and-shoulders close-up portrait from the chest to above the top of the hair; "
            "the second panel shows a full-body standing front view; the third panel shows a full-body standing 90-degree side profile view facing right; "
            "and the fourth panel on the far right shows a full-body standing back view, with panels two, three, and four standing on the exact same horizontal baseline at identical head-to-foot scale."
        )
        body_sentences.append("No text, labels, letters, or dividing grid lines appear anywhere in the frame.")
    elif asset_type == "scene_empty_card":
        body_sentences.append(
            "In the foreground along the left and right edges, architectural framing elements establish depth; "
            "across the centre midground, an open, uncluttered floor and furniture arrangement provides a clean staging area; "
            "and across the background, walls, windows, and environmental details complete the spatial layout."
        )

    body_sentences.append(f"Throughout the frame, surfaces display {style_surface}.")

    body_sentences.extend(rules)

    closing_sentence = (
        f"The overall composition is balanced and spatially coherent, combining {style_adj} fidelity with clear foreground-to-background separation."
    )
    paragraph = " ".join(p for p in [opening, *body_sentences, lighting_sentence, closing_sentence] if p)

    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    if asset_type == "rgba_cutout_asset":
        paragraph = f"This is an RGBA format image with transparency. {paragraph} The image has an alpha channel and a transparent background."
    return paragraph


def register_qwen21_routes():
    """Register local HTTP routes for the Qwen Image 2.1 Prompt Builder editor."""
    server = getattr(PromptServer, "instance", None)
    if server is None or getattr(register_qwen21_routes, "_done", False):
        return

    @server.routes.get("/h3_motion_context/qwen21_catalog")
    async def get_qwen21_catalog(request):
        return web.json_response({
            "asset_types": {
                k: {
                    "label": v["label"],
                    "default_medium": v["default_medium"],
                    "default_lighting": v["default_lighting"],
                    "no_people": k == "scene_empty_card",
                }
                for k, v in ASSET_TYPES.items()
            },
            "person_only": PERSON_ONLY,
            "style_presets": {k: {"label": v[0]} for k, v in STYLE_PRESETS.items()},
            "medium_shots": {k: {"label": v[0]} for k, v in MEDIUM_SHOT_PRESETS.items()},
            "camera_angles": {k: {"label": v[0]} for k, v in CAMERA_ANGLE_PRESETS.items()},
            "lighting_presets": {k: {"label": v[0]} for k, v in LIGHTING_PRESETS.items()},
        })

    @server.routes.post("/h3_motion_context/qwen21_assemble")
    @require_same_origin
    async def post_qwen21_assemble(request):
        data = await request.json()
        asset_type = data.get("asset_type", "character_4view")
        if asset_type not in ASSET_TYPES:
            asset_type = "character_4view"
        # The editor sends the linked size when it can read it; otherwise the preview leaves out the orientation word.
        width, height = data.get("width"), data.get("height")
        prompt = build_direct_prompt(
            asset_type,
            width,
            height,
            data.get("style_preset", "realistic_photo"),
            data.get("medium_shot", "auto_by_asset"),
            data.get("camera_angle", "eye_level"),
            data.get("lighting_preset", "studio_flat"),
            data.get("subject", ""),
        )
        return web.json_response({"prompt": prompt, "negative_prompt": ASSET_TYPES[asset_type]["negative"]})

    register_qwen21_routes._done = True


class QwenImage21VideoPrompt(cio.ComfyNode):
    @classmethod
    def define_schema(cls):
        return cio.Schema(
            node_id="QwenImage21VideoPrompt",
            display_name="Qwen Image 2.1 Prompt Builder",
            category="video/minimax",
            description=(
                "Assemble Qwen Image 2.1 prompts for MiniMax H3 video pre-production "
                "(character 4-view sheets, 3D character cards, empty scene cards, "
                "product anchors, RGBA cutouts). For a short brief, enable "
                "refine_prompt in the Qwen Image 2.1 workflow."
            ),
            inputs=[
                cio.Combo.Input(
                    "asset_type",
                    options=list(ASSET_TYPES.keys()),
                    default="character_4view",
                    tooltip="Image asset type; each type applies its own layout rules.",
                ),
                cio.Int.Input("width", force_input=True, tooltip="width from Resolution Selector, passed unchanged to the width output. The prompt names the frame wide when width is larger."),
                cio.Int.Input("height", force_input=True, tooltip="height from Resolution Selector. The prompt names the frame vertical when height is larger, square when equal."),
                cio.Combo.Input(
                    "style_preset",
                    options=list(STYLE_PRESETS.keys()),
                    default="realistic_photo",
                    tooltip="Visual style (photograph, film still, stylized 3D, Eastern 3D, product, paper collage, papercraft and more).",
                ),
                cio.Combo.Input("medium_shot", options=list(MEDIUM_SHOT_PRESETS.keys()), default="auto_by_asset", tooltip="Shot size. For a bust or waist-up shot, leave trousers and shoes out of the description, or the image comes out full-length."),
                cio.Combo.Input("camera_angle", options=list(CAMERA_ANGLE_PRESETS.keys()), default="eye_level", tooltip="Camera angle."),
                cio.Combo.Input("lighting_preset", options=list(LIGHTING_PRESETS.keys()), default="studio_flat", tooltip="Lighting sentence preset."),
                cio.String.Input("subject", default="", multiline=True, placeholder="Describe the person or scene to generate"),
                cio.Boolean.Input("manual_prompt", default=False, tooltip="Output final_prompt as-is. Turned on automatically when the preview is edited by hand."),
                cio.String.Input("final_prompt", default="", multiline=True, placeholder="Prompt preview; edit to adjust by hand"),
            ],
            outputs=[
                cio.String.Output(display_name="prompt"),
                cio.String.Output(display_name="negative_prompt"),
                cio.Int.Output(display_name="width"),
                cio.Int.Output(display_name="height"),
            ],
        )

    @classmethod
    def execute(cls, asset_type, width, height, style_preset, medium_shot, camera_angle, lighting_preset,
                subject,
                manual_prompt, final_prompt):
        if asset_type not in ASSET_TYPES:
            asset_type = "character_4view"
        if manual_prompt and final_prompt.strip():
            prompt = final_prompt.strip()
        else:
            prompt = build_direct_prompt(
                asset_type, width, height, style_preset, medium_shot, camera_angle, lighting_preset,
                subject,
            )
        return cio.NodeOutput(prompt, ASSET_TYPES[asset_type]["negative"], width, height)


NODE_CLASS_MAPPINGS = {"QwenImage21VideoPrompt": QwenImage21VideoPrompt}
NODE_DISPLAY_NAME_MAPPINGS = {"QwenImage21VideoPrompt": "Qwen Image 2.1 Prompt Builder"}
