// 最小 QR 码编码器（字节模式，纠错等级 M，版本 1–10）。
// 只服务「把 115 扫码链接渲染成图」这一个场景：不引入外部依赖，输出模块矩阵。
// 算法照 ISO/IEC 18004：数据编码 → 分块 RS 纠错 → 交织 → 布图 → 掩码择优。

/** 每个版本的 RS 分块结构（纠错等级 M）：每块纠错码字数与各块数据码字数。 */
const BLOCKS_M: Record<number, { ecc: number; data: number[] }> = {
  1: { ecc: 10, data: [16] },
  2: { ecc: 16, data: [28] },
  3: { ecc: 26, data: [44] },
  4: { ecc: 18, data: [32, 32] },
  5: { ecc: 24, data: [43, 43] },
  6: { ecc: 16, data: [27, 27, 27, 27] },
  7: { ecc: 18, data: [31, 31, 31, 31] },
  8: { ecc: 22, data: [38, 38, 39, 39] },
  9: { ecc: 22, data: [36, 36, 36, 37, 37] },
  10: { ecc: 26, data: [43, 43, 43, 43, 44] },
}

/** 对齐图形中心坐标（版本 1 没有）。 */
const ALIGN_POSITIONS: Record<number, number[]> = {
  1: [],
  2: [6, 18],
  3: [6, 22],
  4: [6, 26],
  5: [6, 30],
  6: [6, 34],
  7: [6, 22, 38],
  8: [6, 24, 42],
  9: [6, 26, 46],
  10: [6, 28, 50],
}

/** 版本信息块（版本 ≥ 7 才画）。 */
const VERSION_BITS: Record<number, number> = {
  7: 0x07c94,
  8: 0x085bc,
  9: 0x09a99,
  10: 0x0a4d3,
}

const MAX_VERSION = 10

function totalDataCodewords(version: number): number {
  return BLOCKS_M[version].data.reduce((sum, count) => sum + count, 0)
}

/** 字节模式可容纳的字符数：扣掉模式指示与字符计数。 */
function capacityBytes(version: number): number {
  const headerBits = 4 + (version < 10 ? 8 : 16)
  return Math.floor((totalDataCodewords(version) * 8 - headerBits) / 8)
}

function gfMultiply(a: number, b: number): number {
  let result = 0
  for (let i = 7; i >= 0; i--) {
    result = ((result << 1) ^ ((result >> 7) * 0x11d)) & 0xff
    if ((b >> i) & 1) result ^= a
  }
  return result
}

function rsGeneratorPoly(degree: number): number[] {
  let poly = [1]
  // 乘数依次是 α^0、α^1 …；必须走 GF 乘法，`1 << i` 在 i ≥ 8 时会溢出 8 位域
  let root = 1
  for (let i = 0; i < degree; i++) {
    const next = new Array<number>(poly.length + 1).fill(0)
    for (let j = 0; j < poly.length; j++) {
      next[j] ^= poly[j]
      next[j + 1] ^= gfMultiply(poly[j], root)
    }
    poly = next
    root = gfMultiply(root, 2)
  }
  return poly
}

function rsRemainder(data: number[], degree: number): number[] {
  const generator = rsGeneratorPoly(degree)
  const result = new Array<number>(degree).fill(0)
  for (const byte of data) {
    const factor = byte ^ result[0]
    result.shift()
    result.push(0)
    for (let i = 0; i < degree; i++) result[i] ^= gfMultiply(generator[i + 1], factor)
  }
  return result
}

/** 字节模式编码：模式指示 + 字符计数 + 数据 + 结束符 + 填充。 */
function encodeData(text: string, version: number): number[] {
  const bytes = Array.from(new TextEncoder().encode(text))
  const bits: number[] = []
  const push = (value: number, length: number) => {
    for (let i = length - 1; i >= 0; i--) bits.push((value >> i) & 1)
  }
  push(0b0100, 4)
  push(bytes.length, version < 10 ? 8 : 16)
  for (const byte of bytes) push(byte, 8)

  const capacityBits = totalDataCodewords(version) * 8
  push(0, Math.min(4, capacityBits - bits.length))
  while (bits.length % 8 !== 0) bits.push(0)

  const codewords: number[] = []
  for (let i = 0; i < bits.length; i += 8) {
    let value = 0
    for (let j = 0; j < 8; j++) value = (value << 1) | bits[i + j]
    codewords.push(value)
  }
  // 填充码字在 0xEC / 0x11 之间交替
  for (let pad = 0xec; codewords.length < totalDataCodewords(version); pad ^= 0xec ^ 0x11) {
    codewords.push(pad)
  }
  return codewords
}

/** 交织数据码字与纠错码字，得到最终码字流。 */
function interleave(codewords: number[], version: number): number[] {
  const { ecc, data: sizes } = BLOCKS_M[version]
  const blocks: { data: number[]; ecc: number[] }[] = []
  let offset = 0
  for (const size of sizes) {
    const data = codewords.slice(offset, offset + size)
    offset += size
    blocks.push({ data, ecc: rsRemainder(data, ecc) })
  }

  const result: number[] = []
  const maxData = Math.max(...blocks.map((block) => block.data.length))
  for (let i = 0; i < maxData; i++) {
    for (const block of blocks) if (i < block.data.length) result.push(block.data[i])
  }
  for (let i = 0; i < ecc; i++) {
    for (const block of blocks) result.push(block.ecc[i])
  }
  return result
}

const MASKS: ((r: number, c: number) => boolean)[] = [
  (r, c) => (r + c) % 2 === 0,
  (r) => r % 2 === 0,
  (_r, c) => c % 3 === 0,
  (r, c) => (r + c) % 3 === 0,
  (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
  (r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
  (r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
  (r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
]

/** 格式信息：纠错等级 M（0b00）+ 掩码号，BCH(15,5) + 固定掩码。 */
function formatBits(maskIndex: number): number {
  const data = (0b00 << 3) | maskIndex
  let remainder = data
  for (let i = 0; i < 10; i++) remainder = (remainder << 1) ^ ((remainder >> 9) * 0x537)
  return ((data << 10) | remainder) ^ 0x5412
}

/** 掩码惩罚分，取最低者。 */
function penalty(modules: boolean[][], size: number): number {
  let score = 0

  for (let r = 0; r < size; r++) {
    let run = 1
    for (let c = 1; c < size; c++) {
      if (modules[r][c] === modules[r][c - 1]) {
        run++
        if (run === 5) score += 3
        else if (run > 5) score++
      } else run = 1
    }
  }
  for (let c = 0; c < size; c++) {
    let run = 1
    for (let r = 1; r < size; r++) {
      if (modules[r][c] === modules[r - 1][c]) {
        run++
        if (run === 5) score += 3
        else if (run > 5) score++
      } else run = 1
    }
  }
  for (let r = 0; r < size - 1; r++) {
    for (let c = 0; c < size - 1; c++) {
      const color = modules[r][c]
      if (
        color === modules[r][c + 1] &&
        color === modules[r + 1][c] &&
        color === modules[r + 1][c + 1]
      ) {
        score += 3
      }
    }
  }
  let dark = 0
  for (const row of modules) for (const cell of row) if (cell) dark++
  score += Math.floor(Math.abs((dark * 100) / (size * size) - 50) / 5) * 10
  return score
}

/**
 * 格式信息的 30 个位置，顺序与 bits 的位号一一对应：
 * 前 15 位环绕左上定位图形，后 15 位分列右上与左下。
 */
function formatPositions(size: number): [number, number][] {
  const positions: [number, number][] = []
  for (let i = 0; i <= 5; i++) positions.push([i, 8])
  positions.push([7, 8])
  positions.push([8, 8])
  positions.push([8, 7])
  for (let i = 9; i <= 14; i++) positions.push([8, 14 - i])
  for (let i = 0; i <= 7; i++) positions.push([8, size - 1 - i])
  for (let i = 8; i <= 14; i++) positions.push([size - 15 + i, 8])
  return positions
}

/** 返回模块矩阵，true 表示深色。内容过长时抛错。 */
export function encodeQr(text: string): boolean[][] {
  const byteLength = new TextEncoder().encode(text).length
  let version = 1
  while (version <= MAX_VERSION && capacityBytes(version) < byteLength) version++
  if (version > MAX_VERSION) throw new Error('内容过长，无法生成二维码')

  const size = version * 4 + 17
  const modules: boolean[][] = Array.from({ length: size }, () => new Array<boolean>(size).fill(false))
  const reserved: boolean[][] = Array.from({ length: size }, () => new Array<boolean>(size).fill(false))

  const put = (row: number, col: number, dark: boolean) => {
    modules[row][col] = dark
    reserved[row][col] = true
  }
  const setFinder = (row: number, col: number) => {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const rr = row + r
        const cc = col + c
        if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue
        const inside = r >= 0 && r <= 6 && c >= 0 && c <= 6
        const dark =
          inside && (r === 0 || r === 6 || c === 0 || c === 6 || (r >= 2 && r <= 4 && c >= 2 && c <= 4))
        put(rr, cc, dark)
      }
    }
  }
  setFinder(0, 0)
  setFinder(0, size - 7)
  setFinder(size - 7, 0)

  for (const row of ALIGN_POSITIONS[version]) {
    for (const col of ALIGN_POSITIONS[version]) {
      if (reserved[row][col]) continue
      for (let r = -2; r <= 2; r++) {
        for (let c = -2; c <= 2; c++) {
          put(row + r, col + c, Math.max(Math.abs(r), Math.abs(c)) !== 1)
        }
      }
    }
  }

  // 时序图形：第 6 行与第 6 列交替
  for (let i = 8; i < size - 8; i++) {
    put(6, i, i % 2 === 0)
    put(i, 6, i % 2 === 0)
  }
  // 固定深色模块
  put(size - 8, 8, true)

  const positions = formatPositions(size)
  // 先把格式信息占位标记成功能区，数据位才不会写进来
  for (const [row, col] of positions) reserved[row][col] = true

  if (version >= 7) {
    const bits = VERSION_BITS[version]
    for (let i = 0; i < 18; i++) {
      const dark = ((bits >> i) & 1) === 1
      const r = Math.floor(i / 3)
      const c = (i % 3) + size - 11
      put(r, c, dark)
      put(c, r, dark)
    }
  }

  // 数据位按之字形自右向左、上下交替填入非功能区
  const stream = interleave(encodeData(text, version), version)
  const totalBits = stream.length * 8
  let bitIndex = 0
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5
    for (let vertical = 0; vertical < size; vertical++) {
      for (let j = 0; j < 2; j++) {
        const col = right - j
        const upward = ((right + 1) & 2) === 0
        const row = upward ? size - 1 - vertical : vertical
        if (reserved[row][col]) continue
        const dark =
          bitIndex < totalBits ? ((stream[bitIndex >> 3] >> (7 - (bitIndex & 7))) & 1) === 1 : false
        modules[row][col] = dark
        bitIndex++
      }
    }
  }

  // 逐个掩码试算，取惩罚分最低的那个
  let best = modules
  let bestScore = Number.POSITIVE_INFINITY
  for (let maskIndex = 0; maskIndex < MASKS.length; maskIndex++) {
    const maskFn = MASKS[maskIndex]
    const candidate = modules.map((row) => row.slice())
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (!reserved[r][c] && maskFn(r, c)) candidate[r][c] = !candidate[r][c]
      }
    }
    const bits = formatBits(maskIndex)
    positions.forEach(([row, col], index) => {
      candidate[row][col] = ((bits >> (index % 15)) & 1) === 1
    })
    const score = penalty(candidate, size)
    if (score < bestScore) {
      bestScore = score
      best = candidate
    }
  }
  return best
}
