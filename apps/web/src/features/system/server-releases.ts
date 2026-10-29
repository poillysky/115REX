// 服务端版本记录：前端静态维护，与 /auth/me 返回的 server.version 对齐展示。
// 新发版时在此追加一条；列表按日期倒序。

export interface ServerRelease {
  version: string
  /** ISO 日期，仅到日 */
  date: string
  /** 单行摘要，列表里不换行展开 */
  note: string
}

export const SERVER_RELEASES: ServerRelease[] = [
  {
    version: '0.1.0',
    date: '2026-04-01',
    note: '首个可运行版本：鉴权、基础设定、图标库与演示数据。',
  },
]
