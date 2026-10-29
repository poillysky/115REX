<script setup lang="ts">
// 品牌 Logo（双环 R），字形与渐变完全取自 RexHub_Brand_Kit_v3/assets/brand。
// 唯一来源，页面不得另画一份。
// tile=true  → App 图标形态：渐变圆角方块 + 白色字形（用于登录、favicon 尺寸场景）
// tile=false → 独立符号：渐变字形本身（用于浅底页头）
import { useId } from 'vue'

withDefaults(
  defineProps<{
    size?: number
    tile?: boolean
  }>(),
  { size: 44, tile: false },
)

// 同页多处使用，渐变 id 必须唯一，否则后出现的会引用到第一个的 id
const uid = useId()
const band = `rex-band-${uid}`
const tileGradient = `rex-tile-${uid}`
const tileSheen = `rex-tile-sheen-${uid}`

// Brand Kit 原始路径坐标系：字形实际包围盒 x 75→381、y 52→361，画布 440×420 本身偏右上。
const GLYPH_BOX = { x: 75, y: 52, w: 306, h: 309 }

// 图标形态：字形缩放到方块内 62% 宽高，并让包围盒中心落在 256,256
const TILE = 512
const TILE_GLYPH_SCALE = (TILE * 0.62) / GLYPH_BOX.w
const TILE_GLYPH_TRANSFORM = `translate(${
  TILE / 2 - (GLYPH_BOX.x + GLYPH_BOX.w / 2) * TILE_GLYPH_SCALE
} ${TILE / 2 - (GLYPH_BOX.y + GLYPH_BOX.h / 2) * TILE_GLYPH_SCALE}) scale(${TILE_GLYPH_SCALE})`
</script>

<template>
  <svg
    v-if="!tile"
    class="logo"
    :width="size * (GLYPH_BOX.w / GLYPH_BOX.h)"
    :height="size"
    :style="{ width: `${size * (GLYPH_BOX.w / GLYPH_BOX.h)}px`, height: `${size}px` }"
    :viewBox="`${GLYPH_BOX.x} ${GLYPH_BOX.y} ${GLYPH_BOX.w} ${GLYPH_BOX.h}`"
    role="img"
    aria-label="115REX"
  >
    <defs>
      <linearGradient :id="band" x1="68" y1="70" x2="390" y2="370" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="var(--brand-g1)" />
        <stop offset=".36" stop-color="var(--brand-g2)" />
        <stop offset=".67" stop-color="var(--brand-g3)" />
        <stop offset="1" stop-color="var(--brand-g4)" />
      </linearGradient>
    </defs>
    <g :fill="`url(#${band})`" stroke-linejoin="round">
      <path
        d="M92 82
           C92 65 106 52 124 52
           H263
           C321 52 357 88 357 140
           C357 178 339 207 309 222
           L284 234
           L372 337
           C381 348 375 361 360 361
           H316
           C306 361 300 356 293 348
           L217 265
           C206 253 209 239 222 229
           L251 212
           C270 200 276 188 276 172
           C276 155 264 145 244 145
           H100
           C94 145 92 139 92 131 Z"
      />
      <path
        d="M135 174
           C160 162 190 165 205 177
           C212 183 210 190 202 198
           L171 229
           C160 241 163 253 175 264
           L260 347
           C269 356 263 361 251 361
           H164
           C125 361 91 338 75 303
           C56 263 69 224 96 197
           C107 186 120 178 135 174 Z"
      />
    </g>
  </svg>

  <!-- App 图标形态：512 坐标系，底衬 10pt 内边距、rx=116，字形整体 scale 1.13 居中 -->
  <svg
    v-else
    class="logo logo--tile"
    :width="size"
    :height="size"
    :style="{ width: `${size}px`, height: `${size}px` }"
    viewBox="0 0 512 512"
    role="img"
    aria-label="115REX"
  >
    <defs>
      <linearGradient :id="tileGradient" x1="70" y1="35" x2="440" y2="480" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="var(--brand-g1)" />
        <stop offset=".48" stop-color="var(--brand-g2)" />
        <stop offset="1" stop-color="var(--brand-g4)" />
      </linearGradient>
      <linearGradient :id="tileSheen" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#FFFFFF" stop-opacity=".22" />
        <stop offset=".55" stop-color="#FFFFFF" stop-opacity="0" />
      </linearGradient>
    </defs>
    <rect x="10" y="10" width="492" height="492" rx="116" :fill="`url(#${tileGradient})`" />
    <rect x="10" y="10" width="492" height="492" rx="116" :fill="`url(#${tileSheen})`" />
    <g :transform="TILE_GLYPH_TRANSFORM" fill="#FFFFFF" stroke-linejoin="round">
      <path
        d="M92 82
           C92 65 106 52 124 52
           H263
           C321 52 357 88 357 140
           C357 178 339 207 309 222
           L284 234
           L372 337
           C381 348 375 361 360 361
           H316
           C306 361 300 356 293 348
           L217 265
           C206 253 209 239 222 229
           L251 212
           C270 200 276 188 276 172
           C276 155 264 145 244 145
           H100
           C94 145 92 139 92 131 Z"
      />
      <path
        d="M135 174
           C160 162 190 165 205 177
           C212 183 210 190 202 198
           L171 229
           C160 241 163 253 175 264
           L260 347
           C269 356 263 361 251 361
           H164
           C125 361 91 338 75 303
           C56 263 69 224 96 197
           C107 186 120 178 135 174 Z"
      />
    </g>
  </svg>
</template>

<style scoped>
.logo {
  display: block;
  flex: none;
  /* 顶栏是 flex 容器，不加这两条会被拉伸成非等比 */
  overflow: visible;
  height: auto;
  max-width: none;
}

/* Logo 不加投影 / 外发光（docs/09 §5）；方块形态靠底板本身识别 */
.logo--tile {
  filter: none;
}
</style>
